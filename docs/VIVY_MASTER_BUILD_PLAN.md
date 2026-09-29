# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# KẾ HOẠCH XÂY DỰNG TỔNG THỂ HỆ THỐNG VIVY / VIVYQU (MASTER BUILD PLAN)
## (HỒ SƠ THẨM ĐỊNH TỰ ĐỘNG QUA BỘ LỌC AUTOPLAN: CEO — DESIGN — ENG — DX)

**Dự án:** Vivy & Vivyqu (Quantum-Inspired Cognitive World Director)  
**Phiên bản kế hoạch:** v1.0-Autoplan-Approved  
**Ngày lập:** 2026-09-27  
**Nhà sáng lập:** Ngọc Châu  
**Đơn vị thẩm định:** Antigravity (Hệ thống Trợ lý Toàn thời gian Ngọc Châu — Powered by gstack autoplan)  
**Trạng thái kế hoạch:** Sẵn sàng thực thi (Ready for Implementation)

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Khởi tạo Kế hoạch Xây dựng Tổng thể Vivy/VivyQu (Master Build Plan) thông qua chu trình thẩm định `/autoplan`. Tích hợp đầy đủ: (1) CEO Review & Khảo sát Tiền đề, (2) Thiết kế Nhận thức & Trải nghiệm Điều phối, (3) Kiến trúc Kỹ thuật & Sơ đồ Phụ thuộc Module C++, (4) Trải nghiệm Nhà phát triển DX & C-ABI, (5) Lộ trình 6 Sprint thực chiến và Ma trận Xử lý Rủi ro.

---

## 1. TỔNG QUAN CHIẾN LƯỢC & ĐỊNH HƯỚNG SẢN PHẨM (CEO REVIEW)

### 1.1. Tuyên Bố Sứ Mệnh & Wedge Hẹp Nhất (The Narrowest Wedge)
* **Vấn đề Cốt lõi (The Core Pain):** Các mô hình ngôn ngữ lớn (LLM) hiện nay bị kẹt trong "Bức tường Bộ nhớ" (Memory Wall) và độ trễ sinh từ tuần tự quá chậm ($50 - 500\text{ ms}$ cho mỗi token), hoàn toàn bất lực khi cần đóng vai trò **Bộ Não Điều Khiển Thời Gian Thực (Real-Time Cognitive Brain)** cho các thế giới tự hành, game engine hoặc robot vật lý.
* **Wedge Hẹp Nhất (Narrowest Wedge):** Thay vì cố gắng sinh văn bản tự hồi quy, VivyQu bắt giữ **vector ngữ cảnh 4.096 chiều duy nhất** từ LLM/Vision và nạp thẳng vào **Lõi Nhận thức Hình học Clifford $\mathcal{C}\ell(12)$ (32 KiB)**. Hệ thống sụp đổ tức thì sang một quyết định tham số tối ưu trong **dưới 10 micro-giây ($< 10\ \mu\text{s}$)**.
* **Sản Phẩm Đầu Ra:** **Vivy World Director** — Bộ điều phối thế giới tham số tự hành (Parametric Spatial & Action Dispatcher).

### 1.2. Thẩm Định Tiền Đề Chiến Lược (Premise Challenge Gate)

| Tiền đề Khảo sát | Đánh giá Tính Hợp lý | Rủi ro nếu Sai | Đối sách Chiến lược |
|---|---|---|---|
| **P1: Chiều 4.096 tương thích tự nhiên với $\mathcal{C}\ell(12)$** | **Hợp lý tuyệt đối:** $\sum_{k=0}^{12} \binom{12}{k} = 2^{12} = 4096$. Đẳng cấu 1-1 không cần padding. | Sai số chiều | Đã có Kế hoạch Thứ cấp Hilbert $\mathcal{H}_{12}$ và Real-Norm. |
| **P2: Bộ nhớ 32 KiB nằm trọn L1 Data Cache** | **Hợp lý:** $4096 \times 8\text{ bytes} = 32\text{ KiB}$, các chip Intel/AMD hiện đại có L1-D $\ge 32 - 48\text{ KiB}$. | Trượt cache | Tối ưu hóa căn lề 64-byte Cacheline Alignment. |
| **P3: Latency Core $< 10\ \mu\text{s}$ là khả thi trên CPU** | **Hợp lý:** Phân tích nhân tử $M \le 16$ rotor Givens chỉ tốn $\sim 6.5 \times 10^4$ FLOPs ($< 4\ \mu\text{s}$ trên 3.5 GHz). | CPU bị bận ngắt | Đã có quy trình SOP Core Pinning ghim CPU thời gian thực. |
| **P4: Cần nhiều hơn 1 giải pháp toán học** | **Đúng đắn tối cao:** Tránh bẫy độc đạo (Single Point of Failure). | Dự án đình trệ | Đã khóa 3 tầng: Primary, Secondary, Fallback cho toàn bộ module. |

### 1.3. Bản Đồ Hiện Trạng & Trạng Thái Mơ Ước (Dream State Delta)

```text
┌───────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│     HIỆN TRẠNG        │      │    KẾ HOẠCH NÀY        │      │     12 THÁNG TỚI       │
│  (THÁNG 09/2026)      │ ───► │  (SPRINT 1 - 6)        │ ───► │   (LÝ TƯỞNG 2027)      │
├───────────────────────┤      ├────────────────────────┤      ├────────────────────────┤
│ • Lý thuyết & Spec    │      │ • Hoàn thành E0 & E1   │      │ • Vivy World Director  │
│ • Ranh giới Soul-Body │      │ • Khóa C-ABI & DLL     │      │   điều phối game 3D    │
│ • Chưa có code C++    │      │ • Lõi Cl(12) < 5 μs    │      │ • Tích hợp Robot thật  │
│ • Chưa có Benchmark   │      │ • Đóng băng Baseline A │      │ • Hardware ASIC/FPGA   │
└───────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

---

## 2. THIẾT KẾ TRẢI NGHIỆM ĐIỀU PHỐI & NHẬN THỨC (SYSTEM & DESIGN REVIEW)

### 2.1. Phân Cấp Kiến Trúc 3 Tầng Nhận Thức

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 1: THẾ NĂNG & NGỮ NGHĨA] — VIVY NPS HYPOTHESIS POPULATION                        │
│ • Quần thể giả thuyết ngữ nghĩa (Claim, Evidence, Verification Plan)                   │
│ • Điều phối bất định Epistemic Gate & Router                                           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ 1 Context Vector h ∈ ℝ⁴⁰⁹⁶
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 2: LÕI NHẬN THỨC SIÊU TỐC] — VIVYQU CORE (CPU L1/L2 CACHE)                       │
│ • Multivector Clifford Cl(12) (32 KiB)                                                 │
│ • Factorized Spin(12) Givens Rotors + Hamiltonian Torque Flow                          │
│ • Sụp đổ hàm sóng xác định Hard-Masked Argmax (< 5 μs)                                 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Decision k* (256 bytes Output Frame)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TẦNG 3: THÂN THỂ THỰC THI] — CẦU TREO (CAUTREO DISPATCHER & ACTUATORS)                │
│ • Godot Engine Actor Controller / 3D Parametric Mesh Generator                         │
│ • Watchdog Circuit Breaker (500 μs Timeout) & Incident Safety Guard                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Ma Trận Đăng Ký Lỗi & Giải Cứu (Error & Rescue Registry)

| Mã Lỗi Hệ Thống | Nguyên Nhân Gốc Rễ | Tác Động Tới Hệ Thống | Cơ Chế Giải Cứu Tự Động (Rescue Strategy) |
|---|---|---|---|
| `ERR_INPUT_NAN_INF` | Vector từ LLM có số không hợp lệ | Phá vỡ tính toán số học | Cầu Treo kẹp giá trị (Clamp) về $[-10.0, 10.0]$ |
| `ERR_ZERO_NORM` | Vector đầu vào toàn số 0 | Không chuẩn hóa được | Nạp vector Neutral Unit State mặc định |
| `ERR_NORM_DRIFT` | Tích lũy sai số sau chuỗi Rotor | Trôi chuẩn độ lớn $|\Delta| > 10^{-4}$ | Lõi Core tự kích hoạt In-place Renormalization |
| `ERR_CORE_TIMEOUT` | Core bị nghẽn CPU $> 500\ \mu\text{s}$ | Nguy cơ rớt khung hình | **Circuit Breaker bật ngay Baseline A ($W \cdot \mathbf{h}$)** |
| `ERR_ALL_CONSTRAINTS`| Mọi ứng viên đều vi phạm | Không có phương án hợp lệ | Kích hoạt Safe Relaxing Constraints của Cầu Treo |

---

## 3. KIẾN TRÚC KỸ THUẬT & PHÂN RÃ MODULE (ENG REVIEW)

### 3.1. Sơ Đồ Phụ Thuộc Module (ASCII Component Dependency Graph)

```text
[Hardware Platform: x86_64 AVX-512 / AVX2 / ARM NEON]
  │
  ├──► [Module 1: Memory & Buffer Subsystem]
  │      ├── shm_ring_buffer.h (SPSC Lock-Free 8-slot, 64-byte aligned)
  │      └── memory_pool.h (Pre-allocated static 32 KiB frames)
  │
  ├──► [Module 2: Mathematical Core Engine (Pure C++20)]
  │      ├── clifford_cl12.h (Multivector 4096D, blade bit-indexing)
  │      ├── rotor_spin12.h (Factorized Givens bivector rotations)
  │      ├── hamiltonian_flow.h (Bivector torque descent)
  │      └── measurement_collapse.h (Hard-masked argmax SIMD)
  │
  ├──► [Module 3: Dual-Tier Fallback Subsystem]
  │      ├── hilbert_complex12.h (Secondary Plan: 64/32 KiB complex state)
  │      ├── fwht_transform.h (Fast Walsh-Hadamard Transform O(d log d))
  │      └── baseline_linear.h (Fallback: W·h low-rank scorer)
  │
  └──► [Module 4: C-ABI & Export Bindings]
         ├── vivyqu_core_api.h (cdecl export: vivyqu_step, vivyqu_reset)
         └── python/vivyqu_cffi.py (Zero-overhead ctypes/cffi wrapper)
```

### 3.2. Sơ Đồ Luồng Kiểm Thử Toàn Diện (Test Diagram & Verification Matrix)

```text
[Luồng Kiểm Thử]
  │
  ├──► [Unit Tests: Toán học thuần khiết]
  │      ├── test_blade_indexing: Kiểm tra 4096 tổ hợp nhị phân không trùng lặp
  │      ├── test_rotor_norm_conservation: Xoay 1.000 góc ngẫu nhiên, kiểm tra |norm - 1.0| < 1e-6
  │      └── test_sandwich_product: So sánh kết quả R ψ R~ với ma trận trực giao tương đương
  │
  ├──► [Performance Harness: Độ trễ vi mô]
  │      ├── bench_warm_cache: 100.000 chu kỳ liên tục, đo p50/p90/p95/p99 (Target: p99 < 5 μs)
  │      ├── bench_cold_cache: Flush cache trước mỗi lượt gọi, đo worst-case latency
  │      └── bench_cache_misses: Sử dụng perf hardware counters đo L1-D Misses (< 2.0%)
  │
  └──► [Integration & Stress Tests: Thân thể - Linh hồn]
         ├── test_shm_ring_buffer_concurrency: Chạy Cầu Treo & Core trên 2 thread kịch trần
         ├── test_watchdog_circuit_breaker: Chèn sleep 1ms vào Core, xác nhận Cầu Treo fallback A
         └── test_nan_resilience: Nạp 10.000 vector chứa NaN/Inf, xác nhận hệ thống không crash
```

---

## 4. TRẢI NGHIỆM NHÀ PHÁT TRIỂN & TÍCH HỢP (DX REVIEW)

### 4.1. Bản Đồ Hành Trình Nhà Phát Triển (Developer Journey Map)

| Giai Đoạn | Mục Tiêu của Developer | Thách Thức / Điểm Nghẽn | Giải Pháp Thiết Kế của VivyQu |
|---|---|---|---|
| **1. Khám phá (Discover)** | Hiểu VivyQu làm được gì | Khái niệm lượng tử phức tạp | Đóng gói thành: "Hộp đen ra quyết định 4096D trong $< 10\ \mu\text{s}$" |
| **2. Tích hợp (Integrate)**| Gọi Core từ Python / Godot | Cài đặt thư viện C++ nặng nề | Cung cấp sẵn file `vivyqu_core.dll` và file Python wrapper 1-file duy nhất |
| **3. Cấu hình (Configure)**| Định nghĩa bài toán & mục tiêu | Viết ma trận thế năng khó khăn | DSL thế năng trực quan: `add_constraint()`, `set_alignment_target()` |
| **4. Gỡ lỗi (Debug)** | Tìm nguyên nhân quyết định sai | Khó theo dõi trạng thái hàm sóng | File Output Frame chứa sẵn `entropy`, `norm_drift`, `top_candidates` |
| **5. Triển khai (Deploy)** | Đưa vào sản xuất ổn định | Xung đột luồng và rớt khung hình| Sổ tay [`SOP_OPERATIONAL_RUNBOOK.md`](file:///d:/Vivyqu/docs/SOP_OPERATIONAL_RUNBOOK.md) kèm CPU Pinning script |

### 4.2. Thời Gian Đạt "Hello World" (Time-to-Hello-World: Target < 3 Phút)
Một kỹ sư mới chỉ cần 3 dòng code Python để tích hợp VivyQu:
```python
import numpy as np
from vivyqu import VivyquEngine

# 1. Khởi tạo Engine (Tự động nạp DLL và ánh xạ Shared Memory)
engine = VivyquEngine(mode="primary_cl12")

# 2. Tạo vector ngữ cảnh giả lập từ LLM (4096 chiều)
latent_h = np.random.randn(4096).astype(np.float64)

# 3. Ra quyết định tức thì
result = engine.step(latent_vector=latent_h)
print(f"Optimal Action Index: {result.best_idx}, Latency: {result.latency_us:.2f} µs")
```

---

## 5. LỘ TRÌNH THỰC THI 6 SPRINT (6-SPRINT IMPLEMENTATION ROADMAP)

```text
Tuần 1-2: [Sprint 1: Nền tảng Toán C++ & Harness] ──► LibClifford Core + Microbench
Tuần 3-4: [Sprint 2: Thực nghiệm E0 & Freeze A2]   ──► Sinh 10.000 mẫu + Khóa SHA-256
Tuần 5-6: [Sprint 3: Lock-Free Shared Memory IPC] ──► Ring Buffer SPSC + C-ABI DLL
Tuần 7-8: [Sprint 4: Nhánh B/C vs. Golden Baseline] ──► Quyết đấu E9 (Regret & Latency)
Tuần 9-10:[Sprint 5: Tích hợp Cầu Treo & Watchdog]──► Circuit Breaker + Godot/Actor
Tuần 11-12:[Sprint 6: Đóng gói Sản phẩm & Release] ──► SDK v1.0 + Báo cáo nghiệm thu
```

### Chi Tiết Từng Sprint:

* **Sprint 1 (Tuần 1–2): Nền Tảng Toán C++ & Microbench Harness**
  * *Nhiệm vụ:* Hiện thực hóa cấu trúc Multivector $\mathcal{C}\ell(12)$ (32 KiB) và thuật toán quay nhân tử Rotor Givens bằng C++20 có cờ tối ưu `-O3 -march=native`.
  * *Đầu ra:* Thư viện tĩnh `libvivyqu_math.a` và benchmark đạt p99 $< 5.0\ \mu\text{s}$.
* **Sprint 2 (Tuần 3–4): Thực Nghiệm E0 & Đóng Băng Golden Baseline A**
  * *Nhiệm vụ:* Sinh tập dữ liệu chuẩn 10.000 mẫu theo [`EXPERIMENT_E0_BENCHMARK_SPEC.md`](file:///d:/Vivyqu/docs/EXPERIMENT_E0_BENCHMARK_SPEC.md). Huấn luyện Baseline A2.
  * *Đầu ra:* File checksum SHA-256 đóng băng vĩnh viễn Baseline A2 với Regret $\le 12.0\%$.
* **Sprint 3 (Tuần 5–6): Tầng Giao Tiếp IPC & C-ABI FFI**
  * *Nhiệm vụ:* Hiện thực hóa Shared Memory Ring Buffer và C-ABI DLL theo [`CAUTREO_CORE_INTERFACE_SPEC.md`](file:///d:/Vivyqu/docs/CAUTREO_CORE_INTERFACE_SPEC.md).
  * *Đầu ra:* `vivyqu_core.dll` chạy mượt mà qua Python wrapper với transport latency $< 0.3\ \mu\text{s}$.
* **Sprint 4 (Tuần 7–8): Quyết Đấu Năm Nhánh (Grand Prix E9)**
  * *Nhiệm vụ:* Chạy đối đầu trực tiếp Nhánh A, Nhánh B (Statevector), Nhánh C ($\mathcal{C}\ell(12)$).
  * *Đầu ra:* Báo cáo kết quả kiểm định. Nếu C thắng A $\to$ Khóa $\mathcal{C}\ell(12)$ làm động cơ sản phẩm. Nếu A thắng $\to$ Chuyển trục sang Baseline A + NPS Lifecycle.
* **Sprint 5 (Tuần 9–10): Tích Hợp Cầu Treo & Tường Lửa Watchdog**
  * *Nhiệm vụ:* Triển khai các quy trình trong [`SOP_OPERATIONAL_RUNBOOK.md`](file:///d:/Vivyqu/docs/SOP_OPERATIONAL_RUNBOOK.md). Kiểm thử ngắt mạch Circuit Breaker $500\ \mu\text{s}$ và kết nối Actor Dispatcher.
  * *Đầu ra:* Hệ thống chạy ổn định 24/7 với zero frame-drop.
* **Sprint 6 (Tuần 11–12): Nghiệm Thu, Đóng Gói SDK & Release**
  * *Nhiệm vụ:* Đóng gói `vivyqu` Python package, hoàn thiện tài liệu hướng dẫn và đồng bộ toàn bộ tri thức vào `D:\2brain`.
  * *Đầu ra:* Bản phát hành **VivyQu Engine v1.0**.

---

## 6. NHẬT KÝ THẨM ĐỊNH TỰ ĐỘNG (AUTONOMOUS DECISION LOG)

Dưới đây là bảng ghi nhận toàn bộ các quyết định tự động được thực hiện trong quá trình duyệt kế hoạch theo **6 Nguyên Tắc Quyết Định (The 6 Decision Principles)** của autoplan:

| # | Giai Đoạn | Quyết Định Thiết Kế | Phân Loại | Nguyên Tắc Áp Dụng | Lý Do Chọn Lựa | Phương Án Bị Bác Bỏ |
|---|---|---|---|---|---|---|
| **1** | **CEO** | Chọn bài toán Không gian Tham số 4096D làm đích đầu tiên | Cơ chế (Mechanical) | P1 (Completeness) | Phù hợp 100% với kiến trúc 12-qubit rời rạc | Bỏ qua bài toán tìm kiếm văn bản tự do |
| **2** | **CEO** | Chọn Chiến lược Đa giải pháp (3 tầng P/S/F) | Thẩm mỹ (Taste) | P6 (Action / Resilience) | Triệt tiêu rủi ro chết đứng khi 1 thuật toán fail | Chỉ dựa vào 1 giải pháp độc đạo duy nhất |
| **3** | **Design** | Cố định kích thước Input 32.8 KiB & Output 256 bytes | Cơ chế (Mechanical) | P5 (Explicit) | Căn lề 64-byte Cacheline, zero false sharing | Định dạng JSON động hoặc gRPC cồng kềnh |
| **4** | **Eng** | Phân tích Rotor Givens $M \le 16$ thay vì ma trận dày | Cơ chế (Mechanical) | P3 (Pragmatic) | Chi phí $6.5 \times 10^4$ FLOPs ($< 4\ \mu\text{s}$ CPU) | Ma trận dày $4096^2$ ngốn 256 MB RAM |
| **5** | **Eng** | Kích hoạt Circuit Breaker $500\ \mu\text{s}$ fallback Baseline A | Thẩm mỹ (Taste) | P1 (Completeness) | Bảo đảm hệ thống không bao giờ bị nghẽn hình | Để luồng bị crash hoặc đứng im vô hạn |
| **6** | **DX** | Cung cấp song song Shared Memory IPC và C-ABI DLL | Thẩm mỹ (Taste) | P2 (Boil Lakes) | Cho phép vừa chạy microbench vừa chạy microservices | Chỉ ép buộc duy nhất 1 giao thức IPC |

---

## 7. CỔNG DUYỆT TỔNG THỂ (FINAL APPROVAL GATE)

### Tóm Tắt Trạng Thái Kế Hoạch:
* **CEO Strategy Score:** 9.5/10 — Xác định rõ bài toán, wedge hẹp nhất, và lộ trình 12 tháng.
* **Design/Architecture Score:** 9.8/10 — Căn lề Cacheline hoàn hảo, sơ đồ 3 tầng rõ ràng.
* **Engineering Rigor Score:** 9.5/10 — Phân tích nhân tử $O(M \cdot d)$, ma trận kiểm thử và xử lý lỗi đầy đủ.
* **Developer Experience Score:** 9.0/10 — Time-to-Hello-World $< 3$ phút, API chuẩn Python/C++.

### Lựa Chọn Quyết Định (Taste Decisions Cần Xác Nhận):
1. **Lựa chọn 1:** Cố định ngôn ngữ lõi là **C++20** (tối ưu SIMD cao nhất) thay vì Rust. (Khuyến nghị: C++20 vì tích hợp trực tiếp AVX-512 và OpenMP không qua lớp trung gian).
2. **Lựa chọn 2:** Kích hoạt ngay kịch bản **Sprint 1 (C++ Math Core)** trong phiên tiếp theo.

> Kế hoạch Xây dựng Tổng thể Vivy/VivyQu này đã sẵn sàng để chuyển giao và khởi động lập trình!
