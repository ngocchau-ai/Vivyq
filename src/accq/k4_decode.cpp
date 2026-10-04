// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — K4 đối chứng cổ điển: Viterbi chuỗi (exact) + beam cặp tổng quát
#include "vivyqu/accq.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace {

constexpr double kInf = std::numeric_limits<double>::infinity();

bool finite_all(const double* p, size_t m) {
    for (size_t i = 0; i < m; ++i)
        if (!std::isfinite(p[i])) return false;
    return true;
}

bool site_dead(const uint8_t* forbid, int i) {
    if (!forbid) return false;
    for (int a = 0; a < ACCQ_STATES; ++a)
        if (!forbid[i * ACCQ_STATES + a]) return false;
    return true;
}

struct Cand {
    double e;
    uint64_t idx;
};

bool cand_less(const Cand& x, const Cand& y) { return x.e < y.e || (x.e == y.e && x.idx < y.idx); }

}  // namespace

ACCQ_API int32_t accq_chain_viterbi(int32_t n, const double* unary, const double* chain, const uint8_t* forbid,
                                    uint64_t* best_idx, double* best_E) {
    if (!unary || !best_idx || !best_E || (n > 1 && !chain)) return ACCQ_ERR_ARG;
    if (n < 1 || n > ACCQ_K4_MAX_SITES) return ACCQ_ERR_SIZE;
    if (!finite_all(unary, (size_t) n * 4) || (n > 1 && !finite_all(chain, (size_t) (n - 1) * 16)))
        return ACCQ_ERR_NONFINITE;
    for (int i = 0; i < n; ++i)
        if (site_dead(forbid, i)) return ACCQ_ERR_INFEASIBLE;

    std::vector<double> V((size_t) n * 4);
    std::vector<uint8_t> bp((size_t) n * 4, 0);
    for (int a = 0; a < 4; ++a) V[a] = (forbid && forbid[a]) ? kInf : unary[a];
    for (int i = 1; i < n; ++i) {
        const double* P = chain + (size_t) (i - 1) * 16;
        for (int b = 0; b < 4; ++b) {
            if (forbid && forbid[i * 4 + b]) { V[i * 4 + b] = kInf; continue; }
            double m = kInf;
            int arg = 0;
            for (int a = 0; a < 4; ++a) {  // '<' chặt, a tăng dần -> tiền nhiệm nhỏ nhất khi hòa
                const double v = V[(i - 1) * 4 + a] + P[a * 4 + b];
                if (v < m) { m = v; arg = a; }
            }
            V[i * 4 + b] = m + unary[i * 4 + b];
            bp[i * 4 + b] = (uint8_t) arg;
        }
    }
    double m = kInf;
    int s = 0;
    for (int b = 0; b < 4; ++b)
        if (V[(n - 1) * 4 + b] < m) { m = V[(n - 1) * 4 + b]; s = b; }
    if (!std::isfinite(m)) return ACCQ_ERR_INFEASIBLE;
    uint64_t idx = 0;
    for (int i = n - 1; i >= 0; --i) {
        idx |= (uint64_t) s << (2 * i);
        if (i > 0) s = bp[i * 4 + s];
    }
    *best_idx = idx;
    *best_E = m;
    return ACCQ_OK;
}

ACCQ_API int32_t accq_pairwise_beam(int32_t n, const double* unary, const double* pair, const uint8_t* forbid,
                                    int32_t beam, uint64_t* best_idx, double* best_E) {
    if (!unary || !pair || !best_idx || !best_E) return ACCQ_ERR_ARG;
    if (n < 1 || n > ACCQ_K4_MAX_SITES) return ACCQ_ERR_SIZE;
    if (beam < 1 || beam > ACCQ_BEAM_MAX) return ACCQ_ERR_SIZE;
    if (!finite_all(unary, (size_t) n * 4)) return ACCQ_ERR_NONFINITE;
    for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j)
            if (!finite_all(pair + ((size_t) i * n + j) * 16, 16)) return ACCQ_ERR_NONFINITE;
    for (int i = 0; i < n; ++i)
        if (site_dead(forbid, i)) return ACCQ_ERR_INFEASIBLE;

    std::vector<Cand> cur{{0.0, 0}}, nxt;
    cur.reserve(beam);
    nxt.reserve((size_t) beam * 4);
    for (int k = 0; k < n; ++k) {
        nxt.clear();
        for (const Cand& c : cur)
            for (int a = 0; a < 4; ++a) {
                if (forbid && forbid[k * 4 + a]) continue;
                double e = c.e + unary[k * 4 + a];
                for (int j = 0; j < k; ++j) {
                    const int sj = (int) ((c.idx >> (2 * j)) & 3);
                    e += pair[((size_t) j * n + k) * 16 + sj * 4 + a];
                }
                nxt.push_back({e, c.idx | ((uint64_t) a << (2 * k))});
            }
        if ((int64_t) nxt.size() > beam) {
            std::nth_element(nxt.begin(), nxt.begin() + beam, nxt.end(), cand_less);
            nxt.resize(beam);
        }
        cur.swap(nxt);
    }
    const Cand best = *std::min_element(cur.begin(), cur.end(), cand_less);
    *best_idx = best.idx;
    *best_E = best.e;
    return ACCQ_OK;
}
