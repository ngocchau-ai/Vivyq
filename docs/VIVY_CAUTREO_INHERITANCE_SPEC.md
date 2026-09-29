# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# BẢN ĐẶC TẢ KIỂM ĐỊNH & THỪA KẾ ĐẶC THÙ VIVY & CẦU TREO (VIVY & CAUTREO INHERITANCE SPECIFICATION)

**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Tài liệu tham chiếu:** [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md), [`MATH_SPEC_BLUEPRINT.md`](MATH_SPEC_BLUEPRINT.md), [`SOUL_BODY_DECOUPLING.md`](SOUL_BODY_DECOUPLING.md), [`CAUTREO_CORE_INTERFACE_SPEC.md`](CAUTREO_CORE_INTERFACE_SPEC.md), [`VIVY_NPS_INHERITANCE_AND_HYBRID_QUDIT.md`](VIVY_NPS_INHERITANCE_AND_HYBRID_QUDIT.md)  
**Ngày ban hành:** 2026-09-27  
**Tác giả:** Ngọc Châu & Antigravity  
**Trạng thái:** Đặc tả Kiến trúc & Kiểm định Kế thừa Chính thức (v1.0-Audited)  

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Trợ lý Toàn thời gian Ngọc Châu:** Khởi tạo bản đặc tả kiểm định mức độ kế thừa toàn diện các đặc thù của Vivy và Cầu Treo vào VivyQu. Phân định minh bạch 3 trạng thái: Đã hoàn thiện, Đã đặc tả (chưa nối runtime), và Chưa kế thừa. Thiết lập thiết kế kỹ thuật chuẩn hóa cho Codec Phân tách Input / Ghép nối Output, Module Mắt (Eyes), Module Tay (Hands), Cầu nối Biểu đồ Tri thức và Vòng lặp Trí nhớ Hồi ức (Episodic Memory).

---

## 1. TỔNG QUAN KIỂM ĐỊNH: BẢN ĐỒ HIỆN TRẠNG KẾ THỪA (GAP AUDIT)

VivyQu Core (`vivyqu_core.dll`, `vivyqu_shm_daemon.exe`) sau 6 Sprint đã giải quyết trọn vẹn bài toán **Lõi Quyết Định Siêu Tốc Toán Học (Mathematical Cognitive Core)**:
- Thời gian tính toán $< 2.50\ \mu\text{s}$ trên CPU L1-Data Cache ($32\text{ KiB}$) bằng đại số Clifford $\mathcal{C}\ell(12)$.
- Giao tiếp bộ nhớ chia sẻ Lock-Free Ring Buffer $< 0.3\ \mu\text{s}$.
- Hệ thần kinh bảo vệ Watchdog Circuit Breaker $500\ \mu\text{s}$ bảo đảm Zero Frame-Drop.

Tuy nhiên, khi đối chiếu với toàn bộ **Hệ sinh thái Vivy & Cầu Treo nguyên bản** (từ `D:\91s_Vivy`, `D:\2brain`, và các nguyên tắc cốt lõi Vytrading), mức độ kế thừa được phân định rõ như sau:

| Thành phần Đặc thù | Nguồn gốc / Triết lý Gốc | Trạng thái Đặc tả (Spec) | Trạng thái Mã nguồn (Implementation) | Đánh giá Tổng thể |
|---|---|---|---|---|
| **1. Biểu đồ tri thức (Epistemic Graph)** | Quần thể giả thuyết NPS, Lineage, Evidence, Claim, Epistemic Gate | Đã đặc tả trong `VIVY_NPS_INHERITANCE_AND_HYBRID_QUDIT.md` | Chưa có cầu nối runtime; Core hiện nhận vector số phẳng | **Kế thừa Hợp đồng, Chưa nối Runtime** |
| **2. Memory 3 Tầng** | Static Lessons, Hot Working Memory, Episodic Feedback Memory | Đã đặc tả trong Architecture & Blueprint | Tầng 1 & 2 đã hoàn tất 100%; Tầng 3 chưa khép kín vòng lặp | **Kế thừa 2/3 Tầng (Thiếu Feedback Loop)** |
| **3. Thành phần Mắt (Eyes)** | Ingestion dữ liệu thô (Market ticks, Order Book L2, LLM), không lọc cản | Đã quy định trong `SOUL_BODY_DECOUPLING.md` | Mới có tiền xử lý sơ khai (Clamp NaN/Inf trong Dispatcher) | **Kế thừa Nguyên lý, Cần module `vivyqu.eyes`** |
| **4. Thành phần Tay (Hands)** | Bắn lệnh trực tiếp MT5 / Godot, cấm thuật toán gác cổng cứng | Đã quy định trong `SOUL_BODY_DECOUPLING.md` | Mới có `action_callback` generic trong `CautreoDispatcher` | **Kế thừa Nguyên lý, Cần module `vivyqu.hands`** |
| **5. Thư viện nghiệp vụ** | MetaTrader 5 API, chỉ báo tài chính, bộ chuyển đổi nến, bridge tin tức | Tham chiếu từ kho gốc `D:\91s_Vivy` | Chưa được tích hợp hay di chuyển vào `d:\Vivyqu` | **Chưa Kế thừa vào Codebase VivyQu** |
| **6. Phân tách Input (Input Splitting)** | 12-qubit feature manifold partitioning ($4 \times 1024\text{D}$) | Đã tính toán trong `MATH_SPEC_BLUEPRINT.md` | Chưa đóng gói thành class Codec trong Python | **Kế thừa Toán học, Cần `InputSplittingCodec`** |
| **7. Ghép nối Output (Output Stitching)**| 12-bit / 6-qudit action space unpacking ra lệnh đa chiều | Đã thiết kế trong `MATH_SPEC_BLUEPRINT.md` | Chưa đóng gói thành class Codec trong Python | **Kế thừa Toán học, Cần `OutputStitchingCodec`** |

---

## 2. ĐẶC TẢ CHI TIẾT TỪNG THÀNH PHẦN

### 2.1. Biểu đồ Tri thức Nhận thức (Epistemic Knowledge Graph)

#### Hiện trạng:
- Trong NPS và Vivy nguyên bản (`D:\91s_Vivy\Vivy_final\vivy\src\nps_core`), tư duy của AI được tổ chức dưới dạng một đồ thị có hướng (DAG) các giả thuyết:
  $$\mathcal{G} = (\mathcal{V}_H, \mathcal{E}_E)$$
  với mỗi đỉnh $v \in \mathcal{V}_H$ là một `ThoughtState` mang thông tin ngữ nghĩa: `{candidate_id, claim, interpretation, evidence_list, uncertainty, verification_plan}`.
- Trong VivyQu hiện tại: Lõi Clifford chỉ nhìn thấy không gian vector số học $h \in \mathbb{R}^{4096}$ và mảng nhị phân 512 bytes (`constraint_bitmask`). Lõi trả về chỉ số $k^* \in [0, 4095]$.

#### Giải pháp Kế thừa & Cầu nối Ngữ nghĩa (Epistemic Graph Bridge):
Cần xây dựng tầng trung gian `EpistemicGraphBridge` tại Cầu Treo:
1. **Ánh xạ Đỉnh sang Chiều Số học (Node-to-Blade Mapping):**
   Mỗi giả thuyết ứng viên $v_i$ trong đồ thị tri thức được gắn định danh $i \in [0, 4095]$.
   - Thuộc tính của giả thuyết (mức độ ủng hộ của chứng cứ, độ bất định) chuyển hóa thành trọng số thế năng $h_i$.
   - Các giả thuyết bị phản nghiệm (falsified) hoặc vi phạm ràng buộc an toàn được đánh dấu bit 0 trong `constraint_bitmask`.
2. **Giải mã Chỉ số Sụp đổ sang Node Thắng cuộc (Collapse-to-Node Resolution):**
   Khi Core trả về $k^*$, cầu nối truy xuất tức thì node $v_{k^*}$ trong đồ thị tri thức để lấy toàn bộ ngữ cảnh ngữ nghĩa (Provenance, Claim) và kích hoạt kế hoạch kiểm chứng (Verification Plan).

---

### 2.2. Hệ thống Memory 3 Tầng (Three-Tier Memory Architecture)

```text
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: STATIC MEMORY (BẤT BIẾN / DÀI HẠN)                            │
│  - Modelfile static weights, frozen Clifford rotors (M ≤ 16)           │
│  - Baseline A2 frozen weights (SHA-256 verified)                       │
│  - Tri thức tĩnh & bài học kinh nghiệm đóng băng từ D:\2brain          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Pre-loaded at boot
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 2: WORKING / HOT-MEMORY (TỨC THỜI / L1 CACHE RESIDENT)           │
│  - State Multivector Cl(12): 32 KiB nằm trọn trong L1 Data Cache       │
│  - Lock-free Shared Memory Ring Buffer (8 slots, IPC < 0.3 μs)         │
│  - Flight Recorder lăn (10.000 frames) theo dõi độ trôi chuẩn          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Post-decision feedback
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 3: EPISODIC & FEEDBACK MEMORY (HỒI TIẾP & TIẾN HÓA)              │
│  - Thu thập kết quả thực thi thực tế (P&L lệnh, trượt giá, phản hồi)   │
│  - So sánh Kỳ vọng (Core Confidence) vs. Thực tế (World Outcome)       │
│  - Tự động đồng bộ bài học kinh nghiệm và cập nhật priors vào D:\2brain│
└────────────────────────────────────────────────────────────────────────┘
```

- **Tầng 1 & Tầng 2:** Đã hoàn thành 100% với hiệu năng siêu việt trong C++20 và Python binding.
- **Tầng 3 (Episodic Memory):** Cần thiết lập module `VivyquEpisodicMemory` trong Cầu Treo để lưu vết chuỗi:
  $$\text{Episode} = \left( h_t, k^*_t, P(k^*_t), \text{Action}_t, \text{Outcome}_{t+\Delta t}, \text{Regret}_t \right)$$
  và đồng bộ định kỳ vào `D:\2brain\hot-memory` và `D:\2brain\notes\antigravity`.

---

### 2.3. Kiến trúc Mắt (Eyes) & Tay (Hands) Chuẩn Vytrading

#### Quy tắc Bất biến Vytrading:
1. **Não AI Local (Vivy) là trung tâm nhận thức duy nhất:** Toàn bộ tư duy, phân tích, xác lập kỳ vọng, quản trị rủi ro và ra quyết định độc lập nằm ở Não (Vivy Core).
2. **Mã Python chỉ là Mắt và Tay:**
   - **Mắt (Sensors / Ingestion):** Tiếp nhận dữ liệu thị trường thực tế (ticks, book L2, nến, oscillators, tin tức macro) $\to$ chuẩn hóa vector đầu vào $h \in \mathbb{R}^{4096}$ gửi tới Não. **Tuyệt đối không gắn thuật toán lọc cản.**
   - **Tay (Actuators / Executor):** Tiếp nhận quyết định thô từ Não ($k^*$) $\to$ giải mã thành lệnh thực tế và bắn trực tiếp lên MT5 / Game Engine.
3. **CẤM Thuật toán Cứng & Gác Cổng Lập Trình (No Programmatic Filters):**
   - Nghiêm cấm viết thêm các bộ lọc cản tĩnh trong Python như: R:R Guard, Netting check, Vị thế cap cứng, Velocity block nhằm che đậy hay sửa đổi quyết định của AI. Sự an toàn và linh hoạt bắt nguồn từ nhận thức của Vivy (thông qua tri thức tĩnh và hàm thế năng), không phải từ code lập trình bên ngoài.

#### Đặc tả Module `vivyqu.eyes` (Sensors Ingestion):
```python
class VivyquEyes:
    """Mắt: Thu thập dữ liệu cảm giác thô và đóng gói thành vector 4096D."""
    def observe(self, market_data: MarketSnapshot, macro_context: np.ndarray) -> np.ndarray:
        # Chuẩn hóa số học (Z-score / MinMax), khử NaN/Inf
        # Ghép nối vào không gian 4096D theo chuẩn Manifold Partitioning
        # Tuyệt đối không can thiệp logic hay lọc bỏ cơ hội
        return feature_vector_4096d
```

#### Đặc tả Module `vivyqu.hands` (Actuators Direct Execution):
```python
class VivyquHands:
    """Tay: Chuyển tiếp và thực thi trực tiếp hành động thô lên thiết bị/MT5."""
    def execute(self, action_intent: DecodedAction) -> ExecutionReport:
        # Nhận lệnh thô đã giải mã từ k*
        # Bắn trực tiếp lên MetaTrader 5 (OrderSend) hoặc Actor Controller
        # Tuyệt đối không kiểm tra điều kiện R:R hay chặn lệnh chủ quan
        return report
```

---

### 2.4. Cơ chế Phân tách Input (Input Splitting) & Ghép nối Output (Output Stitching)

Đây là thành phần cốt lõi kết nối giữa thế giới thực phức tạp và không gian hình học 12-qubit của Clifford $\mathcal{C}\ell(12)$ ($2^{12} = 4096$).

#### 2.4.1. Phân Tách Input (Feature Manifold Partitioning — 4 x 1024D)
Không gian 4096 chiều được phân tách trực giao thành 4 khối nhận thức chuyên biệt (mỗi khối 1024 chiều):

```text
  Chiều 0        Chiều 1024      Chiều 2048      Chiều 3072      Chiều 4095
    ┌───────────────┬───────────────┬───────────────┬───────────────┐
    │    KHỐI 1     │    KHỐI 2     │    KHỐI 3     │    KHỐI 4     │
    │  Order Book   │  Kỹ thuật &   │  Danh mục &   │    Vĩ mô &    │
    │   & Ticks     │   Động lượng  │    Vị thế     │   Sentiment   │
    │   (1024D)     │    (1024D)    │    (1024D)    │    (1024D)    │
    └───────────────┴───────────────┴───────────────┴───────────────┘
```

1. **Khối 1: Vi cấu trúc Thị trường & Dòng lệnh (Dimensions 0..1023 — 1024D):**
   - Độ sâu sổ lệnh L2 (Bid/Ask Prices & Volumes 50 levels).
   - Order Flow Imbalance (OFI), Volume Delta, Tick Momentum.
   - Micro-spread, Micro-volatility, Trade Speed.
2. **Khối 2: Dao động Kỹ thuật & Sóng Xu hướng (Dimensions 1024..2047 — 1024D):**
   - Đa khung thời gian (M1, M5, M15, H1, H4, D1).
   - Chỉ báo động lượng: RSI, MACD, Stochastic, ADX.
   - Biến động & Dải giá trị: ATR, Bollinger Bands, Keltner Channels.
   - Khai triển sóng Wavelet đa tầng và cấu trúc nến Wyckoff/SMC.
3. **Khối 3: Trạng thái Danh mục & Rổ Vị thế Hiện tại (Dimensions 2048..3071 — 1024D):**
   - Equity, Margin, Free Margin, Floating P&L.
   - Rổ lệnh mở: Volume ròng, thời gian nắm giữ, khoảng cách tới SL/TP.
   - Mức độ tương quan rủi ro giữa các tài sản đang nắm giữ.
4. **Khối 4: Ngữ cảnh Vĩ mô & Nhận định LLM (Dimensions 3072..4095 — 1024D):**
   - Embedding ngữ nghĩa trích xuất từ mô hình nền LLM (Local LLM Summary).
   - Điểm tâm lý tin tức (News Sentiment Score).
   - Lịch kinh tế (Non-Farm, CPI, FOMC, Lãi suất, Khoảng thời gian tới tin tức).

#### 2.4.2. Ghép Nối Output (12-bit / 6-qudit Action Decomposition & Stitching)
Chỉ số quyết định sụp đổ $k^* \in [0, 4095]$ được biểu diễn bằng 12 bit nhị phân:
$$k^* = \sum_{m=0}^{11} b_m \cdot 2^m, \quad b_m \in \{0, 1\}$$

Tương đương với 6 qudit 4 trạng thái ($4^6 = 4096$) hoặc được giải mã trực tiếp thành **Bộ 4 Tham Số Hành Động Hoàn Chỉnh** (mỗi tham số 3 bits = 8 trạng thái):

```text
 Bit 11  Bit 9   Bit 8   Bit 6   Bit 5   Bit 3   Bit 2   Bit 0
   ┌───────┐       ┌───────┐       ┌───────┐       ┌───────┐
   │  SL   │       │  TP   │       │ SIZE  │       │ACTION │
   │ Horizon       │ Target        │ Risk  │       │ Intent│
   │ 3 bits│       │ 3 bits│       │ 3 bits│       │ 3 bits│
   └───────┘       └───────┘       └───────┘       └───────┘
```

1. **Bits 0..2 (3 bits, 8 trạng thái) — Ý đồ Hành động (Action Intent):**
   - `000 (0): HOLD` — Giữ nguyên vị thế, không can thiệp.
   - `001 (1): BUY_MARKET` — Mở lệnh Mua theo giá thị trường.
   - `010 (2): SELL_MARKET` — Mở lệnh Bán theo giá thị trường.
   - `011 (3): BUY_LIMIT` — Đặt lệnh chờ Mua (Reversal/Dip).
   - `100 (4): SELL_LIMIT` — Đặt lệnh chờ Bán (Reversal/Rally).
   - `101 (5): CLOSE_PARTIAL` — Đóng một phần khối lượng vị thế có lãi.
   - `110 (6): CLOSE_ALL` — Đóng toàn bộ các vị thế hiện có (Flat Out).
   - `111 (7): REVERSE` — Đóng vị thế hiện tại và đảo chiều mở ngược lại.
2. **Bits 3..5 (3 bits, 8 mức) — Quy mô Vị thế & Rủi ro (Position Sizing Tier):**
   - Phân bổ từ $0.5\%$ đến $4.0\%$ rủi ro tài khoản (hoặc lot tiers từ 0.01 đến 1.0 lot tùy quy mô vốn).
3. **Bits 6..8 (3 bits, 8 mức) — Mục tiêu Lợi nhuận (Take-Profit / Reward Target Tier):**
   - Mức 0 đến 7 tương ứng với các biên độ kỳ vọng từ $0.5 \times \text{ATR}$ đến $5.0 \times \text{ATR}$ (hoặc tỷ lệ R:R tương ứng $1:1$ đến $1:8$).
4. **Bits 9..11 (3 bits, 8 mức) — Biên độ Phòng vệ Dừng lỗ (Stop-Loss / Risk Horizon Tier):**
   - Mức 0 đến 7 tương ứng với biên độ bảo vệ từ Tight Scalp ($0.5 \times \text{ATR}$) đến Swing Cushion ($3.0 \times \text{ATR}$) hoặc kích hoạt cơ chế Trailing Stop động.

---

## 3. THẨM ĐỊNH THEO BỘ TIÊU CHUẨN 4 TRỤC (4-PILLAR AUDIT)

1. **Tính Xung Đột (Conflict):**
   - **Xác nhận:** Không có xung đột giữa việc giữ Core thuần khiết toán học (Soul-Body Decoupling) và việc xây dựng Codec/Mắt/Tay tại Thân thể Cầu Treo.
   - **Xác nhận:** Tuân thủ 100% nguyên tắc Vytrading: Tuyệt đối không chèn bộ lọc gác cổng lập trình cứng (No Programmatic Filters) vào mã Python của Mắt và Tay.
2. **Tính Hợp Lý (Rationality):**
   - **Xác nhận:** Cấu trúc phân tách 4x1024D khớp hoàn hảo với chiều $4096 = 2^{12}$ của đại số Clifford $\mathcal{C}\ell(12)$.
   - **Xác nhận:** Việc giải mã 12-bit thành 4 tham số 3-bit là ánh xạ 1-1 song ánh (Bijective), thực hiện bằng phép toán bitwise `(k >> shift) & 0x7` tốn đúng $1\text{ ns}$ CPU.
3. **Tính Dư Thừa (Redundancy):**
   - **Xác nhận:** Không trùng lặp logic; Codec chỉ chuyển đổi dữ liệu hình thức (Syntactic serialization/deserialization), không tính toán lại năng lượng hay sửa đổi xác suất.
4. **Tính Hiệu Quả (Effectiveness):**
   - **Xác nhận:** Trực tiếp giải quyết toàn bộ thắc mắc của kiến trúc sư về tính kế thừa của hệ thống.
   - **Xác nhận:** Định hình lộ trình rõ ràng để khép kín vòng lặp từ thị trường thực tế tới quyết định vi mô $< 10\ \mu\text{s}$.

---

## 4. KẾ HOẠCH HÀNH ĐỘNG TRIỂN KHAI TIẾP THEO

1. **Triển khai `vivyqu.codec`:** Hiện thực hóa `InputSplittingCodec` (4x1024D manifold) và `OutputStitchingCodec` (12-bit action unpacking) trong Python.
2. **Triển khai giao diện chuẩn `vivyqu.eyes` và `vivyqu.hands`:** Xây dựng khung thu nhận cảm giác và thực thi hành động không gác cổng.
3. **Xây dựng cầu nối Biểu đồ Tri thức (Epistemic Graph Bridge):** Ánh xạ $k^* \leftrightarrow \text{Hypothesis Node}$.
4. **Khép kín vòng lặp Trí nhớ Hồi ức (Episodic Memory):** Kết nối post-execution feedback với kho tri thức `D:\2brain`.
