#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include "vivyqu/c_api.h"
#include "vivyqu/geometric_scorer.h"

int main() {
    std::cout << "=========================================================\n";
    std::cout << "   VIVYQU CORE E9-v2 PRODUCTION MICROBENCHMARK (50,000)   \n";
    std::cout << "=========================================================\n\n";

    constexpr size_t WARMUP_RUNS = 5'000;
    constexpr size_t BREAKDOWN_RUNS = 5'000;
    constexpr size_t BENCHMARK_RUNS = 50'000;

    int init_rc = vivyqu_core_init();
    if (init_rc != vivyqu::ERR_NONE) {
        std::cerr << "Core init failed!\n";
        return 1;
    }

    int load_rc = vivyqu_core_load_e9_weights("data/e9_weights.bin");
    if (load_rc != vivyqu::ERR_NONE) {
        load_rc = vivyqu_core_load_e9_weights("results/branch_c/e9_weights.bin");
    }
    if (load_rc != vivyqu::ERR_NONE) {
        std::cerr << "Failed to load e9_weights.bin!\n";
        return 1;
    }
    std::cout << "[INIT] Loaded E9 Weights successfully.\n\n";

    vivyqu::VivyquInputFrame in_frame{};
    vivyqu::VivyquOutputFrame out_frame{};

    in_frame.magic_header = vivyqu::MAGIC_INPUT_FRAME;
    in_frame.sequence_id = 1;
    in_frame.version = vivyqu::ABI_VERSION_1_0;
    in_frame.mode_flags = vivyqu::MODE_GEOMETRIC_E9;
    in_frame.active_rotors = 0; // Use default 8 Branch C rotors

    // Khởi tạo vector đầu vào
    for (size_t i = 0; i < vivyqu::CL12_DIMENSION; ++i) {
        in_frame.latent_vector[i] = std::sin(static_cast<double>(i) * 0.05);
    }

    // Khởi tạo mặt nạ ràng buộc (75% ứng viên hợp lệ)
    for (size_t i = 0; i < vivyqu::CONSTRAINT_MASK_BYTES; ++i) {
        in_frame.constraint_bitmask[i] = (i % 4 != 0) ? 0xFF : 0xAA;
    }

    // --- BƯỚC 1: LÀM ẤM BỘ NHỚ ĐỆM (CACHE WARM-UP) ---
    std::cout << "[1/3] Warming up CPU L1/L2/L3 Instruction and Weights Cache (" << WARMUP_RUNS << " runs)...\n";
    for (size_t i = 0; i < WARMUP_RUNS; ++i) {
        vivyqu_core_step_e9(&in_frame, &out_frame);
    }
    std::cout << "      Warm-up completed. All ~2 MiB weights hot in CPU Cache.\n\n";

    // --- BƯỚC 2: CHU KỲ RA QUYẾT ĐỊNH ĐẦU-CUỐI (50,000 CHU KỲ ĐO LƯỜNG) ---
    std::cout << "[2/3] Measuring End-to-End Latency across " << BENCHMARK_RUNS << " iterations...\n";
    std::vector<double> latencies;
    latencies.reserve(BENCHMARK_RUNS);

    for (size_t i = 0; i < BENCHMARK_RUNS; ++i) {
        in_frame.sequence_id = i + 1;
        auto t0 = std::chrono::high_resolution_clock::now();
        vivyqu_core_step_e9(&in_frame, &out_frame);
        auto t1 = std::chrono::high_resolution_clock::now();
        double us = std::chrono::duration<double, std::micro>(t1 - t0).count();
        latencies.push_back(us);
    }

    std::sort(latencies.begin(), latencies.end());

    double p50 = latencies[static_cast<size_t>(BENCHMARK_RUNS * 0.50)];
    double p95 = latencies[static_cast<size_t>(BENCHMARK_RUNS * 0.95)];
    double p99 = latencies[static_cast<size_t>(BENCHMARK_RUNS * 0.99)];
    double p999 = latencies[static_cast<size_t>(BENCHMARK_RUNS * 0.999)];
    double min_lat = latencies.front();
    double max_lat = latencies.back();
    double sum = 0.0;
    for (double v : latencies) sum += v;
    double avg = sum / BENCHMARK_RUNS;

    std::cout << "\n" << std::string(60, '=') << "\n";
    std::cout << "         VIVYQU E9-v2 C++ CORE EMPIRICAL BENCHMARK\n";
    std::cout << std::string(60, '=') << "\n";
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "  Iterations Evaluated   : " << BENCHMARK_RUNS << "\n";
    std::cout << "  k* Optimal Decision    : " << out_frame.best_decision_idx << "\n";
    std::cout << "  Confidence Score       : " << out_frame.best_confidence << "\n";
    std::cout << "  Valid Candidates Found : " << out_frame.valid_candidates << " / 4096\n";
    std::cout << "---------------------------------------------------------\n";
    std::cout << "  Min Latency            : " << min_lat << " µs\n";
    std::cout << "  p50 Latency (Median)   : " << p50 << " µs\n";
    std::cout << "  Mean Latency           : " << avg << " µs\n";
    std::cout << "  p95 Latency            : " << p95 << " µs\n";
    std::cout << "  p99 Latency (SLA)      : " << p99 << " µs\n";
    std::cout << "  p99.9 Latency          : " << p999 << " µs\n";
    std::cout << "  Max Latency            : " << max_lat << " µs\n";
    std::cout << std::string(60, '=') << "\n\n";

    vivyqu_core_cleanup();
    return 0;
}
