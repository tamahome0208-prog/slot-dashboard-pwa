#!/usr/bin/env python3
"""
8/5のつく日 実データバックテスト
data/royal_history.json をロードし、日の末尾(0-9)別に集計:
  - 当日Top1機種の差枚
  - 全機種平均差枚 (avg_sa)
  - 勝率 (Top1 sa > 0 の日比率)
末尾8/末尾5/その他 を中心に、全末尾も出力。
結果を harness/state/date_boost_evidence.json に保存。
"""
import json
import os
import sys
from collections import defaultdict
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HIST_PATH = os.path.join(ROOT, "data", "royal_history.json")
OUT_PATH = os.path.join(ROOT, "harness", "state", "date_boost_evidence.json")


def safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def analyze():
    with open(HIST_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    # 日ごとに集計 (1日 = 1レコード想定)
    # groups: key -> list of dict(top1_sa, avg_sa, win_top1)
    groups = defaultdict(list)
    all_days = []

    for rec in history:
        day = safe_int(rec.get("day"))
        if day is None:
            continue
        machines = rec.get("machines") or []
        sa_values = [m.get("sa") for m in machines if isinstance(m.get("sa"), (int, float))]
        if not sa_values:
            continue
        top1_sa = max(sa_values)
        avg_sa = sum(sa_values) / len(sa_values)
        win_top1 = 1 if top1_sa > 0 else 0
        win_avg = 1 if avg_sa > 0 else 0

        last = day % 10
        entry = {
            "day": day,
            "last": last,
            "top1_sa": top1_sa,
            "avg_sa": avg_sa,
            "win_top1": win_top1,
            "win_avg": win_avg,
            "n_machines": len(sa_values),
        }
        all_days.append(entry)

        # bucket: 末尾8 / 末尾5 / その他
        if last == 8:
            bucket = "last8"
        elif last == 5:
            bucket = "last5"
        else:
            bucket = "other"
        groups[bucket].append(entry)
        groups["all"].append(entry)
        groups[f"d{last}"].append(entry)

    summary = {}
    for key, entries in groups.items():
        if not entries:
            continue
        n = len(entries)
        summary[key] = {
            "n_days": n,
            "avg_top1_sa": round(mean(e["top1_sa"] for e in entries), 1),
            "avg_sa": round(mean(e["avg_sa"] for e in entries), 1),
            "win_rate_top1": round(mean(e["win_top1"] for e in entries), 3),
            "win_rate_avg": round(mean(e["win_avg"] for e in entries), 3),
        }

    # 比較: 末尾8/末尾5 vs その他 (last8,last5 を除いた残り)
    other_entries = [e for e in all_days if e["last"] not in (5, 8)]
    if other_entries:
        baseline_avg_sa = mean(e["avg_sa"] for e in other_entries)
        baseline_top1 = mean(e["top1_sa"] for e in other_entries)
    else:
        baseline_avg_sa = 0
        baseline_top1 = 0

    diff = {}
    for key in ("last8", "last5"):
        if key in summary:
            diff[key] = {
                "avg_sa_diff_vs_other": round(summary[key]["avg_sa"] - baseline_avg_sa, 1),
                "top1_sa_diff_vs_other": round(summary[key]["avg_top1_sa"] - baseline_top1, 1),
            }

    # 全末尾(0-9)も diff を出す
    per_last = {}
    for d in range(10):
        k = f"d{d}"
        if k in summary:
            others = [e for e in all_days if e["last"] != d]
            base = mean(e["avg_sa"] for e in others) if others else 0
            per_last[k] = {
                **summary[k],
                "avg_sa_diff_vs_others": round(summary[k]["avg_sa"] - base, 1),
            }

    result = {
        "generated_from": "data/royal_history.json",
        "total_days": len(all_days),
        "buckets": summary,
        "diff_vs_other": diff,
        "per_last_digit": per_last,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 標準出力
    print(f"Total days analyzed: {len(all_days)}")
    print("\n=== Bucket summary ===")
    for k in ("last8", "last5", "other", "all"):
        if k in summary:
            s = summary[k]
            print(f"  {k:6s} n={s['n_days']:3d}  avg_top1_sa={s['avg_top1_sa']:7.1f}  avg_sa={s['avg_sa']:6.1f}  win_top1={s['win_rate_top1']:.3f}")
    print("\n=== Diff vs other (excluding last5 & last8) ===")
    for k, v in diff.items():
        print(f"  {k}: avg_sa diff = {v['avg_sa_diff_vs_other']:+.1f},  top1 diff = {v['top1_sa_diff_vs_other']:+.1f}")
    print("\n=== Per last digit ===")
    for d in range(10):
        k = f"d{d}"
        if k in per_last:
            s = per_last[k]
            print(f"  末尾{d}: n={s['n_days']:3d}  avg_sa={s['avg_sa']:6.1f}  diff={s['avg_sa_diff_vs_others']:+6.1f}  win_top1={s['win_rate_top1']:.3f}")

    print(f"\nSaved -> {OUT_PATH}")
    return result


if __name__ == "__main__":
    analyze()
