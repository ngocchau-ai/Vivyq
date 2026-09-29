#include "vivyqu/clifford_cl12.h"
#include <cmath>
#include <cstring>
#include <algorithm>
#include <immintrin.h>

namespace vivyqu {

void Cl12Multivector::reset() noexcept {
    std::memset(blades, 0, sizeof(blades));
}

void Cl12Multivector::ingest_and_normalize(const double* __restrict latent_h) noexcept {
#if defined(__AVX2__) && defined(__FMA__)
    __m256d acc0 = _mm256_setzero_pd();
    __m256d acc1 = _mm256_setzero_pd();
    __m256d acc2 = _mm256_setzero_pd();
    __m256d acc3 = _mm256_setzero_pd();

    // Duyệt unroll 16 doubles (4 thanh ghi AVX2) mỗi bước dùng loadu/storeu an toàn tuyệt đối
    for (size_t i = 0; i < CL12_DIMENSION; i += 16) {
        __m256d v0 = _mm256_loadu_pd(latent_h + i + 0);
        __m256d v1 = _mm256_loadu_pd(latent_h + i + 4);
        __m256d v2 = _mm256_loadu_pd(latent_h + i + 8);
        __m256d v3 = _mm256_loadu_pd(latent_h + i + 12);

        _mm256_storeu_pd(blades + i + 0, v0);
        _mm256_storeu_pd(blades + i + 4, v1);
        _mm256_storeu_pd(blades + i + 8, v2);
        _mm256_storeu_pd(blades + i + 12, v3);

        acc0 = _mm256_fmadd_pd(v0, v0, acc0);
        acc1 = _mm256_fmadd_pd(v1, v1, acc1);
        acc2 = _mm256_fmadd_pd(v2, v2, acc2);
        acc3 = _mm256_fmadd_pd(v3, v3, acc3);
    }

    __m256d sum_acc = _mm256_add_pd(_mm256_add_pd(acc0, acc1), _mm256_add_pd(acc2, acc3));
    alignas(32) double temp[4];
    _mm256_storeu_pd(temp, sum_acc);
    double sum_sq = temp[0] + temp[1] + temp[2] + temp[3];

    if (sum_sq > 1e-24 && !std::isnan(sum_sq)) {
        double inv_norm = 1.0 / std::sqrt(sum_sq);
        __m256d vinv = _mm256_set1_pd(inv_norm);
        for (size_t i = 0; i < CL12_DIMENSION; i += 16) {
            __m256d v0 = _mm256_loadu_pd(blades + i + 0);
            __m256d v1 = _mm256_loadu_pd(blades + i + 4);
            __m256d v2 = _mm256_loadu_pd(blades + i + 8);
            __m256d v3 = _mm256_loadu_pd(blades + i + 12);

            _mm256_storeu_pd(blades + i + 0, _mm256_mul_pd(v0, vinv));
            _mm256_storeu_pd(blades + i + 4, _mm256_mul_pd(v1, vinv));
            _mm256_storeu_pd(blades + i + 8, _mm256_mul_pd(v2, vinv));
            _mm256_storeu_pd(blades + i + 12, _mm256_mul_pd(v3, vinv));
        }
    } else {
        reset();
        blades[0] = 1.0;
    }
#else
    double sum_sq = 0.0;
    for (size_t i = 0; i < CL12_DIMENSION; ++i) {
        double val = latent_h[i];
        if (std::isnan(val) || std::isinf(val)) val = 0.0;
        blades[i] = val;
        sum_sq += val * val;
    }
    if (sum_sq > 1e-24) {
        double inv_norm = 1.0 / std::sqrt(sum_sq);
        for (size_t i = 0; i < CL12_DIMENSION; ++i) blades[i] *= inv_norm;
    } else {
        reset();
        blades[0] = 1.0;
    }
#endif
}

double Cl12Multivector::compute_squared_norm() const noexcept {
#if defined(__AVX2__) && defined(__FMA__)
    __m256d acc0 = _mm256_setzero_pd();
    __m256d acc1 = _mm256_setzero_pd();
    __m256d acc2 = _mm256_setzero_pd();
    __m256d acc3 = _mm256_setzero_pd();

    for (size_t i = 0; i < CL12_DIMENSION; i += 16) {
        __m256d v0 = _mm256_loadu_pd(blades + i + 0);
        __m256d v1 = _mm256_loadu_pd(blades + i + 4);
        __m256d v2 = _mm256_loadu_pd(blades + i + 8);
        __m256d v3 = _mm256_loadu_pd(blades + i + 12);

        acc0 = _mm256_fmadd_pd(v0, v0, acc0);
        acc1 = _mm256_fmadd_pd(v1, v1, acc1);
        acc2 = _mm256_fmadd_pd(v2, v2, acc2);
        acc3 = _mm256_fmadd_pd(v3, v3, acc3);
    }

    __m256d sum_acc = _mm256_add_pd(_mm256_add_pd(acc0, acc1), _mm256_add_pd(acc2, acc3));
    alignas(32) double temp[4];
    _mm256_storeu_pd(temp, sum_acc);
    return temp[0] + temp[1] + temp[2] + temp[3];
#else
    double sum_sq = 0.0;
    for (size_t i = 0; i < CL12_DIMENSION; ++i) {
        sum_sq += blades[i] * blades[i];
    }
    return sum_sq;
#endif
}

void Cl12Multivector::renormalize_in_place() noexcept {
    double sq_norm = compute_squared_norm();
    if (sq_norm > 1e-24 && std::abs(sq_norm - 1.0) > 1e-5) {
        double inv_norm = 1.0 / std::sqrt(sq_norm);
#if defined(__AVX2__)
        __m256d vinv = _mm256_set1_pd(inv_norm);
        for (size_t i = 0; i < CL12_DIMENSION; i += 16) {
            __m256d v0 = _mm256_loadu_pd(blades + i + 0);
            __m256d v1 = _mm256_loadu_pd(blades + i + 4);
            __m256d v2 = _mm256_loadu_pd(blades + i + 8);
            __m256d v3 = _mm256_loadu_pd(blades + i + 12);

            _mm256_storeu_pd(blades + i + 0, _mm256_mul_pd(v0, vinv));
            _mm256_storeu_pd(blades + i + 4, _mm256_mul_pd(v1, vinv));
            _mm256_storeu_pd(blades + i + 8, _mm256_mul_pd(v2, vinv));
            _mm256_storeu_pd(blades + i + 12, _mm256_mul_pd(v3, vinv));
        }
#else
        for (size_t i = 0; i < CL12_DIMENSION; ++i) {
            blades[i] *= inv_norm;
        }
#endif
    }
}

} // namespace vivyqu
