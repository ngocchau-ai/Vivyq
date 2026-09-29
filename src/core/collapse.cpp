#include "vivyqu/collapse.h"
#include <cmath>
#include <random>
#include <vector>
#include <immintrin.h>

namespace vivyqu {

DecisionResult CollapseEngine::collapse_hard_masked(
    const Cl12Multivector& __restrict state,
    const uint8_t* __restrict constraint_bitmask
) noexcept {
    DecisionResult result{0, -1.0, 0, false};

    uint32_t best_idx = 0;
    double max_prob = -1.0;
    uint32_t valid_count = 0;

    const uint64_t* mask_u64 = reinterpret_cast<const uint64_t*>(constraint_bitmask);
    constexpr size_t NUM_U64 = CONSTRAINT_MASK_BYTES / sizeof(uint64_t); // 512 / 8 = 64 words

    for (size_t word_idx = 0; word_idx < NUM_U64; ++word_idx) {
        uint64_t word = mask_u64 ? mask_u64[word_idx] : ~0ULL;
        if (word == 0ULL) continue; // Nhảy cóc 64 ứng viên vi phạm trong 1 chu kỳ

        uint32_t base_k = static_cast<uint32_t>(word_idx << 6); // * 64

        // Đường dẫn tối ưu siêu tốc: Cả khối 64 ứng viên đều hợp lệ
        if (word == ~0ULL) {
            valid_count += 64;
            for (uint32_t offset = 0; offset < 64; ++offset) {
                uint32_t k = base_k + offset;
                double val = state.blades[k];
                double prob = val * val;
                if (prob > max_prob) {
                    max_prob = prob;
                    best_idx = k;
                }
            }
            continue;
        }

        // Đường dẫn có ứng viên vi phạm: Duyệt bit bật 1 bằng _tzcnt_u64
        while (word != 0ULL) {
#if defined(__BMI__) || defined(__BMI2__) || defined(_MSC_VER)
            uint32_t bit_pos = static_cast<uint32_t>(_tzcnt_u64(word));
#else
            uint32_t bit_pos = static_cast<uint32_t>(__builtin_ctzll(word));
#endif
            uint32_t k = base_k + bit_pos;
            double val = state.blades[k];
            double prob = val * val;
            valid_count++;

            if (prob > max_prob) {
                max_prob = prob;
                best_idx = k;
            }

            word &= (word - 1ULL);
        }
    }

    if (valid_count > 0) {
        result.best_index = best_idx;
        result.confidence = max_prob;
        result.valid_count = valid_count;
        result.is_valid = true;
    } else {
        result.best_index = 0;
        result.confidence = 0.0;
        result.valid_count = 0;
        result.is_valid = false;
    }

    return result;
}

DecisionResult CollapseEngine::collapse_born_sampled(
    const Cl12Multivector& __restrict state,
    const uint8_t* __restrict constraint_bitmask,
    float temperature,
    uint64_t seed
) noexcept {
    DecisionResult result{0, 0.0, 0, false};
    float temp = (temperature > 0.001f) ? temperature : 1.0f;
    double inv_temp = 1.0 / static_cast<double>(temp);

    std::vector<double> probs;
    std::vector<uint32_t> valid_indices;
    probs.reserve(CL12_DIMENSION);
    valid_indices.reserve(CL12_DIMENSION);

    const uint64_t* mask_u64 = reinterpret_cast<const uint64_t*>(constraint_bitmask);
    constexpr size_t NUM_U64 = CONSTRAINT_MASK_BYTES / sizeof(uint64_t);

    double sum_p = 0.0;
    for (size_t word_idx = 0; word_idx < NUM_U64; ++word_idx) {
        uint64_t word = mask_u64 ? mask_u64[word_idx] : ~0ULL;
        if (word == 0ULL) continue;

        uint32_t base_k = static_cast<uint32_t>(word_idx << 6);
        while (word != 0ULL) {
#if defined(__BMI__) || defined(__BMI2__) || defined(_MSC_VER)
            uint32_t bit_pos = static_cast<uint32_t>(_tzcnt_u64(word));
#else
            uint32_t bit_pos = static_cast<uint32_t>(__builtin_ctzll(word));
#endif
            uint32_t k = base_k + bit_pos;
            double val = state.blades[k];
            double p_raw = val * val;
            double p_scaled = std::pow(p_raw + 1e-12, inv_temp);
            probs.push_back(p_scaled);
            valid_indices.push_back(k);
            sum_p += p_scaled;

            word &= (word - 1ULL);
        }
    }

    if (valid_indices.empty() || sum_p <= 0.0) {
        return collapse_hard_masked(state, constraint_bitmask);
    }

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> dist(0.0, sum_p);
    double target = dist(rng);

    double accum = 0.0;
    for (size_t i = 0; i < probs.size(); ++i) {
        accum += probs[i];
        if (accum >= target) {
            result.best_index = valid_indices[i];
            result.confidence = state.blades[valid_indices[i]] * state.blades[valid_indices[i]];
            result.valid_count = static_cast<uint32_t>(valid_indices.size());
            result.is_valid = true;
            return result;
        }
    }

    result.best_index = valid_indices.back();
    result.confidence = state.blades[result.best_index] * state.blades[result.best_index];
    result.valid_count = static_cast<uint32_t>(valid_indices.size());
    result.is_valid = true;
    return result;
}

} // namespace vivyqu
