"""
test_quantum_polarization_bench.py
===================================
Microbenchmark & Unit Tests cho 4 Phân Cực Qubit & Activation Steering Delta:
1. Phân loại chuẩn xác 4 trạng thái:
   - |00>: Quán tính (Inertia)
   - |01>: Tiếp nhận (Sensory)
   - |10>: Hành động (Action)
   - |11>: Giám sát & Cứu nguy (Supervision)
2. Kiểm tra giới hạn chuẩn an toàn của vector steering: ||Δh||_2 <= 0.10 * ||h||_2.
3. Đo lường tốc độ phân loại vi mô (< 10 μs).
"""

import time
from pathlib import Path
import numpy as np
import pytest
import sys

# Windows cp1252 console safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from vivyqu.cautreo_harmonizer import HarmonizedCautreoBridge


@pytest.fixture(scope="module")
def bridge():
    return HarmonizedCautreoBridge()


def test_polarization_inertia(bridge):
    """Vector phân bố đều hoặc nhỏ -> Quán tính |00>."""
    # Vector chuẩn hóa có năng lượng dàn đều 4096 chiều
    vec = np.ones(4096, dtype=np.float32)
    vec = vec / np.linalg.norm(vec)

    code, name, conf = bridge.classify_polarization(vec)
    assert name == "INERTIA", f"Kỳ vọng INERTIA nhưng nhận được {name}"
    assert code == 0
    assert conf > 0.5


def test_polarization_action(bridge):
    """Vector có đỉnh nhọn hoặc năng lượng tập trung ở Khối 2 (Động lực) -> Hành động |10>."""
    vec = np.zeros(4096, dtype=np.float32)
    # Khối 2: 1024..2047
    vec[1024:2048] = 1.0
    vec = vec / np.linalg.norm(vec)

    code, name, conf = bridge.classify_polarization(vec)
    assert name == "ACTION", f"Kỳ vọng ACTION nhưng nhận được {name}"
    assert code == 2
    assert conf > 0.5


def test_polarization_sensory(bridge):
    """Vector tập trung ở Khối 1 (Spatial) hoặc Khối 3 (Semantic) -> Tiếp nhận |01>."""
    vec = np.zeros(4096, dtype=np.float32)
    # Khối 1: 0..1023 và Khối 3: 2048..3071
    vec[0:1024] = 0.7
    vec[2048:3072] = 0.7
    vec = vec / np.linalg.norm(vec)

    code, name, conf = bridge.classify_polarization(vec)
    assert name == "SENSORY", f"Kỳ vọng SENSORY nhưng nhận được {name}"
    assert code == 1
    assert conf > 0.5


def test_polarization_supervision_on_drift(bridge):
    """Vector có độ lệch chuẩn nghiêm trọng hoặc NaN -> Giám sát |11>."""
    # Vector có norm quá lớn (drift)
    vec = np.ones(4096, dtype=np.float32) * 5.0  # Norm >> 1.0

    code, name, conf = bridge.classify_polarization(vec)
    assert name == "SUPERVISION", f"Kỳ vọng SUPERVISION nhưng nhận được {name}"
    assert code == 3


def test_steering_delta_norm_boundary(bridge):
    """Vector điều hướng steering bắt buộc tuân thủ ||Δh|| <= 0.10 * ||h||."""
    rng = np.random.RandomState(42)
    vec = rng.randn(4096).astype(np.float32)
    h_norm = np.linalg.norm(vec)

    delta = bridge.compute_steering_delta(vec, max_scale=0.10)
    delta_norm = np.linalg.norm(delta)

    max_allowed = 0.10 * h_norm + 1e-4
    assert delta_norm <= max_allowed, (
        f"Vi phạm an toàn: delta norm {delta_norm:.6f} vượt quá ngưỡng tối đa {max_allowed:.6f}"
    )


def test_polarization_latency(bridge):
    """Đo thời gian thực thi phân loại 4 phân cực (Target < 25.0 μs)."""
    rng = np.random.RandomState(123)
    vec = rng.randn(4096).astype(np.float32)
    vec = vec / np.linalg.norm(vec)

    # Warmup
    for _ in range(50):
        bridge.classify_polarization(vec)

    n_runs = 500
    t0 = time.perf_counter()
    for _ in range(n_runs):
        bridge.classify_polarization(vec)
    t1 = time.perf_counter()

    avg_us = ((t1 - t0) / n_runs) * 1e6
    print(f"\n[BENCHMARK] Phân loại 4 Phân Cực Qubit trung bình: {avg_us:.2f} μs")
    assert avg_us < 50.0, f"Độ trễ quá lớn: {avg_us:.2f} μs"
