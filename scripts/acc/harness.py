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
