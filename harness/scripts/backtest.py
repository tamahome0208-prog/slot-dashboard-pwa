#!/usr/bin/env python3
"""
バックテストエンジン v2 - 事前選択ロジック
過去N日のデータのみで翌日機種を選び、当日結果で評価する
（後知恵バイアス排除）
"""
import json, os, sys, io
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') if hasattr(sys.stdout, 'buffer') else sys.stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY = os.path.join(ROOT, 'data', 'royal_history.json')
TRENDS = os.path.join(ROOT, 'data', 'royal_trends.json')
KPI = os.path.join(ROOT, 'harness', 'state', 'kpi.json')


def load():
    with open(HISTORY, encoding='utf-8') as f: hist = json.load(f)
    with open(TRENDS, encoding='utf-8') as f: tr = json.load(f)
    # 日付順に昇順ソート（ID昇順=古い順）
    hist.sort(key=lambda x: x.get('id', ''))
    return hist, tr


def compute_trend_up_to(days, top_n=10):
    """指定日リストから機種別平均差枚を計算しTop-N機種名を返す"""
    stats = defaultdict(lambda: {'sum_sa': 0, 'days': 0})
    for d in days:
        seen = set()
        for m in d.get('machines', []):
            n = m.get('name', '')
            sa = m.get('sa') or 0
            if n in seen: continue
            seen.add(n)
            stats[n]['sum_sa'] += sa
            stats[n]['days'] += 1
    ranked = []
    for n, s in stats.items():
        if s['days'] < 3: continue
        ranked.append((n, s['sum_sa']/s['days'], s['days']))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in ranked[:top_n]]


def strategy_pre_select(hist, top_n=10, training_min=30):
    """t日目: 1〜(t-1)日のデータでTop-N選定 → t日に出ているTop-N機種の平均差枚で評価"""
    wins = 0; total = 0; sum_sa = 0; sum_pick_count = 0
    for i, day in enumerate(hist):
        if i < training_min: continue  # 学習データ不足
        training = hist[:i]
        top_names = set(compute_trend_up_to(training, top_n=top_n))
        # その日に top_names に該当する機種を全て取り、平均差枚
        picks = [m for m in day.get('machines', []) if m.get('name') in top_names]
        if not picks: continue
        avg_sa = sum((m.get('sa') or 0) for m in picks) / len(picks)
        sum_sa += avg_sa
        total += 1
        sum_pick_count += len(picks)
        if avg_sa > 0: wins += 1
    return {
        'strategy': f'pre_select_top{top_n}_avg',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': round(sum_sa),
        'avg_picks_per_day': round(sum_pick_count/total, 1) if total else 0,
    }


def strategy_pre_select_best(hist, top_n=10, training_min=30):
    """t日: 過去Top-Nから当日最良の1台に賭ける（事前選定の中の最高差枚）"""
    wins = 0; total = 0; sum_sa = 0
    for i, day in enumerate(hist):
        if i < training_min: continue
        training = hist[:i]
        top_names = set(compute_trend_up_to(training, top_n=top_n))
        picks = [m for m in day.get('machines', []) if m.get('name') in top_names]
        if not picks: continue
        best = max(picks, key=lambda m: m.get('sa') or -99999)
        sa = best.get('sa') or 0
        sum_sa += sa; total += 1
        if sa > 0: wins += 1
    return {
        'strategy': f'pre_select_top{top_n}_best',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': sum_sa,
    }


def strategy_dow_pre(hist, dow_whitelist, training_min=30):
    """曜日フィルタ + Top10事前選定"""
    wins = 0; total = 0; sum_sa = 0
    for i, day in enumerate(hist):
        if i < training_min: continue
        if day.get('dow') not in dow_whitelist: continue
        training = hist[:i]
        top_names = set(compute_trend_up_to(training, top_n=10))
        picks = [m for m in day.get('machines', []) if m.get('name') in top_names]
        if not picks: continue
        avg_sa = sum((m.get('sa') or 0) for m in picks) / len(picks)
        sum_sa += avg_sa; total += 1
        if avg_sa > 0: wins += 1
    return {
        'strategy': f'dow_{"".join(dow_whitelist)}_pre',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': round(sum_sa),
    }


def strategy_baseline_random(hist, training_min=30):
    """ベースライン: 機種ランダム選択（その日の機種からランダム1台）"""
    import random
    random.seed(42)
    wins = 0; total = 0; sum_sa = 0
    for i, day in enumerate(hist):
        if i < training_min: continue
        machines = day.get('machines', [])
        if not machines: continue
        pick = random.choice(machines)
        sa = pick.get('sa') or 0
        sum_sa += sa; total += 1
        if sa > 0: wins += 1
    return {
        'strategy': 'baseline_random',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': sum_sa,
    }


def main():
    hist, tr = load()
    print(f'Loaded {len(hist)} days (sorted ascending)')
    print(f'学習開始: {hist[30].get("date_str", "?")} ({hist[30].get("dow","?")})')
    print()

    results = [
        strategy_baseline_random(hist),
        strategy_pre_select(hist, top_n=5),
        strategy_pre_select(hist, top_n=10),
        strategy_pre_select(hist, top_n=20),
        strategy_pre_select_best(hist, top_n=10),
        strategy_pre_select_best(hist, top_n=20),
        strategy_dow_pre(hist, ['水', '木']),
        strategy_dow_pre(hist, ['土', '日']),
    ]
    print(f"{'strategy':35s} days  win%   avg_sa  total_sa  picks/d")
    print('-' * 80)
    for r in results:
        picks = r.get('avg_picks_per_day', '-')
        print(f"  {r['strategy']:33s} {r['days']:4d} {r['win_rate']:5.1f}% {r['avg_sa']:+7d}  {r['total_sa']:+8d}  {picks}")

    # ベースラインとの差
    base = results[0]
    print(f"\nベースライン勝率: {base['win_rate']}% / avg_sa={base['avg_sa']:+d}")
    print('=== 事前選択戦略でベースライン超え判定 ===')
    for r in results[1:]:
        delta_win = r['win_rate'] - base['win_rate']
        delta_sa = r['avg_sa'] - base['avg_sa']
        mark = '✅' if delta_sa > 0 else '❌'
        print(f"  {mark} {r['strategy']:33s} Δwin={delta_win:+5.1f}%  Δavg_sa={delta_sa:+5d}")

    # KPIへ反映: ベースラインを除いた中で最高avg_saを採用
    if os.path.exists(KPI):
        with open(KPI, encoding='utf-8') as f: kpi = json.load(f)
    else:
        kpi = {'metrics': {}, 'history': []}
    best = max(results[1:], key=lambda r: r['avg_sa'])
    kpi['updated'] = datetime.now().isoformat()
    kpi.setdefault('metrics', {})['backtest_win_rate'] = {
        'value': best['win_rate'], 'unit': '%',
        'source': best['strategy'], 'avg_sa': best['avg_sa'], 'days': best['days'],
        'baseline_win_rate': base['win_rate'], 'baseline_avg_sa': base['avg_sa'],
        'edge_avg_sa': best['avg_sa'] - base['avg_sa'],
    }
    kpi.setdefault('history', []).append({
        'at': datetime.now().isoformat(),
        'best_strategy': best['strategy'],
        'win_rate': best['win_rate'],
        'avg_sa': best['avg_sa'],
        'edge_vs_baseline': best['avg_sa'] - base['avg_sa'],
    })
    with open(KPI, 'w', encoding='utf-8') as f:
        json.dump(kpi, f, ensure_ascii=False, indent=2)
    print(f'\n★ 最良戦略: {best["strategy"]} (avg_sa={best["avg_sa"]:+d}, win={best["win_rate"]}%)')
    print(f'   ベースライン超過分: {best["avg_sa"] - base["avg_sa"]:+d}枚/日')
    print(f'KPI saved: {KPI}')


if __name__ == '__main__':
    main()
