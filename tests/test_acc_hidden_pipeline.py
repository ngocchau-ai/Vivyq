# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — test S3 pipeline: render prompt, P2 trực chuẩn, G-ENC/P6 trên dữ liệu tổng hợp
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from acc import hidden_pipeline as HP  # noqa: E402
from acc.tasks import make_split  # noqa: E402


@pytest.mark.parametrize("task", ["acc1", "acc2", "acc3"])
def test_render_single_line_deterministic_no_answer(task):
    for split in ("train", "test"):
        for s in make_split(task, split, 20, 0):
            p = HP.render(task, s.features)
            assert "\n" not in p and "\r" not in p and p.endswith(("Answer:", "x ="))
            assert p == HP.render(task, s.features.copy())


def test_render_acc3_recovers_integers():
    from acc import acc3_dlog as a3
    rng = np.random.default_rng(5)
    for _ in range(50):
        inst = a3.generate(rng, "test")
        s = make_split("acc3", "test", 1, 0)[0]  # chỉ để lấy kiểu
        t = 2 * np.pi / inst.p
        f = np.array([inst.p / 4096, inst.g / inst.p, inst.h / inst.p, np.cos(t * inst.g), np.sin(t * inst.g),
                      np.cos(t * inst.h), np.sin(t * inst.h)])
        assert f"Find x such that {inst.g}^x = {inst.h} (mod {inst.p})" in HP.render("acc3", f)
        assert s is not None


def test_render_acc1_lists_only_present_edges_and_forbidden():
    f = np.zeros(39)
    f[0] = 1.234   # cạnh 0-1
    f[15 + 2 * 4 + 3] = 1.0  # đỉnh 2 cấm màu 3
    p = HP.render("acc1", f)
    assert "0-1:1.23" in p and "0-2" not in p and "Forbidden (vertex:color): 2:3" in p


def test_p2_projection_orthonormal_and_fixed():
    P = HP.p2_projection()
    assert P.shape == (2560, 4096)
    assert np.allclose(P @ P.T, np.eye(2560), atol=1e-8)
    assert np.array_equal(P, HP.p2_projection())


def _synthetic(linear: bool, n=1500, d_f=10, seed=0):
    rng = np.random.default_rng(seed)
    F = rng.standard_normal((n, d_f))
    if linear:
        H = F @ rng.standard_normal((d_f, 2560)) + 0.1 * rng.standard_normal((n, 2560))
    else:
        H = rng.standard_normal((n, 2560))
    return H[:1200], H[1200:], F[:1200], F[1200:]


def test_genc_passes_when_hidden_encodes_features():
    r = HP.genc_layer(*_synthetic(True), np.random.default_rng(1))
    assert r["r2_val"] > 0.9 and r["p6_shuffled_r2_val"] < 0.1 and r["pass"]


def test_genc_fails_when_hidden_is_noise():
    r = HP.genc_layer(*_synthetic(False), np.random.default_rng(1))
    assert r["r2_val"] < 0.1 and not r["pass"]
