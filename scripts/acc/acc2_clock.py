# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — ACC-2 (Z4 clock cổ điển) generator + verifier exact
"""ACC-2 (phần cổ điển): ground state mô hình Z4 clock có frustration.
H = -sum_{i<j} J_ij cos(pi (s_i - s_j)/2) - sum_i h_i cos(pi s_i/2 + phi_i).
Quantum extension (transverse field) CHƯA triển khai ở S1 (theo spec: cuối pha Q1)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .common import DIGITS, N_CAND, N_SITES, decode

DEGENERACY_TOL = 1e-9


@dataclass(frozen=True)
class Acc2Instance:
    J: np.ndarray      # (6,6) đối xứng, đường chéo 0
    h: np.ndarray      # (6,)
    phi: np.ndarray    # (6,)
    frustration: float  # tỷ lệ cạnh có J<0 yêu cầu


def generate(rng: np.random.Generator, frustration: float, field: bool = True) -> Acc2Instance:
    if not 0.0 <= frustration <= 1.0:
        raise ValueError("frustration phải thuộc [0,1]")
    J = np.zeros((N_SITES, N_SITES))
    for i in range(N_SITES):
        for j in range(i + 1, N_SITES):
            mag = rng.uniform(0.5, 1.5)
            J[i, j] = J[j, i] = -mag if rng.random() < frustration else mag
    h = rng.uniform(0.0, 0.5, N_SITES) if field else np.zeros(N_SITES)
    phi = rng.uniform(0.0, 2 * np.pi, N_SITES)
    return Acc2Instance(J, h, phi, float(frustration))


def energy_all(inst: Acc2Instance) -> np.ndarray:
    s = DIGITS.astype(float)
    e = np.zeros(N_CAND)
    for i in range(N_SITES):
        for j in range(i + 1, N_SITES):
            e -= inst.J[i, j] * np.cos(np.pi * (s[:, i] - s[:, j]) / 2)
        e -= inst.h[i] * np.cos(np.pi * s[:, i] / 2 + inst.phi[i])
    return e


def solve(inst: Acc2Instance) -> dict:
    """Ground state exact + gap + độ suy biến + tập ground states."""
    e = energy_all(inst)
    e0 = float(e.min())
    ground = np.flatnonzero(e <= e0 + DEGENERACY_TOL)
    rest = e[e > e0 + DEGENERACY_TOL]
    gap = float(rest.min() - e0) if rest.size else float("inf")
    return {"e0": e0, "ground": ground.tolist(), "degeneracy": int(ground.size),
            "gap": gap, "top1": int(ground[0])}


def energy_reference(inst: Acc2Instance, index: int) -> float:
    """Verifier độc lập, thuần Python vòng lặp."""
    import math
    s = decode(index)
    e = 0.0
    for i in range(N_SITES):
        for j in range(i + 1, N_SITES):
            e -= float(inst.J[i, j]) * math.cos(math.pi * (s[i] - s[j]) / 2)
        e -= float(inst.h[i]) * math.cos(math.pi * s[i] / 2 + float(inst.phi[i]))
    return e


def recall_at_k(ground: list, ranked: list, k: int = 8) -> float:
    """Tỷ lệ ground states nằm trong Top-k dự đoán (spec ACC-2 §2.2)."""
    if not ground:
        raise ValueError("tập ground rỗng")
    top = set(ranked[:k])
    return sum(1 for g in ground if g in top) / len(ground)
