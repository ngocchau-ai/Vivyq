#ifndef CAUTREO_INVASION_HOOK_H
#define CAUTREO_INVASION_HOOK_H

/*
 * cautreo_invasion_hook.h — Native In-Process Weight Invasion & Qubit Polarization Hook
 *
 * C11 Header định nghĩa giao thức xâm lấn trọng số tại các layer Transformer của LLM (GGUF).
 * Cho phép Vivyqu Core đọc trạng thái ẩn h_l Zero-Copy, tiêm vector điều hướng hoạt hóa
 * (Activation Steering), ngắt sớm (Early Exit) và khóa từ vựng qua 4 phân cực Qubit.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── 4 Phân Cực Trạng Thái Qubit ──────────────────────────────────────── */
typedef enum {
    POLARIZATION_INERTIA     = 0, /* |00>: Quán tính - Fast-path & Early Exit */
    POLARIZATION_SENSORY     = 1, /* |01>: Tiếp nhận - Nén KV-Cache Phase Shift */
    POLARIZATION_ACTION      = 2, /* |10>: Hành động - Sụp đổ Macro-Action E9 */
    POLARIZATION_SUPERVISION = 3  /* |11>: Giám sát - Watchdog Circuit Breaker */
} qubit_polarization_t;

/* ── Ngưỡng An Toàn & Hằng Số Kỹ Thuật ─────────────────────────────────── */
#define CAUTREO_INVASION_MAX_STEERING_SCALE 0.10f /* ||Δh|| <= 10% ||h|| */
#define CAUTREO_INVASION_DEFAULT_LAYER_RATIO 0.50f /* target_layer = total / 2 */

/* ── Ngữ Cảnh Xâm Lấn Trọng Số (Invasion Context) ───────────────────────── */
typedef struct {
    uint32_t             current_layer;        /* Layer hiện tại đang thực thi */
    uint32_t             total_layers;         /* Tổng số layer của mô hình (ví dụ 32) */
    float                confidence_score;     /* Độ tự tin hội tụ [0.0 .. 1.0] */
    qubit_polarization_t polarization;         /* Phân cực qubit do Vivyqu xác định */
    
    /* Con trỏ trực tiếp tới hidden state tensor tại layer hiện tại */
    float               *hidden_state_ptr;     
    uint32_t             hidden_dim;           /* Chiều ẩn (mặc định 4096) */

    /* Vector điều hướng hoạt hóa (Activation Steering) */
    const float         *steering_delta_ptr;   /* Vector Δh (4096D) */
    float                steering_scale;       /* Hệ số scale, tự kẹp <= 0.10 */

    /* Cờ điều khiển luồng thực thi trong Engine */
    bool                 early_exit_triggered; /* true = ngắt forward pass ngay */
    uint32_t             macro_action_id;      /* Action k* sụp đổ nếu ở |10> */
    int32_t              status_code;          /* 0 = OK, < 0 = Lỗi */
} cautreo_invasion_context_t;

/* ── Con Trỏ Hàm Callback Hook Sau Mỗi Layer ───────────────────────────── */
typedef bool (*cautreo_layer_hook_fn)(cautreo_invasion_context_t *ctx, void *user_data);

/* ── Các Hàm Tiện Ích C-ABI Cốt Lõi ────────────────────────────────────── */

/* Khởi tạo ngữ cảnh xâm lấn với các giá trị mặc định an toàn */
static inline cautreo_invasion_context_t cautreo_init_invasion_context(
    uint32_t current_layer,
    uint32_t total_layers,
    float   *hidden_state_ptr,
    uint32_t hidden_dim
) {
    cautreo_invasion_context_t ctx;
    ctx.current_layer = current_layer;
    ctx.total_layers = total_layers;
    ctx.confidence_score = 0.0f;
    ctx.polarization = POLARIZATION_INERTIA;
    ctx.hidden_state_ptr = hidden_state_ptr;
    ctx.hidden_dim = hidden_dim;
    ctx.steering_delta_ptr = NULL;
    ctx.steering_scale = 0.0f;
    ctx.early_exit_triggered = false;
    ctx.macro_action_id = 0;
    ctx.status_code = 0;
    return ctx;
}

/* Áp dụng vector điều hướng hoạt hóa (In-place Activation Steering) an toàn */
static inline bool cautreo_apply_steering(cautreo_invasion_context_t *ctx) {
    if (!ctx || !ctx->hidden_state_ptr || !ctx->steering_delta_ptr) {
        return false;
    }
    float scale = ctx->steering_scale;
    if (scale > CAUTREO_INVASION_MAX_STEERING_SCALE) {
        scale = CAUTREO_INVASION_MAX_STEERING_SCALE; /* Watchdog Clamping */
    }
    if (scale <= 0.0f) {
        return true; /* Không cần tiêm */
    }
    for (uint32_t i = 0; i < ctx->hidden_dim; ++i) {
        ctx->hidden_state_ptr[i] += scale * ctx->steering_delta_ptr[i];
    }
    return true;
}

#ifdef __cplusplus
}
#endif

#endif /* CAUTREO_INVASION_HOOK_H */
