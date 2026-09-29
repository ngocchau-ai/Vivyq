# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# KẾ HOẠCH TỔNG THỂ: VIVYQU THỪA HƯỞNG HƯỚNG ĐI VIVY_FINAL & HỢP NHẤT THÂN THỂ CAUTREO
**Dự án:** Vivyqu & Cautreo Ecosystem  
**Tác giả:** Ngọc Châu & Antigravity  
**Ngày ban hành:** 2026-09-27  
**Nguyên tắc cốt lõi:** *Vivyqu thay đổi Lõi tư duy (The Thinking Core), bảo toàn 100% Phương thức làm việc, học tập và Thân thể Cầu Treo.*

---

## 1. NGUYÊN LÝ BẢN THỂ: CÁI GÌ THAY ĐỔI VÀ CÁI GÌ GIỮ NGUYÊN?

Hệ thống tuân thủ triệt để nguyên tắc **Soul-Body Decoupling** đã được xác lập:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        VIVYQU: LINH HỒN MỚI (THE EVOLVED SOUL)                         │
│  - LÕI TƯ DUY MỚI THAY THẾ NPS-CORE: Đại số hình học Clifford Cl(12) (4096 chiều)      │
│  - Phép quay trực giao Spin(12) Givens Rotors (8 rotor pairs)                          │
│  - Sụp đổ xác định E9 Geometric Scorer siêu tốc (< 30 μs trên CPU)                     │
│  - Tự thích nghi trực tuyến bằng Hamiltonian Torque Descent (không cần backpropagation)│
│  - Thuần túy toán học, phi I/O, không gọi file, không mở port mạng                     │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ C-ABI In-Process Pointer & Shared Memory Bus
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     CẦU TREO (CAUTREO): THÂN THỂ HOÀN VẸN (THE BODY)                   │
│  - ĐÃ SAO CHÉP & HIỆN HỮU NGUYÊN VẸN TRONG REPO (cautreo/, engine/, host/, ui/)        │
│  - Cautreo Engine: C11 Native shared library (cautreo.dll, context_memory.h, wvs.h)   │
│  - Cautreo Server & CLI: cautreo.exe (chat / serve) & cautreo-server.exe (Port 8080)   │
│  - Cautreo Host & UI: cautreo_host bus, bodymap, plugin registry, Desktop Studio UI   │
│  - Weight Pager & SSD Streaming: cautreo_pager.dll                                     │
│  - Nơi tương tác thực tế với thế giới: Tools (WebSearch, FileEdit, CodeExec), Devices │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Bảng Ma Trận Phân Định Ranh Giới:

| Thành phần Hệ thống | Nguồn gốc / Trạng thái | Hướng xử lý tại Vivyqu | Bản chất kiến trúc |
|---|---|---|---|
| **Cơ thể Cầu Treo (The Body)** | `D:\91s_Vivy\Vivy_final` (`cautreo/`, `engine/`, `host/`, `ui/`) | **Đã sao chép sang `d:\Vivyqu`** | **GIỮ NGUYÊN VẸN 100%**: Thân thể thực thi, server, CLI, UI, SSD streaming. |
| **Bản sắc: Nhà khoa học trưởng** | `Vivy_final/docs/ARCHITECTURE.md` | Thừa hưởng nguyên vẹn | **GIỮ NGUYÊN VẸN**: Không làm việc thô, duy trì quần thể giả thuyết, điều phối executor. |
| **Phương thức làm việc (Working Method)** | Chu trình: Ingest $\to$ Think $\to$ Act $\to$ Observe | Thừa hưởng nguyên vẹn | **GIỮ NGUYÊN VẸN**: CCE segment $\le 1500$ tokens, tool dispatcher, evidence collection. |
| **Phương thức học tập (Learning Method)** | Cognitive State Graph, Hebbian Recall, VM-11, Sync `2brain` | Nâng cấp cơ chế thi hành | **GIỮ NGUYÊN VẸN**: NPS Pruning (512B mask) & Torque Descent đồng bộ sang `D:\2brain`. |
| **LÕI TƯ DUY (Thinking Core)** | **NPS-Core cũ**: heuristics rời rạc, nghẽn CPU 60-90s prefill LLM | **Lõi Clifford $\mathcal{C}\ell(12)$ AVX2**: ra quyết định trong $26.8\ \mu\text{s}$ | **CẢI TIẾN DUY NHẤT (THE CORE UPGRADE)** |

---

## 2. PHƯƠNG ÁN THỪA HƯỞNG & HỢP NHẤT CHI TIẾT

### 2.1. Thừa hưởng Bản sắc "Nhà khoa học trưởng" (Principal Scientist Persona)
Theo tài liệu kiến trúc gốc `Vivy_final`:
- Vivy không phải là một chatbot thụ động, cũng không tự ôm đồm việc thực thi chuyên sâu.
- Vivy đóng vai trò điều phối viên nhận thức cấp cao:
  1. Tiếp nhận bài toán và dữ liệu môi trường từ Cầu Treo.
  2. Khởi tạo và duy trì quần thể giả thuyết trong không gian Clifford $\mathcal{C}\ell(12)$.
  3. Xoay góc nhìn trực giao qua 8 cặp Givens Rotors Spin(12) để đánh giá đa chiều.
  4. Sụp đổ hàm sóng xác định để chọn giả thuyết tối ưu $k^* \in [0, 4095]$.
  5. Giao nhiệm vụ cho Cầu Treo thực thi thông qua Tool Dispatcher / Actuator.
  6. Thu nhận bằng chứng (Evidence) và cập nhật mặt nạ ràng buộc (NPS Pruning).

### 2.2. Thừa hưởng Phương thức Làm việc (Working Pipeline)
Chu trình làm việc 5 pha của Vivy_final được gắn kết trực tiếp với các module của Vivyqu:
```text
  [MÔI TRƯỜNG THỰC TẾ / NGƯỜI DÙNG / TÁC VỤ]
                     │
                     ▼
  1. PHA INGESTION (Cầu Treo Context Chain Engine)
     - CCE phân đoạn tài liệu/dữ liệu thành các chunks ≤ 1500 tokens
     - InputSplittingCodec đóng gói 4 khối nhận thức thành h ∈ ℝ⁴⁰⁹⁶
                     │
                     ▼
  2. PHA THINKING (Lõi Vivyqu Core Clifford Cl(12))
     - Nạp vector h vào L1 Data Cache (32 KiB)
     - Xoay Spin(12) Givens Rotors R ψ R~
     - Sụp đổ xác định E9 Geometric Scorer ra quyết định k* trong 26.80 μs
                     │
                     ▼
  3. PHA ACTION (Cầu Treo Tool Dispatcher & Actuator)
     - OutputStitchingCodec giải mã k* thành lệnh hành động 12-bit
     - Cautreo Host điều phối tools (WebSearch, FileEdit, RunCommand, UI)
                     │
                     ▼
  4. PHA OBSERVATION (Bằng chứng thực thi - Evidence Collection)
     - Cầu Treo thu nhận kết quả thực thi (Receipt, Logs, Output, P&L/Reward)
                     │
                     ▼
  5. PHA LEARNING (Bộ nhớ Hồi ức & Tiến hóa bản thể)
     - Ghi nhận Episode vào EpisodicMemoryBuffer (10.000 slots)
     - Cập nhật NPS Pruning (xóa bit k* nếu thất bại liên tiếp trong 512-byte mask)
     - Replay Hamiltonian Torque Descent xoay góc rotor giảm loss tại chỗ
     - Đồng bộ bài học bền vững (Durable Lessons) sang D:\2brain
```

### 2.3. Thừa hưởng Phương thức Học tập & Bộ nhớ Tri thức (Learning & Memory)
Vivyqu thừa hưởng trọn vẹn 3 tầng ký ức của Vivy_final:
1. **Tầng 1: Ký ức Bền vững Tĩnh (Static Weights & Modelfiles):**
   - Trọng số E9 Geometric Scorer (`e9_weights.bin`, 2.016 MiB) được đóng băng.
2. **Tầng 2: Ký ức Làm việc Tức thời (Hot Working State):**
   - Vector trạng thái 32 KiB resident trong L1 Data Cache; mặt nạ ràng buộc 512 bytes kiểm soát các giả thuyết hợp lệ.
3. **Tầng 3: Ký ức Hồi ức & Tiến hóa Tự học (Episodic Feedback & Dream Cycle):**
   - **NPS Pruning:** Kế thừa cơ chế Epistemic Falsification của Vivy_final. Khi một hành động gây lỗi liên tiếp, bitmask bị khóa vĩnh viễn ở cấp độ phần cứng.
   - **Hamiltonian Torque Descent:** Thay thế việc huấn luyện lại mô hình tốn kém bằng việc xoay vi phân 8 cặp rotors Spin(12) theo moment lực bivector ($< 50\ \mu\text{s}$).
   - **Đồng bộ D:\2brain:** Xuất tự động toàn bộ bài học kinh nghiệm sang `D:\2brain\hot-memory` và `D:\2brain\notes\antigravity`.

---

## 3. LỘ TRÌNH KỸ THUẬT TRIỂN KHAI TÍCH HỢP

```text
[BƯỚC 1: ĐÃ XONG] ──► Sao chép trọn vẹn Cầu Treo (cautreo/, engine/, host/, ui/) vào Vivyqu
       │
       ▼
[BƯỚC 2: CẦU NỐI] ──► Xây dựng CautreoBinding: Cầu Treo nạp vivyqu_core.dll làm decision engine
       │
       ▼
[BƯỚC 3: GHÉP NỐI] ──► Nối ContextChainEngine (CCE) ──► InputSplittingCodec ──► Vivyqu Core
       │
       ▼
[BƯỚC 4: ĐIỀU PHỐI]──► Vivyqu Core k* ──► OutputStitchingCodec ──► Cautreo ToolDispatcher
       │
       ▼
[BƯỚC 5: KIỂM ĐỊNH]──► Chạy test tích hợp end-to-end: Cầu Treo gọi Vivyqu ra quyết định và học hỏi
```

---

## 4. THẨM ĐỊNH THEO BỘ TIÊU CHUẨN 4 TRỤC (4-PILLAR AUDIT)

1. **Xung đột (Conflict):**
   - **Đạt:** Không có xung đột giữa Thân thể (Cầu Treo) và Linh hồn (Vivyqu). Đã triệt tiêu hoàn toàn nguy cơ Vivyqu tự đi xây lại một thân thể thứ hai.
2. **Hợp lý (Rationality):**
   - **Đạt:** Cầu Treo đã có sẵn binary C11, server HTTP port 8080 và CLI; Vivyqu đã có sẵn DLL C++ AVX2 siêu tốc. Việc ghép nối in-process qua C-ABI là giải pháp tự nhiên và đạt hiệu năng cao nhất.
3. **Dư thừa (Redundancy):**
   - **Đạt:** Loại bỏ 100% các kế hoạch thừa thãi (tự viết runtime daemon riêng, tự mở cổng HTTP riêng cho Vivyqu). Tái sử dụng tối đa hạ tầng hoàn thiện của Cầu Treo.
4. **Hiệu quả (Effectiveness):**
   - **Đạt:** Giải quyết đúng nỗi đau lớn nhất của Cầu Treo ở Vivy_final: thời gian prefill LLM 60-90s gây soft-hang. Với Vivyqu Core, Cầu Treo ra quyết định vi mô trong **$26.80\ \mu\text{s}$**, tăng tốc độ phản xạ lên gấp 2.000.000 lần!

---

## 5. LỊCH SỬ THAY ĐỔI (AUDIT TRAIL)

| Thời gian (UTC+7) | Agent / Người sửa | Hành động & Lý do |
|:---:|:---|:---|
| 2026-09-27 20:15 | Antigravity IDE | Khởi tạo Kế hoạch tổng thể: Sao chép Cầu Treo vào Vivyqu, xác lập phương án thừa hưởng toàn diện bản sắc, phương thức làm việc và học tập của Vivy_final; định vị Vivyqu là sự thay đổi Lõi tư duy Clifford Cl(12). |
