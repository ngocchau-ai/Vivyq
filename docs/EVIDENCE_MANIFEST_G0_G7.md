# EVIDENCE MANIFEST G0–G7

**Ngày:** 2026-09-29  
**Nguồn chuẩn:** `docs/CAUTREO_AUXILIARY_CAPABILITY_AUDIT_2026-09-29.md` §9  
**Quy tắc:** Không dùng PASS gate thấp để suy ra gate cao. Harness synthetic chỉ hỗ trợ G1/G2.

## Thang bằng chứng

`Thiết kế ≠ Mã ≠ Harness ≠ Native đã chạy ≠ Sản phẩm được nghiệm thu`

Mọi claim phải ghi: source hash · binary hash · command · raw output · environment · gate mà nó **thực sự** chứng minh.

| Gate | Điều kiện PASS tối thiểu | Bằng chứng phải lưu | Trạng thái hiện tại |
|------|--------------------------|---------------------|---------------------|
| **G0 — Ownership** | Một cognition owner; bảng quyền Cautreo/Vivy không mâu thuẫn | Spec version + reviewer sign-off | **PARTIAL** — README đã khóa Vivy=semantic / Cautreo=execution safety; cần sign-off |
| **G1 — Contract** | Observation/Action/Receipt/Evidence schemas + ABI dtype-size-lifetime khóa | Schema, header, negative contract tests | **PARTIAL** — frame ABI khớp; thiếu negative dtype/short-buffer tests |
| **G2 — Boundary safety** | Wrong dtype/short/non-contiguous, all-masked, timeout, stale output đều fail closed | Raw test output + binary/source hashes | **PARTIAL** — đã guard rotor plane, float64 contiguous, fallback validity; còn empty-mask A2 |
| **G3 — Auxiliary E2E** | Một tác vụ thật: Mắt/Tai→Vivy→Tay→receipt, provenance round-trip | Trace ID, timestamps, artifacts, replay | **CHƯA** |
| **G4 — Verifier** | ≥3 verifier có oracle/coverage/error rates; reward không tự promotion | Inventory + held-out confusion/error | **CHƯA** — chưa có inventory |
| **G5 — Native intervention** | Backend model thật cung cấp layer state; exit/steering có control, calibration, fallback | Build/version, raw runs, quality-cost curves | **CHƯA** — chỉ mock |
| **G6 — Performance** | Báo Core/transport/model/verifier/full-task riêng; cold/warm, RSS, p50/p95/p99 | Raw samples, environment manifest, command lines | **PARTIAL** — E9 latency đã tách MEASURED/UNMEASURED |
| **G7 — Product** | Task suite thật có baseline cùng tài nguyên; cải thiện lặp lại, không vượt risk budget | Blind/held-out results, failure corpus, rollback | **CHƯA** |

## Owner contract (G0)

| Vùng | Được làm | Không được làm |
|------|----------|----------------|
| Vivy/VivyQu | hypothesis, semantic policy, quyết định, memory promotion | — |
| Cautreo | I/O, tool bus, executor, receipt/verifier adapter, resource, execution safety | semantic policy, reward ownership, “nhận thức kép” |

## Checklist claim → evidence

- [ ] Mỗi latency có raw sample + DLL/source SHA-256 + command line
- [ ] Mỗi quality number có held-out/OOD protocol + seed
- [ ] Mỗi “100%” chỉ dùng cho metric có denominator được liệt kê
- [ ] Zero-copy chỉ khi cùng allocation consumer đọc trực tiếp (hiện Python hot path là preallocated copy)
- [ ] Native claim chỉ khi backend thật expose/accept hook (không suy từ NumPy mock)

## Backlog evidence (theo audit 29/09 §5)

1. Ownership sign-off  
2. Negative ABI tests (dtype/shape/stride/lifetime)  
3. Trace E2E `fs-read → decision → sandbox write → receipt → verifier`  
4. Native model hook theo backend/version  
5. Early-exit quality curve  
6. Steering causal/off-target  
7. Verifier governance (anti reward-hacking)  
8. Memory promotion/rollback  
9. Paging/sparsity model-specific benchmark  
10. Product acceptance suite  
