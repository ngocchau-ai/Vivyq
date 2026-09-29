> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# ĐẶC TẢ KÍCH HOẠT SPRINT 5: TÍCH HỢP CẦU TREO & TƯỜNG LỬA WATCHDOG
**Dự Án:** VivyQu — Động cơ Nhận thức Lượng tử & Ra Quyết Định Thời Gian Thực  
**Phiên Bản:** 1.0.1 (Post-Audit Revision)  
**Ngày Kích Hoạt:** 2026-09-27  
**Phạm Vi:** Hiện thực hóa Tường lửa Watchdog Circuit Breaker 3 Cấp Độ & Cầu Treo Dispatcher Runtime  

---

## LỊCH SỬ THAY ĐỔI (AUDIT TRAIL)
| Phiên Bản | Thời Gian (UTC+7) | Người / Agent Thực Hiện | Nội Dung & Lý Do Thay Đổi |
|:---:|:---:|:---:|:---|
| **v1.0.1** | 2026-09-27 18:05 | Antigravity AI Assistant | **Đính chính & Đồng bộ theo Technical Audit (chatGPT_review.md):**<br>1. Chuẩn hóa `HALF_OPEN_PROBE_INTERVAL`: giải quyết mâu thuẫn 3 bên (Spec ghi 100, Report ghi 20, Code `watchdog.py` đặt default 50). Khóa default là 50, cấu hình runtime linh hoạt.<br>2. Chuẩn hóa thuật ngữ "Zero Frame-Drop" thành "Zero Decision-Drop trong fault-injection harness" cho tới khi tích hợp và đo đạc cùng application scheduler thực tế. |
| **v1.0.0** | 2026-09-27 16:35 | Antigravity AI Assistant | Khởi tạo đặc tả Sprint 5 theo VIVY_MASTER_BUILD_PLAN.md và SOP_OPERATIONAL_RUNBOOK.md: thiết kế Tường lửa Watchdog Circuit Breaker 500 µs với 3 cấp độ sự cố, Flight Recorder Telemetry, và bộ điều phối Cầu Treo Actor Dispatcher. |

---

## 1. MỤC TIÊU SPRINT 5

Sau khi hoàn tất Sprint 4 với phán quyết Cổng G2 khóa Nhánh C ($\mathcal{C}\ell(12)$ Clifford Rotors) làm Động cơ Nhận thức Lượng tử cốt lõi ($2.50\ \mu\text{s}$, $32\text{ KiB}$ L1 Cache) và Baseline A2 làm Tầng Cứu Nguy tức thời, Sprint 5 có nhiệm vụ kết nối toàn bộ hệ thống vào thực tế vận hành:

1. **Hiện thực hóa Tường lửa Watchdog Circuit Breaker:**
   - Trực tiếp bảo vệ tiến trình theo quy trình chuẩn [`SOP_OPERATIONAL_RUNBOOK.md`](file:///d:/Vivyqu/docs/SOP_OPERATIONAL_RUNBOOK.md).
   - Kiểm soát ngưỡng timeout cứng $T_{\text{max}} = 500\ \mu\text{s}$.
   - Chuyển mạch trạng thái: `CLOSED` (bình thường qua IPC-P) $\to$ `OPEN` (ngắt mạch sang Baseline A2 fallback) $\to$ `HALF_OPEN` (thăm dò phục hồi).
2. **Xử lý 3 Cấp độ Sự cố Đa tầng (Dual-Tier Incident Triage):**
   - **Cấp 1 (Nhẹ):** Trôi chuẩn $> 10^{-4} \to$ Tái chuẩn hóa tại chỗ ($< 0.1\ \mu\text{s}$).
   - **Cấp 2 (Nghiêm trọng):** Timeout $> 500\ \mu\text{s} \to$ Ngắt mạch tức thì sang Baseline A2, bảo đảm Zero Frame-Drop.
   - **Cấp 3 (Thảm họa):** Daemon bị tiêu diệt / OS crash $\to$ Tự động hạ cấp sang In-Process C-ABI DLL (`vivyqu_core.dll`) và kích hoạt quy trình tái khởi động (respawn).
3. **Bộ đệm Nhật ký Bay Telemetry (Flight Recorder):**
   - Lưu trữ rolling ring buffer 10.000 mẫu độ trễ, sai số chuẩn hóa, tỷ lệ timeout và lỗi vi phạm.
4. **Cầu Treo Actor Dispatcher Runtime:**
   - Tiếp nhận vector ngữ cảnh $h \in \mathbb{R}^{4096}$, tiền xử lý khử NaN/Inf, áp dụng mặt nạ ràng buộc an toàn, và điều phối hành động $k^*$ tới hạ tầng thực thi.

---

## 2. KIẾN TRÚC MÁY TRẠNG THÁI WATCHDOG CIRCUIT BREAKER

```text
               ┌────────────────────────────────────────────────────────┐
               │                                                        │
               ▼                                                        │
         ┌────────────┐               Timeout > 500 µs            ┌───────────┐
   ─────►│   CLOSED   ├──────────────────────────────────────────►│   OPEN    │
         │ (IPC-P SHM)│                                           │(BaselineA)│
         └─────▲──────┘                                           └─────┬─────┘
               │                                                        │
               │                   Thành công                           │ Sau N ticks
               └───────────────── ┌───────────┐ ◄───────────────────────┘
                                  │ HALF_OPEN │
                                  │  (Probe)  │
                                  └─────┬─────┘
                                        │ Timeout tiếp
                                        ▼
                                  (Quay lại OPEN)
```

### Các Tham Số Vận Hành Cốt Lõi:
- **`TIMEOUT_US`:** $500.0\ \mu\text{s}$ (Thời gian tối đa chờ phản hồi phi khóa từ Core Daemon).
- **`MAX_CONSECUTIVE_FAILURES`:** $3$ (Số lần timeout liên tiếp trước khi chuyển từ Cấp 2 lên Cấp 3).
- **`HALF_OPEN_PROBE_INTERVAL`:** $50$ (Mặc định: sau mỗi 50 ticks ở trạng thái OPEN, thực hiện 1 tick thăm dò Core; có thể cấu hình từ 20 đến 100 ticks tùy theo chu kỳ ứng dụng).
- **`FALLBACK_ENGINE`:** Baseline A2 ($W_r (W_l h) + b$) đã đóng băng mã băm SHA-256 trong `results/baseline_a2/`.

---

## 3. TIÊU CHUẨN NGHIỆM THU (ACCEPTANCE CRITERIA)

1. **Zero Decision-Drop (Fault-Tolerant Continuity):** Khi cố tình gây nghẽn hoặc dừng tiến trình Core Daemon trong test harness, Cầu Treo vẫn đưa ra quyết định $k^*$ hợp lệ $100.0\%$ qua Baseline A2 trong thời gian $< 500\ \mu\text{s}$. (Lưu ý: Thuật ngữ Zero Frame-Drop toàn diện sẽ chỉ được chuẩn hóa sau khi tích hợp đo lường cùng game engine / actor scheduler).
2. **Khôi phục Tự động (Auto-Recovery):** Khi Daemon hoạt động trở lại, Circuit Breaker tự động chuyển từ `HALF_OPEN` về `CLOSED`.
3. **Chuyển cấp Thảm họa (Level 3 Fallback):** Khi tiến trình Daemon bị tiêu diệt hoàn toàn (`kill`), hệ thống tự động kích hoạt C-ABI DLL in-process mà không ném ra exception làm sập Cầu Treo.
4. **Bảo toàn Ràng buộc Cứng:** Tỷ lệ thỏa mãn ràng buộc $\mathcal{V} = 100.0\%$ xuyên suốt toàn bộ các trạng thái sự cố.
