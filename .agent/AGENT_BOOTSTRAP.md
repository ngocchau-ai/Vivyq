# AGENT BOOTSTRAP — Hướng dẫn Agent nhận và thực thi quy ước

## 1. Khởi động phiên

Khi bắt đầu phiên làm việc trong workspace có `.agent/`, Agent phải:

1. Đọc `CONSTITUTION.md`.
2. Đọc `AUTHORITY_AND_RISK.md`.
3. Đọc `mission/GOAL_BRIEF.yaml`.
4. Đọc `mission/STATE.json`.
5. Đọc `capabilities/registry.yaml`.
6. Đọc phần gần nhất trong `memory/decision-log.md`.
7. Tra `memory/experiences.yaml` nếu gặp tình huống đã từng xử lý.
8. Xác định trạng thái hiện tại và bước hợp lệ tiếp theo.
9. Không hỏi lại điều đã có trong các file trạng thái.
10. Nếu `STATE.status = WAITING_APPROVAL`, không vượt qua checkpoint.

## 2. Phân loại độ phức tạp

- `C0 — TRIVIAL`: tác vụ nhỏ, ít bước, không có thay đổi hệ thống.
- `C1 — BOUNDED`: nhiệm vụ rõ, phạm vi nhỏ, có thể hoàn thành trong một phiên.
- `C2 — PROJECT`: nhiều bước/phụ thuộc, có tool/resources/artifacts.
- `C3 — LONG_RUNNING`: nhiều phiên/workstream/sub-agent, có quota, budget hoặc risk đáng kể.

Quy tắc:
- C0/C1: có thể dùng Goal Contract rút gọn.
- C2: bắt buộc có `GOAL_BRIEF.yaml`.
- C3: bắt buộc có `GOAL_BRIEF.yaml` và `READINESS_REPORT.md` trước khi mở rộng quy mô.

## 3. Vòng đời chuẩn

`INTAKE → GOAL → DISCOVERY → CAPABILITY_AUDIT → ACQUISITION → PLAN → PILOT → EXECUTE → VERIFY → REVIEW_AND_LEARN`

## 4. Khi nào hỏi người dùng

Chỉ hỏi khi quyết định thuộc về người dùng:
- Goal hoặc success criteria mâu thuẫn.
- Change Request ở cấp Mission.
- Chạm R2/R3 ngoài permission envelope.
- Cần chi tiền, tài khoản, credential, 2FA, CAPTCHA.
- Cần lựa chọn kinh doanh/pháp lý/quyền riêng tư mà agent không được tự quyết.
- Không thể xác minh giả định quan trọng.

Không hỏi đối với F1–F4 nếu còn trong permission envelope.

## 5. Khi được tự mở rộng năng lực

Agent chỉ được tải/cài/bật/build capability khi:
1. Có capability gap cụ thể.
2. Đã kiểm tra capability hiện có.
3. Chọn bậc ít xâm lấn nhất.
4. Đã rà trust/security/license/cost.
5. Hành động nằm trong envelope hoặc đã được duyệt.
6. Thử trong sandbox trước khi đưa vào môi trường thật.
7. Có test tối thiểu.
8. Ghi kết quả vào registry.

## 6. Cách báo cáo

Agent báo:
- milestone quan trọng,
- blocker,
- thay đổi kế hoạch,
- thay đổi capability,
- checkpoint cần người dùng.

Không spam thao tác kỹ thuật cấp thấp.

Không được tuyên bố `COMPLETE` trước khi verifier trả `PASS`.
