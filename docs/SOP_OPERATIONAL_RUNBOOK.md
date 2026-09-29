# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# QUY TRÌNH VẬN HÀNH CHUẨN & SỔ TAY THỰC TIỄN (SOP / RUNBOOK)
## HỆ THỐNG ĐIỀU PHỐI VIVYQU CORE & CẦU TREO RUNTIME

**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Mã tài liệu:** SOP-RUNBOOK-v1.0-Production  
**Ngày ban hành:** 2026-09-27  
**Tác giả kiến trúc:** Ngọc Châu & Antigravity  
**Vai trò:** Hướng dẫn chi tiết quy trình vận hành thực tiễn (Standard Operating Procedure), tiền kiểm hệ thống, thiết lập CPU pinning, giám sát telemetry, ứng phó sự cố đa tầng và bảo trì nóng (hot-swap) cho VivyQu Core và Cầu Treo.

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Ban hành Sổ tay Quy trình Vận hành Thực tiễn v1.0 (SOP/Runbook). Thiết lập 5 quy trình chuẩn: (1) Khởi động & Tiền kiểm phần cứng Pre-flight, (2) Vận hành vòng lặp thời gian thực với CPU Pinning & Cache Warm-up, (3) Giám sát Telemetry & Cảnh báo SLA, (4) Ứng phó sự cố đa tầng (Dual-Tier Incident Triage) với Circuit Breaker 500 μs, (5) Quy trình Hot-Swap tham số và Đồng bộ Audit Trail.

---

## 1. TỔNG QUAN VẬN HÀNH & KIẾN TRÚC TRIỂN KHAI

VivyQu là hệ thống tính toán nhận thức thời gian thực yêu cầu độ trễ cực thấp (Sub-10-Microsecond). Vận hành VivyQu đòi hỏi sự kỷ luật tuyệt đối giữa hai thực thể:
- **Cầu Treo (Body Process):** Tiến trình I/O, điều phối phần cứng, giao tiếp LLM, nạp dữ liệu.
- **VivyQu Core (Soul Process):** Tiến trình tính toán toán học thuần túy trên bộ nhớ đệm CPU L1/L2.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              BẢN ĐỒ VẬN HÀNH TỔNG THỂ                                  │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│ GIAI ĐOẠN                │ HÀNH ĐỘNG CỦA CẦU TREO      │ HÀNH ĐỘNG CỦA VIVYQU CORE     │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 1. Khởi động (Boot)      │ Tạo Shared Memory RingBuffer│ Ánh xạ RAM, Pin CPU, Warm-up  │
│ 2. Vận hành (Real-time)  │ Lọc NaN, Ghi Slot, Kích hoạt│ Tính Clifford/H-Flow, Sụp đổ  │
│ 3. Giám sát (Telemetry)  │ Quét SLA, Đo Norm Drift     │ Xuất số chu kỳ CPU, Entropy   │
│ 4. Sự cố (Incident)      │ Cắt mạch 500 μs, Baseline A │ Tự phục hồi, Re-normalize     │
│ 5. Bảo trì (Hot-Swap)    │ Nạp trọng số vào Slot đệm   │ Chuyển đổi con trỏ tức thì    │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## 2. QUY TRÌNH 1: KHỞI ĐỘNG & TIỀN KIỂM PHẦN CỨNG (PRE-FLIGHT SOP)

Trước khi tiếp nhận bất kỳ tín hiệu nào từ môi trường, người vận hành hoặc script tự động phải thực thi quy trình tiền kiểm 4 bước:

### Bước 1.1: Khởi Tạo Vùng Nhớ Dùng Chung (Shared Memory Initialization)
- **Hành động:** Cầu Treo thực thi cấp phát vùng nhớ dùng chung với tên định danh cố định:
  - Windows: `CreateFileMappingA(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, TOTAL_SHM_SIZE, "Local\\VivyquSharedMemory");`
  - Linux/POSIX: `shm_open("/vivyqu_shm", O_CREAT | O_RDWR, 0666);`
- **Kiểm tra:** Xác nhận kích thước vùng nhớ đúng bằng `8 * sizeof(VivyquSlot)` ($\approx 272\text{ KiB}$). Căn lề địa chỉ con trỏ tại ranh giới 64-byte.

### Bước 1.2: Thiết Lập Ghim Lõi CPU (CPU Affinity & Core Pinning)
- **Hành động:** Nhằm triệt tiêu hiện tượng di chuyển luồng (Thread Migration) và ngắt ngữ cảnh (Context Switching) của hệ điều hành:
  - Ghim tiến trình **VivyQu Core** vào một nhân hiệu năng cao cố định (P-Core, ví dụ: CPU Core 2):
    - Windows: `SetProcessAffinityMask(GetCurrentProcess(), (1 << 2));`
    - Linux: `pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);`
  - Thiết lập mức ưu tiên thời gian thực: `SetPriorityClass(GetCurrentProcess(), REALTIME_PRIORITY_CLASS);`
  - Khóa tần số xung nhịp CPU của Core đó (Disable Intel SpeedStep / AMD Cool'n'Quiet cho Core được chỉ định) để tránh trễ tăng xung nhịp (Frequency Scaling Latency).

### Bước 1.3: Làm Ấm Bộ Nhớ Đệm (Cache Pre-warming)
- **Hành động:** Chạy vòng lặp khởi động gồm **100 chu kỳ giả lập (Dummy Cycles)**:
  - Nạp các vector ngẫu nhiên vào Shared Memory và kích hoạt toán tử Clifford.
  - Mục tiêu: Nạp toàn bộ mã lệnh của Core và dữ liệu bảng Rotor vào L1/L2 Instruction Cache và Data Cache.
  - Nghiệm thu: Chu kỳ thứ 100 phải đạt độ trễ $< 5.0\ \mu\text{s}$.

### Bước 1.4: Bắt Tay An Toàn Không Tin Tưởng (Zero-Trust Handshake)
- Cầu Treo gửi gói tin Handshake: `magic_header = 0x564956595155494E` (`"VIVYQUIN"`).
- Core phản hồi: `magic_reply = 0x5649565951554F55` (`"VIVYQUOU"`), `status_flags |= FLAG_INITIALIZED`.
- Nếu sau 3 giây không nhận được phản hồi Handshake: Cảnh báo `ALERT_CORE_BOOT_FAILED`.

---

## 3. QUY TRÌNH 2: VẬN HÀNH CHU KỲ THỜI GIAN THỰC (REAL-TIME LOOP SOP)

Chu kỳ lặp được thực thi tuần tự theo tần số điều phối (mặc định $60\text{ Hz} - 120\text{ Hz}$ hoặc chế độ nhàn rỗi theo sự kiện):

```text
[BẮT ĐẦU CHU KỲ]
   │
   ▼
1. CẦU TREO: Thu thập hidden state h ∈ ℝ⁴⁰⁹⁶ từ LLM/Cảm biến
   │
   ├─── Quét phần tử: Có NaN hoặc ±Inf? 
   │       ├── CÓ: Kẹp giá trị (Clamp) về [-10.0, 10.0] & Ghi log Warning
   │       └── KHÔNG: Giữ nguyên
   │
   ├─── Chuẩn bị Constraint Mask (512 bytes): Đóng dấu các hành vi cấm
   │
   ├─── Ghi vào Slot trống i = seq % 8 trên Shared Memory
   │
   └─── Atomic Store: slot[i].seq_in.store(seq, memory_order_release)
   │
   ▼
2. VIVYQU CORE: Phát hiện seq_in == seq
   │
   ├─── Đọc vector vào mảng đa bậc Cl(12) Multivector (32 KiB)
   │
   ├─── Chuẩn hóa L2: ψ_A = h_k / ||h||₂
   │
   ├─── Áp dụng M chuỗi Rotor sandwich: ψ' = R ψ R~ (M ≤ 16)
   │
   ├─── Tính toán hạ thế năng dòng moment: T = <ψ ∧ ∇V>₂
   │
   ├─── Đo lường có mặt nạ: k* = argmax_{k ∈ Valid} (ψ_{A(k)})²
   │
   ├─── Kiểm tra trôi chuẩn: |‖ψ'‖² - 1.0| > 10⁻⁴ ?
   │       ├── CÓ: Tái chuẩn hóa tại chỗ ψ_re = ψ' / ||ψ'||
   │       └── KHÔNG: Giữ nguyên
   │
   └─── Atomic Store: slot[i].seq_out.store(seq, memory_order_release)
   │
   ▼
3. CẦU TREO: Thu nhận kết quả
   │
   ├─── Kiểm tra error_code:
   │       ├── != 0: Kích hoạt Kế hoạch Cứu nguy (Fallback Action)
   │       └── == 0: Tiến hành kiểm tra an toàn vật lý khẩn cấp
   │
   └─── Chuyển đổi k* thành lệnh điều phối (Godot / Actor / Robot Dispatcher)
[KẾT THÚC CHU KỲ]
```

---

## 4. QUY TRÌNH 3: GIÁM SÁT ĐO TỪ XA & CẢNH BÁO SLA (TELEMETRY & ALERTING)

Mỗi chu kỳ tính toán, Cầu Treo tự động ghi nhận vào một bộ đệm vòng nhật ký số (Flight Recorder Ring Buffer) với các chỉ số đo lường trọng yếu:

### 4.1. Bảng Chỉ Số SLA và Ngưỡng Kích Hoạt Cảnh Báo

| Chỉ Số Đo Lường | Giá Trị Bình Thường | Ngưỡng Cảnh Báo (WARNING) | Ngưỡng Nguy Cấp (CRITICAL) | Hành Động Phản Ứng |
|---|---|---|---|---|
| **Core Latency ($t_{\text{core}}$)** | $2.0 - 5.0\ \mu\text{s}$ | $> 15.0\ \mu\text{s}$ (trong 5 chu kỳ) | $> 50.0\ \mu\text{s}$ (1 chu kỳ) | Ghi vết CPU cycles, kiểm tra cache miss |
| **End-to-End Latency** | $5.0 - 10.0\ \mu\text{s}$ | $> 25.0\ \mu\text{s}$ | $> 100.0\ \mu\text{s}$ | Kiểm tra nghẽn Shared Memory |
| **Độ Trôi Chuẩn ($\Delta_{\text{norm}}$)**| $< 10^{-6}$ | $> 10^{-5}$ | $> 10^{-4}$ | Lõi tự kích hoạt In-place Renormalization |
| **Tỷ Lệ Lọc Rác NaN/Inf** | $0.0\%$ | $> 0.1\%$ số mẫu | $> 1.0\%$ số mẫu | Cảnh báo LLM upstream bị bất ổn định |
| **Hao Hụt Ứng Viên Hợp Lệ** | $400 - 1200$ | $< 50$ ứng viên | $= 0$ (Không còn ứng viên) | Kích hoạt Safe Relaxing Constraints |

---

## 5. QUY TRÌNH 4: ỨNG PHÓ SỰ CỐ ĐA TẦNG (DUAL-TIER INCIDENT TRIAGE)

Hệ thống tuân thủ nguyên tắc: **"Thế giới không bao giờ được dừng lại (Zero Downtime / Zero Frame-Drop)"**. Mọi sự cố được phân loại và xử lý theo 3 cấp độ:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              HỆ THỐNG XỬ LÝ SỰ CỐ ĐA TẦNG                              │
├───────────────────┬───────────────────────────────┬────────────────────────────────────┤
│ CẤP ĐỘ SỰ CỐ      │ HIỆN TƯỢNG                   │ ĐỐI SÁCH TỰ ĐỘNG                   │
├───────────────────┼───────────────────────────────┼────────────────────────────────────┤
│ Cấp 1 (Nhẹ)       │ Trôi chuẩn số học > 10⁻⁴      │ Tái chuẩn hóa tại chỗ (< 0.1 μs)   │
│ Cấp 2 (Nghiêm trọng) Core Timeout > 500 μs        │ Circuit Breaker ──► Baseline A (W·h│
│ Cấp 3 (Thảm họa)  │ Tiến trình Core bị Crash / OS │ Respawn + Auto-Downgrade sang DLL  │
└───────────────────┴───────────────────────────────┴────────────────────────────────────┘
```

### 5.1. Xử Lý Sự Cố Cấp 1: Trôi Chuẩn Số Học (Arithmetic Norm Drift)
- **Triệu chứng:** `norm_drift > 10^{-4}`.
- **Quy trình:**
  1. Core tự động chuẩn hóa vector về chuẩn 1.0 trước khi tìm argmax.
  2. Core bật cờ `status_flags |= FLAG_RENORMALIZED`.
  3. Cầu Treo ghi log mức `DEBUG` và tiếp tục hoạt động bình thường, không ngắt luồng.

### 5.2. Xử Lý Sự Cố Cấp 2: Timeout Quá Tải (Watchdog Circuit Breaker Trigger)
- **Triệu chứng:** Core không phản hồi sau $T_{\text{max}} = 500\ \mu\text{s}$.
- **Quy trình:**
  1. Cầu Treo ngắt chờ slot, ghi nhận lỗi `ERR_CORE_TIMEOUT`.
  2. **Kích hoạt tức thì Kế hoạch Cứu nguy (Fallback):** Gọi module cổ điển **Baseline A ($W \cdot \mathbf{h}$)** thực thi trong $< 1\ \mu\text{s}$ để xuất ra quyết định $k^*$ an toàn.
  3. Gửi lệnh ngắt mềm (Soft-Interrupt Reset) tới Core để xóa buffer và đưa Core về trạng thái sẵn sàng cho chu kỳ tiếp theo.
  4. Nếu xảy ra 3 lần liên tiếp: Nâng lên Sự cố Cấp 3.

### 5.3. Xử Lý Sự Cố Cấp 3: Tiến Trình Core Bị Đình Trệ Hoặc Crash (Process Failure)
- **Triệu chứng:** Tiến trình VivyQu Core bị hệ điều hành tiêu diệt (OOM/Segfault) hoặc mất kết nối Shared Memory.
- **Quy trình Phục hồi Tự động:**
  1. Cầu Treo ngay lập tức kích hoạt chế độ **Kế hoạch Thứ cấp (Secondary Plan - IPC-S)**: Nạp thư viện liên kết động nội bộ `vivyqu_core.dll` qua C-ABI FFI để tiếp quản tính toán trực tiếp mà không cần IPC.
  2. Gửi lệnh tới hệ thống quản lý tiến trình (`watchdog_supervisor`) để khởi động lại (respawn) tiến trình `vivyqu_core_process.exe`.
  3. Khi tiến trình mới hoàn thành chu trình Pre-flight và Handshake thành công, Cầu Treo tự động chuyển mạch (switch-back) lại Shared Memory một cách êm ái (graceful switchover).

---

## 6. QUY TRÌNH 5: BẢO TRÌ NÓNG & CẬP NHẬT TRỌNG SỐ (HOT-SWAP SOP)

Khi cần cập nhật ma trận thế năng, cấu hình Rotor mới, hoặc nạp trọng số tối ưu từ quá trình huấn luyện NPS mà **không được dừng hệ thống**:

### Bước 6.1: Nạp Dữ Liệu Vào Vùng Nhớ Đệm (Shadow Buffer)
- Cầu Treo ghi cấu hình Rotor mới vào vùng nhớ đệm phụ (Shadow Rotor Buffer) trên Shared Memory.
- Kiểm tra tính hợp lệ toán học: Xác nhận các góc quay $\theta \in [-\pi, \pi]$ và các cặp mặt phẳng $(i, j)$ không bị trùng lặp.

### Bước 6.2: Hoán Đổi Nguyên Tử (Atomic Pointer Swap)
- Cầu Treo gửi gói tin điều khiển với cờ `mode_flags |= FLAG_APPLY_SHADOW_ROTORS`.
- Core thực thi tráo đổi con trỏ cấu hình trong đúng 1 lệnh máy (`atomic_exchange`), không tốn chu kỳ chờ.
- Chu kỳ tiếp theo lập tức vận hành trên bộ tham số mới.

### Bước 6.3: Ghi Nhận Lịch Sử Thay Đổi & Đồng Bộ D:\2brain
- Lưu lại bản chụp trạng thái (Snapshot) gồm: Phiên bản tham số cũ, phiên bản mới, thời điểm hoán đổi, và mức suy giảm Regret ghi nhận được.
- Đồng bộ thông tin cấu hình vào hệ thống tri thức dài hạn `D:\2brain`.

---

## 7. CHECKLIST NGHIỆM THU VẬN HÀNH (OPERATIONAL SIGN-OFF CHECKLIST)

Trước khi bàn giao hệ thống VivyQu Core vào vận hành thực tế, kỹ sư vận hành phải tích đủ 6 tiêu chí:

- [ ] **Tiền kiểm Shared Memory:** Vùng nhớ $272\text{ KiB}$ được cấp phát đúng, không có xung đột quyền truy cập.
- [ ] **Ghim Lõi CPU:** Tiến trình Core đã được ghim chặt vào 1 P-Core cố định, mức ưu tiên `REALTIME`.
- [ ] **Làm ấm Cache:** Đã chạy 100 chu kỳ dummy, độ trễ vi mô ổn định $< 5.0\ \mu\text{s}$.
- [ ] **Tường lửa An toàn:** Module kẹp giá trị NaN/Inf hoạt động chính xác khi nhận vector lỗi.
- [ ] **Cắt mạch Circuit Breaker:** Đã thử nghiệm ngắt Core giả lập và xác nhận Cầu Treo tự động kích hoạt Baseline A thành công trong $< 1\ \mu\text{s}$.
- [ ] **Nhật ký Giám sát:** Hệ thống telemetry ghi nhận đầy đủ p50/p95/p99 và trôi chuẩn.
