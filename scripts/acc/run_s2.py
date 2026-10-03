# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S2 runner: chạy arm H0/H1/H2/H7 trên P5, xuất bảng + manifest
"""Chạy: python scripts/acc/run_s2.py --task acc1 --seeds 5 --n-train 2000 --out results/acc_s2_acc1.json
Test (OOD) chỉ được chấm MỘT lần sau khi train xong mọi arm của seed đó."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acc import harness as H  # noqa: E402
from acc.tasks import TASKS, make_split  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[2],
                                       text=True).strip()
    except Exception as e:  # không nuốt im lặng: ghi rõ vào manifest
        return f"UNAVAILABLE({type(e).__name__})"


def sha_arrays(*arrs):
    h = hashlib.sha256()
    for a in arrs:
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def run_seed(task, seed, ntr, nva, nte, epochs):
    t0 = time.time()
    tr, va, te = (make_split(task, s, n, seed) for s, n in (("train", ntr), ("val", nva), ("test", nte)))
    ftr, mtr, ctr = H.stack(tr)
    fva, mva, cva = H.stack(va)
    fte, mte, cte = H.stack(te)
    p5 = H.P5Latent(ftr.shape[1]).fit(ftr)
    ztr, zva, zte = p5(ftr), p5(fva), p5(fte)
    arms = [H.Prior(ctr), H.LinearRank(64, seed)]
    arms.append(H.MLP(arms[1].n_params(), seed))
    res = {"seed": seed, "dataset_sha": sha_arrays(fte, cte), "arms": {}}
    for m in arms:
        if isinstance(m, H.Prior):
            log, vbest = [], None
        else:
            log, vbest = H.train_model(m, ztr, mtr, ctr, zva, mva, cva, epochs=epochs)
        sc = H.predict(m, zte, mte)  # test chấm 1 lần/arm
        ev = H.evaluate(sc, mte, cte, te, task)
        ev["ci95_top1"] = H.bootstrap_ci(ev.pop("_ok"))
        ev.update(params=m.n_params(), val_top1=vbest, final_loss=(log[-1][1] if log else None))
        res["arms"][m.name] = ev
    # H7 oracle: nghiệm exact phải luôn đúng và không vi phạm mask
    res["arms"]["H7_oracle"] = {"top1": float(np.mean([s.correct.any() for s in te])), "params": 0,
                                "note": "đúng theo định nghĩa (vét cạn) — trần, không phải đối thủ"}
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=list(TASKS), required=True)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=500)
    ap.add_argument("--n-test", type=int, default=500)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    runs = [run_seed(a.task, s, a.n_train, a.n_val, a.n_test, a.epochs) for s in range(a.seeds)]
    names = list(runs[0]["arms"])
    summary = {}
    for n in names:
        v = [r["arms"][n]["top1"] for r in runs]
        summary[n] = {"top1_median": float(np.median(v)), "top1_per_seed": v,
                      "params": runs[0]["arms"][n]["params"]}
    manifest = {"task": a.task, "commit": git_sha(), "python": platform.python_version(),
                "numpy": np.__version__, "cpu": platform.processor(), "seeds": a.seeds,
                "n": [a.n_train, a.n_val, a.n_test], "epochs": a.epochs, "latent": "P5",
                "p5_seed": H.P5_SEED, "arms_missing": ["H3", "H4", "H5", "H6"],
                "dll_sha256": "N/A (chưa có arm H3)"}
    out = {"manifest": manifest, "summary": summary, "runs": runs}
    print(json.dumps({"manifest": manifest, "summary": summary}, indent=1, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
