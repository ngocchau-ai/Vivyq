# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S1: test verifier ACC-1..3 khớp vét cạn độc lập
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from acc import acc1_coloring as a1, acc2_clock as a2, acc3_dlog as a3  # noqa: E402
from acc.common import N_CAND, decode, encode  # noqa: E402


def test_encode_decode_roundtrip_and_bounds():
    for k in (0, 1, 4095, 1234):
        assert encode(decode(k)) == k
    with pytest.raises(ValueError):
        decode(4096)
    with pytest.raises(ValueError):
        decode(-1)
    with pytest.raises(ValueError):
        encode((0, 1, 2, 3, 4, 0))
    with pytest.raises(ValueError):
        encode((0, 1, 2))


@pytest.mark.parametrize("family", a1.FAMILIES)
def test_acc1_solver_matches_reference_on_all_4096(family):
    rng = np.random.default_rng(7)
    for _ in range(5):
        inst = a1.generate(rng, family)
        best, opt, mask = a1.solve(inst)
        cost = a1.cost_all(inst)
        for k in range(N_CAND):
            ok, c = a1.verify_reference(inst, k)
            assert ok == bool(mask[k])
            if ok:
                assert c == pytest.approx(cost[k])
        assert mask[best] and opt == min(cost[mask])
        assert a1.regret(inst, best) == 0.0
        bad = np.flatnonzero(~mask)
        if bad.size:
            assert a1.regret(inst, int(bad[0])) == float("inf")


def test_acc1_density_splits_ood():
    rng = np.random.default_rng(1)
    assert all(a1.generate(rng, "sparse").density <= 0.4 + 1e-9 for _ in range(30))
    assert all(a1.generate(rng, "dense").density >= 0.7 - 1e-9 for _ in range(30))
    assert all(0.4 - 1e-9 <= a1.generate(rng, "mid").density <= 0.6 + 1e-9 for _ in range(30))
    with pytest.raises(ValueError):
        a1.generate(rng, "nope")


def test_acc2_solver_matches_reference_and_degeneracy():
    rng = np.random.default_rng(3)
    for f in (0.0, 0.5, 1.0):
        for field in (True, False):
            inst = a2.generate(rng, f, field)
            r = a2.solve(inst)
            e = a2.energy_all(inst)
            for k in range(0, N_CAND, 7):
                assert a2.energy_reference(inst, k) == pytest.approx(e[k], abs=1e-9)
            assert all(abs(a2.energy_reference(inst, g) - r["e0"]) < 1e-8 for g in r["ground"])
            assert r["degeneracy"] == len(r["ground"]) >= 1
            assert r["gap"] > 0
    # không có trường ngoài: đối xứng toàn cục s -> s+1 phải gây suy biến >= 4
    inst = a2.generate(np.random.default_rng(5), 0.3, field=False)
    assert a2.solve(inst)["degeneracy"] >= 4
    with pytest.raises(ValueError):
        a2.generate(rng, 1.5)


def test_acc2_recall_at_k():
    assert a2.recall_at_k([1, 2], [1, 9, 2], 8) == 1.0
    assert a2.recall_at_k([1, 2], [1, 9, 3], 2) == 0.5
    with pytest.raises(ValueError):
        a2.recall_at_k([], [1])


@pytest.mark.parametrize("split", ["train", "val", "test"])
def test_acc3_mask_equals_bruteforce_pow(split):
    rng = np.random.default_rng(11)
    lo, hi = a3.SPLITS[split]
    for _ in range(10):
        inst = a3.generate(rng, split)
        assert lo <= inst.p <= hi
        mask = a3.solve(inst)
        assert mask.any()
        for x in range(N_CAND):
            assert a3.verify_reference(inst, x) == bool(mask[x])


def test_acc3_multiple_solutions_follow_order_and_edges():
    inst = a3.Acc3Instance(g=2, h=1, p=7)  # ord(2 mod 7)=3 -> x=0,3,6,...
    mask = a3.solve(inst)
    assert a3.order(2, 7) == 3
    assert list(np.flatnonzero(mask)[:3]) == [0, 3, 6]
    assert not a3.verify_reference(inst, -1) and not a3.verify_reference(inst, 4096)
    with pytest.raises(ValueError):
        a3.generate(np.random.default_rng(0), "bogus")


def test_acc3_splits_disjoint_ranges():
    assert a3.SPLITS["train"][1] < a3.SPLITS["val"][0] <= a3.SPLITS["val"][1] < a3.SPLITS["test"][0]
