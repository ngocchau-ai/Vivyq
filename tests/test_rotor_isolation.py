# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — kiểm chứng cô lập rotor (ISOLATED ≡ LEGACY về quyết định)
"""Rotor bị cô lập khỏi đường E9 mặc định bằng cách gập vào W_c_active = W_c·R(θ).
Test bảo vệ: (1) mặc định ISOLATED; (2) quyết định ISOLATED == LEGACY trên dữ liệu thật;
(3) đổi góc / thích nghi torque vẫn giữ tương đương; (4) mode sai bị từ chối, trạng thái không đổi."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from vivyqu import VivyquEngine  # noqa: E402

N = 300


@pytest.fixture(scope="module")
def eng():
    # Changelog: 2026-10-04 11:54 | Antigravity (Claude Opus 5.5) | Test toán học Core, không phải watchdog:
    # tắt watchdog wall-clock (trước đây CPU bận -> fallback A2 -> confidence lệch, test chập chờn).
    e = VivyquEngine(timeout_us=float("inf"))
    assert e.load_e9_weights(os.path.join(ROOT, "data", "e9_weights.bin"))
    return e


@pytest.fixture(scope="module")
def data():
    lat = os.path.join(ROOT, "data", "e0_benchmark", "test_latents.npy")
    if not os.path.exists(lat):
        pytest.skip("thiếu data/e0_benchmark")
    return np.load(lat)[:N], np.load(os.path.join(ROOT, "data", "e0_benchmark", "test_masks.npy"))[:N]


def _decide(eng, lat, masks, mode):
    assert eng.set_rotor_mode(mode)
    out = [eng.step(lat[i], constraint_mask=masks[i], mode="e9") for i in range(len(lat))]
    assert not any(r.fallback_used for r in out), "kết quả phải đến từ Core, không phải fallback"
    return np.array([r.best_index for r in out]), np.array([r.confidence for r in out])


def test_default_mode_is_isolated(eng):
    assert eng.get_rotor_mode() == "isolated"


def test_isolated_matches_legacy_decisions(eng, data):
    lat, masks = data
    k_iso, c_iso = _decide(eng, lat, masks, "isolated")
    k_leg, c_leg = _decide(eng, lat, masks, "legacy")
    eng.set_rotor_mode("isolated")
    agree = float((k_iso == k_leg).mean())
    print(f"\n[rotor isolation] agree={agree:.4f} max|dconf|={np.abs(c_iso - c_leg).max():.3e}")
    assert agree == 1.0
    np.testing.assert_allclose(c_iso, c_leg, rtol=1e-4, atol=1e-4)


def test_equivalence_survives_angle_change_and_restore(eng, data):
    lat, masks = data
    a0 = eng.get_rotor_angles().copy()
    try:
        eng.set_rotor_angle(2, float(a0[2]) + 0.7)
        k_iso, _ = _decide(eng, lat[:100], masks[:100], "isolated")
        k_leg, _ = _decide(eng, lat[:100], masks[:100], "legacy")
        assert (k_iso == k_leg).all()
    finally:
        for i, a in enumerate(a0):
            eng.set_rotor_angle(i, float(a))
        eng.set_rotor_mode("isolated")
    assert np.allclose(eng.get_rotor_angles(), a0, atol=1e-6)


def test_torque_adaptation_keeps_equivalence(eng, data):
    lat, masks = data
    a0 = eng.get_rotor_angles().copy()
    try:
        eng.set_rotor_mode("isolated")
        k0 = eng.step(lat[0], constraint_mask=masks[0], mode="e9").best_index
        for _ in range(10):
            eng.adapt_torque(lat[0], k0, (k0 + 1) % 4096, learning_rate=0.05)
        assert np.linalg.norm(eng.get_rotor_angles() - a0) > 1e-4
        k_iso, _ = _decide(eng, lat[:100], masks[:100], "isolated")
        k_leg, _ = _decide(eng, lat[:100], masks[:100], "legacy")
        assert (k_iso == k_leg).all()
    finally:
        for i, a in enumerate(a0):
            eng.set_rotor_angle(i, float(a))
        eng.set_rotor_mode("isolated")


def test_invalid_mode_rejected_without_state_change(eng):
    assert eng.get_rotor_mode() == "isolated"
    with pytest.raises(ValueError):
        eng.set_rotor_mode("off")
    assert eng._lib.vivyqu_core_set_rotor_mode(7) != 0  # ABI trực tiếp: mode lạ bị từ chối
    assert eng.get_rotor_mode() == "isolated"
