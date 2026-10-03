# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — ACC-1 generator + verifier exact
"""ACC-1: tô 4 màu đồ thị 6 đỉnh có ràng buộc cứng. Nhãn = tối ưu exact (vét cạn 4096)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .common import DIGITS, N_CAND, N_SITES, N_STATES, decode

FAMILIES = ("sparse", "mid", "dense", "bipartite", "wheel", "k6_perturbed")


@dataclass(frozen=True)
class Acc1Instance:
    weights: np.ndarray    # (6,6) đối xứng, đường chéo 0, >=0
    forbidden: np.ndarray  # (6,4) bool: forbidden[i,m] = đỉnh i không được màu m
    family: str
    density: float


def _graph(rng: np.random.Generator, family: str):
    n = N_SITES
    adj = np.zeros((n, n), dtype=bool)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    if family == "sparse":
        p = rng.uniform(0.1, 0.4)
        for i, j in pairs:
            adj[i, j] = rng.random() < p
    elif family == "mid":
        p = rng.uniform(0.4, 0.6)
        for i, j in pairs:
            adj[i, j] = rng.random() < p
    elif family == "dense":
        p = rng.uniform(0.7, 1.0)
        for i, j in pairs:
            adj[i, j] = rng.random() < p
    elif family == "bipartite":
        perm = rng.permutation(n)
        a, b = perm[:3], perm[3:]
        for i in a:
            for j in b:
                adj[min(i, j), max(i, j)] = rng.random() < 0.9
    elif family == "wheel":
        hub = int(rng.integers(n))
        rim = [v for v in range(n) if v != hub]
        rng.shuffle(rim)
        for v in rim:
            adj[min(hub, v), max(hub, v)] = True
        for a, b in zip(rim, rim[1:] + rim[:1]):
            adj[min(a, b), max(a, b)] = True
    elif family == "k6_perturbed":
        for i, j in pairs:
            adj[i, j] = rng.random() < 0.9
    else:
        raise ValueError(f"family không hợp lệ: {family}")
    return adj


DENSITY_RANGE = {"sparse": (0.0, 0.4), "mid": (0.4, 0.6), "dense": (0.7, 1.0)}
_MAX_TRIES = 1000


def generate(rng: np.random.Generator, family: str) -> Acc1Instance:
    lo, hi = DENSITY_RANGE.get(family, (0.0, 1.0))
    total = N_SITES * (N_SITES - 1) / 2
    for _ in range(_MAX_TRIES):
        adj = _graph(rng, family)
        if lo - 1e-9 <= adj.sum() / total <= hi + 1e-9:
            break
    else:
        raise RuntimeError(f"không sinh được đồ thị family={family} trong mật độ [{lo},{hi}]")
    w = np.where(adj, rng.uniform(0.5, 2.0, size=adj.shape), 0.0)
    w = np.triu(w, 1)
    w = w + w.T
    forbidden = np.zeros((N_SITES, N_STATES), dtype=bool)
    for i in range(N_SITES):
        for m in range(N_STATES):
            forbidden[i, m] = rng.random() < 0.15
        if forbidden[i].all():  # luôn chừa >=1 màu để tồn tại nghiệm hợp lệ
            forbidden[i, int(rng.integers(N_STATES))] = False
    n_edges = int(adj.sum())
    density = n_edges / (N_SITES * (N_SITES - 1) / 2)
    return Acc1Instance(w, forbidden, family, density)


def cost_all(inst: Acc1Instance) -> np.ndarray:
    """Chi phí mọi ứng viên (4096,) — vectorized."""
    cost = np.zeros(N_CAND)
    for i in range(N_SITES):
        for j in range(i + 1, N_SITES):
            if inst.weights[i, j] > 0:
                cost += inst.weights[i, j] * (DIGITS[:, i] == DIGITS[:, j])
    return cost


def valid_mask(inst: Acc1Instance) -> np.ndarray:
    ok = np.ones(N_CAND, dtype=bool)
    for i in range(N_SITES):
        ok &= ~inst.forbidden[i][DIGITS[:, i]]
    return ok


def solve(inst: Acc1Instance):
    """(index tối ưu, cost tối ưu, mask). Tie-break: index nhỏ nhất."""
    mask = valid_mask(inst)
    cost = np.where(mask, cost_all(inst), np.inf)
    best = int(np.argmin(cost))  # argmin trả index đầu tiên khi hòa
    return best, float(cost[best]), mask


def verify_reference(inst: Acc1Instance, index: int):
    """Verifier độc lập, thuần Python vòng lặp (không dùng DIGITS/vectorized)."""
    a = decode(index)
    for i in range(N_SITES):
        if inst.forbidden[i][a[i]]:
            return False, float("inf")
    c = 0.0
    for i in range(N_SITES):
        for j in range(i + 1, N_SITES):
            if a[i] == a[j]:
                c += float(inst.weights[i, j])
    return True, c


def regret(inst: Acc1Instance, index: int) -> float:
    """(cost chọn - cost tối ưu)/cost tối ưu; vi phạm mask => inf. Tối ưu = 0 => trả hiệu tuyệt đối."""
    _, opt, _ = solve(inst)
    ok, c = verify_reference(inst, index)
    if not ok:
        return float("inf")
    return (c - opt) / opt if opt > 0 else c - opt
