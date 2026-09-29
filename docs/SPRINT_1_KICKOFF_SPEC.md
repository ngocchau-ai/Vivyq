# [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# ĐẶC TẢ KÍCH HOẠT SPRINT 1: XÂY DỰNG MATH CORE C++20 & MICROBENCH HARNESS
## (SPRINT 1 IMPLEMENTATION & VERIFICATION BLUEPRINT)

**Dự án:** Vivyqu (Vivy Qudit Engine)  
**Mã Sprint:** SPRINT-01-MATH-CORE  
**Trạng thái:** ĐÃ PHÊ DUYỆT — SẴN SÀNG TRIỂN KHAI (APPROVED — READY TO CODE)  
**Thời gian mục tiêu:** Tuần 1 – Tuần 2  
**Mục tiêu tối thượng:** Đạt độ trễ tính toán thuần túy Lõi (Core Latency) **p99 < 5.0 micro-giây ($< 5\ \mu\text{s}$)** trên CPU phổ thông với dung lượng bộ nhớ cố định **32 KiB Multivector $\mathcal{C}\ell(12)$**.

---

## LỊCH SỬ THAY ĐỔI (CHANGELOG)

- **2026-09-27 | Antigravity / Ngọc Châu Assistant:** Khởi tạo bản đặc tả kích hoạt Sprint 1 sau khi Kế hoạch Xây dựng Tổng thể được phê duyệt toàn diện. Khóa cấu trúc thư mục source C++, khai báo header chuẩn, thuật toán nhân tử Givens Rotor, cờ biên dịch tối ưu hóa SIMD AVX-512/AVX2 và harness kiểm thử vi mô độ phân giải cao.

---

## 1. CẤU TRÚC THƯ MỤC SOURCE CODE CHUẨN CỦA SPRINT 1

Toàn bộ mã nguồn Sprint 1 sẽ được tổ chức độc lập, module hóa cao độ trong thư mục `src/core/` và `tests/microbench/`:

```text
d:\Vivyqu\
├── include\
│   └── vivyqu\
│       ├── types.h               # Định nghĩa kiểu dữ liệu căn lề 64-byte, bitmask
│       ├── clifford_cl12.h       # Cấu trúc Multivector Cl(12) 4096 chiều (32 KiB)
│       ├── rotor_spin12.h        # Toán tử Spin(12) phân tích nhân tử Givens Rotors
│       ├── hamiltonian_flow.h    # Động lực học hạ thế năng Bivector Torque Flow
│       └── collapse.h            # Sụp đổ hàm sóng xác định Hard-Masked Argmax
├── src\
│   └── core\
│       ├── clifford_cl12.cpp     # Hiện thực hóa nạp vector và chuẩn hóa L2
│       ├── rotor_spin12.cpp      # Tối ưu hóa phép quay sandwich R ψ R~ qua SIMD
│       ├── hamiltonian_flow.cpp  # Tính toán moment lực hình học
│       └── collapse.cpp          # Tìm kiếm argmax có vector hóa AVX2/AVX-512
├── tests\
│   ├── unit\
│   │   ├── test_cl12_math.cpp    # Kiểm thử tính đúng đắn đại số Clifford
│   │   └── test_norm_drift.cpp   # Kiểm tra bảo toàn chuẩn sau 100.000 phép quay
│   └── microbench\
│       ├── bench_core_latency.cpp# Đo đạc p50, p90, p95, p99 bằng CPU cycles
│       └── bench_cache_miss.cpp  # Đo L1-D Misses qua hardware counters
├── CMakeLists.txt                # Cấu hình biên dịch tối ưu hóa phần cứng
└── README.md
```

---

## 2. ĐẶC TẢ CHI TIẾT HEADER & THUẬT TOÁN CỐT LÕI

### 2.1. Cấu Trúc Dữ Liệu Multivector $\mathcal{C}\ell(12)$ (`include/vivyqu/clifford_cl12.h`)

```cpp
#pragma once
#include <cstdint>
#include <cstddef>
#include <immintrin.h>

namespace vivyqu {

// Hằng số không gian trạng thái
constexpr size_t CL12_DIMENSION = 4096; // 2^12 basis blades
constexpr size_t CACHELINE_SIZE = 64;

// Multivector thuần số thực 32 KiB căn lề 64-byte
struct alignas(CACHELINE_SIZE) Cl12Multivector {
    // 4096 hệ số thực (float64) = 32.768 bytes
    // Sắp xếp theo thứ tự nhị phân chuẩn (Canonical Bit-ordering)
    double blades[CL12_DIMENSION];

    // Khởi tạo trạng thái rỗng
    void reset() noexcept;

    // Nạp vector tiềm ẩn h và chuẩn hóa L2 tức thì trong 1 lượt duyệt
    void ingest_and_normalize(const double* __restrict latent_h) noexcept;

    // Tính bình phương chuẩn hình học: ||ψ||² = Σ blades[A]²
    double compute_squared_norm() const noexcept;

    // Tái chuẩn hóa tại chỗ nếu phát hiện trôi số học
    void renormalize_in_place() noexcept;
};

} // namespace vivyqu
```

### 2.2. Toán Tử Xoay Nhân Tử Givens Rotor (`include/vivyqu/rotor_spin12.h`)

Một rotor 2-blade $R_m = \cos(\theta_m / 2) - \sin(\theta_m / 2) e_{i_m} e_{j_m}$ chỉ tác động lên các cặp blade $e_A$ và $e_B$ có liên kết qua mặt phẳng $(i_m, j_m)$:

```cpp
#pragma once
#include "clifford_cl12.h"

namespace vivyqu {

struct GivensRotor {
    uint8_t plane_i;      // Chiều thứ nhất [0..11]
    uint8_t plane_j;      // Chiều thứ hai  [0..11]
    float   cos_half_th;  // cos(θ / 2)
    float   sin_half_th;  // sin(θ / 2)
};

class Spin12Engine {
public:
    // Áp dụng chuỗi M rotor sandwich: ψ' = R_M ... (R_1 ψ R_1~) ... R_M~
    // Tối ưu hóa cache: Xử lý tại chỗ trên mảng 32 KiB không cấp phát bộ nhớ mới
    static void apply_factorized_rotors(
        Cl12Multivector& __restrict state,
        const GivensRotor* __restrict rotors,
        size_t count
    ) noexcept;
};

} // namespace vivyqu
```

### 2.3. Sụp Đổ Hàm Sóng Xác Định Có Mặt Nạ (`include/vivyqu/collapse.h`)

```cpp
#pragma once
#include "clifford_cl12.h"

namespace vivyqu {

struct DecisionResult {
    uint32_t best_index;     // k* ∈ [0..4095]
    double   confidence;     // Biên độ xác suất |ψ_{A(k*)}|²
    bool     is_valid;       // true nếu thỏa mãn ràng buộc
};

class CollapseEngine {
public:
    // Tìm kiếm k* = argmax_{k ∈ Valid} (ψ_A[k]²) sử dụng SIMD AVX2/AVX-512
    static DecisionResult collapse_hard_masked(
        const Cl12Multivector& __restrict state,
        const uint8_t* __restrict constraint_bitmask // 512 bytes (4096 bits)
    ) noexcept;
};

} // namespace vivyqu
```

---

## 3. CẤU HÌNH BIÊN DỊCH TỐI ƯU HÓA PHẦN CỨNG (`CMakeLists.txt`)

Để đạt tốc độ $< 5.0\ \mu\text{s}$, cờ biên dịch bắt buộc phải kích hoạt tối đa năng lực phần cứng của máy chủ/CPU:

```cmake
cmake_minimum_required(VERSION 3.20)
project(vivyqu_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Cờ tối ưu hóa hiệu năng cực đại cho GCC / Clang / MSVC
if(MSVC)
    add_compile_options(
        /O2                 # Tối ưu tốc độ tối đa
        /Oi                 # Bật intrinsics
        /arch:AVX2          # Bật tập lệnh AVX2 (hoặc /arch:AVX512 nếu CPU hỗ trợ)
        /GL                 # Whole Program Optimization
        /fp:fast            # Fast floating-point math
    )
else()
    add_compile_options(
        -O3                 # Mức tối ưu cao nhất
        -march=native       # Tận dụng toàn bộ tập lệnh CPU của máy đang chạy
        -mavx2
        -mfma
        -ffast-math         # Tăng tốc tính toán dấu phẩy động
        -fno-exceptions     # Tắt ngoại lệ C++ để zero overhead
        -fno-rtti           # Tắt RTTI để giảm kích thước nhị phân
    )
endif()

# Build thư viện tĩnh
add_library(vivyqu_math STATIC
    src/core/clifford_cl12.cpp
    src/core/rotor_spin12.cpp
    src/core/hamiltonian_flow.cpp
    src/core/collapse.cpp
)

target_include_directories(vivyqu_math PUBLIC include)

# Build Harness kiểm thử vi mô
add_executable(bench_core_latency tests/microbench/bench_core_latency.cpp)
target_link_libraries(bench_core_latency PRIVATE vivyqu_math)
```

---

## 4. QUY TRÌNH THỰC HIỆN BENCHMARK ĐO LƯỜNG VI MÔ (MICROBENCH HARNESS)

Harness đo lường phải dùng đồng hồ chu kỳ CPU độ phân giải nano-giây:

```cpp
// Trích đoạn logic đo lường trong tests/microbench/bench_core_latency.cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include "vivyqu/clifford_cl12.h"
#include "vivyqu/rotor_spin12.h"
#include "vivyqu/collapse.h"

#ifdef _MSC_VER
#include <intrin.h>
#else
#include <x86intrin.h>
#endif

inline uint64_t rdtsc() {
    return __rdtsc();
}

int main() {
    constexpr size_t WARMUP_RUNS = 10'000;
    constexpr size_t BENCHMARK_RUNS = 100'000;

    vivyqu::Cl12Multivector state;
    alignas(64) double dummy_h[4096];
    alignas(64) uint8_t mask[512];
    std::fill_n(dummy_h, 4096, 1.0);
    std::fill_n(mask, 512, 0xFF); // Toàn bộ hợp lệ

    // 1. Làm ấm Cache (Warm-up)
    for (size_t i = 0; i < WARMUP_RUNS; ++i) {
        state.ingest_and_normalize(dummy_h);
        vivyqu::CollapseEngine::collapse_hard_masked(state, mask);
    }

    // 2. Chạy Benchmark và ghi nhận chu kỳ
    std::vector<double> latencies_us;
    latencies_us.reserve(BENCHMARK_RUNS);

    for (size_t i = 0; i < BENCHMARK_RUNS; ++i) {
        auto t_start = std::chrono::high_resolution_clock::now();

        state.ingest_and_normalize(dummy_h);
        // Áp dụng 16 rotor
        // vivyqu::Spin12Engine::apply_factorized_rotors(state, rotors, 16);
        auto decision = vivyqu::CollapseEngine::collapse_hard_masked(state, mask);

        auto t_end = std::chrono::high_resolution_clock::now();
        double elapsed_us = std::chrono::duration<double, std::micro>(t_end - t_start).count();
        latencies_us.push_back(elapsed_us);
    }

    std::sort(latencies_us.begin(), latencies_us.end());
    double p50 = latencies_us[BENCHMARK_RUNS * 0.50];
    double p95 = latencies_us[BENCHMARK_RUNS * 0.95];
    double p99 = latencies_us[BENCHMARK_RUNS * 0.99];

    std::cout << "=== VIVYQU SPRINT 1 CORE MICROBENCHMARK RESULTS ===\n";
    std::cout << "Runs: " << BENCHMARK_RUNS << "\n";
    std::cout << "Latency p50: " << p50 << " µs\n";
    std::cout << "Latency p95: " << p95 << " µs\n";
    std::cout << "Latency p99: " << p99 << " µs\n";

    if (p99 < 5.0) {
        std::cout << ">> RESULT: [PASS] - Core Latency achieves Sub-5-Microsecond goal!\n";
    } else {
        std::cout << ">> RESULT: [FAIL] - Requires SIMD loop unrolling optimization.\n";
    }
    return 0;
}
```

---

## 5. CHECKLIST NGHIỆM THU KỸ THUẬT SPRINT 1

Kỹ sư triển khai phải đạt 100% các tiêu chí nghiệm thu sau trước khi đóng Sprint 1:

- [ ] Cấu trúc `Cl12Multivector` có kích thước chính xác $32.768\text{ bytes}$ ($32\text{ KiB}$) và căn lề 64-byte.
- [ ] Hàm `ingest_and_normalize` chạy trong $< 1.0\ \mu\text{s}$ trên vector 4096 chiều.
- [ ] Phép quay Rotor Givens bảo toàn chuẩn: sau 100.000 chu kỳ, độ lệch $|\Delta_{\text{norm}}| < 10^{-6}$.
- [ ] Hàm `collapse_hard_masked` chạy trong $< 1.5\ \mu\text{s}$ có mặt nạ lọc 512 bytes.
- [ ] **Tổng thời gian Core-only đo bằng Microbench:** **p99 $< 5.0\ \mu\text{s}$** trên CPU thử nghiệm.
- [ ] Không có memory allocation (`new`, `malloc`) nào diễn ra trong hot path của hàm tính toán.
