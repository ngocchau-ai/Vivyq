# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# VivyQu — Đặc tả Đa hướng Phát triển & Ma trận Thực nghiệm Mở rộng

**Trạng thái:** Đề xuất mở rộng & Thẩm định kiến trúc (Song song với tài liệu gốc)  
**Ngày:** 2026-09-27  
**Tác giả thảo luận:** Ngọc Châu, Deepseek & Antigravity  
**Vai trò:** Bổ sung cho `ARCHITECTURE_SPEC.md`, `MATH_SPEC_BLUEPRINT.md`, `RESEARCH_AND_DEVELOPMENT_PLAN.md`, `VIVY_NPS_INHERITANCE_AND_HYBRID_QUDIT.md`. Không thay thế các tài liệu gốc; giữ nguyên trạng thái mở của các tuyên bố chưa được kiểm chứng.

---

## 0. ĐÍNH CHÍNH PHẠM VI & PHÂN BỔ BỘ NHỚ

Trước khi triển khai các hướng phát triển, cần đóng đinh dứt khoát ranh giới bộ nhớ và không gian biểu diễn:

| Thuộc tính | Giá trị quy chuẩn | Diễn giải & Ranh giới |
|---|---|---|
| **Số chiều không gian trạng thái** | **4.096** | Cố định theo kiến trúc nền tảng (tương thích hidden dimension của LLaMA/Gemma). |
| **Tương đương Qubit** | **12 qubit** | \(2^{12} = 4.096\) trạng thái cơ sở (basis states). |
| **Tương đương Qudit(4)** | **6 qudit** | \(4^6 = 4.096\) trạng thái cơ sở. |
| **Kích thước State (`complex128`)** | **64 KiB** | \(4096 \times 16\) bytes. Mục tiêu nằm trọn trong L1/L2 Cache của CPU. |
| **Kích thước State (`complex64`)** | **32 KiB** | \(4096 \times 8\) bytes. Tối ưu hơn cho L1 Data Cache. |
| **Kích thước State (`real64` / Clifford)** | **32 KiB** | Biểu diễn multivector trong \(\mathcal{C}\ell(12)\) hoặc vector thực bỏ pha. |
| **Ngân sách Bộ nhớ Core** | **16 GiB** | Ngân sách phần cứng cấp riêng cho tiến trình VivyQu Core (Cold memory / Batch buffer / Working-set dự phòng). |
| **Hệ số dư thừa lý thuyết** | **262.144×** | Tỷ lệ giữa 16 GiB RAM và 64 KiB State vector. |

> **Kết luận phân định:** VivyQu **không phải** là máy mô phỏng statevector 30 qubit đa dụng (cần 16 GiB chỉ cho 1 statevector). VivyQu là **Bộ chọn quyết định nhận thức 4.096 chiều (4.096-dim Cognitive Decision Selector)**. 64 KiB là dung lượng *Hot-path Working State* để đạt latency siêu tốc (< 10 µs), trong khi 16 GiB là *System Hardware Envelope* phục vụ batch inference, bảng ma trận tra cứu (lookup tables), và bộ nhớ đệm giả thuyết.

---

## 1. NĂM NHÁNH PHÁT TRIỂN SONG SONG (BRANCHES A–E)

Hệ thống được phân rã thành 5 nhánh phát triển độc lập với giả thuyết, chi phí và tiêu chí thành công minh bạch:

```text
                               ┌─── [A] Baseline Cổ Điển (Score W·h / MLP nhỏ)
                               ├─── [B] Statevector Thuần (Biên độ phức + Unitary đường chéo)
VivyQu Core 4.096D ────────────┼─── [C] Clifford / Đại số Hình học (Multivector Cl(12) + Rotor)
                               ├─── [D] Neural Operator Bridge (MLP / Structural Operator)
                               └─── [E] Hybrid NPS + Core Selection (Vòng đời Giả thuyết)
```

### 1.1. Bảng Tổng Quan Năm Nhánh

| Mã | Tên Nhánh | Ý Tưởng Cốt Lõi | Chi Phí R&D | Rủi Ro | Tiềm Năng Độc Bản |
|---|---|---|---|---|---|
| **A** | **Score Cổ Điển (Baseline)** | `score = W · h`, lọc ràng buộc cứng, `argmax(score)` | Rất thấp (1w) | Rất thấp | Thấp nhưng là thước đo chuẩn mực |
| **B** | **Statevector Thuần** | Mã hóa 4.096 chiều phức, Unitary transform, `argmax \|c\|²` | Thấp (2w) | Trung bình | Trung bình (khai thác pha giao thoa) |
| **C** | **Clifford / Hình Học** | Multivector \(\mathcal{C}\ell(12)\), quay bằng Rotor sandwich \(R \psi \widetilde{R}\) | Trung bình (3w) | Trung bình-Cao | Rất cao (bảo toàn chuẩn, không type-mismatch) |
| **D** | **Neural Operator Bridge** | Mạng học ánh xạ candidate/hidden state sang biên độ tối ưu | Cao (4w) | Trung bình | Cao về khớp dữ liệu, thấp về tính độc bản |
| **E** | **Hybrid NPS + Selection** | Kế thừa vòng đời giả thuyết NPS, dùng Core chọn lọc top-k | Trung bình (3w) | Thấp | Rất cao (tận dụng mã nguồn Vivy có sẵn) |

---

### 1.2. Chi Tiết Từng Nhánh

#### Nhánh A — Score Cổ Điển (Baseline Bắt Buộc)
- **Cơ chế:** Bỏ qua toàn bộ cơ chế lượng tử. Dùng hồi quy tuyến tính `score = W · h` (hoặc MLP 1 tầng ẩn cực nhẹ). Lọc ràng buộc cứng rồi lấy `argmax`.
- **Vai trò:** Cột mốc kiểm định bắt buộc (Golden Baseline). Mọi nhánh B, C, D, E phải chứng minh vượt qua A trên tập dữ liệu held-out ít nhất ở một chỉ số có ý nghĩa thống kê (regret hoặc tính đa dạng hợp lệ).
- **Ngân sách:** < 1 MiB RAM, Latency < 1 µs trên CPU.

#### Nhánh B — Statevector Thuần
- **Cơ chế:** Chuẩn hóa vector đầu vào thành biên độ phức \(c_k = r_k e^{i \theta_k}\). Áp dụng ma trận Unitary có cấu trúc (đường chéo \(U = \text{diag}(e^{i \phi_k})\), block-diagonal 2×2/4×4, hoặc tích Kronecker).
- **Biến thể:**
  - B1: Real-only vector chuẩn hóa \(c = h / \|h\|_2\).
  - B2: Thêm pha Sigmoid \(\theta_k = \pi \cdot \sigma((h_k - \mu)/\sigma)\).
  - B3: Unitary đường chéo (pha đối xứng).
  - B4: Khối ma trận hoán vị và ghép cặp.
- **Tiêu chí:** Chứng minh được rằng *thông tin pha* thực sự tạo ra giao thoa triệt tiêu phương án xấu hiệu quả hơn phép nhân ma trận trọng số cổ điển.

#### Nhánh C — Clifford / Geometric Algebra (\(\mathcal{C}\ell(12)\))
- **Giải quyết Type-Mismatch của Sandwich Product:** Trong các bản thảo trước, biểu thức \(R |\psi\rangle R^\dagger\) bị phản biện là không hợp kiểu với ket trạng thái trong \(\mathbb{C}^{4096}\).
- **Đặc tả chuẩn hóa:**
  - Không gian trạng thái được định nghĩa là một **Multivector trong Đại số Clifford \(\mathcal{C}\ell(12)\)**. Vì \(2^{12} = 4.096\), một multivector tổng quát \(\psi \in \mathcal{C}\ell(12)\) có đúng 4.096 thành phần thực độc lập:
    \[
    \psi = \langle \psi \rangle_0 + \sum_{i} \langle \psi \rangle_{1, i} e_i + \sum_{i<j} \langle \psi \rangle_{2, ij} e_{ij} + \dots + \langle \psi \rangle_{12} e_{12\dots12}
    \]
  - Rotor \(R \in \text{Spin}(12)\) được tạo từ bivector: \(R = \exp(-\frac{1}{2} B)\) với \(B = \sum b_{ij} e_i \wedge e_j\).
  - Tác động quay sandwich: \(\psi' = R \psi \widetilde{R}\) (trong đó \(\widetilde{R}\) là phép đảo - reversion).
  - **Ưu điểm vượt trội:** Hoàn toàn là số thực (32 KiB với `float64`), bảo toàn chuẩn tự nhiên \(\|\psi'\|^2 = \|\psi\|^2\), không cần ma trận phức, nằm trọn trong L1 Cache.

#### Nhánh D — Neural Operator Bridge
- **Cơ chế:** Dùng mạng nơ-ron học toán tử biến đổi từ vector tiềm ẩn sang phân phối quyết định tối ưu.
- **Ranh giới công nghệ:**
  - *Cảnh báo AI Slop / Overkill:* Tránh dùng FNO (Fourier Neural Operator) hay DeepONet vì các công cụ này thiết kế cho không gian hàm liên tục vô hạn chiều (PDEs vật lý). Không gian VivyQu là không gian trạng thái rời rạc 4.096 chiều.
  - *Kiến trúc đề xuất:* MLP nén-giải nén có gating (Linear 4096→512, GELU, Residual, Linear 512→4096) hoặc Structural Cross-Attention cực nhẹ.
- **Rủi ro:** Làm phình working-set lên ~20–40 MB (vượt L1/L2 cache), latency tăng lên 50–200 µs, và có nguy cơ biến VivyQu thành một deep ranker thông thường.

#### Nhánh E — Hybrid NPS + Selection (Kế Thừa Trực Tiếp Vivy)
- **Cơ chế:** Kế thừa trực tiếp hệ thống giả thuyết của `Vivy_final` (`lifecycle.py`, `epistemic_gate.py`, `controller.py`).
- **Luồng tích hợp:**
  1. NPS sinh ra quần thể \(N_h\) giả thuyết ngữ nghĩa.
  2. Encoder ánh xạ các giả thuyết thành vector đặc trưng trong không gian 4.096 chiều.
  3. VivyQu Core đóng vai trò là **Bộ lọc nhận thức (Epistemic Filter)**: thực thi biến đổi và trả về top-k ứng viên có biên độ/xác suất sụp đổ cao nhất.
  4. NPS chỉ kích hoạt thực nghiệm (Verifier/Experiment) trên top-k này, cập nhật evidence và loại bỏ (prune) các nhánh giả thuyết kém hiệu quả.

---

## 2. MA TRẬN THỰC NGHIỆM MỞ RỘNG (E0 – E9)

Bổ sung 4 thử nghiệm E6–E9 vào ma trận chuẩn E0–E5:

| Mã Thử Nghiệm | Tên Nghiệp Vụ | Nhánh Kiểm Tra | Mục Tiêu & Chỉ Số Đo | Thời Gian Dự Kiến | Ngưỡng Pass Chấp Nhận |
|---|---|---|---|---|---|
| **E0** | **Xác lập Bài toán & Baseline** | Nhánh A | Xây dựng oracle chuẩn, tập dữ liệu held-out, đo Baseline A2 (score tuyến tính) | Tuần 1 | Baseline A2 đạt Regret \(\le 10\%\). Đóng băng baseline. |
| **E1** | **Khảo sát Mã hóa Biên độ** | Nhánh B | So sánh signed-real vs. complex-pha; kiểm tra trường hợp suy biến (zero, NaN) | Tuần 2 | Xác định liệu pha có mang lại thông tin vượt trội so với signed-real. |
| **E2** | **Khảo sát Toán tử Biến đổi** | Nhánh B, C | So sánh Identity, Diagonal Unitary, Block-Diagonal và Rotor \(\mathcal{C}\ell(12)\) | Tuần 3–4 | Ít nhất một toán tử đạt Regret < Regret(A2) với p-value < 0.05. |
| **E3** | **Chiến lược Thu nhận Đầu ra** | Nhánh B, C | So sánh `argmax \|c\|²`, `top-k beam`, và `Born sampling` | Tuần 4 | `argmax` đủ cho quyết định đơn trị; Born sampling tối ưu cho đa dạng hóa. |
| **E4** | **Kiểm định Vi mô (Microbench)** | Nhánh A, B, C | Đo p50/p95/p99 latency (warm/cold cache), peak working-set, cache misses | Tuần 5 | Core-only p99 < 10 µs cho A, B; p99 < 20 µs cho C. State memory \(\le 64\) KiB. |
| **E5** | **Tích hợp End-to-End** | Toàn hệ thống | Nối LLM/Vision Encoder \(\to\) VivyQu Core \(\to\) Cầu Treo thực thi | Tuần 6 | End-to-end latency đáp ứng yêu cầu hệ thống; không phát sinh lỗi an toàn. |
| **E6** | **Huấn luyện Neural Operator** | Nhánh D | Train mạng học toán tử trên tập mẫu lớn; đánh giá Regret và sai số biên độ | Tuần 7–9 | Regret(D) \(\le 5\%\); thời gian inference < 200 µs trên CPU. |
| **E7** | **Đánh giá Cross-Domain** | Nhánh D | Đưa model đã train ở E6 sang 3 bài toán/miền dữ liệu chưa từng thấy | Tuần 10 | Vượt Baseline A trên ít nhất 2/3 domain (chứng minh tính tổng quát hóa). |
| **E8** | **Tích hợp NPS Quần thể** | Nhánh E | Đo mức suy giảm số vòng lặp hội tụ của NPS khi có Core lọc top-k | Tuần 11 | Giảm \(\ge 20\%\) số vòng lặp thực nghiệm/chi phí gọi model chuyên gia. |
| **E9** | **Quyết Đấu Năm Nhánh (Grand Prix)** | A, B, C, D, E | Chạy cả 5 nhánh trên cùng bài toán chuẩn, cùng split dữ liệu, cùng hạt giống seed | Tuần 12 | Xác định nhánh tối ưu toàn diện (Pareto Frontier giữa Regret và Latency). |

---

## 3. PHÂN ĐỊNH ĐIỂM MÙ TOÁN HỌC & ĐỘ PHỨC TẠP TÍNH TOÁN

### 3.1. Điểm Mù Chí Tử: Hai Bài Toán Khác Biệt Hoàn Toàn

Trong phân tích sơ bộ của tài liệu Deepseek, có một điểm cần được hiệu chỉnh nghiêm ngặt về mặt toán học:

1. **Bài toán 1 — Context-to-Action Decision (Triết lý VivyQu):**
   - **Đầu vào:** Một vector ngữ cảnh duy nhất \(h \in \mathbb{R}^{4096}\) từ LLM/môi trường.
   - **Cơ chế:** Core ánh xạ \(h \to \psi \in \mathbb{C}^{4096}\) (hoặc \(\mathcal{C}\ell(12)\)), áp dụng toán tử quay \(U\) hoặc Rotor \(R\), rồi đo `argmax` để chọn 1 trong 4.096 hành động / trạng thái tham số rời rạc.
   - **Độ phức tạp:** Chỉ có **1 vector**, biến đổi đường chéo tốn \(O(d)\) hoặc \(O(d \log d)\). Với \(d = 4096\), số phép tính là \(\sim 4.096\) đến \(50.000\) phép tính.
   - **Thời gian thực thi:** **< 5 µs** trên CPU một thread! Hoàn toàn đạt mục tiêu p99 < 10 µs.

2. **Bài toán 2 — Candidate Retrieval / Ranking (Giả định Deepseek trong E0):**
   - **Đầu vào:** \(n = 10.000\) vector ứng viên khác nhau, mỗi vector có 4.096 chiều.
   - **Cơ chế:** Phải mã hóa và chấm điểm từng vector một.
   - **Độ phức tạp:** \(O(n \cdot d) = 10^4 \times 4096 \approx 4 \times 10^7\) phép tính.
   - **Thời gian thực thi:** \(\sim 40\text{ ms}\) trên CPU.

> **Định vị bắt buộc:** VivyQu Core được sinh ra cho **Bài toán 1 (Cognitive Decision)**, không phải công cụ Search/Retrieval cho $10^4$ vector rời rạc. Nếu áp dụng vào bài toán có nhiều ứng viên (Bài toán 2), VivyQu chỉ được nhận danh sách tối đa 4.096 slot ứng viên đã được Cầu Treo gom cụm, hoặc bắt buộc phải dùng kỹ thuật **Batch SIMD Encoding** để không phá vỡ ranh giới thời gian thực.

---

## 4. MA TRẬN ĐÁNH ĐỔI PARETO KỲ VỌNG

| Tiêu Chí | Nhánh A (Baseline) | Nhánh B (Statevector) | Nhánh C (Clifford Cl(12)) | Nhánh D (Neural Op) | Nhánh E (NPS Hybrid) |
|---|---|---|---|---|---|
| **Regret Kỳ Vọng** | ~10% – 12% | ~8% – 10% | ~7% – 9% | **~4% – 6%** | ~6% – 8% |
| **Latency p99 (Core)** | **< 1 µs** | ~5 µs – 10 µs | ~10 µs – 20 µs | ~100 µs – 200 µs | ~5 ms (do vòng lặp NPS) |
| **Working Memory** | **< 1 MiB** | 64 KiB (L1/L2) | **32 KiB (L1 Cache)** | ~20 MiB – 40 MiB | Biến thiên theo giả thuyết |
| **Chi Phí Training** | 0 (hoặc vài giây) | 0 | 0 | ~2 – 4 giờ GPU | 0 |
| **Bản Sắc Độc Bản** | Không có (chuẩn) | Trung bình | **Rất cao** | Thấp (Deep Learning) | **Rất cao (Hệ thống tư duy)** |

### Giá Trị Của Kết Quả Âm (Negative Results)
- Nếu **Nhánh A thắng tất cả các nhánh khác**: Kết luận thẳng thắn: Cơ chế lấy cảm hứng từ lượng tử không mang lại lợi thế cho bài toán này; VivyQu Core nên rút gọn về một ma trận chấm điểm tuyến tính siêu nhẹ.
- Nếu **Nhánh D thắng nhưng B và C thua**: Kết luận: Giá trị nằm ở tính phi tuyến của mạng học sâu, không nằm ở tính bảo toàn chuẩn hay giao thoa biên độ.
- Nếu **Nhánh E thắng vượt trội**: Kết luận: Sức mạnh nhận thức thực sự nằm ở **vòng đời giả thuyết và kiểm chứng chứng cứ (NPS Framework)**, trong khi bộ chọn chỉ cần ở mức đơn giản.

---

## 5. LỘ TRÌNH TRIỂN KHAI TINH GỌN (TRI-FORK STRATEGY)

Thay vì dàn trải cả 5 nhánh cùng lúc gây quá tải tài nguyên (1–2 nhân sự), đề xuất gom lại thành **Chiến Lược Ba Mũi Nhọn**:

```text
Giai đoạn 1 (Tuần 1–4): Mũi Nhọn Cốt Lõi ───► Baseline A + Nhánh B (Statevector) + Nhánh C (Cl(12))
                                              (Xác định dứt khoát: Pha & Hình học có ích không?)
                                              
Giai đoạn 2 (Tuần 5–8): Mũi Nhọn Hệ Thống ──► Nhánh E (Tích hợp NPS Quần thể Giả thuyết)
                                              (Gắn kết Core vào hạ tầng Vivy hiện hữu)

Giai đoạn 3 (Tuần 9–12): Mũi Nhọn Mở Rộng ──► Nhánh D (Neural Op Bridge) & Grand Prix E9
                                              (Thực hiện nếu các nhánh trên cần đối chứng phi tuyến)
```

### Các Cổng Quyết Định (Decision Gates)
- **Cổng G1 (Sau Tuần 2):** Đóng băng Baseline A (Regret \(\le 12\%\)). Kiểm tra E1. Nếu pha phức không cải thiện gì so với signed-real vector, loại bỏ biểu diễn pha phức phức tạp, chuyển sang vector thực 32 KiB.
- **Cổng G2 (Sau Tuần 5):** Kiểm tra E2 và E4. Nếu Nhánh C (\(\mathcal{C}\ell(12)\)) đạt Regret \(\le\) Nhánh B và Latency p99 < 20 µs, chốt \(\mathcal{C}\ell(12)\) làm chuẩn toán học chính thức thay thế Ket phức.
- **Cổng G3 (Sau Tuần 8):** Kiểm tra E8. Xác nhận mức giảm vòng lặp NPS \(\ge 15\%\).
- **Cổng G4 (Sau Tuần 12):** Tổng kết E9, công bố báo cáo kiểm định và chốt mã nguồn chuyển giao.

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:**
  - Khởi tạo tài liệu đặc tả 5 nhánh phát triển (A–E) và ma trận thực nghiệm mở rộng (E0–E9) từ kết quả thảo luận Deepseek.
  - Đính chính điểm mù toán học: phân biệt rõ Bài toán 1 (Context-to-Action Decision, $n=1, d=4096$) và Bài toán 2 (Candidate Retrieval, $n=10^4$).
  - Chuẩn hóa toán học cho Nhánh C: Giải quyết xung đột kiểu của Rotor sandwich bằng cách định nghĩa trạng thái là **Multivector trong Đại số Clifford \(\mathcal{C}\ell(12)\)** với 4.096 thành phần thực.
  - Đề xuất Chiến lược Ba Mũi Nhọn (Tri-Fork Strategy) để tối ưu hóa nguồn lực triển khai trong 12 tuần.
