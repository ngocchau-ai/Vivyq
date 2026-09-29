#include "vivyqu/geometric_scorer.h"
#include <cstdio>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <immintrin.h>

namespace vivyqu {

namespace {

// Helper cộng ngang 8 floats trong thanh ghi __m256 cực nhanh
inline float hsum256_ps(__m256 v) noexcept {
    __m128 vlow = _mm256_castps256_ps128(v);
    __m128 vhigh = _mm256_extractf128_ps(v, 1);
    __m128 vsum = _mm_add_ps(vlow, vhigh);
    __m128 shuf = _mm_movehl_ps(vsum, vsum);
    __m128 sums = _mm_add_ps(vsum, shuf);
    __m128 shuf2 = _mm_shuffle_ps(sums, sums, 1);
    __m128 final_sum = _mm_add_ss(sums, shuf2);
    return _mm_cvtss_f32(final_sum);
}

// Cập nhật mảng Top-8 ứng viên một cách tối ưu với ngưỡng min_val
inline void update_top_candidates(
    CandidateScore* top_arr,
    size_t max_m,
    uint32_t cand_idx,
    float score,
    float& min_val
) noexcept {
    if (!top_arr || max_m == 0 || score <= min_val) return;

    size_t min_pos = 0;
    float current_min = top_arr[0].confidence;
    for (size_t i = 1; i < max_m; ++i) {
        if (top_arr[i].confidence < current_min) {
            current_min = top_arr[i].confidence;
            min_pos = i;
        }
    }

    if (score > current_min) {
        top_arr[min_pos].candidate_idx = cand_idx;
        top_arr[min_pos].confidence = score;

        float new_min = top_arr[0].confidence;
        for (size_t i = 1; i < max_m; ++i) {
            if (top_arr[i].confidence < new_min) {
                new_min = top_arr[i].confidence;
            }
        }
        min_val = new_min;
    }
}

} // anonymous namespace

void GeometricWeights::reset() noexcept {
    std::memset(W_c, 0, sizeof(W_c));
    std::memset(candidate_codebook, 0, sizeof(candidate_codebook));
    std::memset(topology_cost, 0, sizeof(topology_cost));
    std::memset(effective_cost, 0, sizeof(effective_cost));
    std::memset(default_rotors, 0, sizeof(default_rotors));
    std::memset(rotor_pairs, 0, sizeof(rotor_pairs));
    topology_lambda = 0.3f;
    is_loaded = false;
}

void GeometricWeights::precompute_rotors() noexcept {
    for (size_t m = 0; m < E9_NUM_ROTORS; ++m) {
        const auto& r = default_rotors[m];
        uint32_t pi = r.plane_i;
        uint32_t pj = r.plane_j;
        float th = r.angle_theta;

        if (pi >= 12 || pj >= 12 || pi == pj) {
            std::memset(&rotor_pairs[m], 0, sizeof(RotorPairIndices));
            rotor_pairs[m].cos_th = 1.0f;
            rotor_pairs[m].sin_th = 0.0f;
            continue;
        }

        uint32_t bit_i = 1u << std::min(pi, pj);
        uint32_t bit_j = 1u << std::max(pi, pj);
        uint32_t mask_pair = bit_i | bit_j;
        uint32_t free_mask = (~mask_pair) & 0x0FFFu;

        for (uint32_t k = 0; k < 1024; ++k) {
#if defined(__BMI2__) || defined(_MSC_VER)
            uint32_t base = _pdep_u32(k, free_mask);
#else
            uint32_t base = 0;
            uint32_t m_temp = free_mask;
            uint32_t k_temp = k;
            while (m_temp) {
                uint32_t lsb = m_temp & -m_temp;
                if (k_temp & 1) base |= lsb;
                k_temp >>= 1;
                m_temp &= m_temp - 1;
            }
#endif
            rotor_pairs[m].a[k] = static_cast<uint16_t>(base | bit_i);
            rotor_pairs[m].b[k] = static_cast<uint16_t>(base | bit_j);
        }

        rotor_pairs[m].cos_th = std::cos(th);
        rotor_pairs[m].sin_th = std::sin(th);
    }

    // Tiền tính toán bảng chi phí hiệu dụng 0.3 * cost
    for (size_t k = 0; k < CL12_DIMENSION; ++k) {
        effective_cost[k] = topology_lambda * topology_cost[k];
    }
}

bool GeometricWeights::load_from_binary(const char* filepath) noexcept {
    if (!filepath) return false;

    FILE* f = std::fopen(filepath, "rb");
    if (!f) return false;

    // 1. Đọc Header 64 bytes
    struct Header {
        uint64_t magic;
        uint32_t version;
        uint32_t cl12_dim;
        uint32_t subspace_dim;
        uint32_t num_rotors;
        float    topology_lambda;
        uint8_t  padding[36];
    } hdr;

    if (std::fread(&hdr, 1, sizeof(Header), f) != sizeof(Header)) {
        std::fclose(f);
        return false;
    }

    if (hdr.magic != E9_MAGIC || hdr.version != E9_VERSION ||
        hdr.cl12_dim != CL12_DIMENSION || hdr.subspace_dim != E9_SUBSPACE_DIM ||
        hdr.num_rotors != E9_NUM_ROTORS) {
        std::fclose(f);
        return false;
    }

    topology_lambda = hdr.topology_lambda;

    // 2. Đọc 8 Rotors (64 bytes)
    if (std::fread(default_rotors, sizeof(RotorConfig), E9_NUM_ROTORS, f) != E9_NUM_ROTORS) {
        std::fclose(f);
        return false;
    }

    // 3. Đọc W_c (1.048.576 bytes)
    size_t wc_floats = E9_SUBSPACE_DIM * CL12_DIMENSION;
    if (std::fread(W_c, sizeof(float), wc_floats, f) != wc_floats) {
        std::fclose(f);
        return false;
    }

    // 4. Đọc candidate_codebook (1.048.576 bytes)
    size_t cb_floats = CL12_DIMENSION * E9_SUBSPACE_DIM;
    if (std::fread(candidate_codebook, sizeof(float), cb_floats, f) != cb_floats) {
        std::fclose(f);
        return false;
    }

    // 5. Đọc topology_cost (16.384 bytes)
    if (std::fread(topology_cost, sizeof(float), CL12_DIMENSION, f) != CL12_DIMENSION) {
        std::fclose(f);
        return false;
    }

    std::fclose(f);

    precompute_rotors();
    is_loaded = true;
    return true;
}

void GeometricScorer::apply_rotors_f32(
    float* __restrict h_rot,
    const RotorPairIndices* __restrict pairs,
    size_t num_rotors
) noexcept {
    for (size_t m = 0; m < num_rotors; ++m) {
        const auto& r = pairs[m];
        float c = r.cos_th;
        float s = r.sin_th;

        // Unroll 4x để khai thác song song ILP (Instruction-Level Parallelism)
        for (size_t k = 0; k < 1024; k += 4) {
            uint16_t a0 = r.a[k + 0], b0 = r.b[k + 0];
            uint16_t a1 = r.a[k + 1], b1 = r.b[k + 1];
            uint16_t a2 = r.a[k + 2], b2 = r.b[k + 2];
            uint16_t a3 = r.a[k + 3], b3 = r.b[k + 3];

            float va0 = h_rot[a0], vb0 = h_rot[b0];
            float va1 = h_rot[a1], vb1 = h_rot[b1];
            float va2 = h_rot[a2], vb2 = h_rot[b2];
            float va3 = h_rot[a3], vb3 = h_rot[b3];

            h_rot[a0] = c * va0 - s * vb0;
            h_rot[b0] = s * va0 + c * vb0;
            h_rot[a1] = c * va1 - s * vb1;
            h_rot[b1] = s * va1 + c * vb1;
            h_rot[a2] = c * va2 - s * vb2;
            h_rot[b2] = s * va2 + c * vb2;
            h_rot[a3] = c * va3 - s * vb3;
            h_rot[b3] = s * va3 + c * vb3;
        }
    }
}

void GeometricScorer::project_subspace_64x4096(
    float* __restrict z_out,
    const float* __restrict W_c,
    const float* __restrict h_rot
) noexcept {
    for (size_t i = 0; i < E9_SUBSPACE_DIM; i += 2) {
        const float* __restrict w_row0 = W_c + (i + 0) * CL12_DIMENSION;
        const float* __restrict w_row1 = W_c + (i + 1) * CL12_DIMENSION;
        __m256 acc0_0 = _mm256_setzero_ps();
        __m256 acc0_1 = _mm256_setzero_ps();
        __m256 acc1_0 = _mm256_setzero_ps();
        __m256 acc1_1 = _mm256_setzero_ps();

        for (size_t j = 0; j < CL12_DIMENSION; j += 16) {
            __m256 h0 = _mm256_loadu_ps(h_rot + j + 0);
            __m256 h1 = _mm256_loadu_ps(h_rot + j + 8);

            __m256 w0_0 = _mm256_loadu_ps(w_row0 + j + 0);
            __m256 w0_1 = _mm256_loadu_ps(w_row0 + j + 8);
            acc0_0 = _mm256_fmadd_ps(w0_0, h0, acc0_0);
            acc0_1 = _mm256_fmadd_ps(w0_1, h1, acc0_1);

            __m256 w1_0 = _mm256_loadu_ps(w_row1 + j + 0);
            __m256 w1_1 = _mm256_loadu_ps(w_row1 + j + 8);
            acc1_0 = _mm256_fmadd_ps(w1_0, h0, acc1_0);
            acc1_1 = _mm256_fmadd_ps(w1_1, h1, acc1_1);
        }

        z_out[i + 0] = hsum256_ps(_mm256_add_ps(acc0_0, acc0_1));
        z_out[i + 1] = hsum256_ps(_mm256_add_ps(acc1_0, acc1_1));
    }
}

DecisionResult GeometricScorer::score_candidates_masked_argmax(
    const float* __restrict codebook,
    const float* __restrict z_subspace,
    const float* __restrict effective_cost,
    const uint8_t* __restrict constraint_bitmask,
    CandidateScore* __restrict top_candidates,
    size_t max_top_candidates
) noexcept {
    DecisionResult res{0, -1e30, 0, false};
    float min_top_score = -1e30f;

    // Khởi tạo top_candidates nếu được yêu cầu
    if (top_candidates && max_top_candidates > 0) {
        for (size_t i = 0; i < max_top_candidates; ++i) {
            top_candidates[i].candidate_idx = 0;
            top_candidates[i].confidence = -1e30f;
        }
    }

    // Giữ nguyên toàn bộ 64 floats của vector z trong 8 thanh ghi YMM suốt quá trình duyệt
    __m256 z0 = _mm256_loadu_ps(z_subspace + 0);
    __m256 z1 = _mm256_loadu_ps(z_subspace + 8);
    __m256 z2 = _mm256_loadu_ps(z_subspace + 16);
    __m256 z3 = _mm256_loadu_ps(z_subspace + 24);
    __m256 z4 = _mm256_loadu_ps(z_subspace + 32);
    __m256 z5 = _mm256_loadu_ps(z_subspace + 40);
    __m256 z6 = _mm256_loadu_ps(z_subspace + 48);
    __m256 z7 = _mm256_loadu_ps(z_subspace + 56);

    const uint64_t* mask_u64 = reinterpret_cast<const uint64_t*>(constraint_bitmask);
    constexpr size_t NUM_U64 = CONSTRAINT_MASK_BYTES / sizeof(uint64_t); // 64 words

    uint32_t best_k = 0;
    float max_score = -1e30f;
    uint32_t valid_count = 0;

    for (size_t word_idx = 0; word_idx < NUM_U64; ++word_idx) {
        uint64_t word = mask_u64 ? mask_u64[word_idx] : ~0ULL;
        if (word == 0ULL) continue; // Nhảy cóc 64 ứng viên vi phạm trong 1 cycle

        uint32_t base_k = static_cast<uint32_t>(word_idx << 6);

        // Trường hợp tối ưu tuyệt đối: Cả khối 64 ứng viên đều hợp lệ
        if (word == ~0ULL) {
            valid_count += 64;
            for (uint32_t offset = 0; offset < 64; ++offset) {
                uint32_t k = base_k + offset;
                const float* c_k = codebook + (k << 6); // k * 64

                __m256 acc0 = _mm256_mul_ps(_mm256_loadu_ps(c_k + 0), z0);
                __m256 acc1 = _mm256_mul_ps(_mm256_loadu_ps(c_k + 8), z1);
                acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 16), z2, acc0);
                acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 24), z3, acc1);
                acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 32), z4, acc0);
                acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 40), z5, acc1);
                acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 48), z6, acc0);
                acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 56), z7, acc1);

                float dot = hsum256_ps(_mm256_add_ps(acc0, acc1));
                float score = dot - effective_cost[k];

                if (score > max_score) {
                    max_score = score;
                    best_k = k;
                }

                if (score > min_top_score) {
                    update_top_candidates(top_candidates, max_top_candidates, k, score, min_top_score);
                }
            }
            continue;
        }

        // Trường hợp có ứng viên vi phạm: Duyệt bit 1 bằng _tzcnt_u64
        while (word != 0ULL) {
#if defined(__BMI__) || defined(__BMI2__) || defined(_MSC_VER)
            uint32_t bit_pos = static_cast<uint32_t>(_tzcnt_u64(word));
#else
            uint32_t bit_pos = static_cast<uint32_t>(__builtin_ctzll(word));
#endif
            uint32_t k = base_k + bit_pos;
            const float* c_k = codebook + (k << 6); // k * 64

            __m256 acc0 = _mm256_mul_ps(_mm256_loadu_ps(c_k + 0), z0);
            __m256 acc1 = _mm256_mul_ps(_mm256_loadu_ps(c_k + 8), z1);
            acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 16), z2, acc0);
            acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 24), z3, acc1);
            acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 32), z4, acc0);
            acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 40), z5, acc1);
            acc0 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 48), z6, acc0);
            acc1 = _mm256_fmadd_ps(_mm256_loadu_ps(c_k + 56), z7, acc1);

            float dot = hsum256_ps(_mm256_add_ps(acc0, acc1));
            float score = dot - effective_cost[k];

            valid_count++;
            if (score > max_score) {
                max_score = score;
                best_k = k;
            }

            if (score > min_top_score) {
                update_top_candidates(top_candidates, max_top_candidates, k, score, min_top_score);
            }

            word &= (word - 1ULL);
        }
    }

    if (valid_count > 0) {
        res.best_index = best_k;
        res.confidence = static_cast<double>(max_score);
        res.valid_count = valid_count;
        res.is_valid = true;
    } else {
        res.best_index = 0;
        res.confidence = -1.0;
        res.valid_count = 0;
        res.is_valid = false;
    }

    return res;
}

DecisionResult GeometricScorer::score_and_collapse(
    const GeometricWeights& weights,
    const double* __restrict latent_h,
    const uint8_t* __restrict constraint_bitmask,
    const RotorConfig* __restrict custom_rotors,
    size_t custom_rotors_count,
    CandidateScore* __restrict top_candidates,
    size_t max_top_candidates
) noexcept {
    if (!weights.is_loaded) {
        DecisionResult failed{0, -1.0, 0, false};
        return failed;
    }

    // 1. Chuyển đổi an toàn từ double sang float trong buffer căn lề 64-byte
    alignas(64) float h_buf[CL12_DIMENSION];
    alignas(64) float z_subspace[E9_SUBSPACE_DIM];

    for (size_t i = 0; i < CL12_DIMENSION; i += 8) {
        __m256d d0 = _mm256_loadu_pd(latent_h + i + 0);
        __m256d d1 = _mm256_loadu_pd(latent_h + i + 4);
        __m128 f0 = _mm256_cvtpd_ps(d0);
        __m128 f1 = _mm256_cvtpd_ps(d1);
        _mm_storeu_ps(h_buf + i + 0, f0);
        _mm_storeu_ps(h_buf + i + 4, f1);
    }

    // 2. Áp dụng Rotor nhân tử (Givens Cl(12))
    if (custom_rotors && custom_rotors_count > 0) {
        // Tùy biến rotor động nếu có cấu hình từ input
        RotorPairIndices temp_pairs[MAX_ACTIVE_ROTORS];
        size_t m_count = std::min(custom_rotors_count, MAX_ACTIVE_ROTORS);
        for (size_t m = 0; m < m_count; ++m) {
            const auto& r = custom_rotors[m];
            uint32_t pi = r.plane_i;
            uint32_t pj = r.plane_j;
            float th = r.angle_theta;
            // Guard plane indices — same contract as precompute_rotors (audit 29/09 P0).
            // plane_i/plane_j are uint8 from ABI; without this, 1u<<pi can index far past h_buf[4096].
            if (pi >= 12 || pj >= 12 || pi == pj) {
                std::memset(&temp_pairs[m], 0, sizeof(RotorPairIndices));
                temp_pairs[m].cos_th = 1.0f;
                temp_pairs[m].sin_th = 0.0f;
                continue;
            }
            uint32_t bit_i = 1u << std::min(pi, pj);
            uint32_t bit_j = 1u << std::max(pi, pj);
            uint32_t free_mask = (~(bit_i | bit_j)) & 0x0FFFu;

            for (uint32_t k = 0; k < 1024; ++k) {
#if defined(__BMI2__) || defined(_MSC_VER)
                uint32_t base = _pdep_u32(k, free_mask);
#else
                uint32_t base = 0;
                uint32_t m_temp = free_mask;
                uint32_t k_temp = k;
                while (m_temp) {
                    uint32_t lsb = m_temp & -m_temp;
                    if (k_temp & 1) base |= lsb;
                    k_temp >>= 1;
                    m_temp &= m_temp - 1;
                }
#endif
                temp_pairs[m].a[k] = static_cast<uint16_t>(base | bit_i);
                temp_pairs[m].b[k] = static_cast<uint16_t>(base | bit_j);
            }
            temp_pairs[m].cos_th = std::cos(th);
            temp_pairs[m].sin_th = std::sin(th);
        }
        apply_rotors_f32(h_buf, temp_pairs, m_count);
    } else {
        // Sử dụng bảng tra cứu 8 rotor đã tiền tính toán của Branch C
        apply_rotors_f32(h_buf, weights.rotor_pairs, E9_NUM_ROTORS);
    }

    // 3. Chiếu sang không gian con 64 chiều: z = W_c * R(h)
    project_subspace_64x4096(z_subspace, weights.W_c, h_buf);

    // 4. Chấm điểm 4.096 ứng viên & sụp đổ chọn k*
    return score_candidates_masked_argmax(
        weights.candidate_codebook,
        z_subspace,
        weights.effective_cost,
        constraint_bitmask,
        top_candidates,
        max_top_candidates
    );
}

void GeometricWeights::update_rotor_angle(size_t rotor_idx, float delta_theta) noexcept {
    if (rotor_idx >= E9_NUM_ROTORS) return;
    default_rotors[rotor_idx].angle_theta += delta_theta;
    rotor_pairs[rotor_idx].cos_th = std::cos(default_rotors[rotor_idx].angle_theta);
    rotor_pairs[rotor_idx].sin_th = std::sin(default_rotors[rotor_idx].angle_theta);
}

void GeometricWeights::set_rotor_angle(size_t rotor_idx, float theta) noexcept {
    if (rotor_idx >= E9_NUM_ROTORS) return;
    default_rotors[rotor_idx].angle_theta = theta;
    rotor_pairs[rotor_idx].cos_th = std::cos(theta);
    rotor_pairs[rotor_idx].sin_th = std::sin(theta);
}

void GeometricScorer::backproject_subspace_transpose(
    float* __restrict grad_h_rot,
    const float* __restrict W_c,
    const float* __restrict grad_z
) noexcept {
    std::memset(grad_h_rot, 0, CL12_DIMENSION * sizeof(float));

    for (size_t r = 0; r < E9_SUBSPACE_DIM; r += 4) {
        __m256 gz0 = _mm256_set1_ps(grad_z[r + 0]);
        __m256 gz1 = _mm256_set1_ps(grad_z[r + 1]);
        __m256 gz2 = _mm256_set1_ps(grad_z[r + 2]);
        __m256 gz3 = _mm256_set1_ps(grad_z[r + 3]);

        const float* w0 = W_c + (r + 0) * CL12_DIMENSION;
        const float* w1 = W_c + (r + 1) * CL12_DIMENSION;
        const float* w2 = W_c + (r + 2) * CL12_DIMENSION;
        const float* w3 = W_c + (r + 3) * CL12_DIMENSION;

        for (size_t c = 0; c < CL12_DIMENSION; c += 16) {
            __m256 ghA = _mm256_loadu_ps(grad_h_rot + c);
            __m256 ghB = _mm256_loadu_ps(grad_h_rot + c + 8);

            ghA = _mm256_fmadd_ps(_mm256_loadu_ps(w0 + c), gz0, ghA);
            ghB = _mm256_fmadd_ps(_mm256_loadu_ps(w0 + c + 8), gz0, ghB);

            ghA = _mm256_fmadd_ps(_mm256_loadu_ps(w1 + c), gz1, ghA);
            ghB = _mm256_fmadd_ps(_mm256_loadu_ps(w1 + c + 8), gz1, ghB);

            ghA = _mm256_fmadd_ps(_mm256_loadu_ps(w2 + c), gz2, ghA);
            ghB = _mm256_fmadd_ps(_mm256_loadu_ps(w2 + c + 8), gz2, ghB);

            ghA = _mm256_fmadd_ps(_mm256_loadu_ps(w3 + c), gz3, ghA);
            ghB = _mm256_fmadd_ps(_mm256_loadu_ps(w3 + c + 8), gz3, ghB);

            _mm256_storeu_ps(grad_h_rot + c, ghA);
            _mm256_storeu_ps(grad_h_rot + c + 8, ghB);
        }
    }
}


void GeometricScorer::compute_rotor_torques(
    const GeometricWeights& weights,
    const float* __restrict h_rot,
    const float* __restrict grad_h_rot,
    float* __restrict out_torques
) noexcept {
    for (size_t m = 0; m < E9_NUM_ROTORS; ++m) {
        const auto& rp = weights.rotor_pairs[m];
        float torque_sum = 0.0f;

        // Tích tụ moment lực bivector: sum_{k=0..1023} (g_b * h_a - g_a * h_b)
        for (size_t k = 0; k < 1024; ++k) {
            uint16_t a_idx = rp.a[k];
            uint16_t b_idx = rp.b[k];
            float ha = h_rot[a_idx];
            float hb = h_rot[b_idx];
            float ga = grad_h_rot[a_idx];
            float gb = grad_h_rot[b_idx];
            torque_sum += (gb * ha - ga * hb);
        }
        out_torques[m] = torque_sum;
    }
}

float GeometricScorer::adapt_torque_step(
    GeometricWeights& weights,
    const double* __restrict latent_h,
    uint32_t chosen_k,
    uint32_t target_k,
    float learning_rate,
    float* __restrict out_torques
) noexcept {
    if (!latent_h || chosen_k >= CL12_DIMENSION || target_k >= CL12_DIMENSION) return 0.0f;
    if (chosen_k == target_k) return 0.0f;

    alignas(32) float h_buf[CL12_DIMENSION];
    alignas(32) float grad_h_rot[CL12_DIMENSION];
    alignas(32) float z_subspace[E9_SUBSPACE_DIM];
    alignas(32) float grad_z[E9_SUBSPACE_DIM];
    float local_torques[E9_NUM_ROTORS];

    // 1. Chuyển float64 -> float32 và chuẩn hóa L2
    double sum_sq = 0.0;
    for (size_t i = 0; i < CL12_DIMENSION; ++i) {
        sum_sq += latent_h[i] * latent_h[i];
    }
    float inv_norm = (sum_sq > 1e-12) ? static_cast<float>(1.0 / std::sqrt(sum_sq)) : 1.0f;
    for (size_t i = 0; i < CL12_DIMENSION; ++i) {
        h_buf[i] = static_cast<float>(latent_h[i]) * inv_norm;
    }

    // 2. Quay Spin(12) qua 8 rotors hiện tại
    apply_rotors_f32(h_buf, weights.rotor_pairs, E9_NUM_ROTORS);

    // 3. Chiếu sang không gian con 64 chiều
    project_subspace_64x4096(z_subspace, weights.W_c, h_buf);

    // 4. Tính toán gradient trong không gian con:
    // grad_z = codebook[chosen_k] - codebook[target_k]
    const float* cb_chosen = weights.candidate_codebook + chosen_k * E9_SUBSPACE_DIM;
    const float* cb_target = weights.candidate_codebook + target_k * E9_SUBSPACE_DIM;

    float score_chosen = 0.0f;
    float score_target = 0.0f;
    for (size_t d = 0; d < E9_SUBSPACE_DIM; ++d) {
        score_chosen += cb_chosen[d] * z_subspace[d];
        score_target += cb_target[d] * z_subspace[d];
        grad_z[d] = cb_chosen[d] - cb_target[d];
    }
    score_chosen -= weights.effective_cost[chosen_k];
    score_target -= weights.effective_cost[target_k];

    float margin_loss = std::max(0.0f, score_chosen - score_target);

    // 5. Chiếu ngược gradient: grad_h_rot = W_c^T * grad_z
    backproject_subspace_transpose(grad_h_rot, weights.W_c, grad_z);

    // 6. Tính toán moment lực bivector torque trên 8 rotors
    compute_rotor_torques(weights, h_buf, grad_h_rot, local_torques);

    if (out_torques) {
        for (size_t m = 0; m < E9_NUM_ROTORS; ++m) {
            out_torques[m] = local_torques[m];
        }
    }

    // 7. Cập nhật góc quay rotor: theta_m -= lr * Torque_m
    for (size_t m = 0; m < E9_NUM_ROTORS; ++m) {
        float delta_th = -learning_rate * local_torques[m];
        // Kẹp delta_th trong ngưỡng [-0.1, 0.1] rad để ổn định số học
        delta_th = std::max(-0.1f, std::min(0.1f, delta_th));
        weights.update_rotor_angle(m, delta_th);
    }

    return margin_loss;
}

} // namespace vivyqu
