cmake_minimum_required(VERSION 3.20)
project(vivyqu_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Cờ tối ưu hóa tốc độ cực đại (Sub-10-Microsecond Core Latency)
if(MSVC)
    add_compile_options(
        /O2                 # Tối ưu hóa tốc độ tối đa
        /Oi                 # Bật intrinsics
        /arch:AVX2          # Bật tập lệnh AVX2 (hoặc AVX512 nếu CPU hỗ trợ)
        /fp:fast            # Fast floating-point math
        /W4                 # Mức cảnh báo cao
        /permissive-        # Tuân thủ chuẩn C++ khắt khe
    )
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
else()
    add_compile_options(
        -O3                 # Mức tối ưu cao nhất
        -march=native       # Tận dụng toàn bộ tập lệnh của vi xử lý máy đang chạy
        -mavx2
        -mfma
        -ffast-math         # Tăng tốc tính toán dấu phẩy động
        -fno-exceptions     # Tắt exceptions để zero runtime overhead
        -fno-rtti           # Tắt RTTI để giảm kích thước nhị phân
        -Wall
        -Wextra
        -Wpedantic
    )
endif()

# Thư mục include chung
include_directories(include)

# Nguồn Math Core — khớp scripts/build_core.ps1 (single source list)
set(VIVYQU_MATH_SOURCES
    src/core/clifford_cl12.cpp
    src/core/rotor_spin12.cpp
    src/core/hamiltonian_flow.cpp
    src/core/collapse.cpp
    src/core/geometric_scorer.cpp
    src/core/qubit_polarization.cpp
)

# Build Thư viện Toán học Tĩnh VivyQu Math Core (Sprint 1)
add_library(vivyqu_math STATIC
    ${VIVYQU_MATH_SOURCES}
)

target_include_directories(vivyqu_math PUBLIC include)

# C-ABI shared library — khớp artifact vivyqu_core.dll trong build_core.ps1
add_library(vivyqu_core SHARED
    ${VIVYQU_MATH_SOURCES}
    src/core/c_api.cpp
)
target_include_directories(vivyqu_core PUBLIC include)
target_compile_definitions(vivyqu_core PRIVATE VIVYQU_EXPORTS)

# Shared Memory IPC Daemon — khớp vivyqu_shm_daemon.exe trong build_core.ps1
add_executable(vivyqu_shm_daemon
    ${VIVYQU_MATH_SOURCES}
    src/core/c_api.cpp
    src/ipc/shm_daemon.cpp
)
target_include_directories(vivyqu_shm_daemon PRIVATE include)
target_compile_definitions(vivyqu_shm_daemon PRIVATE VIVYQU_EXPORTS)

# Build Harness Benchmark Đo Lường Vi Mô Độ Phân Giải Cao
add_executable(bench_core_latency tests/microbench/bench_core_latency.cpp)
target_link_libraries(bench_core_latency PRIVATE vivyqu_math)

# E9 latency harness (cùng artifact với build_core.ps1)
add_executable(bench_e9_latency tests/microbench/bench_e9_latency.cpp)
target_link_libraries(bench_e9_latency PRIVATE vivyqu_math)
