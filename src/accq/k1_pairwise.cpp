// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — K1 vét cạn năng lượng cặp (DFS cộng dồn, duyệt index tăng dần)
#include "vivyqu/accq.h"

#include <cmath>
#include <limits>
#include <vector>

namespace {

struct K1Ctx {
    int n;
    const double* unary;
    const double* pair;
    const uint8_t* forbid;
    std::vector<int> s;      // trạng thái đã gán (site k..n-1)
    std::vector<uint64_t> pw;
    // pass 1
    double best = std::numeric_limits<double>::infinity();
    uint64_t best_idx = 0;
    // pass 2
    double thr = 0;
    uint64_t count = 0;
    double* out = nullptr;
    int pass = 1;
};

// Gán site k (từ n-1 xuống 0). Site n-1 là chữ số có trọng số lớn nhất -> lá được thăm theo index tăng dần,
// so sánh '<' chặt cho tie-break index nhỏ nhất.
void dfs(K1Ctx& c, int k, double partial, uint64_t idx) {
    for (int a = 0; a < ACCQ_STATES; ++a) {
        const uint64_t id = idx + (uint64_t) a * c.pw[k];
        if (c.forbid && c.forbid[k * ACCQ_STATES + a]) continue;  // cấm: E = +inf (đã khởi tạo trong out)
        double e = partial + c.unary[k * ACCQ_STATES + a];
        for (int j = k + 1; j < c.n; ++j) e += c.pair[((size_t) k * c.n + j) * 16 + a * 4 + c.s[j]];
        if (k == 0) {
            if (c.pass == 1) {
                if (e < c.best) { c.best = e; c.best_idx = id; }
                if (c.out) c.out[id] = e;
            } else if (e <= c.thr) {
                ++c.count;
            }
        } else {
            c.s[k] = a;
            dfs(c, k - 1, e, id);
        }
    }
}

bool finite_all(const double* p, size_t m) {
    for (size_t i = 0; i < m; ++i)
        if (!std::isfinite(p[i])) return false;
    return true;
}

}  // namespace

ACCQ_API const char* accq_version() { return "vivyqu_accq 0.1.0 (K1)"; }

ACCQ_API int32_t accq_pairwise_bruteforce(int32_t n, const double* unary, const double* pair, const uint8_t* forbid,
                                          double tol, uint64_t* best_idx, double* best_E, uint64_t* n_ground,
                                          double* energies_out) {
    if (!unary || !pair || !best_idx || !best_E || !n_ground) return ACCQ_ERR_ARG;
    if (n < 1 || n > ACCQ_K1_MAX_SITES) return ACCQ_ERR_SIZE;
    if (!(tol >= 0) || !std::isfinite(tol)) return ACCQ_ERR_ARG;
    if (!finite_all(unary, (size_t) n * 4)) return ACCQ_ERR_NONFINITE;
    for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j)
            if (!finite_all(pair + ((size_t) i * n + j) * 16, 16)) return ACCQ_ERR_NONFINITE;

    K1Ctx c;
    c.n = n;
    c.unary = unary;
    c.pair = pair;
    c.forbid = forbid;
    c.s.assign(n, 0);
    c.pw.resize(n);
    c.pw[0] = 1;
    for (int i = 1; i < n; ++i) c.pw[i] = c.pw[i - 1] * ACCQ_STATES;
    const uint64_t n_cand = c.pw[n - 1] * ACCQ_STATES;
    c.out = energies_out;
    if (energies_out)
        for (uint64_t i = 0; i < n_cand; ++i) energies_out[i] = std::numeric_limits<double>::infinity();

    dfs(c, n - 1, 0.0, 0);
    if (!std::isfinite(c.best)) return ACCQ_ERR_INFEASIBLE;

    c.thr = c.best + tol;
    if (energies_out) {
        uint64_t cnt = 0;
        for (uint64_t i = 0; i < n_cand; ++i) cnt += energies_out[i] <= c.thr;
        c.count = cnt;
    } else {
        c.pass = 2;
        dfs(c, n - 1, 0.0, 0);
    }
    *best_idx = c.best_idx;
    *best_E = c.best;
    *n_ground = c.count;
    return ACCQ_OK;
}
