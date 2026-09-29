#pragma once
#include "types.h"

namespace vivyqu {

// Multivector thuần số thực 32 KiB căn lề 64-byte theo chuẩn Cacheline
struct alignas(CACHELINE_SIZE) Cl12Multivector {
    // 4.096 hệ số thực (float64) = 32.768 bytes
    // Tương ứng 1-1 với 4.096 basis blades của đại số Clifford Cl(12)
    // Sắp xếp theo thứ tự nhị phân chuẩn (Canonical Bit-ordering)
    double blades[CL12_DIMENSION];

    // Khởi tạo trạng thái zero
    void reset() noexcept;

    // Nạp vector tiềm ẩn h và chuẩn hóa L2 tức thì trong 1 lượt duyệt (O(d))
    // Đồng thời kiểm tra khử NaN/Inf và zero-norm
    void ingest_and_normalize(const double* __restrict latent_h) noexcept;

    // Tính bình phương chuẩn hình học: ||ψ||² = <ψ ψ~>₀ = Σ blades[A]²
    double compute_squared_norm() const noexcept;

    // Tái chuẩn hóa tại chỗ (In-place Renormalization) khi phát hiện trôi số học
    void renormalize_in_place() noexcept;
};

} // namespace vivyqu
