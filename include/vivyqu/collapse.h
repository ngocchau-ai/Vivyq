#pragma once
#include "clifford_cl12.h"

namespace vivyqu {

// Kết quả sụp đổ ra quyết định
struct DecisionResult {
    uint32_t best_index;     // Chỉ số k* tối ưu ∈ [0..4095]
    double   confidence;     // Biên độ xác suất |ψ_{A(k*)}|² ∈ [0.0, 1.0]
    uint32_t valid_count;    // Số lượng ứng viên thỏa mãn ràng buộc
    bool     is_valid;       // true nếu tìm được nghiệm hợp lệ
};

class CollapseEngine {
public:
    // Tìm kiếm xác định có lọc mặt nạ kỹ thuật:
    // k* = argmax_{k ∈ Valid} (ψ_A[k]²)
    // Sử dụng bitmask 512 bytes (4.096 bits) để kiểm tra ràng buộc cực nhanh trong < 1.5 μs
    static DecisionResult collapse_hard_masked(
        const Cl12Multivector& __restrict state,
        const uint8_t* __restrict constraint_bitmask
    ) noexcept;

    // Lấy mẫu Born có nhiệt độ (dành cho chế độ World Director sáng tạo)
    static DecisionResult collapse_born_sampled(
        const Cl12Multivector& __restrict state,
        const uint8_t* __restrict constraint_bitmask,
        float temperature,
        uint64_t seed
    ) noexcept;
};

} // namespace vivyqu
