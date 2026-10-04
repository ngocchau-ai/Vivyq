# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# HOT-MEMORY: CÁC QUYẾT ĐỊNH BỀN VỮNG VỀ HỆ THỐNG VIVYQU & KẾ THỪA VIVY_FINAL

**Thư mục đích đồng bộ:** `D:\2brain\hot-memory\durable_decisions_vivyqu.md`  
**Ngày cập nhật:** 2026-09-27  
**Tác giả:** Antigravity / Trợ lý Toàn thời gian Ngọc Châu  

---

## 1. CÁC QUYẾT ĐỊNH KIẾN TRÚC BỀN VỮNG (DURABLE DECISIONS)

> [!WARNING]
> ### [ISOLATED / DEPRECATED / REPLACED — 2026-09-27 Audit Revision]
> *Nội dung Mục 1 dưới đây bị cô lập do gộp state size 32 KiB với working set và sử dụng số đo 2.50 µs chưa được đo trực tiếp trong E9 harness:*
>
> 1. **Khóa Nhánh C ($\mathcal{C}\ell(12)$ Clifford Rotors) làm Lõi Quyết Định Duy Nhất:**
>    - Chấm dứt tranh cãi số phức vs. số thực. Không gian multivector 4096D số thực ($32\text{ KiB}$) nằm trọn trong L1 Data Cache của CPU.
>    - Đạt độ trễ vi mô kỷ lục: **$2.50\ \mu\text{s}$**, vượt xa mục tiêu p99 $< 10\ \mu\text{s}$.

1. **Khóa Chính Thức Nhánh C ($\mathcal{C}\ell(12)$ Clifford Rotors E9-v2) làm Lõi Quyết Định (Production Locked):**
   - **Tích hợp trọn gói C++ Core (Hướng 1):** Toàn bộ pipeline quyết định E9 gồm $W_c$ ($64 \times 4096$), $C$ ($4096 \times 64$), `topology_cost` ($4096$) và 8 Givens rotors đã được nhúng trực tiếp vào binary C++ Core (`vivyqu_core.dll`) với tập lệnh AVX2/FMA/BMI2.
   - **Bằng chứng Đối chiếu Chéo (Cross-Validation):** Khớp chính xác **100.00% (1500/1500 mẫu test held-out độc lập)** giữa Python NumPy và C++ Production Core.
   - **Độ trễ Thực tế Xác nhận (50.000 chu kỳ đo lường):** Đạt **p50 = 28.50 µs, p95 = 38.10 µs, p99 = 79.10 µs** (thỏa mãn SLA < 100 µs cho toàn bộ 524k FLOPs).
   - **Phân định bộ nhớ minh bạch:** Multivector State chiếm đúng **$32\text{ KiB}$** ($4096 \times \text{float32/64}$, L1 Cache resident). Tổng working set (kèm ma trận giải mã tuyến tính $W_c$ 1 MiB, codebook 1 MiB, cost và rotor tables) là **~2.02 MiB** (hoàn toàn vừa vặn trong L2/L3 Cache của CPU hiện đại).
   - **Trạng thái Cổng G2:** `FINAL PASS` (Chính thức khóa Nhánh C làm Động Cơ Nhận Thức Lõi duy nhất, Nhánh A Baseline A2 làm Tầng Cứu Nguy Khẩn Cấp).
2. **Khóa Hợp Đồng Bóc Tách Bản Thể (Soul-Body Decoupling):**
   - Core (Linh hồn) thuần khiết toán học, cấm I/O, cấm syscalls.
   - Cầu Treo (Thân thể) quản lý I/O, Mắt, Tay, Watchdog, và bộ nhớ chia sẻ Lock-free Ring Buffer ($< 0.3\ \mu\text{s}$).
3. **Tuyệt Đối Tuân Thủ Quy Tắc Vytrading (No Programmatic Filters):**
   - Não AI Local (Vivy) chịu trách nhiệm 100% việc tư duy, định giá rủi ro và tự quyết định độc lập.
   - Mắt chỉ thu thập dữ liệu khách quan, cấm gắn bộ lọc cản.
   - Tay chỉ thực thi trực tiếp hành động thô $k^*$ lên MT5/Host. Nghiêm cấm viết thêm các thuật toán gác cổng lập trình cứng (R:R Guard, Netting check, Vị thế cap cứng, Velocity block) làm méo mó quyết định của AI.
4. **Chuẩn Hóa Phân Tách Input & Ghép Nối Output:**
   - Input Splitting: Phân tách trực giao 4 khối x 1024D (Order Book/Ticks, Kỹ thuật/Wavelets, Danh mục/Vị thế, Vĩ mô/Sentiment).
   - Output Stitching: Giải mã 12 bit nhị phân thành 4 tham số hành động 3-bit: Action Intent, Position Sizing Tier, Take-Profit Tier, Stop-Loss Horizon Tier.
5. **Chiến Lược Tối Ưu Hóa Trên Phần Cứng Giới Hạn (PC 16GB RAM):**
   - Kế thừa `Epistemic Gate` từ `Vivy_final`: Tiết kiệm 95% compute, 90% chu kỳ Core tự tin ra quyết định trong $2.5\ \mu\text{s}$ mà không đánh thức Local LLM.
   - Kế thừa `Adaptive N Controller`: Tự động co giãn tài nguyên theo tải hệ thống.
6. **Triển Khai SHM IPC Daemon với E9 Geometric Scorer Mặc Định:**
   - Tiến trình daemon độc lập `vivyqu_shm_daemon.exe` tự động nạp `e9_weights.bin` vào bộ nhớ L2/L3 (~2.02 MiB), chạy 50 chu kỳ làm ấm CPU cache (Warm-up) trước khi đón luồng tick.
   - Tự động điều phối `MODE_GEOMETRIC_E9`, vận hành trên Ring Buffer 8 slots SPSC phi khóa.
   - Kết quả thực nghiệm: Độ trễ truyền thông IPC $2.80\ \mu\text{s}$, End-to-End Fast-Path $\text{p50} = 30.50\ \mu\text{s}$, $\text{p99} = 59.50\ \mu\text{s}$ (< 120 µs SLA).
7. **Kích Hoạt Cơ Chế Thích Nghi Trực Tuyến Bằng Hamiltonian Torque Descent:**
   - Kế thừa trọn vẹn năng lực tự tiến hóa từ `Vivy_final`: Thích nghi trực tuyến tại chỗ không cần Backpropagation nặng nề.
   - Tính toán trực tiếp moment lực bivector: $\text{Torque}_{ij} = \langle g \wedge h_{\text{rot}}, e_i \wedge e_j \rangle$ và cập nhật góc quay rotor: $\Delta \theta_m = -\eta \cdot \text{Torque}_m$.
   - Tốc độ thực thi thực nghiệm: Toàn bộ chu kỳ forward + loss + backproject transpose $W_c^T$ + torque calculation + rotor update đạt $\text{p50} = 48.60\ \mu\text{s}$ trên 1 core CPU x86-64 AVX2/FMA.
   - Đã kiểm chứng tính hội tụ thực tế: Giảm 29.8% margin loss chỉ sau 25 chu kỳ thích nghi online.

8. **[2026-10-04] Cô lập rotor Givens khỏi đường quyết định E9 mặc định** (chủ dự án duyệt):
   - Căn cứ: bộ nghiệm thu ACC-1..3 (`docs/ACCEPTANCE_SUITE_ACC1_3_QUDIT_HYPOTHESIS.md` §8.10): H3 (có rotor) không thắng H4 (bỏ rotor) ở cả 3 bài.
   - Thực thi (§8.11): gập rotor vào `W_c_active = W_c·R(θ)`; mặc định `ROTOR_MODE_ISOLATED`; đường cũ giữ qua `ROTOR_MODE_LEGACY`. Quyết định tương đương 100% (300 mẫu), p50 20.9 → 17.8 µs.
   - Ảnh hưởng tới Quyết định 1 và 7: rotor không còn là bước runtime; Hamiltonian Torque Descent vẫn chạy nhưng ở ISOLATED tốn p50 274 µs/bước (LEGACY 31.6 µs). Quyết định 1 và 7 **không bị xóa**, chỉ được chú thích bởi Quyết định 8.

9. **[2026-10-04] Runtime C/C++ thuần + Piggyback Host in-process** (chủ dự án duyệt 06:51; ADR `docs/ADR_2026-10-04_PIGGYBACK_HOST_CPP_RUNTIME.md`):
   - Đường quyết định lúc chạy = C/C++ + C-ABI, không phụ thuộc Python; Python chỉ cho nghiên cứu/huấn luyện/harness.
   - Một tiến trình: libllama (llama.cpp 836d571) + cb_eval bắt `l_out-L` token cuối + `vivyqu_core_step_e9`; P2 runtime = Hadamard ngẫu nhiên có đệm 2560->4096 (thay ma trận dày 42-84 MB).
   - Đo (commit 00a400b): quyết định cận biên p50 ~110 µs, p99 ~190 µs (2 lượt); bắt hidden-state làm chậm sinh token 0.58-2.08%. Chất lượng CHƯA đo (trọng số E9 chưa train trên hidden-state).
   - Bắt buộc trước S4: `hidden_pipeline.py` đổi sang cùng P2 Hadamard. Rủi ro mở: lệch phiên bản llama.cpp với Vivy (a94d563); host cần ưu tiên CPU (smoke tranh CPU làm token chậm ~9 lần).

10. **[2026-10-04] Giả thuyết qudit phải thắng solver cổ điển cùng ngân sách thời gian** (chủ dự án duyệt 07:47; spec §8.14.1; kernel `vivyqu_accq` K1–K4 commit 2546cc7..ee447e9):
   - Căn cứ: beam B=64 trên năng lượng exact đạt tối ưu 99% (ACC-1) / 92% (ACC-2) ở n=6 trong ~0.03 ms.
   - Quy tắc: mọi arm học (statevector, MPS, factor, MLP) so với `C-solver-beam(B*)` có p50 C++ ≤ p50 của arm. Ô nào solver đạt ≥ 0.99 thì không được dùng để ủng hộ giả thuyết.
   - Hệ quả: vùng còn khả năng = n lớn dày (12/24) hoặc bài mà năng lượng không quan sát được (cần pre-register riêng).

11. **[2026-10-04] Kết quả S2c: `[GIẢ THUYẾT QUDIT CHƯA ĐƯỢC ỦNG HỘ — P5/Q1]`** (spec §8.15, commit 0cc8eb1; tiêu chí khóa trước §8.12):
   - C1 FAIL 0/3: H5_qudit_interact vượt H1/H2/H4 nhưng không vượt H6_qubit_interact (ACC-1 0.367 vs 0.330, CI chạm; ACC-2 0.408 vs 0.416).
   - C2 PASS 2/3: tương tác bậc 2–3 đóng góp +0.24 (ACC-1), +0.39 (ACC-2). ACC-3 mọi arm ≈ ngẫu nhiên.
   - Quy tắc kế thừa: không được viết "qudit cho lợi thế" trong tài liệu nào; chỉ được nói "cấu trúc tương tác có cổng giúp". Pha Q2 chỉ thiết kế biến thể từ chỗ thất bại (S2d §8.13).
---

## 2. LỊCH SỬ THAY ĐỔI (AUDIT TRAIL)

| Thời gian (UTC+7) | Agent / Người sửa | Hành động & Lý do |
|:---:|:---|:---|
| 2026-09-27 12:00 | Antigravity IDE | Khởi tạo tài liệu các quyết định bền vững VivyQu. |
| 2026-09-27 18:30 | Antigravity IDE | Cập nhật Quyết định 1: Khóa Nhánh C E9-v2 sau khi tích hợp trọn gói vào C++ Core và đối chiếu chéo 100% trên 1500 mẫu test. |
| 2026-09-27 19:15 | Antigravity IDE | Bổ sung Quyết định 6 (SHM Daemon E9 Mode) và Quyết định 7 (Hamiltonian Torque Descent thích nghi trực tuyến p50 = 48.60 µs). |
| 2026-10-04 06:00 | Antigravity IDE (Claude Opus 5.5) | Bổ sung Quyết định 8: cô lập rotor (bằng chứng ACC-1..3 §8.10, thực thi §8.11). |
| 2026-10-04 07:03 | Antigravity IDE (Claude Opus 5.5) | Bổ sung Quyết định 9: runtime C/C++ + Piggyback Host (ADR 2026-10-04, M1/M2 đạt). |
| 2026-10-04 07:49 | Antigravity IDE (Claude Opus 5.5) | Bổ sung Quyết định 10: đối chứng solver-beam cùng ngân sách thời gian cho ACC-Q (spec §8.14.1). |
| 2026-10-04 08:06 | Antigravity IDE (Claude Opus 5.5) | Bổ sung Quyết định 11: kết quả S2c (C1 FAIL, C2 PASS 2/3). |
