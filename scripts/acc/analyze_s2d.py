# Changelog: 2026-10-04 08:25 | Antigravity (Claude Opus 5.5) | Tạo mới — phân tích pre-register S2d (spec §8.13), viết & commit TRƯỚC khi chạy seed 5–9
"""Dùng: python scripts/acc/analyze_s2d.py [--tasks acc1 acc2 acc3] [--out results/acc_s2d_analysis.json]

Tiêu chí (khóa ở spec §8.13, không đổi sau khi thấy dữ liệu):
  D1-C (H+V ủng hộ H5): CI95 gộp top1_V (ok_V theo mẫu) của H5_qudit_interact nằm hoàn toàn TRÊN CI95 gộp top1_V
       của từng arm H1, H2, H4, H6_qubit_interact; H5 có 0 vi phạm mask. Đạt ở >= 2/3 bài.
  D1-L: độ trễ C++ — script này KHÔNG đo; luôn ghi "[CHƯA ĐO]" cho tới khi có bản C++.
  D2-A: Δ_align = ok(H5_qudit_interact) − ok(H5_qudit_misaligned) ghép cặp theo mẫu (top-1). Một bài "đạt" khi
       cận dưới CI95 > 0 VÀ H5_qudit_misaligned không vượt H6_qubit_interact (CI dưới của misaligned <= CI trên của H6).
       Đạt ở >= 2/3 bài -> nhãn "[ƯU THẾ ĐẾN TỪ CẤU TRÚC BIẾT TRƯỚC, KHÔNG PHẢI QUDIT]".
       (Diễn giải: hai điều kiện xét trên CÙNG một bài — chặt hơn cách đọc tách rời.)
  D2-Q: Δ = ok(H5_qudit_interact) − ok(H6_qubit_order4) ghép cặp (top-1). Một bài "đạt" khi cận dưới CI95 <= 0
       (chứa 0 hoặc âm). Đạt ở >= 2/3 bài -> nhãn "[QUDIT KHÔNG HƠN QUBIT ĐỦ BẬC]".
Kiểm tra toàn vẹn (dừng nếu sai): seed >= 5; cùng tập arm và cùng số mẫu mọi seed; ok_V == passk_ok theo từng mẫu
(verifier exact chọn đúng khi và chỉ khi top-K chứa đáp án — xem harness.verify_topk).
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
H5I, H5M = "H5_qudit_interact", "H5_qudit_misaligned"
H6I, H6Q4 = "H6_qubit_interact", "H6_qubit_order4"
RIVALS_V = ("H1_linear_rank64", "H2_mlp_param_matched", "H4_e9_no_rotor", H6I)
REQUIRED = RIVALS_V + (H5I, H5M, H6Q4)
SEED_MIN = 5
LABEL_ALIGN = "[ƯU THẾ ĐẾN TỪ CẤU TRÚC BIẾT TRƯỚC, KHÔNG PHẢI QUDIT]"
LABEL_Q = "[QUDIT KHÔNG HƠN QUBIT ĐỦ BẬC]"


def _pool(runs, arm, key):
    return np.concatenate([np.asarray(r["arms"][arm][key], float) for r in runs])


def analyze_task(task, s2d):
    runs = s2d["runs"]
    if not runs:
        raise SystemExit(f"{task}: không có run")
    for r in runs:
        if r["seed"] < SEED_MIN:
            raise SystemExit(f"{task}: seed {r['seed']} < {SEED_MIN} — vi phạm §8.13 (chạm lại test cũ)")
        miss = [a for a in REQUIRED if a not in r["arms"]]
        if miss:
            raise SystemExit(f"{task}: seed {r['seed']} thiếu arm {miss}")
        for a in REQUIRED:
            e = r["arms"][a]
            n = len(e["ok"])
            if len(e["ok_V"]) != n or len(e["passk_ok"]) != n:
                raise SystemExit(f"{task}: seed {r['seed']} {a} độ dài per-sample không khớp")
            if e["ok_V"] != e["passk_ok"]:
                raise SystemExit(f"{task}: seed {r['seed']} {a} ok_V != passk_ok — lỗi pipeline verifier, dừng")
    ok = {a: _pool(runs, a, "ok") for a in REQUIRED}
    okv = {a: _pool(runs, a, "ok_V") for a in REQUIRED}
    ci = {a: H.bootstrap_ci(v) for a, v in ok.items()}
    civ = {a: H.bootstrap_ci(v) for a, v in okv.items()}
    viol = {a: int(sum(r["arms"][a]["mask_violations"] for r in runs)) for a in REQUIRED}
    beats_v = {a: bool(civ[H5I][0] > civ[a][1]) for a in RIVALS_V}
    d1 = viol[H5I] == 0 and all(beats_v.values())
    d_align = ok[H5I] - ok[H5M]
    ci_align = H.bootstrap_ci(d_align)
    mis_not_above_h6 = bool(ci[H5M][0] <= ci[H6I][1])
    d2a = bool(ci_align[0] > 0) and mis_not_above_h6
    d_q4 = ok[H5I] - ok[H6Q4]
    ci_q4 = H.bootstrap_ci(d_q4)
    d2q = bool(ci_q4[0] <= 0)
    regret = {}
    for a in REQUIRED:
        if runs[0]["arms"][a].get("regret_V") is not None:
            regret[a] = float(np.mean(_pool(runs, a, "regret_V")))
    return {
        "top1_pooled": {a: float(v.mean()) for a, v in ok.items()},
        "ci95_top1": ci,
        "top1_V_pooled": {a: float(v.mean()) for a, v in okv.items()},
        "ci95_top1_V": civ,
        "regret_V_mean": regret or None,
        "mask_violations": viol,
        "D1_beats": beats_v,
        "D1_pass": d1,
        "D1_L": "[CHƯA ĐO]",
        "delta_align": {"mean": float(d_align.mean()), "ci95": ci_align,
                        "misaligned_not_above_H6": mis_not_above_h6, "D2A_pass": d2a},
        "delta_qudit_vs_qubit_order4": {"mean": float(d_q4.mean()), "ci95": ci_q4, "D2Q_pass": d2q},
        "H7_oracle_top1": [r["arms"].get("H7_oracle", {}).get("top1") for r in runs],
        "seeds": [r["seed"] for r in runs],
        "n_pooled": int(len(ok[H5I])),
        "params": {a: runs[0]["arms"][a]["params"] for a in REQUIRED},
    }


def verdict(per):
    n = len(per)
    final = n == 3
    n1 = sum(v["D1_pass"] for v in per.values())
    na = sum(v["delta_align"]["D2A_pass"] for v in per.values())
    nq = sum(v["delta_qudit_vs_qubit_order4"]["D2Q_pass"] for v in per.values())
    labels = []
    if final and na >= 2:
        labels.append(LABEL_ALIGN)
    if final and nq >= 2:
        labels.append(LABEL_Q)
    return {"tasks_evaluated": n, "final": final, "D1_tasks_passed": n1, "D2A_tasks_passed": na,
            "D2Q_tasks_passed": nq, "H5_supported_HV": (n1 >= 2) if final else None,
            "D1_L": "[CHƯA ĐO]", "labels": labels}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", default=["acc1", "acc2", "acc3"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    per = {t: analyze_task(t, json.loads((RESULTS / f"acc_s2d_{t}.json").read_text(encoding="utf-8")))
           for t in a.tasks}
    out = {"verdict": verdict(per), "per_task": per}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
