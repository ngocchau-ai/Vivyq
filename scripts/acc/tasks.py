# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S2: tác vụ ACC-1..3 -> (feature, latent P5, infer_mask, correct set)
"""Adapter tác vụ cho harness. Mỗi mẫu: features(f,), infer_mask(4096 bool), correct(4096 bool), meta.

infer_mask = ràng buộc CÔNG KHAI đưa cho mọi arm lúc suy luận (ACC-1: mask màu cấm; ACC-2/3: toàn 1,
vì đáp án hợp lệ là thứ cần tìm, không được lộ). correct = tập đáp án chấp nhận (verifier exact).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import acc1_coloring as a1, acc2_clock as a2, acc3_dlog as a3
from .common import N_CAND, N_SITES

_TRIU = np.triu_indices(N_SITES, 1)


@dataclass
class Sample:
    features: np.ndarray
    infer_mask: np.ndarray
    correct: np.ndarray
    meta: dict


def _acc1(rng, family):
    inst = a1.generate(rng, family)
    best, opt, mask = a1.solve(inst)
    cost = a1.cost_all(inst)
    correct = mask & (cost <= opt + 1e-9)
    f = np.concatenate([inst.weights[_TRIU], inst.forbidden.astype(float).ravel()])
    return Sample(f, mask, correct, {"family": family, "cost": cost, "opt": opt})


def _acc2(rng, frustration=None):
    f_ = float(rng.random()) if frustration is None else frustration
    inst = a2.generate(rng, f_)
    r = a2.solve(inst)
    correct = np.zeros(N_CAND, dtype=bool)
    correct[r["ground"]] = True
    f = np.concatenate([inst.J[_TRIU], inst.h, np.cos(inst.phi), np.sin(inst.phi)])
    return Sample(f, np.ones(N_CAND, dtype=bool), correct,
                  {"frustration": f_, "energy": a2.energy_all(inst), "e0": r["e0"]})


def _acc3(rng, split):
    inst = a3.generate(rng, split)
    p, g, h = inst.p, inst.g, inst.h
    t = 2 * np.pi / p
    f = np.array([p / 4096, g / p, h / p, np.cos(t * g), np.sin(t * g), np.cos(t * h), np.sin(t * h)])
    return Sample(f, np.ones(N_CAND, dtype=bool), a3.solve(inst), {"p": p})


TASKS = {
    "acc1": {"train": ["sparse"], "val": ["mid"],
             "test": ["dense", "bipartite", "wheel", "k6_perturbed"], "gen": _acc1, "regret": "cost"},
    "acc2": {"train": [None], "val": [None], "test": [None], "gen": _acc2, "regret": "energy"},
    "acc3": {"train": ["train"], "val": ["val"], "test": ["test"], "gen": _acc3, "regret": None},
}


def make_split(task: str, split: str, n: int, seed: int) -> list:
    spec = TASKS[task]
    if split not in ("train", "val", "test"):
        raise ValueError(f"split không hợp lệ: {split}")
    if n <= 0:
        raise ValueError("n phải > 0")
    # seed riêng cho từng split để train/val/test không bao giờ trùng dòng RNG
    rng = np.random.default_rng([seed, {"train": 1, "val": 2, "test": 3}[split], 7919])
    keys = spec[split]
    return [spec["gen"](rng, keys[i % len(keys)]) for i in range(n)]
