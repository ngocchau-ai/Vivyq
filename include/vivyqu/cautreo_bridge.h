#pragma once

/**
 * cautreo_bridge.h — C++20 Harmonization Bridge Interface
 * 
 * Kết nối C++20 Vivyqu Core với Thân thể Cầu Treo (C11 engine + Python Host).
 * Đảm bảo căn chỉnh 64-byte, zero-copy, và ánh xạ an toàn.
 */

#include "vivyqu/types.h"
#include "vivyqu/c_api.h"

#include <string>
#include <vector>
#include <memory>

namespace vivyqu {

struct HarmonizedBridgeConfig {
    std::string e9_weights_path = "data/e9_weights.bin";
    float default_temperature = 1.0f;
    bool enable_watchdog = true;
};

class CautreoHarmonizedBridge {
public:
    explicit CautreoHarmonizedBridge(const HarmonizedBridgeConfig& config = HarmonizedBridgeConfig());
    ~CautreoHarmonizedBridge();

    // Khởi tạo lõi và nạp trọng số E9
    bool initialize();

    // Bước sụp đổ E9 trực tiếp qua con trỏ bộ đệm tĩnh (Zero-copy in hot path)
    int32_t step_direct(const VivyquInputFrame* in_frame, VivyquOutputFrame* out_frame);

    // Áp dụng mặt nạ ràng buộc an toàn (đánh dấu bit = 0 cho các nhánh cấm)
    static void apply_constraint_mask(
        VivyquInputFrame& frame,
        const std::vector<uint32_t>& prohibited_actions
    );

    // Giải phóng
    void shutdown();

private:
    HarmonizedBridgeConfig config_;
    bool is_initialized_ = false;
};

} // namespace vivyqu
