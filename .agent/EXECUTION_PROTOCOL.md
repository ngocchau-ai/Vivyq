# EXECUTION PROTOCOL

## 1. Mission State Machine

Các state hợp lệ:

`IDLE`
`INTAKE`
`DISCOVERING`
`AUDITING_CAPABILITIES`
`WAITING_APPROVAL`
`PLANNING`
`PILOTING`
`EXECUTING`
`VERIFYING`
`REPAIRING`
`BLOCKED`
`PAUSED`
`COMPLETE`
`FAILED`

Mọi state transition quan trọng phải cập nhật `mission/STATE.json`.

## 2. Failure Taxonomy

- `F1 TRANSIENT`: timeout, network, rate limit → retry/backoff.
- `F2 ENVIRONMENT`: thiếu package, conflict, disk → repair environment.
- `F3 TOOL`: API/UI/CLI đổi → rediscover/update adapter/skill.
- `F4 PLAN`: assumption sai/dependency thiếu → replan.
- `F5 PERMISSION`: auth/2FA/access denied → user checkpoint.
- `F6 GOAL`: mục tiêu/criteria mâu thuẫn → user decision.

F1–F4: không hỏi user nếu tự sửa được trong envelope.
Cùng lỗi không retry vô hạn; sau 3 lần phải reclassify, replan hoặc BLOCKED.

## 3. Replan Scope

`LOCAL → TASK → WORKSTREAM → MISSION`

Chỉ tăng scope khi mức thấp hơn không đủ.
MISSION replan luôn cần Change Request.

## 4. Resource Manager

Trước tác vụ C2/C3, agent phải xem:
- CPU/GPU/RAM
- disk
- concurrent jobs
- browser sessions
- API quota
- token quota
- monetary budget
- deadlines

Không spawn concurrency vượt resource policy.

## 5. Pilot Rule

Task lặp lại hoặc scale lớn:
- làm 1 đơn vị mẫu,
- đo time/cost/quality,
- verify,
- chỉ scale khi pilot PASS hoặc user chấp nhận trade-off.

## 6. Reporting

Báo user khi:
- readiness hoàn thành,
- cần approval,
- pilot result,
- blocker,
- major replan,
- final verification.

Không cần hỏi đối với tiến triển kỹ thuật bình thường trong envelope.
