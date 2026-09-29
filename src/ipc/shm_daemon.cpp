#include "vivyqu/ipc_shm.h"
#include "vivyqu/c_api.h"
#include "vivyqu/types.h"
#include <iostream>
#include <string>
#include <vector>
#include <windows.h>
#include <emmintrin.h>

int main(int argc, char* argv[]) {
    std::cout << "=========================================================\n";
    std::cout << "     VIVYQU CORE DAEMON - LOCK-FREE SHARED MEMORY        \n";
    std::cout << "=========================================================\n\n";

    // 1. Phân tích tham số dòng lệnh
    int pin_core = 2;
    std::string weights_path = "";
    bool force_e9_mode = true;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--pin" && i + 1 < argc) {
            pin_core = std::stoi(argv[++i]);
        } else if (arg == "--weights" && i + 1 < argc) {
            weights_path = argv[++i];
        } else if (arg == "--mode" && i + 1 < argc) {
            std::string m = argv[++i];
            force_e9_mode = (m == "e9");
        }
    }

    // 2. Thiết lập ưu tiên thời gian thực theo SOP_OPERATIONAL_RUNBOOK.md
    SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
    if (pin_core >= 0 && pin_core < 64) {
        SetProcessAffinityMask(GetCurrentProcess(), 1ULL << pin_core);
    }

    // 3. Tạo hoặc mở Shared Memory Segment
    HANDLE hMapFile = CreateFileMappingA(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        sizeof(vivyqu::ShmRingBuffer),
        vivyqu::SHM_REGION_NAME
    );

    if (!hMapFile) {
        std::cerr << "[ERROR] Cannot create FileMapping! Error: " << GetLastError() << std::endl;
        return 1;
    }

    vivyqu::ShmRingBuffer* shm = static_cast<vivyqu::ShmRingBuffer*>(
        MapViewOfFile(hMapFile, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(vivyqu::ShmRingBuffer))
    );

    if (!shm) {
        std::cerr << "[ERROR] Cannot MapViewOfFile! Error: " << GetLastError() << std::endl;
        CloseHandle(hMapFile);
        return 1;
    }

    // 4. Khởi tạo cấu trúc Ring Buffer
    shm->magic_header = vivyqu::MAGIC_SHM_HEADER;
    shm->version = vivyqu::ABI_VERSION_1_0;
    shm->shutdown_flag.store(0, std::memory_order_release);

    for (size_t s = 0; s < vivyqu::RING_BUFFER_SLOTS; ++s) {
        shm->slots[s].seq_in.store(0, std::memory_order_release);
        shm->slots[s].seq_out.store(0, std::memory_order_release);
    }

    // 5. Khởi tạo Core Engine
    vivyqu_core_init();

    // 6. Nạp trọng số E9 Geometric Scorer
    bool e9_loaded = false;
    if (!weights_path.empty()) {
        e9_loaded = (vivyqu_core_load_e9_weights(weights_path.c_str()) == 0);
    }
    if (!e9_loaded) {
        const char* default_paths[] = {
            "data/e9_weights.bin",
            "../data/e9_weights.bin",
            "results/branch_c/e9_weights.bin",
            "../results/branch_c/e9_weights.bin"
        };
        for (const char* p : default_paths) {
            if (vivyqu_core_load_e9_weights(p) == 0) {
                weights_path = p;
                e9_loaded = true;
                break;
            }
        }
    }

    // 7. Làm ấm Cache (Cache Warm-Up) trước khi đón nhận luồng tick
    if (e9_loaded) {
        vivyqu::VivyquInputFrame dummy_in{};
        vivyqu::VivyquOutputFrame dummy_out{};
        dummy_in.magic_header = vivyqu::MAGIC_INPUT_FRAME;
        dummy_in.sequence_id = 0;
        dummy_in.mode_flags = vivyqu::MODE_GEOMETRIC_E9;
        std::memset(dummy_in.constraint_bitmask, 0xFF, sizeof(dummy_in.constraint_bitmask));
        for (size_t i = 0; i < 4096; ++i) dummy_in.latent_vector[i] = 0.01;

        for (int w = 0; w < 50; ++w) {
            vivyqu_core_step(&dummy_in, &dummy_out);
        }
    }

    std::cout << "[DAEMON READY] Listening on: " << vivyqu::SHM_REGION_NAME << "\n";
    std::cout << "               Ring Buffer : " << vivyqu::RING_BUFFER_SLOTS << " slots (SPSC Lock-Free)\n";
    std::cout << "               Core Thread : CPU Core " << pin_core << " (HIGH_PRIORITY_CLASS)\n";
    std::cout << "               E9 Scorer   : " << (e9_loaded ? ("LOADED (" + weights_path + ")") : "NOT LOADED (Standard Argmax fallback)") << "\n";
    std::cout << "               Default Mode: " << (force_e9_mode ? "MODE_GEOMETRIC_E9" : "DYNAMIC") << "\n\n";
    std::cout << "Press Ctrl+C or set shutdown_flag=1 to terminate.\n" << std::endl;

    uint64_t expected_seq = 1;
    uint64_t processed_count = 0;

    // 8. Vòng lặp Spin-wait phi khóa cực nhạy (Lock-free SPSC Consumer)
    while (!shm->shutdown_flag.load(std::memory_order_relaxed)) {
        // Quét 8 slot: frame mới là seq_in != 0 && seq_in != seq_out.
        // Không khóa expected_seq — client restart/skip vẫn phục hồi được.
        bool processed = false;
        for (size_t i = 0; i < vivyqu::RING_BUFFER_SLOTS; ++i) {
            vivyqu::ShmSlot& slot = shm->slots[i];
            uint64_t cur_seq = slot.seq_in.load(std::memory_order_acquire);
            uint64_t out_seq = slot.seq_out.load(std::memory_order_relaxed);
            if (cur_seq == 0 || cur_seq == out_seq) {
                continue;
            }

            if (force_e9_mode && e9_loaded && slot.in_frame.mode_flags == 0) {
                slot.in_frame.mode_flags = vivyqu::MODE_GEOMETRIC_E9;
            }

            vivyqu_core_step(&slot.in_frame, &slot.out_frame);
            slot.seq_out.store(cur_seq, std::memory_order_release);
            expected_seq = cur_seq + 1;
            processed_count++;
            processed = true;

            if (processed_count % 10000 == 0) {
                std::cout << "[DAEMON STATS] Processed " << processed_count << " frames in real-time.\n";
            }
            break;
        }
        if (!processed) {
            _mm_pause();
        }
    }

    std::cout << "\n[DAEMON SHUTDOWN] Terminating gracefully. Total processed: " << processed_count << "\n";
    vivyqu_core_cleanup();
    UnmapViewOfFile(shm);
    CloseHandle(hMapFile);
    return 0;
}
