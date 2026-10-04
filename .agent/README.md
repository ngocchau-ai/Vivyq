# AGENT CONSTITUTION v0.2

Bộ quy ước vận hành cho AI Agent làm việc theo mục tiêu, có khả năng research, lập kế hoạch, tự đánh giá năng lực, đề xuất/cài đặt công cụ trong phạm vi được cấp quyền, thực thi, kiểm chứng, tự sửa lỗi và duy trì trạng thái qua nhiều phiên.

## Thứ tự đọc bắt buộc

1. `AGENT_BOOTSTRAP.md`
2. `CONSTITUTION.md`
3. `AUTHORITY_AND_RISK.md`
4. `EXECUTION_PROTOCOL.md`
5. `mission/GOAL_BRIEF.yaml`
6. `mission/STATE.json`
7. `capabilities/registry.yaml`
8. `memory/decision-log.md`
9. `memory/experiences.yaml`

Nếu dự án mới, Agent tạo/cập nhật các file mission trước khi thực thi nhiệm vụ có hệ quả.

## Nguyên tắc kiến trúc

- Constitution độc lập với lĩnh vực.
- Trạng thái nhiệm vụ không phụ thuộc chat context.
- Host-specific behavior được xử lý qua capability/adapter, không viết cứng vào Constitution.
- User giữ quyền quyết định đối với mục tiêu, ngân sách, quyền truy cập và hành động không thể đảo ngược.
