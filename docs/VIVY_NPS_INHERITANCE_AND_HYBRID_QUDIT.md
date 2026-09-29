# VivyQu: kế thừa Vivy/NPS và giả thuyết qudit lai

**Ngày:** 2026-09-27. **Trạng thái:** đối chiếu mã và đề xuất thực nghiệm; chưa có kết quả VivyQu. Tài liệu này bổ sung [hợp đồng kiến trúc](ARCHITECTURE_SPEC.md), [phác thảo toán](MATH_SPEC_BLUEPRINT.md) và [kế hoạch thực nghiệm](RESEARCH_AND_DEVELOPMENT_PLAN.md), không thay thế chúng.

## 1. Ba lớp cần phân biệt

1. **NPS gốc là lớp điều khiển ngữ nghĩa:** trạng thái của *giả thuyết* có claim, evidence, phép thử, vòng đời và người thực thi. Tài liệu lịch sử còn nói rõ bản sắc NPS không phụ thuộc thuật ngữ lượng tử (`D:\2brain\projects\projects-nps-core\nps-core-codex-context_ARCHITECTURE.md:126-168`), và đặt `N_h ≥ N_v ≥ N_e`, thought khác executor (`:269-296`). Đây là nguồn ý tưởng, không là bằng chứng runtime hiện tại.
2. **Vivy hiện có hai dạng liên quan nhưng khác nghĩa:** `QuantumState` giữ vector phức, norm, xác suất và phép đo (`D:\91s_Vivy\Vivy_final\vivy\core\state.py:19-96,149-164`); `ThoughtState` mô tả interpretation, hypothesis, evidence, verification plan có validation (`D:\91s_Vivy\Vivy_final\vivy\src\nps_core\hypothesis_population\thought_state.py:156-274,352-368`). Tên “quantum” ở mã không chứng minh lợi thế lượng tử hoặc năng lực đa phương thức.
3. **VivyQu được đề xuất là lớp tính số có biên rõ:** nhận đặc trưng/ứng viên đã chuẩn bị, biến đổi và xếp hạng trạng thái số, trả top-k/điểm và lý do lỗi. Một cầu nối có schema ánh xạ `candidate_id ↔ basis/block` nối nó với thought/experiment/evidence. Không biến biên độ số thành claim hay chứng cứ ngữ nghĩa. Cầu Treo giữ I/O và thực thi theo [ranh giới Core–Cầu Treo](SOUL_BODY_DECOUPLING.md).

## 2. Có thể kế thừa gì

| Nguồn mã đã thấy | Kế thừa vào VivyQu | Giới hạn chứng cứ |
|---|---|---|
| Vivy `core/state.py:39-96,149-164,200-215` | Kiểm tra norm, xác suất, lấy mẫu và phép biến đổi vector làm **reference** toán học. | API Python/NumPy có cấp phát và phép `gate @ vector`; chưa là lõi 64 KiB/<10 µs. `argmax` khác lấy mẫu Born. |
| Vivy `src/nps_core/hypothesis_population/lifecycle.py:274,396,437,490,577`; `src/nps_core/adaptive_n/controller.py:18-52` | Kế thừa trực tiếp mẫu `PopulationSnapshot`, create/branch/merge/prune, chọn `N_h` và phát hiện trùng lặp cho quần thể giả thuyết **ngữ nghĩa**. | `tests/integration/test_thought_lifecycle_end_to_end.py:155-201` có test nguồn cho vòng đời và lineage; chưa chạy test trong lượt đối chiếu này. Chưa chứng minh các hàm này thích hợp làm toán tử qudit số. |
| Vivy `orchestrator/epistemic_gate.py:102-175`, `orchestrator/model_router.py:175-197` | Mẫu quyết định theo bất định, consent và điều kiện chứng cứ trước khi gọi model chuyên gia. | Confidence suy từ norm ở mã gate chưa chứng minh calibration; không sao chép trực tiếp làm thước đo VivyQu. |
| Vivy `integration/evidence.py:10-27`, `integration/task_state.py:15-43` | Hợp đồng ghi claim, nguồn, quan sát, trạng thái nhiệm vụ để kiểm tra kết quả ứng viên. | `valid_for_promotion()` kiểm tra trường bắt buộc; riêng nó chưa chứng minh claim đúng. |
| NPS runtime `D:\91s_Vivy\projects\91sh\src\thought-state\index.js:24-92` và `orchestrator\index.js:180-210,285-301` | Giữ quần thể giả thuyết, frontier bất định, thí nghiệm và kiểm chứng trước cập nhật trạng thái. | Đây là điều phối ngữ nghĩa JavaScript; không phải simulator statevector. |
| NPS runtime `experiment\index.js:52-61`, `evidence\index.js:52-82` | Dùng baseline chi phí/lợi thông tin và provenance khi so sánh phương án. | Hàm rank là heuristic; independence score là heuristic, không phải phép đo độc lập thống kê. |

**Điểm chung kiến trúc:** giữ nhiều ứng viên, lọc qua ràng buộc/chứng cứ, phân bổ công việc có giới hạn, tách quyết định khỏi executor. **Điểm khác:** NPS chọn *giả thuyết có nghĩa*; VivyQu thử chọn *trạng thái/ứng viên số*. Cầu nối phải lưu identity, phiên bản encoder, objective, constraints, provenance, không chỉ truyền một vector không tên.

## 3. Giới hạn 16 GiB và ý nghĩa qudit lai

Statevector dày của `n` qubit có `2^n` biên độ. Với 30 qubit: `2^30 × 8 byte = 8 GiB` (`complex64`), hoặc `2^30 × 16 byte = 16 GiB` (`complex128`). Máy **16 GiB RAM tổng** không đủ thực tế cho trường hợp thứ hai vì hệ điều hành, model, toán tử và scratch cũng chiếm RAM; 8 GiB chỉ là dữ liệu trạng thái, chưa chứng minh một phép mô phỏng hữu ích chạy được. Mỗi qubit tiếp theo nhân đôi dung lượng. Tài liệu [NVIDIA cuStateVec](https://docs.nvidia.com/cuda/cuquantum/26.01.0/custatevec/overview/statevector-algorithms.html) cũng mô tả tăng trưởng mũ và phụ thuộc bộ nhớ thiết bị.

Với qudit hỗn hợp kích thước `d₁,…,dₘ`, số biên độ `D = ∏ᵢ dᵢ`, RAM trạng thái dày `D × b` byte (`b=8/16` cho complex64/128). Gọi kiến trúc “lai” chỉ có nghĩa khi nêu rõ phần nào là qudit/statevector, phần nào là thuật toán cổ điển và cơ chế kết nối. Qudit lớn **không tự nén** thông tin: cùng `D` thì cùng RAM; `12` qubit cho `4096` biên độ, tương đương một qudit `4096` chiều. Với 4096 biên độ, complex128 là 64 KiB *chỉ riêng state* như [hợp đồng](ARCHITECTURE_SPEC.md) đã nêu.

Các nhánh cần thử theo thứ tự chi phí: (a) score/quét cổ điển, (b) block factor hoặc toán tử thưa áp dụng tại chỗ, (c) statevector nhỏ, (d) MPS/tensor network nếu bài toán có cấu trúc tương quan thấp và sai số xấp xỉ chấp nhận được. MPS có thể tiết kiệm khi mức rối bị chặn; bond dimension tăng có thể làm lợi thế biến mất ([Vidal](https://arxiv.org/abs/quant-ph/0301063)). Sparse chỉ tiết kiệm nếu số trạng thái khác 0 duy trì nhỏ qua toán tử; mất tính thưa thì quay về chi phí dày. “Quantum-inspired” vẫn chạy trên máy cổ điển và phải so với thuật toán cổ điển mạnh; [Tang](https://arxiv.org/abs/1807.04271) là ví dụ nghiên cứu có so sánh hình thức, không là bằng chứng tốc độ cho VivyQu.

## 4. Đích sản phẩm ngoài sinh văn bản

Không có phép “phân rã LLM theo qubit” chung nào biến một lần suy luận thành nhiều đáp án đúng hoặc tăng tốc `×N`. Encoder/vision/LLM vẫn chịu chi phí tạo đặc trưng; statevector cổ điển phải đọc, biến đổi và đánh giá dữ liệu. Hướng khả thi là **đặt bài toán có cấu trúc sau encoder**:

| Miền | Đầu vào và ứng viên có nghĩa | Chỉ tiêu chất lượng trước tốc độ |
|---|---|---|
| Ảnh | đặc trưng ảnh + các crop/segment/nhãn/đường dựng hữu hạn | mIoU, recall@k hoặc lỗi tái tạo; so với model/heuristic xếp hạng trực tiếp. |
| Sắp xếp/điều hướng | tập lịch/đường đi hợp lệ, chi phí và ràng buộc | feasibility, objective gap/regret, thời gian tìm lời giải. |
| Vật lý | trạng thái rời rạc của mô hình **được định nghĩa**, điều kiện biên và bộ giải chuẩn | sai số so với solver đã kiểm chứng, bảo toàn đại lượng, thời gian tổng. |
| Hóa học | bài toán hẹp: conformer/ứng viên phản ứng hoặc Hamiltonian nhỏ có dữ liệu chuẩn | sai số năng lượng/cấu trúc và kiểm chứng hóa học; không suy từ mô phỏng qudit rằng phản ứng thật đã đúng. |

Một lượt có thể trả top-k ứng viên để **tăng độ bao phủ**, nhưng phải đo precision/recall, chi phí verifier và độ trễ tổng. Không coi top-k là nhiều “thế giới” đã tính song song miễn phí.

## 5. Kiến trúc tối thiểu và phép thử quyết định

```text
Nguồn ảnh/bài toán/model → encoder & candidate builder (Cầu Treo)
    → {candidate_id, feature, objective, hard constraints, provenance}
    → VivyQu Core: score baseline | state/block/qudit transform → top-k + score + errors
    → verifier/experiment/evidence NPS/Vivy → quyết định có thẩm quyền → executor
```

**P0:** Chọn *một* tác vụ có dữ liệu held-out, oracle/solver tham chiếu và ≥2 baseline (quét/chọn cổ điển; model trực tiếp). Cố định seed, splits, tiêu chí lỗi và ngưỡng chất lượng trước khi nhìn kết quả. **P1:** so signed-real score, statevector nhỏ, block/sparse; chỉ thêm MPS nếu đo thấy cấu trúc phù hợp. **P2:** đo `p50/p95/p99` core-only và end-to-end, peak RAM/RSS, bytes state/scratch, chất lượng/regret/vi phạm ràng buộc; báo `speedup = T_baseline / T_candidate` tại cùng chất lượng. **P3:** giữ nhánh qudit chỉ nếu đạt chất lượng ít nhất bằng baseline, độ trễ tổng giảm có lặp lại, và fit trong RAM trên máy đích. `64 KiB state`, `p99 <10 µs core`, và tăng tốc `×N` vẫn là **đích/giả thuyết**, không là cổng đạt sẵn.

## Lịch sử thay đổi

- 2026-09-27: Lập đối chiếu mã Vivy/NPS, toán bộ nhớ qubit/qudit và chương trình thử nghiệm tối thiểu. Chưa sửa mã nguồn ngoài `D:\Vivyqu` hay ghi nhận kết quả VivyQu.
- 2026-09-27: Bổ sung điểm kế thừa trực tiếp từ vòng đời quần thể giả thuyết và adaptive N của Vivy; phân biệt test nguồn với test đã chạy.
