# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — ACC-3 logarit rời rạc generator + verifier exact
"""ACC-3: tìm x in [0,4095] sao cho g^x = h (mod p). Mask = tập mọi x hợp lệ (không duy nhất)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .common import N_CAND

SPLITS = {"train": (3, 1024), "val": (1025, 2048), "test": (2049, 4096)}


def primes_upto(n: int) -> list:
    sieve = np.ones(n + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = False
    return np.flatnonzero(sieve).tolist()


_PRIMES = primes_upto(4096)


@dataclass(frozen=True)
class Acc3Instance:
    g: int
    h: int
    p: int


def generate(rng: np.random.Generator, split: str) -> Acc3Instance:
    if split not in SPLITS:
        raise ValueError(f"split không hợp lệ: {split}")
    lo, hi = SPLITS[split]
    pool = [q for q in _PRIMES if lo <= q <= hi]
    p = int(pool[rng.integers(len(pool))])
    g = int(rng.integers(2, p))
    x0 = int(rng.integers(N_CAND))
    return Acc3Instance(g, pow(g, x0, p), p)


def solve(inst: Acc3Instance) -> np.ndarray:
    """Mask bool (4096,): True tại mọi x thỏa g^x = h mod p (lũy thừa lặp, vectorized-free, exact)."""
    mask = np.zeros(N_CAND, dtype=bool)
    cur = 1 % inst.p
    for x in range(N_CAND):
        if cur == inst.h % inst.p:
            mask[x] = True
        cur = (cur * inst.g) % inst.p
    return mask


def verify_reference(inst: Acc3Instance, x: int) -> bool:
    """Verifier độc lập bằng pow() tích hợp."""
    if not 0 <= int(x) < N_CAND:
        return False
    return pow(inst.g, int(x), inst.p) == inst.h % inst.p


def order(g: int, p: int) -> int:
    v, k = g % p, 1
    while v != 1:
        v = (v * g) % p
        k += 1
        if k > p:
            raise ValueError("g không khả nghịch mod p")
    return k
