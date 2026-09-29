# DRAFT — KIỂM TOÁN NĂNG LỰC PHỤ TRỢ CAUTREO VÀ TIỀM NĂNG MỤC TIÊU TỔNG HỢP

**Ngày:** 2026-09-29  
**Phạm vi:** đối chiếu tài liệu, mã nguồn và harness hiện có trong `D:\Vivyqu`; nghiên cứu ngoài chỉ dùng để kiểm tra tính khả thi của các giả thuyết kỹ thuật.  
**Chế độ:** kiểm toán chỉ đọc. Không sửa mã nguồn/tài liệu hiện hữu; không chạy test, DLL, benchmark hay nghiệm thu sản phẩm trong lượt này.  
**Quy ước bằng chứng:** `Thiết kế` ≠ `Mã tồn tại` ≠ `Harness tồn tại` ≠ `Native đã chạy` ≠ `Sản phẩm đã được nghiệm thu`.

## 1. Kết luận điều hành

Cautreo có tiềm năng rõ ràng khi được giữ đúng vai trò **thân thể và tầng phụ trợ có biên giới** của Vivy: thu nhận tín hiệu qua Mắt/Tai, cung cấp công cụ và thư viện, thực thi qua Tay, ghi biên lai, chạy verifier, quản lý tài nguyên và vận chuyển dữ liệu. Vivy/VivyQu vẫn là nơi duy nhất hình thành giả thuyết, đánh giá ý nghĩa, lựa chọn mục tiêu và ra quyết định nhận thức.

Kho hiện tại đã có nhiều mảnh ghép hữu ích: codec 4×1024D, Eyes/Ears/Hands, bridge ctypes, watchdog, episodic buffer, weight-map, host/plugin và các harness mô phỏng. Tuy nhiên, tài liệu đang vượt xa bằng chứng ở bốn điểm: tuyên bố hoàn thiện hoặc “100%” khi mới có code/harness; chuyển Cautreo từ thân thể sang đồng sở hữu nhận thức; coi hidden-state hook, early exit và activation steering là đã tích hợp native; coi verifier, sparse weight paging và tự học torque là vòng lặp đã được chứng minh.

Đánh giá mục tiêu tổng hợp:

- **Khả thi gần hạn:** Cautreo làm I/O, tool bus, capability registry, executor, receipt/verifier adapter, resource telemetry và durable journal.
- **Có cơ sở nghiên cứu nhưng cần thực nghiệm:** early exit có classifier được huấn luyện và calibrate; activation steering có vector mục tiêu đã học; recurrent context compression có đánh giá chất lượng; selective execution có cơ chế abstain/fallback.
- **Đang suy đoán:** lấy hidden state tùy ý từ llama.cpp production mà không sửa backend; giảm cố định 50% layer chỉ từ bốn “phân cực”; nén context/KV tùy ý vào 4096 số mà giữ nguyên chất lượng; “7.000 verifier” tự động tương thích; stream 10% weight của model dense rồi vẫn cho kết quả tương đương; suy tăng tốc LLM từ latency Core riêng.

Mức sẵn sàng tổng thể hiện tại là **prototype kiến trúc có thành phần thật, chưa có chuỗi bằng chứng native→product**. Mục tiêu đáng theo đuổi, nhưng phải tách ba ngân sách: latency Core, latency phụ trợ Cautreo, và latency/chất lượng toàn tác vụ.

## 2. Vai trò chuẩn cần khóa

| Vùng | Năng lực hợp lệ của Cautreo | Ranh giới không được vượt |
|---|---|---|
| **Mắt** | Đọc workspace, cảm biến, ảnh, trạng thái hệ thống; chuẩn hóa kiểu/dimension; gắn timestamp, provenance và quality flags | Không tự diễn giải ý nghĩa, xóa tín hiệu “không thuận”, chọn giả thuyết hoặc sửa quyết định |
| **Tai** | Thu nhận âm thanh, text/context và metadata; encode theo hợp đồng đã phiên bản hóa | Không tự kết luận ý định hay tạo quyết định nhận thức cuối cùng |
| **Tay** | Kiểm tra schema/capability, thực thi action envelope, idempotency, timeout; trả receipt nguyên trạng | Không tự thay mục tiêu hoặc tối ưu semantic policy; các giới hạn quyền/hệ thống là trust boundary, không phải nhận thức thay Vivy |
| **Thư viện** | Registry công cụ, model/artifact catalog, journal, evidence store, weight index/pager, verifier adapters | Không biến heuristic score, retrieval rank hoặc verifier thành “não thứ hai” |
| **Vivy/VivyQu** | Hình thành giả thuyết, chấm semantic utility/risk, chọn hành động, quyết định học từ evidence | Không giao quyền nhận thức cho host/plugin/verifier |

Quy tắc “không có filter cứng” cần được diễn giải hẹp: Cautreo không được bí mật thay chính sách nhận thức. Nó vẫn phải kiểm tra quyền, kích thước buffer, kiểu dữ liệu, schema, timeout, idempotency và giới hạn tài nguyên. Đây là điều kiện thực thi an toàn và bằng chứng, không phải một bộ não cạnh tranh.

## 3. Ma trận chưa đồng bộ và xung đột

| Mức | Nguồn | Mệnh đề/hiện trạng | Xung đột hoặc thiếu bằng chứng | Cách đồng bộ tối thiểu |
|---|---|---|---|---|
| P0 | `docs/VIVY_CAUTREO_INHERITANCE_SPEC.md:102-107` | Vivy là trung tâm nhận thức duy nhất; Python chỉ là Mắt/Tay; cấm gác cổng cứng | Câu chữ phủ định cả kiểm tra trust-boundary, trong khi buffer, permission và all-masked action bắt buộc phải fail closed | Tách “semantic policy” khỏi “execution safety”; Cautreo không quyết định ý nghĩa nhưng phải xác thực hợp đồng thực thi |
| P0 | `docs/VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md:8,97` | “Hệ sinh thái nhận thức kép” Gemma+MiMo | Mâu thuẫn trực tiếp với vai trò một trung tâm nhận thức; chưa có ownership contract xác định ai được update policy/memory | Đổi khái niệm thành **một cognition core + model services phụ trợ**; mọi đề xuất model phải qua Vivy decision contract |
| P0 | `docs/MIMO_RLVR_VIVYQU_STRATEGIC_REVIEW.md:57-72,97-104` | Cautreo tích hợp verifier, reward, pruning và torque descent trong vòng tự hoàn thiện | Verifier có thể xác nhận điều kiện cụ thể nhưng không tự sở hữu reward semantics; chưa có chống reward hacking, replay provenance, holdout hoặc rollback | Verifier chỉ phát `EvidenceReceipt`; Vivy mới chuyển evidence thành update sau gate/calibration/rollback |
| P0 | `python/vivyqu/cautreo_harmonizer.py:264-269` | Hot path được mô tả zero-copy | `ctypes.memmove` là copy; hơn nữa copy `CL12_DIMENSION*8` từ input không có contract dtype/size rõ ràng, đã được audit trước nhận diện nguy cơ đọc vượt buffer với `float32` | Chuẩn hóa một dtype ABI, kiểm tra nbytes/contiguous/alignment trước boundary; gọi đúng là preallocated-copy cho đến khi có shared buffer thật |
| P0 | `python/vivyqu/cautreo_harmonizer.py:280-298` | Watchdog fallback tạo quyết định hợp lệ | `is_valid` khi decode vẫn đọc `_out_frame.error_code`, có thể là trạng thái cũ thay vì kết quả watchdog | Kết quả fallback phải mang validity riêng và fail closed khi mask rỗng/lỗi transport |
| P1 | `docs/VIVY_CAUTREO_INHERITANCE_SPEC.md:36-40` | Eyes/Hands/codec được ghi “cần module/chưa đóng gói” | Code tương ứng đã có ở `python/vivyqu/eyes.py`, `ears.py`, `hands.py`, `codec.py` | Cập nhật trạng thái thành “code hiện diện, runtime/product chưa được chứng minh”, kèm commit/hash và gate |
| P1 | `docs/VIVY_CAUTREO_INHERITANCE_SPEC.md:35,92-95` | Memory tầng 1/2 “100%”; tầng 3 thiếu | `memory.py` đã có episodic buffer/replay/export, nên bảng vừa cũ vừa dùng “100%” không có native/product evidence | Tách design/code/harness/runtime; xác định durable schema, atomic write, provenance, retention, replay isolation |
| P1 | `docs/VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md:24,307-309` | Kế thừa Cautreo 100%, liên thông hoàn hảo, sync 2Brain 100% | Không có manifest đối chiếu plugin/API, receipt E2E, hay snapshot/hash của 2Brain làm bằng chứng tại tài liệu | Hạ xuống “claimed”; yêu cầu manifest, trace E2E và snapshot độc lập |
| P1 | `docs/VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md:98,106,291` | C11↔C++↔Python zero-copy | Python bridge đang `memmove`; đường shared memory/pinned pointer mới là thiết kế | Báo riêng copy count/bytes và transport; chỉ gọi zero-copy khi cùng allocation được consumer đọc trực tiếp |
| P1 | `docs/VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md:107,131-133` | Early exit cắt 50% layer ở confidence 0.85 | Harness `tests/test_cautreo_native_invasion.py:33-89` dùng transformer giả và hook cố định layer 16; nó chứng minh phép tính “16/32=50%”, chưa chứng minh accuracy/calibration/native model | Huấn luyện exit head theo layer, calibrate theo task, đo quality-cost curve và luôn có fallback full inference |
| P1 | `tests/test_cautreo_native_invasion.py:92-119` | Activation steering “không làm vỡ norm” | Chỉ kiểm finite/NaN; không assert norm bound, mục tiêu semantic, causal effect hoặc regression quality | Kiểm tra norm, cosine/dose response, target success, off-target harm và canary rollback trên model thật |
| P1 | `docs/VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md:18,63,142` | “7.000 MiMo verifiers” trả reward ±1 | Chưa có inventory, license, adapter contract, task coverage, false-positive/negative hoặc isolation proof | Bắt đầu 3-5 verifier nội bộ có oracle rõ; mỗi verifier có version/hash/input/output/confidence |
| P1 | `docs/VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md:103,113` | Weight pager stream sparse 10% cross-model | Weight-map/index không chứng minh model dense có thể bỏ 90% weights; loading ít byte không đồng nghĩa compute/chất lượng tương đương | Giới hạn claim thành catalog/paging; sparse execution chỉ mở sau model-specific mask + quality/latency/RSS benchmark |
| P1 | `docs/VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md:227-279` | LLM vừa là “quản thư ngữ cảnh”, vừa tự phản hồi fast path bỏ Core, vừa là phụ tá | Fast path có thể tự tạo output mang ý nghĩa mà không qua Vivy, làm mờ chủ quyền nhận thức và audit trail | Fast path chỉ áp dụng response class đã whitelist và có provenance; tác vụ có quyết định/rủi ro phải quay về Vivy |
| P2 | `python/vivyqu/cautreo_harmonizer.py:39-48` | Action→organ là bảng tĩnh 8 loại | Các action như `PIVOT_STATE`, `RECALIBRATE`, `FULL_RESET` được dispatch “both” dù mang nghĩa nhận thức/hệ thống | Tách cognitive command khỏi physical/tool action; chỉ action envelope đã resolve mới đi tới Bodymap |
| P2 | `docs/VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md:162-189` | Cognitive graph được map thành bitmask và HALTED_SAFE | Bitmask chỉ giữ allow/deny, làm mất evidence, uncertainty và reason; chưa có round-trip proof | Bitmask là cache thực thi; graph/provenance vẫn ở evidence store, output phải trả reason/version của mask |
| P2 | `python/vivyqu/hands.py:9-10,46-53` | Tay chuyển tiếp nguyên vẹn, không gác cổng | Thực thi tool/file/command mà không capability/schema/idempotency là không đủ an toàn và khó kiểm chứng | Thêm execution contract, không thêm semantic policy |

## 4. Sổ cái bằng chứng

| Năng lực | Thiết kế | Mã | Harness | Native/runtime trong lượt này | Bằng chứng sản phẩm | Phán quyết |
|---|:---:|:---:|:---:|:---:|:---:|---|
| Eyes/Ears encode 4×1024D | Có | Có | Có (`test_vivy_four_organs.py`) | Không chạy | Chưa có | Code-level only |
| Hands dispatch + receipt | Có | Có | Có | Không chạy | Chưa có actuator thật/receipt corpus | Code-level only |
| Codec 4096D↔12-bit action | Có | Có | Có | Không chạy | Chưa có semantic acceptance | Structural only |
| ctypes bridge C++ Core | Có | Có | Có | Không chạy | Chưa có trace hiện tại | Unverified runtime |
| Cautreo C11 DLL integration | Có | Nạp tùy tồn tại | Có harness | Không chạy | Chưa có | Conditional path |
| Shared-memory zero-copy | Có | Có thành phần SHM; Python hot path vẫn copy | Có | Không chạy | Chưa có | Claim chưa đạt |
| Watchdog/fallback | Có | Có | Có | Không chạy | Chưa có fail-closed acceptance | Blocked by validity issues |
| Episodic memory/replay | Có | Có | Có một số test | Không chạy | Chưa có durable recovery/rollback | Prototype |
| WeightMap/WeightPager | Có | Index có; execution sparse cần phân biệt | Có test index | Không chạy | Chưa có model quality proof | Catalog useful; sparse inference unproven |
| Early exit | Có | Flag/hook path có | Mock 32-layer | Không có native model | Chưa có accuracy-cost curve | Research |
| Activation steering | Có | Delta API có | Synthetic finite check | Không có native model | Chưa có causal/quality proof | Research |
| Automated verifiers/RLVR | Có | Một số verifier/test rời rạc | Chưa có inventory chuẩn | Không chạy | Chưa có reward safety | Design |
| “LLM acceleration” tổng hợp | Có | PoC paths | Synthetic microbench | Không chạy | Chưa có task-matched baseline | Chưa chứng minh |

## 5. Bằng chứng còn thiếu

1. **Hợp đồng chủ quyền:** một tài liệu ngắn xác định Vivy sở hữu cognition/policy/memory promotion; Cautreo sở hữu transport, resources, execution và evidence capture.
2. **ABI thật:** dtype, shape, stride, ownership, lifetime, alignment, version, error semantics; test negative cho short buffer, non-contiguous, wrong dtype, mask rỗng và multi-instance.
3. **Trace E2E:** observation provenance → Vivy decision → signed/versioned action envelope → Cautreo receipt → verifier evidence → memory proposal → promotion/rollback.
4. **Native model hook:** bằng chứng backend cụ thể xuất hidden state ở layer cụ thể, chấp nhận injection và tiếp tục decode đúng; không thể suy từ NumPy mock.
5. **Early-exit quality:** classifier được học, calibration set tách biệt, risk-coverage, exact task accuracy, latency/RSS tổng và fallback rate.
6. **Steering quality:** vector nguồn, layer, dose, causal target, off-target degradation, stability nhiều prompt/model/seed và rollback.
7. **Verifier governance:** oracle, phạm vi, version/hash, false pass/fail, sandbox, timeout, nondeterminism, reward aggregation và chống reward hacking.
8. **Memory promotion:** immutable raw receipt, dedupe, privacy, schema migration, replay isolation, human override và rollback.
9. **Paging/sparsity:** bytes read, peak RSS, major faults, tokens/s, correctness và fallback trên cùng model/config.
10. **Product acceptance:** tác vụ thật cho hình ảnh/sắp xếp/mô phỏng vật lý-hóa học, so với baseline cùng model/tài nguyên, đo success/regret/latency chứ không chỉ Core µs.

## 6. Kiểm tra nghiên cứu ngoài

Việc tra cứu theo skill `agent-reach` đã được yêu cầu. Trong môi trường kiểm toán này, CLI `agent-reach` và `mcporter` không khả dụng; do đó đã dùng web fallback và chỉ dựa vào nguồn sơ cấp dưới đây. Các nguồn hỗ trợ hướng nghiên cứu, không xác nhận implementation VivyQu/Cautreo.

| Chủ đề | Nguồn sơ cấp | Điều nguồn hỗ trợ | Điều nguồn không chứng minh cho dự án |
|---|---|---|---|
| Early exit | [Accelerating Large Language Model Inference with Self-Supervised Early Exits — arXiv:2407.21082](https://arxiv.org/abs/2407.21082) | Có thể học chính sách bỏ qua compute/layer theo tín hiệu và đánh đổi quality-cost | Không chứng minh rule bốn phân cực, threshold 0.85 hay tiết kiệm cố định 50% của Cautreo |
| Activation steering | [Steering Language Models With Activation Engineering — arXiv:2308.10248](https://arxiv.org/abs/2308.10248) | Hướng điều khiển activation/representation là một hướng thực nghiệm có thật | Không chứng minh delta Clifford hiện tại có semantic direction đúng hoặc an toàn trên Gemma/MiMo |
| llama.cpp server state | [llama.cpp server README-dev](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README-dev.md) | API server có giới hạn và giao diện nội bộ cụ thể; integration phải bám backend thực | Không bảo đảm API ổn định để đọc/ghi hidden state tại layer tùy ý |
| Hidden-state API | [llama.cpp issue #27112](https://github.com/ggml-org/llama.cpp/issues/27112) | Nhu cầu/giới hạn hidden-state access vẫn là vấn đề API cần xác minh theo phiên bản | Một issue không phải API contract hoặc bằng chứng production-ready |
| Context compression | [Recurrent Context Compression — arXiv:2406.06110](https://arxiv.org/abs/2406.06110) | Recurrent learned compression có thể nghiên cứu khi kiến trúc và training phù hợp | Không chứng minh arbitrary KV/context nén lossless vào D=4096, O(1), hoặc dùng trực tiếp với model hiện tại |
| Selective prediction | [SelectiveNet — PMLR v97, Geifman & El-Yaniv 2019](https://proceedings.mlr.press/v97/geifman19a.html) | Hệ thống có thể học coverage và abstain để kiểm soát risk | Không biến confidence thô của Core thành xác suất đúng; vẫn cần calibration và fallback |

## 7. Phân loại tiềm năng mục tiêu tổng hợp

### 7.1. Gần hạn — đáng triển khai sau khi qua boundary gates

- Cautreo capability registry và tool bus có schema/version rõ.
- Mắt/Tai tạo observation frame có provenance, quality flags và timestamp.
- Tay thực thi action envelope có capability check, idempotency và receipt.
- Thư viện lưu manifest model/tool/verifier và immutable evidence journal.
- Verifier adapter cho test deterministic có oracle rõ; Vivy quyết định promotion.
- Telemetry riêng cho Core, transport, model, verifier và full task.

### 7.2. Nghiên cứu — chỉ mở bằng thí nghiệm có control

- Learned early-exit head với calibration và abstention.
- Learned activation steering ở layer/backend được hỗ trợ.
- Recurrent lossy context summary đo quality/latency/memory.
- Selective/sparse compute khi model có cấu trúc hỗ trợ, cùng exact dense fallback.
- Weight-map dùng để chọn artifact/capability; chỉ nâng thành weight slicing khi có bằng chứng model-specific.

### 7.3. Suy đoán — chưa đưa vào roadmap cam kết

- Cautreo như engine nhận thức thứ hai hoặc “nhận thức kép”.
- Hidden-state zero-copy/injection phổ quát giữa mọi model/backend.
- 50% layer saving cố định mà không giảm chất lượng.
- 7.000 verifier plug-and-play và reward nhị phân đủ để tự cải thiện.
- Nén toàn bộ KV/context vào 4096 state với fidelity đầy đủ.
- Tăng tốc xN toàn LLM từ Core latency microsecond hoặc PoC macro-action synthetic.

## 8. Kiến trúc mục tiêu tối thiểu

```text
Mắt/Tai/Thư viện
  -> ObservationFrame{payload_ref, schema, provenance, quality, time}
  -> Vivy/VivyQu cognition (chủ sở hữu duy nhất của hypothesis/policy/decision)
  -> ActionEnvelope{intent, candidate_id, capability, constraints, evidence_ref}
  -> Cautreo executor (schema + permission + resource + idempotency)
  -> ExecutionReceipt{result, errors, timing, artifact hashes}
  -> VerifierEvidence{oracle, version, measurements, uncertainty}
  -> Vivy memory proposal -> calibration/promotion gate -> durable lesson
```

Chỉ cần bảy kiểu dữ liệu/versioned envelopes trên; chưa cần một orchestration framework mới. Bitmask 512 byte là cache cho Core, không phải nguồn sự thật semantic. WeightMap là catalog/index trước khi là sparse inference engine. Cautreo giữ plugin, resource, transport và receipts; không giữ policy nhận thức.

## 9. Cổng nghiệm thu G0–G7

| Gate | Điều kiện PASS tối thiểu | Bằng chứng phải lưu |
|---|---|---|
| **G0 — Ownership** | Một cognition owner; bảng quyền Cautreo/Vivy không mâu thuẫn | Spec version + reviewer sign-off |
| **G1 — Contract** | Observation/Action/Receipt/Evidence schemas và ABI dtype-size-lifetime được khóa | Schema, header, negative contract tests |
| **G2 — Boundary safety** | Wrong dtype/short/non-contiguous buffer, all-masked, timeout, stale output đều fail closed | Raw test output + binary/source hashes |
| **G3 — Auxiliary E2E** | Một tác vụ thật đi Mắt/Tai→Vivy→Tay→receipt, có provenance round-trip | Trace ID, timestamps, artifacts, replay |
| **G4 — Verifier** | Ít nhất ba verifier có oracle/coverage/error rates; reward không tự promotion | Inventory + held-out confusion/error report |
| **G5 — Native intervention** | Backend model thật cung cấp layer state; exit/steering có control, calibration, fallback | Build/version, raw runs, quality-cost curves |
| **G6 — Performance** | Báo Core/transport/model/verifier/full-task riêng; cold/warm, RSS/page faults, p50/p95/p99 | Raw samples, environment manifest, command lines |
| **G7 — Product** | Task suite hình ảnh/sắp xếp/mô phỏng có baseline cùng tài nguyên; cải thiện lặp lại và không vượt risk budget | Blind/held-out results, failure corpus, rollback proof |

Không được dùng PASS ở gate thấp để suy ra gate cao. Harness synthetic chỉ có thể hỗ trợ G1/G2; không nghiệm thu G5–G7.

## 10. Việc tiếp theo theo ưu tiên

1. **P0 — Khóa quyền sở hữu:** thay “nhận thức kép” bằng một cognition owner và các model services phụ trợ; định nghĩa semantic policy so với execution safety.
2. **P0 — Sửa boundary trước thực nghiệm:** dtype/nbytes/contiguous, fallback validity, all-masked, rotor plane bounds và multi-instance ownership; sau đó mới chạy native.
3. **P0 — Dựng một trace E2E nhỏ:** `fs-read → Vivy decision → fs-write vào sandbox → receipt → deterministic verifier`; không cần 7.000 verifier.
4. **P1 — Lập evidence manifest:** mỗi claim có source hash, binary hash, command, raw output, environment và gate mà nó thực sự chứng minh.
5. **P1 — Chọn một backend model duy nhất:** xác minh API hidden state/steering/exit theo đúng phiên bản; nếu backend không hỗ trợ, dừng nhánh “native invasion” thay vì mô phỏng như production.
6. **P1 — Thí nghiệm early exit tối thiểu:** full inference baseline, exit head, calibration split, held-out/OOD, risk-coverage và latency toàn tác vụ.
7. **P1 — Thí nghiệm steering tối thiểu:** no-steer, random direction, learned direction, nhiều dose; đo target gain và off-target harm.
8. **P2 — Giữ WeightMap ở vai trò catalog:** chỉ triển khai sparse weight compute khi benchmark model-specific cho thấy quality và wall-clock gain.
9. **P2 — Sau G0–G6 mới đánh giá xN:** tốc độ tổng hợp phải bao gồm encoder/model/Cautreo/verifier/output, cùng success/regret của tác vụ.

## 11. Phán quyết cuối

Cautreo là phần có giá trị cao của VivyQu nếu được phát triển như **nền tảng phụ trợ có kiểm chứng**: cơ quan cảm giác, cơ quan chấp hành, thư viện công cụ, resource manager và evidence recorder. Việc mở rộng nó thành “nhận thức kép”, reward owner hoặc policy engine làm mất đường biên kiến trúc, khiến các test harness dễ bị diễn giải thành năng lực sản phẩm.

Mục tiêu tổng hợp vẫn đáng theo đuổi theo chuỗi: **đúng hợp đồng → an toàn boundary → trace thật → verifier đáng tin → can thiệp model native → hiệu năng toàn luồng → nghiệm thu sản phẩm**. Hiện trạng đủ để bắt đầu G0–G3; chưa đủ để tuyên bố hidden-state native, early-exit 50%, activation steering có ích, sparse 10% tương đương, RLVR tự cải thiện hay tăng tốc LLM xN.
