# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# BÓC TÁCH BẢN THỂ: VIVYQU CORE (LINH HỒN) VS. CẦU TREO (THÂN THỂ)
**Dự án:** Vivyqu  
**Tác giả:** Ngọc Châu & Antigravity  
**Ngày lập:** 2026-09-26  

---

## 1. NGUYÊN TẮC PHÂN TÁCH SINH HỌC
Để Vivyqu không bao giờ bị lỗi thời, cồng kềnh hay dính chặt vào một nền tảng công nghệ đơn lẻ, toàn bộ hệ thống tuân thủ nguyên tắc **Phân tách Bản thể (Soul-Body Decoupling)**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   VIVYQU CORE (LINH HỒN - THE SOUL)                    │
│  - Không gian Hilbert 12 Qubit / 6 Qudit 4 trạng thái (|Ψ⟩ ∈ ℂ⁴⁰⁹⁶)    │
│  - Đại số hình học Clifford (Geometric Rotors & Interference)          │
│  - Động lực học hạ thế năng Hamiltonian (Minimizing Energy Surface)    │
│  - Thuần khiết toán học, phi I/O, không gọi file, không truy cập mạng  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ State Tensor Bus (64 KB Lock-free IPC)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    CẦU TREO - CAUTREO (THÂN THỂ - THE BODY)            │
│  - Phần cứng, Bộ nhớ VRAM, CUDA / Tensor Cores / LibTorch C++          │
│  - Mắt (Sensors / Ingestion): Lắng nghe môi trường, chuẩn hóa vector   │
│  - Tay (Actuators / Dispatcher): Gọi Engine (Godot/Vulkan), N-Model    │
│  - Hệ thần kinh tự vệ (Watchdog, SVD Truncation, State Snapshot)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. NHỮNG BỨC TƯỜNG LỬA BẮT BUỘC (ARCHITECTURAL FIREWALLS)
1. **Tường lửa Không I/O trong Core:**
   - Vivyqu Core tuyệt đối không chứa các thư viện gọi HTTP, đọc ghi tệp đĩa, hoặc mã driver đồ họa.
   - Core chỉ nhận vào: Vector trạng thái và Ma trận thế năng; Core xuất ra: Trạng thái đo lường sụp đổ $k^*$ hoặc ma trận mật độ $\rho$.
2. **Quy tắc Cấm Gác Cổng (No Gatekeeping in Cautreo):**
   - Thân thể Cầu Treo chịu trách nhiệm gồng mình tính toán và thực thi hành động, tuyệt đối không được dùng thuật toán `if-else` cứng để sửa đổi hoặc lọc chặn quyết định của Vivyqu Core.
   - **[ISOLATED / REPLACED — 2026-09-27]** Cầu Treo được từ chối thực thi khi đầu ra sai hợp đồng, vi phạm ràng buộc an toàn hoặc không thể thực thi và phải trả lý do rõ ràng. Cầu Treo không được âm thầm xếp hạng lại hay viết lại ngữ nghĩa quyết định của Core. Thẩm quyền quyết định ngữ nghĩa giữa hai bên vẫn là câu hỏi mở tại `ARCHITECTURE_SPEC.md`.
3. **Quản trị Tài nguyên Phần cứng Cục bộ (Edge Resource Constraint):**
   - Cầu Treo tự động kích hoạt cơ chế nén SVD khi độ rối vượt ngưỡng nhằm đảm bảo Vivyqu vận hành mượt mà trên PC 16GB RAM.

## LỊCH SỬ THAY ĐỔI (CHANGELOG)
- **2026-09-27 | Vy / doc_author:** Cô lập và làm rõ điều khoản Cấm Gác Cổng: quyền từ chối thực thi sai hợp đồng hoặc không an toàn phải có lý do; giữ nguyên câu gốc.
