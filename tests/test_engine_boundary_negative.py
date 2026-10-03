"""Negative boundary tests for VivyquEngine (audit 29/09 G1/G2: dtype/size/stride, fallback).

Each test asserts fail-closed behaviour; none is a smoke test.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

from vivyqu import VivyquEngine, CL12_DIMENSION
from vivyqu.types import ERR_CORE_TIMEOUT


@pytest.fixture(scope="module")
def engine():
    eng = VivyquEngine()
    yield eng
    eng.close()


def test_step_fast_rejects_float32(engine):
    with pytest.raises(ValueError, match="float64"):
        engine.step_fast(np.zeros(CL12_DIMENSION, dtype=np.float32))


def test_step_fast_rejects_short_buffer(engine):
    with pytest.raises(ValueError, match="float64"):
        engine.step_fast(np.zeros(CL12_DIMENSION // 2, dtype=np.float64))


def test_step_fast_rejects_non_contiguous(engine):
    strided = np.zeros(CL12_DIMENSION * 2, dtype=np.float64)[::2]
    assert strided.size == CL12_DIMENSION and not strided.flags.c_contiguous
    with pytest.raises(ValueError, match="float64"):
        engine.step_fast(strided)


def test_step_fast_rejects_bad_mask(engine):
    latent = np.zeros(CL12_DIMENSION, dtype=np.float64)
    with pytest.raises(ValueError, match="uint8"):
        engine.step_fast(latent, np.zeros(256, dtype=np.uint8))
    with pytest.raises(ValueError, match="uint8"):
        engine.step_fast(latent, np.zeros(512, dtype=np.int32))


def test_step_fast_valid_input_still_works(engine):
    rng = np.random.default_rng(0)
    k = engine.step_fast(rng.standard_normal(CL12_DIMENSION), np.full(512, 0xFF, dtype=np.uint8))
    assert 0 <= k < CL12_DIMENSION


def test_fallback_without_weights_returns_core_timeout_not_nameerror(engine, monkeypatch):
    """Regression: engine.py referenced ERR_CORE_TIMEOUT without importing it."""
    monkeypatch.setattr(engine, "_baseline_a2_weights", None)
    real_exists = os.path.exists
    monkeypatch.setattr(
        "vivyqu.engine.os.path.exists",
        lambda p: False if str(p).endswith("baseline_a2_weights.npz") else real_exists(p),
    )
    res = engine._execute_fallback(np.zeros(CL12_DIMENSION), None, 1234.0)
    assert res.is_valid is False
    assert res.error_code == ERR_CORE_TIMEOUT
