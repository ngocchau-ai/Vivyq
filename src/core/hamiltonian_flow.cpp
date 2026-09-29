#include "vivyqu/hamiltonian_flow.h"
#include <cstring>
#include <cmath>

namespace vivyqu {

void BivectorTorque::reset() noexcept {
    std::memset(torque_components, 0, sizeof(torque_components));
}

void HamiltonianEngine::step_torque_descent(
    Cl12Multivector& __restrict state,
    const double* __restrict objective_weights,
    double step_size_delta_tau
) noexcept {
    if (!objective_weights || step_size_delta_tau <= 0.0) return;

    // 1. Điều chế thế năng trực tiếp lên các biên độ theo nguyên lý biến phân
    // ψ_A' = ψ_A * exp(-Δτ * V_A)
    #pragma omp simd
    for (size_t i = 0; i < CL12_DIMENSION; ++i) {
        double penalty = objective_weights[i];
        // Áp dụng hệ số suy giảm thế năng
        double factor = std::exp(-step_size_delta_tau * penalty);
        state.blades[i] *= factor;
    }

    // 2. Tự động tái chuẩn hóa lại về mặt cầu đơn vị
    state.renormalize_in_place();
}

} // namespace vivyqu
