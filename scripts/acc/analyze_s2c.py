# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — phân tích pre-register H5/H6 (spec §8.12), viết & commit TRƯỚC khi chạy s2c
"""Dùng: python scripts/acc/analyze_s2c.py [--tasks acc1 acc2 acc3] [--out results/acc_s2c_analysis.json]

Tiêu chí (khóa ở spec §8.12, không đổi sau khi thấy dữ liệu):
  C1 (H5 ủng hộ, theo §4, chỉ dùng top-1): trên test OOD, CI95 gộp của H5_qudit_interact nằm hoàn toàn TRÊN CI95 gộp
     của từng arm H1, H2, H4, H6_qubit_interact; H5 có 0 vi phạm mask. Đạt ở >= 2/3 bài -> ủng hộ (phạm vi P5/Q1).
  C2 (Δ_interaction): hiệu ghép cặp theo mẫu H5_qudit_interact − H5_qudit_additive; đóng góp nếu CI95 dưới > 0 ở >= 2/3 bài.
  C3 (báo cáo, không quyết định): Δ_qudit = H5_qudit_interact − H6_qubit_interact ghép cặp.
Bắt buộc: dataset_sha từng seed của s2b và s2c phải trùng (cùng dữ liệu test), nếu không -> dừng, không kết luận.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acc import harness as H  # noqa: E402

RESULTS = Path(__file__).resolve().parents[2] / "results"
H5I, H5A, H6I = "H5_qudit_interact", "H5_qudit_additive", "H6_qubit_interact"
RIVALS = ("H1_linear_rank64", "H2_mlp_param_matched", "H4_e9_no_rotor", H6I)


def pooled(runs, arm):
    return np.concatenate([np.asarray(r["arms"][arm]["ok"], float) for r in runs])


def analyze_task(task, s2b, s2c):
    rb, rc = s2b["runs"], s2c["runs"]
    if len(rb) != len(rc):
        raise SystemExit(f"{task}: số seed khác nhau ({len(rb)} vs {len(rc)})")
    for a, b in zip(rb, rc):
        if a["seed"] != b["seed"] or a["dataset_sha"] != b["dataset_sha"]:
            raise SystemExit(f"{task}: dataset_sha seed {a['seed']} không khớp -> dữ liệu test khác, dừng")
    runs = {**{k: rb for k in rb[0]["arms"] if "ok" in rb[0]["arms"][k]},
            **{k: rc for k in rc[0]["arms"] if "ok" in rc[0]["arms"][k]}}
    ok = {k: pooled(v, k) for k, v in runs.items()}
    ci = {k: H.bootstrap_ci(v) for k, v in ok.items()}
    viol = {k: int(sum(r["arms"][k]["mask_violations"] for r in runs[k])) for k in runs}
    beats = {r: bool(ci[H5I][0] > ci[r][1]) for r in RIVALS}
    c1 = viol[H5I] == 0 and all(beats.values())
    d_int = ok[H5I] - ok[H5A]
    d_qud = ok[H5I] - ok[H6I]
    ci_int, ci_qud = H.bootstrap_ci(d_int), H.bootstrap_ci(d_qud)
    return {
        "top1_pooled": {k: float(v.mean()) for k, v in ok.items()},
        "ci95_pooled": ci,
        "mask_violations": viol,
        "C1_beats": beats,
        "C1_pass": c1,
        "delta_interaction": {"mean": float(d_int.mean()), "ci95": ci_int, "C2_pass": bool(ci_int[0] > 0)},
        "delta_qudit_vs_qubit": {"mean": float(d_qud.mean()), "ci95": ci_qud},
        "n_pooled": int(len(ok[H5I])),
        "params": {k: runs[k][0]["arms"][k]["params"] for k in runs},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", default=["acc1", "acc2", "acc3"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    per = {}
    for t in a.tasks:
        s2b = json.loads((RESULTS / f"acc_s2b_{t}.json").read_text(encoding="utf-8"))
        s2c = json.loads((RESULTS / f"acc_s2c_{t}.json").read_text(encoding="utf-8"))
        per[t] = analyze_task(t, s2b, s2c)
    n = len(per)
    n_c1 = sum(v["C1_pass"] for v in per.values())
    n_c2 = sum(v["delta_interaction"]["C2_pass"] for v in per.values())
    verdict = {
        "tasks_evaluated": n,
        "final": n == 3,
        "C1_tasks_passed": n_c1,
        "C2_tasks_passed": n_c2,
        "H5_supported_P5_Q1": (n_c1 >= 2) if n == 3 else None,
        "interaction_contributes": (n_c2 >= 2) if n == 3 else None,
    }
    out = {"verdict": verdict, "per_task": per}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
