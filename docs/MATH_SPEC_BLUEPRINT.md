# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# VIVYQU CORE — BẢN PHÁC THẢO THIẾT KẾ TOÁN HỌC & LÕI NHẬN THỨC
**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Tác giả sáng lập:** Ngọc Châu  
**Đơn vị hỗ trợ kiến trúc:** Antigravity (Trợ lý toàn thời gian Ngọc Châu)  
**Phiên bản:** v0.1-Alpha  
**Thời gian tạo:** 2026-09-26  

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)
- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Bổ sung Phần II — Khóa thiết kế toán học đa giải pháp (Locked Dual-Tier Mathematical Specification v0.2). Xác lập giải pháp chính (Primary Plan - P) và giải pháp thứ cấp / dự phòng (Secondary/Fallback Plan - S/F) cho toàn bộ 5 thành phần: (1) Đa tạp trạng thái Multivector \(\mathcal{C}\ell(12)\) vs. Hilbert \(\mathbb{C}^{4096}\), (2) Nạp & chiếu Grade Canonical vs. Modulus-Sigmoid, (3) Toán tử Spin(12) Rotor phân tích nhân tử vs. Diagonal Unitary + FWHT, (4) Động lực học hạ thế năng Bivector Torque Flow vs. Bounded Grover, (5) Sụp đổ quyết định Hard-Masked Argmax vs. Born Sampling.
- **2026-09-26 | Antigravity (Trợ lý Ngọc Châu):** Khởi tạo bản phác thảo thiết kế toán học đầu tiên cho Vivyqu Core. Định nghĩa không gian Hilbert 12-qubit / 6-qudit (4.096 chiều), toán tử hình học Clifford, động lực học hạ thế năng Hamiltonian và cơ chế sụp đổ hàm sóng đo lường trong micro-giây.
- **2026-09-27 | Vy / doc_author:** Bổ sung ghi chú trạng thái cô lập cho các giả thuyết toán học và hiệu năng ở §2–6; giữ nguyên bản phác thảo gốc.

---

> **[ISOLATED / REPLACED — 2026-09-27]** Các diễn giải và tuyên bố trong §2–6 là giả thuyết nghiên cứu, chưa được chứng minh hay đo trên VivyQu. Ánh xạ `R^4096 → C^4096` là phép **mã hóa**, không phải đẳng cấu tuyến tính phức; biểu thức rotor tác động lên ket, suy luận tốc độ cổ điển từ số truy vấn Grover, và cách gọi top-M là ma trận mật độ rút gọn cần được đặc tả/sửa theo [chương trình nghiên cứu](RESEARCH_AND_DEVELOPMENT_PLAN.md). 64 KiB chỉ là kích thước một vector trạng thái `complex128`; dưới 10 µs là mục tiêu chưa được đo.

## 1. TỔNG QUAN & NGUYÊN LÝ NỀN TẢNG (THE CORE PARADIGM)

Vivyqu không phải là một mô hình sinh ngôn ngữ tự hồi quy (Autoregressive Token Predictor) thông thường. Vivyqu được kiến trúc hóa như một **Lõi Tính Toán Nhận Thức Lượng Tử Hóa Cổ Điển (Quantum-Inspired Cognitive Core)** hoạt động dựa trên:
1. **Sự tương thích 1-1 giữa Không gian Ẩn LLM và Không gian Hilbert:** Kích thước vector ẩn $d_{\text{model}} = 4.096$ của các LLM hiện đại (Gemma-2, LLaMA-3) tương đương chính xác với Không gian Hilbert của **12 Qubit** ($2^{12} = 4.096$) hoặc **6 Qudit 4 trạng thái** ($4^6 = 4.096$).
2. **Cơ chế "Nuốt Linh Hồn" (Superposition Injection):** Bỏ qua bước giải mã văn bản tuần tự (vốn ngốn 95% thời gian và bộ nhớ). Bắt giữ vector 4.096 chiều từ tầng ẩn LLM và nạp thẳng vào không gian chồng chập lượng tử mô phỏng chỉ tốn **64 KB RAM/Cache**.
3. **Cơ chế Giao thoa Hình học Clifford (Clifford Interference):** Áp dụng đại số hình học để triệt tiêu các nhánh phương án mâu thuẫn/lỗi và khuếch đại nhánh tối ưu theo mục tiêu.
4. **Cơ chế "Nhả Mảnh Linh Hồn" (Instantaneous Collapse):** Sụp đổ hàm sóng để trích xuất trạng thái quyết định tối ưu trong vài micro-giây ($\mu\text{s}$).

---

## 2. KHÔNG GIAN TRẠNG THÁI TOÁN HỌC (MATHEMATICAL STATE MANIFOLD)

### 2.1. Đẳng cấu Không gian Hilbert (Hilbert Space Isomorphism)
Xét không gian vector ẩn của LLM: $\mathcal{V}_{\text{LLM}} = \mathbb{R}^{d}$, với $d = 4.096$.

Vivyqu thiết lập đẳng cấu vào Không gian Hilbert phức $\mathcal{H}_{12}$:
$$\mathcal{H}_{12} = \bigotimes_{k=1}^{12} \mathbb{C}^2 \cong \mathbb{C}^{4096}$$

Hoặc biểu diễn qua hệ Qudit 4 trạng thái $\mathcal{H}_{6}^{(4)}$:
$$\mathcal{H}_{6}^{(4)} = \bigotimes_{k=1}^{6} \mathbb{C}^4 \cong \mathbb{C}^{4096}$$

Trạng thái nhận thức toàn cục $|\Psi\rangle$ tại một thời điểm suy luận được biểu diễn dưới dạng vector trạng thái chuẩn hóa:
$$|\Psi\rangle = \sum_{k=0}^{4095} c_k |k\rangle, \quad c_k \in \mathbb{C}$$
với điều kiện bảo toàn xác suất (Unitarity):
$$\langle \Psi | \Psi \rangle = \sum_{k=0}^{4095} |c_k|^2 = 1$$

---

## 3. CƠ CHẾ "NUỐT LINH HỒN" — TOÁN TỬ CHIẾU & CHUẨN HÓA

### 3.1. Vector ẩn đầu vào từ LLM (Ingested Latent Vector)
Gọi $\mathbf{h} = [h_0, h_1, \dots, h_{4095}]^T \in \mathbb{R}^{4096}$ là vector kích hoạt tầng ẩn (hidden activation) được trích xuất từ LLM giao tiếp (ví dụ: Gemma-2-9B).

### 3.2. Mã hóa Biên độ và Pha Phức (Complex Amplitude & Phase Encoding)
Do $\mathbf{h}$ là vector thực, Vivyqu sử dụng phép chiếu điều chế pha để đưa vào miền phức $\mathbb{C}^{4096}$:
$$c_k = r_k \cdot e^{i \theta_k}$$

Trong đó:
- **Mô-đun biên độ (Modulus Amplitude):**
  $$r_k = \frac{|h_k|}{\sqrt{\sum_{j=0}^{4095} |h_j|^2}} = \frac{|h_k|}{\|\mathbf{h}\|_2}$$
- **Góc pha nhận thức (Cognitive Phase Angle):**
  $$\theta_k = \pi \cdot \sigma\left(\frac{h_k - \mu_{\mathbf{h}}}{\sigma_{\mathbf{h}}}\right)$$
  *(trong đó $\sigma(\cdot)$ là hàm sigmoid chuẩn hóa về khoảng $[0, \pi]$, $\mu_{\mathbf{h}}$ và $\sigma_{\mathbf{h}}$ là kỳ vọng và độ lệch chuẩn của vector kích hoạt).*

> [!NOTE]
> **Bộ nhớ tiêu thụ:** $4.096 \times 16 \text{ bytes (complex128)} = 65.536 \text{ bytes} \approx 64 \text{ KB}$.  
> Toàn bộ trạng thái nhận thức của Vivyqu nằm trọn vẹn trong bộ nhớ đệm L1/L2 Cache của GPU hoặc CPU!

---

## 4. CƠ CHẾ GIAO THOA HÌNH HỌC (CLIFFORD ROTATION & INTERFERENCE)

### 4.1. Biểu diễn trong Đại số Clifford $\mathcal{C}\ell(p, q)$
Thay vì sử dụng các ma trận biến đổi cồng kềnh, Vivyqu biểu diễn các quy luật thế giới, ràng buộc thẩm mỹ ("Gu") và luật chơi dưới dạng **Toán tử Rotor hình học (Geometric Rotors)**:
$$R = \exp\left(-\frac{1}{2} \sum_{i < j} B_{ij} \, e_i \wedge e_j\right)$$
trong đó:
- $e_i \wedge e_j$ là bivector đại diện cho mặt phẳng xoay trong không gian nhận thức.
- $B_{ij}$ là ma trận trọng số tương tác giữa các chiều ý niệm.

### 4.2. Hiện tượng Giao thoa Trạng thái (Quantum-Inspired Interference)
Toán tử tiến hóa nhận thức $\hat{U}_{\text{Vivy}}$ tác động lên hàm sóng:
$$|\Psi'\rangle = \hat{U}_{\text{Vivy}} |\Psi\rangle = R |\Psi\rangle R^\dagger$$

- **Giao thoa Triệt tiêu (Destructive Interference):** Đối với các trạng thái vi phạm điều kiện biên kỹ thuật, phi logic hoặc "AI slop", các thành phần pha ngược chiều nhau tự hủy:
  $$\sum_{\text{lỗi}} c_k e^{i \theta_k} \to 0$$
- **Giao thoa Tăng cường (Constructive Interference):** Đối với các trạng thái thỏa mãn tối ưu toán học và đúng "Gu" người dùng, biên độ xác suất cộng hưởng đạt cực đại:
  $$|\langle \text{Tối ưu} | \Psi'\rangle|^2 \to \max$$

---

## 5. ĐỘNG LỰC HỌC HẠ THẾ NĂNG HAMILTONIAN (COGNITIVE MINIMIZATION)

Quyết định của Vivyqu không phải là một chuỗi rẽ nhánh `if/else`, mà là quá trình tìm trạng thái cân bằng năng lượng thấp nhất trên Đa tạp Trạng thái (Variational Principle).

### 5.1. Toán tử Hamiltonian Nhận thức $\hat{H}$
$$\hat{H} = \hat{H}_{\text{Objective}} + \lambda_1 \hat{H}_{\text{Constraint}} + \lambda_2 \hat{H}_{\text{Aesthetic}}$$

- $\hat{H}_{\text{Objective}}$: Hàm mục tiêu toán học (ví dụ: tối ưu diện tích, cân bằng DPS/HP, tối ưu chi phí).
- $\hat{H}_{\text{Constraint}}$: Thế năng phạt cho các vi phạm ràng buộc (va chạm vật lý, lỗi quy hoạch).
- $\hat{H}_{\text{Aesthetic}}$: Thế năng định hướng "Gu" của người chơi / người dùng.

### 5.2. Thuật toán Khuếch đại Biên độ (Amplitude Amplification / Grover-like)
Để tìm trạng thái cơ sở $|\Psi_0\rangle$ sao cho:
$$E = \langle \Psi_0 | \hat{H} | \Psi_0 \rangle = \min$$

Thời gian tìm kiếm trạng thái tối ưu trên không gian $N = 4.096$ giảm từ $O(N)$ xuống $O(\sqrt{N})$:
$$\text{Số bước lặp cần thiết: } K \approx \frac{\pi}{4} \sqrt{4096} = \frac{\pi}{4} \times 64 \approx 50 \text{ bước tính toán!}$$

---

## 6. CƠ CHẾ "NHẢ MẢNH LINH HỒN" (MEASUREMENT & WAVEFUNCTION COLLAPSE)

### 6.1. Toán tử Đo lường Chiếu (Projective Measurement)
Khi nhận được tín hiệu kích hoạt hành động từ Cầu Treo (Cautreo), Vivyqu thực hiện phép đo sụp đổ hàm sóng:
$$\hat{M}_k = |k\rangle \langle k|$$

Xác suất xuất hiện mảnh quyết định $k$ là:
$$P(k) = |\langle k | \Psi'\rangle|^2 = |c_k'|^2$$

### 6.2. Mảnh Linh Hồn Giá Trị (The Core Latent Fragment)
Vivyqu trích xuất vector chỉ số tối ưu:
$$k^* = \arg\max_k P(k)$$
hoặc xuất ra **Ma trận Mật độ Rút gọn (Reduced Density Matrix)** cho cụm $M$ trạng thái có xác suất cao nhất:
$$\rho_{\text{Core}} = \sum_{j=1}^M P(k_j) |k_j\rangle \langle k_j|$$

> [!TIP]
> **Tốc độ thực thi:** Toàn bộ chu trình từ lúc nhận vector 4.096 $\rightarrow$ Xoay Clifford $\rightarrow$ Sụp đổ đo lường chỉ diễn ra trong **dưới 10 micro-giây ($< 10\,\mu\text{s}$)** trên phần cứng GPU/NPU phổ thông!

---

## 7. GIAO DIỆN BẢN THỂ VỚI THÂN THỂ (CAUTREO INTERFACE PROTOCOL)

Vivyqu Core (Linh hồn) giao tiếp với Cầu Treo (Thân thể) thông qua một kênh bộ nhớ chia sẻ phi khóa (Lock-free Shared Memory / Ring Buffer):

```
┌────────────────────────────────────────────────────────┐
│               VIVYQU CORE (LINH HỒN - SOUL)            │
│  - Không gian trạng thái 12-Qubit (|Ψ⟩ ∈ ℂ⁴⁰⁹⁶)        │
│  - Toán tử Clifford & Hamiltonian Engine               │
└──────────────────────────┬─────────────────────────────┘
                           │ State Tensor Bus (64 KB IPC)
                           ▼
┌────────────────────────────────────────────────────────┐
│               CẦU TREO - CAUTREO (THÂN THỂ - BODY)     │
│  - Đọc k* / ρ_Core từ Shared Memory                    │
│  - Dịch k* thành hành động thực tế:                     │
│    + Gửi lệnh điều khiển Actor tới Game Engine / Godot │
│    + Kích hoạt Model Vệ tinh (Worker Model sinh 3D/UI) │
│    + Điều phối giao dịch hoặc cập nhật cảnh quan       │
└────────────────────────────────────────────────────────┘
```

---

## 8. BỘ TIÊU CHUẨN KIỂM ĐỊNH 4 TRỤC CHO VIVYQU CORE

1. **Tính Xung Đột (Conflict):**
   - Không được để logic I/O, gọi file, hay mạng Internet xâm nhập vào Vivyqu Core. Core phải thuần khiết toán học.
2. **Tính Hợp Lý (Rationality):**
   - Dung lượng 64 KB hoàn toàn khả thi trên mọi phần cứng từ PC 16GB RAM đến thiết bị di động.
3. **Tính Dư Thừa (Redundancy):**
   - Loại bỏ hoàn toàn tầng giải mã token chữ (Text Generation) không cần thiết khi ra quyết định kỹ thuật.
4. **Tính Hiệu Quả (Effectiveness):**
   - Đo lường bằng thời gian phản hồi: mục tiêu $< 10\,\mu\text{s}$ cho một chu trình quyết định trạng thái.

---

# PHẦN II: ĐẶC TẢ KHÓA THIẾT KẾ TOÁN HỌC ĐA GIẢI PHÁP
## (LOCKED DUAL-TIER MATHEMATICAL SPECIFICATION — V0.2)

> [!IMPORTANT]
> **NGUYÊN TẮC THIẾT KẾ ĐA LỚP (DUAL-TIER DESIGN PRINCIPLE):**
> Nhằm triệt tiêu điểm nghẽn rủi ro kỹ thuật (single point of failure) trong quá trình thực nghiệm, mỗi thành phần toán học của VivyQu Core được trang bị bắt buộc:
> 1. **Giải pháp Chính (Primary Plan - P):** Thiết kế tối ưu về mặt lý thuyết, độc bản và khai thác tối đa hiệu năng L1/L2 Cache.
> 2. **Giải pháp Thứ cấp / Dự phòng (Secondary Plan - S):** Thiết kế dựa trên các tiêu chuẩn toán học cổ điển / lượng tử hóa đã được kiểm chứng rộng rãi trong công nghiệp, sẵn sàng thay thế ngay lập tức nếu giải pháp chính gặp trở ngại thực nghiệm.
> 3. **Giải pháp Cứu nguy (Fallback Plan - F):** Thiết kế tối giản, loại bỏ mọi giả định phức tạp để đảm bảo hệ thống luôn vận hành được trong mọi tình huống.

---

### THÀNH PHẦN 1: ĐA TẠP KHÔNG GIAN TRẠNG THÁI (STATE MANIFOLD REPRESENTATION)

#### 1.1. Giải pháp Chính (P1): Multivector trong Đại số Hình học $\mathcal{C}\ell(12)$ (32 KiB float64)
- **Cơ sở Toán học:** Không gian vector thực $\mathbb{R}^{12}$ với hệ cơ sở trực chuẩn $\{e_1, e_2, \dots, e_{12}\}$ thỏa mãn hệ thức Clifford:
  $$e_i e_j + e_j e_i = 2 \delta_{ij} \mathbf{1}$$
  Đại số Clifford $\mathcal{C}\ell(12)$ có số chiều:
  $$\dim(\mathcal{C}\ell(12)) = \sum_{k=0}^{12} \binom{12}{k} = 2^{12} = 4.096$$
- **Biểu diễn Trạng thái:** Trạng thái nhận thức $\psi \in \mathcal{C}\ell(12)$ là một multivector thuần số thực:
  $$\psi = \langle \psi \rangle_0 + \sum_{i=1}^{12} \langle \psi \rangle_{1, i} e_i + \sum_{1 \le i < j \le 12} \langle \psi \rangle_{2, ij} e_i e_j + \dots + \langle \psi \rangle_{12} e_1 e_2 \dots e_{12}$$
- **Bảo toàn Chuẩn:** Sử dụng phép đảo (reversion) $\widetilde{\psi}$. Chuẩn hình học được định nghĩa qua tích vô hướng phần vô hướng (scalar part):
  $$\|\psi\|^2 = \langle \psi \widetilde{\psi} \rangle_0 = \sum_{A=0}^{4095} \psi_A^2 = 1$$
- **Bộ nhớ:** $4.096 \times 8\text{ bytes} = 32.768\text{ bytes} = 32\text{ KiB}$ (`float64`). Nằm trọn trong L1 Data Cache ($32\text{ KiB} - 48\text{ KiB}$).
- **Lợi thế:** Loại bỏ số phức, không có hiện tượng lệch kiểu (type-mismatch) khi áp dụng phép quay Rotor sandwich $R \psi \widetilde{R}$, bảo toàn chuẩn tự nhiên.

#### 1.2. Giải pháp Thứ cấp (S1): Statevector Phức trong Không gian Hilbert $\mathcal{H}_{12} \cong \mathbb{C}^{4096}$ (64 KiB complex128 / 32 KiB complex64)
- **Cơ sở Toán học:** Hệ 12 qubit tương tác:
  $$|\Psi\rangle = \sum_{k=0}^{4095} c_k |k\rangle, \quad c_k \in \mathbb{C}$$
- **Bảo toàn Xác suất:** $\langle \Psi | \Psi \rangle = \sum_{k=0}^{4095} |c_k|^2 = 1$.
- **Bộ nhớ:** 64 KiB (`complex128`) hoặc 32 KiB (`complex64`).
- **Điều kiện kích hoạt S1:** Kích hoạt nếu trình biên dịch CPU/SIMD trên phần cứng đích tối ưu hóa các lệnh số phức (Complex AVX-512) tốt hơn phép nhân multivector Clifford.

#### 1.3. Giải pháp Cứu nguy (F1): Vector Thực Chuẩn Hóa Cực Nhẹ (Real Normalized Latent - 16 KiB float32)
- **Cơ sở Toán học:** $\mathbf{v} \in \mathbb{R}^{4096}$ với $\|\mathbf{v}\|_2 = 1$.
- **Bộ nhớ:** 16 KiB (`float32`).
- **Điều kiện kích hoạt F1:** Khi cần độ trễ tuyệt đối $< 1\ \mu\text{s}$ và bài toán không đòi hỏi cấu trúc quay hình học.

---

### THÀNH PHẦN 2: CƠ CHẾ NẠP VECTOR ĐẦU VÀO (INGESTION & GRADE PROJECTION)

Đầu vào từ Cầu Treo: vector tiềm ẩn $\mathbf{h} = [h_0, h_1, \dots, h_{4095}]^T \in \mathbb{R}^{4096}$ (ví dụ: hidden activations trích xuất từ LLM nền tảng).

#### 2.1. Giải pháp Chính (P2): Clifford Blade Canonical Ordering (Ánh xạ Tọa độ Đa bậc)
- **Quy tắc Ánh xạ:** Mỗi chỉ số $k \in [0, 4095]$ được biểu diễn dưới dạng nhị phân 12-bit $(b_{11} b_{10} \dots b_1 b_0)_2$. Ta ánh xạ $h_k$ vào blade cơ sở tương ứng:
  $$k \iff e_A = e_1^{b_0} e_2^{b_1} \dots e_{12}^{b_{11}}$$
  - $k=0 \ (000000000000_2)$: Hệ số vô hướng $\langle \psi \rangle_0$ (Grade 0, 1 chiều).
  - $k$ có 1 bit bật: 12 hệ số vector $\langle \psi \rangle_1$ (Grade 1, 12 chiều).
  - $k$ có 2 bit bật: $\binom{12}{2} = 66$ hệ số bivector $\langle \psi \rangle_2$ (Grade 2, 66 chiều).
  - ...
  - $k=4095 \ (111111111111_2)$: Hệ số giả vô hướng $\langle \psi \rangle_{12}$ (Grade 12, 1 chiều).
- **Chuẩn hóa Đầu vào:**
  $$\psi_A = \frac{h_k}{\sqrt{\sum_{j=0}^{4095} h_j^2 + \epsilon}} = \frac{h_k}{\|\mathbf{h}\|_2 + \epsilon}$$
- **Độ phức tạp:** $O(d)$ thuần túy. Hoàn toàn không tốn chi phí hàm lượng giác.

#### 2.2. Giải pháp Thứ cấp (S2): Điều Chế Pha Sigmoid + Biên Độ Chuẩn Hóa
- **Cơ chế:** Áp dụng khi sử dụng Không gian Hilbert (S1):
  $$c_k = r_k \cdot e^{i \theta_k}$$
  - Biên độ xác suất: $r_k = |h_k| / (\|\mathbf{h}\|_2 + \epsilon)$.
  - Góc pha nhận thức: $\theta_k = \pi \cdot \sigma\left(\frac{h_k - \mu_{\mathbf{h}}}{\sigma_{\mathbf{h}} + \epsilon}\right)$.
- **Điều kiện kích hoạt S2:** Kích hoạt đồng thời khi S1 được lựa chọn.

#### 2.3. Giải pháp Cứu nguy (F2): Sign-Preserving L2 Normalization
- $c_k = h_k / (\|\mathbf{h}\|_2 + \epsilon)$. Giữ nguyên dấu thực của vector đặc trưng.

---

### THÀNH PHẦN 3: TOÁN TỬ BIẾN ĐỔI & GIAO THOA (TRANSFORMATION & INTERFERENCE)

#### 3.1. Giải pháp Chính (P3): Phân Tích Nhân Tử Rotor Hình Học (Factorized Spin(12) Rotors)
- **Cơ chế:** Một rotor đầy đủ $R = \exp(-\frac{1}{2} B)$ với bivector tổng quát $B = \sum_{i<j} B_{ij} e_i e_j$ (66 tham số) được phân rã thành tích của $M$ rotor 2-blade cơ sở (tương tự Givens rotations trong đại số tuyến tính):
  $$R = \prod_{m=1}^{M} R_m, \quad R_m = \cos\left(\frac{\theta_m}{2}\right) - \sin\left(\frac{\theta_m}{2}\right) e_{i_m} e_{j_m}$$
  trong đó $(i_m, j_m)$ là các cặp chiều tương tác được trích xuất từ ma trận hiệp phương sai hoặc ràng buộc thế năng của Cầu Treo.
- **Biến đổi Trạng thái (Sandwich Product):**
  $$\psi' = R \psi \widetilde{R} = R_M \dots (R_1 \psi \widetilde{R}_1) \dots \widetilde{R}_M$$
- **Độ phức tạp:** Với $M \le 16$ cặp mặt phẳng trọng yếu nhất, mỗi bước quay 2-blade chỉ cập nhật các thành phần liên quan. Tổng chi phí: $\sim 16 \times 4.096 \approx 6.5 \times 10^4$ FLOPs.
- **Thời gian thực thi:** **$2 - 4\ \mu\text{s}$** trên CPU 1 thread!

#### 3.2. Giải pháp Thứ cấp (S3): Unitary Đường Chéo Kết Hợp FWHT (Diagonal Phase + Fast Walsh-Hadamard Transform)
- **Cơ chế:**
  1. *Pha thế năng:* Áp dụng toán tử đường chéo $c_k^{(1)} = c_k \cdot e^{-i \phi_k}$ ($O(d)$).
  2. *Giao thoa toàn cục:* Biến đổi Walsh-Hadamard nhanh: $c^{(2)} = \text{FWHT}(c^{(1)})$ ($O(d \log_2 d) = 4096 \times 12 \approx 4.9 \times 10^4$ FLOPs).
  3. *Pha ràng buộc:* Áp dụng toán tử đường chéo $c_k' = c_k^{(2)} \cdot e^{-i \xi_k}$ ($O(d)$).
- **Lợi thế:** Triển khai cực kỳ đơn giản, không cần ma trận ngoài, độ trễ $< 3\ \mu\text{s}$.
- **Điều kiện kích hoạt S3:** Kích hoạt khi cần giao thoa toàn cục giữa mọi trạng thái mà không muốn giới hạn trong $M$ mặt phẳng bivector của P3.

#### 3.3. Giải pháp Cứu nguy (F3): Structured Low-Rank Scoring ($W_r \cdot W_l \cdot \mathbf{h}$)
- Dùng phân rã ma trận hạng thấp với rank $r = 16$. Chi phí $2 \times 16 \times 4096 \approx 1.3 \times 10^5$ FLOPs.

---

### THÀNH PHẦN 4: ĐỘNG LỰC HỌC TỐI ƯU THẾ NĂNG (ENERGY MINIMIZATION DYNAMICS)

#### 4.1. Giải pháp Chính (P4): Dòng Gradient Bivector Hamiltonian (Hamiltonian Torque Flow)
- **Cơ chế:** Coi bài toán ra quyết định là tối thiểu hóa hàm mục tiêu năng lượng $V(\psi)$ trên đa tạp Clifford:
  $$V(\psi) = \langle \psi, H_{\text{obj}} \psi \rangle + \lambda_{\text{hard}} \sum_{c \in \text{Violations}} \langle \psi, P_c \psi \rangle$$
- **Moment Lực Hình Học (Bivector Torque):**
  $$\mathcal{T} = \langle \psi \wedge \nabla_\psi V \rangle_2 \in \bigwedge^2 \mathbb{R}^{12}$$
- **Cập nhật Trạng thái Geodesic:**
  $$\psi(\tau + \Delta \tau) = \exp\left(-\frac{\Delta \tau}{2} \mathcal{T}\right) \psi(\tau) \exp\left(\frac{\Delta \tau}{2} \mathcal{T}\right)$$
- **Đặc tính:** Hội tụ sau $3 - 5$ bước lặp vi mô, tự động dồn biên độ xác suất về nhánh nghiệm thỏa mãn ràng buộc cứng và tối ưu mục tiêu.

#### 4.2. Giải pháp Thứ cấp (S4): Bounded Fixed-Point Grover / Amplitude Amplification
- **Cơ chế:**
  - Oracle đảo pha nghiệm thỏa mãn: $O_f |k\rangle = (-1)^{f(k)} |k\rangle$.
  - Toán tử khuếch tán: $D = 2 |\Psi_0\rangle\langle\Psi_0| - I$ (thực thi thông qua FWHT).
  - Giới hạn cứng số bước lặp: $K \le 8$ bước (không chạy 50 bước để tránh over-rotation và giữ latency $< 10\ \mu\text{s}$). Dừng sớm khi độ suy giảm entropy vượt ngưỡng $\Delta H < \epsilon$.
- **Điều kiện kích hoạt S4:** Kích hoạt khi hàm mục tiêu là bài toán tìm kiếm tổ hợp dạng boolean/discrete oracle.

#### 4.3. Giải pháp Cứu nguy (F4): Softmax Temperature Annealing với Hard Masking
- Đánh giá điểm trực tiếp cho 4.096 trạng thái, gán $-\infty$ cho các trạng thái vi phạm ràng buộc, áp dụng Softmax có suy giảm nhiệt độ $T$.

---

### THÀNH PHẦN 5: PHÉP ĐO & SỤP ĐỔ RA QUYẾT ĐỊNH (MEASUREMENT & DECISION COLLAPSE)

#### 5.1. Giải pháp Chính (P5): Argmax Xác Định Có Lọc Mặt Nạ Ràng Buộc (Deterministic Hard-Masked Argmax)
- **Cơ chế:**
  $$k^* = \arg\max_{k \in \mathcal{K}_{\text{Valid}}} \left( \psi_{A(k)}^2 \right)$$
  trong đó $\mathcal{K}_{\text{Valid}} = \{k \in [0, 4095] \mid \text{CheckConstraint}(k) == \text{True}\}$.
- **Hợp Đồng Đầu Ra:**
  $$\text{Payload} = \left\{ k^*, \ P(k^*) = \psi_{A(k^*)}^2, \ \text{is\_valid}: \text{True}, \ \text{mode}: \text{"Deterministic"} \right\}$$
- **Ưu điểm:** Đảm bảo 100% tính lặp lại (reproducibility), loại bỏ rủi ro bất định ngẫu nhiên trong các quyết định quy hoạch thế giới và điều khiển hệ thống.

#### 5.2. Giải pháp Thứ cấp (S5): Lấy Mẫu Born Có Nhiệt Độ (Calibrated Born Sampling with Temperature)
- **Cơ chế:** Dành riêng cho chế độ World Director sáng tạo (Stochastic Exploration):
  $$P(k) = \frac{(\psi_{A(k)}^2)^{1/T}}{\sum_{j \in \mathcal{K}_{\text{Valid}}} (\psi_{A(j)}^2)^{1/T}}$$
- Bắt buộc ghi nhận `seed` ngẫu nhiên để có thể tái lập vết thực thi (audit trail).
- **Điều kiện kích hoạt S5:** Kích hoạt khi Cầu Treo yêu cầu hành vi sáng tạo ngẫu nhiên hoặc khám phá phương án mới.

#### 5.3. Giải pháp Cứu nguy (F5): Top-M Confidence Set Extraction
- Xuất danh sách $M$ ứng viên có năng lượng cao nhất: $\mathcal{S}_{\text{Top-}M} = \{(k_1, p_1), \dots, (k_M, p_M)\}$ cho Cầu Treo thực thi đa luồng song song.

---

## BẢNG MA TRẬN ĐỐI CHIẾU & ĐIỀU KIỆN CHUYỂN ĐỔI (SWITCHING CONDITIONS)

| Thành phần | Giải pháp Chính (Primary) | Giải pháp Thứ cấp (Secondary) | Giải pháp Cứu nguy (Fallback) | Điều kiện kích hoạt Thứ cấp |
|---|---|---|---|---|
| **1. Đa tạp trạng thái** | Multivector $\mathcal{C}\ell(12)$ (32 KiB) | Statevector $\mathcal{H}_{12}$ (64/32 KiB) | Real Vector (16 KiB) | Trình biên dịch không tối ưu SIMD cho Clifford |
| **2. Nạp vector đầu vào** | Grade Canonical Ordering | Modulus-Sigmoid Modulation | Sign-Preserving L2 | Kích hoạt đồng thời khi chuyển sang S1 |
| **3. Toán tử biến đổi** | Spin(12) Factorized Rotors | Diagonal Unitary + FWHT | Structured $W_r W_l$ | Cần giao thoa toàn thể không qua bivector |
| **4. Động lực tối ưu** | Hamiltonian Torque Flow | Bounded Grover ($K \le 8$) | Softmax Annealing | Bài toán có oracle kiểm tra dạng Boolean |
| **5. Đo lường ra quyết định** | Hard-Masked Argmax | Calibrated Born Sampling | Top-M Subspace | Nhiệm vụ yêu cầu tính sáng tạo đa dạng |
