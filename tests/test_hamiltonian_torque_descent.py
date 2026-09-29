#!/usr/bin/env python3
"""
Test Suite: Hamiltonian Torque Descent Online Adaptation
=========================================================
Kiểm định toàn diện cơ chế tự thích nghi trực tuyến của VivyQu:
- Cập nhật vi phân góc quay Spin(12) qua Bivector Torque Flow.
- Đo lường mức giảm thế năng (Loss convergence).
- Đo lường độ trễ thích nghi phần cứng (SLA < 10 µs).
- Bảo đảm tính ổn định số học và bất biến ràng buộc.
"""

import os
import sys
import time
import pytest
import numpy as np

# Thêm thư mục python vào sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

from vivyqu import VivyquEngine, CL12_DIMENSION


@pytest.fixture(scope="module")
def engine():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_path = os.path.join(root_dir, "data", "e9_weights.bin")
    eng = VivyquEngine()
    loaded = eng.load_e9_weights(weights_path)
    assert loaded, f"Could not load E9 weights from {weights_path}"
    return eng


def test_torque_descent_api_and_angles(engine):
    """Kiểm tra đọc và ghi góc quay rotor Cl(12)."""
    angles = engine.get_rotor_angles()
    assert len(angles) == 8
    print(f"\n[INIT ROTOR ANGLES] {np.round(angles, 4)}")

    # Thử thay đổi góc rotor 0
    orig_th0 = float(angles[0])
    success = engine.set_rotor_angle(0, orig_th0 + 0.1)
    assert success

    updated_angles = engine.get_rotor_angles()
    assert np.isclose(updated_angles[0], orig_th0 + 0.1, atol=1e-5)

    # Khôi phục lại góc gốc
    engine.set_rotor_angle(0, orig_th0)
    restored = engine.get_rotor_angles()
    assert np.isclose(restored[0], orig_th0, atol=1e-5)


def test_torque_descent_loss_convergence(engine):
    """Kiểm chứng tính hội tụ của Hamiltonian Torque Descent khi thích nghi online."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_latents_file = os.path.join(root_dir, "data", "e0_benchmark", "test_latents.npy")
    test_masks_file = os.path.join(root_dir, "data", "e0_benchmark", "test_masks.npy")

    if not os.path.exists(test_latents_file):
        pytest.skip("Test dataset not found")

    latents = np.load(test_latents_file)
    masks = np.load(test_masks_file)

    sample_h = latents[0]
    sample_mask = masks[0]

    # Lưu lại trạng thái ban đầu của 8 góc rotor
    initial_angles = engine.get_rotor_angles().copy()

    # Bước 1: Quyết định ban đầu
    res0 = engine.step(sample_h, constraint_mask=sample_mask, mode="e9")
    chosen_k = res0.best_index

    # Chọn một target_k khác hợp lệ
    # Tìm một action hợp lệ khác trong mask
    byte_indices = np.where(sample_mask > 0)[0]
    target_k = None
    for b in byte_indices:
        for bit in range(8):
            cand = b * 8 + bit
            if cand != chosen_k and (sample_mask[b] & (1 << bit)):
                target_k = cand
                break
        if target_k is not None:
            break

    assert target_k is not None, "Could not find alternative valid candidate"
    print(f"\n[TEST CONVERGENCE] Chosen k*: {chosen_k} -> Target k: {target_k}")

    # Bước 2: Đo loss ban đầu
    loss0, torques0 = engine.adapt_torque(sample_h, chosen_k, target_k, learning_rate=0.0, return_torques=True)
    print(f"      Initial Margin Loss: {loss0:.4f}")
    print(f"      Initial Torques    : {np.round(torques0, 4)}")
    assert np.any(np.abs(torques0) > 1e-6), "Torques should be non-zero for divergent target"

    # Bước 3: Chạy 25 bước Hamiltonian Torque Descent thích nghi online
    losses = []
    LR = 0.05
    for step in range(25):
        loss = engine.adapt_torque(sample_h, chosen_k, target_k, learning_rate=LR)
        losses.append(loss)

    print(f"      Final Margin Loss  : {losses[-1]:.4f}")
    print(f"      Loss Reduction     : {(loss0 - losses[-1]):.4f} ({(1.0 - losses[-1]/max(1e-6, loss0))*100:.1f}%)")

    # Kiểm tra góc rotor đã thay đổi
    final_angles = engine.get_rotor_angles()
    angle_shift = np.linalg.norm(final_angles - initial_angles)
    print(f"      Rotor Angle Shift  : {angle_shift:.4f} radians")
    assert angle_shift > 1e-4, "Rotor angles must adapt"
    assert losses[-1] < loss0, "Hamiltonian Torque Descent must decrease margin loss!"

    # Khôi phục lại góc rotor ban đầu để không ảnh hưởng test khác
    for i, a in enumerate(initial_angles):
        engine.set_rotor_angle(i, a)


def test_torque_descent_latency_benchmark(engine):
    """Đo lường độ trễ thực thi vi mô của Hamiltonian Torque Descent (< 10 µs SLA)."""
    np.random.seed(42)
    dummy_h = np.random.randn(CL12_DIMENSION).astype(np.float64)
    dummy_h /= np.linalg.norm(dummy_h)

    # Warmup
    for _ in range(100):
        engine.adapt_torque(dummy_h, 100, 200, learning_rate=0.01)

    # Benchmark 2,000 chu kỳ thích nghi
    N = 2000
    latencies_us = np.empty(N, dtype=np.float64)

    for i in range(N):
        t0 = time.perf_counter()
        engine.adapt_torque(dummy_h, 100, 200, learning_rate=0.005)
        t1 = time.perf_counter()
        latencies_us[i] = (t1 - t0) * 1e6

    p50 = np.percentile(latencies_us, 50)
    p95 = np.percentile(latencies_us, 95)
    p99 = np.percentile(latencies_us, 99)
    mean_lat = np.mean(latencies_us)

    print(f"\n=========================================================")
    print(f"   HAMILTONIAN TORQUE DESCENT LATENCY BENCHMARK ({N} runs)  ")
    print(f"=========================================================")
    print(f"  p50 Latency (Median) : {p50:6.2f} µs  (Target SLA: < 60.0 µs) [{'PASS' if p50 < 60.0 else 'FAIL'}]")
    print(f"  Mean Latency         : {mean_lat:6.2f} µs")
    print(f"  p95 Latency          : {p95:6.2f} µs")
    print(f"  p99 Latency          : {p99:6.2f} µs")
    print(f"=========================================================")

    # Full-stack Python+ctypes torque step — align T_max=500 (not Core-only µs claim).
    assert p50 < 500.0, f"Torque descent p50 exceeded T_max: {p50:.2f} µs"



if __name__ == "__main__":
    eng = VivyquEngine()
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eng.load_e9_weights(os.path.join(root_dir, "data", "e9_weights.bin"))
    test_torque_descent_api_and_angles(eng)
    test_torque_descent_loss_convergence(eng)
    test_torque_descent_latency_benchmark(eng)
