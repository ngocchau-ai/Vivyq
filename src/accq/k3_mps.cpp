// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — K3 MPS Born machine: biên độ, chuẩn (transfer), lấy mẫu chính xác
#include "vivyqu/accq.h"

#include <cmath>
#include <complex>
#include <vector>

using cd = std::complex<double>;

namespace {

struct Mps {
    int n;
    const int32_t* D;
    std::vector<size_t> off;  // offset (theo số phức) của từng site
    const cd* T;
    // A_i[a](l, r)
    const cd& at(int i, int l, int a, int r) const { return T[off[i] + ((size_t) l * 4 + a) * D[i + 1] + r]; }
};

int32_t validate(int32_t n, const int32_t* bonds, const double* t, Mps& m) {
    if (!bonds || !t) return ACCQ_ERR_ARG;
    if (n < 1 || n > ACCQ_MPS_MAX_SITES) return ACCQ_ERR_SIZE;
    if (bonds[0] != 1 || bonds[n] != 1) return ACCQ_ERR_ARG;
    for (int i = 0; i <= n; ++i)
        if (bonds[i] < 1 || bonds[i] > ACCQ_MPS_MAX_BOND) return ACCQ_ERR_SIZE;
    m.n = n;
    m.D = bonds;
    m.off.resize(n + 1);
    m.off[0] = 0;
    for (int i = 0; i < n; ++i) m.off[i + 1] = m.off[i] + (size_t) bonds[i] * 4 * bonds[i + 1];
    for (size_t k = 0; k < 2 * m.off[n]; ++k)
        if (!std::isfinite(t[k])) return ACCQ_ERR_NONFINITE;
    m.T = reinterpret_cast<const cd*>(t);  // std::complex<double> tương thích bố cục double[2]
    return ACCQ_OK;
}

// Môi trường phải: R_n = [1]; R_i (D_i x D_i) = sum_a A_i[a] R_{i+1} A_i[a]^H. Chuẩn hóa từng bước để tránh tràn,
// trả về log của các hệ số chuẩn hóa (cộng dồn) để tính chuẩn tuyệt đối.
double right_envs(const Mps& m, std::vector<std::vector<cd>>& R) {
    R.assign(m.n + 1, {});
    R[m.n] = {cd(1, 0)};
    double logscale = 0;
    for (int i = m.n - 1; i >= 0; --i) {
        const int Dl = m.D[i], Dr = m.D[i + 1];
        std::vector<cd> tmp((size_t) Dl * Dr), out((size_t) Dl * Dl, cd(0, 0));
        for (int a = 0; a < 4; ++a) {
            // tmp = A[a] R_{i+1}  (Dl x Dr)
            for (int l = 0; l < Dl; ++l)
                for (int r = 0; r < Dr; ++r) {
                    cd s(0, 0);
                    for (int k = 0; k < Dr; ++k) s += m.at(i, l, a, k) * R[i + 1][(size_t) k * Dr + r];
                    tmp[(size_t) l * Dr + r] = s;
                }
            // out += tmp A[a]^H
            for (int l = 0; l < Dl; ++l)
                for (int l2 = 0; l2 < Dl; ++l2) {
                    cd s(0, 0);
                    for (int r = 0; r < Dr; ++r) s += tmp[(size_t) l * Dr + r] * std::conj(m.at(i, l2, a, r));
                    out[(size_t) l * Dl + l2] += s;
                }
        }
        double mx = 0;
        for (const cd& x : out) mx = std::max(mx, std::abs(x));
        if (!(mx > 0) || !std::isfinite(mx)) return NAN;
        for (cd& x : out) x /= mx;
        logscale += std::log(mx);
        R[i] = std::move(out);
    }
    return logscale;
}

uint64_t splitmix(uint64_t& x) {
    x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

}  // namespace

ACCQ_API int32_t accq_mps_amplitude(int32_t n, const int32_t* bonds, const double* t, uint64_t idx, double* out) {
    Mps m;
    if (int32_t rc = validate(n, bonds, t, m)) return rc;
    if (!out) return ACCQ_ERR_ARG;
    if (n < 32 && idx >> (2 * n)) return ACCQ_ERR_ARG;
    std::vector<cd> v(1, cd(1, 0)), w;
    for (int i = 0; i < n; ++i) {
        const int a = (int) ((idx >> (2 * i)) & 3), Dl = m.D[i], Dr = m.D[i + 1];
        w.assign(Dr, cd(0, 0));
        for (int l = 0; l < Dl; ++l)
            for (int r = 0; r < Dr; ++r) w[r] += v[l] * m.at(i, l, a, r);
        v.swap(w);
    }
    out[0] = v[0].real();
    out[1] = v[0].imag();
    return ACCQ_OK;
}

ACCQ_API int32_t accq_mps_norm2(int32_t n, const int32_t* bonds, const double* t, double* out) {
    Mps m;
    if (int32_t rc = validate(n, bonds, t, m)) return rc;
    if (!out) return ACCQ_ERR_ARG;
    std::vector<std::vector<cd>> R;
    const double ls = right_envs(m, R);
    if (!std::isfinite(ls)) return ACCQ_ERR_NONFINITE;
    *out = R[0][0].real() * std::exp(ls);
    return ACCQ_OK;
}

ACCQ_API int32_t accq_mps_sample(int32_t n, const int32_t* bonds, const double* t, int32_t K, uint64_t seed,
                                 uint64_t* idx_out, double* logp_out) {
    Mps m;
    if (int32_t rc = validate(n, bonds, t, m)) return rc;
    if (!idx_out || !logp_out || K <= 0) return ACCQ_ERR_ARG;
    std::vector<std::vector<cd>> R;
    if (!std::isfinite(right_envs(m, R))) return ACCQ_ERR_NONFINITE;
    uint64_t rng = seed;
    std::vector<cd> v, cand[4];
    for (int k = 0; k < K; ++k) {
        v.assign(1, cd(1, 0));
        uint64_t idx = 0;
        double logp = 0;
        for (int i = 0; i < n; ++i) {
            const int Dl = m.D[i], Dr = m.D[i + 1];
            double w[4], tot = 0;
            for (int a = 0; a < 4; ++a) {
                cand[a].assign(Dr, cd(0, 0));
                for (int l = 0; l < Dl; ++l)
                    for (int r = 0; r < Dr; ++r) cand[a][r] += v[l] * m.at(i, l, a, r);
                // w_a = cand R_{i+1} cand^H (thực, >= 0 về lý thuyết)
                cd s(0, 0);
                for (int r = 0; r < Dr; ++r)
                    for (int r2 = 0; r2 < Dr; ++r2) s += cand[a][r] * R[i + 1][(size_t) r * Dr + r2] * std::conj(cand[a][r2]);
                w[a] = std::max(0.0, s.real());
                tot += w[a];
            }
            if (!(tot > 0) || !std::isfinite(tot)) return ACCQ_ERR_NONFINITE;
            const double u = (double) (splitmix(rng) >> 11) * (1.0 / 9007199254740992.0) * tot;
            int pick = 3;
            double acc = 0;
            for (int a = 0; a < 4; ++a) {
                acc += w[a];
                if (u < acc) { pick = a; break; }
            }
            while (w[pick] <= 0 && pick > 0) --pick;  // phòng sai số làm tròn ở biên
            logp += std::log(w[pick] / tot);
            idx |= (uint64_t) pick << (2 * i);
            // v = cand[pick] chuẩn hóa (chỉ hướng quan trọng; xác suất điều kiện đã chuẩn hóa theo tot)
            double nv = 0;
            for (const cd& x : cand[pick]) nv = std::max(nv, std::abs(x));
            v.assign(cand[pick].begin(), cand[pick].end());
            for (cd& x : v) x /= nv;
        }
        idx_out[k] = idx;
        logp_out[k] = logp;
    }
    return ACCQ_OK;
}
