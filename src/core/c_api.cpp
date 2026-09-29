#define VIVYQU_EXPORTS
#include "vivyqu/c_api.h"
#include "vivyqu/clifford_cl12.h"
#include "vivyqu/rotor_spin12.h"
#include "vivyqu/hamiltonian_flow.h"
#include "vivyqu/collapse.h"
#include "vivyqu/geometric_scorer.h"

#include <chrono>
#include <cmath>
#include <cstring>
#include <cstdlib>

#ifdef _WIN32
#include <malloc.h>
#endif

namespace {
    struct CoreContext {
        alignas(64) vivyqu::Cl12Multivector state;
        alignas(64) vivyqu::GivensRotor rotors[vivyqu::MAX_ACTIVE_ROTORS];
        alignas(64) vivyqu::GeometricWeights e9_weights;
    };

    static CoreContext* g_ctx = nullptr;

    inline void zero_output_frame(vivyqu::VivyquOutputFrame* out_frame) noexcept {
        uint8_t* p = reinterpret_cast<uint8_t*>(out_frame);
        for (size_t i = 0; i < sizeof(vivyqu::VivyquOutputFrame); ++i) {
            p[i] = 0;
        }
    }
}

VIVYQU_API int32_t vivyqu_core_init() {
    if (!g_ctx) {
#ifdef _WIN32
        g_ctx = static_cast<CoreContext*>(_aligned_malloc(sizeof(CoreContext), 64));
#else
        void* ptr = nullptr;
        posix_memalign(&ptr, 64, sizeof(CoreContext));
        g_ctx = static_cast<CoreContext*>(ptr);
#endif
    }
    if (g_ctx) {
        g_ctx->state.reset();
        g_ctx->e9_weights.reset();

        // Tự động dò tìm nạp trọng số E9 nếu có sẵn ở đường dẫn mặc định
        const char* default_paths[] = {
            "data/e9_weights.bin",
            "results/branch_c/e9_weights.bin",
            "../data/e9_weights.bin",
            "../results/branch_c/e9_weights.bin"
        };
        for (const char* p : default_paths) {
            if (g_ctx->e9_weights.load_from_binary(p)) {
                break;
            }
        }

        return vivyqu::ERR_NONE;
    }
    return vivyqu::ERR_MATH_OVERFLOW;
}

VIVYQU_API int32_t vivyqu_core_load_e9_weights(const char* weights_bin_path) {
    if (!weights_bin_path) return vivyqu::ERR_INPUT_NAN_INF;

    if (!g_ctx) {
        int32_t rc = vivyqu_core_init();
        if (rc != vivyqu::ERR_NONE) return rc;
    }

    if (!g_ctx->e9_weights.load_from_binary(weights_bin_path)) {
        return vivyqu::ERR_INPUT_NAN_INF;
    }
    return vivyqu::ERR_NONE;
}

VIVYQU_API int32_t vivyqu_core_cleanup() {
    if (g_ctx) {
#ifdef _WIN32
        _aligned_free(g_ctx);
#else
        std::free(g_ctx);
#endif
        g_ctx = nullptr;
    }
    return vivyqu::ERR_NONE;
}

VIVYQU_API const char* vivyqu_core_version() {
    return "VivyQu Core Engine v1.2.0 (E9 Geometric Scorer AVX2/FMA/BMI2 Locked)";
}

VIVYQU_API int32_t vivyqu_core_step_e9(const vivyqu::VivyquInputFrame* in_frame, vivyqu::VivyquOutputFrame* out_frame) {
    if (!in_frame || !out_frame) {
        return vivyqu::ERR_INPUT_NAN_INF;
    }

    if (!g_ctx) {
        vivyqu_core_init();
        if (!g_ctx) return vivyqu::ERR_MATH_OVERFLOW;
    }

    // Nếu trọng số chưa nạp, thử tìm nạp lại
    if (!g_ctx->e9_weights.is_loaded) {
        const char* default_paths[] = {
            "data/e9_weights.bin",
            "results/branch_c/e9_weights.bin",
            "../data/e9_weights.bin",
            "../results/branch_c/e9_weights.bin"
        };
        for (const char* p : default_paths) {
            if (g_ctx->e9_weights.load_from_binary(p)) break;
        }
        if (!g_ctx->e9_weights.is_loaded) {
            return vivyqu::ERR_INPUT_NAN_INF;
        }
    }

    auto t_start = std::chrono::high_resolution_clock::now();

    // 1. Kiểm tra Magic Header
    if (in_frame->magic_header != vivyqu::MAGIC_INPUT_FRAME) {
        zero_output_frame(out_frame);
        out_frame->magic_reply = vivyqu::MAGIC_OUTPUT_FRAME;
        out_frame->sequence_id = in_frame->sequence_id;
        out_frame->error_code = vivyqu::ERR_INPUT_NAN_INF;
        return vivyqu::ERR_INPUT_NAN_INF;
    }

    // 2. Xác định cấu hình rotor
    size_t active_rot = std::min(static_cast<size_t>(in_frame->active_rotors), vivyqu::MAX_ACTIVE_ROTORS);
    const vivyqu::RotorConfig* rot_ptr = (active_rot > 0) ? in_frame->rotors : nullptr;

    // 3. Thực thi chấm điểm và sụp đổ hình học
    vivyqu::CandidateScore top8[8];
    vivyqu::DecisionResult decision = vivyqu::GeometricScorer::score_and_collapse(
        g_ctx->e9_weights,
        in_frame->latent_vector,
        in_frame->constraint_bitmask,
        rot_ptr,
        active_rot,
        top8,
        8
    );

    auto t_end = std::chrono::high_resolution_clock::now();
    uint64_t elapsed_ns = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(t_end - t_start).count()
    );

    // 4. Điền OutputFrame chuẩn ABI
    zero_output_frame(out_frame);
    out_frame->magic_reply = vivyqu::MAGIC_OUTPUT_FRAME;
    out_frame->sequence_id = in_frame->sequence_id;
    out_frame->error_code = decision.is_valid ? vivyqu::ERR_NONE : vivyqu::ERR_ALL_CONSTRAINTS_VIOLATED;
    out_frame->status_flags = vivyqu::FLAG_IS_DETERMINISTIC | vivyqu::FLAG_GEOMETRIC_E9;
    out_frame->latency_core_ns = elapsed_ns;

    out_frame->best_decision_idx = decision.best_index;
    out_frame->valid_candidates = decision.valid_count;
    out_frame->best_confidence = decision.confidence;
    out_frame->norm_drift = 0.0;
    out_frame->system_entropy = 0.0;

    for (size_t i = 0; i < 8; ++i) {
        out_frame->top_candidates[i] = top8[i];
    }

    return vivyqu::ERR_NONE;
}

VIVYQU_API int32_t vivyqu_core_step(const vivyqu::VivyquInputFrame* in_frame, vivyqu::VivyquOutputFrame* out_frame) {
    if (!in_frame || !out_frame) {
        return vivyqu::ERR_INPUT_NAN_INF;
    }

    // Nếu cờ yêu cầu E9 Geometric Scorer, điều phối sang pipeline E9
    if ((in_frame->mode_flags & vivyqu::MODE_GEOMETRIC_E9) != 0) {
        return vivyqu_core_step_e9(in_frame, out_frame);
    }

    if (!g_ctx) {
        vivyqu_core_init();
        if (!g_ctx) return vivyqu::ERR_MATH_OVERFLOW;
    }

    auto t_start = std::chrono::high_resolution_clock::now();

    // 1. Kiểm tra Magic Header
    if (in_frame->magic_header != vivyqu::MAGIC_INPUT_FRAME) {
        zero_output_frame(out_frame);
        out_frame->magic_reply = vivyqu::MAGIC_OUTPUT_FRAME;
        out_frame->sequence_id = in_frame->sequence_id;
        out_frame->error_code = vivyqu::ERR_INPUT_NAN_INF;
        return vivyqu::ERR_INPUT_NAN_INF;
    }

    // 2. Nạp và chuẩn hóa L2 multivector
    g_ctx->state.ingest_and_normalize(in_frame->latent_vector);

    // 3. Áp dụng Rotor nhân tử nếu có yêu cầu
    size_t num_rotors = std::min(static_cast<size_t>(in_frame->active_rotors), vivyqu::MAX_ACTIVE_ROTORS);
    if (num_rotors > 0) {
        for (size_t m = 0; m < num_rotors; ++m) {
            const auto& rc = in_frame->rotors[m];
            g_ctx->rotors[m].plane_i = rc.plane_i;
            g_ctx->rotors[m].plane_j = rc.plane_j;
            float half_th = rc.angle_theta * 0.5f;
            g_ctx->rotors[m].cos_half_th = std::cos(half_th);
            g_ctx->rotors[m].sin_half_th = std::sin(half_th);
        }
        vivyqu::Spin12Engine::apply_factorized_rotors(g_ctx->state, g_ctx->rotors, num_rotors);
    }

    // 4. Thực thi Sụp đổ trạng thái (Born hoặc Argmax cơ sở)
    vivyqu::DecisionResult decision;
    bool is_born = (in_frame->mode_flags & vivyqu::MODE_CALIBRATED_BORN) != 0;
    if (is_born) {
        uint64_t seed = in_frame->timestamp_ns ^ (in_frame->sequence_id * 6364136223846793005ULL);
        decision = vivyqu::CollapseEngine::collapse_born_sampled(
            g_ctx->state,
            in_frame->constraint_bitmask,
            in_frame->temperature,
            seed
        );
    } else {
        decision = vivyqu::CollapseEngine::collapse_hard_masked(
            g_ctx->state,
            in_frame->constraint_bitmask
        );
    }

    // 5. Tính toán sai số bảo toàn chuẩn
    double sq_norm = g_ctx->state.compute_squared_norm();
    double norm_drift = std::abs(sq_norm - 1.0);

    auto t_end = std::chrono::high_resolution_clock::now();
    uint64_t elapsed_ns = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(t_end - t_start).count()
    );

    // 6. Điền dữ liệu ra OutputFrame (an toàn mọi alignment)
    zero_output_frame(out_frame);
    out_frame->magic_reply = vivyqu::MAGIC_OUTPUT_FRAME;
    out_frame->sequence_id = in_frame->sequence_id;
    out_frame->error_code = decision.is_valid ? vivyqu::ERR_NONE : vivyqu::ERR_ALL_CONSTRAINTS_VIOLATED;
    out_frame->status_flags = is_born ? 0 : vivyqu::FLAG_IS_DETERMINISTIC;
    out_frame->latency_core_ns = elapsed_ns;

    out_frame->best_decision_idx = decision.best_index;
    out_frame->valid_candidates = decision.valid_count;
    out_frame->best_confidence = decision.confidence;
    out_frame->norm_drift = norm_drift;
    out_frame->system_entropy = is_born ? 1.0 : 0.0;

    out_frame->top_candidates[0].candidate_idx = decision.best_index;
    out_frame->top_candidates[0].confidence = static_cast<float>(decision.confidence);

    return vivyqu::ERR_NONE;
}

VIVYQU_API float vivyqu_core_adapt_torque(
    const double* latent_h,
    uint32_t chosen_k,
    uint32_t target_k,
    float learning_rate,
    float* out_torques
) {
    if (!g_ctx) {
        vivyqu_core_init();
        if (!g_ctx) return 0.0f;
    }
    if (!g_ctx->e9_weights.is_loaded) {
        const char* default_paths[] = {
            "data/e9_weights.bin",
            "../data/e9_weights.bin",
            "results/branch_c/e9_weights.bin",
            "../results/branch_c/e9_weights.bin"
        };
        for (const char* p : default_paths) {
            if (g_ctx->e9_weights.load_from_binary(p)) break;
        }
    }
    return vivyqu::GeometricScorer::adapt_torque_step(
        g_ctx->e9_weights,
        latent_h,
        chosen_k,
        target_k,
        learning_rate,
        out_torques
    );
}

VIVYQU_API int32_t vivyqu_core_get_rotor_angle(size_t rotor_idx, float* out_angle) {
    if (!g_ctx || !out_angle || rotor_idx >= vivyqu::E9_NUM_ROTORS) {
        return vivyqu::ERR_INPUT_NAN_INF;
    }
    *out_angle = g_ctx->e9_weights.default_rotors[rotor_idx].angle_theta;
    return vivyqu::ERR_NONE;
}

VIVYQU_API int32_t vivyqu_core_set_rotor_angle(size_t rotor_idx, float angle) {
    if (!g_ctx || rotor_idx >= vivyqu::E9_NUM_ROTORS) {
        return vivyqu::ERR_INPUT_NAN_INF;
    }
    g_ctx->e9_weights.set_rotor_angle(rotor_idx, angle);
    return vivyqu::ERR_NONE;
}
