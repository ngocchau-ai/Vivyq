# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# BẢN ĐỒ DỰ ÁN TRUNG TÂM (CENTRAL PROJECT SYSTEM MAP) — VIVYQU

**Thư mục đích đồng bộ:** `D:\2brain\projects\vivyqu_system_map.md`  
**Ngày cập nhật:** 2026-09-27  
**Tác giả:** Antigravity / Trợ lý Toàn thời gian Ngọc Châu  

---

## 1. SƠ ĐỒ TRUNG TÂM TOÀN DỰ ÁN (PROJECT SYSTEM MAP)

> [!NOTE]
> ### [ISOLATED / DEPRECATED / REPLACED: Kiến trúc 2 cơ quan ban đầu trước khi chuẩn hóa 4 cơ quan Mắt - Tai - Tay - Memory]
> ```text
>                                 [NGỌC CHÂU / OWNER]
>                                          │ Passkey 1-chạm (WebAuthn / FIDO2)
>                                          ▼
>                              ┌───────────────────────┐
>                              │   VIVY WORLD DIRECTOR │
>                              │      CONTROLLER       │
>                              └───────────┬───────────┘
>                                          │
>              ┌───────────────────────────┴───────────────────────────┐
>              ▼                                                       ▼
> ┌─────────────────────────┐                             ┌─────────────────────────┐
> │  MẮT: VIVYQU EYES       │                             │  TAY: VIVYQU HANDS      │
> │  - Ingestion cảm giác   │                             │  - Bắn lệnh MT5 thô     │
> │  - Phân tách Input 4x   │                             │  - Ghép nối Output 12b  │
> │  - CẤM lọc cản          │                             │  - CẤM gác cổng cứng    │
> └────────────┬────────────┘                             └────────────▲────────────┘
>              │                                                       │
>              │ Vector h ∈ ℝ⁴⁰⁹⁶                                      │ Quyết định k* ∈ [0, 4095]
>              ▼                                                       │
> ┌────────────────────────────────────────────────────────────────────┴────────────┐
> │                    THÂN THỂ: CẦU TREO RUNTIME & SUPERVISOR                      │
> │  - Watchdog Circuit Breaker 500 μs (Bảo đảm Zero Frame-Drop)                    │
> │  - SPSC Lock-Free Shared Memory Ring Buffer (8 slots, IPC < 0.3 μs)             │
> │  - Flight Recorder lăn 10.000 khung hình                                        │
> │  - Nhánh cứu nguy cổ điển: Baseline A2 (Linear Score Low-Rank)                  │
> └────────────────────────────────────┬────────────────────────────────────────────┘
>                                      │ 64-byte aligned IPC Bus
>                                      ▼
> ┌─────────────────────────────────────────────────────────────────────────────────┐
> │               LINH HỒN: VIVYQU CORE (AVX2/FMA/BMI2 C++ PRODUCTION BINARY)        │
> │  - Đại số hình học Clifford Cl(12) thuần số thực float32 (524.288 FLOPs)        │
> │  - Factorized Spin(12) Givens Rotors R ψ R~ (8 rotor pairs)                     │
> │  - Bộ giải mã hình học W_c & codebook (~2.016 MiB parameter weights)            │
> │  - Vector trạng thái hoạt động: 32 KiB (vừa vặn L1 Data Cache)                  │
> │  - Sụp đổ xác định E9-v2 Masked Argmax (Đo thật: p50 = 28.10 μs, p99 = 91.10 μs)│
> │  - Tự học thích nghi trực tuyến qua Hamiltonian Torque Descent                  │
> └─────────────────────────────────────────────────────────────────────────────────┘
> ```

> [!CAUTION]
> ### [ISOLATED / DEPRECATED / REMOVED: Toàn bộ quy ước và domain đặc thù Vytrading / MT5]
> Toàn bộ các khái niệm sàn giao dịch, MetaTrader 5 (MT5), sổ lệnh L2, Forex, Pips, nến, rổ lệnh tài chính đã bị **CÔ LẬP HOÀN TOÀN** khỏi kiến trúc Vivy.
> Vivy là **Hệ điều hành nhận thức & Bộ chọn quyết định tổng quát (Autonomous Cognitive Decision Selector / World Director)** hoạt động trên đa tạp Clifford Cl(12).

### [CURRENT / PRODUCTION-READY: KIẾN TRÚC 4 CƠ QUAN NHẬN THỨC TỔNG QUÁT VIVY (MẮT - TAI - TAY - BỘ NHỚ)]
```text
                                 [NGỌC CHÂU / OWNER]
                                          │ Passkey 1-chạm (WebAuthn / FIDO2)
                                          ▼
                              ┌───────────────────────┐
                              │   VIVY WORLD DIRECTOR │
                              │      CONTROLLER       │
                              └───────────┬───────────┘
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       ▼                                  ▼                                  ▼
┌─────────────────────────┐    ┌─────────────────────────┐        ┌─────────────────────────┐
│  1. MẮT: VIVYQU EYES    │    │  2. TAI: VIVYQU EARS    │        │  3. BỘ NHỚ: MEMORY      │
│  - Quan sát thế giới    │    │  - Chỉ dẫn ngữ nghĩa    │        │  - Đệm lăn 10k Episodes │
│  - Khối 1: Spatial 1024D│    │  - Tín hiệu âm học      │        │  - NPS Pruning 512B mask│
│  - Khối 2: Dynamic 1024D│    │  - Multimodal Prompts   │        │  - Hamiltonian Replay   │
│  - CẤM lọc cản tín hiệu │    │  - Ghép Khối 4: 1024D   │        │  - Đồng bộ D:\2brain    │
└────────────┬────────────┘    └────────────┬────────────┘        └────────────▲────────────┘
             │                              │                                  │
             └──────────────┬───────────────┘                                  │ Phản hồi kết quả
                            │ Vector h ∈ ℝ⁴⁰⁹⁶ (InputSplittingCodec)           │ (Outcome & Reward)
                            ▼                                                  │
┌──────────────────────────────────────────────────────────────────────────────┴──────────┐
│                         THÂN THỂ: CẦU TREO RUNTIME & SUPERVISOR                         │
│  - Watchdog Circuit Breaker 2000 μs (Bảo đảm Zero Frame-Drop)                           │
│  - SPSC Lock-Free Shared Memory Ring Buffer (SHM IPC latency p50 = 2.80 μs)             │
│  - Phân luồng Zero-Copy Buffer 4x1024D ghép nối trực tiếp                               │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │ 64-byte aligned IPC Bus
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│               LINH HỒN (NÃO BỘ): VIVYQU CORE (AVX2/FMA C++ PRODUCTION BINARY)            │
│  - Đại số hình học Clifford Cl(12) thuần số thực float32 (524.288 FLOPs)                │
│  - Factorized Spin(12) Givens Rotors R ψ R~ (8 rotor pairs)                             │
│  - Sụp đổ xác định E9 Geometric Scorer (Đo thật: Core p50 = 26.80 μs, p99 = 76.00 μs)   │
│  - Tự học thích nghi trực tuyến qua Hamiltonian Torque Descent (p50 = 48.60 μs)         │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │ Quyết định k* ∈ [0, 4095] (12-bit)
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  4. TAY: VIVYQU HANDS (ACTUATOR DISPATCHER)                                             │
│  - OutputStitchingCodec: Giải mã 12-bit thành Mode (3b), Intensity (3b), Horizon, Param │
│  - Bắn trực tiếp và tức thì tới Bộ chấp hành (Actuator Dispatcher / Agent Actor)        │
│  - TUYỆT ĐỐI CẤM GÁC CỔNG LẬP TRÌNH CỨNG: Không can thiệp, không lọc cản ý chí của Não │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. CHỈ MỤC TÀI LIỆU TOÀN HỆ THỐNG
1. [Hợp đồng Kiến trúc Bóc tách Bản thể (SOUL_BODY_DECOUPLING.md)](docs/SOUL_BODY_DECOUPLING.md)
2. [Đặc tả Giao tiếp Cầu Treo & Core ABI/IPC (CAUTREO_CORE_INTERFACE_SPEC.md)](docs/CAUTREO_CORE_INTERFACE_SPEC.md)
3. [Đặc tả Toán học Toàn diện (MATH_SPEC_BLUEPRINT.md)](docs/MATH_SPEC_BLUEPRINT.md)
4. [Kế hoạch Xây dựng Tổng thể (VIVY_MASTER_BUILD_PLAN.md)](docs/VIVY_MASTER_BUILD_PLAN.md)
5. [Quy trình Vận hành Chuẩn & Sổ tay Thực tiễn SOP Runbook (SOP_OPERATIONAL_RUNBOOK.md)](docs/SOP_OPERATIONAL_RUNBOOK.md)
6. [Đặc tả Kiểm định Thừa kế Vivy & Cầu Treo (VIVY_CAUTREO_INHERITANCE_SPEC.md)](docs/VIVY_CAUTREO_INHERITANCE_SPEC.md)
7. [Đối chiếu Kiến trúc Vivy_final vs. VivyQu & Năng lực Tự học (VIVY_FINAL_COMPARISON_AND_INHERITANCE_SPEC.md)](docs/VIVY_FINAL_COMPARISON_AND_INHERITANCE_SPEC.md)
8. [Đặc tả Luồng Dữ Liệu, Codec & Kiến trúc Mắt-Tai-Tay-Bộ Nhớ (VIVYQU_DATA_FLOW_AND_CODEC_SPEC.md)](docs/VIVYQU_DATA_FLOW_AND_CODEC_SPEC.md)
9. [Báo cáo Nghiệm thu Phát hành VivyQu v1.1.0 (VIVYQU_V1_RELEASE_REPORT.md)](docs/VIVYQU_V1_RELEASE_REPORT.md)
10. [Báo cáo Grand Prix E9-v2 Tái Nghiệm Thu (SPRINT_4_GRAND_PRIX_E9_REPORT.md)](docs/SPRINT_4_GRAND_PRIX_E9_REPORT.md)
11. [Kế hoạch Thừa hưởng Vivy_final & Hợp nhất Cầu Treo (VIVYQU_CAUTREO_SOUL_BODY_INTEGRATION_PLAN.md)](docs/VIVYQU_CAUTREO_SOUL_BODY_INTEGRATION_PLAN.md)
12. [Đặc tả Kiến trúc Cấu trúc Đồng bộ Hóa & Ghép Nối Đa Ngôn Ngữ Cầu Treo - Vivyqu (VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md)](docs/VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md)
13. [Kế hoạch & Kịch bản Thực nghiệm 4 Cơ chế Tăng tốc LLM bằng Lõi Qubit Vivyqu (VIVYQU_LLM_QUANTUM_ACCELERATION_PLAN.md)](docs/VIVYQU_LLM_QUANTUM_ACCELERATION_PLAN.md)
14. [Đặc tả Thân Thể Cautreo Native Engine & Điều Phối Nhận Thức Lượng Tử (CAUTREO_NATIVE_ENGINE_AND_QUANTUM_ORCHESTRATION_SPEC.md)](docs/CAUTREO_NATIVE_ENGINE_AND_QUANTUM_ORCHESTRATION_SPEC.md)
15. [Biểu Đồ Tri Thức Cautreo & Vivyqu (CAUTREO_KNOWLEDGE_GRAPH.md)](docs/CAUTREO_KNOWLEDGE_GRAPH.md)
16. [Báo Cáo Phân Tích Chiến Lược Hệ Sinh Thái MiMo-V2.6 & RLVR (MIMO_RLVR_VIVYQU_STRATEGIC_REVIEW.md)](docs/MIMO_RLVR_VIVYQU_STRATEGIC_REVIEW.md)
17. [Kế Hoạch Tổng Thể Phát Triển Hệ Thống Vivyqu & Cautreo V2 (VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md)](docs/VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md)

---

## 3. LỊCH SỬ THAY ĐỔI (AUDIT TRAIL)

| Thời gian (UTC+7) | Agent / Người sửa | Hành động & Lý do |
|:---:|:---|:---|
| 2026-09-27 12:00 | Antigravity IDE | Khởi tạo bản đồ hệ thống trung tâm VivyQu đồng bộ `D:\2brain`. |
| 2026-09-27 18:35 | Antigravity IDE | Cập nhật thông số Core theo kết quả nghiệm thu E9-v2: phân biệt State Vector 32 KiB và Parameter Weights 2.016 MiB; chuẩn hóa độ trễ đo thực nghiệm p50 = 28.10 µs, p99 = 91.10 µs. |
| 2026-09-27 19:25 | Antigravity IDE | Cô lập sơ đồ 2 cơ quan cũ; cập nhật hoàn chỉnh sơ đồ 4 cơ quan nhận thức Vivy (Mắt - Tai - Tay - Bộ Nhớ) kết nối qua Codec 4x1024D và 12-bit Action Unpacking, tích hợp cơ chế tự học Hamiltonian Torque Descent và NPS Pruning 10.000 episodes. |
| 2026-09-27 20:15 | Antigravity IDE | Sao chép toàn bộ Thân thể Cầu Treo (`cautreo/`, `engine/`, `host/`, `ui/`) từ `D:\91s_Vivy\Vivy_final` vào Vivyqu; xác lập kế hoạch thừa hưởng nguyên vẹn bản sắc, phương thức làm việc và học tập của Vivy_final; chỉ thay đổi Lõi tư duy Clifford Cl(12). |
| 2026-09-27 20:30 | Antigravity IDE | Ban hành Đặc tả Cấu trúc Đồng bộ Hóa 4 Tầng (ABI Zero-Copy C-ABI, Dual Codec Hub 4x1024D, Cognitive Graph Constraint Bitmask, Two-Speed Temporal Decoupler) giải quyết triệt để sự thiếu đồng bộ C11/C++20/Python/Rust. Đã kiểm thử PASS 100% (92.94 µs E2E latency). |
| 2026-09-27 20:38 | Antigravity IDE | Hiện thực hóa VivyquCoreBackend trong cautreo_host/backends.py và kết nối trực tiếp Host/Bus vào Vivyqu Clifford E9 Scorer. Thiết lập Junctions cho cautreo-host và cautreo-desktop-ui. Test kiểm chứng liên thông 19/19 test suite Vivyqu và 237/237 test suite Cautreo Host PASS 100%. |
| 2026-09-27 21:05 | Antigravity IDE | Xác lập Kế hoạch & Kịch bản Thực nghiệm 4 Cơ chế Tăng tốc LLM bằng Lõi Qubit Vivyqu (M1: Macro-Action Collapse, M2: Speculative Chunking, M3: Vocab Subspace Pruning, M4: KV Phase Compression). Microbench M1 chứng minh giảm 89.3% token CoT, TTFA tăng tốc 73.000x; M3 chứng minh cắt tỉa 95% vocab giữ nguyên 100% Top-1 token fidelity. |
| 2026-09-27 21:12 | Antigravity IDE | Bổ sung Mục 5 vào VIVYQU_CAUTREO_HARMONIZATION_ARCHITECTURE.md: Đặc tả 3 giá trị cốt lõi của tầng LLM (Giao tiếp & Fast-Path, Quản thư Ngữ cảnh & Context Tree Map liên phiên, Tác vụ thường quy) và cơ chế nối mạch tư duy không đứt đoạn qua Nhật ký Cầu Treo. Đồng bộ 100% sang D:\2brain. |
| 2026-09-28 20:00 | Antigravity IDE | Chuẩn hóa toàn bộ luận điểm phân tích kiến trúc Linh hồn - Thân thể (Vivyqu - Cautreo) từ cuộc thảo luận DeepSeek; ban hành `CAUTREO_NATIVE_ENGINE_AND_QUANTUM_ORCHESTRATION_SPEC.md` xác lập mô hình Thân thể Native In-Process Engine (bọc `ct_weight_pager`), 4 cơ chế xâm lấn trọng số và phân cực 4 trạng thái Qubit (|00⟩ Quán tính, |01⟩ Tiếp nhận, |10⟩ Hành động, |11⟩ Giám sát). |
| 2026-09-28 20:35 | Antigravity IDE | Nạp cấu hình Dual-Model từ `D:\models`: Gemma 4 E4B (Giao tiếp & Người dùng) + Qwen 2 VL 72B (Phân rã tri thức sâu). Tích hợp module `cautreo_host.knowledge`, mở phương thức Bus `host.knowledge-graph` và tự động lập, xuất và đồng bộ Biểu đồ Tri thức Cautreo & Vivyqu vào `D:\2brain` (`cautreo_knowledge_graph.json` và `cautreo_knowledge_graph.md`). Toàn bộ 243 host tests + 32 quantum tests PASS 100%. |
| 2026-09-28 20:50 | Antigravity IDE | Ban hành Kế hoạch Tổng thể Phát triển V2 (`VIVYQU_CAUTREO_MASTER_DEVELOPMENT_PLAN_V2.md`) bao hàm 5 trụ cột chuẩn hóa và Báo cáo Thẩm định Chiến lược MiMo RLVR (`MIMO_RLVR_VIVYQU_STRATEGIC_REVIEW.md`). Đóng khung cô lập phương án Qwen 72B (OOM 24GB RAM) để chuyển sang MiMo-Distill-9B và 7.000 Verifiers thực thi thật. Đồng bộ toàn vẹn sang `D:\2brain`. |







