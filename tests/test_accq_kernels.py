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
