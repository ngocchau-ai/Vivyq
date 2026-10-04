> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# DESIGN — Kernel C++ cho ACC-Q (bước 3, ADR 2026-10-04)

**Trạng thái:** `[ĐÃ DUYỆT — chủ dự án 2026-10-04 07:09]` · **Cấp độ:** `[PROTOTYPE]` · Liên quan: spec ACC §8.13/§8.14, ADR piggyback (runtime C/C++).

## 1. Mục tiêu & phạm vi
Cung cấp các kernel **suy luận/giải mã/sinh nhãn** bằng C++ để: (a) sinh nhãn exact ACC-8/12 (Python không đủ nhanh cho 4¹² = 16.7 triệu ứng viên × hàng nghìn instance); (b) chạy forward + ra quyết định của hướng A (statevector) và B (MPS) trong ngân sách độ trễ; (c) đối chứng cổ điển (giải mã factor).
**Không thuộc phạm vi bước này:** huấn luyện arm A/B (làm ở Python/NumPy, gọi kernel khi cần), tích hợp vào Core DLL (Core ABI giữ nguyên).

## 2. Kiến trúc
- Thư viện riêng `vivyqu_accq` (`include/vivyqu/accq.h`, `src/accq/*.cpp`), build `scripts/build_accq.ps1` → `build/bin/vivyqu_accq.dll` + `libvivyqu_accq.a`. **Không** sửa `vivyqu_core.dll`.
- C-ABI thuần (`extern "C"`), mọi hàm trả mã lỗi `int32` (0 = OK; 1 = tham số sai/null; 2 = vượt giới hạn kích thước; 3 = NaN/Inf; 4 = cấp phát thất bại). Không ném exception qua biên ABI.
- Mã hóa ứng viên giống `scripts/acc/common.py`: index = Σ cᵢ·4ⁱ, site i là chữ số base-4 thứ i.
- Số học: complex128/float64 ở bản đầu để kiểm chứng đúng trước. `[HIỆU NĂNG — CHƯA TỐI ƯU]` complex64/SIMD là backlog sau khi có cổng đúng.

## 3. Kernel & cổng kiểm chứng (mỗi kernel phải qua cổng trước khi sang kernel sau)
| ID | Kernel | API chính | Cổng đúng (bắt buộc) | Đo hiệu năng (báo cáo) |
|---|---|---|---|---|
| **K1** | Vét cạn năng lượng cặp: E(s) = Σ uᵢ(sᵢ) + Σ_{i<j} Pᵢⱼ(sᵢ,sⱼ), mask cấm theo (site, trạng thái), n ≤ 13 | `accq_pairwise_bruteforce(n, unary[n·4], pair[n·n·16], forbid[n·4] hoặc NULL, tol, &best_idx, &best_E, &n_ground, energies_out hoặc NULL)` | n=6: khớp `acc1.cost_all`/`acc2.energy_all` trên 200 instance mỗi bài, \|ΔE\| ≤ 1e-9, argmin trùng (tie-break index nhỏ nhất), số ground state trùng. n=8: khớp tham chiếu NumPy vectorized | Thời gian n = 8, 10, 12 |
| **K2** | Statevector qudit-4 (hướng A) | `accq_sv_*`: init \|0…0⟩, áp cổng 1-qudit (4×4) và 2-qudit (16×16) phức, xác suất Born, top-K | Chuẩn bảo toàn ≤ 1e-12 với cổng unita ngẫu nhiên; khớp tham chiếu NumPy (kron dày) n = 3, 4 tới 1e-12 | Một lớp (n cổng 1-qudit + n−1 cổng 2-qudit) ở n = 8, 10 |
| **K3** | MPS Born machine (hướng B) | `accq_mps_*`: biên độ ψ(s), chuẩn hóa, **lấy mẫu Born chính xác** (tuần tự có điều kiện với môi trường phải), log P(s) | Biên độ khớp contraction dày n ≤ 6 tới 1e-12; tổng P = 1 ± 1e-12; phân phối mẫu: khoảng cách TV < 0.01 với 200 000 mẫu (n = 4, χ = 4) | Lấy K = 8 mẫu ở n = 24, χ ∈ {8, 16} |
| **K4** | Giải mã factor (đối chứng cổ điển) | `accq_chain_viterbi` (exact cho tương tác chuỗi i–i+1), `accq_pairwise_beam` (beam B, tổng quát) | Viterbi = K1 trên 100% instance chuỗi n ≤ 8; beam: chỉ báo cáo tỷ lệ đạt tối ưu so với K1 (không phải cổng) | n = 12, 24 |

Kiểm thử: `tests/test_accq_kernels.py` (pytest + ctypes, tham chiếu NumPy/`scripts/acc`), thêm kiểm tham số sai (null, n ngoài phạm vi, NaN) phải trả đúng mã lỗi.

## 4. Rủi ro (Devil's Advocate)
| Rủi ro | Giảm thiểu |
|---|---|
| Kernel đúng ở n nhỏ nhưng sai ở n lớn (tràn index, thứ tự duyệt) | index `uint64`; K1 kiểm thêm n=8 với tham chiếu NumPy; tie-break ghi rõ |
| Lấy mẫu MPS sai phân phối nhưng biên độ đúng | Cổng TV distance riêng cho sampling |
| Tham chiếu NumPy và kernel cùng sai một kiểu | K1 đối chiếu với verifier thuần Python đã có (`verify_reference`/`energy_reference`) trên mẫu ngẫu nhiên |
| Statevector n=12 (128 MiB complex64 / 256 MiB complex128) làm chậm test | Test đúng chỉ ở n ≤ 4; n lớn chỉ bench |

## Lịch sử thay đổi
- 2026-10-04 07:12 | Antigravity (Claude Opus 5.5) | Tạo mới thiết kế kernel K1–K4 + cổng kiểm chứng, theo duyệt bước 3.
