# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S2: harness arm H0,H1,H2,H7 trên latent P5 (CPU, numpy)
"""Harness S2. Arm đã có: H0 (prior), H1 (linear rank-64), H2 (MLP khớp tham số), H7 (oracle vét cạn).
Arm CHƯA có (cần đọc Core E9 / thiết kế riêng): H3 Core E9, H4 bỏ rotor, H5 qudit-hybrid, H6 qubit-12.
Mọi arm: logits (N,4096); mask suy luận áp bằng -1e30; chọn ngoài mask bị đếm (phải = 0, fail-closed).
Hyper-parameter / early-stop CHỈ chọn trên val; test chỉ được chấm sau khi train xong.
"""
from __future__ import annotations

import numpy as np

from .common import N_CAND
from .tasks import Sample, TASKS

NEG = -1e30
P5_SEED = 20261003  # cố định: phép chiếu P5 phải tái lập được


# ---------- P5: latent tổng hợp có cấu trúc ----------
class P5Latent:
    """z = Q (f - mu)/sd, Q (4096,d) cột trực giao cố định theo seed. Fit mu/sd chỉ trên train."""

    def __init__(self, d: int):
        rng = np.random.default_rng(P5_SEED)
        q, _ = np.linalg.qr(rng.standard_normal((N_CAND, d)))
        self.Q = q.astype(np.float32)
        self.mu = self.sd = None

    def fit(self, feats: np.ndarray):
        self.mu = feats.mean(0)
        self.sd = feats.std(0) + 1e-8
        return self

    def __call__(self, feats: np.ndarray) -> np.ndarray:
        return (((feats - self.mu) / self.sd).astype(np.float32)) @ self.Q.T * np.float32(np.sqrt(N_CAND))


def stack(samples: list):
    feats = np.stack([s.features for s in samples])
    mask = np.stack([s.infer_mask for s in samples])
    correct = np.stack([s.correct for s in samples])
    return feats, mask, correct


# ---------- Mô hình ----------
def _masked_softmax_loss(logits, mask, correct):
    """-log sum_{y in correct∩mask} p(y); trả (loss, dlogits). Hợp lệ khi đa nhãn."""
    lg = np.where(mask, logits, NEG)
    lg = lg - lg.max(1, keepdims=True)
    e = np.exp(lg) * mask
    z = e.sum(1, keepdims=True)
    p = e / z
    good = correct & mask
    zg = (e * good).sum(1, keepdims=True)
    loss = float(-np.mean(np.log(zg / z + 1e-30)))
    q = e * good / (zg + 1e-30)
    return loss, (p - q) / len(logits)


class _Adam:
    def __init__(self, params, lr):
        self.lr, self.t = lr, 0
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}

    def step(self, params, grads):
        self.t += 1
        for k in params:
            self.m[k] = 0.9 * self.m[k] + 0.1 * grads[k]
            self.v[k] = 0.999 * self.v[k] + 0.001 * grads[k] ** 2
            mh = self.m[k] / (1 - 0.9 ** self.t)
            vh = self.v[k] / (1 - 0.999 ** self.t)
            params[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)


class LinearRank:
    name = "H1_linear_rank64"

    def __init__(self, rank=64, seed=0):
        r = np.random.default_rng(seed)
        self.p = {"U": (r.standard_normal((N_CAND, rank)) / np.sqrt(N_CAND)).astype(np.float32),
                  "V": (r.standard_normal((rank, N_CAND)) / np.sqrt(rank)).astype(np.float32)}

    def n_params(self):
        return sum(v.size for v in self.p.values())

    def forward(self, z):
        h = z @ self.p["U"]
        return h @ self.p["V"], h

    def grads(self, z, dlog, h):
        return {"V": h.T @ dlog, "U": z.T @ (dlog @ self.p["V"].T)}


class MLP:
    name = "H2_mlp_param_matched"

    def __init__(self, target_params: int, seed=0):
        # chọn hidden để số tham số gần target nhất: 4096h + h + h*4096 + 4096
        self.h = max(1, min(range(1, 4096), key=lambda h: abs(8192 * h + h + N_CAND - target_params)))
        r = np.random.default_rng(seed + 1)
        self.p = {"W1": (r.standard_normal((N_CAND, self.h)) / np.sqrt(N_CAND)).astype(np.float32),
                  "b1": np.zeros(self.h, np.float32),
                  "W2": (r.standard_normal((self.h, N_CAND)) / np.sqrt(self.h)).astype(np.float32),
                  "b2": np.zeros(N_CAND, np.float32)}

    def n_params(self):
        return sum(v.size for v in self.p.values())

    def forward(self, z):
        a = z @ self.p["W1"] + self.p["b1"]
        h = np.maximum(a, 0)
        return h @ self.p["W2"] + self.p["b2"], (a, h)

    def grads(self, z, dlog, cache):
        a, h = cache
        dh = (dlog @ self.p["W2"].T) * (a > 0)
        return {"W2": h.T @ dlog, "b2": dlog.sum(0), "W1": z.T @ dh, "b1": dh.sum(0)}


# Mặt phẳng rotor giống Core E9 (results/branch_c: rotors_config); góc khởi tạo cũng lấy từ E9.
E9_ROTORS = [(0, 1, 0.25), (2, 3, -0.35), (4, 5, 0.40), (6, 7, -0.20),
             (8, 9, 0.15), (10, 11, -0.30), (0, 6, 0.18), (1, 7, -0.22)]


def _rotor_pairs(pi, pj):
    bi, bj = 1 << min(pi, pj), 1 << max(pi, pj)
    base = np.flatnonzero((np.arange(N_CAND) & (bi | bj)) == 0)
    return base | bi, base | bj  # 1024 cặp, khớp precompute_rotor_pairs của E9


_PAIRS = [_rotor_pairs(pi, pj) for pi, pj, _ in E9_ROTORS]


class E9CoreArm:
    """H3 (use_rotors=True) / H4 (False): [rotor Givens] -> W_c (64x4096) -> codebook C (4096x64) + cost b.
    Tham số học: W_c, C, b (+ 8 góc rotor ở H3; mặt phẳng cố định như E9)."""

    def __init__(self, use_rotors: bool, seed=0, rank=64):
        self.use_rotors = use_rotors
        self.name = "H3_e9_core" if use_rotors else "H4_e9_no_rotor"
        r = np.random.default_rng(seed + 2)
        self.p = {"Wc": (r.standard_normal((rank, N_CAND)) / np.sqrt(N_CAND)).astype(np.float32),
                  "C": (r.standard_normal((N_CAND, rank)) / np.sqrt(rank)).astype(np.float32),
                  "b": np.zeros(N_CAND, np.float32)}
        if use_rotors:
            self.p["theta"] = np.array([t for _, _, t in E9_ROTORS], np.float32)

    def n_params(self):
        return sum(v.size for v in self.p.values())

    def _rot(self, x, theta):
        y = x.copy()
        for (ia, ib), th in zip(_PAIRS, theta):
            c, s = np.float32(np.cos(th)), np.float32(np.sin(th))
            va, vb = y[:, ia].copy(), y[:, ib].copy()
            y[:, ia], y[:, ib] = c * va - s * vb, s * va + c * vb
        return y

    def forward(self, z):
        zr = self._rot(z, self.p["theta"]) if self.use_rotors else z
        pr = zr @ self.p["Wc"].T
        return pr @ self.p["C"].T + self.p["b"], (zr, pr)

    def grads(self, z, dlog, cache):
        zr, pr = cache
        dpr = dlog @ self.p["C"]
        g = {"C": dlog.T @ pr, "b": dlog.sum(0), "Wc": dpr.T @ zr}
        if self.use_rotors:
            y, dy = zr.copy(), dpr @ self.p["Wc"]
            dth = np.zeros(len(_PAIRS), np.float32)
            for m in range(len(_PAIRS) - 1, -1, -1):
                ia, ib = _PAIRS[m]
                th = self.p["theta"][m]
                c, s = np.float32(np.cos(th)), np.float32(np.sin(th))
                ya, yb, dya, dyb = y[:, ia].copy(), y[:, ib].copy(), dy[:, ia].copy(), dy[:, ib].copy()
                dth[m] = float((dyb * ya - dya * yb).sum())
                dy[:, ia], dy[:, ib] = c * dya + s * dyb, -s * dya + c * dyb
                y[:, ia], y[:, ib] = c * ya + s * yb, -s * ya + c * yb  # khôi phục đầu vào (phép quay trực giao)
            g["theta"] = dth
        return g


# ---------- H5 / H6: mô hình factor có cấu trúc (2026-10-04, pre-register §8.12) ----------
from itertools import combinations  # noqa: E402


def _site_states(n_sites: int, n_states: int, perm=None) -> np.ndarray:
    """(4096, n_sites): trạng thái từng site của ứng viên k. 6x4 -> qudit (base 4), 12x2 -> qubit (bit).
    perm (12,) nếu có: bit i của chỉ số đã hoán vị = bit perm[i] của k, rồi mới gom thành site (S2d D2)."""
    bits = int(np.log2(n_states))
    k = np.arange(N_CAND)
    if perm is not None:
        k = sum(((k >> int(src)) & 1) << i for i, src in enumerate(perm))
    return np.stack([(k >> (bits * i)) & (n_states - 1) for i in range(n_sites)], axis=1)


def factor_incidence(n_sites: int, n_states: int, orders, perm=None) -> np.ndarray:
    """G (M, 4096) 0/1: logit_k = sum_f out[f, local(k)] = (out @ G)[k]. Factor = tập con site có kích thước ∈ orders."""
    st = _site_states(n_sites, n_states, perm)
    rows = []
    for o in orders:
        for subset in combinations(range(n_sites), o):
            local = np.zeros(N_CAND, dtype=np.int64)
            for s in subset:
                local = local * n_states + st[:, s]
            block = np.zeros((n_states ** o, N_CAND), np.float32)
            block[local, np.arange(N_CAND)] = 1.0
            rows.append(block)
    return np.concatenate(rows, 0)


FACTOR_SPECS = {
    # tên arm: (n_sites, n_states, orders, rank r) — r chọn để số tham số ≈ H3 (528 392) ±1%
    "H5_qudit_additive": (6, 4, (1,), 128),       # tương hỗ cộng tính (chỉ unary) -> mốc cho Δ_interaction
    "H5_qudit_interact": (6, 4, (1, 2, 3), 93),   # tương hỗ-có-cổng: cặp + bộ ba qudit
    "H6_qubit_interact": (12, 2, (1, 2, 3), 86),  # cùng cấu trúc trên 12 qubit -> tách 'qudit' khỏi 'tensor'
}

# Changelog: 2026-10-04 08:20 | Antigravity (Claude Opus 5.5) | S2d (spec §8.13 D2). Tách dict riêng để suite s2c
# (lặp qua FACTOR_SPECS) giữ nguyên tập arm → tái lập được.
MISALIGN_SEED = 20261004


def broken_pairs(perm) -> int:
    """Số site (cặp bit 2i, 2i+1 sau hoán vị) KHÔNG trùng một cặp gốc {2j, 2j+1} của bài."""
    return sum(int(perm[2 * i]) // 2 != int(perm[2 * i + 1]) // 2 for i in range(6))


def misaligned_perm(seed: int = MISALIGN_SEED, min_broken: int = 4) -> np.ndarray:
    """Hoán vị 12 bit cố định; sinh lại (cùng rng) tới khi ≥ min_broken cặp bị phá (§8.13)."""
    rng = np.random.default_rng(seed)
    while True:
        p = rng.permutation(12)
        if broken_pairs(p) >= min_broken:
            return p


FACTOR_SPECS_S2D = {
    "H5_qudit_misaligned": (6, 4, (1, 2, 3), 93),   # như H5_qudit_interact nhưng site ≠ site của bài
    "H6_qubit_order4": (12, 2, (1, 2, 3, 4), 37),   # qubit đủ bậc biểu diễn factor cặp-qudit (4 bit)
}
FACTOR_PERM = {"H5_qudit_misaligned": "misaligned"}


class FactorArm:
    """z -> h = z A (rank r) -> bảng factor out = h B + c (M) -> logits = out @ G (G cố định, không học)."""

    def __init__(self, name: str, seed=0):
        n_sites, n_states, orders, r = {**FACTOR_SPECS, **FACTOR_SPECS_S2D}[name]
        self.name = name
        perm = misaligned_perm() if FACTOR_PERM.get(name) == "misaligned" else None
        self.G = factor_incidence(n_sites, n_states, orders, perm)
        m = self.G.shape[0]
        rng = np.random.default_rng(seed + 3)
        self.p = {"A": (rng.standard_normal((N_CAND, r)) / np.sqrt(N_CAND)).astype(np.float32),
                  "B": (rng.standard_normal((r, m)) / np.sqrt(r * self.G.sum(0).mean())).astype(np.float32),
                  "c": np.zeros(m, np.float32)}

    def n_params(self):
        return sum(v.size for v in self.p.values())

    def forward(self, z):
        h = z @ self.p["A"]
        out = h @ self.p["B"] + self.p["c"]
        return out @ self.G, h

    def grads(self, z, dlog, h):
        dout = dlog @ self.G.T
        return {"c": dout.sum(0), "B": h.T @ dout, "A": z.T @ (dout @ self.p["B"].T)}


def train_model(model, ztr, mtr, ctr, zva, mva, cva, epochs=200, lr=2e-3, eval_every=10):
    """Full-batch Adam; giữ tham số tốt nhất theo val top-1. Trả về log (epoch, loss, val_acc)."""
    opt = _Adam(model.p, lr)
    best = (-1.0, None)
    log = []
    for ep in range(1, epochs + 1):
        logits, cache = model.forward(ztr)
        loss, dlog = _masked_softmax_loss(logits, mtr, ctr)
        if not np.isfinite(loss):
            raise FloatingPointError(f"loss không hữu hạn tại epoch {ep}")
        opt.step(model.p, model.grads(ztr, dlog.astype(np.float32), cache))
        if ep % eval_every == 0 or ep == epochs:
            va = top1(predict(model, zva, mva), cva)
            log.append((ep, loss, va))
            if va > best[0]:
                best = (va, {k: v.copy() for k, v in model.p.items()})
    model.p = best[1]
    return log, best[0]


def predict(model, z, mask):
    """Điểm số đã áp mask suy luận (N,4096)."""
    out = []
    for i in range(0, len(z), 256):
        lg, _ = model.forward(z[i:i + 256])
        out.append(np.where(mask[i:i + 256], lg, NEG))
    return np.concatenate(out)


class Prior:
    name = "H0_prior"

    def __init__(self, ctr):
        self.freq = ctr.sum(0).astype(np.float32)

    def n_params(self):
        return N_CAND

    def forward(self, z):
        return np.tile(self.freq, (len(z), 1)), None


# ---------- Đánh giá ----------
def top1(scores, correct):
    pred = scores.argmax(1)
    return float(correct[np.arange(len(pred)), pred].mean())


def evaluate(scores, mask, correct, samples, task, k=8):
    n = len(scores)
    pred = scores.argmax(1)
    idx = np.arange(n)
    ok = correct[idx, pred]
    viol = int((~mask[idx, pred]).sum())
    topk = np.argpartition(-scores, k, axis=1)[:, :k]
    pass_k = correct[idx[:, None], topk].any(1)
    out = {"top1": float(ok.mean()), f"pass@{k}": float(pass_k.mean()), "mask_violations": viol, "n": n}
    kind = TASKS[task]["regret"]
    if kind:
        reg = []
        for i, s in enumerate(samples):
            if kind == "cost":
                reg.append((s.meta["cost"][pred[i]] - s.meta["opt"]) / (s.meta["opt"] + 1e-12)
                           if s.meta["opt"] > 0 else s.meta["cost"][pred[i]])
            else:
                reg.append(s.meta["energy"][pred[i]] - s.meta["e0"])
        out["mean_regret"] = float(np.mean(reg))
    out["_ok"] = ok
    return out


def bootstrap_ci(x, B=2000, seed=0):
    r = np.random.default_rng(seed)
    x = np.asarray(x, float)
    m = r.choice(x, (B, len(x))).mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


# Changelog: 2026-10-04 08:20 | Antigravity (Claude Opus 5.5) | S2d D1 (spec §8.13): Đề xuất top-K + Kiểm chứng exact
def verify_topk(scores, mask, correct, samples, task, k=8):
    """Arm đề xuất K ứng viên điểm cao nhất; chỉ ứng viên trong mask được xét. Verifier exact (cùng cho mọi arm):
    ACC-1 cost nhỏ nhất, ACC-2 năng lượng nhỏ nhất, ACC-3 ứng viên thỏa phương trình (= thuộc correct).
    Hòa -> ứng viên index nhỏ hơn. Trả về ok_V, passk_ok (theo mẫu, int) và regret_V (ACC-1/2, None cho ACC-3)."""
    n = len(scores)
    kind = TASKS[task]["regret"]
    ok_v = np.zeros(n, int)
    passk = np.zeros(n, int)
    reg = [] if kind else None
    for i in range(n):
        top = np.argsort(-scores[i], kind="stable")[:k]
        top = np.sort(top[mask[i, top]])
        if len(top) == 0:  # không có đề xuất hợp lệ -> sai, regret tính theo ứng viên argmax (giống top-1)
            top = np.array([int(scores[i].argmax())])
        passk[i] = int(correct[i, top].any())
        if kind == "cost":
            v = top[int(np.argmin(samples[i].meta["cost"][top]))]
            opt = samples[i].meta["opt"]
            reg.append((samples[i].meta["cost"][v] - opt) / (opt + 1e-12) if opt > 0 else samples[i].meta["cost"][v])
        elif kind == "energy":
            v = top[int(np.argmin(samples[i].meta["energy"][top]))]
            reg.append(samples[i].meta["energy"][v] - samples[i].meta["e0"])
        else:
            hit = top[correct[i, top]]
            v = int(hit[0]) if len(hit) else int(top[0])
        ok_v[i] = int(correct[i, v] and mask[i, v])
    return {"ok_V": ok_v, "passk_ok": passk, "regret_V": None if reg is None else np.asarray(reg, float)}
