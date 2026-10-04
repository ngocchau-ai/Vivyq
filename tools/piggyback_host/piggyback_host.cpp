// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — Piggyback Host (ADR_2026-10-04): libllama + cb_eval + vivyqu_core in-process, đo M1/M2/M3
//
// Dùng:
//   piggyback_host --selftest
//   piggyback_host -m model.gguf -w e9_weights.bin [-l 31] [-t 6] [-n 64] [-r 3] [-p "prompt"]
// Kết quả: 1 dòng JSON "RESULT {...}" ra stdout (M1 µs, M2 tok/s, M3). Lỗi -> mã thoát != 0.
// GIỚI HẠN (ADR §4): trọng số E9 không được huấn luyện trên hidden-state LLM -> k* vô nghĩa về chất lượng; chỉ đo độ trễ.
#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"
#include "vivyqu/c_api.h"
#include "vivyqu/types.h"

#include <algorithm>
#include <chrono>
#include <clocale>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

using clk = std::chrono::steady_clock;

namespace {

constexpr int N_IN = 2560;
constexpr int N_OUT = 4096;  // = vivyqu::CL12_DIMENSION
constexpr uint64_t P2_SEED = 20261004ULL;

// ---------- P2 runtime: pad + dấu ±1 cố định + Walsh–Hadamard chuẩn hóa (trực giao) ----------
struct HadamardP2 {
    std::vector<double> sign;
    HadamardP2() : sign(N_OUT) {
        uint64_t x = P2_SEED;
        for (int i = 0; i < N_OUT; ++i) {  // splitmix64
            x += 0x9E3779B97F4A7C15ULL;
            uint64_t z = x;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            z ^= z >> 31;
            sign[i] = (z & 1) ? 1.0 : -1.0;
        }
    }
    static void fwht(double * a) {
        for (int len = 1; len < N_OUT; len <<= 1)
            for (int i = 0; i < N_OUT; i += len << 1)
                for (int j = i; j < i + len; ++j) {
                    const double u = a[j], v = a[j + len];
                    a[j] = u + v;
                    a[j + len] = u - v;
                }
    }
    // x (N_IN, đã chuẩn hóa) -> z (N_OUT)
    void apply(const float * x, double * z) const {
        for (int i = 0; i < N_IN; ++i) z[i] = sign[i] * (double) x[i];
        for (int i = N_IN; i < N_OUT; ++i) z[i] = 0.0;
        fwht(z);
        const double s = 1.0 / 64.0;  // 1/sqrt(4096)
        for (int i = 0; i < N_OUT; ++i) z[i] *= s;
    }
};

int selftest() {
    HadamardP2 p;
    std::vector<float> x(N_IN);
    uint64_t r = 7;
    double n2 = 0;
    for (int i = 0; i < N_IN; ++i) {
        r = r * 6364136223846793005ULL + 1442695040888963407ULL;
        x[i] = (float) ((double) (r >> 11) / 9007199254740992.0 - 0.5);
        n2 += (double) x[i] * x[i];
    }
    std::vector<double> z(N_OUT);
    p.apply(x.data(), z.data());
    double m2 = 0;
    for (double v : z) m2 += v * v;
    // nghịch đảo: H là đối hợp (H·H = 4096·I) -> x = sign ⊙ (H z)/64
    std::vector<double> back(z);
    HadamardP2::fwht(back.data());
    double err = 0, pad = 0;
    for (int i = 0; i < N_IN; ++i) err = std::max(err, std::fabs(back[i] / 64.0 * p.sign[i] - (double) x[i]));
    for (int i = N_IN; i < N_OUT; ++i) pad = std::max(pad, std::fabs(back[i] / 64.0));
    const bool ok = std::fabs(m2 - n2) / n2 < 1e-12 && err < 1e-12 && pad < 1e-12;
    printf("SELFTEST norm_in=%.12f norm_out=%.12f max_inv_err=%.3e max_pad_leak=%.3e -> %s\n", n2, m2, err, pad,
           ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

// ---------- bắt l_out-L của token cuối ----------
struct Capture {
    std::string want;
    std::vector<float> h = std::vector<float>(N_IN);
    bool got = false;
    std::string error;
};

bool cb_eval(struct ggml_tensor * t, bool ask, void * ud) {
    auto * c = static_cast<Capture *>(ud);
    const bool match = c->want == t->name;
    if (ask) return match;
    if (!match) return true;
    if (t->type != GGML_TYPE_F32 || t->ne[0] != N_IN || t->nb[0] != sizeof(float)) {
        c->error = std::string("tensor bất thường: ") + t->name;
        return false;
    }
    ggml_backend_tensor_get(t, c->h.data(), (size_t) (t->ne[1] - 1) * t->nb[1], N_IN * sizeof(float));
    c->got = true;
    return true;
}

double pct(std::vector<double> v, double q) {
    if (v.empty()) return NAN;
    std::sort(v.begin(), v.end());
    return v[std::min(v.size() - 1, (size_t) (q * (double) v.size()))];
}

double median(std::vector<double> v) { return pct(std::move(v), 0.5); }

struct RunStats {
    std::vector<double> tok_ms;     // thời gian decode từng token (không gồm prefill)
    std::vector<double> decide_us;  // M1: copy + chuẩn hóa + P2 + core
    int errors = 0;
};

int decode_one(llama_context * ctx, llama_batch_ext * b, llama_token tok, llama_pos pos) {
    llama_batch_ext_clear(b);
    const int32_t idx = llama_batch_ext_add_token(b, 0, tok);
    llama_batch_ext_set_pos(b, idx, &pos);
    llama_batch_ext_set_output_logits(b, idx, true);
    return llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, b);
}

}  // namespace

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    if (argc == 2 && std::strcmp(argv[1], "--selftest") == 0) return selftest();

    std::string model_path, weights, prompt = "Explain briefly why the sky is blue.";
    int layer = 31, threads = 6, n_gen = 64, reps = 3;
    for (int i = 1; i + 1 < argc; i += 2) {
        std::string k = argv[i];
        if (k == "-m") model_path = argv[i + 1];
        else if (k == "-w") weights = argv[i + 1];
        else if (k == "-l") layer = std::atoi(argv[i + 1]);
        else if (k == "-t") threads = std::atoi(argv[i + 1]);
        else if (k == "-n") n_gen = std::atoi(argv[i + 1]);
        else if (k == "-r") reps = std::atoi(argv[i + 1]);
        else if (k == "-p") prompt = argv[i + 1];
        else { fprintf(stderr, "tham số lạ: %s\n", k.c_str()); return 1; }
    }
    if (model_path.empty() || weights.empty() || n_gen <= 0 || reps <= 0 || threads <= 0) {
        fprintf(stderr, "usage: %s -m model.gguf -w e9_weights.bin [-l 31] [-t 6] [-n 64] [-r 3] [-p prompt]\n", argv[0]);
        return 1;
    }

    if (vivyqu_core_init() != vivyqu::ERR_NONE) { fprintf(stderr, "ERROR core init\n"); return 2; }
    if (vivyqu_core_load_e9_weights(weights.c_str()) != vivyqu::ERR_NONE) {
        fprintf(stderr, "ERROR không nạp được trọng số E9: %s\n", weights.c_str());
        return 2;
    }

    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    llama_model * model = llama_model_load_from_file(model_path.c_str(), mp);
    if (!model) { fprintf(stderr, "ERROR nạp model\n"); return 2; }
    if (llama_model_n_embd(model) != N_IN) { fprintf(stderr, "ERROR n_embd != %d\n", N_IN); return 2; }
    if (layer < 0 || layer >= llama_model_n_layer(model)) { fprintf(stderr, "ERROR layer ngoài phạm vi\n"); return 2; }
    const llama_vocab * vocab = llama_model_get_vocab(model);

    const int n_prompt = -llama_tokenize(vocab, prompt.c_str(), (int32_t) prompt.size(), nullptr, 0, true, true);
    if (n_prompt <= 0) { fprintf(stderr, "ERROR tokenize\n"); return 2; }
    std::vector<llama_token> ptoks(n_prompt);
    llama_tokenize(vocab, prompt.c_str(), (int32_t) prompt.size(), ptoks.data(), n_prompt, true, true);

    Capture cap;
    cap.want = "l_out-" + std::to_string(layer);
    auto make_ctx = [&](bool with_cb) {
        llama_context_params cp = llama_context_default_params();
        cp.n_ctx = n_prompt + n_gen + 16;
        cp.n_batch = cp.n_ctx;
        cp.n_ubatch = cp.n_ctx;
        cp.n_threads = threads;
        cp.n_threads_batch = threads;
        cp.no_perf = true;
        if (with_cb) {
            cp.cb_eval = cb_eval;
            cp.cb_eval_user_data = &cap;
        }
        return llama_init_from_model(model, cp);
    };
    llama_context * ctx_plain = make_ctx(false);
    llama_context * ctx_cb = make_ctx(true);
    if (!ctx_plain || !ctx_cb) { fprintf(stderr, "ERROR tạo context\n"); return 2; }

    HadamardP2 p2;
    std::vector<float> xs(N_IN);
    auto * in = new vivyqu::VivyquInputFrame{};
    vivyqu::VivyquOutputFrame out{};
    in->magic_header = vivyqu::MAGIC_INPUT_FRAME;
    in->version = vivyqu::ABI_VERSION_1_0;
    in->mode_flags = vivyqu::MODE_GEOMETRIC_E9;
    in->temperature = 1.0f;
    in->active_rotors = 0;
    std::memset(in->constraint_bitmask, 0xFF, sizeof(in->constraint_bitmask));

    RunStats plain, piggy;
    uint32_t last_k = 0;
    uint64_t seq = 0;
    auto run = [&](llama_context * ctx, bool decide, RunStats & st) -> int {
        llama_memory_clear(llama_get_memory(ctx), true);
        llama_sampler * smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
        llama_sampler_chain_add(smpl, llama_sampler_init_greedy());
        llama_batch_ext * b = llama_batch_ext_init(ctx);
        llama_batch_ext_clear(b);
        for (int i = 0; i < n_prompt; ++i) {
            const int32_t idx = llama_batch_ext_add_token(b, 0, ptoks[i]);
            const llama_pos pos = i;
            llama_batch_ext_set_pos(b, idx, &pos);
        }
        llama_batch_ext_set_output_logits(b, n_prompt - 1, true);
        if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, b) != 0) return 3;  // prefill: không tính
        for (int g = 0; g < n_gen; ++g) {
            const llama_token tok = llama_sampler_sample(smpl, ctx, -1);
            cap.got = false;
            cap.error.clear();
            const auto t0 = clk::now();
            if (decode_one(ctx, b, tok, n_prompt + g) != 0 || !cap.error.empty()) return 4;
            const auto t1 = clk::now();
            st.tok_ms.push_back(std::chrono::duration<double, std::milli>(t1 - t0).count());
            if (decide) {
                if (!cap.got) return 5;
                const auto d0 = clk::now();
                // chuẩn hóa: PROTOTYPE dùng mu=0, sd=1 (mu/sd thật fit trên train ở S4) — chi phí giữ nguyên
                for (int i = 0; i < N_IN; ++i) xs[i] = cap.h[i];
                p2.apply(xs.data(), in->latent_vector);
                in->sequence_id = ++seq;
                const int32_t rc = vivyqu_core_step_e9(in, &out);
                const auto d1 = clk::now();
                if (rc != vivyqu::ERR_NONE || out.error_code != vivyqu::ERR_NONE) ++st.errors;
                last_k = out.best_decision_idx;
                st.decide_us.push_back(std::chrono::duration<double, std::micro>(d1 - d0).count());
            }
        }
        llama_batch_ext_free(b);
        llama_sampler_free(smpl);
        return 0;
    };

    for (int r = 0; r < reps; ++r) {  // xen kẽ thứ tự để triệt nhiễu nhiệt/cache
        const bool cb_first = (r % 2) == 1;
        int rc = cb_first ? run(ctx_cb, true, piggy) : run(ctx_plain, false, plain);
        if (rc == 0) rc = cb_first ? run(ctx_plain, false, plain) : run(ctx_cb, true, piggy);
        if (rc != 0) { fprintf(stderr, "ERROR run rep %d rc=%d %s\n", r, rc, cap.error.c_str()); return rc; }
        fprintf(stderr, "rep %d done\n", r);
    }

    const double tok_plain = median(plain.tok_ms), tok_cb = median(piggy.tok_ms);
    const double m1_p50 = pct(piggy.decide_us, 0.5), m1_p99 = pct(piggy.decide_us, 0.99);
    const double m1_max = piggy.decide_us.empty() ? NAN : *std::max_element(piggy.decide_us.begin(), piggy.decide_us.end());
    const double slow = (tok_cb - tok_plain) / tok_plain * 100.0;
    printf("RESULT {\"layer\":%d,\"threads\":%d,\"n_gen\":%d,\"reps\":%d,\"n_prompt\":%d,"
           "\"M1_decide_us\":{\"p50\":%.2f,\"p99\":%.2f,\"max\":%.2f,\"n\":%zu,\"core_errors\":%d,\"pass_p99_le_1000us\":%s},"
           "\"M2_tok_ms_median\":{\"plain\":%.3f,\"cb\":%.3f,\"tok_s_plain\":%.2f,\"tok_s_cb\":%.2f,\"slowdown_pct\":%.2f,\"pass_le_5pct\":%s},"
           "\"M3_marginal_ratio\":%.5f,\"last_k\":%u,\"quality\":\"VO_NGHIA (E9 weights khong train tren hidden-state)\"}\n",
           layer, threads, n_gen, reps, n_prompt, m1_p50, m1_p99, m1_max, piggy.decide_us.size(), piggy.errors,
           (m1_p99 <= 1000.0 && piggy.errors == 0) ? "true" : "false", tok_plain, tok_cb, 1000.0 / tok_plain,
           1000.0 / tok_cb, slow, slow <= 5.0 ? "true" : "false", (m1_p50 / 1000.0) / tok_cb, last_k);

    delete in;
    llama_free(ctx_cb);
    llama_free(ctx_plain);
    llama_model_free(model);
    llama_backend_free();
    vivyqu_core_cleanup();
    return 0;
}
