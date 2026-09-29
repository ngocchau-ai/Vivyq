# VivyQu: phản biện, review hiện trạng và hướng nghiên cứu tiếp theo

**Trạng thái: DRAFT — đề xuất nghiên cứu, chưa khóa kiến trúc và chưa nghiệm thu sản phẩm.**

Ngày: 2026-09-28. Tác giả: Vy / subagent `critique_research`, với kết quả review độc lập từ `latest_boundary_review` và `latest_math_evidence`. Phạm vi: tài liệu, mã nguồn và nghiên cứu gốc. Không chạy DLL hay benchmark VivyQu trong lượt viết này; không thay đổi mã hoặc tài liệu hiện hữu. Tài liệu này chưa được đồng bộ sang `D:\2brain`.

## 1. Cách xử lý phản biện người dùng cung cấp

Nguồn: attachment `Pasted text.txt`, thư mục `aef8b65b-7b70-4ce4-9abe-37c4e1e006dd`.

| Luận điểm | Quyết định nghiên cứu |
|---|---|
| VivyQu có D=4096, tương đương 12 qubit hoặc 6 qudit(4) | Đúng với nhánh Hilbert. Đóng khung rõ phạm vi. Một statevector complex128 là 64 KiB; toàn bộ hệ thống còn encoder, weights, workspace và verifier. |
| Phân tích 30 qubit không áp dụng trực tiếp cho lõi 4096 chiều | Đúng. Tuy nhiên người dùng đã nêu khả năng mô phỏng khoảng 30 qubit trên PC 16 GB; phần giới hạn đó trả lời bối cảnh mở rộng, không phải bằng chứng VivyQu cần 30 qubit. |
| Cầu nối ngữ nghĩa cần học | Là phương án đáng thử, không phải định lý bắt buộc. Cầu nối thủ công có thể đủ trong một bài toán có cấu trúc; học ánh xạ feature→score/amplitude khi dữ liệu cho thấy cần. |
| `candidate_id ↔ basis` phải học | Cần sửa: giữ codec danh tính cố định, có phiên bản và đảo được; học biểu diễn/điểm/biên độ trên codec đó. ID chính xác và feature có nghĩa giải quyết hai trách nhiệm khác nhau. |
| Huấn luyện trên held-out | Sai nếu held-out được dùng để báo cáo generalization. Train để học, validation để chọn, calibration để hiệu chỉnh, test đóng băng để đánh giá cuối. |
| Qudit ít gate nên giúp dưới 10 µs | Có thể đúng cho gate set/bài toán cụ thể trên phần cứng lượng tử; chưa suy ra FLOPs, memory traffic hoặc latency thấp hơn trên CPU. Phải so kernel cùng phép biến đổi. |
| E0 oracle tổng hợp có thể làm ngay | Hợp lý để kiểm chứng số học và đo chi phí; không đủ chứng minh cầu nối ngữ nghĩa hoặc lợi thế ứng dụng. Không loại toàn bộ chương trình chỉ vì một oracle tuyến tính không phù hợp thua. |
| Cho phép kết luận quantum-inspired chưa giúp | Giữ. Báo cáo phạm vi dữ liệu, ngân sách và phương pháp cụ thể; không khái quát vượt phép thử. |

Nhánh chính hiện ghi `Cl(12)` không đồng nhất với sáu qudit phức. `Cl(12,0)` có 4096 hệ số thực; Hilbert `C^4096` có 8192 bậc tự do thực trước chuẩn hóa. Việc bằng số hệ số không chứng minh hai kiến trúc có cùng biểu diễn hay động lực.

Ngay cả rotor sandwich đúng cũng bảo toàn từng Clifford grade; scalar và pseudoscalar bất biến dưới proper rotation. Spin(12) có 66 tham số liên tục, là bias cấu trúc hẹp hơn phép quay tùy ý trên 4096 hệ số. Gán arbitrary latent coordinates vào blades chưa chứng minh tối ưu tùy ý 4096 ứng viên. Đây là suy luận đại số cần kiểm tra theo bài toán, không là kết luận mọi nhánh Clifford thất bại. E0-Q định nghĩa semantic factors base4 rõ; có thể thử true Clifford như một nhánh hạn chế riêng sau khi sửa induced action.

## 2. Hướng tiếp theo: E0-Q với sáu yếu tố bốn trạng thái

**Đề xuất có thể kiểm chứng:** chọn cấu hình không gian cho một vật thể trong cảnh, với

\[
a=(a_0,\ldots,a_5)\in\{0,1,2,3\}^6,\qquad
k(a)=\sum_{i=0}^{5}a_i4^i\in[0,4095].
\]

Ví dụ sáu yếu tố: X, Y, Z, hướng, kích thước và vật liệu; mỗi yếu tố có bảng bốn giá trị vật lý cố định. Bảng giải mã có version và checksum. Không gọi 4096 cấu hình là 4096 thế giới độc lập. Các tên yếu tố phải được chọn theo ứng dụng thực tế trước khi khóa dữ liệu.

Với cảnh `s`, mục tiêu:

\[
E_s(a)=\sum_i u_{s,i}(a_i)
 +\sum_{(i,j)\in G_s}J_{s,ij}(a_i,a_j)
 +\lambda\,r_s(a).
\]

`u` là chi phí từng yếu tố; `J` là tương tác cặp; `r` là chi phí phi tuyến như khoảng cách, ổn định hoặc công năng. `G_s` có cạnh liên yếu tố, không chỉ sáu bài toán độc lập. Ràng buộc cứng kiểm tra ít nhất va chạm, vùng cho phép và tương thích kích thước/vật liệu; không chỉ mask ngẫu nhiên. Định nghĩa rõ trường hợp không có nghiệm, tie và sai số số học.

Oracle độc lập quét đủ 4096 cấu hình và kiểm tra hình học/hàm mục tiêu bằng implementation tham chiếu. Oracle tạo nhãn train và đánh giá; toàn bộ thời gian oracle phải được tính khi oracle là baseline runtime. Nếu mask/oracle đã được cung cấp miễn phí cho một nhánh thì các nhánh khác nhận cùng thông tin và phải báo riêng chi phí tạo mask/oracle.

Dữ liệu tách theo **cảnh/seed sinh cảnh**, không chỉ theo hàng feature. Thêm test ngoài phân phối: hình học mới, tương tác mạnh hơn, ít nghiệm, không có nghiệm và optimum gần hòa. Cảnh trùng hoặc biến thể gần trùng không đi qua hai split. Hidden feature từ LLM/image encoder chỉ thêm sau khi có bài toán rõ; encoder giữ cố định và được đo riêng. Đề xuất học offline đầu nhỏ không đồng nghĩa huấn luyện toàn bộ LLM.

## 3. Ba nhánh tối thiểu và điều kiện giữ

| Nhánh | Cơ chế | Câu hỏi cần trả lời |
|---|---|---|
| A: real structured | Đầu học có cấu trúc/low-rank hoặc butterfly, xuất score 4096 ứng viên | Mốc chất lượng, latency và RAM thực dụng; luôn có thêm baseline exact feasible-energy scan 4096 trong E0-Q analytic này. |
| B: phase + mixing | Feature→amplitude, các phase gate xen mixing có cấu trúc, Born readout rồi hard mask | Pha có tăng chất lượng/cost tradeoff so với real transform cùng ngân sách? |
| C: bounded MPS | Sáu chỉ số vật lý d=4, bond χ=4 hoặc 8, học score/phân phối phù hợp | Có giảm bộ nhớ và giữ tương quan cần thiết? Có mất nghiệm tốt khi rank bị giới hạn? |

Giữ cùng dữ liệu, input, số lần truy cập verifier và ngân sách tuning. Công bố số tham số chính xác; không giả vờ cùng số tham số luôn tương đương cùng FLOPs. Có comparator real với cùng topology mixing của B. Nhánh C chỉ cần nếu cấu trúc dữ liệu gợi ý rank thấp; statevector 4096 đã nhỏ, MPS không tự là lựa chọn nhanh hơn.

**Bắt buộc ablation:** bỏ pha; bỏ mixing; real/complex cùng topology; học/không học cầu nối; không có phase cuối; χ4/χ8 và dense reference; oracle đầy đủ so với top-k proposal; nhãn sạch so với cảnh mới. Nếu fixed transform cộng free linear readout gộp được thành một linear map, benchmark thêm map đã gộp.

Hướng theo đuổi tốc độ cụ thể ở chế độ rotor đóng băng: nếu `z=W_c(Rh)`, tiền tính `W_eff=W_c R` để `z=W_eff h`, rồi benchmark cùng decision function với mask/cost giữ đúng. Adaptive rotor thay đổi thì phải cập nhật folded weights và tính cả chi phí cập nhật. Đây là tối ưu đại số có điều kiện, không là bằng chứng tăng tốc lượng tử. Cầu nối dense MLP có thể vượt 64 KiB dù state vừa cache; thử shared/factor blocks hoặc phase coefficients nhỏ và báo riêng state/weights/workspace.

Pha đường chéo ở ngay trước Born readout không thay đổi phân phối:

\[
|e^{i\theta_k}c_k|^2=|c_k|^2.
\]

Muốn pha tác động đến lựa chọn phải có mixing sau pha hoặc readout nhạy pha được đặc tả. Bảo toàn norm không chứng minh semantic reliability; unitary evolution cũng không tự bảo đảm gradient descent trên hàm năng lượng.

## 4. Ngân sách và phép đo

| Đối tượng | Ngân sách/số học | Điều chưa gồm |
|---|---|---|
| Statevector D4096 | 64 KiB complex128; 32 KiB complex64 | Input, copy, scratch, gates, weights, encoder, verifier |
| Dense transform D×D | 64 MiB float32; 256 MiB complex128 | Workspace và training |
| Codebook 4096×4096 | Cùng ngân sách dense trên | Không được gọi là hệ thống 64 KiB |
| Codebook 4096×64 | 1 MiB float32 | Cầu nối 4096×64 thêm 1 MiB, chưa gồm các buffer khác |
| MPS χ8 | Σᵢ4χᵢχᵢ₊₁; upper estimate 1536 complex coefficients = 24 KiB complex128 | Workspace, feature bridge, readout, giải nén dense, verifier |

Rank Schmidt tối đa ở giữa sáu qudit là `4^3=64`; χ8 là giới hạn biểu diễn có chủ đích. Khi materialize dense amplitudes, tính thêm statevector. Top-k từ MPS không tự có chi phí như sampling; phải đặc tả cách tìm top-k hoặc quét 4096 cấu hình.

Tương tác cặp tùy ý không bảo đảm bond χ8 đủ; graph, thứ tự yếu tố và coupling strength ảnh hưởng rank. Nếu chuyển sang bài toán surrogate có energy chưa biết đầy đủ, khóa riêng ngân sách truy cập oracle/verifier cho mọi nhánh; không dùng khả năng truy cập privileged để làm thắng baseline.

Với statevector D và local gate q×q dày, có D/q block, khoảng Dq phép nhân phức: gate một qudit(4) khoảng 4D, gate hai qudit(4) khoảng 16D. Đây là đếm phép nhân, không phải số FLOPs đầy đủ và không phải số đo latency. Gate nhỏ có thể fuse, sparsity có thể giảm chi phí; phải tính số lượt đọc/ghi bộ nhớ và benchmark compiler/kernel thật.

**64 KiB và <10 µs là mục tiêu hoàn mỹ**, ghi rõ là vector state và Core call nào. Báo p50/p95/p99 trên batch=1; cold/warm, allocation/copy, thread count, precision, clock, mẫu lặp và sai số timer. Báo RAM đỉnh toàn tiến trình, resident weights và total workspace. Đo cả input→decision→verifier và encoder→action; tốc độ riêng Core chưa phải tăng tốc toàn luồng.

Kết quả chính: regret so exact feasible optimum, success/constraint violation sau verifier, recall optimum trong top-k, lượng verifier work và latency/RAM ở cùng quality. Ngưỡng nghiệm thu phải khóa trước test; không chọn ngưỡng sau khi xem kết quả. Test không có nghiệm phải từ chối, không tự chọn k=0.

## 5. Verifier và calibration

Proposal trả `(candidate_id, raw_score, distribution_version, mask_version)`; confidence là field riêng có calibration version. Verifier kiểm tra lại action decode, ràng buộc và mục tiêu từ dữ liệu cảnh độc lập. Nó không chỉ kiểm tra norm hoặc dùng lại score của mạng. Nếu verifier từ chối tất cả, NPS nhận no-valid-candidate và tiếp tục vòng đời giả thuyết.

Calibration cần định nghĩa event: ví dụ ứng viên được chọn có feasible regret ≤ δ. Xác suất Born trên các candidate không tự là xác suất event này. Temperature scaling trên log-probabilities có thể hiệu chỉnh phân phối chọn, nhưng không tự giải quyết confidence correctness; đo reliability, NLL/Brier và coverage-risk theo event. Fit calibration trên phần dành riêng; test và OOD không dùng để fit. Confidence hiệu chỉnh không thay quyền phê duyệt hành động của NPS/Cầu Treo.

## 6. Review bằng chứng đang có

### 6.1. M1–M4 chưa chứng minh tăng tốc LLM

`tests/microbench/test_quantum_llm_acceleration_bench.py:50–63` gán 25 ms/token, 280 token CoT và 30 token kết luận. Token reduction là số học từ hằng số; TTFA ratio so CoT giả lập với riêng Core. Không có log gọi model thật. Plan `VIVYQU_LLM_QUANTUM_ACCELERATION_PLAN.md:28–31` đánh dấu ĐẠT vượt phạm vi đó.

M3 tại dòng 104–106 chèn trước high-logit token vào mask. Dòng 118–120 dựng phân phối zero ngoài mask nhưng không tính KL; assert 130–131 chỉ top1/pruning. Không đo ma trận unembedding, chỉ random logits/softmax. Với positive full softmax mass bị zero, KL(Pfull||Pmasked) là vô hạn; mục tiêu ≤0.005 cần định nghĩa distribution/fidelity đúng và không dùng prior biết đáp án.

M2 cần draft distribution, verifier target, rejection/correction và đo overhead thật. Nghiên cứu speculative decoding bảo toàn **phân phối**, không hứa chuỗi giống bit-for-bit dưới cùng seed. M4 rotor cố định không bảo đảm nén KV arbitrarily dài vào 4096 số với full fidelity và O(1) latency; recurrent lossy summary cần kiến trúc attention phù hợp, học và chất lượng đo độc lập.

### 6.2. Synthetic loss chưa chứng minh quantum/semantic gain

`scripts/train_branches_b_c.py:86–92,237–244` huấn luyện readout để khôi phục `train_latents @ proj_matrix` đã biết từ oracle; C rotors cố định ở 214–223. Đây có thể là distillation tuyến tính hợp lệ nếu gọi đúng tên. Fixed invertible transform + free linear map không tạo hypothesis class mới; map gộp phải là baseline. Train MSE thấp chưa đủ chứng minh bridge ngữ nghĩa, phase learning hay navigation quality. Phản biện mới cũng không được dùng synthetic oracle làm tiêu chuẩn duy nhất để loại mọi ứng dụng khác.

### 6.3. Boundary review độc lập: lỗi đang còn trong source

Kết quả `latest_boundary_review` là source inspection và isolated Python repro; chưa execute DLL:

| Mức | Vị trí | Vấn đề cần sửa trước tích hợp |
|---|---|---|
| P1 | `python/vivyqu/engine.py:243–270,316–323` | `memmove` input/mask và fast path thiếu hợp đồng dtype/shape/contiguity/status đầy đủ. |
| P1 | `python/vivyqu/cautreo_harmonizer.py:199–244` | Public float32 input giữ dtype rồi copy 32768B từ allocation 16384B: nguy cơ đọc vượt buffer. |
| P1 | `src/core/geometric_scorer.cpp:406–429` | Custom rotor path thiếu guard plane<12; plane_j=12 có thể tạo index ngoài h_buf D4096. Ordinary rotor implementation có guard; custom path cần cùng boundary contract. |
| P1 | `python/vivyqu/engine.py:341–360`; `python/vivyqu/watchdog.py:182–208` | Empty mask có thể argmax(all −inf)→k0, is_valid=True. Isolated mock repro đã xác nhận, không phải DLL runtime. |
| P1 | `python/vivyqu/engine.py:374` | Fallback thiếu weights tham chiếu ERR_CORE_TIMEOUT chưa import; isolated repro báo NameError. |
| P1 | `src/core/c_api.cpp:25,35–47,81–89` | Shared global context/reset/free không lock, nhiều engine có thể reset/free trạng thái đang dùng. ctypes C call giải phóng GIL nên cần hợp đồng ownership/concurrency. |
| P1 | `python/vivyqu/cautreo_harmonizer.py:255–272` | Fallback lấy is_valid từ old C output, không lấy từ watchdog result. |

Old E9 dispatch mismatch đã được report là **source-fixed** (`c_api.cpp:181–184`, scorer:140–148); không giữ nó như blocker hiện tại. Source-fixed chưa xác nhận binary đang load đã rebuild hoặc có semantic acceptance.

### 6.4. Review toán học và provenance độc lập

Kết quả `latest_math_evidence`, source đọc ổn định; phép tái hiện gradient là JS số học độc lập, không phải gọi VivyQu DLL:

| Mức | Vị trí | Kết quả và hành động |
|---|---|---|
| P1 | `tests/test_grand_prix_e9.py:318–335,386` | Aggregate latency mặc định 28.50/38.10/79.10 µs; ROOT_DIR không định nghĩa trong nhánh đo, exception bị bỏ qua; output vẫn ghi empirical. Raw JSON khớp defaults. Tách modeled/default khỏi measured, fail thiếu phép đo và lưu raw sample+binary hash. Bench C++ và C crossval riêng có tồn tại: không suy ra chưa từng chạy binary trong lịch sử. |
| P1 | `src/core/rotor_spin12.cpp:74–75`; `src/core/geometric_scorer.cpp:216` | Cùng sign giữa grade làm sai sandwich rotor: plane02 đưa e0→c e0+s e2, giữ e1 thì e01 phải→c e01−s e12; pair3,6 code dùng plus. Cần kiểm tra induced action trên blades trước gọi là Spin(12) sandwich. |
| P1 | `src/core/geometric_scorer.cpp:508–531,586` | Mọi generator dùng final h/g, thiếu chain rule cho noncommuting rotors. Repro tám rotor thực với x khác 0 tại indices `[1,2,64]`, values `[1,2,3]`, linear loss gradient tại cùng indices `[-1,-3,3]`: torque0 +2.182306552 nhưng finite derivative −0.411770293; update theta0 theo code với step .001 tăng positive loss 2.985187204→2.986101551. Cần intermediate-state/adjoint derivative và finite-difference gate. |
| P2 | `src/core/geometric_scorer.cpp:580–599` | Hinge đã zero vẫn update; cần zero-gradient/loss gate và acceptance bảo đảm hành vi mong muốn. |
| P1 | `scripts/train_baseline_a2.py:75`; `scripts/train_branches_b_c.py:81,238` | Ridge alpha A/C=1e−4, B=1; cùng teacher linear projection và broad linear readout. Transform orthogonal với cùng alpha có đối chứng basis invariant; so hiện tại không đủ kết luận B kém vì Hilbert. Khóa tuning budget/control trước xếp hạng. |
| P2 | `tests/test_grand_prix_e9.py:390` và phần gate sau đó | Gate chủ yếu regret, hardcode champion/PASS; cần derive mọi gate từ measurements và contract, không từ tên nhánh. |

Đã sửa trong source theo reviewer: E9 C++ scorer/CAPI dispatch, little-bitorder, normalized-regret denominator, binary header64/packing, B FWHT/readout và mô tả state-vs-parameters. Chúng không là lỗi hiện hành trong memo. Hợp nhất ưu tiên thành tám nhóm: memory boundary; empty-mask/fallback; context ownership; E9 provenance; rotor algebra; gradient/zero-loss update; fair controls/gates; M1/M3 evidence. M4 và semantic bridge là giả thuyết cần thực nghiệm, không tự coi là crash bug.

Feature concatenation trong harmonizer và Gaussian E0 chưa chứng minh cầu nối semantic; đây là giới hạn suy luận bằng chứng. Vòng đời NPS và giải mã fixed ID vẫn hữu ích trước khi học bridge.

### 6.5. Snapshot và phạm vi chứng cứ

Snapshot riêng của tác giả trong lượt đọc ngày 2026-09-28:

| File | LastWriteTimeUtc | SHA256 |
|---|---|---|
| `docs/MATH_SPEC_BLUEPRINT.md` | 2026-09-27 04:27:22 | `91393EEAC5A504FB2308972117DC5B8F855FE4C7EBFD69518770154DC333B4F0` |
| `docs/VIVYQU_LLM_QUANTUM_ACCELERATION_PLAN.md` | 2026-09-27 14:00:48 | `EED13F08CF7518F5ADAE27D7B7A6126642C45DE933EDC768F656EFBCC29D015F` |
| `scripts/train_branches_b_c.py` | 2026-09-27 11:21:33 | `B9011A9DE55AFBB91FB11F62BEADA5EA407AADBA722B5586FF96BD055147ADB2` |
| `tests/microbench/test_quantum_llm_acceleration_bench.py` | 2026-09-27 14:02:19 | `FF5B70B69CA15A88B8EDA21E545B0AFF56F13C4EFBC297B212EC60D33FE8FA84` |

Antigravity có thể đang chỉnh đồng thời. Findings áp dụng snapshot đã đọc; review lại current diff trước sửa hoặc nghiệm thu. Không chuyển green tests/hashes thành bằng chứng sản phẩm hoàn chỉnh.

Snapshot reviewer toán học trước/sau đọc không đổi (mtime Asia/Saigon 2026-09-27):

| Artifact | Mtime +07 | SHA256 |
|---|---|---|
| `src/core/geometric_scorer.cpp` | 19:08:25 | `76DA55DF99CCD9FB885307771664743EC0A7923CEA4CE296588BE823468E33AA` |
| `src/core/rotor_spin12.cpp` | 15:24:10 | `D84627F81A4B0C548EFE8FE0F997AB071AE18883A4E48A5C32ECB9DBCB1F3CA0` |
| `tests/test_grand_prix_e9.py` | 18:43:14 | `416C9B99F329771CE5A10DAB2FD17710F19080478A6FE83B5D76BF2CC2137FA7` |
| `results/grand_prix_e9/grand_prix_e9_results.json` | 18:47:20 | `57242B6EC3F1E7AD12A72EC5920A8725182672EE608B24977DDDEB28CD9B7493` |

## 7. Nghiên cứu gốc và điều thực sự được hỗ trợ

1. Dao et al., [Learning Fast Algorithms for Linear Transforms Using Butterfly Factorizations](https://proceedings.mlr.press/v97/dao19a.html), ICML 2019: học transform dạng sparse products, O(NlogN), có thí nghiệm compress/classification. Hỗ trợ lựa chọn structured bridge; không chứng minh VivyQu 10 µs.
2. Arjovsky et al., [Unitary Evolution Recurrent Neural Networks](https://proceedings.mlr.press/v48/arjovsky16.html), ICML 2016: ghép structured matrices để học unitary và thực nghiệm long dependency. Hỗ trợ parameterization; không chứng minh mọi rotor sẽ tối ưu năng lượng.
3. Stoudenmire–Schwab, [Supervised Learning with Tensor Networks](https://papers.neurips.cc/paper_files/paper/2016/hash/5314b9674c86e3f9d1ba25ef9bb32895-Abstract.html), NeurIPS 2016: MPS/tensor train supervised image classification. Hỗ trợ nhánh học tensor, không là benchmark VivyQu.
4. Han et al., [Unsupervised Generative Modeling Using Matrix Product States](https://arxiv.org/abs/1709.01662), PRX 2018: probabilistic/Born interpretation, tensor learning và direct sampling. Hỗ trợ mô hình phân phối; top-k tối ưu là câu hỏi riêng.
5. Guo et al., [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html), ICML 2017: calibration và temperature scaling. Hỗ trợ calibration trên data riêng; norm/Born không tự là confidence đúng.
6. Kurkcuoglu et al., [Quantum simulation of phi4 theories in qudit systems](https://arxiv.org/abs/2108.13357): cấu trúc multi-level cho field interaction bằng diagonal single-qudit gates. Gustafson, [Prospects for simulating a qudit-based model of scalar QED](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.103.114505): minh họa cost savings qutrit encoding trong bài toán/gate set cụ thể. Hỗ trợ chọn factor theo physics; không chứng minh classical CPU speedup chỉ từ gate count.
7. Leviathan et al., [Fast Inference from Transformers via Speculative Decoding](https://proceedings.mlr.press/v202/leviathan23a.html), ICML 2023: draft và verification để tăng tốc, bảo toàn output distribution với thuật toán phù hợp. Hỗ trợ M2 khi integration thật tồn tại; không hỗ trợ công thức ratio bỏ draft/verification overhead hoặc equality từng chuỗi.

E0-Q, ngân sách MPS, đếm local gate và các ablation ở trên là đề xuất/suy luận thiết kế của lượt review, không phải kết quả đã đo của các bài báo.

## 8. Thứ tự công việc đề xuất

1. Sửa input boundary, empty-mask/fallback và ownership/concurrency trước integration. Rebuild binary và khóa artifact provenance riêng.
2. Khóa E0-Q, codec, oracle độc lập, split theo cảnh, baseline exact/structured và metric trước training.
3. Học đầu nhỏ A/B; chạy test đóng băng một lần sau tuning. Thêm C nếu cấu trúc dữ liệu và ngân sách cần.
4. Đo kernel/Core, verifier và toàn luồng ở cùng quality. Đưa proposal đã kiểm chứng vào NPS lifecycle; chỉ Cầu Treo thực thi sau gate phù hợp.
5. Mở một nhánh ảnh/spatial thật sau synthetic controlled test; LLM acceleration là chương trình riêng với model thật và quality parity.

## Lịch sử thay đổi

- 2026-09-28 — Vy / `critique_research`: tạo memo DRAFT mới theo ủy quyền hoàn thiện tài liệu; giữ nguyên file hiện hữu để tránh đụng chỉnh sửa Antigravity. Phân xử phản biện, đề xuất E0-Q và ghi rõ giới hạn bằng chứng/source snapshot. Không tuyên bố chạy thực nghiệm VivyQu.
