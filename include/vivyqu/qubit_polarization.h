#pragma once
#include <cstdint>
#include <cstddef>
#include <cmath>

#ifdef _WIN32
  #ifdef VIVYQU_EXPORTS
    #define VIVYQU_API extern "C" __declspec(dllexport)
  #else
    #define VIVYQU_API extern "C" __declspec(dllimport)
  #endif
#else
  #define VIVYQU_API extern "C" __attribute__((visibility("default")))
#endif

namespace vivyqu {

enum class QubitPolarization : uint32_t {
    Inertia     = 0, // |00>: Fast-path cú pháp & Early Exit
    Sensory     = 1, // |01>: Tiếp nhận giác quan & Nén KV-Cache
    Action      = 2, // |10>: Sụp đổ Macro-Action E9
    Supervision = 3  // |11>: Giám sát an toàn & Watchdog Fallback
};

// Cấu trúc phân tích phân cực nhận thức
struct PolarizationResult {
    QubitPolarization polarization;
    float             confidence;
    float             energy_inertia;
    float             energy_sensory;
    float             energy_action;
    float             norm_drift;
};

// Phân tích vector trạng thái 4096 chiều thành 4 phân cực Qubit
PolarizationResult analyze_polarization(const float* state_4096, size_t dim = 4096);

// Tính vector điều hướng hoạt hóa (Activation Steering Delta) qua phép biến đổi Clifford
void compute_steering_delta(
    const float* state_in,
    float* delta_out,
    size_t dim = 4096,
    float max_scale = 0.10f
);

} // namespace vivyqu

// C-ABI Exports
VIVYQU_API int32_t vivyqu_core_classify_polarization(
    const float* state_4096,
    size_t dim,
    uint32_t* out_polarization,
    float* out_confidence
);

VIVYQU_API int32_t vivyqu_core_compute_steering(
    const float* state_in,
    float* delta_out,
    size_t dim,
    float max_scale
);
