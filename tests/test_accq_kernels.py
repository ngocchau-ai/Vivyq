# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — cổng kiểm chứng kernel ACC-Q (docs/DESIGN_ACCQ_KERNELS_CPP.md §3). K1.
import ctypes
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acc import acc1_coloring as a1, acc2_clock as a2  # noqa: E402

DLL = ROOT / "build" / "bin" / "vivyqu_accq.dll"
pytestmark = pytest.mark.skipif(not DLL.exists(), reason="chạy scripts/build_accq.ps1 trước")

_D = ctypes.POINTER(ctypes.c_double)


@pytest.fixture(scope="module")
def lib():
    L = ctypes.CDLL(str(DLL))
    L.accq_pairwise_bruteforce.argtypes = [ctypes.c_int32, _D, _D, ctypes.POINTER(ctypes.c_uint8), ctypes.c_double,
                                           ctypes.POINTER(ctypes.c_uint64), _D, ctypes.POINTER(ctypes.c_uint64), _D]
    L.accq_pairwise_bruteforce.restype = ctypes.c_int32
    return L


def k1(lib, unary, pair, forbid=None, tol=1e-9, want_e=True):
    n = unary.shape[0]
    u = np.ascontiguousarray(unary, np.float64)
    p = np.ascontiguousarray(pair, np.float64)
    f = None if forbid is None else np.ascontiguousarray(forbid, np.uint8)
    e = np.empty(4 ** n) if want_e else None
    bi, bc = ctypes.c_uint64(), ctypes.c_uint64()
    be = ctypes.c_double()
    rc = lib.accq_pairwise_bruteforce(
        n, u.ctypes.data_as(_D), p.ctypes.data_as(_D),
        None if f is None else f.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), tol,
        ctypes.byref(bi), ctypes.byref(be), ctypes.byref(bc), None if e is None else e.ctypes.data_as(_D))
    return rc, bi.value, be.value, bc.value, e


def acc1_terms(inst):
    n = 6
    u = np.zeros((n, 4))
    p = np.zeros((n, n, 4, 4))
    for i in range(n):
        for j in range(i + 1, n):
            p[i, j] = inst.weights[i, j] * np.eye(4)
    return u, p, inst.forbidden


def acc2_terms(inst):
    n = 6
    a = np.arange(4)
    u = -inst.h[:, None] * np.cos(np.pi * a[None, :] / 2 + inst.phi[:, None])
    p = np.zeros((n, n, 4, 4))
    for i in range(n):
        for j in range(i + 1, n):
            p[i, j] = -inst.J[i, j] * np.cos(np.pi * (a[:, None] - a[None, :]) / 2)
    return u, p


def test_k1_matches_acc1_200_instances(lib):
    rng = np.random.default_rng(11)
    fams = a1.FAMILIES
    for t in range(200):
        inst = a1.generate(rng, fams[t % len(fams)])
        u, p, f = acc1_terms(inst)
        rc, bi, be, ng, e = k1(lib, u, p, f)
        assert rc == 0
        best, opt, mask = a1.solve(inst)
        ref = np.where(mask, a1.cost_all(inst), np.inf)
        fin = np.isfinite(ref)
        assert np.array_equal(fin, np.isfinite(e))
        assert np.max(np.abs(e[fin] - ref[fin])) <= 1e-9
        assert bi == best and abs(be - opt) <= 1e-9
        assert ng == int((ref <= opt + 1e-9).sum())
        # verifier thuần Python độc lập trên ứng viên tối ưu + 3 ứng viên ngẫu nhiên
        for k in [bi, *rng.integers(0, 4096, 3)]:
            ok, c = a1.verify_reference(inst, int(k))
            assert ok == bool(np.isfinite(e[k])) and (not ok or abs(c - e[k]) <= 1e-9)


def test_k1_matches_acc2_200_instances(lib):
    rng = np.random.default_rng(12)
    for t in range(200):
        inst = a2.generate(rng, float(rng.random()))
        u, p = acc2_terms(inst)
        rc, bi, be, ng, e = k1(lib, u, p)
        assert rc == 0
        r = a2.solve(inst)
        ref = a2.energy_all(inst)
        assert np.max(np.abs(e - ref)) <= 1e-9
        assert bi == r["top1"] and abs(be - r["e0"]) <= 1e-9 and ng == r["degeneracy"]
        for k in [bi, *rng.integers(0, 4096, 3)]:
            assert abs(a2.energy_reference(inst, int(k)) - e[k]) <= 1e-9


def _numpy_energy(u, p):
    n = u.shape[0]
    d = np.stack([(np.arange(4 ** n) // 4 ** i) % 4 for i in range(n)], 1)
    e = u[np.arange(n)[None, :], d].sum(1)
    for i in range(n):
        for j in range(i + 1, n):
            e += p[i, j][d[:, i], d[:, j]]
    return e


def test_k1_n8_random_matches_numpy_and_no_energies_path(lib):
    rng = np.random.default_rng(13)
    for _ in range(5):
        u = rng.standard_normal((8, 4))
        p = rng.standard_normal((8, 8, 4, 4))
        ref = _numpy_energy(u, p)
        rc, bi, be, ng, e = k1(lib, u, p)
        assert rc == 0 and np.max(np.abs(e - ref)) <= 1e-9
        assert bi == int(np.argmin(ref)) and abs(be - ref.min()) <= 1e-12
        rc2, bi2, be2, ng2, _ = k1(lib, u, p, want_e=False)  # đường 2-pass không cấp phát
        assert (rc2, bi2, ng2) == (0, bi, ng) and be2 == be


def test_k1_tie_break_smallest_index_and_ground_count(lib):
    u = np.zeros((3, 4))
    p = np.zeros((3, 3, 4, 4))  # mọi ứng viên E = 0
    rc, bi, be, ng, _ = k1(lib, u, p)
    assert (rc, bi, be, ng) == (0, 0, 0.0, 64)


def test_k1_errors(lib):
    u = np.zeros((6, 4))
    p = np.zeros((6, 6, 4, 4))
    assert k1(lib, np.zeros((14, 4)), np.zeros((14, 14, 4, 4)), want_e=False)[0] == 2
    bad = u.copy()
    bad[2, 1] = math.nan
    assert k1(lib, bad, p)[0] == 3
    badp = p.copy()
    badp[0, 1, 0, 0] = math.inf
    assert k1(lib, u, badp)[0] == 3
    assert k1(lib, u, p, forbid=np.ones((6, 4)))[0] == 5  # mọi ứng viên bị cấm
    assert k1(lib, u, p, tol=-1.0)[0] == 1
    bi = ctypes.c_uint64()
    assert lib.accq_pairwise_bruteforce(6, None, None, None, 0.0, ctypes.byref(bi), None, None, None) == 1


# ---------------- K2: statevector ----------------
_P = ctypes.c_void_p


def _sv_lib(lib):
    if getattr(lib, "_sv_ready", False):
        return lib
    lib.accq_sv_create.argtypes = [ctypes.c_int32, ctypes.POINTER(_P)]
    lib.accq_sv_destroy.argtypes = [_P]
    lib.accq_sv_destroy.restype = None
    for name, args in {"accq_sv_reset": [_P], "accq_sv_set": [_P, _D, ctypes.c_uint64],
                       "accq_sv_get": [_P, _D, ctypes.c_uint64], "accq_sv_apply1": [_P, ctypes.c_int32, _D],
                       "accq_sv_apply2": [_P, ctypes.c_int32, ctypes.c_int32, _D], "accq_sv_norm2": [_P, _D],
                       "accq_sv_probs": [_P, _D, ctypes.c_uint64],
                       "accq_sv_topk": [_P, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32,
                                        ctypes.POINTER(ctypes.c_uint64), _D, ctypes.POINTER(ctypes.c_int32)]}.items():
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = ctypes.c_int32
    lib.accq_sv_create.restype = ctypes.c_int32
    lib._sv_ready = True
    return lib


def _reim(m):
    m = np.ascontiguousarray(m, np.complex128)
    return np.ascontiguousarray(m.view(np.float64).ravel())


def _unitary(rng, d):
    q, r = np.linalg.qr(rng.standard_normal((d, d)) + 1j * rng.standard_normal((d, d)))
    return q * (np.diag(r) / np.abs(np.diag(r)))


def _ref1(psi, n, site, U):
    T = psi.reshape([4] * n)
    ax = n - 1 - site
    return np.moveaxis(np.tensordot(U, T, axes=([1], [ax])), 0, ax).reshape(-1)


def _ref2(psi, n, sa, sb, U):
    T = psi.reshape([4] * n)
    aa, ab = n - 1 - sa, n - 1 - sb
    R = np.tensordot(U.reshape(4, 4, 4, 4), T, axes=([2, 3], [aa, ab]))
    return np.moveaxis(R, [0, 1], [aa, ab]).reshape(-1)


class _SV:
    def __init__(self, lib, n):
        self.lib, self.n, self.h = _sv_lib(lib), n, _P()
        assert self.lib.accq_sv_create(n, ctypes.byref(self.h)) == 0

    def get(self):
        buf = np.empty(2 * 4 ** self.n)
        assert self.lib.accq_sv_get(self.h, buf.ctypes.data_as(_D), 4 ** self.n) == 0
        return buf.view(np.complex128)

    def close(self):
        self.lib.accq_sv_destroy(self.h)


@pytest.mark.parametrize("n", [3, 4])
def test_k2_matches_numpy_tensordot_and_preserves_norm(lib, n):
    rng = np.random.default_rng(20 + n)
    sv = _SV(lib, n)
    psi = np.zeros(4 ** n, complex)
    psi[0] = 1
    for _ in range(3):  # 3 lớp: cổng 1-qudit mọi site + cổng 2-qudit cặp ngẫu nhiên (kể cả a > b)
        for s in range(n):
            U = _unitary(rng, 4)
            u = _reim(U)
            assert lib.accq_sv_apply1(sv.h, s, u.ctypes.data_as(_D)) == 0
            psi = _ref1(psi, n, s, U)
        for _ in range(n):
            a, b = rng.choice(n, 2, replace=False)
            U = _unitary(rng, 16)
            u = _reim(U)
            assert lib.accq_sv_apply2(sv.h, int(a), int(b), u.ctypes.data_as(_D)) == 0
            psi = _ref2(psi, n, int(a), int(b), U)
    got = sv.get()
    assert np.max(np.abs(got - psi)) <= 1e-12
    nrm = ctypes.c_double()
    assert lib.accq_sv_norm2(sv.h, ctypes.byref(nrm)) == 0 and abs(nrm.value - 1) <= 1e-12
    probs = np.empty(4 ** n)
    assert lib.accq_sv_probs(sv.h, probs.ctypes.data_as(_D), 4 ** n) == 0
    assert np.max(np.abs(probs - np.abs(psi) ** 2)) <= 1e-12
    # top-K có mask: so với sắp xếp NumPy (hòa -> index nhỏ)
    mask = (rng.random(4 ** n) < 0.5).astype(np.uint8)
    idx = (ctypes.c_uint64 * 8)()
    pr = np.empty(8)
    ko = ctypes.c_int32()
    assert lib.accq_sv_topk(sv.h, mask.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), 8, idx, pr.ctypes.data_as(_D),
                            ctypes.byref(ko)) == 0
    allowed = np.flatnonzero(mask)
    order = allowed[np.lexsort((allowed, -probs[allowed]))][:8]
    assert ko.value == 8 and list(idx) == order.tolist()
    sv.close()


def test_k2_set_get_roundtrip_topk_ties_and_errors(lib):
    sv = _SV(lib, 2)
    amp = np.zeros(16, complex)
    amp[[3, 5, 9]] = 1 / np.sqrt(3)  # hòa 3 ứng viên
    a = _reim(amp)
    assert lib.accq_sv_set(sv.h, a.ctypes.data_as(_D), 16) == 0
    assert np.allclose(sv.get(), amp, atol=0)
    idx = (ctypes.c_uint64 * 20)()
    pr = np.empty(20)
    ko = ctypes.c_int32()
    assert lib.accq_sv_topk(sv.h, None, 20, idx, pr.ctypes.data_as(_D), ctypes.byref(ko)) == 0
    assert ko.value == 16 and list(idx)[:3] == [3, 5, 9]
    z = np.zeros(32)
    assert lib.accq_sv_apply1(sv.h, 2, z.ctypes.data_as(_D)) == 1      # site ngoài phạm vi
    assert lib.accq_sv_apply2(sv.h, 1, 1, np.zeros(512).ctypes.data_as(_D)) == 1  # cùng site
    bad = np.zeros(32)
    bad[5] = np.nan
    assert lib.accq_sv_apply1(sv.h, 0, bad.ctypes.data_as(_D)) == 3
    assert lib.accq_sv_set(sv.h, a.ctypes.data_as(_D), 15) == 2
    sv.close()
    h = _P()
    assert lib.accq_sv_create(13, ctypes.byref(h)) == 2 and lib.accq_sv_create(0, ctypes.byref(h)) == 2


# ---------------- K3: MPS (Changelog 2026-10-04 07:21 | Antigravity (Claude Opus 5.5) | thêm cổng K3) ----------------
_I32 = ctypes.POINTER(ctypes.c_int32)
_U64 = ctypes.POINTER(ctypes.c_uint64)


def _mps_lib(lib):
    if getattr(lib, "_mps_ready", False):
        return lib
    lib.accq_mps_amplitude.argtypes = [ctypes.c_int32, _I32, _D, ctypes.c_uint64, _D]
    lib.accq_mps_norm2.argtypes = [ctypes.c_int32, _I32, _D, _D]
    lib.accq_mps_sample.argtypes = [ctypes.c_int32, _I32, _D, ctypes.c_int32, ctypes.c_uint64, _U64, _D]
    for f in (lib.accq_mps_amplitude, lib.accq_mps_norm2, lib.accq_mps_sample):
        f.restype = ctypes.c_int32
    lib.accq_version.restype = ctypes.c_char_p
    lib._mps_ready = True
    return lib


def _rand_mps(rng, n, chi):
    bonds = [1] + [min(chi, 4 ** min(i, n - i)) for i in range(1, n)] + [1]
    As = [rng.standard_normal((bonds[i], 4, bonds[i + 1])) + 1j * rng.standard_normal((bonds[i], 4, bonds[i + 1]))
          for i in range(n)]
    return np.array(bonds, np.int32), As


def _pack(As):
    return _reim(np.concatenate([A.ravel() for A in As]))


def _dense(As):
    M = As[0][0]  # (4, D1); hàng = index các site đã duyệt (s_0 bit thấp)
    for A in As[1:]:
        C = M.shape[0]
        M = np.einsum("cl,lar->acr", M, A).reshape(4 * C, A.shape[2])
    return M[:, 0]


def _mps_call_norm(lib, bonds, t):
    out = ctypes.c_double()
    rc = lib.accq_mps_norm2(len(bonds) - 1, bonds.ctypes.data_as(_I32), t.ctypes.data_as(_D), ctypes.byref(out))
    return rc, out.value


def _mps_sample(lib, bonds, t, K, seed):
    idx = np.empty(max(K, 1), np.uint64)
    lp = np.empty(max(K, 1))
    rc = lib.accq_mps_sample(len(bonds) - 1, bonds.ctypes.data_as(_I32), t.ctypes.data_as(_D), K, seed,
                             idx.ctypes.data_as(_U64), lp.ctypes.data_as(_D))
    return rc, idx, lp


@pytest.mark.parametrize("n,chi", [(1, 1), (3, 2), (5, 4), (6, 8)])
def test_k3_amplitude_and_norm_match_dense(lib, n, chi):
    L = _mps_lib(lib)
    assert L.accq_version().decode().startswith("vivyqu_accq 0.4.0")
    rng = np.random.default_rng(100 + n)
    bonds, As = _rand_mps(rng, n, chi)
    t = _pack(As)
    psi = _dense(As)
    out = np.empty(2)
    got = np.empty(4 ** n, complex)
    for k in range(4 ** n):
        assert L.accq_mps_amplitude(n, bonds.ctypes.data_as(_I32), t.ctypes.data_as(_D), k, out.ctypes.data_as(_D)) == 0
        got[k] = out[0] + 1j * out[1]
    scale = np.abs(psi).max()
    assert np.abs(got - psi).max() <= 1e-12 * scale
    rc, nrm = _mps_call_norm(L, bonds, t)
    ref = float(np.sum(np.abs(psi) ** 2))
    assert rc == 0 and abs(nrm - ref) <= 1e-12 * ref


def test_k3_sampling_tv_logp_determinism(lib):
    L = _mps_lib(lib)
    rng = np.random.default_rng(7)
    bonds, As = _rand_mps(rng, 4, 4)
    t = _pack(As)
    p = np.abs(_dense(As)) ** 2
    p /= p.sum()
    N = 1_000_000
    rc, idx, lp = _mps_sample(L, bonds, t, N, 12345)
    assert rc == 0
    emp = np.bincount(idx.astype(np.int64), minlength=256) / N
    tv = 0.5 * np.abs(emp - p).sum()
    assert tv < 0.01, tv
    assert np.abs(lp - np.log(p[idx.astype(np.int64)])).max() <= 1e-10
    rc2, idx2, lp2 = _mps_sample(L, bonds, t, 1000, 12345)
    assert rc2 == 0 and np.array_equal(idx2, idx[:1000]) and np.array_equal(lp2, lp[:1000])
    _, idx3, _ = _mps_sample(L, bonds, t, 1000, 999)
    assert not np.array_equal(idx3, idx2)


def test_k3_n24_large_scale_stays_finite(lib):
    L = _mps_lib(lib)
    rng = np.random.default_rng(24)
    bonds, As = _rand_mps(rng, 24, 16)
    t = _pack([A * 30.0 for A in As])  # biên độ khổng lồ: kernel phải chuẩn hóa log-scale, logp vẫn hữu hạn
    rc, idx, lp = _mps_sample(L, bonds, t, 8, 1)
    assert rc == 0 and np.all(np.isfinite(lp)) and np.all(lp <= 0)
    assert np.all(idx < np.uint64(4 ** 24))


def test_k3_errors(lib):
    L = _mps_lib(lib)
    rng = np.random.default_rng(3)
    bonds, As = _rand_mps(rng, 3, 2)
    t = _pack(As)
    out = np.empty(2)
    B = lambda b: np.array(b, np.int32)  # noqa: E731
    assert L.accq_mps_amplitude(3, B([2, 2, 2, 1]).ctypes.data_as(_I32), t.ctypes.data_as(_D), 0,
                                out.ctypes.data_as(_D)) == 1  # bonds[0] != 1
    assert L.accq_mps_amplitude(3, bonds.ctypes.data_as(_I32), t.ctypes.data_as(_D), 64,
                                out.ctypes.data_as(_D)) == 1  # idx >= 4^n
    assert L.accq_mps_amplitude(3, bonds.ctypes.data_as(_I32), t.ctypes.data_as(_D), 0, None) == 1
    assert _mps_call_norm(L, B([1]), t)[0] == 2                    # n = 0
    assert _mps_call_norm(L, B([1] * 33), t)[0] == 2               # n = 32
    assert _mps_call_norm(L, B([1, 65, 1]), np.zeros(2 * 65 * 8))[0] == 2  # bond > 64
    bad = t.copy()
    bad[3] = np.nan
    assert _mps_call_norm(L, bonds, bad)[0] == 3
    assert _mps_call_norm(L, bonds, np.zeros_like(t))[0] == 3      # chuẩn = 0
    assert _mps_sample(L, bonds, np.zeros_like(t), 4, 0)[0] == 3
    assert _mps_sample(L, bonds, t, 0, 0)[0] == 1


# ---------------- K4 (Changelog 2026-10-04 07:24 | Antigravity (Claude Opus 5.5) | thêm cổng K4) ----------------
_U8 = ctypes.POINTER(ctypes.c_uint8)


def _k4_lib(lib):
    if getattr(lib, "_k4_ready", False):
        return lib
    lib.accq_chain_viterbi.argtypes = [ctypes.c_int32, _D, _D, _U8, _U64, _D]
    lib.accq_pairwise_beam.argtypes = [ctypes.c_int32, _D, _D, _U8, ctypes.c_int32, _U64, _D]
    lib.accq_chain_viterbi.restype = lib.accq_pairwise_beam.restype = ctypes.c_int32
    lib._k4_ready = True
    return lib


def _fp(f):
    return None if f is None else np.ascontiguousarray(f, np.uint8).ctypes.data_as(_U8)


def viterbi(lib, u, chain, f=None):
    u, chain = np.ascontiguousarray(u, np.float64), np.ascontiguousarray(chain, np.float64)
    fa = None if f is None else np.ascontiguousarray(f, np.uint8)
    bi, be = ctypes.c_uint64(), ctypes.c_double()
    rc = lib.accq_chain_viterbi(u.shape[0], u.ctypes.data_as(_D), chain.ctypes.data_as(_D), _fp(fa),
                                ctypes.byref(bi), ctypes.byref(be))
    return rc, bi.value, be.value


def beam(lib, u, p, B, f=None):
    u, p = np.ascontiguousarray(u, np.float64), np.ascontiguousarray(p, np.float64)
    fa = None if f is None else np.ascontiguousarray(f, np.uint8)
    bi, be = ctypes.c_uint64(), ctypes.c_double()
    rc = lib.accq_pairwise_beam(u.shape[0], u.ctypes.data_as(_D), p.ctypes.data_as(_D), _fp(fa), B,
                                ctypes.byref(bi), ctypes.byref(be))
    return rc, bi.value, be.value


def _chain_to_pair(chain, n):
    p = np.zeros((n, n, 4, 4))
    for i in range(n - 1):
        p[i, i + 1] = chain[i]
    return p


def _rand_forbid(rng, n, prob):
    f = (rng.random((n, 4)) < prob).astype(np.uint8)
    f[f.sum(1) == 4, rng.integers(0, 4)] = 0  # không để site chết
    return f


def test_k4_viterbi_matches_k1_on_300_chain_instances(lib):
    L = _k4_lib(lib)
    rng = np.random.default_rng(41)
    unique = 0
    for t in range(300):
        n = 2 + t % 7
        u = rng.standard_normal((n, 4))
        ch = rng.standard_normal((n - 1, 4, 4))
        f = _rand_forbid(rng, n, 0.15) if t % 2 else None
        rc, bi, be = viterbi(L, u, ch, f)
        rc1, bi1, be1, ng, e = k1(lib, u, _chain_to_pair(ch, n), f)
        assert rc == 0 and rc1 == 0
        assert abs(be - be1) <= 1e-9 and e[bi] <= be1 + 1e-9
        if ng == 1:
            assert bi == bi1
            unique += 1
    assert unique >= 250  # đảm bảo phần lớn instance thực sự kiểm tra so khớp index


def test_k4_viterbi_integer_ties_exact_smallest_index(lib):
    # năng lượng nguyên -> cộng chính xác, nhiều ground state -> index phải trùng K1 (nhỏ nhất) tuyệt đối
    L = _k4_lib(lib)
    rng = np.random.default_rng(42)
    multi = 0
    for t in range(200):
        n = 2 + t % 7
        u = rng.integers(-1, 2, (n, 4)).astype(float)
        ch = rng.integers(-1, 2, (n - 1, 4, 4)).astype(float)
        f = _rand_forbid(rng, n, 0.2) if t % 3 == 0 else None
        rc, bi, be = viterbi(L, u, ch, f)
        rc1, bi1, be1, ng, _ = k1(lib, u, _chain_to_pair(ch, n), f, want_e=False)
        assert (rc, bi, be) == (rc1, bi1, be1)
        multi += ng > 1
    assert multi >= 100
    assert viterbi(L, np.zeros((1, 4)), np.zeros((0, 4, 4)))[:2] == (0, 0)  # n = 1


def test_k4_beam_exact_when_beam_covers_all_prefixes(lib):
    L = _k4_lib(lib)
    rng = np.random.default_rng(43)
    for t in range(60):
        n = 2 + t % 5
        u = rng.standard_normal((n, 4))
        p = rng.standard_normal((n, n, 4, 4))
        f = _rand_forbid(rng, n, 0.15) if t % 2 else None
        rc, bi, be = beam(L, u, p, 4 ** (n - 1), f)
        rc1, bi1, be1, _, e = k1(lib, u, p, f)
        assert rc == 0 and abs(be - be1) <= 1e-9 and abs(e[bi] - be) <= 1e-9
    u, p = np.zeros((3, 4)), np.zeros((3, 3, 4, 4))
    assert beam(L, u, p, 1)[:2] == (0, 0)  # hòa -> index nhỏ nhất


def test_k4_errors(lib):
    L = _k4_lib(lib)
    u, ch, p = np.zeros((4, 4)), np.zeros((3, 4, 4)), np.zeros((4, 4, 4, 4))
    assert viterbi(L, np.zeros((32, 4)), np.zeros((31, 4, 4)))[0] == 2
    bad = u.copy()
    bad[1, 2] = math.nan
    assert viterbi(L, bad, ch)[0] == 3 and beam(L, bad, p, 4)[0] == 3
    badc = ch.copy()
    badc[0, 0, 0] = math.inf
    assert viterbi(L, u, badc)[0] == 3
    dead = np.zeros((4, 4), np.uint8)
    dead[2] = 1
    assert viterbi(L, u, ch, dead)[0] == 5 and beam(L, u, p, 4, dead)[0] == 5
    assert beam(L, u, p, 0)[0] == 2 and beam(L, u, p, 65537)[0] == 2
    bi, be = ctypes.c_uint64(), ctypes.c_double()
    assert L.accq_chain_viterbi(4, u.ctypes.data_as(_D), None, None, ctypes.byref(bi), ctypes.byref(be)) == 1
    assert L.accq_pairwise_beam(4, None, None, None, 4, ctypes.byref(bi), ctypes.byref(be)) == 1

