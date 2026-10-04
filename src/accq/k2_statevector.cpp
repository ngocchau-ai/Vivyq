// Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — K2 statevector qudit-4 (complex128, bản kiểm chứng đúng trước tối ưu)
#include "vivyqu/accq.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <new>
#include <numeric>
#include <vector>

using cd = std::complex<double>;

struct AccqSV {
    int n;
    uint64_t dim;
    std::vector<uint64_t> pw;
    std::vector<cd> a;
};

namespace {

bool finite_n(const double* p, size_t m) {
    for (size_t i = 0; i < m; ++i)
        if (!std::isfinite(p[i])) return false;
    return true;
}

}  // namespace

ACCQ_API int32_t accq_sv_create(int32_t n, AccqSV** out) {
    if (!out) return ACCQ_ERR_ARG;
    *out = nullptr;
    if (n < 1 || n > ACCQ_SV_MAX_SITES) return ACCQ_ERR_SIZE;
    auto* sv = new (std::nothrow) AccqSV;
    if (!sv) return ACCQ_ERR_ALLOC;
    sv->n = n;
    sv->pw.resize(n + 1);
    sv->pw[0] = 1;
    for (int i = 1; i <= n; ++i) sv->pw[i] = sv->pw[i - 1] * ACCQ_STATES;
    sv->dim = sv->pw[n];
    try {
        sv->a.assign(sv->dim, cd(0, 0));
    } catch (...) {
        delete sv;
        return ACCQ_ERR_ALLOC;
    }
    sv->a[0] = 1.0;
    *out = sv;
    return ACCQ_OK;
}

ACCQ_API void accq_sv_destroy(AccqSV* sv) { delete sv; }

ACCQ_API int32_t accq_sv_reset(AccqSV* sv) {
    if (!sv) return ACCQ_ERR_ARG;
    std::fill(sv->a.begin(), sv->a.end(), cd(0, 0));
    sv->a[0] = 1.0;
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_set(AccqSV* sv, const double* amp, uint64_t len) {
    if (!sv || !amp) return ACCQ_ERR_ARG;
    if (len != sv->dim) return ACCQ_ERR_SIZE;
    if (!finite_n(amp, 2 * len)) return ACCQ_ERR_NONFINITE;
    for (uint64_t i = 0; i < len; ++i) sv->a[i] = cd(amp[2 * i], amp[2 * i + 1]);
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_get(const AccqSV* sv, double* amp, uint64_t len) {
    if (!sv || !amp) return ACCQ_ERR_ARG;
    if (len != sv->dim) return ACCQ_ERR_SIZE;
    for (uint64_t i = 0; i < len; ++i) {
        amp[2 * i] = sv->a[i].real();
        amp[2 * i + 1] = sv->a[i].imag();
    }
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_apply1(AccqSV* sv, int32_t site, const double* u) {
    if (!sv || !u) return ACCQ_ERR_ARG;
    if (site < 0 || site >= sv->n) return ACCQ_ERR_ARG;
    if (!finite_n(u, 32)) return ACCQ_ERR_NONFINITE;
    cd U[16];
    for (int i = 0; i < 16; ++i) U[i] = cd(u[2 * i], u[2 * i + 1]);
    const uint64_t st = sv->pw[site], block = st * 4;
    for (uint64_t base = 0; base < sv->dim; base += block)
        for (uint64_t off = 0; off < st; ++off) {
            const uint64_t i0 = base + off;
            const cd x0 = sv->a[i0], x1 = sv->a[i0 + st], x2 = sv->a[i0 + 2 * st], x3 = sv->a[i0 + 3 * st];
            for (int r = 0; r < 4; ++r)
                sv->a[i0 + r * st] = U[r * 4] * x0 + U[r * 4 + 1] * x1 + U[r * 4 + 2] * x2 + U[r * 4 + 3] * x3;
        }
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_apply2(AccqSV* sv, int32_t sa, int32_t sb, const double* u) {
    if (!sv || !u) return ACCQ_ERR_ARG;
    if (sa < 0 || sb < 0 || sa >= sv->n || sb >= sv->n || sa == sb) return ACCQ_ERR_ARG;
    if (!finite_n(u, 512)) return ACCQ_ERR_NONFINITE;
    std::vector<cd> U(256);
    for (int i = 0; i < 256; ++i) U[i] = cd(u[2 * i], u[2 * i + 1]);
    const uint64_t pa = sv->pw[sa], pb = sv->pw[sb];
    uint64_t off[16];
    for (int x = 0; x < 4; ++x)
        for (int y = 0; y < 4; ++y) off[x * 4 + y] = x * pa + y * pb;
    cd v[16];
    // Mỗi chữ số base-4 = 2 bit -> cơ sở có s_a = s_b = 0 sinh bằng cách chèn 2 bit 0 tại vị trí thấp rồi cao.
    const int lo = std::min(sa, sb), hi = std::max(sa, sb);
    auto ins = [](uint64_t x, int digit) {
        const int b = 2 * digit;
        return ((x >> b) << (b + 2)) | (x & ((1ULL << b) - 1));
    };
    const uint64_t n_base = sv->dim / 16;
    for (uint64_t t0 = 0; t0 < n_base; ++t0) {
        const uint64_t i = ins(ins(t0, lo), hi);
        for (int t = 0; t < 16; ++t) v[t] = sv->a[i + off[t]];
        for (int r = 0; r < 16; ++r) {
            cd acc(0, 0);
            for (int c = 0; c < 16; ++c) acc += U[r * 16 + c] * v[c];
            sv->a[i + off[r]] = acc;
        }
    }
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_norm2(const AccqSV* sv, double* out) {
    if (!sv || !out) return ACCQ_ERR_ARG;
    double s = 0;
    for (const cd& x : sv->a) s += std::norm(x);
    *out = s;
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_probs(const AccqSV* sv, double* probs, uint64_t len) {
    if (!sv || !probs) return ACCQ_ERR_ARG;
    if (len != sv->dim) return ACCQ_ERR_SIZE;
    for (uint64_t i = 0; i < len; ++i) probs[i] = std::norm(sv->a[i]);
    return ACCQ_OK;
}

ACCQ_API int32_t accq_sv_topk(const AccqSV* sv, const uint8_t* mask, int32_t k, uint64_t* idx, double* prob,
                              int32_t* k_out) {
    if (!sv || !idx || !prob || !k_out || k <= 0) return ACCQ_ERR_ARG;
    std::vector<uint64_t> cand;
    cand.reserve(mask ? 1024 : sv->dim);
    for (uint64_t i = 0; i < sv->dim; ++i)
        if (!mask || mask[i]) cand.push_back(i);
    const size_t kk = std::min<size_t>((size_t) k, cand.size());
    auto better = [&](uint64_t x, uint64_t y) {
        const double px = std::norm(sv->a[x]), py = std::norm(sv->a[y]);
        return px > py || (px == py && x < y);
    };
    std::partial_sort(cand.begin(), cand.begin() + (std::ptrdiff_t) kk, cand.end(), better);
    for (size_t t = 0; t < kk; ++t) {
        idx[t] = cand[t];
        prob[t] = std::norm(sv->a[cand[t]]);
    }
    *k_out = (int32_t) kk;
    return ACCQ_OK;
}
