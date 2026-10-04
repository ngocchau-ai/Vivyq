# Verification Protocol

## 1. Independence

Verifier không nên là cùng role/session đã tạo artifact nếu host cho phép tách vai trò.

Verifier chỉ cần:
- Goal
- Success/Acceptance Criteria
- Artifact
- Evidence

Không dùng reasoning của executor làm bằng chứng.

## 2. Kết quả hợp lệ

- `PASS`
- `FAIL`
- `INCONCLUSIVE`

`INCONCLUSIVE` được xử lý như FAIL cho đến khi có thêm evidence.

## 3. Verify Checklist

- Artifact tồn tại?
- Đúng scope?
- Đạt từng acceptance criterion?
- Có lỗi nghiêm trọng?
- Evidence có tái kiểm tra được?
- Có phần nào chưa xác minh?
- Có external side effect chưa được duyệt?

## 4. Completion Rule

Chỉ set `STATE.status = COMPLETE` khi verifier PASS.
