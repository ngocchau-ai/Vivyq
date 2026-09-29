#pragma once
#include "vivyqu/types.h"

#ifdef _WIN32
  #ifdef VIVYQU_EXPORTS
    #define VIVYQU_API extern "C" __declspec(dllexport)
  #else
    #define VIVYQU_API extern "C" __declspec(dllimport)
  #endif
#else
  #define VIVYQU_API extern "C" __attribute__((visibility("default")))
#endif

// Khởi tạo trạng thái và tiền cấp phát bộ nhớ đệm
VIVYQU_API int32_t vivyqu_core_init();

// Nạp trọng số mô hình E9 Geometric Scorer từ file nhị phân
VIVYQU_API int32_t vivyqu_core_load_e9_weights(const char* weights_bin_path);

// Thực thi 1 chu kỳ tính toán thuần từ InputFrame sang OutputFrame (Tự động chọn E9 nếu cờ MODE_GEOMETRIC_E9 bật)
VIVYQU_API int32_t vivyqu_core_step(const vivyqu::VivyquInputFrame* in_frame, vivyqu::VivyquOutputFrame* out_frame);

// Thực thi trực tiếp 1 chu kỳ quyết định bằng E9 Geometric Scorer
VIVYQU_API int32_t vivyqu_core_step_e9(const vivyqu::VivyquInputFrame* in_frame, vivyqu::VivyquOutputFrame* out_frame);

// Giải phóng tài nguyên nội bộ
VIVYQU_API int32_t vivyqu_core_cleanup();

// Trả về chuỗi định danh phiên bản
VIVYQU_API const char* vivyqu_core_version();

// Thích nghi trực tuyến bằng Hamiltonian Torque Descent qua 8 rotors Cl(12)
VIVYQU_API float vivyqu_core_adapt_torque(
    const double* latent_h,
    uint32_t chosen_k,
    uint32_t target_k,
    float learning_rate,
    float* out_torques
);

// Lấy góc quay hiện tại của rotor
VIVYQU_API int32_t vivyqu_core_get_rotor_angle(size_t rotor_idx, float* out_angle);

// Đặt trực tiếp góc quay của rotor
VIVYQU_API int32_t vivyqu_core_set_rotor_angle(size_t rotor_idx, float angle);

