#pragma once
#include "clifford_cl12.h"

namespace vivyqu {

// Khung tham số của 1 rotor bivector cơ sở (tương tự Givens rotation)
struct GivensRotor {
    uint8_t plane_i;      // Chiều thứ nhất của mặt phẳng quay [0..11]
    uint8_t plane_j;      // Chiều thứ hai của mặt phẳng quay  [0..11]
    float   cos_half_th;  // cos(θ / 2)
    float   sin_half_th;  // sin(θ / 2)
};

class Spin12Engine {
public:
    // Áp dụng chuỗi M rotor sandwich: ψ' = R_M ... (R_1 ψ R_1~) ... R_M~
    // Tối ưu hóa cache: Xử lý tại chỗ trên mảng 32 KiB không cấp phát bộ nhớ mới
    // Độ phức tạp: O(M * d) ≈ 16 * 4096 ≈ 6.5 * 10^4 FLOPs (< 4 μs trên CPU)
    static void apply_factorized_rotors(
        Cl12Multivector& __restrict state,
        const GivensRotor* __restrict rotors,
        size_t count
    ) noexcept;
};

} // namespace vivyqu
