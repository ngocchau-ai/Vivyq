# Recovery Protocol

## 1. Mục tiêu

Cho phép resume sau:
- agent/session crash,
- host restart,
- mất browser session,
- tool failure,
- machine restart.

## 2. Checkpoint

Trước bước dài hoặc có rủi ro:
- cập nhật STATE,
- ghi task hiện tại,
- ghi artifact/evidence đã có,
- ghi next_action,
- lưu reference cần thiết để resume.

## 3. Resume

Khi khởi động lại:
1. Đọc Bootstrap/Constitution.
2. Đọc Goal Brief.
3. Đọc State.
4. Đối chiếu filesystem/tool state với State.
5. Nếu lệch, ghi reconciliation decision.
6. Resume từ checkpoint an toàn gần nhất.
