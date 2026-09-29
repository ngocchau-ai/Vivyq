#include "vivyqu/rotor_spin12.h"
#include <cmath>
#include <algorithm>
#include <immintrin.h>

namespace vivyqu {

void Spin12Engine::apply_factorized_rotors(
    Cl12Multivector& __restrict state,
    const GivensRotor* __restrict rotors,
    size_t count
) noexcept {
    if (!rotors || count == 0) return;

    size_t active_m = std::min(count, MAX_ACTIVE_ROTORS);

    for (size_t m = 0; m < active_m; ++m) {
        const GivensRotor& r = rotors[m];
        if (r.plane_i >= 12 || r.plane_j >= 12 || r.plane_i == r.plane_j) continue;

        uint32_t bit_i = 1u << std::min(r.plane_i, r.plane_j);
        uint32_t bit_j = 1u << std::max(r.plane_i, r.plane_j);
        uint32_t mask_pair = bit_i | bit_j;
        uint32_t free_mask = (~mask_pair) & 0x0FFFu;

        // Góc quay toàn phần: cos(θ) = cos²(θ/2) - sin²(θ/2), sin(θ) = 2 sin(θ/2) cos(θ/2)
        double c = static_cast<double>(r.cos_half_th * r.cos_half_th - r.sin_half_th * r.sin_half_th);
        double s = static_cast<double>(2.0f * r.sin_half_th * r.cos_half_th);

#if defined(__BMI2__)
        // Unroll 4x với BMI2 _pdep_u32: Tận dụng pipeline siêu vô hướng (Superscalar execution)
        for (uint32_t k = 0; k < 1024; k += 4) {
            uint32_t base0 = _pdep_u32(k + 0, free_mask);
            uint32_t base1 = _pdep_u32(k + 1, free_mask);
            uint32_t base2 = _pdep_u32(k + 2, free_mask);
            uint32_t base3 = _pdep_u32(k + 3, free_mask);

            uint32_t a0 = base0 | bit_i, b0 = base0 | bit_j;
            uint32_t a1 = base1 | bit_i, b1 = base1 | bit_j;
            uint32_t a2 = base2 | bit_i, b2 = base2 | bit_j;
            uint32_t a3 = base3 | bit_i, b3 = base3 | bit_j;

            double va0 = state.blades[a0], vb0 = state.blades[b0];
            double va1 = state.blades[a1], vb1 = state.blades[b1];
            double va2 = state.blades[a2], vb2 = state.blades[b2];
            double va3 = state.blades[a3], vb3 = state.blades[b3];

            state.blades[a0] = c * va0 - s * vb0;
            state.blades[b0] = s * va0 + c * vb0;
            state.blades[a1] = c * va1 - s * vb1;
            state.blades[b1] = s * va1 + c * vb1;
            state.blades[a2] = c * va2 - s * vb2;
            state.blades[b2] = s * va2 + c * vb2;
            state.blades[a3] = c * va3 - s * vb3;
            state.blades[b3] = s * va3 + c * vb3;
        }
#else
        for (uint32_t k = 0; k < 1024; ++k) {
            uint32_t base = 0;
            uint32_t m_temp = free_mask;
            uint32_t k_temp = k;
            while (m_temp) {
                uint32_t lsb = m_temp & -m_temp;
                if (k_temp & 1) base |= lsb;
                k_temp >>= 1;
                m_temp &= m_temp - 1;
            }
            uint32_t idx_a = base | bit_i;
            uint32_t idx_b = base | bit_j;

            double val_a = state.blades[idx_a];
            double val_b = state.blades[idx_b];

            state.blades[idx_a] = c * val_a - s * val_b;
            state.blades[idx_b] = s * val_a + c * val_b;
        }
#endif
    }
}

} // namespace vivyqu
