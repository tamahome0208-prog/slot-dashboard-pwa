#!/usr/bin/env python3
"""
ロイヤル登別 毎日自動データ拡張スクリプト
毎朝7時(JST)に最新ページを取得→ data/royal_history.json に追記
"""
import os, json, re, sys, io, urllib.request, concurrent.futures
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') if hasattr(sys.stdout, 'buffer') else sys.stdout

BASE_URL = 'https://min-repo.com/tag/%e3%83%ad%e3%82%a4%e3%83%a4%e3%83%ab%e7%99%bb%e5%88%a5%e5%ba%97/'
DATA_FILE = 'data/royal_history.json'
TRENDS_FILE = 'data/royal_trends.json'
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def is_valid_machine_name(n):
    if not n or len(n) < 3: return False
    if re.match(r'^[\d\.\s%]+$', n): return False
    if 'ゾロ目' in n or n in ['機種名','機種','設定','合計','タイプ','スロット','ボーナス']: return False
    return True


def fetch(url):
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  ⚠ {e}')
    return None


def get_all_urls():
    """全ページからURLを取得"""
    all_urls = []
    seen = set()
    for p in range(1, 11):
        url = BASE_URL if p == 1 else f'{BASE_URL}page/{p}/'
        html = fetch(url)
        if not html: break
        matches = re.findall(r'href="(https://min-repo\.com/(\d+)/?)"[^>]*>([^<]*)', html)
        page_count = 0
        for u, num, text in matches:
            if num in seen: continue
            seen.add(num)
            m = re.search(r'(\d+)/(\d+)\(([日月火水木金土])\)', text)
            if m:
                all_urls.append({
                    'url': u.rstrip('/'), 'date_str': f"{m.group(1)}/{m.group(2)}",
                    'dow': m.group(3), 'month': int(m.group(1)), 'day': int(m.group(2)),
                    'id': num
                })
                page_count += 1
        if page_count == 0: break
    return all_urls


def parse_page(html):
    """1ページから機種データ抽出"""
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text()

    stats = {}
    m = re.search(r'平均G数[：:]?\s*([\d,]+)', text)
    if m: stats['avg_g'] = int(m.group(1).replace(',', ''))
    m = re.search(r'勝率[：:]?\s*(\d+)/(\d+)', text)
    if m:
        stats['wins'] = int(m.group(1))
        stats['total'] = int(m.group(2))

    machines = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2: continue
        hcells = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
        if not any('機種' in h or '差枚' in h for h in hcells): continue
        idx = {}
        for ii, h in enumerate(hcells):
            if '機種' in h or 'タイプ' in h: idx['name'] = ii
            elif '台数' in h: idx['daisuu'] = ii
            elif '差枚' in h: idx['sa'] = ii
            elif 'G' in h and ('平均' in h or '数' in h): idx['g'] = ii
            elif '出率' in h or '機械割' in h: idx['p'] = ii
        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) < 2: continue
            try:
                name = cells[idx.get('name', 0)]
                if not is_valid_machine_name(name): continue

                def num(k):
                    if k not in idx or idx[k] >= len(cells): return None
                    v = cells[idx[k]].replace(',', '').replace('+', '').replace('%', '').replace('枚', '').replace('G', '').replace('台', '').strip()
                    try: return float(v) if '.' in v else int(v)
                    except: return None

                m_data = {'name': name, 'daisuu': num('daisuu'), 'sa': num('sa'), 'g': num('g'), 'p': num('p')}
                if m_data['sa'] is not None: machines.append(m_data)
            except: continue
    return stats, machines


def main():
    print(f'🏆 ロイヤル登別 毎日自動更新: {datetime.now(JST).isoformat()}')

    # 既存DBロード
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as f:
            history = json.load(f)
        existing_ids = {d.get('id') for d in history if 'id' in d}
        print(f'既存: {len(history)}日')
    else:
        history = []
        existing_ids = set()

    # 最新URL一覧取得
    urls = get_all_urls()
    print(f'URL取得: {len(urls)}件')

    # 新規分のみ抽出
    new_urls = [u for u in urls if u['id'] not in existing_ids]
    print(f'新規: {len(new_urls)}件')

    if not new_urls:
        print('変更なし')
        return

    # 並列スクレイピング
    def fetch_one(u):
        html = fetch(u['url'])
        if not html: return None
        stats, machines = parse_page(html)
        return {**u, 'stats': stats, 'machines': machines}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch_one, new_urls))

    new_data = [r for r in results if r]
    print(f'追加: {len(new_data)}日')

    history.extend(new_data)
    history.sort(key=lambda x: x.get('id', ''), reverse=True)

    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f'保存: {DATA_FILE} ({len(history)}日)')

    # 集計（royal_trends.json）
    from collections import defaultdict
    machine_stats = defaultdict(lambda: {'sa_w': 0, 'w': 0, 'days': 0, 'wins': 0, 'p_w': 0})
    for d in history:
        seen = set()
        for m in d.get('machines', []):
            n = m['name']
            if not is_valid_machine_name(n): continue
            w = m['daisuu'] or 1
            machine_stats[n]['sa_w'] += m['sa'] * w
            machine_stats[n]['w'] += w
            if m.get('p'): machine_stats[n]['p_w'] += m['p'] * w
            if n not in seen:
                machine_stats[n]['days'] += 1
                if m['sa'] > 0: machine_stats[n]['wins'] += 1
                seen.add(n)

    top = []
    for n, s in machine_stats.items():
        if s['days'] < 3: continue
        top.append({
            'name': n[:35],
            'avg_sa': round(s['sa_w']/s['w']) if s['w'] else 0,
            'avg_p': round(s['p_w']/s['w'], 1) if s['w'] else 0,
            'days': s['days'],
            'win_rate': round(s['wins']/s['days']*100),
        })
    top.sort(key=lambda x: x['avg_sa'], reverse=True)

    trends = {
        'updated': datetime.now(JST).isoformat(),
        'sample': len(history),
        'top': top[:30],
        'bottom': top[-15:][::-1],
    }
    with open(TRENDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(trends, f, ensure_ascii=False, indent=2)
    print(f'傾向集計: {TRENDS_FILE}')


if __name__ == '__main__':
    main()
