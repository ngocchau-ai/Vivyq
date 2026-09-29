#pragma once
#include "vivyqu/types.h"
#include <atomic>

namespace vivyqu {

constexpr const char* SHM_REGION_NAME   = "Local\\VivyquSharedMemory_v1";
constexpr size_t      RING_BUFFER_SLOTS = 8;
constexpr uint64_t    MAGIC_SHM_HEADER  = 0x564956595155534DULL; // "VIVYQUSM"

#pragma pack(push, 1)

// Một slot truyền tin song công (Duplex Slot) căn lề 64-byte
struct alignas(64) ShmSlot {
    // Kênh gửi: Cầu Treo -> Core
    // seq_in: monotonic sequence ID loaded by the client, starting at 1.
    // The daemon accepts any non-zero seq_in and resyncs expected_seq to it,
    // so a client restart cannot deadlock the SPSC ring.
    std::atomic<uint64_t> seq_in;       // Sequence ID được nạp bởi Cầu Treo
    uint8_t               pad0[56];     // Căn lề tròn 64 bytes Cacheline
    VivyquInputFrame      in_frame;     // 33.600 bytes

    // Kênh trả về: Core -> Cầu Treo
    std::atomic<uint64_t> seq_out;      // Sequence ID phản hồi bởi Core
    uint8_t               pad1[56];     // Căn lề tròn 64 bytes Cacheline
    VivyquOutputFrame     out_frame;    // 256 bytes
};

// Vùng nhớ chia sẻ toàn cục (Global Shared Memory Layout)
struct alignas(64) ShmRingBuffer {
    uint64_t              magic_header;  // MAGIC_SHM_HEADER
    uint32_t              version;       // ABI_VERSION_1_0
    std::atomic<uint32_t> shutdown_flag; // 1: Ra lệnh Core tắt tiến trình
    uint8_t               pad_hdr[48];   // Căn lề tròn 64 bytes

    ShmSlot               slots[RING_BUFFER_SLOTS];
};

#pragma pack(pop)

} // namespace vivyqu
