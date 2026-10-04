# S3 G-ENC ACC-1 — Chẩn đoán, 2 phương án kỹ thuật, đánh giá có cần tiếp tục

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

**Trạng thái:** `[ĐỀ XUẤT — chờ chủ dự án quyết]` · Liên quan: spec ACC §3 (P1–P6), §G-ENC (dòng 78), §8.12, §8.13, §8.15 · Code: `scripts/acc/hidden_pipeline.py` (commit 4a4c573)

## 1. Dữ kiện (đã đo, seed 0, val 500 mẫu)

| Probe (ridge, alpha chọn trên holdout nội bộ train) | R²_val | P6 (xáo nhãn) |
|---|---|---|
| L21 token cuối | 0.100 | −0.272 |
| L31 token cuối (tốt nhất) | 0.191 | −0.226 |
| L41 token cuối | 0.179 | −0.228 |
| Ghép L21+L31+L41 (7680 chiều, alpha=3000) — đo 11:38 | 0.220 | — |
| **Ngưỡng G-ENC** | **≥ 0.5** | < 0.1 |

Chẩn đoán theo nhóm feature (`scratch/genc_diag.py`):
- 15 trọng số cạnh (78% bằng 0): R² trung bình ~0.19, cao nhất 0.77 → một phần thông tin **có** trong token cuối.
- 24 bit cấm (tỷ lệ 15%): L21 0.04, L31 0.19, L41 0.18.
- Holdout R² đạt đỉnh ở alpha lớn (1000–3000), ghép 3 layer chỉ tăng +0.03 → **nút thắt là "1 token cuối" phải nén 39 giá trị số**, không phải chọn layer.
- P6 âm và ổn định → không rò rỉ, pipeline sạch. Kết quả fail là thật.

Kết luận chẩn đoán: `[ĐÃ KIỂM CHỨNG]` hidden-state token cuối của Gemma4 E4B Q4_K_M không mang đủ thông tin instance ACC-1 ở dạng tuyến tính. Đúng rủi ro spec đã dự liệu (dòng 81).

## 2. Phương án A — Đọc theo vị trí (slot pooling) trên prompt định dạng cố định

- **Prompt v2 chuẩn tắc:** liệt kê đủ 15 cặp theo thứ tự cố định (kể cả trọng số 0.00) và lưới cấm 6×4 dạng 0/1. Mỗi giá trị nằm ở vị trí token xác định được.
- **Trích:** sửa `hidden_extract.cpp` để lưu hidden L31 tại các vị trí token của từng giá trị (hoặc mean theo đoạn), thay vì chỉ token cuối.
- **Probe:** ridge từ vector slot → feature tương ứng.
- **Kỳ vọng:** R² cao (số được mã hóa cục bộ ở token chứa nó). `[GIẢ ĐỊNH — cần pilot]`
- **Chi phí:** sửa C++ ~1–2 h; trích lại 3000 prompt, prompt dài hơn → ước ≥ 2.3 h (lần trước 8141 s). Pilot trước 600 prompt (~35 phút) để đo tốc độ.
- **Phản biện:** gần như tautology — chứng minh mô hình "chép lại" input, không chứng minh có biểu diễn tổng hợp. Đổi giao diện Core từ 1 vector sang tập slot (39 × 2560) → khác giả định P2 hiện tại, cần pre-register lại S4.

## 3. Phương án B — Tách "thiếu thông tin" khỏi "thông tin phi tuyến / thiếu dữ liệu"

- Giữ token cuối (giữ giao diện Core 1 vector), tăng n_train 2000 → 8000 và thêm probe MLP 1 lớp ẩn (báo cáo riêng, **không** thay gate tuyến tính).
- Thêm suffix prompt yêu cầu mô hình tóm tắt instance trước "Answer:" (đẩy thông tin vào token cuối).
- **Quyết định đọc:** nếu R² tuyến tính vẫn < 0.5 với 8000 mẫu nhưng MLP ≥ 0.5 → thông tin có nhưng phi tuyến; nếu cả hai < 0.5 → token cuối không đủ, đóng nhánh 1-vector.
- **Chi phí:** trích thêm 6000 prompt × ~3.3 s ≈ 5.5 h CPU (tranh CPU với S2d); probe vài phút.
- **Phản biện:** probe MLP mạnh có thể "học task" thay vì đọc thông tin → bắt buộc giữ P6 và so với MLP trên input ngẫu nhiên cùng chiều.

## 4. Đánh giá: có cần tiếp tục hướng G-ENC lúc này không?

**Khuyến nghị: TẠM DỪNG, không chạy A hoặc B ngay.** Lý do:
1. G-ENC chỉ là cổng cho S4 (chạy arm trên hidden-state thật). S2c C1 đã FAIL trên P5, và §8.12 quy định C1 fail thì **không cần** lặp lại C1 ở S4 → G-ENC không nằm trên đường găng.
2. S2d cũng chạy trên P5, không cần G-ENC.
3. Thí nghiệm mới tranh CPU với S2d đang chạy (bài học 2026-10-04: tiến trình nền làm sai số đo ~9×).
4. Dữ kiện đã đủ cho một quyết định kiến trúc: muốn Core giải bài cấu trúc thì nên nạp **đặc trưng có cấu trúc** (từ parser/tool) thay vì hidden-state token cuối.

**Điều kiện mở lại:** nếu S2d cho tín hiệu dương (D1-C đạt, hoặc C2 cần kiểm lại ở S4) → chạy pilot **Phương án B trước** (giữ giao diện 1 vector, không cần sửa C++), A chỉ khi B kết luận "token cuối không đủ" mà vẫn cần nhánh hidden-state.

## Lịch sử thay đổi
| Thời gian | Agent | Nội dung |
|---|---|---|
| 2026-10-04 11:40 | Antigravity (Claude Opus 5.5, conv dac524cf) | Tạo mới: chẩn đoán G-ENC acc1, đo thêm probe ghép 3 layer (R² 0.220), 2 phương án, khuyến nghị tạm dừng |
