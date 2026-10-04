// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — C-ABI kernel ACC-Q (docs/DESIGN_ACCQ_KERNELS_CPP.md). K1 trước; K2–K4 thêm sau khi K1 qua cổng.
#pragma once
#include <cstdint>

#ifdef _WIN32
  #ifdef VIVYQU_ACCQ_EXPORTS
    #define ACCQ_API extern "C" __declspec(dllexport)
  #else
    #define ACCQ_API extern "C" __declspec(dllimport)
  #endif
#else
  #define ACCQ_API extern "C" __attribute__((visibility("default")))
#endif

// Mã lỗi chung
enum AccqError : int32_t {
    ACCQ_OK = 0,
    ACCQ_ERR_ARG = 1,      // con trỏ null / tham số sai
    ACCQ_ERR_SIZE = 2,     // vượt giới hạn kích thước
    ACCQ_ERR_NONFINITE = 3,
    ACCQ_ERR_ALLOC = 4,
    ACCQ_ERR_INFEASIBLE = 5  // mọi ứng viên đều bị cấm
};

constexpr int32_t ACCQ_STATES = 4;        // qudit-4
constexpr int32_t ACCQ_K1_MAX_SITES = 13; // 4^13 = 67 108 864 ứng viên

// ---------------- K1: vét cạn năng lượng cặp ----------------
// E(s) = sum_i unary[i*4 + s_i] + sum_{i<j} pair[(i*n + j)*16 + s_i*4 + s_j]
// Ứng viên index = sum_i s_i * 4^i (khớp scripts/acc/common.py). Phần tử pair với i >= j bị bỏ qua.
// forbid: NULL hoặc n*4 byte (khác 0 = site i cấm trạng thái a); ứng viên bị cấm có E = +inf.
// Kết quả: best_idx = argmin (hòa -> index nhỏ nhất), best_E, n_ground = số ứng viên có E <= best_E + tol.
// energies_out: NULL hoặc mảng 4^n double (ghi E của mọi ứng viên, +inf nếu bị cấm).
ACCQ_API int32_t accq_pairwise_bruteforce(int32_t n, const double* unary, const double* pair,
                                          const uint8_t* forbid, double tol,
                                          uint64_t* best_idx, double* best_E, uint64_t* n_ground,
                                          double* energies_out);

// ---------------- K2: statevector qudit-4 (hướng A) ----------------
// Số phức truyền dạng xen kẽ (re, im) double. Biên độ index = sum_i s_i * 4^i.
// Cổng 1-qudit: U 4x4 row-major (32 double). Cổng 2-qudit trên (site_a, site_b): U 16x16 row-major (512 double),
// chỉ số cục bộ = s_a*4 + s_b. Kernel KHÔNG kiểm tính unita (để còn áp toán tử bất kỳ); test kiểm chuẩn riêng.
constexpr int32_t ACCQ_SV_MAX_SITES = 12;  // 4^12 biên độ complex128 = 256 MiB
typedef struct AccqSV AccqSV;
ACCQ_API int32_t accq_sv_create(int32_t n, AccqSV** out);   // trạng thái |0...0>
ACCQ_API void    accq_sv_destroy(AccqSV* sv);
ACCQ_API int32_t accq_sv_reset(AccqSV* sv);
ACCQ_API int32_t accq_sv_set(AccqSV* sv, const double* amp_reim, uint64_t len);  // len = 4^n
ACCQ_API int32_t accq_sv_get(const AccqSV* sv, double* amp_reim, uint64_t len);
ACCQ_API int32_t accq_sv_apply1(AccqSV* sv, int32_t site, const double* u_reim);
ACCQ_API int32_t accq_sv_apply2(AccqSV* sv, int32_t site_a, int32_t site_b, const double* u_reim);
ACCQ_API int32_t accq_sv_norm2(const AccqSV* sv, double* out);
ACCQ_API int32_t accq_sv_probs(const AccqSV* sv, double* probs, uint64_t len);  // |psi_k|^2
// Top-K theo xác suất Born, mask: NULL hoặc 4^n byte (khác 0 = được phép). Hòa -> index nhỏ hơn trước.
// k_out = số ứng viên thực sự trả về (<= k nếu ít ứng viên hợp lệ).
ACCQ_API int32_t accq_sv_topk(const AccqSV* sv, const uint8_t* mask, int32_t k, uint64_t* idx, double* prob,
                              int32_t* k_out);

// ---------------- K3: MPS Born machine (hướng B) ----------------
// bonds: mảng n+1 phần tử, bonds[0] = bonds[n] = 1, 1 <= bonds[i] <= ACCQ_MPS_MAX_BOND.
// tensors: nối tiếp các site; site i có bonds[i]*4*bonds[i+1] số phức (re, im), chỉ số [l][a][r] -> (l*4 + a)*Dr + r.
// psi(s) = A_0[s_0] A_1[s_1] ... A_{n-1}[s_{n-1}] (tích ma trận Dl x Dr). Index ứng viên = sum s_i 4^i (n <= 31).
constexpr int32_t ACCQ_MPS_MAX_SITES = 31;
constexpr int32_t ACCQ_MPS_MAX_BOND = 64;
ACCQ_API int32_t accq_mps_amplitude(int32_t n, const int32_t* bonds, const double* tensors_reim, uint64_t idx,
                                    double* out_reim2);
ACCQ_API int32_t accq_mps_norm2(int32_t n, const int32_t* bonds, const double* tensors_reim, double* out);
// Lấy K mẫu Born chính xác (tuần tự có điều kiện, môi trường phải). seed xác định -> kết quả tái lập.
// idx_out[K], logp_out[K] (log xác suất chuẩn hóa của mẫu). Trả ACCQ_ERR_NONFINITE nếu chuẩn = 0/không hữu hạn.
ACCQ_API int32_t accq_mps_sample(int32_t n, const int32_t* bonds, const double* tensors_reim, int32_t K,
                                 uint64_t seed, uint64_t* idx_out, double* logp_out);

// ---------------- K4: giải mã factor cổ điển (đối chứng) ----------------
// Chuỗi: E = sum_i unary[i*4+s_i] + sum_{i<n-1} chain[i*16 + s_i*4 + s_{i+1}]. Exact. Hòa -> index nhỏ nhất (theo số học DP).
constexpr int32_t ACCQ_K4_MAX_SITES = 31;
constexpr int32_t ACCQ_BEAM_MAX = 65536;
ACCQ_API int32_t accq_chain_viterbi(int32_t n, const double* unary, const double* chain, const uint8_t* forbid,
                                    uint64_t* best_idx, double* best_E);
// Beam tổng quát trên năng lượng cặp (bố cục unary/pair/forbid như K1). Heuristic, không đảm bảo tối ưu.
ACCQ_API int32_t accq_pairwise_beam(int32_t n, const double* unary, const double* pair, const uint8_t* forbid,
                                    int32_t beam, uint64_t* best_idx, double* best_E);

ACCQ_API const char* accq_version();
