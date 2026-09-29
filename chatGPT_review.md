**VIVYQU**

**TECHNICAL REVIEW & VERIFICATION AUDIT**

Architecture • Benchmark • Grand Prix E9 • C++ Core • IPC • Watchdog

| **Dự án**         | **VivyQu / Vivy Qudit Engine**                                                         |
|-------------------|----------------------------------------------------------------------------------------|
| **Loại tài liệu** | Independent technical review based on supplied project artifacts                       |
| **Ngày review**   | 27/09/2026                                                                             |
| **Phạm vi**       | Tài liệu kiến trúc + Sprint reports/specs + E9 source + collapse.cpp/.o + JSON results |
| **Trạng thái**    | Audit report — không thay thế nghiệm thu độc lập bằng raw benchmark artefacts          |

**Kết luận cấp cao**

> VivyQu có implementation thực và một số lựa chọn kiến trúc tốt, đặc biệt ở Core/Body separation, IPC/FFI và fault-tolerance. Tuy nhiên, Grand Prix E9 hiện chưa chứng minh được cùng lúc ba claim “Clifford zero-regret + 2.50 µs + 32 KiB working set” vì decision function trong E9, benchmark latency và C++ collapse path chưa đồng nhất.

# 1. Executive Summary

| **Trạng thái**               | **Kết luận**                                                                                                                                                     |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Mạnh                         | Kiến trúc Soul–Body tách Core thuần tính toán khỏi Cầu Treo I/O/dispatcher; IPC/FFI và watchdog có cấu trúc thực dụng.                                           |
| Đã có implementation         | Nguồn C++ và object file cho thấy collapse path đã được compile; các lỗi Windows/ctypes/bit-order trong Sprint 3 mang dấu hiệu của quá trình chạy hệ thống thật. |
| E9 có dữ liệu thật           | Script E9 và JSON xác nhận 1.500 mẫu test, Branch A và C đạt mean regret gần 0, Branch B khoảng 2.8846%.                                                         |
| Chưa được chứng minh         | Con số C++ Core 2.50 µs trong E9 được hard-code vào output, không được đo bởi test_grand_prix_e9.py.                                                             |
| Mâu thuẫn cốt lõi            | Branch C E9 dùng rotor + W_c + candidate_codebook + topology_cost, trong khi collapse.cpp chỉ argmax(state²) trên mask; hai decision function không tương đương. |
| Footprint bị đánh đồng       | 32 KiB chỉ là state 4096×float64; implementation E9 còn dùng W_c và candidate_codebook cỡ MiB.                                                                   |
| Benchmark cần tái nghiệm thu | E9 nên được chạy lại bằng đúng C++ binary/DLL thực thi decision function cuối cùng, đo p50/p95/p99 trực tiếp, verify checksum và thống nhất bit order.           |

**Đánh giá cập nhật:** Dự án nên được xem là “implementation real, benchmark promising, nhưng E9 cần tái nghiệm thu”. Không có phát hiện nào buộc phải loại bỏ kiến trúc VivyQu; vấn đề chính nằm ở evidence governance, benchmark methodology và sự không đồng nhất giữa algorithm được benchmark với C++ Core được tuyên bố.

# 2. Phạm vi và phương pháp review

Review này dựa hoàn toàn trên các artefact do dự án cung cấp. Không tự bổ sung benchmark hoặc kết quả thực nghiệm ngoài hồ sơ. Các nhận định được chia theo bốn mức chứng cứ: Supported, Partially Supported, Not Verified, Contradicted.

| **Mức**             | **Ý nghĩa**                                                          | **Cách sử dụng**                                                                    |
|---------------------|----------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| SUPPORTED           | Có code/output hoặc tài liệu nhất quán trực tiếp hỗ trợ.             | Có thể dùng như fact nội bộ, nhưng vẫn cần tái lập độc lập nếu phát hành công khai. |
| PARTIALLY SUPPORTED | Một phần claim có bằng chứng nhưng wording/metrics vượt quá dữ liệu. | Cần thu hẹp claim hoặc bổ sung artefact.                                            |
| NOT VERIFIED        | Tài liệu có tuyên bố nhưng artefact hiện có không đo/không xác nhận. | Không dùng như claim nghiệm thu.                                                    |
| CONTRADICTED        | Source/spec/report mô tả các giá trị hoặc algorithm không đồng nhất. | Phải sửa trước khi khóa release.                                                    |

# 3. Nền tảng kiến trúc: điểm mạnh và giới hạn

## 3.1. Soul–Body Decoupling

Kiến trúc phân tách VivyQu Core (tính toán thuần, không I/O) khỏi Cầu Treo (ingestion, I/O, dispatch, safety) là một lựa chọn đúng hướng. Nó cho phép benchmark Core độc lập, thay engine mà không phá runtime, và đặt safety/refusal ở biên hệ thống thay vì nhồi vào primitive toán học.

Điểm cần giữ nguyên trong mọi revision: Core không tự thực thi hành động; Cầu Treo có quyền từ chối output vi phạm contract/safety nhưng không được âm thầm rewrite semantic decision.

## 3.2. Clifford Cl(12) là một representation hợp lý, không tự động là cognitive advantage

Việc dùng 4096 hệ số thực tương ứng 2^12 basis blades tạo một representation gọn và thuận lợi cho SIMD. Tuy nhiên, 4096 hidden coordinates không tự động mang nghĩa 4096 hành động, và một phép quay trực giao nhanh không tự chứng minh cải thiện chất lượng quyết định.

Giá trị khoa học của VivyQu vì vậy phải được chứng minh qua task-held-out quality so với baseline cổ điển mạnh, không qua tên gọi quantum-inspired hoặc kích thước state.

# 4. Audit chuỗi Sprint 1 → 5

## 4.1. Sprint 1 — Math Core và microbenchmark

Sprint 1 spec đặt mục tiêu p99 \< 5.0 µs cho Core. Báo cáo tổng hợp sau đó ghi Sprint 1 p99 = 9.4 µs nhưng vẫn đánh dấu PASS. Về quản trị thực nghiệm, đây phải là Functional PASS / Performance Target Not Met, hoặc phải có decision record thay đổi tiêu chí nghiệm thu.

Điểm tích cực là cấu trúc source được đặc tả rõ: Cl12Multivector, Givens rotors, collapse, unit tests, microbench và cache-miss benchmark. Đây là nền tảng tốt để tái nghiệm thu bằng binary.

## 4.2. Sprint 3 — IPC / C-ABI

Sprint 3 cung cấp bằng chứng implementation đáng tin cậy hơn: shared-memory SPSC ring buffer, C-ABI DLL, Python ctypes, CPU pinning và các lỗi cụ thể khi chạy Windows. Các lỗi thread_local, AVX alignment, pointer truncation và bit-order mismatch là chi tiết có tính thực thi cao.

Report Sprint 3 ghi Core p50 2.50 µs, p95 3.20 µs, p99 3.30 µs; IPC p50 2.70 µs và E2E p99 9.40 µs. Do đó nếu tiếp tục dùng con số 2.50 µs, phải ghi rõ đây là p50 chứ không phải latency tổng quát hoặc p99.

## 4.3. Sprint 4 — Grand Prix E9

E9 là khu vực có nhiều claim quan trọng nhất và cũng là nơi phát hiện gap lớn nhất giữa report và code. JSON xác nhận A và C gần zero-regret trên 1.500 mẫu, nhưng cách diễn giải 'Clifford Core 32 KiB, 2.50 µs, zero-regret' chưa được code hiện tại chứng minh như một unitary claim.

## 4.4. Sprint 5 — Watchdog / fault tolerance

Watchdog có state machine CLOSED → OPEN → HALF_OPEN, fallback Baseline A2 và downgrade sang C-ABI DLL. Fault-injection report cho thấy test normal, timeout, recovery và daemon kill. Đây là bước tiến rõ ràng từ microbenchmark sang runtime resilience.

Tuy nhiên, spec đặt HALF_OPEN_PROBE_INTERVAL = 100 trong khi report mô tả 20 cycles; cần đồng bộ config và changelog. Ngoài ra thuật ngữ 'Zero Frame-Drop' nên được thu hẹp thành 'zero decision-drop trong fault-injection harness' cho đến khi đo tích hợp với application scheduler/actor/engine.

# 5. Audit trực tiếp Grand Prix E9

## 5.1. Branch B thực tế là FWHT + ridge, không phải full Hilbert phase/Born implementation

Comment trong training mô tả U1 phase → Hadamard → U2 phase → Born probability. Nhưng code thực tế tính FWHT(train_latents), sau đó học W_b bằng Ridge Regression để tái tạo target projection 64D, rồi dùng candidate_codebook để sinh score.

H_train = FWHT(h)  
W_b = Ridge(H_train -\> P h)  
score_B = candidate_codebook @ (W_b H(h)) - 0.3 \* topology_cost

Không thấy complex state, learned phase vectors, exp(iφ), exp(iθ) hoặc Born sampling trong path E9. Vì vậy Branch B nên được gọi đúng là 'FWHT spectral linear baseline/branch' nếu code không được thay đổi.

## 5.2. Branch C thực tế là Rotor + learned linear decoder + candidate codebook

Branch C áp dụng 8 rotor lên input, sau đó học W_c có shape 64×4096 để tái tạo cùng target projection P h mà oracle sử dụng. Score cuối còn nhân với candidate_codebook 4096×64 và trừ topology_cost.

h_rot = R h  
z = W_c h_rot  
score_C = candidate_codebook @ z - 0.3 \* topology_cost  
k\* = argmax(score_C under mask)

Đây là một algorithm hợp lệ, nhưng khác đáng kể với mô tả '32 KiB Clifford state + collapse'. Readout có đủ năng lực để học gần như inverse của phép quay trực giao, nên zero-regret trên task tuyến tính không tự chứng minh rotor tạo representation tốt hơn.

## 5.3. C++ collapse path không phải decision function của E9

collapse.cpp thực hiện masked argmax trên bình phương các hệ số state: k\* = argmax(state\[k\]^2). Không có W_c, candidate_codebook hay topology_cost trong function này.

C++: k\* = argmax\_{k in valid} state.blades\[k\]^2  
E9: k\* = argmax\_{k in valid} \[C · W_c · R(h) - 0.3 t\]\_k

Hai function này không tương đương. Vì vậy hiện chưa thể nối trực tiếp quality của E9 với latency của C++ collapse path.

## 5.4. Con số 2.50 µs trong E9 được hard-code

test_grand_prix_e9.py đo Python latency, nhưng các trường latency_core_cpp_us = 3.50 / 12.00 / 2.50 được ghi trực tiếp vào dictionary output. Không có call tới DLL/executable hoặc C++ benchmark trong script E9.

Kết luận: E9 có thể sử dụng latency C++ từ benchmark khác làm metadata, nhưng không được gọi đó là 'latency measured by E9'. Muốn khóa Gate G2 dựa trên latency, phải link tới raw benchmark artefact tương ứng với đúng binary/algorithm.

## 5.5. Footprint 32 KiB không phải working set của Branch C E9

State 4096×float64 = 32 KiB là đúng. Nhưng E9 Branch C còn dùng W_c và candidate_codebook. Với float32, mỗi matrix 64×4096 hoặc 4096×64 khoảng 1 MiB; hai matrix đã khoảng 2 MiB, chưa kể topology, input và scratch.

Do đó report phải tách State Size, Parameter Size, Hot Working Set và Process RSS. Không được dùng 32 KiB state để suy ra toàn algorithm 'L1 resident' hoặc 'zero cache miss'.

## 5.6. Checksum và bit-order

Script E9 import hashlib và in thông báo 'Loading & Verifying Held-Out Test Set' nhưng không thực hiện SHA-256 comparison. Checksum freeze vì vậy chưa được verify bởi test code hiện tại.

Ngoài ra E9 dùng np.unpackbits(mask_bytes) với default bit order, trong khi Sprint 3 đã khóa protocol C++/Python về little-endian để phù hợp \_tzcnt_u64. E9 cần dùng bitorder='little' và dataset generator phải cùng convention.

# 6. Kết quả JSON: điều gì được hỗ trợ thật

| **Branch**           | **Validity** | **Mean regret** | **p95 regret** | **Python latency**        |
|----------------------|--------------|-----------------|----------------|---------------------------|
| A — Baseline A2      | 100%         | 6.2314e-7%      | 0%             | 56.10 µs (per-sample p50) |
| B — FWHT/Ridge path  | 100%         | 2.88456%        | 11.29230%      | 1086.77 µs (batch avg)    |
| C — Rotor/Ridge path | 100%         | 6.2314e-7%      | 0%             | 392.12 µs (batch avg)     |

A và C có mean regret giống nhau đến toàn precision được ghi. Điều này cần kiểm tra prediction-by-prediction; rất có thể learned readout C đang tái tạo cùng linear projection mà A/oracle sử dụng.

Latency Python giữa A và B/C không cùng methodology: A đo từng sample trong loop; B/C đo whole batch rồi chia N. Vì vậy không dùng bảng Python latency này để xếp hạng real-time path.

# 7. Claim Verification Matrix

| **Claim**                                         | **Trạng thái**      | **Căn cứ**                                                                  | **Hành động**                                     |
|---------------------------------------------------|---------------------|-----------------------------------------------------------------------------|---------------------------------------------------|
| Có C++ Core thực                                  | SUPPORTED           | collapse.cpp + object file cho thấy binary x86-64 với masked scan/BMI path. | Giữ claim ở mức implementation tồn tại.           |
| E9 chạy 1.500 held-out samples                    | SUPPORTED           | test_grand_prix_e9.py + JSON.                                               | Giữ.                                              |
| A/C gần zero-regret trên E0 test                  | SUPPORTED           | JSON kết quả.                                                               | Giữ nhưng mô tả đúng benchmark E0.                |
| C++ Core 2.50 µs được đo trong E9                 | CONTRADICTED        | 2.50 được hard-code vào output.                                             | Đo trực tiếp binary trong E9-v2.                  |
| Branch C E9 có 32 KiB working set                 | CONTRADICTED        | Có W_c + candidate_codebook cỡ MiB.                                         | Đổi thành State Size 32 KiB; đo working set thật. |
| C++ collapse algorithm = E9 zero-regret algorithm | CONTRADICTED        | collapse dùng state² argmax; E9 dùng C·W_c·R(h)-cost.                       | Hợp nhất algorithm hoặc benchmark đúng path.      |
| Branch B là Hilbert phase/Born engine             | CONTRADICTED        | Code là FWHT + Ridge; không có phase/Born path.                             | Đổi tên branch hoặc hiện thực spec thật.          |
| E9 verify SHA-256                                 | NOT VERIFIED        | Không có hash compare trong script.                                         | Thêm verify trước load/benchmark.                 |
| Python/C++ mask protocol thống nhất               | NOT VERIFIED        | E9 dùng unpackbits default; Sprint 3 yêu cầu little.                        | Khóa bitorder='little'.                           |
| Zero Frame-Drop toàn sản phẩm                     | PARTIALLY SUPPORTED | Watchdog test chứng minh decision continuity trong harness.                 | Thu hẹp wording hoặc đo E2E application.          |
| Clifford có cognitive advantage                   | NOT VERIFIED        | E0 là target projection tuyến tính và decoder có thể undo rotor.            | Thiết kế OOD/nonlinear benchmarks.                |

# 8. Rủi ro kỹ thuật và mức ưu tiên

| **Priority** | **Risk**                            | **Mô tả**                                                            | **Tác động**                                          |
|--------------|-------------------------------------|----------------------------------------------------------------------|-------------------------------------------------------|
| P0           | Decision-function mismatch          | Quality và latency đang gắn cho hai algorithm khác nhau.             | Có thể làm vô hiệu Gate G2 nếu không tái nghiệm thu.  |
| P0           | Hard-coded latency in E9            | C++ latency không được test E9 đo.                                   | Không thể dùng E9 như bằng chứng latency.             |
| P1           | Working-set overclaim               | 32 KiB state bị gọi là total working set.                            | Sai định vị cache/footprint.                          |
| P1           | Benchmark too easy / linear teacher | Target trung gian P h là tuyến tính và được dùng trực tiếp để train. | Khó suy ra general cognitive advantage.               |
| P1           | Mask bit-order inconsistency        | Python E9 và C++ có thể chọn tập valid khác nhau.                    | Có thể gây silent correctness bug.                    |
| P2           | Checksum not enforced               | Frozen test set chỉ là convention, chưa được code verify.            | Giảm reproducibility/auditability.                    |
| P2           | Watchdog config drift               | HALF_OPEN interval 100 vs 20.                                        | Spec/binary lệch.                                     |
| P2           | Born path allocates                 | std::vector reserve trong sampled collapse.                          | Không phù hợp nếu claim zero-allocation cho mọi mode. |

# 9. Đề xuất E9-v2 — tái nghiệm thu chuẩn

Mục tiêu của E9-v2 là buộc quality, latency và memory metrics xuất phát từ cùng một implementation path và cùng binary.

1.  Khóa SHA-256 của dataset, weights và binary; test phải verify hash trước khi chạy.

2.  Thống nhất mask bit order little-endian ở generator, Python harness, C-ABI và C++.

3.  Định nghĩa một API duy nhất: input h\[4096\] + mask\[512\] → output k\*, score/status.

4.  Nếu production path có W_c/candidate_codebook/topology, đưa chúng vào C++ Core hoặc công khai rằng scorer nằm ngoài Core.

5.  Không hard-code latency. Harness phải gọi đúng DLL/exe cho từng sample và ghi raw nanoseconds/cycles.

6.  Warm-up riêng, sau đó đo ít nhất 50k–100k runs cho p50/p95/p99/max; giữ cả cold-cache test.

7.  Xuất prediction cho toàn 1.500 test samples; Python chỉ tính oracle/regret sau khi nhận k\* từ C++.

8.  Đo state bytes, parameter bytes, peak working set và RSS riêng; hardware counters nếu có.

9.  Chạy pure collapse(state²) như một ablation để biết riêng rotor+argmax đạt regret bao nhiêu.

10. Chạy no-rotor + same W_c readout để đo đóng góp thật của rotor.

11. Chạy random orthogonal transform + same readout để kiểm tra liệu lợi ích chỉ đến từ một transform khả nghịch bất kỳ.

12. Chạy OOD/nonlinear benchmark để tránh trường hợp Ridge tái tạo teacher linear projection gần hoàn hảo.

## 9.1. Acceptance criteria đề xuất

| **Trục**        | **PASS**                                                  | **Ghi chú**                                  |
|-----------------|-----------------------------------------------------------|----------------------------------------------|
| Correctness     | Validity 100%; prediction log complete; hash verified     | Không silent bit-order mismatch.             |
| Quality         | Regret đạt ngưỡng pre-registered trên held-out và OOD     | Không thay threshold sau khi xem test.       |
| Latency         | p99 đo từ exact production binary/API                     | Không dùng số hard-code hoặc benchmark khác. |
| Memory          | Công bố state/params/hot working set/RSS                  | Không gọi state size là working set.         |
| Reproducibility | commit SHA + compiler + flags + CPU + binary hash + seeds | Có thể chạy lại trên máy sạch.               |
| Ablation        | rotor vs no-rotor vs random orthogonal vs baseline        | Chứng minh phần nào tạo lợi ích.             |

# 10. Đánh giá cập nhật của dự án

| **Trục**                             | **Điểm** | **Nhận định**                                                               |
|--------------------------------------|----------|-----------------------------------------------------------------------------|
| Kiến trúc tổng thể                   | 8.5/10   | Tách Core/Body tốt; interface và resilience có tư duy hệ thống.             |
| Implementation credibility           | 8/10     | Có source/object/runtime artefacts cụ thể.                                  |
| IPC / FFI engineering                | 8.5/10   | Các lỗi/khắc phục có tính thực thi cao.                                     |
| Fault tolerance                      | 8/10     | Có circuit breaker/fallback/auto-recovery, cần wording chính xác hơn.       |
| Experimental design                  | 7/10     | Có held-out/baseline, nhưng E0 quá thuận lợi và E9 metrics không đồng nhất. |
| Mathematical / algorithm consistency | 6/10     | Spec B/C khác code; C++ collapse khác E9 decision function.                 |
| Benchmark evidence                   | 5.5/10   | Quality có output; latency C++ E9 chưa được đo trực tiếp.                   |
| Document consistency                 | 4/10     | Nhiều claim/spec/report drift và trạng thái PASS chưa nhất quán.            |
| Product-readiness evidence           | 5/10     | Prototype mạnh, nhưng chưa đủ để gọi production-verified theo chuẩn audit.  |

# 11. Kết luận cuối cùng

VivyQu không nên bị đánh giá như một ý tưởng thuần lý thuyết. Các artefact cho thấy có implementation C++ thực, một runtime IPC/FFI có chủ đích, và fault-tolerance được thiết kế tương đối nghiêm túc. Đây là nền tảng tốt.

Tuy nhiên, bằng chứng hiện tại chưa cho phép khóa kết luận rằng 'Clifford Core 32 KiB đạt zero-regret ở 2.50 µs'. Quality gần zero-regret được tạo bởi một path có learned linear decoder và codebook; C++ collapse được cung cấp lại là amplitude-squared argmax; 2.50 µs trong E9 là metadata hard-code. Vì vậy ba claim đang thuộc ba lớp thực thi khác nhau.

**Trạng thái khuyến nghị:** VivyQu = implementation real / research prototype mạnh / benchmark promising / cần E9-v2 trước khi gắn nhãn production-verified.

Nếu E9-v2 dùng đúng production binary, vẫn đạt quality tương đương A2, p99 microsecond-level và công bố footprint thật, đó sẽ là bước chuyển quan trọng từ một kiến trúc thú vị sang một low-latency decision engine có bằng chứng kỹ thuật đáng tin cậy.

# 12. Source Register

| **Artefact**                                     | **Vai trò trong audit**                                    |
|--------------------------------------------------|------------------------------------------------------------|
| ARCHITECTURE_SPEC(1).md                          | Contract architecture, Core boundary, performance caveats. |
| CAUTREO_CORE_INTERFACE_SPEC(1).md                | ABI/IPC, watchdog, fallback contract.                      |
| E0_BASELINE_AND_SPRINT_1_REPORT(1).md            | Sprint 1 reported microbenchmark.                          |
| EXP_MATRIX_AND_MULTI_BRANCH_SPEC(1).md           | Multi-branch experiment framing.                           |
| EXPERIMENT_E0_BENCHMARK_SPEC(1).md               | E0 dataset/oracle/baseline/acceptance.                     |
| MATH_SPEC_BLUEPRINT(1).md                        | Mathematical design and isolated assumptions.              |
| RESEARCH_AND_DEVELOPMENT_PLAN(1).md              | Evidence labels, E0–E5 matrix, working-set caveats.        |
| SOP_OPERATIONAL_RUNBOOK(1).md                    | Operations, telemetry and incident handling.               |
| SOUL_BODY_DECOUPLING(1).md                       | Core vs Cầu Treo separation.                               |
| VIVY_CAUTREO_INHERITANCE_SPEC(1).md              | Inheritance status and runtime gaps.                       |
| VIVY_FINAL_COMPARISON_AND_INHERITANCE_SPEC(1).md | Vivy/NPS comparison.                                       |
| VIVY_MASTER_BUILD_PLAN(1).md                     | 6-sprint roadmap.                                          |
| VIVY_NPS_INHERITANCE_AND_HYBRID_QUDIT(1).md      | NPS semantic layer vs numerical selector.                  |
| VIVYQU_DATA_FLOW_AND_CODEC_SPEC(1).md            | End-to-end dataflow and codec.                             |
| VIVYQU_V1_RELEASE_REPORT(1).md                   | Production/release claims.                                 |
| SPRINT_1_KICKOFF_SPEC(1).md                      | Sprint 1 target and C++ source blueprint.                  |
| SPRINT_3_IPC_AND_C_ABI_REPORT(1).md              | IPC/C-ABI results and implementation issues.               |
| SPRINT_4_GRAND_PRIX_E9_SPEC(1).md                | E9 branch definitions and gate criteria.                   |
| SPRINT_4_GRAND_PRIX_E9_REPORT(1).md              | E9 leaderboard and production decision.                    |
| SPRINT_5_WATCHDOG_INTEGRATION_SPEC(1).md         | Watchdog spec.                                             |
| SPRINT_5_WATCHDOG_INTEGRATION_REPORT(1).md       | Fault-injection report.                                    |
| train_branches_b_c.py                            | Actual Branch B/C training implementation.                 |
| test_grand_prix_e9.py                            | Actual E9 evaluation and JSON generation.                  |
| collapse.cpp                                     | Actual C++ hard-mask/Born collapse implementation.         |
| collapse.o                                       | Compiled object corresponding to collapse implementation.  |
| grand_prix_e9_results.json                       | Recorded E9 output metrics.                                |

# 13. Checklist phát hành lại tài liệu sau audit

- Đổi mọi 'working set 32 KiB' thành 'state size 32 KiB' nếu chưa có measurement working set.

- Đổi mọi 'E9 measured 2.50 µs' thành nguồn benchmark cụ thể hoặc loại bỏ.

- Ghi p50/p95/p99 đầy đủ cho Core thay vì dùng 2.50 µs chung chung.

- Đồng bộ Branch B naming với code thực hoặc hiện thực phase/Born đúng spec.

- Đồng bộ Branch C production decision function với E9 scorer.

- Sửa Sprint 1 status nếu target p99 \< 5 µs không đạt.

- Đưa config watchdog về single source of truth; resolve 20 vs 100 probe interval.

- Thu hẹp 'zero frame-drop' nếu chưa có app-level scheduler measurement.

- Thêm hash verification vào E9.

- Thêm bitorder='little' rõ ràng vào mọi mask pack/unpack.

- Tạo manifest: commit SHA, binary SHA, compiler, flags, CPU, seeds, dataset SHA.

- Chạy E9-v2 trước khi tái công bố 'Production Verified'.
