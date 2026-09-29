#pragma once
#include "vivyqu/types.h"
#include "vivyqu/collapse.h"
#include <cstdint>
#include <cstddef>

namespace vivyqu {

constexpr uint64_t E9_MAGIC         = 0x564956595F453957ULL; // "VIVY_E9W"
constexpr uint32_t E9_VERSION       = 1;
constexpr uint32_t E9_SUBSPACE_DIM  = 64;
constexpr uint32_t E9_NUM_ROTORS    = 8;

// Cấu trúc lưu 1.024 cặp chỉ số trực giao của 1 rotor Cl(12)
struct RotorPairIndices {
    uint16_t a[1024];
    uint16_t b[1024];
    float    cos_th;
    float    sin_th;
};

// Cấu trúc lưu trữ toàn bộ Trọng số Mô hình E9 trong bộ nhớ L2/L3 (~2.02 MiB)
struct alignas(64) GeometricWeights {
    // Ma trận chiếu W_c: (64, 4096) float32 = 1.048.576 bytes
    float W_c[E9_SUBSPACE_DIM * CL12_DIMENSION];

    // Bộ mã ứng viên (Candidate Codebook): (4096, 64) float32 = 1.048.576 bytes
    float candidate_codebook[CL12_DIMENSION * E9_SUBSPACE_DIM];

    // Chi phí tô pô gốc: (4096,) float32 = 16.384 bytes
    float topology_cost[CL12_DIMENSION];

    // Chi phí tô pô hiệu dụng (0.3 * cost): (4096,) float32 = 16.384 bytes (Precomputed)
    float effective_cost[CL12_DIMENSION];

    // Cấu hình 8 rotor mặc định của Branch C
    RotorConfig default_rotors[E9_NUM_ROTORS];

    // Bảng tra cứu 1.024 cặp chỉ số tiền tính toán cho 8 rotor (32 KiB)
    RotorPairIndices rotor_pairs[E9_NUM_ROTORS];

    float topology_lambda; // 0.3f
    bool  is_loaded;

    void reset() noexcept;
    bool load_from_binary(const char* filepath) noexcept;
    void precompute_rotors() noexcept;
    void update_rotor_angle(size_t rotor_idx, float delta_theta) noexcept;
    void set_rotor_angle(size_t rotor_idx, float theta) noexcept;
};

// Lớp thực thi quyết định hình học E9 tối ưu hóa AVX2 / FMA / BMI2
class GeometricScorer {
public:
    // Thực thi toàn bộ chuỗi quyết định E9 từ latent_h đến chỉ số k*
    static DecisionResult score_and_collapse(
        const GeometricWeights& weights,
        const double* __restrict latent_h,
        const uint8_t* __restrict constraint_bitmask,
        const RotorConfig* __restrict custom_rotors = nullptr,
        size_t custom_rotors_count = 0,
        CandidateScore* __restrict top_candidates = nullptr,
        size_t max_top_candidates = 0
    ) noexcept;

    // Biến đổi rotor Cl(12) trực tiếp trên mảng float32 4096 phần tử
    static void apply_rotors_f32(
        float* __restrict h_rot,
        const RotorPairIndices* __restrict pairs,
        size_t num_rotors
    ) noexcept;

    // Phép nhân ma trận - vector AVX2+FMA: z = W_c * h_rot (64 x 4096 * 4096 -> 64)
    static void project_subspace_64x4096(
        float* __restrict z_out,
        const float* __restrict W_c,
        const float* __restrict h_rot
    ) noexcept;

    // Chấm điểm 4.096 ứng viên & chọn k* bằng BMI2 bitmask skipping & AVX2 FMA
    static DecisionResult score_candidates_masked_argmax(
        const float* __restrict codebook,
        const float* __restrict z_subspace,
        const float* __restrict effective_cost,
        const uint8_t* __restrict constraint_bitmask,
        CandidateScore* __restrict top_candidates,
        size_t max_top_candidates
    ) noexcept;

    // Phép chiếu ngược ma trận chuyển vị AVX2+FMA: grad_h = W_c^T * grad_z (4096 x 64 * 64 -> 4096)
    static void backproject_subspace_transpose(
        float* __restrict grad_h_rot,
        const float* __restrict W_c,
        const float* __restrict grad_z
    ) noexcept;

    // Tính toán bivector torque moment lực Cl(12) trên 8 rotors
    static void compute_rotor_torques(
        const GeometricWeights& weights,
        const float* __restrict h_rot,
        const float* __restrict grad_h_rot,
        float* __restrict out_torques
    ) noexcept;

    // Thực thi 1 bước Hamiltonian Torque Descent thích nghi tại chỗ (< 10 µs)
    static float adapt_torque_step(
        GeometricWeights& weights,
        const double* __restrict latent_h,
        uint32_t chosen_k,
        uint32_t target_k,
        float learning_rate,
        float* __restrict out_torques = nullptr
    ) noexcept;
};


} // namespace vivyqu
