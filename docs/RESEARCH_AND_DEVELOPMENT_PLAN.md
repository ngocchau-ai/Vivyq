# VivyQu — chương trình hoàn thiện lý thuyết và thực nghiệm

**Trạng thái:** đề cương nghiên cứu, chưa triển khai hay đo hiệu năng VivyQu  
**Ngày:** 2026-09-27  
**Phạm vi:** lõi tính toán trạng thái 4.096 chiều; Cầu Treo giữ vai trò thu nhận, điều phối và thực thi như trong `SOUL_BODY_DECOUPLING.md`.

## 1. Mục tiêu và quy ước chứng cứ

Hai đích **64 KiB trạng thái** và **dưới 10 µs mỗi lần xử lý lõi** là mục tiêu hoàn mỹ để theo đuổi, chưa phải đặc tính đã đạt. Mọi báo cáo phải gắn nhãn: **giả thuyết**, **suy ra từ toán học**, **được nguồn ngoài hỗ trợ**, **đo bằng harness**, **đo trên hệ tích hợp**, hoặc **đạt chất lượng sản phẩm**. Không nâng cấp nhãn chỉ vì mã chạy hoặc phép đo vi mô nhanh.

Một chu trình được xác định rõ: đầu vào là vector thực 4.096 phần tử đã có sẵn trong bộ nhớ và đặc tả mục tiêu/ràng buộc đã biên dịch; đầu ra là chỉ số quyết định hoặc danh sách top-k kèm điểm và trạng thái lỗi. Đồng hồ **core-only** bắt đầu trước phép mã hóa, kết thúc sau chọn đầu ra; bao gồm mọi bản sao, cấp phát và khôi phục buffer do lõi tạo ra. Đồng hồ **end-to-end** tính thêm lấy vector từ model, IPC, đồng bộ, Cầu Treo và thực thi. Báo cáo cả hai, không dùng core-only để suy ra độ trễ sản phẩm. Với GPU, đo thêm thời gian host-to-completion, không chỉ kernel time.

**64 KiB** chính xác là `4096 × 16 = 65.536 byte` cho một vector `complex128`; nó không tính vector đầu vào, toán tử, scratch, mã chương trình, metadata, IPC hay model nguồn. Không bảo đảm vừa L1 vì dung lượng L1 khác nhau và còn dữ liệu khác cạnh tranh. Chỉ tiêu bộ nhớ cần báo cáo riêng: (a) state bytes, (b) working-set đỉnh của lõi, (c) RSS tiến trình và (d) bộ nhớ model/thiết bị. Nếu mục tiêu toàn bộ working-set là 64 KiB, `complex128` không để lại byte nào cho phần còn lại; cần biểu diễn nhỏ hơn hoặc tính tại chỗ.

## 2. Những chỗ trong bản phác thảo cần chứng minh lại

| Phát biểu hiện có | Diễn giải chặt chẽ và việc cần làm |
|---|---|
| `R^4096` tương đương Hilbert `C^4096` | Bằng nhau về **số tọa độ**, không đẳng cấu tuyến tính phức. Ánh xạ vector thực sang biên độ phức là lựa chọn mã hóa; chứng minh hoặc đo khả năng giữ thông tin nhiệm vụ. Thử `c=h/||h||₂` làm mốc giữ dấu, so với `|h|` và pha sigmoid được đề xuất. Quy định xử lý vector không hữu hạn, norm bằng 0 và phương sai bằng 0. |
| Rotor `R|ψ⟩R†` | Biểu thức sandwich phù hợp với một số đối tượng đại số/toán tử, không tự động hợp kiểu với ket. Phải chọn rõ biểu diễn Clifford, ánh xạ sang ma trận/tác động tuyến tính trên 4.096 biên độ, điều kiện bảo toàn norm và chi phí tính. Nếu không, dùng toán tử thưa/trực giao hoặc unitary có cấu trúc làm mốc đơn giản. |
| Giao thoa tự loại phương án sai | Pha chỉ tạo triệt tiêu khi toán tử và mã hóa liên hệ đúng với hàm mục tiêu; không có bảo đảm từ việc gán pha đơn lẻ. Cần oracle/score có thể kiểm định, phản ví dụ, và phép so sánh với thuật toán cổ điển. |
| Grover khoảng 50 bước | `π√N/4 ≈ 50` là số **lần truy vấn oracle** trong bài toán tìm kiếm không cấu trúc có oracle thích hợp trên máy lượng tử, không phải cam kết runtime của mô phỏng cổ điển, cũng không giải tổng quát bài toán tối thiểu Hamiltonian. Tính chi phí oracle, khuếch tán, chuẩn bị trạng thái và đọc kết quả cho từng phương án. |
| `argmax |cₖ|²` là phép đo sụp đổ | Đây là chọn quyết định xác định; phép đo Born là lấy mẫu theo phân phối. Chọn một hợp đồng đầu ra và tiêu chí chất lượng tương ứng. |
| Top-M đường chéo là ma trận mật độ rút gọn | Nó là phân phối top-M bị cắt hoặc toán tử đường chéo, không phải partial trace của hệ con. Nếu cần reduced density matrix, xác định tensor factor và thực hiện partial trace; nếu chỉ cần top-M, gọi đúng tên và quy định chuẩn hóa phần khối lượng bị bỏ. |

Nguồn lý thuyết: [Grover, bài báo gốc](https://arxiv.org/abs/quant-ph/9605043); [IBM Quantum, density matrices và partial trace](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/introduction). Các mục trong bảng là đánh giá toán học đối với bản phác thảo, **chưa** phải kết quả thực nghiệm VivyQu.

## 3. Rào cản và nhánh kỹ thuật cần thử

1. **Ý nghĩa của trạng thái:** chiều 4.096 của model không mặc nhiên khớp 4.096 hành động hay basis state. Xây bộ ánh xạ nhãn hành động/ứng viên, kiểm tra dữ liệu held-out và phép xoay/đổi model. Ưu tiên model không bị phụ thuộc vào một tầng ẩn duy nhất.
2. **Chất lượng quyết định:** định nghĩa bài toán cụ thể trước khi chọn toán tử: tập ứng viên, objective, ràng buộc cứng, output hợp lệ, điểm tham chiếu. Mọi thuật toán phải so với argmax score, lọc ràng buộc + quét tuyến tính, và random hợp lệ. Nếu biến đổi Hilbert không thắng mốc ở chất lượng hoặc chi phí, không giữ nó chỉ vì hình thức lượng tử.
3. **Chi phí toán tử:** ma trận dày `4096²` có 16.777.216 phần tử, riêng complex128 khoảng 256 MiB; không phù hợp mục tiêu. Thử toán tử đường chéo, hoán vị, block/sparse có cấu trúc, tích Kronecker hoặc rotor thật sự có khai triển rẻ. Ghi số phép toán và bộ nhớ trung gian, kiểm tra norm/sai số số học.
4. **Biên bộ nhớ:** hướng A: state `complex128` 64 KiB để giữ mốc độ chính xác; hướng B: `complex64` 32 KiB dành 32 KiB cho scratch và output; hướng C: vector thực 16/32 KiB nếu pha không tạo lợi ích. Đánh đổi phải dựa trên lỗi quyết định, không chỉ sai số norm.
5. **Biên thời gian:** CPU tại chỗ, dữ liệu ấm cache, một thread là giả thuyết đầu tiên để nhắm <10 µs; benchmark cùng dữ liệu lạnh và thay đổi xung nhịp. GPU chỉ là nhánh đối chứng sau khi đo host-to-completion vì chi phí launch/đồng bộ có thể lấn át tác vụ nhỏ; CUDA Graph/fusion chỉ thử nếu profile chỉ ra bottleneck này. [NVIDIA CUDA Graph](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html) mô tả lợi ích giảm chi phí launch, không chứng minh VivyQu đạt 10 µs.
6. **Nguồn vector và ranh giới sản phẩm:** lấy hidden state từ LLM vẫn tốn thời gian và bộ nhớ của LLM; việc bỏ decoder văn bản không làm biến mất chi phí encoder/prefill. Cầu Treo được phép xác thực hợp đồng, an toàn tài nguyên và lỗi đầu vào; quyền quyết định ngữ nghĩa cần được đặc tả riêng để tránh xung đột với nguyên tắc không sửa quyết định của lõi.

## 4. Ma trận thực nghiệm tối thiểu

| Thử nghiệm | Biến thể / mốc đối chứng | Đo và điều kiện chấp nhận |
|---|---|---|
| E0 — xác lập bài toán | Ít nhất một bài toán không gian tham số nhỏ có oracle nghiệm, tập held-out, ràng buộc cứng; random hợp lệ và quét toàn bộ 4.096 ứng viên | Công bố dữ liệu/seed, tỷ lệ hợp lệ, regret/điểm objective, thời gian mốc. Chưa có bài toán này thì chưa tuyên bố “nhận thức” hay tối ưu. |
| E1 — mã hóa | signed real, complex pha bằng 0, công thức pha đề xuất; trường hợp zero/constant/NaN | Norm, tính xác định, tỉ lệ bảo toàn thứ hạng/hiệu năng held-out. Với `argmax |c|²` và không có toán tử phụ thuộc pha, signed real và complex pha bằng 0 có thể cho đầu ra tương đương; chỉ so giá trị của pha sau khi có toán tử khai thác pha. Công thức pha chỉ được giữ nếu cải thiện có lặp lại so với signed baseline. |
| E2 — toán tử | không biến đổi; diagonal/sparse/Kronecker; Clifford được định nghĩa hợp kiểu | Tỷ lệ vi phạm, regret, norm drift, peak working-set, latency. Chỉ chấp nhận ứng viên đạt chất lượng ít nhất bằng mốc đơn giản trong khoảng sai số đã định trước. |
| E3 — chọn đầu ra | argmax, top-k, lấy mẫu Born nếu sản phẩm cần đa dạng | Đúng hợp đồng đầu ra, hiệu năng nhiệm vụ và độ ổn định theo seed. Không gọi argmax là phép lấy mẫu. |
| E4 — vi mô | CPU state nóng/lạnh, complex128/64/real; GPU nếu có lý do profile | p50/p95/p99, phân phối theo nhiều lượt, peak state/working-set/RSS, hardware/compiler/flags, cycles/cache misses. Đích core-only: p99 <10 µs và không giảm chất lượng so với mốc E0; ghi riêng trạng thái đạt/chưa đạt. |
| E5 — tích hợp | vector từ model thật → core → Cầu Treo; mốc model → quyết định cổ điển → Cầu Treo | end-to-end p50/p95/p99, peak RAM/VRAM, mức đúng nhiệm vụ, lỗi an toàn. Không suy từ E4. |

Mỗi phép đo thời gian phải warm-up, cố định phiên bản phần cứng/phần mềm, lặp đủ để báo khoảng tin cậy hoặc độ phân tán, hiệu chỉnh overhead đồng hồ, tránh cấp phát ngoài ý muốn, nêu chế độ pin core/tần số và giữ log thô. Chạy cả mẫu “xấu” làm lộ chi phí dữ liệu/phân nhánh; không chỉ chọn mẫu thuận lợi. Các ngưỡng chất lượng cụ thể cần đặt **trước** khi chạy E0 theo bài toán, tránh chọn sau khi nhìn kết quả. Hướng dẫn tối ưu theo profile phần cứng: [Intel Optimization Reference Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel64-and-ia32-architectures-optimization.html).

## 5. Cổng quyết định tài liệu và phát triển

1. **Lý thuyết:** xuất bản đặc tả hợp kiểu cho input, mã hóa, toán tử, objective, output, invariant và trường hợp lỗi; sửa các phát biểu trong MATH_SPEC bằng phần đính chính có đánh dấu, giữ lịch sử.
2. **Khả thi thuật toán:** E0–E3 cho thấy giá trị so với mốc cổ điển trên dữ liệu held-out. Nếu không, giữ lõi quyết định đơn giản và ghi nhánh quantum-inspired là nghiên cứu chưa được hỗ trợ.
3. **Khả thi kỹ thuật:** E4 đạt mục tiêu trên phần cứng nêu tên; tách **64 KiB state** khỏi **64 KiB working-set** và công bố cái nào đạt. Nếu hụt, profile xác định nút thắt trước khi đổi kiến trúc.
4. **Giá trị sản phẩm:** E5 chứng minh độ đúng và độ trễ trong luồng thật. Chỉ cổng này mới cho phép phát biểu khả năng của VivyQu khi dùng cùng Cầu Treo/model.

Không có số đo VivyQu nào được ghi nhận trong tài liệu này. Các con số 64 KiB và 10 µs giữ vai trò mục tiêu, còn ~50 lần truy vấn Grover là kết quả lý thuyết trong mô hình bài toán khác.

## Lịch sử thay đổi

- 2026-09-27 | Vy / doc_author: lập chương trình nghiên cứu, đính chính phạm vi các tuyên bố lý thuyết, định nghĩa cổng chứng cứ và phép đo; không sửa hay xóa tài liệu gốc.
- 2026-09-27 | Vy / doc_author: làm rõ E1 về sự tương đương đầu ra của signed real và complex pha bằng 0 khi chỉ dùng `argmax |c|²`.
