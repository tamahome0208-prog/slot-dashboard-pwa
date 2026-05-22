#!/usr/bin/env python3
"""
バックテストエンジン
royal_history.json に対して「上位機種を毎日狙う」戦略の勝率を計算
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
    return hist, tr


def strategy_top_n(hist, trends, n=5):
    """毎日Top-N機種から最良差枚を取った場合の勝率"""
    # トレンドTopの機種名集合
    top_names = {x['name'] for x in trends.get('top', [])[:n]}
    wins = 0; total = 0; sum_sa = 0
    for day in hist:
        machines = [m for m in day.get('machines', []) if any(t in m['name'] or m['name'] in t for t in top_names)]
        if not machines: continue
        best = max(machines, key=lambda m: m.get('sa') or -99999)
        sa = best.get('sa') or 0
        sum_sa += sa
        total += 1
        if sa > 0: wins += 1
    return {
        'strategy': f'top_{n}_best_pick',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': sum_sa,
    }


def strategy_dow_filter(hist, dow_whitelist):
    """指定曜日のみ参戦戦略"""
    wins = 0; total = 0; sum_sa = 0
    for day in hist:
        if day.get('dow') not in dow_whitelist: continue
        machines = day.get('machines', [])
        if not machines: continue
        best = max(machines, key=lambda m: m.get('sa') or -99999)
        sa = best.get('sa') or 0
        sum_sa += sa
        total += 1
        if sa > 0: wins += 1
    return {
        'strategy': f'dow_{"".join(dow_whitelist)}',
        'days': total,
        'win_rate': round(wins/total*100, 1) if total else 0,
        'avg_sa': round(sum_sa/total) if total else 0,
        'total_sa': sum_sa,
    }


def main():
    hist, tr = load()
    print(f'Loaded {len(hist)} days')
    results = [
        strategy_top_n(hist, tr, 5),
        strategy_top_n(hist, tr, 10),
        strategy_top_n(hist, tr, 20),
        strategy_dow_filter(hist, ['水', '木']),
        strategy_dow_filter(hist, ['土', '日']),
    ]
    for r in results:
        print(f"  {r['strategy']:30s} days={r['days']:3d} win={r['win_rate']:5.1f}% avg_sa={r['avg_sa']:+5d}")

    # KPIへ反映
    if os.path.exists(KPI):
        with open(KPI, encoding='utf-8') as f: kpi = json.load(f)
    else:
        kpi = {'metrics': {}, 'history': []}
    best = max(results, key=lambda r: r['win_rate'])
    kpi['updated'] = datetime.now().isoformat()
    kpi.setdefault('metrics', {})['backtest_win_rate'] = {
        'value': best['win_rate'], 'unit': '%',
        'source': best['strategy'], 'avg_sa': best['avg_sa'], 'days': best['days']
    }
    kpi.setdefault('history', []).append({
        'at': datetime.now().isoformat(),
        'best_strategy': best['strategy'],
        'win_rate': best['win_rate'],
    })
    with open(KPI, 'w', encoding='utf-8') as f:
        json.dump(kpi, f, ensure_ascii=False, indent=2)
    print(f'\nBest strategy: {best["strategy"]} ({best["win_rate"]}%)')
    print(f'KPI saved: {KPI}')


if __name__ == '__main__':
    main()
