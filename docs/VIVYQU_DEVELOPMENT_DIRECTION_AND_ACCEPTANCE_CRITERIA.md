# VIVYQU — ĐỊNH HƯỚNG PHÁT TRIỂN VÀ TIÊU CHÍ NGHIỆM THU

**Status:** `CANONICAL DIRECTION v1.1`  
**Ngày:** 2026-09-29  
**Phạm vi:** định hướng bắt buộc cho agent thiết kế, lập trình, kiểm thử, benchmark và viết tài liệu VivyQu.  
**Giới hạn:** tài liệu này là hợp đồng phát triển; **không phải bằng chứng nghiệm thu sản phẩm**.

## 1. Mục tiêu sản phẩm gần nhất

Mục tiêu duy nhất của chu kỳ hiện tại là chứng minh một vertical slice E0-Q thật và có thể tái lập:

```text
Observation thật
  -> Vivy/VivyQu tạo và xếp hạng proposal
  -> verifier độc lập kiểm tra ràng buộc
  -> Cautreo thực thi trong sandbox
  -> receipt quan sát được
  -> evidence bất biến
  -> NPS quyết định promotion hoặc rollback
```

Không dùng “Vivy hoàn chỉnh” làm tiêu chí. Tiêu chí gần nhất là: **trên dữ liệu chưa thấy, VivyQu tạo một quyết định thật, quyết định đó được thực thi và kiểm chứng, đồng thời tốt hơn hoặc rẻ hơn một baseline trung thực trong cùng ngân sách**.

E0-Q phải có đúng sáu yếu tố bốn trạng thái, `a = (a0..a5)`, `ai ∈ {0,1,2,3}`, tạo `4^6 = 4096` candidate. ID phải cố định, đảo được và có phiên bản:

```text
k = sum(ai * 4^i), i=0..5
```

Sáu yếu tố phải mang nghĩa miền cụ thể, thí dụ `X, Y, Z, orientation, size, material`; mỗi mức có định nghĩa rõ. Bài toán phải có ràng buộc vật lý hoặc hình học, tương tác cặp và ít nhất một thành phần phi tuyến để tránh toy task tách biến hoàn toàn. Khi hàm năng lượng đã biết, exact scan đủ 4096 candidate là oracle bắt buộc.

## 2. Những việc đóng băng

Không triển khai mới, quảng bá hoặc dùng làm điều kiện hoàn thành cho đến khi gate tương ứng cho phép:

| Hướng | Trạng thái | Điều kiện mở lại |
|---|---|---|
| Nén KV/context bất kỳ vào 4096 state với `O(1)` | Đóng băng | G7 của E0-Q đạt; có protocol riêng về fidelity, task quality và memory |
| Sparse paging/model 72B | Đóng băng | G6 đạt; có model-specific sparsity, dense fallback và benchmark page fault/RSS/tokens-s |
| Early exit | Đóng băng | G4 đạt; có exit head học thật, calibration, risk-coverage và full-inference fallback |
| Activation steering | Đóng băng | G4 đạt; có vector/layer/dose xác định, causal test và off-target regression |
| “7.000 verifier” | Đóng băng | G4 đạt với 3–5 verifier có oracle, version, false-pass/false-fail và isolation |
| Tuyên bố tăng tốc LLM xN | Đóng băng | G6–G7 đạt trên model và tác vụ thật, gồm encoder, verifier, fallback và output |

Code cũ có thể được giữ để đối chiếu. Không mở rộng nó trong ba sprint A–C, trừ sửa lỗi làm ảnh hưởng trực tiếp đến vertical slice hoặc tính trung thực của bằng chứng.

## 3. Ma trận thẩm quyền

| Thành phần | Sở hữu | Được làm | Không được làm |
|---|---|---|---|
| **Vivy/VivyQu** | Nhận thức, hypothesis, semantic scoring, proposal, policy lựa chọn | Nhận observation; tạo/xếp hạng candidate; abstain; đề xuất học | Tự tuyên bố action đã thành công; sửa raw receipt |
| **Cautreo** | Mắt, Tai, Tay, Thư viện, transport, resource control, executor, evidence capture | Chuẩn hóa input; kiểm schema/quyền/tài nguyên; thực thi typed action; trả receipt | Tự đặt mục tiêu, tự chọn semantic policy, tự tạo reward/target, tự promotion memory |
| **Verifier** | Xác nhận một điều kiện đã khai báo | Đo oracle/ràng buộc; trả kết quả, confidence và provenance | Thay Vivy chọn mục tiêu; tự tổng hợp reward không có contract; tự sửa action |
| **NPS** | Vòng đời giả thuyết và evidence | Ghi nhận evidence; quyết định promotion/rejection/rollback theo rule đã khóa | Sửa raw evidence; biến harness PASS thành product acceptance |

Trust-boundary checks của Cautreo là bắt buộc. Kiểm dtype, shape, buffer, permission, timeout, idempotency và resource không phải quyền nhận thức.

## 4. Hợp đồng dữ liệu tối thiểu

Mọi envelope phải có `schema`, `schema_version`, `run_id`, `trace_id`, `created_at`, `producer`, `producer_version` và `payload_hash`. ID xuyên suốt phải bất biến trong một run.

### 4.1 ObservationEnvelope

```text
observation_id
domain
payload_ref | inline_payload
dtype, shape, units
source_id
captured_at
provenance[]
quality_flags[]
```

### 4.2 ProposalEnvelope

```text
proposal_id
observation_id
candidate_codec_version
candidate_id
rank
raw_score
score_semantics
constraints_version
model_or_weights_hash
abstained
reason_codes[]
```

`candidate_id` là ID cố định của hành động/cấu hình, không phải nhãn được học lại. Score hoặc amplitude có thể học; ý nghĩa giải mã ID không được trôi.

### 4.3 ActionEnvelope

```text
action_id
proposal_id
domain
action_schema_version
capability
parameters
constraints
permission_ref
idempotency_key
timeout_ms
verifier_plan_ref
```

### 4.4 ExecutionReceipt

```text
receipt_id
action_id
executor_id, executor_version
status: SUCCEEDED | FAILED | REJECTED | TIMEOUT | OFFLINE
started_at, finished_at
result_ref
error_code, error_detail
resource_usage
artifact_hashes[]
side_effects[]
```

Không có actuator hoặc executor thì phải trả `OFFLINE`; không được trả `SUCCEEDED`.

### 4.5 EvidenceEnvelope

```text
evidence_id
receipt_id
verifier_id, verifier_version
oracle_version
measurements
passed
confidence_semantics
failure_modes[]
raw_evidence_ref
raw_evidence_hash
```

Verifier không trả “đúng” chung chung. Nó phải nêu điều kiện đã kiểm, số đo, phiên bản và phạm vi kết luận.

## 5. Blocker phải sửa trước thực nghiệm mới

Không dùng kết quả training hoặc benchmark mới để quyết định kiến trúc cho đến khi các blocker liên quan đã có test tái hiện và test hồi quy:

1. Sửa dấu induced blade rotation hoặc đổi tên trung thực nếu phép biến đổi không phải Clifford rotor sandwich.
2. Sửa chain rule cho chuỗi nhiều rotor bằng intermediate states/adjoints; đối chiếu finite difference.
3. Khi hinge loss bằng 0, không cập nhật rotor.
4. Loại fallback trọng số ngẫu nhiên. Thiếu artifact hợp lệ phải trả `UNAVAILABLE/OFFLINE` và giữ fail-closed.
5. Mask rỗng, candidate ngoài mask, buffer sai dtype/shape/stride/nbytes và executor vắng mặt phải fail-closed.
6. Làm rõ ownership/lifetime/concurrency của native context; multi-instance không được reset/free trạng thái của nhau.
7. Benchmark không được có latency mặc định mang nhãn measured. Artifact cũ phải đánh dấu stale hoặc được thay bằng run mới có raw samples và binary hash.
8. Không dùng `success=True`, confidence giả hoặc receipt giả để đi qua gate.

Nguồn đối chiếu: [Review và hướng nghiên cứu 28/09](./REVIEW_AND_RESEARCH_DIRECTION_2026-09-28.md), [Audit Cautreo 29/09](./CAUTREO_AUXILIARY_CAPABILITY_AUDIT_2026-09-29.md), [Audit đồng bộ/xung đột 29/09](./REVIEW_SYNC_CONFLICT_AUDIT_2026-09-29.md).

## 6. Ma trận baseline

Mọi nhánh dùng cùng input, split, feature access, candidate mask, oracle access, tuning budget, parameter budget được công bố và hardware/runtime. Không cho VivyQu biết thông tin đáp án mà baseline không có.

| Nhánh | Vai trò | Bắt buộc | Điều kiện giữ |
|---|---|---:|---|
| Exact scan 4096 | Oracle/quality ceiling khi energy có thể tính; báo cost riêng | Có | Luôn giữ để tính regret/correctness; không phải product comparator bắt buộc phải thắng về quality |
| Linear hoặc low-rank scorer | Baseline sản phẩm tối thiểu | Có | Giữ nếu đạt quality với cost thấp nhất |
| Structured real transform | Kiểm lợi ích cấu trúc/butterfly | Có | Giữ nếu hơn linear về quality-memory-latency |
| Phase + mixing | Giả thuyết quantum-inspired chính | Có | Giữ nếu thắng structured real trong cùng ngân sách và ablation xác nhận phase đóng góp |
| MPS `χ=4/8` | Nhánh nén có điều kiện | Chưa | Chỉ mở nếu dữ liệu cho thấy cấu trúc rank thấp và A/B không đạt memory/quality |

Đối chứng bắt buộc gồm: no-transform; transform cố định đã gộp `W_eff = W_cR`; no-phase; no-mixing; no-rotor. Một diagonal phase cuối cùng không đổi Born probability nếu không có mixing sau phase, nên không được xem là cơ chế tạo lợi ích.

## 7. Protocol dữ liệu và đánh giá

1. Chia dữ liệu theo **scene/group**, không chia ngẫu nhiên từng record khiến near-duplicate rò sang tập khác.
2. `train` chỉ dùng học tham số.
3. `validation` dùng chọn kiến trúc/hyperparameter trong tuning budget đã khóa.
4. `calibration` riêng dùng fit confidence/threshold; không dùng để chọn weights.
5. `test` untouched chỉ mở một lần sau khi khóa cấu hình.
6. `OOD` gồm scene, coupling hoặc constraint chưa thấy; báo riêng, không trộn test IID.
7. Không train trên held-out/test. Mọi rerun sau khi nhìn test phải tạo protocol version mới và ghi rõ test đã mất tính untouched.
8. Seeds, preprocessing, dedupe, exclusions, failures và số mẫu thực tế phải nằm trong run artifact.

Metric tối thiểu:

- Feasible-action rate và constraint violation rate.
- Exact-match với oracle khi có, normalized regret và top-k regret.
- NLL/Brier, reliability và risk-coverage cho confidence đã định nghĩa.
- p50/p95/p99 latency của Core, Cautreo, verifier và end-to-end tách riêng.
- Peak RSS, weights resident, state bytes, workspace bytes, bytes copied/page faults nếu có.
- Failure/fallback/abstention rate.
- OOD degradation và verifier false-pass/false-fail.

### 7.1. Acceptance Threshold Freeze

Trước lần mở `test`, owner phải tạo và khóa một artifact `acceptance_thresholds.json` có hash, liên kết tới `protocol_ref`. Artifact tối thiểu phải chứa:

| Trường bắt buộc | Nội dung |
|---|---|
| `primary_metric` | Một metric quyết định chính và chiều tốt hơn |
| `product_comparator` | Baseline sản phẩm phải so; exact scan chỉ là oracle/ceiling |
| `non_inferiority_margin` hoặc `effect_margin` | Sai khác tối đa chấp nhận hoặc mức cải thiện tối thiểu |
| `sample_count`, `group_count` | Số mẫu và số scene/group tối thiểu cho test và OOD |
| `ci_method`, `ci_level`, `bootstrap_seed`, `bootstrap_replicates` | Phương pháp bất định được khóa trước khi xem test |
| `risk_budget` | Giới hạn violation, false-pass, failure, fallback và abstention |
| `latency_budget` | p50/p95/p99 Core và end-to-end, warm/cold nếu áp dụng |
| `memory_budget` | State, resident weights, workspace và peak RSS |
| `deadline` | Thời điểm freeze và hạn hoàn tất đánh giá |
| `protocol_ref` | ID/version/hash của protocol, dataset split và metric implementation |

Thiếu hoặc sửa artifact này sau khi xem test/OOD làm G5–G7 không được mở. Muốn thay đổi phải tạo protocol version mới, giải thích lý do và dùng test set mới chưa bị quan sát.

## 8. Gate G0–G7

Gate chỉ `PASS` khi có artifact chỉ định. `PARTIAL`, code tồn tại hoặc test xanh không được nâng thành PASS. Tác giả implementation hoặc run không được tự ký PASS. Technical reviewer độc lập ký G1–G6; user/product owner cùng independent reviewer ký G0 và G7. Mỗi chữ ký nằm trong decision record, gồm identity, thời điểm, gate, artifact hashes và phán quyết.

| Gate | Điều kiện PASS | Bằng chứng bắt buộc |
|---|---|---|
| **G0 — Authority** | Một cognition owner; Cautreo boundary và vocabulary nhất quán | Tài liệu canonical này; conflict scan không còn claim active trái thẩm quyền; decision record do user/product owner và independent reviewer ký |
| **G1 — Contract/ABI** | Năm envelope và native ABI version hóa, round-trip đúng | Schema; ABI manifest; positive + negative tests cho dtype/shape/stride/short buffer/version |
| **G2 — Fail-closed** | Blocker §5 được xử lý, không fake success/random fallback | Regression tests; sanitizer hoặc boundary harness phù hợp; raw failure receipts; source/binary hashes |
| **G3 — Vertical slice** | Domain/codec/energy/constraints đã freeze và hash trước khi mở gate; một trace thật observation→proposal→action→receipt chạy trong sandbox | Frozen domain bundle; raw trace; executor side effect quan sát được; replay/idempotency check; artifact hashes |
| **G4 — Verification** | Verifier độc lập; event semantics và confidence threshold được khóa/calibrate | Calibration split; event/threshold contract; verifier corpus và raw predictions; sample protocol; false-pass/false-fail; abstain/fallback evidence |
| **G5 — Learning** | Acceptance Threshold Freeze đã khóa; học trên train, chọn bằng val, calibrate riêng, test/OOD untouched | `acceptance_thresholds.json`; dataset manifest; split/group hashes; training logs; locked config; test/OOD raw predictions |
| **G6 — Performance** | Số đo native và end-to-end tái lập ở cùng quality | Raw latency samples; peak RSS; environment; binary hash; warm/cold protocol; failure/fallback cost |
| **G7 — Product acceptance** | Đạt Acceptance Threshold Freeze trên task thật và baseline công bằng | Acceptance report sinh từ immutable runs; receipt corpus; verifier evidence; decision record do user/product owner và independent reviewer ký |

Đối chiếu trạng thái hiện hành tại [Evidence Manifest G0–G7](./EVIDENCE_MANIFEST_G0_G7.md). Current status chỉ lấy từ manifest và latest finalized immutable run. Các review/audit liên kết trong tài liệu là snapshot lịch sử tại ngày ghi trên file; agent phải kiểm tra code hiện tại trước khi sửa. Khi manifest và tài liệu này xung đột, tiêu chí trong tài liệu canonical này được dùng cho run mới; trạng thái cũ không tự động được nâng cấp.

## 9. Kế hoạch ba sprint

### Sprint A — Làm sạch sự thật

**Tasks**

- Khóa authority và vocabulary.
- Sửa toàn bộ blocker §5 tại root cause.
- Khóa schema/ABI envelopes.
- Tạo run recorder tối thiểu và sinh metrics từ raw samples.
- Gắn nhãn hoặc cô lập stale benchmark/claim.

**Deliverables**

- Contract/schema và ABI manifest.
- Regression tests cho từng blocker.
- Một run thất bại mẫu chứng minh fail-closed.
- Evidence manifest cập nhật bằng liên kết artifact.

**Exit:** G0, G1 và G2 PASS. Không cần thêm tính năng.

### Sprint B — Vertical slice E0-Q

**Tasks**

- Khóa domain sáu yếu tố, codec version, energy/constraints và exact oracle.
- Freeze và hash domain/codec/energy/constraints bundle trước khi mở G3.
- Thu scene thật hoặc fixture bắt nguồn từ scene thật có provenance.
- Nối observation, proposal, verifier, sandbox executor, receipt và NPS evidence.
- Chạy exact scan và linear baseline end-to-end.

**Deliverables**

- Dataset/split manifest.
- Frozen domain bundle; oracle và baseline artifacts với cost báo riêng.
- Ít nhất một successful trace và các failure traces có chủ đích.
- Receipt/evidence corpus có hash.
- Calibration split; event semantics; confidence threshold và sample protocol đã khóa.
- Verifier corpus, raw predictions và báo cáo false-pass/false-fail.
- `acceptance_thresholds.json` đã freeze trước lần mở test.

**Exit:** G3 và G4 PASS; protocol G5 đã khóa trước training.

### Sprint C — Ablation VivyQu

**Tasks**

- Huấn luyện/đánh giá linear, structured real và phase+mixing theo cùng protocol.
- Chạy ablation no-phase/no-mixing/no-rotor/folded transform.
- Đo test, OOD, Core và end-to-end; ghi mọi fallback.
- Chỉ mở MPS khi dữ liệu rank/memory cho thấy nhu cầu.

**Deliverables**

- Immutable runs của từng nhánh.
- Bảng quality/latency/memory/failure công bằng.
- Go/stop decision cho phase, MPS và mục tiêu quantum-inspired.

**Exit:** G5 và G6 PASS. G7 chỉ PASS nếu tiêu chí sản phẩm đã khóa thực sự đạt; kết quả âm phải ghi `REJECTED`, không điều chỉnh tiêu chí sau khi xem kết quả.

## 10. Artifact run bất biến

Mỗi lần chạy tạo một thư mục mới; không sửa đè run đã hoàn tất:

```text
runs/<run_id>/
  manifest.json
  root_manifest.json
  protocol.json
  acceptance_thresholds.json
  source_hashes.json
  binary_hashes.json
  environment.json
  command.txt
  dataset_manifest.json
  raw_samples.jsonl
  raw_predictions.jsonl
  receipts.jsonl
  verifier_evidence.jsonl
  failures.jsonl
  metrics.json
  decision.json
  FINALIZED
```

`metrics.json` chỉ được tạo từ raw artifacts cùng run. Nếu phép đo không chạy hoặc lỗi, giá trị là `UNMEASURED` kèm lỗi; không dùng default. `decision.json` ghi gate, tiêu chí, technical reviewer hoặc user/product owner, và đường dẫn bằng chứng. Author của code/run không được là người ký duy nhất.

Khi finalize, `root_manifest.json` phải liệt kê relative path, byte size và content hash của mọi file trong run, cùng `finalized_at`. File marker `FINALIZED` chỉ chứa run ID, hash của `root_manifest.json` và thời điểm finalize. Sau marker, run là bất biến; mọi sửa nhỏ cũng phải tạo run ID mới. Dùng hashing và file operations chuẩn của nền tảng, không xây thêm framework nếu chưa cần.

Mỗi claim trong code comment, log, UI, README hoặc report phải mang đúng một nhãn:

- `DESIGN`: đặc tả chưa triển khai.
- `CODE`: mã hiện diện, chưa xác nhận runtime.
- `SYNTHETIC HARNESS`: chạy trên mock/fixture/synthetic data.
- `NATIVE MEASURED`: binary thật đã chạy, có raw sample và hash.
- `PRODUCT ACCEPTED`: G7 đã đạt trên task thật.
- `REJECTED`: giả thuyết hoặc cấu hình không đạt tiêu chí đã khóa.

## 11. Quy tắc go/stop

### Phase + mixing

`GO` khi cùng budget với structured real, phase+mixing cải thiện metric sản phẩm đã khóa và ablation cho thấy phase/mixing là nguyên nhân. `STOP/FOLD` khi lợi ích biến mất với `W_eff`, đến từ regularization/tuning khác nhau, hoặc không bù được latency/memory.

### MPS

`GO` khi coupling/rank analysis ủng hộ, `χ=4/8` giảm resident weights rõ ràng và quality nằm trong ngưỡng. `STOP` khi phải materialize/quét toàn state làm mất lợi ích hoặc truncation gây regret vượt ngưỡng. Sampling không được thay thế exact top-k nếu acceptance yêu cầu tối ưu chính xác.

### “Quantum-inspired”

Giữ tên này ở cấp nghiên cứu khi có phase/interference/mixing hoặc tensor structure được định nghĩa và ablation xác nhận. Nếu mô hình rút gọn thành linear/real transform tương đương, dùng tên kỹ thuật thực tế. Không suy ra quantum advantage hoặc classical speedup từ gate count.

### 64 KiB và dưới 10 µs

Đây là mục tiêu hoàn mỹ của **Core state/kernel**, không phải trạng thái đã đạt và không phải ngân sách toàn sản phẩm.

- `64 KiB` chỉ đạt cho state khi `4096 × complex128`; `complex64` là 32 KiB. Phải báo riêng weights, input, workspace, allocator và peak RSS.
- `<10 µs` chỉ được công nhận là `NATIVE MEASURED` khi có raw samples, binary/source hash, warm/cold protocol, CPU pinning/clock information và p99 trên số mẫu đã khóa.
- Product claim phải báo end-to-end latency gồm feature extraction, Core, verifier, executor và fallback.
- Nếu không đạt, giữ số đo thật và tối ưu sau profiling; không đổi định nghĩa ngân sách.

## 12. Hợp đồng làm việc cho agent

Trước khi nhận task, agent phải đọc tài liệu này cùng:

- [Review và hướng nghiên cứu 28/09](./REVIEW_AND_RESEARCH_DIRECTION_2026-09-28.md)
- [Audit Cautreo 29/09](./CAUTREO_AUXILIARY_CAPABILITY_AUDIT_2026-09-29.md)
- [Evidence Manifest G0–G7](./EVIDENCE_MANIFEST_G0_G7.md)
- [Audit đồng bộ/xung đột 29/09](./REVIEW_SYNC_CONFLICT_AUDIT_2026-09-29.md)

Agent phải:

1. Nêu gate, file và acceptance criterion mà task phục vụ.
2. Giữ diff nhỏ, sửa root cause và không mở nhánh speculative ngoài task.
3. Không sửa claim, metric hoặc trạng thái gate nếu không có artifact chứng minh.
4. Không dùng mock/synthetic/native result thay thế lẫn nhau.
5. Không sửa raw run artifact; rerun tạo `run_id` mới.
6. Báo cáo riêng bốn lớp: **code/syntax**, **test/harness**, **native/runtime**, **product/semantic**.
7. Ghi rõ điều chưa chạy, dependency thiếu, test bị skip và phạm vi snapshot.
8. Không tự gán `PASS`, `production`, `verified`, `100%`, `xN` hoặc `zero-copy` từ sự tồn tại của code.
9. Với thay đổi trust boundary, để lại ít nhất một negative regression test.
10. Không giao quyền semantic policy hoặc memory promotion cho Cautreo.
11. Xem audit/review là snapshot lịch sử; đọc code hiện tại, manifest hiện tại và latest finalized run trước khi kết luận hoặc sửa.
12. Không tự ký gate do chính mình triển khai hoặc chạy; tạo decision record để reviewer đúng thẩm quyền ký.

## 13. Definition of Done

Một task hoàn thành khi:

- Scope và gate được xác định; diff không chứa thay đổi ngoài scope.
- Acceptance criterion có check chạy được và kết quả được lưu.
- Lỗi/nhánh âm được kiểm tra; trust boundary fail-closed.
- Source và binary/artifact liên quan có hash.
- Tài liệu claim khớp đúng tầng bằng chứng.
- Không còn số liệu nhập tay được trình bày như measurement.
- Run đã finalize bằng root manifest, content hashes, `finalized_at` và marker.
- Gate decision có reviewer đúng thẩm quyền; author không tự PASS.
- Handoff nêu rõ: file đổi, lệnh chạy, kết quả, artifact, giới hạn và bước gate tiếp theo.

Vertical slice E0-Q chỉ hoàn thành khi G0–G7 đều PASS. Nếu chỉ G0–G6 đạt, kết quả là prototype native đã đo; chưa phải sản phẩm được nghiệm thu.

## 14. Backlog ưu tiên

| Ưu tiên | Công việc | Gate |
|---:|---|---|
| P0 | Rotor signs, multi-rotor chain rule, zero-hinge update | G2 |
| P0 | Loại random/fake-success fallback; fail-closed mask/buffer/executor | G2 |
| P0 | Context ownership/concurrency và ABI negative tests | G1–G2 |
| P0 | Dọn stale benchmark; immutable run recorder; raw-derived metrics | G2/G6 |
| P1 | Khóa E0-Q domain, codec, energy, constraints và exact oracle | G3 |
| P1 | Hoàn thiện typed envelopes và sandbox action/receipt trace | G1/G3 |
| P1 | Verifier độc lập, calibration và false-pass/false-fail | G4 |
| P1 | Scene-group split, held-out test và OOD manifest | G5 |
| P1 | Fair A/B: linear, structured real, phase+mixing và ablation | G5–G6 |
| P2 | MPS `χ=4/8` nếu có bằng chứng rank/memory | G6 |
| P3 | Early exit, steering, 72B sparse, KV compression, large verifier program | Sau G7, protocol riêng |

Thứ tự backlog là ràng buộc. Agent không lấy task P2/P3 khi P0 của gate nền còn mở, trừ nhiệm vụ chỉ đọc nhằm thu thập bằng chứng hoặc bác bỏ giả thuyết.

## 15. Quy tắc thay đổi tài liệu canonical

Mọi thay đổi tiêu chí phải tăng version, ghi lý do, phạm vi, người/agent đề xuất và bằng chứng. Không hạ tiêu chí sau khi đã xem test/OOD để biến failure thành PASS. Claim lịch sử được giữ với nhãn và snapshot; trạng thái hiện tại chỉ lấy từ latest finalized run artifact và manifest được liên kết.

**Lịch sử:** v1.1 bổ sung Acceptance Threshold Freeze, quyền ký gate độc lập, frozen E0-Q domain bundle, verifier/calibration evidence và cơ chế finalize run bằng content hashes. Không thay đổi trạng thái nghiệm thu sản phẩm.

---

**Phán quyết v1.1:** VivyQu tiếp tục như một chương trình kỹ thuật có kiểm chứng. Ba sprint tiếp theo chỉ phục vụ E0-Q, bằng chứng bất biến và baseline công bằng. Mọi năng lực khác chờ gate.
