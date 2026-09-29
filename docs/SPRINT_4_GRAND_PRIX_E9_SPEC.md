> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# ĐẶC TẢ KÍCH HOẠT SPRINT 4: QUYẾT ĐẤU NĂM NHÁNH (GRAND PRIX E9)
**Dự Án:** VivyQu — Động cơ Nhận thức Lượng tử & Ra Quyết Định Thời Gian Thực  
**Phiên Bản:** 1.0.1 (Post-Audit Revision)  
**Ngày Kích Hoạt:** 2026-09-27  
**Phạm Vi:** Huấn luyện, Tối ưu hóa và Quyết đấu Trực tiếp giữa Nhánh A, Nhánh B và Nhánh C  

---

## LỊCH SỬ THAY ĐỔI (AUDIT TRAIL)
| Phiên Bản | Thời Gian (UTC+7) | Người / Agent Thực Hiện | Nội Dung & Lý Do Thay Đổi |
|:---:|:---:|:---:|:---|
| **v1.0.1** | 2026-09-27 18:05 | Antigravity AI Assistant | **Đính chính & Đồng bộ theo Technical Audit (chatGPT_review.md):**<br>1. Cô lập đặc tả toán học thuần lý thuyết của Nhánh B (Hilbert Phase/Born) và Nhánh C (Weighted energy); đối chiếu với implementation thực tế trong `train_branches_b_c.py` (FWHT+Ridge và Rotor+Ridge Readout).<br>2. Ghi nhận mâu thuẫn P0 giữa E9 Python readout và `collapse.cpp` (amplitude-squared argmax).<br>3. Bổ sung các tiêu chí nghiệm thu E9-v2: verify SHA-256 test set, khóa Little-Endian mask bit-order, đo trực tiếp latency binary. |
| **v1.0.0** | 2026-09-27 16:35 | Antigravity AI Assistant | Khởi tạo đặc tả Sprint 4 theo VIVY_MASTER_BUILD_PLAN.md: xác lập kiến trúc toán học cho Nhánh B (Hilbert Statevector) và Nhánh C (Clifford Rotors), quy trình tối ưu hóa trên tập E0 10.000 mẫu và tiêu chuẩn nghiệm thu Cổng Quyết định (Decision Gate). |

---

## 1. MỤC TIÊU & BỐI CẢNH THỰC NGHIỆM

Sau khi hoàn thành Sprint 1 (C++ Math Core), Sprint 2 (E0 Benchmark & Baseline A2 Freezing), và Sprint 3 (Lock-Free Shared Memory IPC & C-ABI FFI), hệ thống đã sở hữu:
- Một Core C++20 tối ưu AVX2/BMI2 siêu tốc ($< 3.3\ \mu\text{s}$ Core calculation).
- Một hạ tầng giao tiếp IPC phi khóa hai tầng ($5.30\ \mu\text{s}$ End-to-End).
- Một bộ dữ liệu chuẩn 10.000 mẫu E0 Benchmark đã khóa mã băm SHA-256.
- Một Golden Baseline A2 đã đóng băng vĩnh viễn trong `results/baseline_a2/BASELINE_A2_FREEZE.sha256`.

**Sprint 4 là thời khắc phán quyết khoa học (Moment of Truth):**
Thực thi **Grand Prix E9** trên cùng một tập dữ liệu held-out test (1.500 mẫu), đối đầu trực diện giữa 3 nhánh:
1. **Nhánh A (Baseline A2):** Factorized Low-Rank Linear Scorer ($Rank = 64$).
2. **Nhánh B (Statevector $\mathcal{H}_{12}$):** Không gian Hilbert phức $\mathbb{C}^{4096}$ với toán tử Unitary pha đường chéo và giao thoa biên độ.
3. **Nhánh C ($\mathcal{C}\ell(12)$ Clifford Rotors):** Multivector thực $\mathbb{R}^{4096}$ với chuỗi $M \le 16$ Rotor Givens trong đại số hình học xoay trên 66 mặt phẳng bivector $\binom{12}{2}$.

---

## 2. ĐẶC TẢ TOÁN HỌC CÁC NHÁNH THAM CHIẾN

### 2.1. Nhánh A — Golden Baseline A2 (Đã Khóa)
- **Cơ chế:** Chiếu vector ngữ cảnh $h \in \mathbb{R}^{4096}$ qua ma trận phân tích nhân tử hạng thấp:
  $$s(k \mid h) = \sum_{r=1}^{64} W_{r, k}^{(R)} \left( \sum_{j=1}^{4096} W_{r, j}^{(L)} h_j \right) + b_k$$
- **Trạng thái:** Đã huấn luyện bằng Ridge Regression ($\alpha = 10^{-4}$), đạt:
  - Tỷ lệ hợp lệ $\mathcal{V} = 100.0\%$
  - Độ hối tiếc $\mathcal{R} \le 12.0\%$ (thực đo: $0.00\%$)
  - Checksum: `baseline_a2_weights.npz` (SHA-256 locked).

### 2.2. Nhánh B — Statevector Hilbert $\mathcal{H}_{12}$

> [!WARNING]
> ### [ISOLATED / THEORETICAL SPEC — 2026-09-27 Audit Reconciliation]
> *Đặc tả dưới đây là giả thuyết toán học ban đầu. Trong mã nguồn thực tế `scripts/train_branches_b_c.py`, Nhánh B được hiện thực bằng thuật toán phổ FWHT kết hợp hồi quy tuyến tính Ridge.*
>
> - **Không gian trạng thái:** $|\psi\rangle \in \mathbb{C}^{4096}$ với $\|\psi\|_2 = 1$.
> - **Mã hóa ngữ cảnh:** Ánh xạ $h \in \mathbb{R}^{4096}$ thành biên độ phức với góc pha học được $\phi \in [-\pi, \pi]^{4096}$:
>   $$\psi_0(k) = \frac{h_k \cdot e^{i \phi_k}}{\sqrt{\sum_{j} h_j^2}}$$
> - **Toán tử Unitary Biến đổi:** Toán tử Unitary đường chéo (Diagonal Phase Rotation) kết hợp giao thoa Hadamard / Entangling phase shifts:
>   $$\psi'(k) = e^{i \theta_k} \psi_0(k)$$
> - **Đo lường & Sụp đổ:** Xác suất Born $P(k) = |\psi'(k)|^2$, sàng lọc qua mặt nạ ràng buộc $\mathcal{A}$:
>   $$k^* = \arg\max_{k \in \mathcal{A}} P(k)$$
> - **Số lượng tham số:** $2 \times 4096 = 8.192$ tham số góc pha $(\phi, \theta)$.

**[HIỆN THỰC THỰC TẾ TRONG CODE]: FWHT Spectral Linear Scorer**
- Tính biến đổi Walsh-Hadamard nhanh trên vector ngữ cảnh: $H(h) = \text{FWHT}(h)$.
- Học ma trận biến đổi tuyến tính $W_b \in \mathbb{R}^{64 \times 4096}$ bằng Ridge Regression để xấp xỉ không gian chiếu hạng thấp 64D.
- Điểm quyết định: $\text{score}_B = \text{candidate\_codebook} \times (W_b H(h)) - 0.3 \times \text{topology\_cost}$.
- Quyết định: $k^* = \arg\max_{k \in \mathcal{A}} \text{score}_B(k)$.

---

### 2.3. Nhánh C — $\mathcal{C}\ell(12)$ Clifford Rotors (Động cơ Cốt lõi)

> [!WARNING]
> ### [ISOLATED / THEORETICAL SPEC — 2026-09-27 Audit Reconciliation]
> *Đặc tả dưới đây mô tả năng lượng cơ sở blade có trọng số $s(k) = w_k (\Psi'_k)^2 + b_k$. Cần lưu ý sự khác biệt giữa implementation trong `train_branches_b_c.py` (dùng learned linear readout $W_c$) và C++ Core `collapse.cpp` (dùng pure unweighted amplitude-squared argmax).*
>
> - **Không gian trạng thái:** Multivector thực $\Psi \in \mathcal{C}\ell(12)$ có 4.096 tọa độ thành phần cơ sở blade.
> - **Mã hóa ngữ cảnh:** $\Psi_0 = \sum_{k=0}^{4095} h_k e_k$, chuẩn hóa $\|\Psi_0\|_2 = 1$.
> - **Biến đổi Rotor Givens:** Chuỗi $M \le 16$ rotor trên các mặt phẳng bivector $(i_m, j_m) \in \binom{12}{2} = 66$:
>   $$R = R_M \dots R_2 R_1, \quad R_m = \cos\frac{\theta_m}{2} - \sin\frac{\theta_m}{2} e_{i_m} e_{j_m}$$
>   $$\Psi' = R \Psi_0 \tilde{R}$$
>   Được tối ưu hóa bằng SIMD AVX2 và BMI2 `_pdep_u32` trong `Spin12Engine::apply_factorized_rotors`.
> - **Đo lường & Sụp đổ:** Năng lượng cơ sở blade có trọng số:
>   $$s(k) = w_k \cdot (\Psi'_k)^2 + b_k$$
>   $$k^* = \arg\max_{k \in \mathcal{A}} s(k)$$

**[HIỆN THỰC THỰC TẾ TRONG CODE]: Rotor Transform + Learned Linear Readout**
- Áp dụng chuỗi 8 Givens rotors trực giao $R$ lên vector đầu vào: $h_{\text{rot}} = R \cdot h$.
- Ánh xạ qua bộ giải mã tuyến tính $W_c \in \mathbb{R}^{64 \times 4096}$ huấn luyện bằng Ridge: $z = W_c \cdot h_{\text{rot}}$.
- Tính điểm thông qua ma trận mã ứng viên: $\text{score}_C = \text{candidate\_codebook} \times z - 0.3 \times \text{topology\_cost}$.
- Quyết định: $k^* = \arg\max_{k \in \mathcal{A}} \text{score}_C(k)$.
- **Lưu ý kiểm định (P0 Risk):** Hàm tính điểm trên chưa được tích hợp vào `collapse.cpp` (vốn chỉ làm $\arg\max \text{state}^2$). Bắt buộc phải đồng nhất ở phiên bản **E9-v2**.

---

## 3. QUY TRÌNH THỰC THI & TỐI ƯU HÓA SPRINT 4

```text
[BƯỚC 1]: Huấn luyện Nhánh B (FWHT + Ridge Linear Scorer)
          ├── Biến đổi FWHT trên train_latents (7.000 mẫu)
          ├── Hồi quy Ridge khớp không gian chiếu hạng thấp 64D
          └── Validate trên val_latents (1.500 mẫu)

[BƯỚC 2]: Huấn luyện Nhánh C (Clifford Rotor Evolution & Linear Readout W_c)
          ├── Tìm kiếm mặt phẳng bivector tối ưu và góc quay Rotor (M = 8)
          ├── Huấn luyện ma trận W_c 64x4096 bằng Ridge Regression
          └── Validate trên val_latents (1.500 mẫu)

[BƯỚC 3]: Quyết Đấu Grand Prix E9 trên Held-out Test Set (1.500 mẫu)
          ├── Đo đồng thời Nhánh A2, Nhánh B, Nhánh C
          ├── Ghi nhận: Validity Rate (%), Mean Regret (%), p95 Regret (%)
          ├── Ghi nhận: Core Calculation Latency (µs), Peak Working Set (KiB)
          └── Vẽ bản đồ Pareto Frontier (Regret vs Latency)

[BƯỚC 4]: Áp Dụng Cổng Phán Quyết (Decision Gate G2)
          ├── Khóa tạm thời (Provisional) Nhánh C Cl(12) làm động cơ nghiên cứu chính thức
          └── Thiết lập lộ trình E9-v2 để tái nghiệm thu đồng nhất C++ Production Binary
```

---

## 4. TIÊU CHUẨN NGHIỆM THU E9-v2 (RE-VERIFIED ACCEPTANCE CRITERIA)

1. **Tuân thủ Mặt nạ Tuyệt đối:** $\mathcal{V} = 100.0\%$ trên cả 3 nhánh (không một ngoại lệ vi phạm ràng buộc cứng).
2. **Khóa Toàn Vẹn Dữ Liệu:** Toàn bộ dữ liệu train/val/test phải được kiểm tra mã băm SHA-256 đối chiếu với `data/e0_benchmark/checksums.sha256` trước khi nạp.
3. **Thống nhất Giao thức Bitmask:** Bắt buộc áp dụng `bitorder='little'` cho `np.packbits` và `np.unpackbits` để đồng nhất với lệnh CPU BMI2 `_tzcnt_u64`.
4. **Độ Trễ Phân Vị (Latency SLA đo trực tiếp Binary):**
   - Đo trực tiếp trên C++ DLL hoặc IPC-P SHM (tối thiểu 50.000 chu kỳ), không dùng số hardcode.
   - Core Latency p50 $< 5.0\ \mu\text{s}$, p99 $< 15.0\ \mu\text{s}$.
5. **Độ Hối Tiếc (Normalized Regret $\mathcal{R}$):** $\mathcal{R} \le 12.0\%$ (ngưỡng đạt chuẩn E0).
6. **Bóc tách Bộ nhớ Rõ ràng:**
   - Multivector State: Cố định 32 KiB float64 (nằm trong L1 Cache).
   - Parameter & Scorer Working Set: Đo lường và công bố chính xác (dự kiến ~2 MiB).
