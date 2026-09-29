# REVIEW: ĐỒNG BỘ & XUNG ĐỘT TOÀN DỰ ÁN VIVYQU / CAUTREO

**Ngày:** 2026-09-29  
**Phạm vi:** toàn cây `D:\Vivyqu` (ABI C++/Python, docs vs code, host/UI/engine, bản sao tri thức)  
**Đối chiếu bắt buộc:** `chatGPT_review.md` (27/09) · `docs/CAUTREO_AUXILIARY_CAPABILITY_AUDIT_2026-09-29.md`  
**Thang bằng chứng:** `Thiết kế ≠ Mã ≠ Harness ≠ Native đã chạy ≠ Sản phẩm được nghiệm thu`

---

## 0. Kết luận điều hành

Dự án có implementation thật (C++ Core, DLL, IPC, host/plugin, codec), nhưng **bằng chứng đang bị trộn tầng**:

- Số latency “đo thật” trong Grand Prix E9 thực ra là **hardcode fallback**.
- Claim `PRODUCTION-READY` cùng tồn tại với `RESEARCH PROTOTYPE` và `DRAFT — chưa nghiệm thu`.
- Hot path Python **copy qua `memmove`**, không zero-copy như mô tả.
- Cautreo bị tài liệu đẩy sang “nhận thức kép”, vượt vai trò thân thể/tầng phụ trợ (audit 29/09 P0).

**Mức sẵn sàng trung thực:** `prototype kiến trúc có thành phần thật` — đủ mở G0–G3 theo audit 29/09, **chưa đủ** gắn production-verified.

---

## 1. Đối chiếu hai review ChatGPT

| Nguồn | P0 cốt lõi | Khớp với audit nội bộ |
|---|---|---|
| `chatGPT_review.md` §5.4, §7–9 | Hardcode latency E9; decision-function ≠ collapse; 32 KiB ≠ working set | Có — `test_grand_prix_e9.py` vẫn hardcode 28.50/38.10/79.10, `ROOT_DIR` NameError bị nuốt |
| `chatGPT_review.md` §5.3 | E9 scoring ≠ `collapse.cpp` argmax state² | Có — 3 đường quyết định còn sống; Python default `mode="argmax"` |
| `CAUTREO_AUXILIARY…29/09` §3 P0 | `memmove` không zero-copy; thiếu dtype/size contract | Có — `cautreo_harmonizer.py` copy `CL12_DIMENSION*8` |
| `CAUTREO_AUXILIARY…29/09` §3 P0 | Fallback `is_valid` đọc frame cũ | Có — decode dùng `_out_frame.error_code` sau watchdog |
| `CAUTREO_AUXILIARY…29/09` §2–3 | “Nhận thức kép” mâu thuẫn một cognition owner | Có — docs Cautreo nhận reward/policy; host/UI overclaim |
| `CAUTREO_AUXILIARY…29/09` §10 P0 | Sửa boundary **trước** experiment native | Điều chỉnh thứ tự fix: boundary + evidence honesty trước G5–G7 |

---

## 2. CRITICAL

### C1 — Latency E9 là số hardcode, không phải measurement

**[CRITICAL] (confidence 10/10)** `tests/test_grand_prix_e9.py:318-334`

```
p50_core_lat_c = 28.50
p95_core_lat_c = 38.10
p99_core_lat_c = 79.10
try:
    ...
    bin_w = os.path.join(ROOT_DIR, "data", "e9_weights.bin")  # ROOT_DIR undefined
    ...
except Exception as e:
    pass
```

JSON vẫn ghi `"latency_core_cpp_source": "Empirical measurement on production C++ DLL"`.  
Raw `results/grand_prix_e9/grand_prix_e9_results.json` khớp đúng defaults.  
**Impact:** Gate G2 / PRODUCTION-READY dựa trên metadata, không có raw sample + binary hash.

### C2 — Boundary ABI không an toàn

**[CRITICAL] (confidence 9/10)** `src/core/geometric_scorer.cpp:405-415`  
Custom rotor path thiếu guard `pi >= 12` (có ở `:77`) → `plane_i/j` uint8 tới 255 tạo index tới ~36863, ghi ngoài `h_buf[4096]`.

**[HIGH→P0 theo 29/09] (confidence 9/10)** `python/vivyqu/cautreo_harmonizer.py:267`  
`memmove(..., CL12_DIMENSION*8)` không ép `float64` + contiguous → overread 16 KB nếu input `float32`.

**[P0 theo 29/09] (confidence 9/10)** `python/vivyqu/cautreo_harmonizer.py:297`  
Sau watchdog fallback vẫn `is_valid=(self._out_frame.error_code == 0)` — đọc frame Core cũ/thất bại.

### C3 — Trạng thái / quyền sở hữu nhận thức trộn tầng

**[CRITICAL] (confidence 10/10)**

- `README.md:13` `[PRODUCTION-READY — E9-v2 C++ CORE VERIFIED]`
- `README.md:82` `[RESEARCH PROTOTYPE / BENCHMARK PROMISING — E9-v2 PENDING]`
- `docs/REVIEW_AND_RESEARCH_DIRECTION_2026-09-28.md:3` `DRAFT — chưa nghiệm thu sản phẩm`

Audit 29/09 P0: “nhận thức kép” Gemma+MiMo / Cautreo reward owner mâu thuẫn một cognition owner.  
**Impact:** agent kế thừa đọc status khác nhau ra quyết định khác nhau; Cautreo bị hiểu nhầm là não thứ hai.

---

## 3. HIGH (đồng bộ có hệ thống)

| # | Vấn đề | Vị trí |
|---|--------|--------|
| H1 | Version 4 nguồn: `1.0.0` / `1.3.0` / `v1.1.0` / `v1.0` | `pyproject.toml`, `__init__.py`, `c_api.cpp:94`, README |
| H2 | CMake thiếu `c_api.cpp` + `shm_daemon`; build thật là `build_core.ps1` | `CMakeLists.txt:38` |
| H3 | 3 đường quyết định; Python default `argmax`; daemon force-E9 không kích | `c_api.cpp`, `engine.py:208`, `shm_daemon.cpp:130` |
| H4 | `confidence` = raw score (E9) vs \|ψ\|² (collapse) | `geometric_scorer.cpp:359` vs `types.h:94` |
| H5 | Timeout `2000` vs `T_max 500` µs | `engine.py:75` vs watchdog/SOP |
| H6 | `knowledge.py` hardcode `26.8 µs` + ghi 3–4 nơi mỗi host boot | `knowledge.py:297`, `host.py:375` |
| H7 | Latency cùng binary hai bộ: 28.50/79.10 vs 28.10/91.10 | durable_decisions vs audit note |
| H8 | Receipt gửi 2 lần; UI bịa ONLINE; `tra`/`recall` luôn `-32002` | `bus.py`, `app.js:207`, `provenance.py:160` |
| H9 | desktop-studio bịa answer/vitals; 2 protocol UI khônginterop | `server.py:160`, `bridge.py:134` |
| H10 | 4 cơ quan VivyQu vs manifest 3 organ; `cautreo.h` include header chết | `manifest.py:19`, `cautreo.h:17` |
| H11 | `bench_core_latency.exe` hai bản đã drift; DLL package copy không auto-sync | `build/` vs `build/bin/` |
| H12 | Docs claim zero-copy / 100% / early-exit 50% / sparse 10% vượt bằng chứng | audit 29/09 §3 P1 |

---

## 4. MEDIUM

- `HALF_OPEN_PROBE` 100 / 50 / 20 (audit vs code default vs test)
- 11 docs mồ côi ngoài README (gồm review 28/09 + audit 29/09)
- README tree chỉ liệt kê `README+docs`
- Pytest cache tách đôi: root 39 fail vs `host/` pass
- `_pytest_tmp` / `scratch_tmp` pollution do `--basetemp` CWD-relative
- `e9_weights.bin` fallback 4 path theo CWD, không checksum khi nạp
- Fallback A2 `is_valid=True, confidence=1.0` kể cả `ERR_ALL_CONSTRAINTS_VIOLATED`
- StatusFlags không set `FLAG_RENORMALIZED` / `FLAG_ZERO_NORM` / `FLAG_FALLBACK_USED`
- SHM seq lockstep: client restart → daemon treo
- 8 cặp docs↔sync_2brain copy cứng (hash trùng hiện tại, vẫn là dual-home)
- Qubit taxonomy `Ground/…` vs `INERTIA/…`
- Test đóng băng câu trả lời bịa làm contract

---

## 5. Đã đồng bộ (không flag)

- Frame ABI 33600 / 256 byte khớp `types.h` ↔ `types.py` ↔ `cautreo_vivyqu_bridge.h`
- Magic numbers + dimensions 4096/512/16/64 khớp 4 lớp
- E9 weights binary format khớp export ↔ C++ load
- 11 export DLL khớp ctypes prototypes
- `vivyqu_core.dll` đôi + `e9_weights.bin` đôi: hash trùng **hiện tại**
- 7 cặp docs↔sync_2brain: hash trùng **hiện tại**
- Junction `cautreo-host`, `cautreo-desktop-ui` resolve đúng
- Checksum E0 dataset + `BASELINE_A2_FREEZE` match

---

## 6. Thứ tự sửa (đã chốt sau 2 audit ChatGPT)

1. **Evidence honesty:** `ROOT_DIR`, bỏ nuốt exception, tách MEASURED/UNMEASURED, hash DLL — *chatGPT 27/09 P0*
2. **Boundary safety:** guard `pi/pj`, `float64` contiguous trước `memmove`, `is_valid` từ watchdog — *29/09 P0 (sửa trước experiment)*
3. **Status + ownership:** một status trung thực, cô lập claim cũ, tách semantic policy (Vivy) vs execution safety (Cautreo)
4. Gộp version / đồng bộ CMake ↔ `build_core.ps1`
5. Gỡ hardcode `26.8 µs` khỏi `knowledge.py`; bỏ auto-write host boot
6. Cắm backend `cautreo` hoặc gỡ verb `tra`; bỏ receipt trùng; bỏ fake ONLINE
7. Chọn 1 UI hoặc 1 protocol; đánh dấu desktop-studio là sandbox nếu giữ
8. Evidence manifest G0–G7 theo audit 29/09 (ownership → contract → boundary → E2E → verifier → native → perf → product)

---

## 7. Phạm vi lượt này

Thực hiện **CRITICAL 1–3** (mục 6). Các mục 4–8 để backlog, không tự ý mở rộng.
