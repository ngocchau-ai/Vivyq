# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# ĐẶC TẢ THỰC NGHIỆM E0: XÁC LẬP BÀI TOÁN CHUẨN, ORACLE & ĐÓNG BĂNG BASELINE A

**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Mã thực nghiệm:** EXP-E0-BENCHMARK-v1.0  
**Ngày ban hành:** 2026-09-27  
**Tác giả kiến trúc:** Ngọc Châu & Antigravity  
**Vai trò:** Thiết lập môi trường thực nghiệm chuẩn mực đầu tiên (E0), xác lập hàm mục tiêu toán học, xây dựng Oracle tham chiếu, tập dữ liệu held-out cố định hạt giống (fixed seed), và đóng băng Golden Baseline A theo nguyên tắc đa giải pháp.

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Khởi tạo tài liệu đặc tả chi tiết thực nghiệm E0. Thiết lập: (1) Bài toán tham số không gian 4.096 chiều (Parametric Spatial Optimization), (2) Hệ thống Oracle 2 tầng (Primary Geometric Ground-Truth vs. Secondary Quadratic Solver), (3) Bộ dữ liệu 10.000 mẫu held-out với quy chuẩn phân chia 70/15/15 và seed cố định, (4) Các biến thể Baseline A (A0, A1, A2, A3) và giao thức đóng băng cryptographic hash (SHA-256), (5) Bộ chỉ số định lượng Regret, Validity Rate, Latency p99 và Cache Footprint.

---

## 1. MỤC TIÊU CỐT LÕI CỦA THỰC NGHIỆM E0

Theo nguyên tắc nghiên cứu nghiêm ngặt của dự án: **"Không có bài toán chuẩn và baseline đóng băng thì không có quyền phát biểu về nhận thức hay ưu thế lượng tử"**.

Thực nghiệm E0 được thiết kế để giải quyết 3 nhiệm vụ sống còn:
1. **Xác lập Bài toán Thực tế Đầu tiên (The First Concrete Task):** Chọn bài toán **Tối ưu hóa Tham số Không gian Đa chiều (Parametric Spatial-Architectural Optimization)** với không gian quyết định rời rạc gồm đúng $4.096$ trạng thái cấu hình.
2. **Xây dựng Oracle Chân Lý (Ground Truth Reference):** Cung cấp lời giải tối ưu tuyệt đối để đo lường độ hối tiếc (Regret) của mọi thuật toán.
3. **Đóng Băng Golden Baseline A (Classical Frozen Baseline):** Xác lập ngưỡng hiệu năng và độ trễ của thuật toán cổ điển ($W \cdot \mathbf{h}$). Mọi nhánh lượng tử (B, C, D, E) sau này bắt buộc phải chứng minh vượt qua mốc này.

---

## 2. ĐẶC TẢ BÀI TOÁN THAM SỐ KHÔNG GIAN 4.096 CHIỀU

### 2.1. Miền Bài Toán: Đạo Diễn Thế Giới & Quy Hoạch Không Gian Tham Số
- **Bối cảnh:** Hệ thống nhận một vector ngữ cảnh $4.096$ chiều $\mathbf{h} \in \mathbb{R}^{4096}$ từ Cầu Treo (tổng hợp từ yêu cầu của người dùng, địa hình và quy luật thế giới).
- **Không gian Quyết định:** Tập hợp $N = 4.096$ trạng thái cấu hình không gian $\mathcal{S} = \{0, 1, \dots, 4095\}$.
  - Mỗi chỉ số $k \in [0, 4095]$ đại diện cho một bộ tham số kiến trúc/vật lý hoàn chỉnh (ví dụ: tọa độ cụm công trình, phân bổ mật độ, phân luồng giao thông, cân bằng tài nguyên).

### 2.2. Hàm Mục Tiêu Năng Lượng Hình Học (Objective Energy Landscape)
Năng lượng của trạng thái $k$ đối với ngữ cảnh đầu vào $\mathbf{h}$ được xác định bởi trường thế năng:
$$V(k \mid \mathbf{h}) = V_{\text{Alignment}}(k, \mathbf{h}) + \lambda_{\text{Smooth}} V_{\text{Topology}}(k) + \lambda_{\text{Aesthetic}} V_{\text{Style}}(k)$$

Trong đó:
1. **$V_{\text{Alignment}}(k, \mathbf{h})$:** Độ lệch giữa đặc trưng trạng thái $k$ và vector mục tiêu $\mathbf{h}$:
   $$V_{\text{Alignment}}(k, \mathbf{h}) = \|\mathbf{u}_k - \mathbf{h}\|_Q^2 = (\mathbf{u}_k - \mathbf{h})^T Q (\mathbf{u}_k - \mathbf{h})$$
   với $\mathbf{u}_k$ là vector đặc trưng nội tại của cấu hình $k$, và $Q \in \mathbb{R}^{4096 \times 4096}$ là ma trận trọng số tương quan bán xác định dương (Positive Semi-Definite).
2. **$V_{\text{Topology}}(k)$:** Chi phí phân mảnh hình học hoặc xung đột cấu trúc.
3. **$V_{\text{Style}}(k)$:** Độ lệch thẩm mỹ/phong cách thiết kế được chỉ định từ Cầu Treo.

### 2.3. Hệ Thống Ràng Buộc Cứng (Hard Constraints)
Mỗi trạng thái $k$ được kiểm tra qua tập $C$ ràng buộc kỹ thuật bất khả xâm phạm:
$$\text{ConstraintValid}(k) = \bigwedge_{c=1}^{C} \left( g_c(k) \le 0 \right)$$
- Các ràng buộc bao gồm: Không va chạm kết cấu, không vượt quá giới hạn ngân sách năng lượng, thỏa mãn quy chuẩn thoát hiểm/kết nối đồ thị.
- Tập hợp các ứng viên hợp lệ: $\mathcal{K}_{\text{Valid}} \subseteq [0, 4095]$.
- Tỷ lệ ứng viên hợp lệ trung bình trong mỗi bài toán được khống chế ở mức $\sim 10\% - 30\%$ (khoảng $400 - 1.200$ ứng viên hợp lệ trên tổng số $4.096$).

---

## 3. THIẾT KẾ ORACLE THAM CHIẾU ĐA TẦNG (DUAL-TIER ORACLE)

Để đảm bảo tính khách quan và có kế hoạch dự phòng khi đánh giá:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                HỆ THỐNG ORACLE THAM CHIẾU                              │
├─────────────────────────────────────────────────┬──────────────────────────────────────┤
│ KẾ HOẠCH CHÍNH (ORACLE-P): QUÉT TOÀN BỘ (BRUTE) │ KẾ HOẠCH THỨ CẤP (ORACLE-S): QP/MILP │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ - Tính toán song song trên GPU toàn bộ 4.096 điểm│ - Bộ giải quy hoạch toán học chuẩn   │
│ - Lọc chính xác 100% ràng buộc cứng             │   (Gurobi / OSQP / SciPy)            │
│ - k* = argmin V(k | h)                          │ - Dùng làm đối chứng chéo sai số     │
│ - Độ chính xác: Tuyệt đối 100%                  │ - Độ chính xác: xấp xỉ liên tục      │
└─────────────────────────────────────────────────┴──────────────────────────────────────┘
```

### 3.1. Kế Hoạch Chính (Oracle-P): Exhaustive Brute-Force Evaluator
- Do không gian chỉ có $4.096$ điểm rời rạc, Oracle chính được xây dựng bằng thuật toán **Quét vét cạn song song trên CUDA/C++**:
  $$k_{\text{oracle}} = \arg\min_{k \in \mathcal{K}_{\text{Valid}}} V(k \mid \mathbf{h})$$
- **Tính chuẩn xác:** Đảm bảo $100\%$ tìm ra nghiệm toàn cục (Global Optimum), không bị bẫy cực tiểu địa phương.
- **Thời gian chạy của Oracle:** $\approx 5\text{ ms}$ trên GPU / $40\text{ ms}$ trên CPU cho 1 mẫu (chỉ dùng trong môi trường offline để dán nhãn ground-truth, không chạy runtime).

### 3.2. Kế Hoạch Thứ Cấp (Oracle-S): Continuous Quadratic Programming (QP Solver)
- Nới lỏng không gian rời rạc thành đa tạp liên tục, giải bằng bộ giải quy hoạch toàn phương lồi lồi (OSQP / Gurobi), sau đó chiếu (project) về điểm lưới rời rạc $4.096$ gần nhất.
- *Vai trò:* Dùng làm đối chứng chéo để phát hiện lỗi tính toán hoặc thiên kiến dữ liệu trong Oracle-P.

---

## 4. BỘ DỮ LIỆU CHUẨN & PHÂN CHIA HELD-OUT (DATASET SPECIFICATION)

Nhằm đảm bảo tính tái lập (reproducibility) tuyệt đối trên toàn thế giới, bộ dữ liệu thực nghiệm được cố định hạt giống (fixed seed) và lưu trữ dưới dạng binary tensors:

### 4.1. Quy Cách Sinh Dữ Liệu
- **Quy mô:** $N_{\text{total}} = 10.000$ mẫu bài toán độc lập.
- **Hạt giống toàn cục (Global Seeds):**
  - Sinh vector ngữ cảnh: `SEED_LATENT = 20260927`
  - Sinh ma trận thế năng và trọng số: `SEED_LANDSCAPE = 42`
  - Phân chia tập dữ liệu: `SEED_SPLIT = 1337`
- **Đặc tính Vector $\mathbf{h}$:**
  - $\mathbf{h} \sim \mathcal{N}(\boldsymbol{\mu}, \Sigma)$ được lấy mẫu từ phân phối chuẩn đa biến $4.096$ chiều, mô phỏng đúng phân bố kích hoạt tầng ẩn của Gemma-2-9B / LLaMA-3-8B.
  - Tích hợp thêm $5\%$ mẫu dị biệt (Outliers) và $5\%$ mẫu tiệm cận biên ràng buộc (Adversarial edge-cases) để thử thách độ bền vững của thuật toán.

### 4.2. Phân Chia Tập Dữ Liệu (Split Ratios)
- **Tập Huấn luyện (Train Set — 70%):** $7.000$ mẫu (dành riêng cho việc học ma trận $W$ của Baseline A2 và huấn luyện Neural Operator của Nhánh D).
- **Tập Thẩm định (Validation Set — 15%):** $1.500$ mẫu (dùng để tinh chỉnh siêu tham số và đóng băng mô hình).
- **Tập Kiểm định Độc lập (Held-out Test Set — 15%):** $1.500$ mẫu **bất khả xâm phạm**. Tuyệt đối không được sử dụng trong quá trình huấn luyện hay tinh chỉnh. Mọi chỉ số công bố phải đo lường trên tập này.

---

## 5. HỆ THỐNG BASELINE A VÀ GIAO THỨC ĐÓNG BĂNG (GOLDEN BASELINE PROTOCOL)

Hệ thống Baseline A gồm 4 cấp độ đối chứng:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              HỆ THỐNG BASELINE A (CỔ ĐIỂN)                             │
├─────────────────────┬──────────────────────────────────────────────────────────────────┤
│ MÃ BASELINE         │ NGUYÊN LÝ HOẠT ĐỘNG                                              │
├─────────────────────┼──────────────────────────────────────────────────────────────────┤
│ A0 (Random Valid)   │ Lấy mẫu ngẫu nhiên đồng đều trong tập hợp lệ K_Valid             │
│ A1 (Exhaustive Top) │ Quét tuyến tính đơn giản trên tích vô hướng thô <u_k, h>         │
│ A2 (Linear Scorer)  │ [CHỦ LỰC] Hồi quy s = W · h + b, lọc ràng buộc cứng, argmax      │
│ A3 (Mini-MLP Scorer)│ [THỨ CẤP] Mạng MLP 1 tầng ẩn cực nhẹ (4096 → 64 → 4096)          │
└─────────────────────┴──────────────────────────────────────────────────────────────────┘
```

### 5.1. Chi Tiết Baseline A2 (Chủ Lực Bắt Buộc Vượt Qua)
- **Huấn luyện:** Học ma trận trọng số $W \in \mathbb{R}^{4096 \times 4096}$ (hoặc phân rã rank thấp $W_r W_l$) trên $7.000$ mẫu Train bằng hồi quy Ridge Regression với hàm phạt $L_2$:
  $$\min_W \sum_{i=1}^{7000} \|W \mathbf{h}^{(i)} - \mathbf{y}^{(i)}\|_2^2 + \alpha \|W\|_F^2$$
  với $\mathbf{y}^{(i)}$ là vector điểm số nghịch đảo năng lượng của Oracle.
- **Inference Runtime:**
  1. `score = W @ h` ($O(d)$ hoặc $O(r \cdot d)$).
  2. Áp dụng mặt nạ: `score[~constraint_mask] = -INFINITY`.
  3. $k^* = \arg\max(\text{score})$.
- **Thời gian thực thi:** **$< 1\ \mu\text{s}$** trên CPU (với rank 16) hoặc $\sim 8\ \mu\text{s}$ với ma trận đầy đủ có AVX-512.

### 5.2. Giao Thức Đóng Băng Khắt Khe (Cryptographic Freezing Protocol)
Trước khi khởi chạy bất kỳ thực nghiệm nào của các Nhánh B, C, D, E:
1. Huấn luyện hoàn tất Baseline A2 trên Train Set.
2. Đo lường chỉ số trên Held-out Test Set.
3. Xuất file trọng số `baseline_a2_weights.bin` và file dự đoán `baseline_a2_test_predictions.json`.
4. **Tạo mã băm SHA-256:**
   ```bash
   sha256sum baseline_a2_weights.bin > BASELINE_A2_FREEZE.sha256
   sha256sum baseline_a2_test_predictions.json >> BASELINE_A2_FREEZE.sha256
   ```
5. Khóa vĩnh viễn file kết quả. Nghiêm cấm điều chỉnh lại trọng số của Baseline A2 sau khi đã nhìn thấy kết quả của các nhánh khác.

---

## 6. BỘ CHỈ SỐ KIỂM ĐỊNH ĐỊNH LƯỢNG (EVALUATION METRICS)

Mọi thuật toán tham gia thử nghiệm bắt buộc phải báo cáo đầy đủ 4 trục chỉ số sau:

### 6.1. Độ Hối Tiếc Chuẩn Hóa (Normalized Decision Regret — $\mathcal{R}$)
Đo khoảng cách giữa nghiệm do thuật toán chọn ($k^*$) và nghiệm tối ưu tuyệt đối của Oracle ($k_{\text{oracle}}$):
$$\mathcal{R} = \frac{V(k^* \mid \mathbf{h}) - V(k_{\text{oracle}} \mid \mathbf{h})}{V_{\text{worst}}(\mathbf{h}) - V(k_{\text{oracle}} \mid \mathbf{h})} \times 100\%$$
- **Ý nghĩa:** $\mathcal{R} = 0\%$ nghĩa là đạt nghiệm hoàn hảo như Oracle. $\mathcal{R} = 100\%$ nghĩa là chọn trúng phương án tồi tệ nhất.
- **Mục tiêu chấp nhận:**
  - Baseline A2 phải đạt: $\mathcal{R}_{\text{Baseline}} \le 12.0\%$.
  - Nhánh B / C muốn thắng phải đạt: $\mathcal{R} < \mathcal{R}_{\text{Baseline}} - 2.5\%$ với kiểm định ý nghĩa thống kê $p$-value $< 0.01$.

### 6.2. Tỷ Lệ Thỏa Mãn Ràng Buộc (Validity Rate — $\mathcal{V}$)
$$\mathcal{V} = \frac{1}{N_{\text{test}}} \sum_{i=1}^{N_{\text{test}}} \mathbb{I}\left(k^{*(i)} \in \mathcal{K}_{\text{Valid}}^{(i)}\right) \times 100\%$$
- **Ngưỡng bắt buộc:** **$\mathcal{V} = 100.0\%$**. Mọi quyết định trả về bắt buộc phải hợp lệ. Nếu thuật toán sinh ra dù chỉ $0.1\%$ quyết định vi phạm ràng buộc cứng $\to$ **Đánh trượt ngay lập tức (FAIL)**.

### 6.3. Hồ Sơ Độ Trễ Vi Mô (Latency Profile — Core Only & End-to-End)
Đo bằng đồng hồ phần cứng độ phân giải cao (`__rdtsc` / `QueryPerformanceCounter`):
- **Core-Only Latency:** Tính từ lúc vector nằm trong L1 Cache đến khi ghi xong $k^*$ vào Output Frame:
  - Báo cáo: p50, p90, p95, p99 và độ lệch chuẩn $\sigma_t$.
  - **Mục tiêu:** Core-only p99 $< 10.0\ \mu\text{s}$ trên phần cứng CPU chuẩn (Intel i7/AMD Ryzen phổ thông, 1 thread cố định tần số).
- **End-to-End Latency:** Tính từ khi Cầu Treo gửi qua Shared Memory đến khi nhận lại kết quả:
  - **Mục tiêu:** End-to-end p99 $< 15.0\ \mu\text{s}$.

### 6.4. Dấu Chân Bộ Nhớ & Cache Footprint
- Peak Working-Set: Đo lượng RAM đỉnh trong quá trình chạy.
- Đo số lần trượt bộ nhớ đệm L1/L2 (L1 Data Cache Misses) qua `perf` / Intel VTune.
- **Mục tiêu:** L1-D Miss Rate $< 2.0\%$.

---

## 7. MA TRẬN TIÊU CHÍ NGHIỆM THU E0 (ACCEPTANCE CRITERIA)

| Tiêu Chí Kiểm Tra | Baseline A0 (Random) | Baseline A2 (Linear W·h) | Ngưỡng PASS Thực Nghiệm E0 |
|---|---|---|---|
| **Regret Trung Bình ($\mathcal{R}$)** | $\sim 50\% - 70\%$ | **$\le 12.0\%$** | Baseline A2 đạt $\le 12.0\%$ trên Held-out |
| **Tỷ Lệ Hợp Lệ ($\mathcal{V}$)** | $100\%$ (do lọc) | **$100.0\%$** | Đạt chính xác $100.0\%$ |
| **Độ Trễ Core-only p99** | $< 0.1\ \mu\text{s}$ | **$< 2.0\ \mu\text{s}$** | p99 $< 5.0\ \mu\text{s}$ |
| **Tính Lặp Lại (Determinism)** | $0\%$ | **$100.0\%$** | Chạy 10 lần cho cùng 1 kết quả 100% |
| **Trạng Thái Khóa (Freeze)** | Không áp dụng | **Bắt buộc SHA-256** | File checksum được commit vào Git |

---

## 8. KẾ HOẠCH HÀNH ĐỘNG TRIỂN KHAI E0 (SPRINT PLAN — 1 TUẦN)

- **Ngày 1:** Viết script sinh dữ liệu 10.000 mẫu (`generate_dataset.py`), cố định seeds, xuất ra thư mục dữ liệu chuẩn `data/e0_benchmark/`.
- **Ngày 2:** Hiện thực hóa Oracle-P trên C++/CUDA và chạy dán nhãn toàn bộ 10.000 mẫu.
- **Ngày 3:** Huấn luyện Baseline A2 trên 7.000 mẫu Train, lưu trọng số.
- **Ngày 4:** Đánh giá Baseline A2 trên 1.500 mẫu Test, đo đạc p50/p95/p99 bằng harness C++.
- **Ngày 5:** Tính toán SHA-256 checksum, đóng băng toàn bộ kết quả, xuất báo cáo `E0_BASELINE_REPORT.md` và sẵn sàng mở cổng thực nghiệm cho Nhánh B/C.
