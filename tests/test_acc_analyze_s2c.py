# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — test logic tiêu chí pre-register H5/H6 (analyze_s2c)
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from acc import analyze_s2c as A  # noqa: E402

N = 500


def _runs(rates, seeds=5, sha="x", viol=None):
    viol = viol or {}
    out = []
    for s in range(seeds):
        rng = np.random.default_rng(100 + s)
        arms = {k: {"ok": (rng.random(N) < p).astype(int).tolist(), "mask_violations": viol.get(k, 0),
                    "params": 1, "top1": p} for k, p in rates.items()}
        out.append({"seed": s, "dataset_sha": f"{sha}{s}", "arms": arms})
    return {"runs": out}


B = {"H1_linear_rank64": .17, "H2_mlp_param_matched": .19, "H3_e9_core": .17, "H4_e9_no_rotor": .16}


def test_clear_win_passes_c1_and_c2():
    r = A.analyze_task("t", _runs(B), _runs({A.H5I: .40, A.H5A: .20, A.H6I: .25}))
    assert r["C1_pass"] and all(r["C1_beats"].values())
    assert r["delta_interaction"]["C2_pass"] and r["delta_interaction"]["ci95"][0] > 0


def test_tie_with_mlp_fails_c1_and_null_interaction_fails_c2():
    r = A.analyze_task("t", _runs(B), _runs({A.H5I: .19, A.H5A: .19, A.H6I: .19}))
    assert not r["C1_pass"] and not r["C1_beats"]["H2_mlp_param_matched"]
    assert not r["delta_interaction"]["C2_pass"]


def test_mask_violation_disqualifies_h5():
    r = A.analyze_task("t", _runs(B), _runs({A.H5I: .40, A.H5A: .20, A.H6I: .25}, viol={A.H5I: 1}))
    assert not r["C1_pass"]


def test_dataset_mismatch_aborts():
    with pytest.raises(SystemExit):
        A.analyze_task("t", _runs(B), _runs({A.H5I: .4, A.H5A: .2, A.H6I: .2}, sha="other"))
