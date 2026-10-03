# [!IMPORTANT] Agent chỉnh sửa file này phải ghi Changelog; chỉ cô lập, không xóa; đồng bộ D:\2brain.
# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S1 của ACC-1..3 (docs/ACCEPTANCE_SUITE_ACC1_3_QUDIT_HYPOTHESIS.md)
"""Tiện ích chung: ứng viên 12-bit = 6 qudit x 4 trạng thái (index = sum c_i * 4**i)."""
from __future__ import annotations

import numpy as np

N_SITES = 6
N_STATES = 4
N_CAND = N_STATES ** N_SITES  # 4096


def digits_table() -> np.ndarray:
    """Bảng (4096, 6): digits[k, i] = trạng thái của site i trong ứng viên k."""
    k = np.arange(N_CAND)
    return np.stack([(k // N_STATES ** i) % N_STATES for i in range(N_SITES)], axis=1)


DIGITS = digits_table()


def encode(assign) -> int:
    if len(assign) != N_SITES or any(not 0 <= int(c) < N_STATES for c in assign):
        raise ValueError(f"assign phải gồm {N_SITES} giá trị trong [0,{N_STATES - 1}]: {assign}")
    return sum(int(c) * N_STATES ** i for i, c in enumerate(assign))


def decode(index: int) -> tuple:
    if not 0 <= int(index) < N_CAND:
        raise ValueError(f"index ngoài [0,{N_CAND - 1}]: {index}")
    return tuple((int(index) // N_STATES ** i) % N_STATES for i in range(N_SITES))
