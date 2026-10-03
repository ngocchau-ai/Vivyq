> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# ACCEPTANCE SUITE ACC-1..3 — Nghiệm thu giả thuyết Qudit / N luồng giả thuyết

**Trạng thái:** `[DRAFT — CHỜ DUYỆT PRE-REGISTRATION]` · **Ngày:** 2026-10-03 · **Cấp độ dự án:** `[PROTOTYPE]`
**Bối cảnh:** review 2026-10-03 phát hiện benchmark E0/E9 bị vòng tròn (nhãn sinh từ cùng hàm rank-64 tuyến tính với Core). Suite này thay thế vai trò "bằng chứng nhận thức"; **không** thay thế các test ABI/IPC hiện có.
**Quyết định chủ dự án (2026-10-03):** VivyQu là não quyết định độc lập với Vivy/Vyvy; quy tắc Vytrading "không thuật toán cứng" **không** áp dụng cho dự án này.

## 0. Giả định & định nghĩa

- **[GIẢ ĐỊNH] "N luồng giả thuyết"** = N *arm* kiến trúc/biểu diễn cạnh tranh được đánh giá trên cùng dữ liệu (không phải N luồng chạy song song trong runtime). Biến thể runtime (Top-K = K giả thuyết đồng thời do Core trả về) được đo riêng bằng metric `pass@K` (§4). Cần chủ dự án xác nhận nghĩa này.
- Ứng viên = 12-bit (0..4095) = 6 qudit 4 trạng thái = 12 qubit. Mọi tác vụ phải có **verifier xác định (exact)** hoặc oracle tính được; không dùng nhãn do mô hình sinh.

## 1. Các arm (luồng giả thuyết) — chung cho cả ba bài

| Arm | Mô tả | Vai trò |
|---|---|---|
| **H0** | Random / majority class | Sàn |
| **H1** | Linear probe rank-64 + codebook + mask (≈ Baseline A2) | Đối chứng cổ điển rẻ nhất |
| **H2** | MLP, cùng số tham số với H4 | Đối chứng phi tuyến công bằng |
| **H3** | Core E9 hiện tại (rotor Givens 8 + W_c 64×4096) | Hệ đang có |
| **H4** | Core bỏ rotor (gộp vào W_c) | Kiểm tra dư thừa rotor |
| **H5** | **Qudit-hybrid**: 6 qudit×4 trạng thái, tương tác cặp/ba giữa qudit (tích tensor có cấu trúc), cùng số tham số | Giả thuyết cần chứng minh |
| **H6** | Qubit-12 (2¹²) cùng số tham số với H5 | Tách "qudit" khỏi "tensor-structure" |
| **H7** | Bộ giải cổ điển exact (vét cạn 4096) | Trần chất lượng, không phải đối thủ về khái quát |

Quy tắc: tham số của H2/H5/H6 phải khớp H3 ±5% (báo cáo số thực). Chọn hyper-parameter chỉ trên tập `val`; **test OOD chạm đúng 1 lần**.

## 2. Ba tác vụ

### ACC-1 — Tô 4 màu đồ thị 6 đỉnh có ràng buộc (đã duyệt)
- **Ứng viên:** phép gán màu `c ∈ {0..3}⁶` → index `Σ cᵢ·4ⁱ`.
- **Instance:** đồ thị 6 đỉnh + trọng số cạnh + một số ràng buộc cứng "đỉnh i ≠ màu m" (→ mask thật). Chi phí = tổng trọng số cạnh bị xung đột.
- **Nhãn:** phép tô tối ưu (min cost, tie-break xác định) từ H7 — exact.
- **Split OOD:** train trên đồ thị thưa (mật độ ≤0.4); val mật độ 0.4–0.6; **test** mật độ ≥0.7 và họ có cấu trúc (hai phía, bánh xe, K₆ perturbed) chưa thấy.
- **Metric:** top-1 accuracy, *cost-regret* (cost chọn − cost tối ưu)/cost tối ưu, tỷ lệ chọn vi phạm mask (phải = 0), `pass@8`.
- **Kết quả đã biết:** có (exact) → dùng làm **kiểm tra sanity + khái quát hóa**.

### ACC-2 — Vật lý: trạng thái cơ bản của mô hình clock/Potts 4 trạng thái có frustration (kết quả mở)
- **Ứng viên:** cấu hình 6 spin 4 trạng thái (Z₄ clock) trên đồ thị bất kỳ → 4096 trạng thái. Hamiltonian `H = −Σ Jᵢⱼ cos(π(sᵢ−sⱼ)/2) − Σ hᵢ cos(π sᵢ/2 + φᵢ)`.
- **Instance:** (J, h, φ) lấy mẫu; vector hidden-state mã hóa instance (§3).
- **Nhãn:** ground state exact bằng vét cạn 4096; kèm **khoảng cách năng lượng** (gap) và **độ suy biến**.
- **Phần "mở" (không biết trước đáp án):**
  1. *Phase-boundary mapping:* quét độ frustration f ∈ [0,1] (tỷ lệ J âm). Câu hỏi mở: arm nào giữ accuracy khi gap → 0? Đường cong accuracy(f) của từng arm được **vẽ ra, không giả định hình dạng**.
  2. *Degenerate ground states:* khi suy biến >1, Core có trả về **tập** giả thuyết chứa mọi ground state trong Top-8 không (`recall@8` trên tập suy biến). Đây là phép thử trực tiếp cho "N luồng giả thuyết đồng thời".
  3. *Quantum extension (tùy chọn, G+):* thêm transverse field Γ (6 qudit, Hilbert 4⁶=4096 — **khớp chính xác** với Core), ground state bằng chéo hóa exact (ma trận 4096×4096, vài giây bằng `scipy.sparse.linalg.eigsh`). Nhãn = trạng thái cơ bản vector; metric = fidelity |⟨ψ_pred|ψ₀⟩|² và sai số năng lượng. Đây là bài duy nhất mà biểu diễn "trạng thái lượng tử mô phỏng" có thể thắng cấu trúc cổ điển một cách có ý nghĩa.
- **Metric chính:** top-1 accuracy theo đoạn gap; regret năng lượng; `recall@8` suy biến; (quantum) fidelity.
- **Ngưỡng báo cáo:** trung vị theo 5 seed + CI 95% bootstrap.

### ACC-3 — Toán: logarit rời rạc & cấu trúc chu kỳ trên 𝔽ₚ (kết quả mở)
- **Ứng viên:** x ∈ [0, 4095], bài toán `g^x ≡ h (mod p)`, p nguyên tố ∈ (2,4096] (hoặc bậc nhóm ≤4096).
- **Instance:** (g, h, p) → mã hóa thành prompt văn bản → hidden-state.
- **Nhãn/verifier:** exact bằng tính lũy thừa; verifier chấp nhận *mọi* x thỏa phương trình (đáp án không duy nhất khi ord(g) < p−1) — mask động = tập đáp án hợp lệ.
- **Lý do chọn:** cấu trúc *tuần hoàn/pha* là nơi giả thuyết "pha phức/qudit" có cơ sở lý thuyết (biến đổi Fourier trên Z_n), và là nơi probe tuyến tính bị cho là yếu.
- **Phần "mở":**
  1. *Generalize qua p chưa thấy:* train trên p ≤ 1024, test p ∈ (2048, 4096]. Kết quả chưa biết.
  2. *Có "grokking" Fourier không:* so sánh phổ Fourier của W_c học được với đặc trưng đã biết của mạng học modular arithmetic; báo cáo trung thực nếu không có.
  3. *Phân tách theo cấu trúc nhóm:* accuracy theo `ord(g)` và `p−1` có/không smooth (nhiều thừa số nhỏ).
- **Kỳ vọng trung thực:** nhiều khả năng **mọi arm thất bại OOD** ở p lớn. Đó là kết quả hợp lệ — bài này đo *ranh giới* chứ không nhằm thắng. `[GIẢ ĐỊNH — cần chạy thật]`.

## 3. Pipeline hidden-state (bắt buộc) + phương án dự phòng

**Mục tiêu:** vector 4096 chiều mã hóa instance, lấy từ LLM thật, đi vào Core qua cùng ABI (float64[4096], contiguous).

| Phương án | Mô tả | Khi dùng |
|---|---|---|
| **P1 (chính)** | Model có hidden dim = 4096 (ví dụ họ LLaMA-3-8B); residual stream của **token cuối**, layer ℓ ∈ {mid, ¾, last} chọn trên `val`; prompt định dạng cố định; ghi `model_sha`, `layer`, `prompt_template_sha`, `dtype/quant` | Mặc định |
| **P2** | Model hidden dim ≠ 4096: đệm 0 hoặc **PCA/ngẫu nhiên-trực-giao cố định** về 4096 (fit trên train), ghi lại phép chiếu | Gemma-2 (kiểm tra hidden dim thực của biến thể dùng) |
| **P3** | Embedding model 4096 chiều chuyên dụng (không phải generative) | Không lấy được hidden-state từ backend (ví dụ llama.cpp không expose layer) |
| **P4** | Mean-pool nhiều token/nhiều layer, nối rồi chiếu | Token cuối quá nhiễu |
| **P5 (kiểm soát, không phải sản phẩm)** | Latent **tổng hợp có cấu trúc**: đặc trưng instance → ánh xạ trực giao cố định → 4096 | Tách "LLM không mã hóa instance" khỏi "Core không học được"; cũng là đường chạy khi chưa có GPU |
| **P6 (kiểm soát âm)** | Hidden-state của prompt đã **xáo nhãn/xáo instance** | Phải ra ~ngẫu nhiên; nếu không → rò rỉ |

**Gate G-ENC (chạy trước mọi so sánh arm):** probe tuyến tính (ridge) từ hidden-state → đặc trưng instance (ví dụ ma trận kề flatten, hoặc p, g, h). Nếu R² trên val < 0.5 → hidden-state **không** mang thông tin instance → đổi layer/prompt/phương án; **cấm** kết luận về Core khi G-ENC fail.

> [!WARNING]
> LLM thường **không** biểu diễn tốt đồ thị/số học modular trong hidden-state (đặc biệt ACC-3). G-ENC fail là kịch bản thật, không phải ngoại lệ. Vì vậy P5 chạy song song từ ngày đầu để mọi kết luận về Core có đường chứng minh độc lập với LLM.

## 4. Metric chung và tiêu chí pass (pre-register — KHÓA TRƯỚC KHI CHẠY)

- **Seeds:** ≥5 (khởi tạo + split), báo cáo trung vị + CI 95% bootstrap.
- **Fail-closed:** tỷ lệ chọn ứng viên ngoài mask = 0 ở mọi arm (vi phạm → arm bị loại khỏi bảng xếp hạng).
- **Giả thuyết H5 (qudit) được coi là ủng hộ** khi, trên **test OOD** của ít nhất 2/3 bài: top-1 hoặc regret của H5 tốt hơn **cả** H1, H2, H4, H6 với CI 95% không chồng lấn, **và** G-ENC pass (hoặc có cùng kết quả trên P5).
- **Giả thuyết H3 (Core+rotor) được coi là có giá trị** nếu thắng H4 (bỏ rotor) theo cùng chuẩn; nếu không → ghi `[ROTOR DƯ THỪA]` và đề xuất cô lập (không xóa) phần rotor.
- **Kết quả âm là kết quả:** nếu H5 không thắng, cập nhật README thành `[GIẢ THUYẾT QUDIT CHƯA ĐƯỢC ỦNG HỘ]`; không đổi tiêu chí sau khi thấy dữ liệu.
- **Báo cáo bắt buộc kèm:** manifest (commit SHA, DLL SHA-256, compiler/flags, CPU, seeds, dataset SHA, model SHA, layer, prompt template SHA).

## 5. Rủi ro & phản biện (Devil's Advocate)

| Rủi ro | Hệ quả | Giảm thiểu |
|---|---|---|
| Bộ không gian 4096 quá nhỏ → vét cạn thắng mọi arm học | "Core vô dụng" | Đúng — thừa nhận; giá trị chỉ ở khái quát/hiệu quả tham số, không ở tốc độ giải |
| Hidden-state không mã hóa instance (ACC-3 đặc biệt) | Mọi arm ~ngẫu nhiên | G-ENC + P5 |
| Số tham số khớp nhưng kiến trúc H5 được "tune" nhiều hơn | Thiên vị | Cùng ngân sách tune/arm; ghi số lần thử |
| Chọn ngưỡng sau khi thấy dữ liệu | p-hacking | Khóa §4 bằng commit trước khi chạy |
| ACC-2 quantum extension: Hamiltonian 4096² nặng | Chậm | `eigsh` trên ma trận thưa; giới hạn số instance |
| Test OOD bị rò rỉ qua val | Kết quả ảo | Test chạm 1 lần; hash tập test |

## 6. Kế hoạch thực thi (thứ tự, mỗi bước có cổng verify)

1. **S0** — Đóng băng spec này (commit) + khóa §4. *Verify:* hash commit.
2. **S1** — Bộ sinh dữ liệu + verifier exact cho ACC-1..3 (`scripts/acc/`), test tự động rằng verifier khớp vét cạn trên 100% mẫu. *Verify:* pytest.
3. **S2** — Harness arm H0–H7 với đếm tham số; chạy trên P5 (không cần GPU). *Verify:* bảng kết quả + manifest.
4. **S3** — Trích hidden-state (P1→P6), G-ENC. *Verify:* R² báo cáo.
5. **S4** — Chạy lại toàn bộ trên hidden-state thật; một lượt test OOD.
6. **S5** — Báo cáo + cập nhật README trạng thái theo kết quả (kể cả âm) + đồng bộ `D:\2brain`.

## 7. Câu hỏi còn mở cho chủ dự án
1. Xác nhận định nghĩa "N luồng giả thuyết" ở §0 (N arm cạnh tranh, kèm `pass@K` cho đa-giả-thuyết trong runtime)?
2. Model nào cho hidden-state (hidden dim thực tế, và chạy bằng backend nào: HF transformers hay llama.cpp)? GPU/VRAM có sẵn?
3. Chạy `ACC-2` quantum extension (chéo hóa exact) ngay từ đầu hay để giai đoạn sau?

## Lịch sử thay đổi
- 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới: bộ nghiệm thu ACC-1..3, pipeline hidden-state + phương án dự phòng, tiêu chí pre-register. Lý do: benchmark E0/E9 vòng tròn (review 2026-10-03).
- 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Revision #2 (§8): phân pha qubit-trước, arm tương hỗ, mô hình Gemma chạy CPU, chọn ACC-2 quantum extension ở cuối pha Q1. Lý do: quyết định chủ dự án 18:43. §0–§7 giữ nguyên; điểm bị thay thế ghi rõ trong §8.

## 8. REVISION #2 (2026-10-03) — theo quyết định chủ dự án

### 8.1 Ý nghĩa "luồng giả thuyết" `[REPLACES §0 giả định đầu — bản cũ giữ nguyên]`
Chủ dự án: đây là **lý thuyết mở**; luồng giả thuyết = N trạng thái (mặc định N=4 hoặc 6 theo qubit), có thể **cạnh tranh** (+`pass@K`) **hoặc tương hỗ**. Suite phải đo cả hai chế độ, không chọn trước:

| Chế độ | Arm | Đo gì |
|---|---|---|
| Cạnh tranh | chọn 1 trong N luồng (argmax/mask) | top-1, `pass@K` |
| Tương hỗ | N luồng cùng đóng góp: tổng có trọng số / mixture-of-experts / bỏ phiếu tuyến tính trên N luồng | top-1, regret, đa dạng (độ tương quan lỗi giữa các luồng) |
| Tương hỗ-có-cổng | luồng này điều biến luồng kia (tích tensor có cấu trúc, ý tưởng H5) | so với tương hỗ cộng tính để tách "tương tác" khỏi "ensemble" |

Chỉ số then chốt `Δ_interaction` = (tương hỗ-có-cổng) − (tương hỗ cộng tính) với cùng số tham số: nếu ≈0 thì phần "qudit/entangle" không đóng góp ngoài ensemble.

### 8.2 Phân pha: qubit trước, qudit sau `[REPLACES thứ tự §6 từ S2 trở đi]`
- **Pha Q1 — Qubit baseline:** N luồng = N qubit (N∈{4,6,12}); mọi arm cạnh tranh/tương hỗ trên ACC-1..3 (P5 latent tổng hợp, CPU). Mục tiêu: tìm cấu hình qubit tốt nhất và biết nó **thất bại ở đâu**.
- **Pha Q2 — Phương án bổ sung:** chỉ thiết kế biến thể từ chỗ Q1 thất bại (ví dụ ghép 2 qubit thành 1 qudit-4, tương tác bậc 3, tham số hóa pha). Mỗi biến thể là một arm mới, khóa tiêu chí trước khi chạy.
- **Pha Q3 — Chu trình qudit:** chỉ dựng khi ≥1 biến thể Q2 thắng Q1 theo §4. Nếu không: ghi nhận kết quả âm.
- **ACC-2 quantum extension (transverse field):** chọn đặt ở **cuối Q1** làm bài thử qubit/qudit duy nhất có nhãn lượng tử exact (Hilbert 2¹² = 4⁶ = 4096).

### 8.3 Hidden-state với Gemma "4eb", không GPU rời `[PHẠM VI P1/P2]`
- `[GIẢ ĐỊNH]` "gemma4 4eb" = biến thể Gemma cỡ ~4B tham số hiệu dụng (tên chính xác và hidden dim **chưa xác minh** — cần chủ dự án cung cấp tên file/repo model). Khả năng cao hidden dim **≠ 4096** → dùng **P2** (chiếu cố định về 4096, fit trên train, lưu ma trận chiếu + SHA).
- Phần cứng không GPU rời: chạy CPU, lượng tử hóa nếu cần. `[HIỆU NĂNG — CHƯA ĐO]`: ước lượng ~10⁴ prompt ngắn × một forward CPU mỗi prompt; phải đo thời gian/prompt trên máy thật trước khi cam kết kích thước tập (đề xuất: bắt đầu 2.000 instance/bài, cache hidden-state ra `.npy` kèm SHA, chỉ trích xuất 1 lần).
- Phương án dự phòng bổ sung cho máy yếu (thứ tự ưu tiên): **P5** (tổng hợp, chạy ngay) → **P3** (embedding model nhỏ chuyên dụng chiếu về 4096) → **P7 (mới)**: model nhỏ hơn cùng họ (≤1–2B) → **P8 (mới)**: trích hidden-state theo lô qua đêm + checkpoint từng 100 prompt (tiếp tục được khi gián đoạn).
- **G-ENC vẫn bắt buộc.** Với model nhỏ + CPU, khả năng G-ENC fail ở ACC-3 cao hơn; khi đó kết luận về Core chỉ dựa P5.

### 8.4 Việc đã làm cùng phiên
- Sửa `engine.py` (import `ERR_CORE_TIMEOUT`, guard `step_fast`) + `tests/test_engine_boundary_negative.py`; root tests 80 passed.

### 8.5 Tiến độ S1 (2026-10-03, phiên tiếp nối) `[PROTOTYPE]`
- Đã tạo `scripts/acc/` (`common.py`, `acc1_coloring.py`, `acc2_clock.py`, `acc3_dlog.py`) + `tests/test_acc_verifiers.py`: 14/14 PASS. Mỗi verifier tham chiếu (thuần Python) được đối chiếu với solver vectorized trên **toàn bộ 4096 ứng viên** (ACC-1, ACC-3) hoặc mẫu bước 7 (ACC-2).
- Lỗi phát hiện & sửa: ACC-1 sinh đồ thị chỉ theo xác suất cạnh nên mật độ thực vượt khoảng split → thêm rejection sampling theo mật độ thực (sparse ≤0.4, mid 0.4–0.6, dense ≥0.7).
- **Chưa làm:** S0 (commit đóng băng spec/§4 — chờ chủ dự án), ACC-2 quantum extension, S2 harness arm H0–H7, S3 hidden-state.
- `[GIẢ ĐỊNH]` còn mở: tên/hidden-dim chính xác của "gemma4 4eb"; chưa cung cấp file model.
- Test flaky có sẵn, không do thay đổi này: `tests/test_shm_ipc.py` timeout 500 µs ngẫu nhiên (1/3 lần chạy riêng; `[CẦN THEO DÕI]`).


### 8.6 Kết quả S2 (2026-10-03) — arm H0/H1/H2/H7 trên P5, CPU, 5 seed, n=2000/500/500, 200 epoch `[PROTOTYPE]`
| Tác vụ | H0 prior | H1 linear r64 | H2 MLP khớp tham số | Ghi chú |
|---|---|---|---|---|
| ACC-1 top-1 (median) / pass@8 | 0.100 / 0.422 | 0.156 / 0.440 | 0.206 / 0.492 | OOD test; vi phạm mask = 0 |
| ACC-2 top-1 / pass@8 | 0.062 / 0.276 | 0.280 / 0.622 | 0.214 / 0.504 | |
| ACC-3 top-1 / pass@8 | 0.002 / 0.012 | 0.004 / 0.014 | 0.004 / 0.016 | ~ngẫu nhiên, đúng kỳ vọng §2 |
- Params: H1 524 288, H2 520 255 (−0,77%, trong ±5%). Mã: `scripts/acc/{tasks,harness,run_s2}.py`, test `tests/test_acc_harness.py`; toàn bộ `pytest tests` 106 passed. Kết quả thô: `results/acc_s2_acc{1,2,3}.json`.
- **Diễn giải trung thực:** trên P5 (latent là phép xoay trực giao của ~40 đặc trưng) H1/H2 chỉ hơn prior nhẹ ở ACC-1 và hơn rõ ở ACC-2; ACC-3 thất bại hoàn toàn. `[GIẢ ĐỊNH]` có thể do chưa tune (lr/epoch cố định, full-batch) — chưa chứng minh là giới hạn kiến trúc. Chưa được rút kết luận về H3–H6.
- **Hạn chế:** H7 là tautology (oracle chấm đúng theo định nghĩa) — chỉ để kiểm tra pipeline. Manifest `commit` trong JSON trỏ S0 (3680245) vì code S2 chưa commit lúc chạy. Chưa có arm H3 (Core E9), H4, H5, H6; chưa có G-ENC (chỉ cần khi dùng hidden-state thật). Tune hyper-parameter chưa làm (cần ngân sách bằng nhau/arm theo §5).
- Lịch sử: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | §8.6 kết quả S2.

### 8.7 Model hidden-state đã xác minh (2026-10-03) `[CẬP NHẬT §8.3 — thay giả định]`
- File: `D:\models\gemma4-e4b\vivy-gemma-e4b-q4km.gguf` (9 608 338 848 B, Q4_K_M, `general.file_type=15`). Đọc metadata bằng `gguf` (pip, mới cài vào môi trường Python hệ thống).
- Kiến trúc `gemma4`: **embedding_length = 2560** (≠ 4096 → bắt buộc **P2**), 42 block, 8 head / 2 kv-head, `embedding_length_per_layer_input=256`, context 131072, 2131 tensor, kèm tower vision (768d) và audio (1024d) — không dùng cho ACC.
- Backend: `D:\models\bin\llama-server.exe` / `llama-cli.exe` có sẵn; `llama_cpp` Python chưa cài; `torch 2.13.0+cpu` có nhưng KHÔNG có trọng số HF. llama-server chỉ lộ embedding đã pooling của lớp cuối (qua `--embeddings`) — **không lấy được residual theo layer mid/¾** như P1 yêu cầu. [GIẢ ĐỊNH — chưa verify]: cần thử endpoint thực tế; nếu cần hidden-state theo layer phải dùng eval-callback C++ hoặc cài llama-cpp-python (chưa làm).
- Hệ quả: P2 dùng embedding lớp cuối 2560d → chiếu cố định lên 4096 (fit trên train, lưu ma trận + SHA). Chưa chạy trích xuất; `[HIỆU NĂNG — CHƯA ĐO]`. G-ENC bắt buộc trước mọi kết luận.
- Lịch sử: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | §8.7 xác minh model.

### 8.8 Thử llama-cpp-python (2026-10-03) `[KẾT QUẢ ÂM — chặn P1 theo layer]`
- Cài `llama-cpp-python 0.3.36` (bản mới nhất trên PyPI, wheel CPU dựng sẵn). Interpreter `python` của shell này là venv Hermes (`C:\Users\LENOVO\AppData\Local\hermes\hermes-agent\venv`) — `gguf`, `llama-cpp-python`, `diskcache` đã cài vào venv đó (dự án chưa có venv riêng).
- **Nạp model FAIL:** `llama_model_load: done_getting_tensors: wrong number of tensors; expected 2131, got 720` — llama.cpp đóng gói trong wheel nhận ra arch `gemma4` nhưng triển khai cũ/khác, không khớp GGUF này. Trong khi `D:\models\bin\llama-server.exe` (build commit a94d563) nạp được model (theo AGENTS.md của 91s_Vivy).
- Máy có g++/gcc/git nhưng KHÔNG có cmake/cl/ninja. Đường khả dĩ: (A) dựng llama.cpp mới + chương trình C++ dùng `cb_eval` bắt tensor `l_out-N`; (B) dựng llama-cpp-python từ source với llama.cpp mới; (C) chỉ dùng embedding lớp cuối qua llama-server (không đủ P1 theo layer).
- Lịch sử: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | §8.8 kết quả thử llama-cpp-python.

### 8.9 Kết quả S2b — ACC-1 (2026-10-03, `[TẠM THỜI]` — ACC-2/3 đang chạy) `[PROTOTYPE]`
Có tune lr đồng đều (lưới `5e-4, 2e-3, 8e-3`, 3 lần thử/arm, chọn trên val seed 0; cả 4 arm đều chọn lr=8e-3 = biên lưới → có thể chưa tối ưu). 5 seed, test OOD (dense/bipartite/wheel/K6-perturbed), CI95 gộp 2500 mẫu. Raw: `results/acc_s2b_acc1.json`, `results/acc_s2_tune_acc1.json`.
| Arm | Params | top-1 gộp [CI95] | pass@8 | regret | vi phạm mask |
|---|---|---|---|---|---|
| H0 prior | 4 096 | 0.102 [0.090, 0.114] | 0.422 | 1.70 | 0 |
| H1 linear r64 | 524 288 | 0.172 [0.158, 0.187] | 0.500 | 1.68 | 0 |
| H2 MLP khớp tham số | 520 255 | 0.194 [0.179, 0.210] | 0.512 | 1.53 | 0 |
| H3 Core E9 (8 rotor) | 528 392 | 0.168 [0.154, 0.183] | 0.446 | 1.76 | 0 |
| H4 E9 bỏ rotor | 528 384 | 0.157 [0.143, 0.171] | 0.462 | 1.70 | 0 |
- **H3 − H4 (ghép cặp theo mẫu):** +0.011, CI95 [−0.007, +0.029] chứa 0 → theo §4 H3 **không** thắng H4: `[ROTOR DƯ THỪA — ủng hộ, trên ACC-1/P5]`. Phù hợp phân tích lý thuyết: rotor cố định-mặt-phẳng là phép trực giao đứng trước `W_c` tuyến tính nên bị `W_c` hấp thụ. Đề xuất cô lập (không xóa) rotor nếu ACC-2/3 cho kết quả tương tự.
- H2 (MLP) cao nhất nhưng chênh H1/H3 nhỏ (CI chồng lấn một phần). Mọi arm chỉ ~0.16–0.19 so với prior 0.10; khoảng cách lớn val (~0.39) → test OOD (~0.17) cho thấy **không khái quát hóa sang đồ thị dày**.
- Chưa kết luận về H5/H6 (chưa dựng). Manifest `commit` = `5a7d4a9` nhưng `run_s2.py` phiên bản có H3/H4 chưa commit lúc chạy [GHI CHÚ].
- Lịch sử: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | §8.9 ACC-1 tạm thời.

### 8.10 Kết quả S2b HOÀN CHỈNH — ACC-1..3 (2026-10-03) `[PROTOTYPE]` (thay phần `[TẠM THỜI]` ở §8.9; §8.9 giữ nguyên làm lịch sử)
Có tune lr đồng đều (3 lần thử/arm, chọn trên val seed 0; hầu hết chọn lr=8e-3 = biên lưới → có thể chưa tối ưu). 5 seed, CI95 gộp 2500 mẫu test. Vi phạm mask = 0 ở mọi arm/tác vụ. Raw: `results/acc_s2b_acc{1,2,3}.json`, `results/acc_s2_tune_acc{1,2,3}.json`; `pytest tests`: 108 passed.
| top-1 gộp (CI95) | H0 prior | H1 linear | H2 MLP | H3 E9+rotor | H4 E9 bỏ rotor | H3−H4 ghép cặp [CI95] |
|---|---|---|---|---|---|---|
| ACC-1 | 0.102 | 0.172 | **0.194** | 0.168 | 0.157 | +0.011 [−0.007, +0.029] |
| ACC-2 | 0.060 | 0.292 | 0.218 | 0.299 | **0.306** | −0.008 [−0.022, +0.007] |
| ACC-3 | 0.003 | 0.003 | 0.002 | 0.002 | 0.005 | −0.003 [−0.006, −0.0004] |
- **Kết luận theo §4 (khóa trước):** H3 không thắng H4 ở bất kỳ bài nào → `[ROTOR DƯ THỪA]` (trên P5, CPU, ≤2500 mẫu/bài). ACC-3 cho CI không chứa 0 nhưng ngược chiều có lợi H4 và cả hai ~ngẫu nhiên (0.2% vs 0.5%) — không có ý nghĩa thực tiễn. Đề xuất **cô lập (không xóa)** phần rotor khỏi đường chính của Core; chờ chủ dự án quyết định.
- ACC-3: mọi arm ≈ prior (≈ngẫu nhiên): hidden/latent P5 + 4 arm đều không học được logarit rời rạc OOD — đúng kỳ vọng §2 (kết quả hợp lệ, đo ranh giới).
- ACC-1: MLP nhỉnh hơn nhóm tuyến tính; ACC-2: nhóm tuyến tính/E9 thắng MLP rõ. Không có arm nào thống trị cả hai bài. Val→test OOD tụt mạnh ở ACC-1 (~0.39→~0.17).
- **Hạn chế:** chưa có H5/H6 → **chưa thể kết luận gì về giả thuyết qudit**. H3 ở đây là bản NumPy train được (mặt phẳng rotor = E9), không phải DLL Core. Manifest ACC-1 ghi commit 5a7d4a9, ACC-2/3 ghi c443878 (code đã commit). Latent là P5 (tổng hợp), chưa dùng hidden-state LLM.
- Lịch sử: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | §8.10 kết quả hoàn chỉnh.
