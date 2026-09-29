# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# HỢP ĐỒNG GIAO TIẾP & ĐẶC TẢ ABI / IPC: CẦU TREO (BODY) ↔ VIVYQU CORE (SOUL)

**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Phiên bản:** v1.0-Locked  
**Ngày ban hành:** 2026-09-27  
**Tác giả kiến trúc:** Ngọc Châu & Antigravity  
**Vai trò:** Khóa dứt khoát ranh giới kỹ thuật, cấu trúc nhị phân (Binary Layout), giao thức đồng bộ phi khóa (Lock-free Shared Memory), và cơ chế an toàn theo tiêu chuẩn đa giải pháp (Dual-Tier Architecture).

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Ban hành bản đặc tả chính thức đầu tiên (v1.0-Locked) về hợp đồng giao tiếp giữa Cầu Treo và VivyQu Core. Khóa 3 tầng giải pháp: (1) Cơ chế truyền thông Lock-Free Shared Memory Ring Buffer vs. In-Process C-ABI FFI vs. Named Pipes, (2) Cấu trúc Binary Memory Layout chuẩn căn lề 64-byte cho 32 KiB Multivector và 64 KiB Statevector, (3) Ranh giới an toàn, Watchdog Circuit Breaker và thẩm quyền xử lý quyết định.

---

## 1. NGUYÊN TẮC CỐT LÕI VÀ TRIẾT LÝ GIAO TIẾP

Để đảm bảo hiệu năng ra quyết định dưới 10 micro-giây ($< 10\ \mu\text{s}$) và bảo vệ tính thuần khiết của Lõi nhận thức, hợp đồng tuân thủ 4 nguyên tắc bất biến:

1. **Nguyên Tắc Bóc Tách Bản Thể (Soul-Body Decoupling):**
   - **VivyQu Core (Linh hồn):** Thuần khiết tính toán toán học trên CPU/Cache. Tuyệt đối không chứa mã I/O, không gọi hàm hệ điều hành (syscalls), không đọc/ghi đĩa, không socket mạng.
   - **Cầu Treo (Thân thể):** Chịu trách nhiệm quản lý I/O, thu nhận tín hiệu từ môi trường, chuẩn hóa vector, điều phối bộ nhớ chia sẻ, và chuyển đổi kết quả tính toán thành hành động thực tế.
2. **Không Khóa & Không Chờ Lãng Phí (Lock-Free & Zero-Copy):**
   - Giao tiếp dữ liệu diễn ra hoàn toàn trên bộ nhớ chia sẻ được ánh xạ trước (pre-mapped memory). Cầu Treo và Core trao đổi qua các thanh ghi nguyên tử (Atomic Sequence Flags), loại bỏ hoàn toàn chi phí context switch của OS mutex/lock.
3. **Thiết Kế Đa Lớp (Dual-Tier Strategy):**
   - Luôn luôn trang bị: **Kế hoạch Chính (Primary - P)**, **Kế hoạch Thứ cấp (Secondary - S)** và **Kế hoạch Cứu nguy (Fallback - F)** cho từng thành phần giao tiếp.
4. **Tường Lửa Thẩm Quyền Minh Bạch (Authority Firewall):**
   - Core có thẩm quyền tuyệt đối trong việc chấm điểm năng lượng và sụp đổ trạng thái ra chỉ số $k^*$.
   - Cầu Treo có quyền **Từ chối thực thi (Refusal)** khi vi phạm hợp đồng an toàn, nhưng tuyệt đối không được âm thầm sửa điểm hay hoán đổi quyết định của Core.

---

## 2. TẦNG 1: CƠ CHẾ TRUYỀN THÔNG LIÊN TIẾN TRÌNH (IPC TRANSPORT)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [CẦU TREO - PRODUCER]                                                                  │
│  1. Thu thập latent h ∈ ℝ⁴⁰⁹⁶ từ LLM/Vision                                            │
│  2. Ghi trực tiếp vào Slot trống trên Shared Memory                                    │
│  3. Atomic Store (Sequence = N, memory_order_release)                                   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Lock-Free Ring Buffer (Cacheline Aligned)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [VIVYQU CORE - CONSUMER / SOLVER]                                                      │
│  1. Spin-wait nhẹ (≤ 500 cycles) / WaitOnAddress kiểm tra Sequence == N                │
│  2. Atomic Load (memory_order_acquire)                                                 │
│  3. Xử lý Toán tử Clifford / Multivector Cl(12) (< 5 μs)                               │
│  4. Ghi kết quả vào Output Frame                                                       │
│  5. Atomic Store (Core_Sequence = N, memory_order_release)                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1. Kế Hoạch Chính (IPC-P): Lock-Free Shared Memory Ring Buffer với Atomic Sequence
- **Cơ chế:** Vùng nhớ chia sẻ (Shared Memory Segment qua `CreateFileMapping` / `MapViewOfFile` trên Windows hoặc `shm_open` trên POSIX).
- **Cấu trúc hàng đợi:** Single-Producer Single-Consumer (SPSC) Circular Ring Buffer gồm $N_{\text{slots}} = 8$ slots (đủ để đệm các xung nhịp spike mà không bị tràn).
- **Đồng bộ phi khóa:**
  - Mỗi slot có một trường `sequence_id` kiểu `std::atomic<uint64_t>`.
  - Phía Cầu Treo (Writer): ghi payload vào slot $i = \text{seq} \pmod{N}$, sau đó phát lệnh:
    `slot[i].seq_in.store(seq, std::memory_order_release);`
  - Phía Core (Reader): thực hiện spin-wait ngắn ($\le 500$ vòng CPU `PAUSE`), nếu sau đó chưa có dữ liệu thì chuyển sang chế độ ngủ nhẹ qua Windows API `WaitOnAddress(&slot[i].seq_in, ...)` hoặc Linux `futex`. Khi có tín hiệu:
    `uint64_t s = slot[i].seq_in.load(std::memory_order_acquire);`
- **Độ trễ vận chuyển (Transport Latency):** **$< 0.3\ \mu\text{s}$** (gần như tức thời vì chỉ đọc/ghi trên RAM chia sẻ đã warm cache).

### 2.2. Kế Hoạch Thứ Cấp (IPC-S): Direct In-Process C-ABI FFI (Thư Viện Động DLL)
- **Cơ chế:** Đóng gói VivyQu Core thành một thư viện liên kết động (`vivyqu_core.dll` trên Windows hoặc `libvivyqu_core.so` trên Linux) xuất ra hàm C thuần túy:
  ```c
  int32_t vivyqu_core_step(const VivyquInputFrame* in, VivyquOutputFrame* out);
  ```
- **Lợi thế:** Loại bỏ hoàn toàn tầng IPC giữa các tiến trình. Độ trễ giao tiếp là **$0\ \mu\text{s}$** (chỉ tốn chi phí gọi hàm cdecl thông thường $\approx 5\text{ ns}$).
- **Điều kiện kích hoạt IPC-S:** Khi VivyQu Core và Cầu Treo được triển khai tích hợp trong cùng một tiến trình host (Python `ctypes`/`cffi`, C++, Rust), không cần phân tách crash domain giữa hai tiến trình.

### 2.3. Kế Hoạch Cứu Nguy (IPC-F): Local Named Pipes / Unix Domain Sockets
- **Cơ chế:** Giao tiếp qua Windows Named Pipe (`\\.\pipe\vivyqu_ipc`) hoặc Unix Domain Socket (`AF_UNIX`).
- **Lợi thế:** Hoạt động ổn định trong mọi môi trường sandbox khắt khe (khi quyền Shared Memory bị hệ điều hành chặn).
- **Điều kiện kích hoạt IPC-F:** Khi môi trường runtime không cho phép cấp phát Shared Memory hoặc khi cần phân tích/debug mạng nội bộ.

---

## 3. TẦNG 2: CẤU TRÚC NHỊ PHÂN VÀ BỐ TRÍ BỘ NHỚ (BINARY MEMORY LAYOUT & ABI)

Mọi cấu trúc dữ liệu bắt buộc phải được **căn lề 64-byte (`alignas(64)`)** để tương thích hoàn hảo với kích thước một đường nhớ đệm (Cacheline) của CPU, triệt tiêu hoàn toàn hiện tượng suy hao hiệu năng do **False Sharing**.

### 3.1. Cấu Trúc Khung Đầu Vào (Input Frame ABI — 32 KiB Layout)

Dành cho Kế hoạch Toán học P1/P2 ($\mathcal{C}\ell(12)$ Multivector):

```c
// Căn lề 64-byte theo chuẩn Cacheline
#pragma pack(push, 1)

typedef struct alignas(64) {
    // --- KHỐI ĐIỀU KHIỂN & ĐỒNG BỘ (HEADER: 64 BYTES) ---
    uint64_t magic_header;       // 0x564956595155494E ("VIVYQUIN")
    uint64_t sequence_id;        // Số thứ tự chu kỳ (tăng đơn điệu)
    uint32_t version;            // Phiên bản ABI (0x00010000 = v1.0)
    uint32_t mode_flags;         // Bit 0: Deterministic Argmax, Bit 1: Born Sampling, Bit 2: Fallback LowRank
    uint64_t timestamp_ns;       // Thời gian gửi từ Cầu Treo (nanoseconds)
    float    temperature;        // Nhiệt độ lấy mẫu Born (mặc định 1.0)
    uint32_t active_rotors;      // Số lượng rotor hình học áp dụng (M ≤ 16)
    uint8_t  reserved_hdr[24];   // Phần dự phòng căn lề

    // --- MẶT NẠ RÀNG BUỘC CỨNG (HARD CONSTRAINT MASK: 512 BYTES) ---
    // 4.096 bits (512 bytes): 1 bit = 1 ứng viên. Bit = 1: Hợp lệ, Bit = 0: Vi phạm ràng buộc
    uint8_t  constraint_bitmask[512]; 

    // --- CẤU HÌNH ROTOR HÌNH HỌC (TRANSFORMATION CONFIG: 256 BYTES) ---
    // Tối đa 16 rotor bivector: Mỗi rotor gồm cặp chỉ số (i, j) và góc quay theta
    struct {
        uint8_t  plane_i;        // Chiều 1 [0..11]
        uint8_t  plane_j;        // Chiều 2 [0..11]
        uint16_t reserved_r;
        float    angle_theta;    // Góc quay radian
    } rotors[16];                // 16 * 8 bytes = 128 bytes
    uint8_t  reserved_rotors[128];

    // --- VECTOR TIỀM ẨN ĐẦU VÀO (LATENT PAYLOAD: 32.768 BYTES) ---
    // 4.096 phần tử số thực chuẩn IEEE 754 (float64) = 32 KiB
    // Tương ứng 1-1 với 4.096 basis blades của đại số Clifford Cl(12)
    double   latent_vector[4096]; 

} VivyquInputFrame; // Tổng kích thước: 64 + 512 + 256 + 32768 = 33.600 bytes (~32.8 KiB)

#pragma pack(pop)
```

> **Biến thể S1/S2 (Hilbert Complex State):** Nếu kích hoạt Không gian Hilbert phức (S1), mảng `latent_vector` được thay thế bằng `double complex_vector[4096][2]` (gồm phần thực và ảo, tổng $64\text{ KiB}$). Cầu Treo xác định định dạng thông qua cờ `mode_flags`.

---

### 3.2. Cấu Trúc Khung Đầu Ra (Output Frame ABI — 256 Bytes)

Được thiết kế siêu nhỏ gọn, nằm trọn trong đúng **4 Cachelines (256 bytes)**:

```c
#pragma pack(push, 1)

typedef struct alignas(64) {
    // --- KHỐI TRẠNG THÁI & ĐỒNG BỘ (64 BYTES) ---
    uint64_t magic_reply;        // 0x5649565951554F55 ("VIVYQUOU")
    uint64_t sequence_id;        // Phải khớp chính xác với sequence_id của Input Frame
    uint32_t error_code;         // 0: SUCCESS, 1: ERR_NAN_INPUT, 2: ERR_TIMEOUT, 3: ERR_ALL_CONSTRAINTS_VIOLATED
    uint32_t status_flags;       // Bit 0: Is_Deterministic, Bit 1: Renormalized, Bit 2: Fallback_Used
    uint64_t latency_core_ns;    // Thời gian tính toán thuần túy của Core (nanoseconds)
    uint8_t  reserved_stat[32];

    // --- MẢNH QUYẾT ĐỊNH CHÍNH (THE CORE FRAGMENT: 64 BYTES) ---
    uint32_t best_decision_idx;  // Chỉ số k* tối ưu ∈ [0..4095]
    uint32_t valid_candidates;   // Số lượng ứng viên thỏa mãn ràng buộc
    double   best_confidence;    // Biên độ xác suất P(k*) = |ψ_{A(k*)}|² ∈ [0.0, 1.0]
    double   norm_drift;         // Độ lệch chuẩn |‖ψ‖² - 1.0|
    double   system_entropy;     // Độ đo entropy thông tin của phân phối sau sụp đổ
    uint8_t  reserved_decision[32];

    // --- TẬP HỢP TOP-M ỨNG VIÊN (TOP-M SET: 128 BYTES) ---
    // Danh sách 8 phương án dự phòng cao nhất (dành cho Cầu Treo Multi-Worker)
    struct {
        uint32_t candidate_idx;  // Chỉ số ứng viên [0..4095]
        float    confidence;     // Điểm số xác suất
    } top_candidates[8];         // 8 * 8 bytes = 64 bytes
    uint8_t  reserved_top_m[64];

} VivyquOutputFrame; // Tổng kích thước: 256 bytes

#pragma pack(pop)
```

---

## 4. TẦNG 3: BẤT BIẾN TOÁN HỌC & TƯỜNG LỬA AN TOÀN (INVARIANTS & SAFETY FIREWALL)

Để đảm bảo hệ thống không bao giờ bị sụp đổ bất thường hay sinh ra quyết định sai lệch, 5 bất biến bắt buộc phải được kích hoạt trong mọi chu kỳ:

### 4.1. Bất Biến Lọc Rác Đầu Vào (Input Sanitization Firewall)
1. **Kiểm tra NaN / Infinite:**
   - Cầu Treo bắt buộc phải quét vector $\mathbf{h}$ trước khi nạp vào Shared Memory. Nếu có bất kỳ phần tử nào là `NaN` hoặc `±Inf`, Cầu Treo **không được truyền** vào Core mà phải kích hoạt một trong hai đối sách:
     - *Đối sách 1 (Default):* Kẹp giá trị (Clamp) về khoảng $[-10.0, 10.0]$.
     - *Đối sách 2:* Thay thế bằng vector trạng thái trung tính mặc định (Neutral State) và ghi cảnh báo lỗi.
2. **Kiểm tra Chuẩn Triệt Tiêu (Zero-Norm Check):**
   - Nếu $\|\mathbf{h}\|_2 < 10^{-12}$, vector bị coi là vector rỗng; Core tự động trả về quyết định ngẫu nhiên trong vùng hợp lệ và đánh dấu cờ cảnh báo `status_flags |= FLAG_ZERO_NORM`.

### 4.2. Bất Biến Bảo Toàn Chuẩn & Chống Trôi Số Học (Norm Conservation Guard)
- Độ lệch chuẩn được kiểm tra sau mỗi chu trình biến đổi:
  $$\Delta_{\text{norm}} = |\|\psi'\|^2 - 1.0|$$
- Nếu $\Delta_{\text{norm}} > 10^{-4}$: Lõi Core tự động thực hiện phép tái chuẩn hóa tức thì (In-place Renormalization):
  $$\psi_{\text{re}} = \frac{\psi'}{\|\psi'\|}$$
  và ghi lại độ lệch vào trường `norm_drift` trong Output Frame để Cầu Treo theo dõi độ thoái hóa số học.

### 4.3. Ranh Giới Thẩm Quyền (Authority Boundary)
- **Quyền của VivyQu Core:** Độc quyền quyết định giá trị $k^*$ dựa trên trường thế năng toán học. Cầu Treo không được phép "đoán ý" hay ghi đè kết quả dựa trên các bộ lọc heuristics bên ngoài.
- **Quyền Từ Chối Của Cầu Treo (Refusal of Execution):**
  - Cầu Treo được quyền từ chối đưa $k^*$ ra động cơ vật lý/thế giới **CHỈ KHI**:
    1. Output Frame có `error_code != 0`.
    2. Chỉ số $k^*$ nằm trong vùng vi phạm an toàn vật lý khẩn cấp (Emergency Collision/Hazard).
  - Khi từ chối, Cầu Treo **bắt buộc** phải kích hoạt hành động dự phòng (Fail-safe Default Action) và phát sinh bản ghi kiểm định (Audit Trail Log) giải thích rõ lý do từ chối.

---

## 5. TẦNG 4: GIÁM SÁT THỜI GIAN THỰC & CƠ CHẾ CỨU NGUY (WATCHDOG & RECOVERY)

```text
Chu kỳ bắt đầu ────────────────────────────────────────────────────────►
        │
        ├─── [ t < 10 μs ] ────► Core xử lý hoàn tất ──► Trả kết quả chuẩn
        │
        ├─── [ t = 100 μs ] ───► Cảnh báo Slowdown ────► Ghi log Telemetry
        │
        └─── [ t > 500 μs ] ───► TIMEOUT WATCHDOG ─────► CẮT MẠCH (CIRCUIT BREAKER)
                                                        ├── Kích hoạt Baseline A (W·h)
                                                        └── Reset Lõi Core
```

### 5.1. Cơ Chế Watchdog & Timeout Cắt Mạch (Circuit Breaker)
- **Ngưỡng Timeout:** $T_{\text{max}} = 500\ \mu\text{s}$ (gấp 50 lần độ trễ thiết kế bình thường).
- Nếu Core không phản hồi sau $500\ \mu\text{s}$:
  1. Cầu Treo lập tức ngắt chu kỳ chờ, đánh dấu slot hiện tại bị lỗi `ERR_CORE_TIMEOUT`.
  2. Cầu Treo tự động chuyển quyền quyết định sang **Nhánh Cứu Nguy Cổ Điển: Baseline A ($W \cdot \mathbf{h}$)** chạy trong $< 1\ \mu\text{s}$ để đảm bảo thế giới không bị khựng hình (frame-drop).
  3. Cầu Treo gửi tín hiệu tái lập (Reset Signal) để đưa trạng thái Core về khởi thủy.

### 5.2. Chế Độ Phục Hồi Tự Động (Self-Healing Lifecycle)
- Nếu Core gặp sự cố tràn số hoặc lỗi phần cứng 3 lần liên tiếp trong 100 chu kỳ:
  - Hệ thống tự động kích hoạt **Hạ Cấp Xuống Kế Hoạch Thứ Cấp (Auto-Downgrade to Secondary Plan)**: Chuyển từ $\mathcal{C}\ell(12)$ sang Không gian Hilbert phức (S1/S2) hoặc Score Tuyến Tính (F3).
  - Báo cáo sự cố lên trung tâm giám sát NPS để ghi nhận bài học kinh nghiệm (Lesson Learned).

---

## 6. MA TRẬN ĐỐI CHIẾU CÁC KẾ HOẠCH GIAO DIỆN (INTERFACE TRADE-OFF MATRIX)

| Tiêu Chí | Kế Hoạch Chính (P): Lock-Free Shared Mem | Kế Hoạch Thứ Cấp (S): Direct DLL FFI | Kế Hoạch Cứu Nguy (F): Named Pipes |
|---|---|---|---|
| **Độ trễ vận chuyển (Latency)** | **$< 0.3\ \mu\text{s}$** | **$\approx 0.005\ \mu\text{s}$** | $\approx 15 - 30\ \mu\text{s}$ |
| **Cách ly tiến trình (Process Isolation)**| **Tuyệt đối (2 tiến trình riêng)** | Không (Cùng 1 tiến trình) | Tuyệt đối (Có thể qua container) |
| **Độ phức tạp triển khai** | Trung bình (Shared Memory + Atomic) | Rất thấp (Gọi con trỏ hàm C) | Thấp (Đọc ghi stream) |
| **Rủi ro khi một bên bị Crash** | Bên còn lại tồn tại an toàn | Cả hệ thống cùng crash | Bên còn lại tồn tại an toàn |
| **Môi trường phù hợp nhất** | **Sản phẩm Production thời gian thực** | **Benchmark & Nghiên cứu nội bộ** | **Môi trường Sandbox / Cloud Microservices** |

---

## 7. KẾT LUẬN & CAM KẾT CHUYỂN GIAO

Bản đặc tả này đóng đinh toàn bộ ranh giới nhị phân và giao thức giữa Cầu Treo và VivyQu Core. Mọi module phát triển tiếp theo (Python binding, C++ Core, hoặc Rust Actor) **bắt buộc phải tuân thủ chính xác 100% kích thước byte, độ căn lề 64-byte, và các trường của `VivyquInputFrame` và `VivyquOutputFrame`**.
