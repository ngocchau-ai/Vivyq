#ifndef CAUTREO_VIVYQU_BRIDGE_H
#define CAUTREO_VIVYQU_BRIDGE_H

/*
 * cautreo_vivyqu_bridge.h — CAUTREO Body <-> Vivyqu Soul Harmonization Bridge
 *
 * C11 Header tương thích 100% ABI nhị phân với Vivyqu Core (C++20 AVX2).
 * Đảm bảo Zero-copy, Zero-allocation trong hot path giữa Thân thể Cầu Treo và Linh hồn Vivy.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#include "score_graph.h"
#include "context_chain.h"
#include "context_memory.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ── Hằng số Giao thức Nhị phân ───────────────────────────────────────── */
#define CT_VIVYQU_CL12_DIMENSION        4096
#define CT_VIVYQU_CONSTRAINT_MASK_BYTES 512
#define CT_VIVYQU_MAX_ACTIVE_ROTORS     16

#define CT_VIVYQU_MAGIC_INPUT           0x564956595155494EULL  /* "VIVYQUIN" */
#define CT_VIVYQU_MAGIC_OUTPUT          0x5649565951554F55ULL  /* "VIVYQUOU" */
#define CT_VIVYQU_ABI_VERSION_1_0       0x00010000

/* ── Cờ Điều Khiển (Mode Flags) ───────────────────────────────────────── */
#define CT_VIVYQU_MODE_DETERMINISTIC_ARGMAX (1 << 0)
#define CT_VIVYQU_MODE_CALIBRATED_BORN      (1 << 1)
#define CT_VIVYQU_MODE_FALLBACK_LOWRANK     (1 << 2)
#define CT_VIVYQU_FLAG_APPLY_SHADOW_ROTORS  (1 << 3)
#define CT_VIVYQU_MODE_GEOMETRIC_E9         (1 << 4)

/* ── Cờ Trạng Thái (Status Flags) ─────────────────────────────────────── */
#define CT_VIVYQU_STATUS_SUCCESS            0
#define CT_VIVYQU_FLAG_IS_DETERMINISTIC     (1 << 0)
#define CT_VIVYQU_FLAG_RENORMALIZED         (1 << 1)
#define CT_VIVYQU_FLAG_FALLBACK_USED        (1 << 2)
#define CT_VIVYQU_FLAG_ZERO_NORM_DETECTED   (1 << 3)
#define CT_VIVYQU_FLAG_GEOMETRIC_E9         (1 << 4)

#pragma pack(push, 1)

/* ── Cấu hình Rotor (8 bytes) ─────────────────────────────────────────── */
typedef struct {
    uint8_t  plane_i;        /* [0..11] */
    uint8_t  plane_j;        /* [0..11] */
    uint16_t reserved_r;     /* 2 bytes căn lề */
    float    angle_theta;    /* Góc quay radian */
} ct_vivyqu_rotor_config_t;

/* ── Điểm số Ứng viên (8 bytes) ───────────────────────────────────────── */
typedef struct {
    uint32_t candidate_idx;  /* [0..4095] */
    float    confidence;     /* Biên độ xác suất */
} ct_vivyqu_candidate_score_t;

/* ── Khung Dữ liệu Đầu vào Cầu Treo -> Vivyqu Core (33.600 bytes) ─────── */
typedef struct {
    /* Header (64 bytes) */
    uint64_t magic_header;
    uint64_t sequence_id;
    uint32_t version;
    uint32_t mode_flags;
    uint64_t timestamp_ns;
    float    temperature;
    uint32_t active_rotors;
    uint8_t  reserved_hdr[24];

    /* Mặt nạ ràng buộc (512 bytes = 4.096 bits) */
    uint8_t  constraint_bitmask[CT_VIVYQU_CONSTRAINT_MASK_BYTES];

    /* Cấu hình Rotor (256 bytes) */
    ct_vivyqu_rotor_config_t rotors[CT_VIVYQU_MAX_ACTIVE_ROTORS];
    uint8_t  reserved_rotors[128];

    /* Vector ngữ cảnh nhận thức (32.768 bytes = 4.096 double) */
    double   latent_vector[CT_VIVYQU_CL12_DIMENSION];
} ct_vivyqu_input_frame_t;

/* ── Khung Dữ liệu Đầu ra Vivyqu Core -> Cầu Treo (256 bytes) ─────────── */
typedef struct {
    /* Header đồng bộ (64 bytes) */
    uint64_t magic_reply;
    uint64_t sequence_id;
    uint32_t error_code;
    uint32_t status_flags;
    uint64_t latency_core_ns;
    uint8_t  reserved_stat[32];

    /* Quyết định cốt lõi (64 bytes) */
    uint32_t best_decision_idx;  /* k* ∈ [0..4095] */
    uint32_t valid_candidates;   /* Số ứng viên hợp lệ */
    double   best_confidence;    /* Xác suất P(k*) */
    double   norm_drift;         /* |‖ψ‖² - 1.0| */
    double   system_entropy;     /* Entropy thông tin */
    uint8_t  reserved_decision[32];

    /* Top-8 ứng viên dự phòng (128 bytes) */
    ct_vivyqu_candidate_score_t top_candidates[8];
    uint8_t  reserved_top[64];
} ct_vivyqu_output_frame_t;

#pragma pack(pop)

/* ── Hành động Cấu trúc Giải mã từ k* ─────────────────────────────────── */
typedef enum {
    CT_ACT_IDLE = 0,               /* 0: Giữ nguyên quan sát */
    CT_ACT_ENGAGE_PRIMARY,         /* 1: Kích hoạt công cụ Mắt/Tay chính */
    CT_ACT_ENGAGE_SECONDARY,       /* 2: Kích hoạt công cụ phụ trợ */
    CT_ACT_PIVOT_STATE,            /* 3: Đổi hướng tiếp cận / rẽ nhánh giả thuyết */
    CT_ACT_RECALIBRATE,            /* 4: Hiệu chuẩn lại tham số rotor */
    CT_ACT_PARTIAL_RELEASE,        /* 5: Cautreo Pager nhả tải bộ nhớ đệm */
    CT_ACT_FULL_RESET,             /* 6: Đặt lại trạng thái an toàn */
    CT_ACT_ADAPTIVE_EXPEDITE       /* 7: Tăng tốc luồng suy luận */
} ct_vivyqu_action_type_t;

typedef struct {
    uint32_t                k_star;
    float                   confidence;
    ct_vivyqu_action_type_t action_type;
    uint8_t                 intensity_tier; /* [0..7] */
    float                   intensity_val;  /* 0.125 - 1.0 */
    uint8_t                 horizon_tier;   /* [0..7] */
    float                   horizon_val;    /* 0.5x - 5.0x */
    uint8_t                 param_tier;     /* [0..7] */
    float                   param_val;      /* 0.5 - 4.0 */
    bool                    is_valid;
} ct_vivyqu_structured_action_t;

/* ── Context Ghép Nối Hợp Nhất (Harmonized Context) ──────────────────── */
typedef struct {
    ct_vivyqu_input_frame_t  in_frame;
    ct_vivyqu_output_frame_t out_frame;
    uint64_t                 step_count;
    uint64_t                 total_latency_ns;
    bool                     is_initialized;
} ct_vivyqu_harmonized_context_t;

/* ── API Cầu Nối C11 ─────────────────────────────────────────────────── */

/* Khởi tạo context ghép nối hợp nhất */
int ct_vivyqu_bridge_init(ct_vivyqu_harmonized_context_t *ctx);

/* Chuyển hóa dữ liệu từ CCE + Score Graph vào Input Frame (Tầng 2 Dual Codec) */
int ct_vivyqu_bridge_encode_context(
    ct_vivyqu_harmonized_context_t *ctx,
    const ct_context_segment       *cce_segments,
    int                             cce_count,
    const ct_score_graph_t         *score_graph,
    uint64_t                        sequence_id
);

/* Áp dụng ràng buộc an toàn từ Score Graph và trạng thái hệ thống vào Bitmask (Tầng 3) */
int ct_vivyqu_bridge_apply_constraints(
    ct_vivyqu_harmonized_context_t *ctx,
    const bool                     *falsified_actions, /* Mảng 4096 bool: true = cấm */
    int                             count
);

/* Giải mã kết quả k* thành lệnh hành động cấu trúc cho Thân thể (Tầng 2 Action Path) */
int ct_vivyqu_bridge_decode_action(
    const ct_vivyqu_output_frame_t *out_frame,
    ct_vivyqu_structured_action_t  *out_action
);

#ifdef __cplusplus
}
#endif

#endif /* CAUTREO_VIVYQU_BRIDGE_H */
