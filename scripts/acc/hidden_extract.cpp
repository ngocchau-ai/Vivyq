// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — trích residual `l_out-{il}` token cuối (P1 theo layer, spec §3/§8.3)
//
// Dùng: hidden_extract -m model.gguf -i prompts.txt -o out_dir -l 21,31,41 [-t threads] [-c n_ctx]
//   prompts.txt : UTF-8, mỗi dòng 1 prompt (chuỗi "\n" trong dòng được giải mã thành xuống dòng thật).
//   out_dir/L{il}.f32 : float32 nối tiếp, mỗi prompt n_embd giá trị (row-major N x n_embd).
//   out_dir/progress.txt : số prompt đã ghi xong (checkpoint mỗi 100 prompt + cuối) -> chạy lại sẽ TIẾP TỤC.
// Lỗi bất kỳ (tokenize, decode, thiếu tensor, sai kiểu) -> thoát mã != 0, không ghi dữ liệu dở cho prompt đó.
#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"

#include <algorithm>
#include <chrono>
#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

struct Capture {
    std::map<std::string, int> want;            // "l_out-21" -> 21
    std::map<int, std::vector<float>> got;      // il -> n_embd floats (token cuối)
    int n_embd = 0;
    std::string error;
};

static bool cb_eval(struct ggml_tensor * t, bool ask, void * ud) {
    auto * c = static_cast<Capture *>(ud);
    auto it = c->want.find(t->name);
    if (ask) {
        return it != c->want.end();
    }
    if (it == c->want.end()) {
        return true;
    }
    if (t->type != GGML_TYPE_F32 || t->ne[0] != c->n_embd || t->ne[2] != 1 || t->ne[3] != 1 ||
        t->nb[0] != sizeof(float)) {
        c->error = std::string("tensor bất thường: ") + t->name + " type=" + ggml_type_name(t->type) +
                   " ne0=" + std::to_string(t->ne[0]) + " ne1=" + std::to_string(t->ne[1]);
        return false;  // dừng tính toán -> llama_process trả lỗi
    }
    std::vector<float> row(c->n_embd);
    const size_t off = (size_t) (t->ne[1] - 1) * t->nb[1];  // hàng cuối = token cuối
    ggml_backend_tensor_get(t, row.data(), off, row.size() * sizeof(float));
    c->got[it->second] = std::move(row);
    return true;
}

static std::string unescape_nl(const std::string & s) {
    std::string o;
    o.reserve(s.size());
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == '\\' && i + 1 < s.size() && s[i + 1] == 'n') {
            o += '\n';
            ++i;
        } else {
            o += s[i];
        }
    }
    return o;
}

static int fail(const char * msg) {
    fprintf(stderr, "ERROR: %s\n", msg);
    return 2;
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    std::string model_path, in_path, out_dir, layers_s;
    int n_threads = 0, n_ctx = 512;
    for (int i = 1; i + 1 < argc; i += 2) {
        std::string k = argv[i];
        if (k == "-m") model_path = argv[i + 1];
        else if (k == "-i") in_path = argv[i + 1];
        else if (k == "-o") out_dir = argv[i + 1];
        else if (k == "-l") layers_s = argv[i + 1];
        else if (k == "-t") n_threads = std::atoi(argv[i + 1]);
        else if (k == "-c") n_ctx = std::atoi(argv[i + 1]);
        else { fprintf(stderr, "tham số lạ: %s\n", k.c_str()); return 1; }
    }
    if (model_path.empty() || in_path.empty() || out_dir.empty() || layers_s.empty()) {
        fprintf(stderr, "usage: %s -m model.gguf -i prompts.txt -o out_dir -l 21,31,41 [-t N] [-c n_ctx]\n", argv[0]);
        return 1;
    }

    std::vector<std::string> prompts;
    {
        std::ifstream f(in_path, std::ios::binary);
        if (!f) return fail("không mở được file prompt");
        std::string line;
        while (std::getline(f, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) return fail("prompt rỗng trong file (từ chối, để chỉ số khớp)");
            prompts.push_back(unescape_nl(line));
        }
    }
    if (prompts.empty()) return fail("file prompt rỗng");

    fs::create_directories(out_dir);
    size_t done = 0;
    {
        std::ifstream p(fs::path(out_dir) / "progress.txt");
        if (p) p >> done;
    }
    if (done > prompts.size()) return fail("progress.txt lớn hơn số prompt — sai thư mục output?");

    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    llama_model * model = llama_model_load_from_file(model_path.c_str(), mp);
    if (!model) return fail("không nạp được model");
    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int n_embd = llama_model_n_embd(model);
    const int n_layer = llama_model_n_layer(model);

    Capture cap;
    cap.n_embd = n_embd;
    std::vector<int> layers;
    {
        std::stringstream ss(layers_s);
        std::string tok;
        while (std::getline(ss, tok, ',')) {
            int il = std::atoi(tok.c_str());
            if (il < 0 || il >= n_layer) return fail("layer ngoài phạm vi");
            layers.push_back(il);
            cap.want["l_out-" + std::to_string(il)] = il;
        }
    }

    // Kiểm tra kích thước file output khớp progress (chống ghi lệch sau khi bị ngắt giữa chừng).
    std::map<int, FILE *> outs;
    for (int il : layers) {
        fs::path fp = fs::path(out_dir) / ("L" + std::to_string(il) + ".f32");
        const uintmax_t want_bytes = (uintmax_t) done * n_embd * sizeof(float);
        if (fs::exists(fp) && fs::file_size(fp) < want_bytes) {
            return fail("file layer ngắn hơn checkpoint — dữ liệu hỏng, xóa thư mục output và chạy lại");
        } else if (fs::exists(fp) && fs::file_size(fp) > want_bytes) {
            fs::resize_file(fp, want_bytes);  // cắt phần dở dang sau checkpoint cuối
        } else if (!fs::exists(fp) && done != 0) {
            return fail("thiếu file layer trong khi progress > 0");
        }
        FILE * f = std::fopen(fp.string().c_str(), "ab");
        if (!f) return fail("không mở được file output");
        outs[il] = f;
    }

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = n_ctx;
    cp.n_batch = n_ctx;
    cp.n_ubatch = n_ctx;
    cp.cb_eval = cb_eval;
    cp.cb_eval_user_data = &cap;
    if (n_threads > 0) {
        cp.n_threads = n_threads;
        cp.n_threads_batch = n_threads;
    }
    llama_context * ctx = llama_init_from_model(model, cp);
    if (!ctx) return fail("không tạo được context");
    llama_batch_ext * batch = llama_batch_ext_init(ctx);

    fprintf(stderr, "INFO n_embd=%d n_layer=%d prompts=%zu resume_from=%zu threads=%d\n", n_embd, n_layer,
            prompts.size(), done, llama_n_threads(ctx));
    auto t0 = std::chrono::steady_clock::now();
    size_t max_tok = 0;
    for (size_t pi = done; pi < prompts.size(); ++pi) {
        const std::string & pr = prompts[pi];
        int n = -llama_tokenize(vocab, pr.c_str(), (int32_t) pr.size(), nullptr, 0, true, true);
        if (n <= 0 || n > n_ctx) {
            fprintf(stderr, "ERROR prompt %zu: %d token (n_ctx=%d)\n", pi, n, n_ctx);
            return 3;
        }
        std::vector<llama_token> toks(n);
        if (llama_tokenize(vocab, pr.c_str(), (int32_t) pr.size(), toks.data(), n, true, true) < 0) {
            return fail("tokenize thất bại");
        }
        max_tok = std::max(max_tok, (size_t) n);
        llama_memory_clear(llama_get_memory(ctx), true);
        llama_batch_ext_clear(batch);
        for (int i = 0; i < n; ++i) {
            const int32_t idx = llama_batch_ext_add_token(batch, 0, toks[i]);
            const llama_pos pos = i;
            llama_batch_ext_set_pos(batch, idx, &pos);
        }
        llama_batch_ext_set_output_logits(batch, n - 1, true);
        cap.got.clear();
        cap.error.clear();
        if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch) != 0 || !cap.error.empty()) {
            fprintf(stderr, "ERROR prompt %zu: decode thất bại %s\n", pi, cap.error.c_str());
            return 4;
        }
        for (int il : layers) {
            auto g = cap.got.find(il);
            if (g == cap.got.end()) {
                fprintf(stderr, "ERROR prompt %zu: không bắt được l_out-%d\n", pi, il);
                return 5;
            }
            if (std::fwrite(g->second.data(), sizeof(float), n_embd, outs[il]) != (size_t) n_embd) {
                return fail("ghi file thất bại");
            }
        }
        const size_t n_done = pi + 1;
        if (n_done % 100 == 0 || n_done == prompts.size()) {
            for (auto & kv : outs) std::fflush(kv.second);
            std::ofstream p(fs::path(out_dir) / "progress.txt", std::ios::trunc);
            p << n_done;
            const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            fprintf(stderr, "PROGRESS %zu/%zu  %.3f s/prompt  max_tok=%zu\n", n_done, prompts.size(),
                    s / (double) (n_done - done), max_tok);
        }
    }
    for (auto & kv : outs) std::fclose(kv.second);
    llama_batch_ext_free(batch);
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
    fprintf(stderr, "DONE\n");
    return 0;
}
