# Changelog: 2026-10-04 11:55 | Antigravity (Claude Opus 5.5) | Tạo mới — regression G2 §5.8: fallback không được giả confidence
"""Khi watchdog chuyển sang Baseline A2, kết quả phải tự khai là fallback và không tuyên bố confidence."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from vivyqu import VivyquEngine  # noqa: E402
from vivyqu.types import CL12_DIMENSION  # noqa: E402

A2 = os.path.join(ROOT, "results", "baseline_a2", "baseline_a2_weights.npz")
FORCE_FALLBACK_US = 1e-9  # mọi bước Core đều vượt ngưỡng -> luôn fallback


def _latent(seed=0):
    return np.random.default_rng(seed).standard_normal(CL12_DIMENSION)


@pytest.mark.skipif(not os.path.exists(A2), reason="thiếu Baseline A2 weights")
def test_fallback_marks_itself_and_claims_no_confidence():
    eng = VivyquEngine(timeout_us=FORCE_FALLBACK_US)
    r = eng.step(_latent(), mode="e9")
    assert r.fallback_used is True
    assert r.confidence == 0.0  # trước đây 1.0 (confidence giả)
    assert r.is_valid and 0 <= r.best_index < CL12_DIMENSION


@pytest.mark.skipif(not os.path.exists(A2), reason="thiếu Baseline A2 weights")
def test_fallback_respects_mask():
    eng = VivyquEngine(timeout_us=FORCE_FALLBACK_US)
    mask = np.zeros(CL12_DIMENSION, bool)
    mask[[7, 123, 4000]] = True
    r = eng.step(_latent(1), constraint_mask=mask, mode="e9")
    assert r.fallback_used and r.best_index in (7, 123, 4000)
    empty = eng.step(_latent(2), constraint_mask=np.zeros(CL12_DIMENSION, bool), mode="e9")
    assert not empty.is_valid and empty.confidence == 0.0


def test_core_path_not_marked_fallback():
    eng = VivyquEngine(timeout_us=float("inf"))
    r = eng.step(_latent(3), mode="e9")
    assert r.fallback_used is False


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
def test_invalid_timeout_rejected(bad):
    with pytest.raises(ValueError):
        VivyquEngine(timeout_us=bad)
