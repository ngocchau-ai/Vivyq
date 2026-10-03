# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — S3: prompt cố định -> hidden_extract (l_out theo layer) -> P2 chiếu 2560->4096 -> G-ENC ridge + P6 xáo nhãn
"""Pipeline hidden-state thật cho ACC-1..3 (spec §3, §8.3, §8.7).

  python scripts/acc/hidden_pipeline.py prompts --task acc1 --seed 0
  python scripts/acc/hidden_pipeline.py extract --task acc1 --seed 0 [--threads 6]
  python scripts/acc/hidden_pipeline.py genc    --task acc1 --seed 0 [--layers 21 31 41]

Dữ liệu (lớn, KHÔNG vào git): D:\\models\\vivyqu_hidden\\{task}_s{seed}\\ (prompts.txt, L{il}.f32, manifest.json, genc.json).
Thứ tự dòng trong prompts.txt = train (n_train) rồi val rồi test, đúng thứ tự make_split -> ghép được với nhãn của harness.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acc.tasks import make_split  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(os.environ.get("VIVYQU_HIDDEN_DIR", r"D:\models\vivyqu_hidden"))
MODEL = Path(os.environ.get("VIVYQU_HIDDEN_MODEL", r"D:\models\gemma4-e4b\vivy-gemma-e4b-q4km.textonly.gguf"))
EXE = Path(os.environ.get("VIVYQU_HIDDEN_EXE", r"D:\models\tools\hidden_extract\hidden_extract.exe"))
N_EMBD, D_CORE = 2560, 4096
LAYERS = (21, 31, 41)  # mid / ~3/4 / last (42 block) — chọn trên val (spec §3 P1)
P2_SEED = 20261004
GENC_THRESHOLD = 0.5
SPLITS = (("train", 2000), ("val", 500), ("test", 500))
_TRIU = np.triu_indices(6, 1)

TEMPLATE_VERSION = "v1-2026-10-04"


def _pairs(vals):
    return ", ".join(f"{i}-{j}:{v:.2f}" for (i, j), v in zip(zip(*_TRIU), vals))


def render(task: str, f: np.ndarray) -> str:
    """Prompt cố định, tất định từ vector đặc trưng instance (không chứa đáp án)."""
    if task == "acc1":
        w, forb = f[:15], f[15:].reshape(6, 4)
        edges = ", ".join(f"{i}-{j}:{v:.2f}" for (i, j), v in zip(zip(*_TRIU), w) if v != 0) or "none"
        fb = ", ".join(f"{v}:{c}" for v, c in zip(*np.nonzero(forb))) or "none"
        return ("Task: weighted graph 4-coloring.\\nVertices 0-5, colors 0-3.\\n"
                f"Edges (u-v:weight): {edges}\\nForbidden (vertex:color): {fb}\\n"
                "Goal: choose colors that minimize the total weight of edges whose endpoints share a color.\\nAnswer:")
    if task == "acc2":
        j, h, c, s = f[:15], f[15:21], f[21:27], f[27:33]
        deg = np.rint(np.degrees(np.arctan2(s, c))).astype(int)
        return ("Task: 6 coupled 4-state clock spins.\\n"
                f"Couplings J (i-j:value): {_pairs(j)}\\n"
                f"Fields h: {', '.join(f'{i}:{v:.2f}' for i, v in enumerate(h))}\\n"
                f"Phase offsets in degrees: {', '.join(f'{i}:{d}' for i, d in enumerate(deg))}\\n"
                "Goal: find the spin configuration with minimum energy.\\nAnswer:")
    if task == "acc3":
        p = int(round(f[0] * 4096))
        g, hh = int(round(f[1] * p)), int(round(f[2] * p))
        return f"Task: discrete logarithm.\\nFind x such that {g}^x = {hh} (mod {p}).\\nAnswer: x ="
    raise ValueError(task)


def _dir(task, seed):
    return ROOT / f"{task}_s{seed}"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_feats(task, seed):
    feats = []
    for split, n in SPLITS:
        feats.append(np.stack([s.features for s in make_split(task, split, n, seed)]))
    return feats


def cmd_prompts(a):
    d = _dir(a.task, a.seed)
    d.mkdir(parents=True, exist_ok=True)
    feats = load_feats(a.task, a.seed)
    lines = [render(a.task, f) for F in feats for f in F]
    if any("\n" in x or "\r" in x for x in lines):
        raise RuntimeError("prompt chứa xuống dòng thật — vi phạm định dạng 1 dòng/prompt")
    text = "\n".join(lines) + "\n"
    pf = d / "prompts.txt"
    if pf.exists() and pf.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{pf} đã tồn tại với nội dung khác — từ chối ghi đè (sẽ lệch hidden-state đã trích)")
    pf.write_text(text, encoding="utf-8", newline="\n")
    man = {"task": a.task, "seed": a.seed, "splits": dict(SPLITS), "template_version": TEMPLATE_VERSION,
           "prompt_template_sha": _sha(inspect.getsource(render).encode("utf-8")),
           "prompts_sha": _sha(text.encode("utf-8")),
           "features_sha": _sha(b"".join(np.ascontiguousarray(F).tobytes() for F in feats)),
           "example": lines[0]}
    (d / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(man, indent=1, ensure_ascii=False))


def _model_sha(path: Path) -> str:
    cache = path.with_suffix(path.suffix + ".sha256")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        return cache.read_text().strip()
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    cache.write_text(h.hexdigest())
    return h.hexdigest()


def cmd_extract(a):
    d = _dir(a.task, a.seed)
    if not (d / "prompts.txt").exists():
        raise SystemExit("chưa có prompts.txt — chạy 'prompts' trước")
    cmd = [str(EXE), "-m", str(MODEL), "-i", str(d / "prompts.txt"), "-o", str(d),
           "-l", ",".join(map(str, a.layers)), "-t", str(a.threads), "-c", "512"]
    t0 = time.time()
    with open(d / "extract.log", "ab") as log:
        rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
    if rc != 0:
        raise SystemExit(f"hidden_extract thoát mã {rc} — xem {d / 'extract.log'}")
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    man.update(model=str(MODEL), model_sha=_model_sha(MODEL), exe_sha=_sha(EXE.read_bytes()), layers=list(a.layers),
               dtype="float32 residual l_out token cuối", quant="Q4_K_M (text-only strip)",
               extract_seconds_last_run=round(time.time() - t0, 1))
    (d / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("model_sha", "layers", "extract_seconds_last_run")}, indent=1))


def p2_projection(seed=P2_SEED):
    """Ma trận (2560, 4096) cột-trực-chuẩn cố định: z = x_std @ P  (P @ P.T = I_2560, bảo toàn hình học)."""
    q, _ = np.linalg.qr(np.random.default_rng(seed).standard_normal((D_CORE, N_EMBD)))
    return q.T.astype(np.float64)


def ridge_fit(X, Y, alpha):
    xm, ym = X.mean(0), Y.mean(0)
    Xc = X - xm
    W = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ (Y - ym))
    return W, xm, ym


def r2(Y, P, keep):
    ss_res = ((Y - P) ** 2).sum(0)
    ss_tot = ((Y - Y.mean(0)) ** 2).sum(0)
    per = 1 - ss_res[keep] / ss_tot[keep]
    return float(per.mean()), per


def genc_layer(H_tr, H_va, F_tr, F_va, rng):
    mu, sd = H_tr.mean(0), H_tr.std(0) + 1e-6
    P = p2_projection()
    Z_tr, Z_va = ((H_tr - mu) / sd) @ P, ((H_va - mu) / sd) @ P
    keep = F_tr.std(0) > 1e-9  # bỏ cột hằng (ví dụ h=0) khỏi R²
    # chọn alpha bằng holdout NỘI BỘ train (20% cuối) — val chỉ dùng để báo cáo
    cut = int(0.8 * len(Z_tr))
    scores = {}
    for alpha in (1.0, 10.0, 100.0, 1000.0, 10000.0):
        W, xm, ym = ridge_fit(Z_tr[:cut], F_tr[:cut], alpha)
        scores[alpha] = r2(F_tr[cut:], (Z_tr[cut:] - xm) @ W + ym, keep)[0]
    alpha = max(scores, key=scores.get)
    W, xm, ym = ridge_fit(Z_tr, F_tr, alpha)
    r2_val, per = r2(F_va, (Z_va - xm) @ W + ym, keep)
    # P6: xáo hàng nhãn train -> phải ~0 (hoặc âm) trên val thật
    Wn, xmn, ymn = ridge_fit(Z_tr, F_tr[rng.permutation(len(F_tr))], alpha)
    r2_neg, _ = r2(F_va, (Z_va - xmn) @ Wn + ymn, keep)
    return {"alpha": alpha, "alpha_holdout_r2": scores, "r2_val": r2_val, "r2_val_per_feature": per.tolist(),
            "p6_shuffled_r2_val": r2_neg, "pass": bool(r2_val >= GENC_THRESHOLD and r2_neg < 0.1)}


def load_hidden(d, il, n_total):
    fp = d / f"L{il}.f32"
    H = np.fromfile(fp, np.float32)
    if H.size != n_total * N_EMBD:
        raise SystemExit(f"{fp}: {H.size // N_EMBD} hàng, cần {n_total} — trích xuất chưa xong?")
    return H.reshape(n_total, N_EMBD).astype(np.float64)


def cmd_genc(a):
    d = _dir(a.task, a.seed)
    F_tr, F_va, _ = load_feats(a.task, a.seed)  # test KHÔNG dùng ở G-ENC
    n_tr, n_va = len(F_tr), len(F_va)
    n_total = sum(n for _, n in SPLITS)
    rng = np.random.default_rng(a.seed + 17)
    out = {"task": a.task, "seed": a.seed, "threshold": GENC_THRESHOLD, "p2_seed": P2_SEED,
           "p2_sha": _sha(p2_projection().tobytes()), "layers": {}}
    for il in a.layers:
        H = load_hidden(d, il, n_total)
        if not np.isfinite(H).all():
            raise SystemExit(f"L{il}: có giá trị không hữu hạn")
        out["layers"][il] = genc_layer(H[:n_tr], H[n_tr:n_tr + n_va], F_tr, F_va, rng)
        print(f"[G-ENC {a.task} s{a.seed}] L{il}: R2_val={out['layers'][il]['r2_val']:.3f} "
              f"P6={out['layers'][il]['p6_shuffled_r2_val']:.3f} alpha={out['layers'][il]['alpha']}", flush=True)
    best = max(out["layers"], key=lambda k: out["layers"][k]["r2_val"])
    out.update(best_layer=best, genc_pass=out["layers"][best]["pass"])
    (d / "genc.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("best_layer", "genc_pass", "p2_sha")}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("prompts", "extract", "genc"))
    ap.add_argument("--task", choices=("acc1", "acc2", "acc3"), required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--layers", type=int, nargs="+", default=list(LAYERS))
    ap.add_argument("--threads", type=int, default=6)
    a = ap.parse_args(argv)
    {"prompts": cmd_prompts, "extract": cmd_extract, "genc": cmd_genc}[a.cmd](a)


if __name__ == "__main__":
    main()
