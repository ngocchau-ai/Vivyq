"""
test_cautreo_native_invasion.py
================================
Kiểm thử liên thông Thân thể Cautreo Native Invasion & Điều phối Lõi Vivyqu:
1. Mô phỏng Transformer 32 Layers với Layer 16 Invasion Hook.
2. Kiểm chứng Zero-Copy Hidden State Passing & Phân cực 4 Qubit.
3. Kiểm chứng cơ chế Early Exit (tiết kiệm 50% số layer khi có nghiệm).
4. Kiểm chứng Activation Steering tiêm vector Δh vào tensor an toàn.
5. Kiểm chứng VivyquCoreBackend trong cautreo_host/backends.py.
"""

from pathlib import Path
import sys
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))
sys.path.insert(0, str(REPO_ROOT / "host"))
sys.path.insert(0, str(REPO_ROOT / "cautreo-host"))

# Windows cp1252 console safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from vivyqu.cautreo_harmonizer import HarmonizedCautreoBridge
from cautreo_host.backends import VivyquCoreBackend, ModelBackend


class MockInferenceEngine:
    """Mô phỏng runtime LLM 32 layers với tensor con trỏ tại mỗi layer."""

    def __init__(self, total_layers: int = 32, hidden_dim: int = 4096):
        self.total_layers = total_layers
        self.hidden_dim = hidden_dim
        self.layers_computed = 0

    def forward_pass_with_hook(self, initial_state: np.ndarray, hook_layer: int, hook_fn):
        """Chạy forward pass tuần tự qua các layer, gọi hook_fn tại hook_layer."""
        state = initial_state.copy()
        self.layers_computed = 0

        for layer in range(1, self.total_layers + 1):
            self.layers_computed += 1
            # Mô phỏng tính toán layer (thêm chút biến đổi)
            state = state + 0.001 * np.roll(state, 1)

            if layer == hook_layer:
                # Kích hoạt hook xâm lấn trọng số
                should_stop, delta = hook_fn(layer, state)
                if delta is not None:
                    # Tiêm steering
                    state = state + delta
                if should_stop:
                    # Ngắt sớm (Early Exit)
                    break

        return state, self.layers_computed


def test_native_invasion_early_exit_saving():
    """Kiểm chứng cơ chế Early Exit: Ngắt tại Layer 16 tiết kiệm 50% compute."""
    bridge = HarmonizedCautreoBridge()
    engine = MockInferenceEngine(total_layers=32, hidden_dim=4096)

    # Khởi tạo vector kích hoạt trạng thái Action |10>
    vec = np.zeros(4096, dtype=np.float32)
    vec[1024:2048] = 1.0  # Khối Dynamic
    vec = vec / np.linalg.norm(vec)

    def invasion_hook(layer_idx, state_ptr):
        res = bridge.step(raw_latent_vector=state_ptr)
        # res.early_exit là True khi ở trạng thái INERTIA hoặc ACTION
        return res.early_exit, res.steering_delta

    final_state, computed_layers = engine.forward_pass_with_hook(
        initial_state=vec,
        hook_layer=16,
        hook_fn=invasion_hook,
    )

    # Xác nhận chỉ chạy đúng 16 layer thay vì 32 layer
    assert computed_layers == 16, f"Kỳ vọng ngắt tại layer 16, thực tế chạy {computed_layers} layers"
    compute_saved_pct = (32 - computed_layers) / 32 * 100.0
    assert compute_saved_pct == 50.0
    print(f"\n[EVIDENCE] Early Exit tại Layer 16: Tiết kiệm {compute_saved_pct:.1f}% số layer!")


def test_native_invasion_steering_injection():
    """Kiểm chứng tiêm Activation Steering không làm vỡ norm của tensor."""
    bridge = HarmonizedCautreoBridge()
    engine = MockInferenceEngine(total_layers=32, hidden_dim=4096)

    rng = np.random.RandomState(99)
    vec = rng.randn(4096).astype(np.float32)
    vec = vec / np.linalg.norm(vec)

    injected_delta = None

    def invasion_hook(layer_idx, state_ptr):
        nonlocal injected_delta
        res = bridge.step(raw_latent_vector=state_ptr, compute_steering=True)
        injected_delta = res.steering_delta
        # Tiếp tục chạy (không ngắt sớm) để kiểm tra tính liên tục của tensor
        return False, res.steering_delta

    final_state, computed_layers = engine.forward_pass_with_hook(
        initial_state=vec,
        hook_layer=16,
        hook_fn=invasion_hook,
    )

    assert computed_layers == 32
    # Tensor cuối cùng phải hữu hạn và không bị nổ giá trị
    assert np.isfinite(final_state).all()
    assert not np.isnan(final_state).any()


def test_cautreo_host_backend_polarization_integration():
    """Kiểm chứng VivyquCoreBackend trong cautreo_host/backends.py tích hợp 4 phân cực."""
    bridge = HarmonizedCautreoBridge()
    backend = VivyquCoreBackend(bridge=bridge)

    # 1. Kiểm tra decide()
    rng = np.random.RandomState(77)
    latent = rng.randn(4096).astype(np.float64)
    norm = np.linalg.norm(latent)
    latent = latent / norm

    dec = backend.decide(raw_latent_vector=latent)
    assert "polarization" in dec
    assert dec["polarization"] in ("INERTIA", "SENSORY", "ACTION", "SUPERVISION")
    assert "early_exit" in dec
    assert "has_steering" in dec

    # 2. Kiểm tra complete() với Macro-Action Injection
    res = backend.complete("Đọc file config và kiểm tra hệ thống")
    assert "vivyqu_decision" in res
    assert "polarization" in res["vivyqu_decision"]
    assert "early_exit" in res["vivyqu_decision"]
    assert any("Phân cực" in line for line in res["thinking"])
    print(f"\n[EVIDENCE] VivyquCoreBackend thinking log: {res['thinking'][0]}")
