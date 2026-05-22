#!/usr/bin/env python3
"""
日次軽量チェック
- KPI再計算
- 異常検知 (前日比 >10% 悪化)
- backlog自動追加
"""
import json, os, subprocess, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') if hasattr(sys.stdout, 'buffer') else sys.stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KPI = os.path.join(ROOT, 'harness', 'state', 'kpi.json')
BACKLOG = os.path.join(ROOT, 'harness', 'state', 'backlog.json')
LOG = os.path.join(ROOT, 'harness', 'state', 'cycle_log.json')


def run_backtest():
    bt = os.path.join(ROOT, 'harness', 'scripts', 'backtest.py')
    r = subprocess.run([sys.executable, bt], capture_output=True, text=True, encoding='utf-8')
    return r.returncode == 0, r.stdout, r.stderr


def main():
    print(f'=== 日次チェック {datetime.now().isoformat()} ===')

    # 1. バックテスト再計算
    ok, out, err = run_backtest()
    print(out)
    if not ok:
        print('⚠ backtest失敗:', err)

    # 2. KPI読込・前回比較
    with open(KPI, encoding='utf-8') as f: kpi = json.load(f)
    history = kpi.get('history', [])
    if len(history) >= 2:
        prev = history[-2]['win_rate']; curr = history[-1]['win_rate']
        delta = curr - prev
        print(f'win_rate: {prev}% → {curr}% (Δ{delta:+.1f}%)')
        if delta < -10:
            # 異常検知 → backlog緊急追加
            with open(BACKLOG, encoding='utf-8') as f: bl = json.load(f)
            bl['items'].append({
                'id': f'B{len(bl["items"])+1:03d}',
                'title': f'⚠ 勝率低下調査 ({delta:+.1f}%)',
                'rationale': f'前日比 {delta:+.1f}% 悪化。原因究明・対策。',
                'priority': 'critical', 'status': 'pending',
                'estimated_impact': 'high', 'created_by': 'daily_check',
                'created_at': datetime.now().isoformat(),
            })
            with open(BACKLOG, 'w', encoding='utf-8') as f:
                json.dump(bl, f, ensure_ascii=False, indent=2)
            print('🚨 緊急タスク追加')

    # 3. cycle_log
    with open(LOG, encoding='utf-8') as f: cl = json.load(f)
    cl['cycles'].append({
        'at': datetime.now().isoformat(),
        'kind': 'daily',
        'kpi_snapshot': kpi.get('metrics', {}).get('backtest_win_rate'),
    })
    with open(LOG, 'w', encoding='utf-8') as f:
        json.dump(cl, f, ensure_ascii=False, indent=2)

    print('✅ 日次チェック完了')


if __name__ == '__main__':
    main()
