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
- 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.11 cô lập rotor; §8.12 pre-register H5/H6 + Δ_interaction (tiêu chí khóa bằng code trước khi chạy). Lý do: chủ dự án duyệt 2026-10-04 05:54.
- 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.13 pre-register S2d (H+V, lệch cấu trúc, seed 5–9); §8.14 khung ACC-Q (statevector / MPS, 8/12/24 qudit) + đính chính MPS argmax. Kèm ADR `ADR_2026-10-04_PIGGYBACK_HOST_CPP_RUNTIME.md`. Lý do: chủ dự án duyệt 06:40 và 06:51.

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

### 8.11 Thực thi cô lập rotor (2026-10-04, chủ dự án duyệt) `[PRODUCTION-READY cho đường quyết định; xem rủi ro]`
- **Cách cô lập (không xóa):** rotor được gập vào ma trận chiếu `W_c_active = W_c·R(θ)` lúc nạp/đổi góc (`GeometricWeights::refresh_active_projection`). Đường E9 mặc định (`ROTOR_MODE_ISOLATED`) không còn bước rotor lúc chạy. `W_c` gốc, bảng rotor, `adapt_torque`, `get/set_rotor_angle`, rotor tùy biến trong frame **giữ nguyên hợp đồng**. Đường cũ còn nguyên qua `ROTOR_MODE_LEGACY` (ABI mới `vivyqu_core_set_rotor_mode/get_rotor_mode`, Python `engine.set_rotor_mode('legacy')`).
- **Tương đương:** `tests/test_rotor_isolation.py` 5/5 — 300 mẫu E0 test: quyết định ISOLATED = LEGACY 100%, |Δconfidence| ≤ 9.5e-7; vẫn tương đương sau đổi góc và sau 10 bước thích nghi torque; mode sai bị từ chối, trạng thái không đổi. `pytest tests`: 113 passed.
- **Hiệu năng (bench_e9_latency, 50 000 vòng, cùng máy, chạy xen kẽ 2 lần):** quyết định p50 20.9 → **17.8 µs**, p99 30.1–38.8 → **25.3–25.5 µs**; k* giống nhau (1985).
- **Rủi ro / đánh đổi:** `adapt_torque` ở ISOLATED p50 **274 µs** (LEGACY 31.6 µs) vì mỗi bước phải tính lại `W_c_active` (64×8×1024 phép quay vô hướng). Vẫn dưới ngưỡng test 500 µs, nhưng dòng in “SLA < 60 µs” của `test_hamiltonian_torque_descent` báo FAIL ở ISOLATED. Khuyến nghị: phiên thích nghi online dùng `legacy`. `[HIỆU NĂNG — CHƯA TỐI ƯU]` backlog: vector hóa refresh hoặc cập nhật lười.
- Working set tăng 1 MiB (thêm `W_c_active`); đường nóng ISOLATED vẫn chỉ đọc `W_c_active` + codebook (~2 MiB).
- Lịch sử: 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.11 cô lập rotor.

### 8.12 PRE-REGISTER H5/H6 + Δ_interaction (2026-10-04, chủ dự án duyệt) `[KHÓA TRƯỚC KHI CHẠY — commit này có trước mọi lần chấm test của H5/H6]`
**Arm** (mã: `scripts/acc/harness.py::FactorArm`, `FACTOR_SPECS`). Chung: `z (4096) → h = zA (rank r) → bảng factor out = hB + c (M) → logits = out·G`, `G` (M×4096) là ma trận 0/1 cố định (không học) nối ứng viên với ô trạng thái cục bộ của từng factor. Factor = tập con site có kích thước thuộc `orders`.
| Arm | Site × trạng thái | orders | r | M | Params (lệch so H3 528 392) | Vai trò |
|---|---|---|---|---|---|---|
| `H5_qudit_additive` | 6 qudit × 4 | (1) | 128 | 24 | 527 384 (−0.19%) | Tương hỗ **cộng tính** (chỉ unary) — mốc cho Δ_interaction |
| `H5_qudit_interact` | 6 qudit × 4 | (1,2,3) | 93 | 1 544 | 526 064 (−0.44%) | **H5** — tương hỗ-có-cổng: cặp + bộ ba qudit |
| `H6_qubit_interact` | 12 qubit × 2 | (1,2,3) | 86 | 2 048 | 530 432 (+0.39%) | **H6** — cùng cấu trúc trên qubit, tách "qudit" khỏi "tensor" |

**Quy trình (giống hệt S2b):** P5, n = 2000/500/500, 200 epoch, full-batch Adam, giữ checkpoint tốt nhất theo val; lưới lr `5e-4, 2e-3, 8e-3`, đúng 3 lần thử/arm, chọn trên val seed 0 (`--suite s2c --tune` → `results/acc_s2c_tune_{task}.json`); 5 seed (0–4); test OOD chấm **1 lần**/arm/seed (`results/acc_s2c_{task}.json`). Không mở rộng lưới kể cả khi chọn biên (cùng ngân sách như H1–H4). H0–H4 **tái dùng** từ `results/acc_s2b_*.json`; điều kiện: `dataset_sha` từng seed phải trùng (đã kiểm seed 0 cả 3 bài: khớp).

**Tiêu chí (khóa bằng code `scripts/acc/analyze_s2c.py`, test `tests/test_acc_analyze_s2c.py`):**
- **C1 — H5 được ủng hộ (phạm vi P5/Q1):** trên test OOD, CI95 gộp (bootstrap 2000, 2500 mẫu) top-1 của `H5_qudit_interact` nằm **hoàn toàn trên** CI95 gộp của **từng** arm H1, H2, H4, H6, và H5 có 0 vi phạm mask; đạt ở **≥ 2/3** bài. Ghi chú: chỉ dùng top-1 — **chặt hơn** §4 (bỏ nhánh "hoặc regret"); quyết định trước khi thấy dữ liệu. Theo §4, kết quả trên P5 thỏa vế "G-ENC pass hoặc cùng kết quả trên P5"; lần chạy lại trên hidden-state thật (S4) báo cáo riêng.
- **C2 — tương tác có đóng góp:** `Δ_interaction` = hiệu **ghép cặp theo mẫu** `H5_qudit_interact − H5_qudit_additive`; đóng góp khi cận dưới CI95 > 0 ở **≥ 2/3** bài. Nếu không → ghi `[TƯƠNG TÁC KHÔNG ĐÓNG GÓP NGOÀI CỘNG TÍNH]`.
- **C3 — chỉ báo cáo:** `Δ_qudit = H5_qudit_interact − H6_qubit_interact` ghép cặp (CI95).
- **Hệ quả khóa trước:** C1 fail → README ghi `[GIẢ THUYẾT QUDIT CHƯA ĐƯỢC ỦNG HỘ — P5/Q1]` và chuyển Pha Q2 (§8.2) chỉ thiết kế biến thể từ chỗ thất bại; C1 pass → chưa tuyên bố chung, phải lặp lại trên hidden-state thật (S4) với cùng tiêu chí.
- **Rủi ro đã biết trước khi chạy:** ACC-3 mọi arm ≈ ngẫu nhiên ở S2b → nhiều khả năng ACC-3 không đạt C1/C2 với bất kỳ arm nào; vì vậy C1/C2 thực tế phải đạt ở cả ACC-1 **và** ACC-2.
- Lịch sử: 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.12 pre-register H5/H6.

### 8.13 PRE-REGISTER S2d — Đề xuất+Kiểm chứng (H+V) và Lệch cấu trúc (2026-10-04 06:40, chủ dự án duyệt) `[KHÓA TRƯỚC KHI CHẠY — chưa có code]`
**Khai báo trung thực về thời điểm:** lúc viết mục này, S2c ACC-1 đang chấm test top-1 (seed 0–3). Agent **chưa xem** số top-1 test (đã che trong log) và **chưa xem** pass@K của S2c. Để không chạm lại tập test đã dùng, **S2d dùng seed mới 5–9** (5 seed; dữ liệu train/val/test sinh mới theo `make_split`). Seed 0–4 không dùng cho S2d.

**Thí nghiệm D1 — Đề xuất + Kiểm chứng (H+V).** Mỗi arm học (H1, H2, H4, H5_qudit_interact, H6_qubit_interact) đề xuất top-K (K = 8, trong mask), sau đó verifier exact của bài chọn ứng viên tốt nhất: ACC-1 chọn cost nhỏ nhất, ACC-2 chọn năng lượng nhỏ nhất, ACC-3 chọn x thỏa phương trình. Dùng **cùng** V cho mọi arm.
- Metric chính: `top1_V` theo từng mẫu = 1 nếu ứng viên V chọn thuộc tập đúng (với cả ba bài, giá trị này bằng pass@K theo từng mẫu). Metric phụ: `regret_V` (ACC-1/2) và độ trễ.
- **D1-C (ủng hộ):** CI95 gộp `top1_V` của H5 nằm hoàn toàn trên CI95 của từng arm H1+V, H2+V, H4+V, H6+V ở ≥ 2/3 bài; 0 vi phạm mask.
- **D1-L (ngân sách thời gian, báo cáo riêng):** độ trễ H5 + top-K + V đo bằng bản C++ ≤ 1 ms p99 trên máy này. Chưa có bản C++ → ghi `[CHƯA ĐO]`, không suy ra từ NumPy.
- Tham chiếu: H7 (vét cạn 4096) báo cáo kèm, không phải đối thủ.

**Thí nghiệm D2 — Lệch cấu trúc** (tách "qudit" khỏi "biết trước cách chia site").
- `H5_qudit_misaligned`: giống `H5_qudit_interact` (6×4, orders 1–3, r = 93, 526 064 params) nhưng 12 bit của ứng viên được hoán vị cố định trước khi gom cặp thành site, nên site của mô hình **không** trùng site của bài. Hoán vị sinh từ `np.random.default_rng(20261004).permutation(12)`, **loại** hoán vị chỉ đổi chỗ trong cặp hoặc đổi thứ tự cặp (sinh lại tới khi có ≥ 4 cặp bị phá).
- `H6_qubit_order4`: 12 qubit, orders 1–4, M = 9 968, r = 37, 530 336 params (+0.37%). Arm qubit **đủ khả năng biểu diễn** factor cặp-qudit (4 bit).
- **D2-A:** `Δ_align` = hiệu ghép cặp `H5_qudit_interact − H5_qudit_misaligned`. Nếu cận dưới CI95 > 0 ở ≥ 2/3 bài **và** `H5_qudit_misaligned` không vượt `H6_qubit_interact` (CI chồng lấn hoặc thấp hơn) → ghi `[ƯU THẾ ĐẾN TỪ CẤU TRÚC BIẾT TRƯỚC, KHÔNG PHẢI QUDIT]`.
- **D2-Q:** `H5_qudit_interact − H6_qubit_order4` ghép cặp. Nếu CI95 chứa 0 hoặc âm ở ≥ 2/3 bài → ghi `[QUDIT KHÔNG HƠN QUBIT ĐỦ BẬC]`.

**Quy trình chung:** P5, n = 2000/500/500, 200 epoch, lưới lr và 3 lần thử như §8.12. Arm đã tune giữ nguyên lr từ `acc_s2_tune_*` / `acc_s2c_tune_*`; arm mới (`H5_qudit_misaligned`, `H6_qubit_order4`) tune 3 lần trên val seed 0 (không chạm test). Mỗi arm/seed chấm test 1 lần. Lưu `ok`, `passk_ok` theo từng mẫu. Kết quả ghi vào `results/acc_s2d_*.json`. Code và test của `analyze_s2d.py` phải commit **trước** khi chạy seed 5–9.
- Lịch sử: 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.13 pre-register S2d (D1 H+V, D2 lệch cấu trúc).

### 8.14 PRE-REGISTER ACC-Q — Hai hướng mô phỏng chồng chập, quy mô 8/12/24 qudit (2026-10-04 06:55, chủ dự án duyệt) `[KHÓA KHUNG ĐÁNH GIÁ — chưa có code; chạy sau ADR piggyback]`
**Mục tiêu (chủ dự án):** mô phỏng đặc tính **chồng chập** (superposition) của qubit/qudit, **để ngỏ ít nhất 2 hướng**, không chọn trước hướng thắng. Mốc 32 qubit = suy luận từ giới hạn RAM.

**Ràng buộc phần cứng đã đo (2026-10-04):** RAM 23.3 GB, L3 16 MB, 6 lõi / 12 luồng (Ryzen AI 5 340). Statevector complex64 = 8 B × 2ⁿ:
| qubit (qudit-4) | Bộ nhớ | Vai trò |
|---|---|---|
| 16 (8) | 512 KiB | Runtime, cỡ µs–ms |
| 20 (10) | 8 MiB (vừa L3) | **Trần runtime "ms"** |
| 24 (12) | 128 MiB | Nghiên cứu |
| 30 (15) | 8 GiB | Trần nghiên cứu thực tế khi Gemma (8.6 GB) đang nạp |
| 32 (16) | 32 GiB | **Vượt RAM** → mốc 32 qubit = trần lý thuyết, không phải mục tiêu chạy |
Lưu ý: 1 qudit-4 = 2 qubit; **24 qudit = 48 qubit → không thể dùng statevector**.

> **[REPLACED 2026-10-04 07:17 — dòng "20 (10) | 8 MiB (vừa L3) | Trần runtime 'ms'" và "16 (8) | Runtime, cỡ µs–ms" ở bảng trên bị THAY THẾ bởi số đo K2; bảng gốc giữ nguyên làm lịch sử]**
> Vừa bộ nhớ ≠ vừa ngân sách tính toán: một lớp mạch dày (n cổng 1-qudit + n−1 cổng 2-qudit 16×16) tốn ≈ 16·4ⁿ·(n−1) phép nhân-cộng phức. Đo K2 (complex128, vô hướng, `-O2 -fcx-limited-range`, CPU có tiến trình nền): **n=6: 0.29 ms/lớp · n=8: 7.1 ms/lớp · n=10: 198 ms/lớp**. Hệ quả: hướng A chỉ nằm trong ngân sách "ms" ở **n ≤ 6–7 qudit** với vài lớp; n=8 là cỡ chục ms; n ≥ 10 chỉ để nghiên cứu. SIMD/complex64 có thể cải thiện hằng số (ước ~2–4× `[GIẢ ĐỊNH]`), không đổi bậc tăng 4ⁿ.

**Hướng A — Statevector exact (Born machine có điều kiện):** ψ(z) = U_L(θ, z)⋯U_1(θ, z)|0⟩ trên n qudit; cổng 1-qudit và 2-qudit tham số hóa, góc = hàm tuyến tính của z; P(k) = |ψ_k|² trên 4ⁿ ứng viên (= ứng viên của bài). Áp dụng cho ACC-8 (16 qubit) và ACC-12 (24 qubit, chỉ nghiên cứu).
**Hướng B — Tensor network / MPS (Born machine có điều kiện):** ψ(s|z) = A₁[s₁](z)⋯Aₙ[sₙ](z), bond χ ∈ {4, 8, 16}; tensor lõi = ánh xạ hạng thấp từ z. Áp dụng ACC-8, ACC-12, ACC-24.
- **Đính chính (2026-10-04, agent tự sửa phát biểu trong thảo luận trước):** với MPS χ > 1, **argmax |ψ(s)|² nói chung KHÔNG giải exact được bằng Viterbi** (biên độ là tổng theo đường bond, không phải max-product). Phần exact và rẻ của MPS là **lấy mẫu Born chính xác** O(n·d·χ²)/mẫu và tính xác suất biên. Vì vậy hướng B ra quyết định bằng **lấy mẫu K + verifier** (giống D1 §8.13) hoặc beam search; Viterbi exact chỉ đúng cho **factor graph dạng chuỗi** (log-tuyến tính), là arm đối chứng cổ điển.

**Bài:** ACC-8 và ACC-12 = mở rộng ACC-1 (tô 4 màu, n đỉnh) và ACC-2 (clock spin 4 trạng thái, n site), giữ split OOD cùng triết lý (thưa→dày; họ cấu trúc chưa thấy). ACC-3 không mở rộng (đã ≈ ngẫu nhiên ở n=6).
- Nhãn exact: ACC-8 vét cạn 65 536; ACC-12 vét cạn 16.7 triệu bằng C++ (không Python) hoặc solver exact; ACC-24 **không có nhãn tối ưu chứng minh được trong mọi trường hợp** → dùng best-known từ solver (CP-SAT / branch-and-bound), ghi rõ gap của solver.

**Arm (cùng ngân sách tham số ±5% trong mỗi quy mô, cùng lưới lr/3 thử):** A-statevector, B-MPS(χ), đối chứng cổ điển: factor qudit (H5 mở rộng, orders 1–2) + giải mã (vét cạn nếu ≤ 8, max-product/beam nếu ≥ 12), MLP (H2), và ở ACC-24 thêm local search/simulated annealing có cùng ngân sách thời gian.

**Metric khóa trước:** top-1 (ACC-8/12), regret so với tối ưu exact (ACC-8/12) hoặc best-known (ACC-24), pass@K + verifier (K=8), độ trễ quyết định p50/p99 bằng C++ (Python chỉ để huấn luyện), bộ nhớ đỉnh. 5 seed, CI95 bootstrap gộp, test OOD chấm 1 lần.
**Tiêu chí đọc kết quả (không chọn trước hướng thắng):**
- Một hướng được coi là **"có giá trị"** ở một quy mô khi CI95 gộp của nó (top-1 hoặc top1_V) nằm hoàn toàn trên CI95 của **mọi** đối chứng cổ điển ở ≥ 1 bài (ACC-1-mở rộng hoặc ACC-2-mở rộng), **và** độ trễ p99 ≤ 1 ms nếu quy mô thuộc vùng runtime (≤ 20 qubit).
- ACC-24: nhãn `[KHÁM PHÁ]`, chỉ báo cáo regret và thời gian; **không** dùng để tuyên bố ủng hộ giả thuyết cho tới khi ACC-12 có kết quả.
- Cả hai hướng thua đối chứng cổ điển → ghi `[CHỒNG CHẬP MÔ PHỎNG KHÔNG CHO LỢI THẾ BIỂU DIỄN — quy mô n]`.
**Phản biện đã ghi nhận trước:** mô phỏng chồng chập trên máy cổ điển lưu tường minh 2ⁿ biên độ; không có tăng tốc tính toán so với vét cạn. Giá trị nếu có là **biểu diễn/khái quát**, và đó là thứ suite này đo.
- Lịch sử: 2026-10-04 | Antigravity (Claude Opus 5.5) | §8.14 pre-register khung ACC-Q (A statevector, B MPS) + đính chính MPS argmax.



