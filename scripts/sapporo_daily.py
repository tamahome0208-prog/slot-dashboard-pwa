#!/usr/bin/env python3
"""札幌5店舗の台番別データを min-repo.com から日次取得"""
import os, json, re, sys, io, urllib.request, time
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_FILE = 'data/sapporo_history.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (slot-pwa harness/1.0)'}

STORES = [
    {'id': 'hp_minami6', 'name': 'プレイランドハッピー南6条店',
     'tag_url': 'https://min-repo.com/tag/%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC%E5%8D%976%E6%9D%A1%E5%BA%97/'},
    {'id': 'hp_aso', 'name': 'プレイランドハッピー麻生店',
     'tag_url': 'https://min-repo.com/tag/%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC%E9%BA%BB%E7%94%9F%E5%BA%97/'},
    {'id': 'keiz_teine', 'name': 'KEIZ手稲店',
     'tag_url': 'https://min-repo.com/tag/keiz%E6%89%8B%E7%A8%B2%E5%BA%97/'},
    {'id': 'vegas_sapporo', 'name': 'ベガスベガス札幌店',
     'tag_url': 'https://min-repo.com/tag/%E3%83%99%E3%82%AC%E3%82%B9%E3%83%99%E3%82%AC%E3%82%B9%E6%9C%AD%E5%B9%8C%E5%BA%97/'},
    {'id': 'himawari_sapporo', 'name': 'ひまわり札幌駅前タワー店',
     'tag_url': 'https://min-repo.com/tag/%E3%81%B2%E3%81%BE%E3%82%8F%E3%82%8A%E6%9C%AD%E5%B9%8C%E9%A7%85%E5%89%8D%E3%82%BF%E3%83%AF%E3%83%BC%E5%BA%97/'},
]


def fetch(url):
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  WARN {e}')
            time.sleep(2)
    return None


def get_page_urls(tag_url, max_days=5):
    html = fetch(tag_url)
    if not html:
        return []
    matches = re.findall(r'href="(https://min-repo\.com/(\d+)/?)"[^>]*>([^<]*)', html)
    urls = []
    seen = set()
    for u, num, text in matches:
        if num in seen:
            continue
        seen.add(num)
        m = re.search(r'(\d+)/(\d+)\(([日月火水木金土])\)', text)
        if m:
            urls.append({'url': u.rstrip('/'), 'date_str': f"{m.group(1)}/{m.group(2)}",
                         'dow': m.group(3), 'id': num})
            if len(urls) >= max_days:
                break
    return urls


def parse_page(html):
    soup = BeautifulSoup(html, 'lxml')
    machines = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        hcells = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
        if not any('台番' in h or '機種' in h or '差枚' in h for h in hcells):
            continue
        idx = {}
        for ii, h in enumerate(hcells):
            if '機種' in h:
                idx['name'] = ii
            elif '台番' in h:
                idx['unit'] = ii
            elif '差枚' in h:
                idx['sa'] = ii
            elif 'G数' in h or 'ゲーム' in h:
                idx['g'] = ii
            elif '出率' in h or '機械割' in h:
                idx['p'] = ii
        if 'name' not in idx or 'unit' not in idx:
            continue
        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) < 2:
                continue
            try:
                name = cells[idx.get('name')]
                unit = cells[idx.get('unit')]
                if not name or not unit:
                    continue

                def num(k):
                    if k not in idx or idx[k] >= len(cells):
                        return None
                    v = cells[idx[k]].replace(',', '').replace('+', '').replace('%', '').replace('枚', '').replace('G', '').replace('台', '').strip()
                    try:
                        return float(v) if '.' in v else int(v)
                    except Exception:
                        return None

                machines.append({'unit': unit, 'name': name, 'sa': num('sa'), 'g': num('g'), 'shutsu_ritsu': num('p')})
            except Exception:
                continue
    return machines


def main():
    print(f'札幌5店舗データ収集: {datetime.now(JST).isoformat()}')
    all_stores = []
    for store in STORES:
        print(f'\n[{store["name"]}]')
        if '<確定URL>' in store.get('tag_url', ''):
            print('  URL未確定, skip')
            continue
        urls = get_page_urls(store['tag_url'], max_days=10)
        print(f'  取得URL: {len(urls)}件')
        history = []
        for u in urls:
            time.sleep(2)
            html = fetch(u['url'])
            if not html:
                continue
            ms = parse_page(html)
            if ms:
                history.append({'date': u['date_str'], 'dow': u['dow'], 'id': u['id'], 'machines': ms})
        print(f'  日次データ: {len(history)}日分')
        all_stores.append({**store, 'history': history})

    os.makedirs('data', exist_ok=True)
    output = {'updated': datetime.now(JST).isoformat(), 'stores': all_stores}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n保存: {DATA_FILE} ({len(all_stores)}店舗)')


if __name__ == '__main__':
    main()
