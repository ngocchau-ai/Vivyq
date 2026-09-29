#pragma once
#include <cstdint>
#include <cstddef>

namespace vivyqu {

// Hằng số không gian trạng thái kiến trúc VivyQu
constexpr size_t CL12_DIMENSION       = 4096; // 2^12 basis blades
constexpr size_t CACHELINE_SIZE       = 64;   // Kích thước chuẩn 1 Cacheline x86_64
constexpr size_t CONSTRAINT_MASK_BYTES = 512; // 4.096 bits nén = 512 bytes
constexpr size_t MAX_ACTIVE_ROTORS    = 16;   // Số lượng rotor nhân tử tối đa trong 1 chu kỳ

// Hằng số định danh giao thức IPC (Magic Numbers)
constexpr uint64_t MAGIC_INPUT_FRAME  = 0x564956595155494EULL; // "VIVYQUIN"
constexpr uint64_t MAGIC_OUTPUT_FRAME = 0x5649565951554F55ULL; // "VIVYQUOU"
constexpr uint32_t ABI_VERSION_1_0    = 0x00010000;             // v1.0

// Cờ điều khiển chế độ hoạt động (Mode Flags)
enum ModeFlags : uint32_t {
    MODE_DETERMINISTIC_ARGMAX = 1 << 0, // Bit 0: Chọn argmax xác định (Born rule)
    MODE_CALIBRATED_BORN      = 1 << 1, // Bit 1: Lấy mẫu Born có nhiệt độ
    MODE_FALLBACK_LOWRANK     = 1 << 2, // Bit 2: Kích hoạt chế độ cứu nguy
    FLAG_APPLY_SHADOW_ROTORS  = 1 << 3, // Bit 3: Hoán đổi cấu hình rotor nóng
    MODE_GEOMETRIC_E9         = 1 << 4  // Bit 4: E9 Geometric Scorer (W_c, Codebook, Topology Cost)
};

// Cờ trạng thái đầu ra (Status Flags)
enum StatusFlags : uint32_t {
    STATUS_SUCCESS           = 0,
    FLAG_IS_DETERMINISTIC    = 1 << 0,
    FLAG_RENORMALIZED        = 1 << 1,
    FLAG_FALLBACK_USED       = 1 << 2,
    FLAG_ZERO_NORM_DETECTED  = 1 << 3,
    FLAG_GEOMETRIC_E9        = 1 << 4
};

// Mã lỗi chuẩn của Core
enum ErrorCode : uint32_t {
    ERR_NONE                      = 0,
    ERR_INPUT_NAN_INF             = 1,
    ERR_CORE_TIMEOUT              = 2,
    ERR_ALL_CONSTRAINTS_VIOLATED  = 3,
    ERR_MATH_OVERFLOW             = 4
};

#pragma pack(push, 1)

// Cấu hình từng rotor trong khung truyền
struct RotorConfig {
    uint8_t  plane_i;        // [0..11]
    uint8_t  plane_j;        // [0..11]
    uint16_t reserved_r;     // 2 bytes căn lề
    float    angle_theta;    // Góc quay radian
};

// Cấu hình điểm số Top-M ứng viên
struct CandidateScore {
    uint32_t candidate_idx;  // [0..4095]
    float    confidence;     // Biên độ xác suất
};

// Khung dữ liệu đầu vào Cầu Treo -> VivyQu Core (33.600 bytes = 525 Cachelines)
struct VivyquInputFrame {
    // Header (64 bytes)
    uint64_t magic_header;       // 0x564956595155494E ("VIVYQUIN")
    uint64_t sequence_id;        // Sequence ID tăng đơn điệu
    uint32_t version;            // ABI_VERSION_1_0
    uint32_t mode_flags;         // ModeFlags
    uint64_t timestamp_ns;       // Nanoseconds từ Cầu Treo
    float    temperature;        // Nhiệt độ lấy mẫu Born (mặc định 1.0)
    uint32_t active_rotors;      // Số rotor thực tế (M <= 16)
    uint8_t  reserved_hdr[24];   // Căn lề tròn 64 bytes

    // Mặt nạ ràng buộc cứng (512 bytes = 4.096 bits)
    uint8_t  constraint_bitmask[512];

    // Cấu hình Rotor (256 bytes)
    RotorConfig rotors[16];      // 16 * 8 = 128 bytes
    uint8_t  reserved_rotors[128];

    // Vector ngữ cảnh đầu vào (32.768 bytes = 4.096 float64)
    double   latent_vector[4096];
};

// Khung dữ liệu đầu ra VivyQu Core -> Cầu Treo (256 bytes = 4 Cachelines)
struct VivyquOutputFrame {
    // Header đồng bộ & trạng thái (64 bytes)
    uint64_t magic_reply;        // 0x5649565951554F55 ("VIVYQUOU")
    uint64_t sequence_id;        // Khớp với InputFrame::sequence_id
    uint32_t error_code;         // ErrorCode
    uint32_t status_flags;       // StatusFlags
    uint64_t latency_core_ns;    // Thời gian tính toán Core (nanoseconds)
    uint8_t  reserved_stat[32];  // Căn lề tròn 64 bytes

    // Quyết định cốt lõi (64 bytes)
    uint32_t best_decision_idx;  // k* ∈ [0..4095]
    uint32_t valid_candidates;   // Số ứng viên hợp lệ
    double   best_confidence;    // Xác suất P(k*)
    double   norm_drift;         // |‖ψ‖² - 1.0|
    double   system_entropy;     // Entropy thông tin
    uint8_t  reserved_decision[32]; // Căn lề tròn 64 bytes

    // Top-8 ứng viên dự phòng (128 bytes)
    CandidateScore top_candidates[8]; // 8 * 8 = 64 bytes
    uint8_t  reserved_top_m[64];
};

#pragma pack(pop)

// Kiểm định kích thước ABI bất biến lúc biên dịch (Compile-time assertions)
static_assert(sizeof(VivyquInputFrame) == 33600, "VivyquInputFrame size mismatch! Expected 33600 bytes.");
static_assert(sizeof(VivyquOutputFrame) == 256, "VivyquOutputFrame size mismatch! Expected 256 bytes.");

} // namespace vivyqu
