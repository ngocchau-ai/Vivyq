> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** Nội dung muốn thay đổi phải đóng khung và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ.**

# Đối chiếu S2d với Định hướng canonical — Khoảng cách của VivyQu (2026-10-12)

**Nhãn:** `SYNTHETIC HARNESS` (kết luận S2d) · `[PROTOTYPE]`. Tài liệu này là phân tích, **không** phải nghiệm thu gate.
**Nguồn đối chiếu:** `VIVYQU_DEVELOPMENT_DIRECTION_AND_ACCEPTANCE_CRITERIA.md` v1.1 (canonical), `EVIDENCE_MANIFEST_G0_G7.md` (2026-09-29, **cũ**), spec ACC §8.13/§8.16, DD8–DD15.
**Giả định "chấp thuận S2d":** chấp nhận kết luận `[QUDIT KHÔNG HƠN QUBIT ĐỦ BẬC]`, H5+V không được ủng hộ (D1-C 1/3, D2-A 0/3, D2-Q 2/3 trong đó acc3 tầm thường).

## 1. S2d trả lời được gì, không trả lời được gì (so với canonical)

| Câu hỏi canonical | Tham chiếu | S2d cho biết | Mức bằng chứng |
|---|---|---|---|
| Phase+mixing/“quantum-inspired” có thắng structured real cùng ngân sách? (§6, §11) | `GO` khi thắng + ablation; `STOP/FOLD` khi lợi ích biến mất / chỉ do tuning khác / không bù latency-memory | **Không có lợi thế của qudit so với qubit đủ bậc** (H5 ≈ H6_interact ≈ H6_order4 ở acc1/acc2). Lợi ích đến từ **tương tác bậc cao có cổng** (S2c C2 +0.24/+0.39), không từ cấu trúc qudit | SYNTHETIC HARNESS |
| Tên gọi (§11 “Quantum-inspired”) | “Nếu rút gọn thành linear/real transform tương đương, dùng tên kỹ thuật thực tế” | → dùng tên kỹ thuật: **“gated interaction factor scorer”**, bỏ hàm ý qudit/quantum advantage | khớp DD11/DD15 |
| Có hơn baseline linear/low-rank cùng ngân sách? (§6 baseline sản phẩm tối thiểu) | Linear giữ nếu đạt quality với cost thấp nhất | Có ở harness: top1_V gộp H5 0.669 vs H1 0.470 (acc1), 0.778 vs 0.634 (acc2); acc3 mọi arm ≈ ngẫu nhiên (0.015–0.023). Params khớp trong ±1.2% quanh 524k | SYNTHETIC HARNESS, P5 tổng hợp |
| Có hơn exact/classical solver cùng ngân sách thời gian? (§1: “tốt hơn **hoặc rẻ hơn** baseline trung thực”; DD10) | arm học phải có p50 ≤ solver | **Chưa đạt/chưa đo công bằng:** beam B=64 đạt 99% (ACC-1) / 92% (ACC-2) trong ~0.03 ms, cao hơn top1_V tốt nhất của S2d (0.67/0.78) và nhanh hơn. `[GIẢ ĐỊNH]` S2d và beam không cùng quyền truy cập năng lượng — chưa kiểm tra tính công bằng theo §6 | DD10 + S2d |
| Latency của đề xuất+kiểm chứng (D1-L) | ≤ 1 ms p99 bản C++ | `[CHƯA ĐO]` (chưa có bản C++) | — |
| Hidden-state thật / G-ENC | S4 | Không kiểm tra; G-ENC đã FAIL (R² 0.22 < 0.5) và đang tạm dừng; điều kiện mở lại “S2d tín hiệu dương” **không thỏa** | DD12/DD15 |

**Điều S2d KHÔNG chứng minh:** không đủ để đóng G5 (không có `acceptance_thresholds.json`, split theo scene/group, calibration split, OOD). Bất kỳ số S2d nào cũng không được nâng thành `NATIVE MEASURED` hay `PRODUCT ACCEPTED`.

## 2. Khoảng cách theo mục tiêu gần nhất (vertical slice E0-Q, canonical §1)

Mục tiêu: *observation thật → proposal VivyQu → verifier độc lập → Cautreo thực thi sandbox → receipt → evidence bất biến → NPS promotion/rollback; trên dữ liệu chưa thấy tốt hơn hoặc rẻ hơn baseline trung thực cùng ngân sách.*

| Gate | Yêu cầu PASS (canonical §8) | Hiện trạng (nguồn) | Khoảng cách |
|---|---|---|---|
| G0 Authority | Một cognition owner + sign-off user/product owner & reviewer độc lập | Manifest 09-29: PARTIAL, thiếu sign-off | Thiếu chữ ký decision record |
| G1 Contract/ABI | 5 envelope + ABI version hóa, test dương/âm | Manifest: PARTIAL (thiếu negative dtype/short-buffer). Verified hôm nay: **không có** thư mục `schemas/`, `include/` có; `tests/test_engine_boundary_negative.py` tồn tại (chưa audit nội dung) | Chưa có schema 5 envelope; ABI manifest `[CHƯA VERIFY]` |
| G2 Fail-closed | Blocker §5 xử lý, không fake success | Manifest: PARTIAL (còn empty-mask A2). Từ manifest tới nay: commit `9abd40d` sửa watchdog không còn giả confidence=1.0; 167 test pass | Chưa tái audit §5 blocker 1–8 từng mục; **blocker nghiên cứu §5.1–5.3 (dấu induced blade, chain rule nhiều rotor, hinge=0) `[CHƯA VERIFY]`** |
| G3 Vertical slice | Domain/codec/energy/constraints freeze + hash; 1 trace thật observation→action→receipt trong sandbox | Manifest: CHƯA. Verified hôm nay: không có `runs/`; có `data/e0_benchmark/*_oracle.npy` và `VIVYQU_DATA_FLOW_AND_CODEC_SPEC.md`, `python/vivyqu/codec.py` (đã thiết kế/mã); **không thấy domain bundle đã hash/freeze, không thấy trace thật** | Chưa bắt đầu phần thực thi sandbox + receipt |
| G4 Verification | Verifier độc lập, calibration, false-pass/fail | Manifest: CHƯA (chưa có inventory verifier) | Chưa có |
| G5 Learning | `acceptance_thresholds.json` khóa trước; train/val/calib/test/OOD riêng | Verified: **không có** `acceptance_thresholds.json`. Học mới ở mức ACC harness tổng hợp (S2b/c/d) | Gate chưa thể mở |
| G6 Performance | Số đo native + end-to-end cùng quality, raw samples + binary hash | PARTIAL. Hôm nay đo (có raw log): Core native p50 17.8 / p99 25 µs (ADR) vs mục tiêu <10 µs p99 → **gấp ~2.5× ở p99**; Python smoke p50 5.6 µs (T2); Piggyback marginal p99 ~132 µs trung vị (24 lượt, T3); torque ISOLATED p50 374 µs vs 60 µs (**~6×**). End-to-end: LLM forward 0.25–3.3 s/prompt chi phối (không đạt “vài ms”, ADR §0) | Core xa mục tiêu <10 µs; end-to-end thiếu protocol; chưa có `runs/` immutable |
| G7 Product | Đạt freeze trên task thật, baseline công bằng | CHƯA | Chưa bắt đầu |

**Đếm (theo manifest + kiểm tra hôm nay):** PASS 0/8 · PARTIAL 4/8 (G0, G1, G2, G6) · CHƯA 4/8 (G3, G4, G5, G7). Manifest ngày 2026-09-29, **chưa được cập nhật** sau các thay đổi tới 2026-10-12 → số PARTIAL/CHƯA có thể thấp hơn thực tế ở G2/G6 `[CẦN CẬP NHẬT MANIFEST]`.

## 3. Vị trí theo kế hoạch 3 sprint (canonical §9)

| Sprint | Exit | Vị trí hiện tại |
|---|---|---|
| A — Làm sạch sự thật | G0, G1, G2 PASS | **Đang dở:** còn sign-off, schema/ABI manifest, tái audit blocker §5, run recorder tối thiểu (`runs/` chưa có) |
| B — Vertical slice E0-Q | G3, G4 PASS; protocol G5 khóa | **Chưa bắt đầu thực chất:** chưa freeze domain bundle, chưa trace sandbox, chưa verifier, chưa `acceptance_thresholds.json` |
| C — Ablation VivyQu | G5, G6 PASS; go/stop | **Làm trước ở mức tổng hợp:** ablation H1–H6, no-rotor, folded rotor, qudit-vs-qubit (S2b–S2d) chỉ là `SYNTHETIC HARNESS`; chưa phải immutable run theo §10 |

Nói cách khác: phần nghiên cứu (Sprint C) đi **trước** hạ tầng (Sprint A/B). Điều này không sai về khám phá, nhưng canonical §8: “không dùng PASS gate thấp để suy ra gate cao”, và §5: “không dùng kết quả benchmark mới để quyết định kiến trúc cho đến khi blocker liên quan có test tái hiện và hồi quy” — kết luận S2d chỉ nên ảnh hưởng tên gọi và hướng nghiên cứu, **không** ảnh hưởng quyết định kiến trúc sản phẩm.

## 4. Hệ quả đề xuất (chờ chủ dự án duyệt)
1. **Đổi tên kỹ thuật:** bỏ “qudit/quantum-inspired” trong mô tả sản phẩm; dùng “gated interaction factor scorer” (canonical §11). Giữ H1 linear làm baseline sản phẩm tối thiểu.
2. **Ưu tiên đóng khoảng cách hạ tầng trước:** (a) cập nhật Evidence Manifest, (b) schema 5 envelope + ABI manifest + negative tests (G1), (c) tái audit blocker §5 (G2), (d) run recorder `runs/<run_id>/` tối thiểu (§10).
3. **Chưa mở G-ENC/S4 và chưa mở rộng thêm nhánh qudit** (đóng băng theo §2).
4. **Kiểm tra tính công bằng so với classical solver** (DD10) trước khi nói “tốt hơn baseline”: xác định quyền truy cập năng lượng của solver vs scorer.
5. **Core latency:** quyết định có theo đuổi <10 µs p99 hay giữ T1 (p99<100 µs, mục tiêu 50 µs) — hiện chênh ~2.5× so với mục tiêu canonical; cần profile (DD8 ghi nguồn chi phí P2/Core).

## 5. Hạn chế của chính phân tích này
- Hiện trạng G1/G2/G3 dựa vào manifest cũ + kiểm tra sự hiện diện file; chưa đọc nội dung `test_engine_boundary_negative.py` và chưa tái audit từng blocker §5 `[CHƯA VERIFY]`.
- Không quy đổi “khoảng cách” thành phần trăm hay thời gian vì không có cơ sở đo (tránh số bịa); chỉ đếm gate/sprint.
- Số S2d là P5 tổng hợp, 5 seed, một cấu hình; có một bất thường chưa giải thích (acc2 H6 seed 5).

## Lịch sử thay đổi
| Thời gian | Agent | Hành động |
|---|---|---|
| 2026-10-12 20:30 | Antigravity IDE (Claude Sonnet 5.5, conv 46df9870) | Tạo tài liệu đối chiếu S2d ↔ canonical theo yêu cầu chủ dự án |
