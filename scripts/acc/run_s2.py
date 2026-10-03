# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S2 runner: chạy arm H0/H1/H2/H7 trên P5, xuất bảng + manifest
# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Revision: thêm H3/H4, tune lr đồng đều (--tune), CI95 gộp theo mẫu
"""Chạy:
  python scripts/acc/run_s2.py --task acc1 --tune          # chọn lr/arm trên VAL của seed 0 (lưới chung 3 giá trị)
  python scripts/acc/run_s2.py --task acc1 --seeds 5 --out results/acc_s2b_acc1.json   # dùng lr đã tune
Test (OOD) chỉ được chấm MỘT lần/arm/seed, sau khi train xong. Lưới lr và số lần thử giống nhau cho mọi arm."""
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

LR_GRID = (5e-4, 2e-3, 8e-3)  # khóa trước khi chạy; mọi arm có đúng 3 lần thử
RESULTS = Path(__file__).resolve().parents[2] / "results"


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


def arm_factories(ref_params):
    return {
        "H1_linear_rank64": lambda s: H.LinearRank(64, s),
        "H2_mlp_param_matched": lambda s: H.MLP(ref_params, s),
        "H3_e9_core": lambda s: H.E9CoreArm(True, s),
        "H4_e9_no_rotor": lambda s: H.E9CoreArm(False, s),
    }


def load_data(task, seed, ntr, nva, nte):
    tr, va, te = (make_split(task, s, n, seed) for s, n in (("train", ntr), ("val", nva), ("test", nte)))
    ftr, mtr, ctr = H.stack(tr)
    fva, mva, cva = H.stack(va)
    fte, mte, cte = H.stack(te)
    p5 = H.P5Latent(ftr.shape[1]).fit(ftr)
    return dict(te=te, ftr=ftr, fte=fte, cte=cte, mte=mte, ctr=ctr, mtr=mtr, mva=mva, cva=cva,
                ztr=p5(ftr), zva=p5(fva), zte=p5(fte))


def tune(task, ntr, nva, nte, epochs):
    """Chọn lr cho từng arm trên VAL (seed 0). Không chạm test."""
    d = load_data(task, 0, ntr, nva, nte)
    ref = H.LinearRank(64, 0).n_params()
    best = {}
    for name, mk in arm_factories(ref).items():
        trials = []
        for lr in LR_GRID:
            m = mk(0)
            _, v = H.train_model(m, d["ztr"], d["mtr"], d["ctr"], d["zva"], d["mva"], d["cva"],
                                 epochs=epochs, lr=lr)
            trials.append({"lr": lr, "val_top1": v})
            print(f"[tune {task}] {name} lr={lr}: val_top1={v:.3f}", flush=True)
        b = max(trials, key=lambda t: t["val_top1"])
        best[name] = {"lr": b["lr"], "val_top1": b["val_top1"], "trials": trials}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"acc_s2_tune_{task}.json").write_text(json.dumps(best, indent=1), encoding="utf-8")
    return best


def run_seed(task, seed, ntr, nva, nte, epochs, lrs):
    t0 = time.time()
    d = load_data(task, seed, ntr, nva, nte)
    ref = H.LinearRank(64, seed).n_params()
    res = {"seed": seed, "dataset_sha": sha_arrays(d["fte"], d["cte"]), "arms": {}}
    arms = [H.Prior(d["ctr"])] + [mk(seed) for mk in arm_factories(ref).values()]
    for m in arms:
        if isinstance(m, H.Prior):
            log, vbest = [], None
        else:
            log, vbest = H.train_model(m, d["ztr"], d["mtr"], d["ctr"], d["zva"], d["mva"], d["cva"],
                                       epochs=epochs, lr=lrs[m.name])
        ev = H.evaluate(H.predict(m, d["zte"], d["mte"]), d["mte"], d["cte"], d["te"], task)  # test chấm 1 lần
        ev["ok"] = ev.pop("_ok").astype(int).tolist()
        ev.update(params=m.n_params(), val_top1=vbest, final_loss=(log[-1][1] if log else None),
                  lr=lrs.get(m.name))
        res["arms"][m.name] = ev
        print(f"  seed {seed} {m.name}: top1={ev['top1']:.3f}", flush=True)
    res["arms"]["H7_oracle"] = {"top1": float(np.mean([s.correct.any() for s in d["te"]])), "params": 0,
                                "note": "đúng theo định nghĩa (vét cạn) — trần, chỉ để kiểm tra pipeline"}
    res["seconds"] = round(time.time() - t0, 1)
    return res


def summarize(runs):
    out = {}
    for n in runs[0]["arms"]:
        a = [r["arms"][n] for r in runs]
        row = {"top1_median": float(np.median([x["top1"] for x in a])),
               "top1_per_seed": [x["top1"] for x in a], "params": a[0]["params"]}
        if "ok" in a[0]:
            pooled = np.concatenate([x["ok"] for x in a])
            row["top1_pooled"] = float(pooled.mean())
            row["ci95_pooled"] = H.bootstrap_ci(pooled)
            row["pass@8_median"] = float(np.median([x["pass@8"] for x in a]))
            if "mean_regret" in a[0]:
                row["regret_median"] = float(np.median([x["mean_regret"] for x in a]))
            row["mask_violations"] = int(sum(x["mask_violations"] for x in a))
        out[n] = row
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=list(TASKS), required=True)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=500)
    ap.add_argument("--n-test", type=int, default=500)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    if a.tune:
        tune(a.task, a.n_train, a.n_val, a.n_test, a.epochs)
        return None
    tf = RESULTS / f"acc_s2_tune_{a.task}.json"
    if not tf.exists():
        raise SystemExit(f"Thiếu {tf}: chạy --tune trước (không được chạy test khi chưa tune đồng đều).")
    tuned = json.loads(tf.read_text(encoding="utf-8"))
    lrs = {k: v["lr"] for k, v in tuned.items()}
    runs = [run_seed(a.task, s, a.n_train, a.n_val, a.n_test, a.epochs, lrs) for s in range(a.seeds)]
    manifest = {"task": a.task, "commit": git_sha(), "python": platform.python_version(),
                "numpy": np.__version__, "cpu": platform.processor(), "seeds": a.seeds,
                "n": [a.n_train, a.n_val, a.n_test], "epochs": a.epochs, "latent": "P5",
                "p5_seed": H.P5_SEED, "lr_grid": list(LR_GRID), "tuned_lr": lrs,
                "tune_file_sha": hashlib.sha256(tf.read_bytes()).hexdigest(),
                "arms_missing": ["H5", "H6"],
                "dll_sha256": "N/A (H3 là bản NumPy train được, không dùng DLL Core)"}
    out = {"manifest": manifest, "summary": summarize(runs), "runs": runs}
    print(json.dumps({"manifest": manifest, "summary": out["summary"]}, indent=1, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
