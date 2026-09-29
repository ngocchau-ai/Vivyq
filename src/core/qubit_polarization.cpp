#define VIVYQU_EXPORTS
#include "vivyqu/qubit_polarization.h"
#include <cmath>
#include <algorithm>
#include <cstring>

namespace vivyqu {

PolarizationResult analyze_polarization(const float* state_4096, size_t dim) {
    PolarizationResult res{};
    if (!state_4096 || dim == 0) {
        res.polarization = QubitPolarization::Supervision;
        res.confidence = 0.0f;
        res.norm_drift = 1.0f;
        return res;
    }

    float total_sq = 0.0f;
    float q_energy[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    size_t q_size = dim / 4;
    float max_sq = 0.0f;

    for (size_t i = 0; i < dim; ++i) {
        float val = state_4096[i];
        if (std::isnan(val) || std::isinf(val)) {
            res.polarization = QubitPolarization::Supervision;
            res.confidence = 0.0f;
            res.norm_drift = 999.0f;
            return res;
        }
        float sq = val * val;
        total_sq += sq;
        if (sq > max_sq) max_sq = sq;

        size_t q_idx = std::min(i / (q_size > 0 ? q_size : 1), static_cast<size_t>(3));
        q_energy[q_idx] += sq;
    }

    float norm = std::sqrt(total_sq);
    res.norm_drift = std::abs(norm - 1.0f);

    // Bất thường norm quá lớn -> Supervision
    if (norm < 1e-6f || res.norm_drift > 0.40f) {
        res.polarization = QubitPolarization::Supervision;
        res.confidence = 0.90f;
        return res;
    }

    res.energy_inertia = q_energy[0] / (total_sq + 1e-8f);
    res.energy_action  = q_energy[1] / (total_sq + 1e-8f);
    res.energy_sensory = (q_energy[0] + q_energy[2]) / (total_sq + 1e-8f);

    float peak_ratio = max_sq / (total_sq + 1e-8f);

    // Phân loại phân cực
    if (res.energy_action > 0.35f || peak_ratio > 0.04f) {
        // Đỉnh nhọn hoặc năng lượng dồn về khối Động lực/Tay -> Action (|10>)
        res.polarization = QubitPolarization::Action;
        res.confidence = std::min(1.0f, res.energy_action * 2.0f);
    } else if (res.energy_sensory > 0.55f) {
        // Năng lượng dồn vào Mắt/Tai -> Sensory (|01>)
        res.polarization = QubitPolarization::Sensory;
        res.confidence = std::min(1.0f, res.energy_sensory);
    } else {
        // Năng lượng phân bố đều, quán tính cú pháp -> Inertia (|00>)
        res.polarization = QubitPolarization::Inertia;
        res.confidence = 0.85f;
    }

    return res;
}

void compute_steering_delta(
    const float* state_in,
    float* delta_out,
    size_t dim,
    float max_scale
) {
    if (!state_in || !delta_out || dim == 0) return;

    float effective_scale = std::min(max_scale, 0.10f);
    if (effective_scale <= 0.0f) {
        std::memset(delta_out, 0, dim * sizeof(float));
        return;
    }

    float norm_in_sq = 0.0f;
    for (size_t i = 0; i < dim; ++i) {
        norm_in_sq += state_in[i] * state_in[i];
    }
    float norm_in = std::sqrt(norm_in_sq);

    // Sinh vector steering trực giao thông qua bivector shift (Spin(12) torque projection)
    float delta_norm_sq = 0.0f;
    for (size_t i = 0; i < dim; ++i) {
        size_t paired_idx = (i + 1) % dim;
        float diff = state_in[paired_idx] - state_in[i];
        delta_out[i] = diff;
        delta_norm_sq += diff * diff;
    }

    float delta_norm = std::sqrt(delta_norm_sq);
    if (delta_norm > 1e-7f) {
        // Chuẩn hóa và scale về tối đa effective_scale * norm_in (kèm biên an toàn làm tròn float32)
        float target_norm = effective_scale * 0.999f * (norm_in > 1e-6f ? norm_in : 1.0f);
        float factor = target_norm / delta_norm;
        for (size_t i = 0; i < dim; ++i) {
            delta_out[i] *= factor;
        }
    } else {
        std::memset(delta_out, 0, dim * sizeof(float));
    }
}

} // namespace vivyqu

// C-ABI Implementation
VIVYQU_API int32_t vivyqu_core_classify_polarization(
    const float* state_4096,
    size_t dim,
    uint32_t* out_polarization,
    float* out_confidence
) {
    if (!state_4096 || !out_polarization || !out_confidence) return -1;
    auto res = vivyqu::analyze_polarization(state_4096, dim);
    *out_polarization = static_cast<uint32_t>(res.polarization);
    *out_confidence   = res.confidence;
    return 0;
}

VIVYQU_API int32_t vivyqu_core_compute_steering(
    const float* state_in,
    float* delta_out,
    size_t dim,
    float max_scale
) {
    if (!state_in || !delta_out) return -1;
    vivyqu::compute_steering_delta(state_in, delta_out, dim, max_scale);
    return 0;
}
