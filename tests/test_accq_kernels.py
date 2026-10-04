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
