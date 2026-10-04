# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — S2 runner: chạy arm H0/H1/H2/H7 trên P5, xuất bảng + manifest
# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Revision: thêm H3/H4, tune lr đồng đều (--tune), CI95 gộp theo mẫu
# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Thêm --suite s2c (H5/H6, pre-register spec §8.12); s2b giữ nguyên hành vi + tên file
# Changelog: 2026-10-04 08:22 | Antigravity (Claude Opus 5.5) | Thêm --suite s2d (spec §8.13): seed 5–9, H+V, lệch cấu trúc
"""Chạy:
  python scripts/acc/run_s2.py --task acc1 --tune          # chọn lr/arm trên VAL của seed 0 (lưới chung 3 giá trị)
  python scripts/acc/run_s2.py --task acc1 --seeds 5 --out results/acc_s2b_acc1.json   # dùng lr đã tune
  python scripts/acc/run_s2.py --suite s2c --task acc1 --tune / --out results/acc_s2c_acc1.json   # H5/H6
  python scripts/acc/run_s2.py --suite s2d --task acc1 --tune   # chỉ tune 2 arm mới (val seed 0)
  python scripts/acc/run_s2.py --suite s2d --task acc1 --seed-start 5 --seeds 5 --out results/acc_s2d_acc1.json
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


SUITES = ("s2b", "s2c", "s2d")
S2D_SEED_MIN = 5  # §8.13: seed 0–4 đã dùng test cho s2b/s2c -> S2d chỉ dùng seed mới
S2D_OLD = ("H1_linear_rank64", "H2_mlp_param_matched", "H4_e9_no_rotor")  # lr từ acc_s2_tune_*
S2D_S2C = ("H5_qudit_interact", "H6_qubit_interact")                       # lr từ acc_s2c_tune_*


def arm_factories(ref_params, suite="s2b"):
    if suite == "s2c":
        return {n: (lambda s, n=n: H.FactorArm(n, s)) for n in H.FACTOR_SPECS}
    base = {
        "H1_linear_rank64": lambda s: H.LinearRank(64, s),
        "H2_mlp_param_matched": lambda s: H.MLP(ref_params, s),
        "H3_e9_core": lambda s: H.E9CoreArm(True, s),
        "H4_e9_no_rotor": lambda s: H.E9CoreArm(False, s),
    }
    if suite == "s2d":
        out = {n: base[n] for n in S2D_OLD}
        out.update({n: (lambda s, n=n: H.FactorArm(n, s)) for n in S2D_S2C + tuple(H.FACTOR_SPECS_S2D)})
        return out
    return base


def tune_file(task, suite):
    return RESULTS / (f"acc_s2_tune_{task}.json" if suite == "s2b" else f"acc_{suite}_tune_{task}.json")


def load_lrs(task, suite):
    """lr đã tune. s2d ghép 3 nguồn (arm cũ giữ nguyên lr, arm mới tune riêng) — thiếu file nào thì dừng."""
    files = [tune_file(task, suite)] if suite != "s2d" else [tune_file(task, "s2b"), tune_file(task, "s2c"),
                                                             tune_file(task, "s2d")]
    lrs, shas = {}, {}
    for tf in files:
        if not tf.exists():
            raise SystemExit(f"Thiếu {tf}: chạy --tune trước (không được chạy test khi chưa tune đồng đều).")
        lrs.update({k: v["lr"] for k, v in json.loads(tf.read_text(encoding="utf-8")).items()})
        shas[tf.name] = hashlib.sha256(tf.read_bytes()).hexdigest()
    return lrs, shas


def load_data(task, seed, ntr, nva, nte):
    tr, va, te = (make_split(task, s, n, seed) for s, n in (("train", ntr), ("val", nva), ("test", nte)))
    ftr, mtr, ctr = H.stack(tr)
    fva, mva, cva = H.stack(va)
    fte, mte, cte = H.stack(te)
    p5 = H.P5Latent(ftr.shape[1]).fit(ftr)
    return dict(te=te, ftr=ftr, fte=fte, cte=cte, mte=mte, ctr=ctr, mtr=mtr, mva=mva, cva=cva,
                ztr=p5(ftr), zva=p5(fva), zte=p5(fte))


def tune(task, ntr, nva, nte, epochs, suite="s2b"):
    """Chọn lr cho từng arm trên VAL (seed 0). Không chạm test."""
    d = load_data(task, 0, ntr, nva, nte)
    ref = H.LinearRank(64, 0).n_params()
    best = {}
    for name, mk in arm_factories(ref, suite).items():
        if suite == "s2d" and name not in H.FACTOR_SPECS_S2D:
            continue  # §8.13: arm đã tune giữ nguyên lr, chỉ tune arm mới
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
    tune_file(task, suite).write_text(json.dumps(best, indent=1), encoding="utf-8")
    return best


def run_seed(task, seed, ntr, nva, nte, epochs, lrs, suite="s2b"):
    t0 = time.time()
    d = load_data(task, seed, ntr, nva, nte)
    ref = H.LinearRank(64, seed).n_params()
    res = {"seed": seed, "dataset_sha": sha_arrays(d["fte"], d["cte"]), "arms": {}}
    arms = [H.Prior(d["ctr"])] + [mk(seed) for mk in arm_factories(ref, suite).values()]
    if suite == "s2d":
        arms = arms[1:]  # §8.13 không dùng H0
    for m in arms:
        if isinstance(m, H.Prior):
            log, vbest = [], None
        else:
            log, vbest = H.train_model(m, d["ztr"], d["mtr"], d["ctr"], d["zva"], d["mva"], d["cva"],
                                       epochs=epochs, lr=lrs[m.name])
        ev = H.evaluate(H.predict(m, d["zte"], d["mte"]), d["mte"], d["cte"], d["te"], task)  # test chấm 1 lần
        ev["ok"] = ev.pop("_ok").astype(int).tolist()
        if suite == "s2d" and not isinstance(m, H.Prior):
            sc = H.predict(m, d["zte"], d["mte"])  # cùng tham số, cùng điểm (tất định) — không phải chấm lại
            v = H.verify_topk(sc, d["mte"], d["cte"], d["te"], task, k=8)
            ev["passk_ok"] = v["passk_ok"].tolist()
            ev["ok_V"] = v["ok_V"].tolist()
            ev["top1_V"] = float(v["ok_V"].mean())
            ev["regret_V"] = None if v["regret_V"] is None else v["regret_V"].tolist()
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
    ap.add_argument("--suite", choices=SUITES, default="s2b")
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    if a.tune:
        tune(a.task, a.n_train, a.n_val, a.n_test, a.epochs, a.suite)
        return None
    if a.suite == "s2d" and a.seed_start < S2D_SEED_MIN:
        raise SystemExit(f"s2d chỉ được dùng seed >= {S2D_SEED_MIN} (§8.13: test seed 0–4 đã dùng).")
    lrs, tune_shas = load_lrs(a.task, a.suite)
    seeds = list(range(a.seed_start, a.seed_start + a.seeds))
    runs = [run_seed(a.task, s, a.n_train, a.n_val, a.n_test, a.epochs, lrs, a.suite) for s in seeds]
    manifest = {"task": a.task, "commit": git_sha(), "python": platform.python_version(),
                "numpy": np.__version__, "cpu": platform.processor(), "seeds": seeds,
                "n": [a.n_train, a.n_val, a.n_test], "epochs": a.epochs, "latent": "P5",
                "p5_seed": H.P5_SEED, "lr_grid": list(LR_GRID), "tuned_lr": lrs,
                "tune_file_sha": tune_shas if a.suite == "s2d" else next(iter(tune_shas.values())),
                "suite": a.suite,
                "arms_missing": {"s2b": ["H5", "H6"], "s2c": ["H1-H4 (xem acc_s2b_*.json)"],
                                 "s2d": ["H0", "H3", "H5_qudit_additive"]}[a.suite],
                "misaligned_perm": H.misaligned_perm().tolist() if a.suite == "s2d" else None,
                "dll_sha256": "N/A (H3 là bản NumPy train được, không dùng DLL Core)"}
    out = {"manifest": manifest, "summary": summarize(runs), "runs": runs}
    print(json.dumps({"manifest": manifest, "summary": out["summary"]}, indent=1, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
