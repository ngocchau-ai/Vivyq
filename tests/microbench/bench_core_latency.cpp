#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>
#include "vivyqu/clifford_cl12.h"
#include "vivyqu/rotor_spin12.h"
#include "vivyqu/collapse.h"

int main() {
    std::cout << "=========================================================\n";
    std::cout << "     VIVYQU CORE SPRINT 1 - MICROBENCHMARK HARNESS       \n";
    std::cout << "=========================================================\n\n";

    constexpr size_t WARMUP_RUNS = 5'000;
    constexpr size_t BREAKDOWN_RUNS = 2'000;
    constexpr size_t BENCHMARK_RUNS = 50'000;

    vivyqu::Cl12Multivector state;
    alignas(64) double dummy_latent[vivyqu::CL12_DIMENSION];
    alignas(64) uint8_t constraint_mask[vivyqu::CONSTRAINT_MASK_BYTES];

    // Khởi tạo vector đầu vào giả lập
    for (size_t i = 0; i < vivyqu::CL12_DIMENSION; ++i) {
        dummy_latent[i] = std::sin(static_cast<double>(i) * 0.05);
    }

    // Khởi tạo mặt nạ ràng buộc (75% ứng viên hợp lệ)
    for (size_t i = 0; i < vivyqu::CONSTRAINT_MASK_BYTES; ++i) {
        constraint_mask[i] = (i % 4 != 0) ? 0xFF : 0xAA;
    }

    // Khởi tạo 16 Givens Rotors
    vivyqu::GivensRotor rotors[16];
    for (uint8_t m = 0; m < 16; ++m) {
        rotors[m].plane_i = m % 12;
        rotors[m].plane_j = (m + 3) % 12;
        float angle = static_cast<float>(m) * 0.1f;
        rotors[m].cos_half_th = std::cos(angle * 0.5f);
        rotors[m].sin_half_th = std::sin(angle * 0.5f);
    }

    // --- BƯỚC 1: LÀM ẤM BỘ NHỚ ĐỆM (CACHE WARM-UP) ---
    std::cout << "[1/3] Warming up CPU L1/L2 Instruction and Data Cache (" << WARMUP_RUNS << " runs)...\n";
    for (size_t i = 0; i < WARMUP_RUNS; ++i) {
        state.ingest_and_normalize(dummy_latent);
        vivyqu::Spin12Engine::apply_factorized_rotors(state, rotors, 16);
        vivyqu::CollapseEngine::collapse_hard_masked(state, constraint_mask);
    }
    std::cout << "      Warm-up completed. L1 Data Cache pre-warmed.\n\n";

    // --- BƯỚC 2: ĐO LƯỜNG TỪNG PHÂN ĐOẠN ĐỘC LẬP (PROFILING BREAKDOWN) ---
    std::cout << "[2/3] Profiling Individual Pipeline Stages (" << BREAKDOWN_RUNS << " runs)...\n";
    double t_ingest_sum = 0.0;
    double t_rotor_sum = 0.0;
    double t_collapse_sum = 0.0;

    for (size_t i = 0; i < BREAKDOWN_RUNS; ++i) {
        auto t0 = std::chrono::high_resolution_clock::now();
        state.ingest_and_normalize(dummy_latent);
        auto t1 = std::chrono::high_resolution_clock::now();
        vivyqu::Spin12Engine::apply_factorized_rotors(state, rotors, 16);
        auto t2 = std::chrono::high_resolution_clock::now();
        vivyqu::CollapseEngine::collapse_hard_masked(state, constraint_mask);
        auto t3 = std::chrono::high_resolution_clock::now();

        t_ingest_sum += std::chrono::duration<double, std::micro>(t1 - t0).count();
        t_rotor_sum += std::chrono::duration<double, std::micro>(t2 - t1).count();
        t_collapse_sum += std::chrono::duration<double, std::micro>(t3 - t2).count();
    }
    double avg_ingest = t_ingest_sum / BREAKDOWN_RUNS;
    double avg_rotor = t_rotor_sum / BREAKDOWN_RUNS;
    double avg_collapse = t_collapse_sum / BREAKDOWN_RUNS;
    std::cout << "      Stage 1: Ingest & Norm (32 KiB) : " << avg_ingest << " µs\n";
    std::cout << "      Stage 2: 16x Givens Rotors      : " << avg_rotor << " µs\n";
    std::cout << "      Stage 3: Masked Collapse Scan   : " << avg_collapse << " µs\n\n";

    // --- BƯỚC 3: ĐO LƯỜNG ĐỘ TRỄ VI MÔ TOÀN CHUỖI KHÔNG NHIỄU (50.000 RUNS) ---
    std::cout << "[3/3] Running Pure High-Resolution Core Pipeline Benchmarks (" << BENCHMARK_RUNS << " runs)...\n";
    std::vector<double> latencies_us;
    latencies_us.reserve(BENCHMARK_RUNS);

    double initial_sq_norm = 0.0;
    double final_sq_norm = 0.0;

    for (size_t i = 0; i < BENCHMARK_RUNS; ++i) {
        auto t_start = std::chrono::high_resolution_clock::now();

        // Chuỗi tính toán Lõi (Core Pipeline):
        // 1. Nạp và chuẩn hóa L2 (32 KiB)
        state.ingest_and_normalize(dummy_latent);
        if (i == 0) initial_sq_norm = state.compute_squared_norm();

        // 2. Quay chuỗi 16 Rotor Givens
        vivyqu::Spin12Engine::apply_factorized_rotors(state, rotors, 16);

        // 3. Sụp đổ xác định có lọc mặt nạ 512 bytes
        auto decision = vivyqu::CollapseEngine::collapse_hard_masked(state, constraint_mask);

        auto t_end = std::chrono::high_resolution_clock::now();
        double elapsed_us = std::chrono::duration<double, std::micro>(t_end - t_start).count();
        latencies_us.push_back(elapsed_us);

        if (i == BENCHMARK_RUNS - 1) {
            final_sq_norm = state.compute_squared_norm();
            (void)decision;
        }
    }

    // --- BƯỚC 4: PHÂN TÍCH VÀ BÁO CÁO THỐNG KÊ ---
    std::sort(latencies_us.begin(), latencies_us.end());

    double p50 = latencies_us[static_cast<size_t>(BENCHMARK_RUNS * 0.50)];
    double p90 = latencies_us[static_cast<size_t>(BENCHMARK_RUNS * 0.90)];
    double p95 = latencies_us[static_cast<size_t>(BENCHMARK_RUNS * 0.95)];
    double p99 = latencies_us[static_cast<size_t>(BENCHMARK_RUNS * 0.99)];
    double max_lat = latencies_us.back();
    double min_lat = latencies_us.front();

    double norm_drift = std::abs(final_sq_norm - 1.0);

    std::cout << "\n================ BENCHMARK REPORT ================\n";
    std::cout << " State Representation   : Multivector Cl(12) [32.768 bytes]\n";
    std::cout << " Active Rotors          : 16 Givens-like Rotors\n";
    std::cout << " Total Test Runs        : " << BENCHMARK_RUNS << "\n";
    std::cout << "--------------------------------------------------\n";
    std::cout << " Stage 1: Ingest & Norm : " << avg_ingest << " µs (avg)\n";
    std::cout << " Stage 2: 16x Rotors    : " << avg_rotor << " µs (avg)\n";
    std::cout << " Stage 3: Collapse Scan : " << avg_collapse << " µs (avg)\n";
    std::cout << " Total Pipeline Sum     : " << (avg_ingest + avg_rotor + avg_collapse) << " µs (avg)\n";
    std::cout << "--------------------------------------------------\n";
    std::cout << " Latency p50 (Median)   : " << p50 << " µs\n";
    std::cout << " Latency p90            : " << p90 << " µs\n";
    std::cout << " Latency p95            : " << p95 << " µs\n";
    std::cout << " Latency p99 (Target)   : " << p99 << " µs\n";
    std::cout << " Min / Max Latency      : " << min_lat << " µs / " << max_lat << " µs\n";
    std::cout << " Norm Conservation Drift: " << norm_drift << " (Initial: " << initial_sq_norm << ", Final: " << final_sq_norm << ")\n";
    std::cout << "==================================================\n\n";

    if (p99 < 10.0 && norm_drift < 1e-5) {
        std::cout << ">> VERDICT: [PASS] - Core achieves Sub-10-Microsecond target (" << p99 << " µs) and strict norm conservation!\n";
        if (p99 < 5.0) {
            std::cout << ">> STRETCH GOAL: [ACHIEVED] - Sub-5-Microsecond latency unlocked!\n";
        }
        return 0;
    } else {
        std::cout << ">> VERDICT: [WARNING/FAIL] - Check SIMD optimizations or norm drift tolerances.\n";
        return 1;
    }
}
