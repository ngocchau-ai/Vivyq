# Changelog: 2026-10-04 08:26 | Antigravity (Claude Opus 5.5) | Tạo mới — test S2d (spec §8.13): arm mới, verifier H+V, tiêu chí analyze_s2d
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from acc import analyze_s2d as A  # noqa: E402
from acc import harness as H  # noqa: E402
from acc import run_s2 as R  # noqa: E402
from acc.tasks import make_split  # noqa: E402

N = 500


# ---------- harness ----------
def test_misaligned_perm_is_fixed_valid_and_breaks_at_least_4_pairs():
    p = H.misaligned_perm()
    assert sorted(p.tolist()) == list(range(12))
    assert H.broken_pairs(p) >= 4
    assert np.array_equal(p, H.misaligned_perm())  # tất định
    assert H.broken_pairs(np.arange(12)) == 0
    assert H.broken_pairs(np.array([1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10])) == 0  # chỉ đổi trong cặp
    assert H.broken_pairs(np.array([2, 3, 0, 1, 4, 5, 6, 7, 8, 9, 10, 11])) == 0  # chỉ đổi thứ tự cặp


def test_perm_none_keeps_existing_arms_identical_and_identity_perm_matches():
    for n_sites, n_states in ((6, 4), (12, 2)):
        a = H._site_states(n_sites, n_states)
        k = np.arange(4096)
        ref = np.stack([(k >> (int(np.log2(n_states)) * i)) & (n_states - 1) for i in range(n_sites)], 1)
        assert np.array_equal(a, ref)
        assert np.array_equal(H._site_states(n_sites, n_states, np.arange(12)), ref)


def test_misaligned_sites_are_bit_pairs_of_permuted_index():
    p = H.misaligned_perm()
    st = H._site_states(6, 4, p)
    k = 0b101100111010
    bits = [(k >> j) & 1 for j in range(12)]
    exp = [bits[p[2 * i]] + 2 * bits[p[2 * i + 1]] for i in range(6)]
    assert st[k].tolist() == exp


def test_new_arm_param_counts_match_spec():
    assert H.FactorArm("H5_qudit_misaligned", 0).n_params() == 526064
    a = H.FactorArm("H6_qubit_order4", 0)
    assert a.G.shape == (9968, 4096) and a.n_params() == 530336
    assert set(H.FACTOR_SPECS) == {"H5_qudit_additive", "H5_qudit_interact", "H6_qubit_interact"}  # s2c không đổi


@pytest.mark.parametrize("task", ["acc1", "acc2", "acc3"])
def test_verify_topk_equals_passk_and_picks_exact_best(task):
    te = make_split(task, "test", 40, 999)
    _, mask, correct = H.stack(te)
    rng = np.random.default_rng(1)
    scores = np.where(mask, rng.standard_normal(mask.shape), H.NEG).astype(np.float32)
    for i in range(0, 40, 4):  # cài đáp án vào top-8 cho một phần mẫu để có cả đúng lẫn sai
        scores[i, np.flatnonzero(correct[i])[0]] = 100.0
    v = H.verify_topk(scores, mask, correct, te, task, k=8)
    assert np.array_equal(v["ok_V"], v["passk_ok"])
    assert v["ok_V"][::4].all() and 0 < v["ok_V"].sum() <= 40
    if v["regret_V"] is not None:
        assert np.all(v["regret_V"][v["ok_V"] == 1] <= 1e-9) and np.all(v["regret_V"] >= -1e-9)


def test_s2d_refuses_old_seeds():
    with pytest.raises(SystemExit):
        R.main(["--suite", "s2d", "--task", "acc1", "--seed-start", "0", "--seeds", "1"])


# ---------- analyze_s2d ----------
def _runs(rates, seeds=range(5, 10), viol=None, break_v=False):
    viol = viol or {}
    out = []
    for s in seeds:
        rng = np.random.default_rng(100 + s)
        arms = {}
        for k, (p, pv) in rates.items():
            ok = (rng.random(N) < p).astype(int).tolist()
            okv = (rng.random(N) < pv).astype(int).tolist()
            pk = list(okv)
            if break_v and k == A.H5I:
                pk[0] = 1 - pk[0]
            arms[k] = {"ok": ok, "ok_V": okv, "passk_ok": pk, "mask_violations": viol.get(k, 0), "params": 1,
                       "regret_V": None}
        out.append({"seed": s, "dataset_sha": f"x{s}", "arms": arms})
    return {"runs": out}


BASE = {"H1_linear_rank64": (.17, .40), "H2_mlp_param_matched": (.19, .42), "H4_e9_no_rotor": (.16, .41)}


def test_d1_clear_win_and_d2_structure_label():
    r = A.analyze_task("t", _runs({**BASE, A.H6I: (.30, .45), A.H5I: (.37, .70), A.H5M: (.20, .40),
                                   A.H6Q4: (.36, .60)}))
    assert r["D1_pass"] and all(r["D1_beats"].values())
    assert r["delta_align"]["D2A_pass"]                        # H5 >> misaligned, misaligned không vượt H6
    assert r["delta_qudit_vs_qubit_order4"]["D2Q_pass"]        # H5 ≈ H6_order4 -> CI chứa 0
    assert r["D1_L"] == "[CHƯA ĐO]"


def test_d1_fails_on_tie_with_h6_and_d2a_fails_if_misaligned_beats_h6():
    r = A.analyze_task("t", _runs({**BASE, A.H6I: (.30, .70), A.H5I: (.37, .70), A.H5M: (.20, .40),
                                   A.H6Q4: (.20, .60)}))
    assert not r["D1_pass"] and not r["D1_beats"][A.H6I]
    assert not r["delta_qudit_vs_qubit_order4"]["D2Q_pass"]    # H5 rõ ràng hơn order4
    r2 = A.analyze_task("t", _runs({**BASE, A.H6I: (.20, .45), A.H5I: (.40, .70), A.H5M: (.30, .40),
                                    A.H6Q4: (.40, .60)}))
    assert not r2["delta_align"]["misaligned_not_above_H6"] and not r2["delta_align"]["D2A_pass"]


def test_integrity_guards():
    good = {**BASE, A.H6I: (.3, .4), A.H5I: (.3, .4), A.H5M: (.3, .4), A.H6Q4: (.3, .4)}
    with pytest.raises(SystemExit):
        A.analyze_task("t", _runs(good, seeds=range(0, 5)))     # seed cũ
    with pytest.raises(SystemExit):
        A.analyze_task("t", _runs(good, break_v=True))          # ok_V != passk_ok
    bad = dict(good)
    bad.pop(A.H6Q4)
    with pytest.raises(SystemExit):
        A.analyze_task("t", _runs(bad))                         # thiếu arm
    r = A.analyze_task("t", _runs({**good, A.H5I: (.6, .9)}, viol={A.H5I: 1}))
    assert not r["D1_pass"]                                     # vi phạm mask loại H5


def test_verdict_labels_need_two_of_three_and_all_tasks():
    p = {"D1_pass": True, "delta_align": {"D2A_pass": True}, "delta_qudit_vs_qubit_order4": {"D2Q_pass": False}}
    f = {"D1_pass": False, "delta_align": {"D2A_pass": False}, "delta_qudit_vs_qubit_order4": {"D2Q_pass": True}}
    v = A.verdict({"a": p, "b": p, "c": f})
    assert v["H5_supported_HV"] and v["labels"] == [A.LABEL_ALIGN]
    assert A.verdict({"a": p, "b": p})["labels"] == [] and A.verdict({"a": p, "b": p})["final"] is False
