#!/usr/bin/env python3
"""
AI自動サイクル - GitHub Actions上でClaude APIを叩いて週次/日次サイクル実行
- 情報収集タスク発注（指示役プロンプト）
- 提案策定（backlog更新）
- 分析レポート生成
- 採点

注: コード変更は行わない（GHA上での自動コード編集は範囲外）。
    コード変更が必要な改善は backlog.json に積み、CEO手動キック時に修正役が実装。
"""
import os, sys, json, io, urllib.request
from datetime import datetime
import cost_guard

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') if hasattr(sys.stdout, 'buffer') else sys.stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(ROOT, 'harness', 'state')
PROMPTS = os.path.join(ROOT, 'harness', 'prompts')

API_KEY = os.environ.get('ANTHROPIC_API_KEY')
API_URL = 'https://api.anthropic.com/v1/messages'
MODEL = os.environ.get('HARNESS_MODEL', 'claude-3-5-haiku-latest')


def call_claude(system, user, max_tokens=2000, task=''):
    """Claude API呼び出し"""
    if not API_KEY:
        raise RuntimeError('ANTHROPIC_API_KEY 未設定。harness/SETUP_API.md参照')
    cost_guard.check_budget()
    payload = {
        'model': MODEL,
        'max_tokens': max_tokens,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        API_URL, data=body, method='POST',
        headers={
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    text = resp['content'][0]['text']
    usage = resp.get('usage', {})
    cost = cost_guard.record(MODEL, usage.get('input_tokens', 0), usage.get('output_tokens', 0), task=task)
    print(f'  [{task}] tokens in/out={usage.get("input_tokens",0)}/{usage.get("output_tokens",0)} cost=${cost:.4f}')
    return text


def load_state(name):
    p = os.path.join(STATE, name + '.json')
    if not os.path.exists(p): return {}
    with open(p, encoding='utf-8') as f: return json.load(f)


def save_state(name, data):
    p = os.path.join(STATE, name + '.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_prompt(name):
    p = os.path.join(PROMPTS, name + '.md')
    if not os.path.exists(p): return ''
    with open(p, encoding='utf-8') as f: return f.read()


def phase_info_summarize():
    """Phase: 既存info_feedの傾向まとめ（実Web取得はGHAではseleniumなしのため簡略）"""
    feed = load_state('info_feed')
    kpi = load_state('kpi')
    sources = json.dumps(feed.get('sources', {}), ensure_ascii=False)
    system = load_prompt('instructor')
    user = f"""現在の info_feed:
{sources}

直近KPI:
{json.dumps(kpi.get('metrics', {}), ensure_ascii=False)}

タスク: 既存ソースから「現在の状況」「気になるシグナル」「勝率改善仮説」を200字で要約してください。"""
    return call_claude(system, user, max_tokens=500, task='info_summary')


def phase_proposal(summary):
    """Phase: 提案を backlog に追加"""
    backlog = load_state('backlog')
    pending = [i for i in backlog.get('items', []) if i.get('status') == 'pending']
    pending_titles = [i['title'] for i in pending]
    system = load_prompt('instructor')
    user = f"""情報サマリ:
{summary}

既存pending backlog:
{json.dumps(pending_titles, ensure_ascii=False)}

タスク: 勝率向上に直結する新規改善案を1-3件、以下JSONフォーマットで出してください（既存と重複しない案のみ）。説明文は不要、JSONだけ:
[
  {{"title": "...", "rationale": "...", "priority": "high|medium|low", "estimated_impact": "high|medium|low"}}
]
"""
    return call_claude(system, user, max_tokens=800, task='proposal')


def phase_kpi_review():
    """Phase: KPI推移レビュー"""
    kpi = load_state('kpi')
    log = load_state('cycle_log')
    system = "あなたはスロット管理PWAのKPIアナリストです。"
    user = f"""KPI履歴:
{json.dumps(kpi.get('history', [])[-10:], ensure_ascii=False)}

最近の cycle log:
{json.dumps(log.get('cycles', [])[-3:], ensure_ascii=False)}

タスク: 勝率トレンドと懸念点を150字で。"""
    return call_claude(system, user, max_tokens=400, task='kpi_review')


def main():
    print(f'=== AI週次サイクル {datetime.now().isoformat()} ===')
    print(f'モデル: {MODEL}')

    status = cost_guard.check_budget()
    print(f'予算: 残${status["remaining_month"]:.2f}/月')

    try:
        # Phase 1: 情報サマリ
        print('\n[1/3] 情報サマリ生成...')
        summary = phase_info_summarize()
        print(f'  {summary[:100]}...')

        # Phase 2: 提案生成
        print('\n[2/3] 改善提案策定...')
        proposal_raw = phase_proposal(summary)
        print(f'  {proposal_raw[:150]}...')
        # JSON抽出
        try:
            import re
            m = re.search(r'\[.*\]', proposal_raw, re.DOTALL)
            if m:
                new_items = json.loads(m.group(0))
                backlog = load_state('backlog')
                existing_ids = [i['id'] for i in backlog['items']]
                next_n = max([int(i['id'][1:]) for i in backlog['items'] if i['id'].startswith('B')] + [0]) + 1
                for it in new_items:
                    backlog['items'].append({
                        'id': f'B{next_n:03d}',
                        'title': it.get('title', ''),
                        'rationale': it.get('rationale', ''),
                        'priority': it.get('priority', 'medium'),
                        'status': 'pending',
                        'estimated_impact': it.get('estimated_impact', 'medium'),
                        'created_by': 'ai_cycle',
                        'created_at': datetime.now().isoformat(),
                    })
                    next_n += 1
                backlog['updated'] = datetime.now().isoformat()
                save_state('backlog', backlog)
                print(f'  ✅ {len(new_items)}件のbacklog追加')
        except Exception as e:
            print(f'  ⚠ JSON解析失敗: {e}')

        # Phase 3: KPIレビュー
        print('\n[3/3] KPIレビュー...')
        review = phase_kpi_review()
        print(f'  {review[:150]}...')

        # サイクルログ記録
        log = load_state('cycle_log')
        log.setdefault('cycles', []).append({
            'cycle': len(log.get('cycles', [])) + 1,
            'at': datetime.now().isoformat(),
            'kind': 'ai_weekly',
            'summary': summary[:200],
            'kpi_review': review[:200],
            'model': MODEL,
        })
        save_state('cycle_log', log)

        # 最終コスト
        final = cost_guard.check_budget()
        print(f'\n✅ サイクル完了。今月累計: ${final["monthly_limit"] - final["remaining_month"]:.4f}')

    except RuntimeError as e:
        print(f'\n⛔ 中止: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
