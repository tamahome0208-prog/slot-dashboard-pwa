#!/usr/bin/env python3
"""
コストガード - Anthropic API使用量を月次累積追跡
上限を超えたら例外を投げて呼び出し側を停止
"""
import json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, 'harness', 'state', 'cost_ledger.json')

# 料金表 (USD per 1M tokens) - 2026年5月時点のClaude料金
PRICES = {
    'claude-3-5-haiku-latest':  {'in': 0.80, 'out': 4.00},
    'claude-haiku-4-5':         {'in': 1.00, 'out': 5.00},  # 仮値
    'claude-sonnet-4-5':        {'in': 3.00, 'out': 15.00}, # 仮値
}

# 上限 (USD)
MONTHLY_LIMIT = float(os.environ.get('HARNESS_MONTHLY_LIMIT', '5.0'))
PER_CYCLE_LIMIT = float(os.environ.get('HARNESS_PER_CYCLE_LIMIT', '1.0'))


def _load():
    if not os.path.exists(LEDGER):
        return {'entries': [], 'monthly_total': {}}
    with open(LEDGER, encoding='utf-8') as f:
        return json.load(f)


def _save(data):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def estimate_cost(model, input_tokens, output_tokens):
    p = PRICES.get(model, PRICES['claude-3-5-haiku-latest'])
    return input_tokens / 1_000_000 * p['in'] + output_tokens / 1_000_000 * p['out']


def check_budget(cycle_cost_so_far=0.0):
    """月次・サイクル予算チェック。超えてたらRaiseError"""
    data = _load()
    ym = datetime.now().strftime('%Y-%m')
    month_total = data.get('monthly_total', {}).get(ym, 0.0)
    if month_total >= MONTHLY_LIMIT:
        raise RuntimeError(f'❌ 月予算超過: ${month_total:.2f} >= ${MONTHLY_LIMIT}')
    if cycle_cost_so_far >= PER_CYCLE_LIMIT:
        raise RuntimeError(f'❌ サイクル予算超過: ${cycle_cost_so_far:.2f} >= ${PER_CYCLE_LIMIT}')
    return {
        'month_total': month_total,
        'monthly_limit': MONTHLY_LIMIT,
        'remaining_month': MONTHLY_LIMIT - month_total,
    }


def record(model, input_tokens, output_tokens, task=''):
    cost = estimate_cost(model, input_tokens, output_tokens)
    data = _load()
    ym = datetime.now().strftime('%Y-%m')
    data['entries'].append({
        'at': datetime.now().isoformat(),
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cost_usd': round(cost, 4),
        'task': task,
    })
    data.setdefault('monthly_total', {})
    data['monthly_total'][ym] = round(data['monthly_total'].get(ym, 0.0) + cost, 4)
    _save(data)
    return cost


if __name__ == '__main__':
    status = check_budget()
    print(f'月予算: ${status["monthly_limit"]} / 使用 ${status["month_total"]:.4f} / 残 ${status["remaining_month"]:.4f}')
