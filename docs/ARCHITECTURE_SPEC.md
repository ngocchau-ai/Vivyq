# VivyQu — hợp đồng kiến trúc giai đoạn lý thuyết

**Trạng thái:** đề xuất cần kiểm chứng, chưa triển khai.  
**Ngày:** 2026-09-27.  
**Vai trò:** làm rõ ranh giới mô tả trong `MATH_SPEC_BLUEPRINT.md` và `SOUL_BODY_DECOUPLING.md`; các điểm cần kiểm chứng nằm trong `RESEARCH_AND_DEVELOPMENT_PLAN.md`.

## 1. Luồng ứng viên

```text
Môi trường / người dùng
        ↓
Cầu Treo: cảm nhận, trích xuất và xác thực vector, đóng gói mục tiêu
        ↓
VivyQu Core: mã hóa → biến đổi có cấu trúc → chấm điểm/chọn kết quả
        ↓
Cầu Treo: kiểm tra hợp đồng và an toàn thực thi → bộ thực thi/model vệ tinh
```

Đây là sơ đồ trách nhiệm, chưa khẳng định mọi bước đều cần tồn tại hoặc có hiệu quả. Một mốc đối chứng bắt buộc là Cầu Treo chuyển trực tiếp điểm ứng viên cho phép quét/chọn cổ điển; biến đổi lấy cảm hứng từ lượng tử chỉ được giữ nếu chứng minh lợi ích nhiệm vụ.

## 2. Hợp đồng ở biên Core

**Đầu vào dự kiến:** một vector thực 4.096 phần tử đã nằm trong bộ nhớ; bản mô tả hữu hạn về tập ứng viên, hàm mục tiêu và ràng buộc đã được chuẩn bị; phiên bản schema và chính sách xử lý giá trị không hữu hạn. Con số 4.096 chỉ là hình dạng dữ liệu, không bảo đảm rằng mỗi chiều ẩn tương ứng một hành động hay một trạng thái có nghĩa. Nguồn vector có thể là model hoặc bộ tạo khác; chi phí tạo vector nằm ngoài Core.

**Đầu ra dự kiến:** chỉ số ứng viên hoặc danh sách top-k cùng điểm, cờ hợp lệ/trạng thái lỗi và metadata đủ để Cầu Treo diễn giải theo cùng schema. `argmax` là chọn xác định; lấy mẫu theo phân phối là chế độ khác và phải ghi seed. Top-k không được gọi là ma trận mật độ rút gọn. Chưa cố định binary ABI hoặc bố trí bộ nhớ trước khi E0–E3 xác nhận dạng dữ liệu cần thiết.

**Bất biến:** cùng đầu vào và chế độ xác định phải cho cùng kết quả trong dung sai đã công bố; không đọc/ghi file, mạng hay gọi driver trong thuật toán Core; không trả hành động ngoài tập ứng viên; không xuất kết quả có NaN/Inf âm thầm; ràng buộc cứng phải được kiểm tra theo chính sách đã định nghĩa. Cầu Treo được phép từ chối thực thi vì vi phạm hợp đồng hoặc an toàn, phải báo lý do; quyền sửa quyết định ngữ nghĩa của Cầu Treo là câu hỏi sản phẩm chưa chốt.

## 3. Ranh giới hiệu năng và tài nguyên

**64 KiB trạng thái** là 4.096 số `complex128`, tức 65.536 byte. Không bao gồm vector đầu vào, toán tử, scratch, output, IPC, mã nguồn/model hay bộ nhớ tiến trình. Mục tiêu **64 KiB working-set** (nếu chọn) là mục tiêu riêng, đòi biểu diễn nhỏ hơn hoặc tính tại chỗ. Không giả định state này vừa L1 trên mọi CPU.

**Dưới 10 µs** được thử trước cho một lần gọi Core, tính từ trước mã hóa vector đã có trong bộ nhớ đến sau khi đầu ra đã sẵn sàng. Phải ghi p50/p95/p99 và điều kiện máy đo; tiêu chí tham vọng là p99 < 10 µs. Độ trễ tích hợp tính thêm model, truyền dữ liệu, đồng bộ, Cầu Treo và bộ thực thi. Trên GPU, phép đo phải tính host-to-completion. Không suy độ trễ tích hợp từ phép đo Core.

## 4. Quyết định còn mở

1. Bài toán sản phẩm đầu tiên, tập ứng viên, dữ liệu held-out và thước đo chất lượng.
2. Ánh xạ từ vector ẩn sang trạng thái/hành động; liệu pha phức có ích hơn vector thực giữ dấu.
3. Toán tử có kiểu toán học hợp lệ và chi phí phù hợp; có cần Clifford hay chỉ cần score/quét cổ điển.
4. `complex128`, `complex64` hay biểu diễn thực; giới hạn lỗi số học chấp nhận được.
5. Quy tắc lọc ràng buộc cứng, thẩm quyền từ chối thực thi và cách báo lỗi giữa Core/Cầu Treo.
6. ABI/IPC cụ thể, chiến lược CPU/GPU và cấp phát bộ nhớ sau khi đã có profile.

Các quyết định này phải được đóng bằng chứng cứ từ `RESEARCH_AND_DEVELOPMENT_PLAN.md` trước khi nâng thành đặc tả triển khai. Tài liệu hiện không đưa ra kết quả đo hay tuyên bố sản phẩm đã hoàn thành.

## Lịch sử thay đổi

- 2026-09-27 | Vy / doc_author: lập hợp đồng kiến trúc giai đoạn lý thuyết để lấp mục tài liệu được README tham chiếu; giữ các điểm chưa được chứng minh ở trạng thái mở.
