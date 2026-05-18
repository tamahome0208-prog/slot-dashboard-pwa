#!/usr/bin/env python3
"""
スロット台データ自動収集スクリプト（みんレポ専用版）

データソース: みんレポ (min-repo.com)
対象エリア: 苫小牧・室蘭・登別・千歳・恵庭（道南エリア18ホール）

GitHub Actions から毎日朝7時(JST)に自動実行され、data/halls.json に出力します。
"""

import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ──────────────────────────────────────
# 対象ホール一覧（18店舗・道南エリア網羅）
# ──────────────────────────────────────
HALLS = [
    # ▼ 苫小牧エリア（7店）
    {
        'エリア': '苫小牧', '名': 'ベガスベガス苫小牧店',
        'tag': 'https://min-repo.com/tag/%e3%83%99%e3%82%ac%e3%82%b9%e3%83%99%e3%82%ac%e3%82%b9%e8%8b%ab%e5%b0%8f%e7%89%a7%e5%ba%97/',
        'イベント日': '5のつく日・11日・22日',
    },
    {
        'エリア': '苫小牧', '名': 'マルハン苫小牧駅前店',
        'tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e8%8b%ab%e5%b0%8f%e7%89%a7%e9%a7%85%e5%89%8d%e5%ba%97/',
        'イベント日': '7のつく日・毎週金曜',
    },
    {
        'エリア': '苫小牧', '名': 'プレイランドハッピー三光店',
        'tag': 'https://min-repo.com/tag/%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC%E4%B8%89%E5%85%89%E5%BA%97/',
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'コアシティ',
        'tag': 'https://min-repo.com/tag/%E3%82%B3%E3%82%A2%E3%82%B7%E3%83%86%E3%82%A3/',
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'ひまわり苫小牧店',
        'tag': 'https://min-repo.com/tag/%E3%81%B2%E3%81%BE%E3%82%8F%E3%82%8A%E8%8B%AB%E5%B0%8F%E7%89%A7%E5%BA%97/',
        'イベント日': '0のつく日',
    },
    {
        'エリア': '苫小牧', '名': 'ロイヤル沼ノ端店',
        'tag': 'https://min-repo.com/tag/%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E6%B2%BC%E3%83%8E%E7%AB%AF%E5%BA%97/',
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'ロイヤル苫小牧店',
        'tag': 'https://min-repo.com/tag/%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E8%8B%AB%E5%B0%8F%E7%89%A7%E5%BA%97/',
        'イベント日': '要調査',
    },

    # ▼ 登別エリア（2店）
    {
        'エリア': '登別', '名': 'ロイヤル登別店',
        'tag': 'https://min-repo.com/tag/%e3%83%ad%e3%82%a4%e3%83%a4%e3%83%ab%e7%99%bb%e5%88%a5%e5%ba%97/',
        'イベント日': '8のつく日',
    },
    {
        'エリア': '登別', '名': 'ダイナム登別店',
        'tag': 'https://min-repo.com/tag/%E3%83%80%E3%82%A4%E3%83%8A%E3%83%A0%E7%99%BB%E5%88%A5%E5%BA%97/',
        'イベント日': '7のつく日',
    },

    # ▼ 室蘭エリア（4店）
    {
        'エリア': '室蘭', '名': 'ビクトリア室蘭店',
        'tag': 'https://min-repo.com/tag/%E3%83%93%E3%82%AF%E3%83%88%E3%83%AA%E3%82%A2%E5%AE%A4%E8%98%AD%E5%BA%97/',
        'イベント日': '5のつく日',
    },
    {
        'エリア': '室蘭', '名': 'ひまわり室蘭店',
        'tag': 'https://min-repo.com/tag/%e3%81%b2%e3%81%be%e3%82%8f%e3%82%8a%e5%ae%a4%e8%98%ad%e5%ba%97/',
        'イベント日': '0のつく日',
    },
    {
        'エリア': '室蘭', '名': 'マルハン室蘭店',
        'tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e5%ae%a4%e8%98%ad%e5%ba%97/',
        'イベント日': '7のつく日',
    },
    {
        'エリア': '室蘭', '名': 'ZEUS',
        'tag': 'https://min-repo.com/tag/zeus/',
        'イベント日': '毎週金曜日',
    },

    # ▼ 千歳エリア（3店）★新規
    {
        'エリア': '千歳', '名': 'マルハン千歳店',
        'tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e5%8d%83%e6%ad%b3%e5%ba%97/',
        'イベント日': '7のつく日',
    },
    {
        'エリア': '千歳', '名': 'プレイランドハッピー千歳駅前店',
        'tag': 'https://min-repo.com/tag/%e3%83%97%e3%83%ac%e3%82%a4%e3%83%a9%e3%83%b3%e3%83%89%e3%83%8f%e3%83%83%e3%83%94%e3%83%bc%e5%8d%83%e6%ad%b3%e9%a7%85%e5%89%8d%e5%ba%97/',
        'イベント日': '要調査',
    },
    {
        'エリア': '千歳', '名': 'クラブイーグル千歳店',
        'tag': 'https://min-repo.com/tag/%e3%82%af%e3%83%a9%e3%83%96%e3%82%a4%e3%83%bc%e3%82%b0%e3%83%ab%e5%8d%83%e6%ad%b3%e5%ba%97/',
        'イベント日': '要調査',
    },

    # ▼ 恵庭エリア（2店）★新規
    {
        'エリア': '恵庭', '名': 'マルハン恵庭店',
        'tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e6%81%b5%e5%ba%ad%e5%ba%97/',
        'イベント日': '7のつく日',
    },
    {
        'エリア': '恵庭', '名': 'パーラー恵み野',
        'tag': 'https://min-repo.com/tag/%e3%83%91%e3%83%bc%e3%83%a9%e3%83%bc%e6%81%b5%e3%81%bf%e9%87%8e/',
        'イベント日': '要調査',
    },
]


def fetch(url, retries=3):
    """URLからHTMLを取得（リトライ付き）"""
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except Exception as e:
            if i < retries - 1:
                time.sleep(2)
    return None


def 最新ページURL取得(tag_url):
    """ホールタグページから最新の日別ページURLを取得"""
    html = fetch(tag_url)
    if not html: return None, None
    soup = BeautifulSoup(html, 'lxml')
    for a in soup.select('a[href*="min-repo.com/"]'):
        href = a.get('href', '')
        m = re.match(r'^https://min-repo\.com/(\d+)/?$', href)
        if m:
            text = a.get_text(strip=True)
            date_match = re.search(r'(\d+)/(\d+)', text)
            return href, date_match.group(0) if date_match else ''
    return None, None


def 機種データ抽出(detail_url):
    """日別ページから機種データと全体統計を抽出"""
    html = fetch(detail_url)
    if not html: return [], {}

    soup = BeautifulSoup(html, 'lxml')
    機種一覧 = []

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2: continue

        header_cells = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
        if not any('機種' in h or '差枚' in h for h in header_cells): continue

        idx = {}
        for i, h in enumerate(header_cells):
            if '機種' in h or 'タイプ' in h: idx['name'] = i
            elif '台数' in h: idx['daisuu'] = i
            elif '差枚' in h: idx['avg_sa'] = i
            elif 'G' in h and ('平均' in h or '数' in h): idx['avg_g'] = i
            elif '勝率' in h: idx['win'] = i
            elif '出率' in h or '機械割' in h: idx['payout'] = i

        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) < 2: continue

            try:
                name = cells[idx.get('name', 0)] if 'name' in idx else cells[0]
                if not name or '機種' in name: continue

                def 数値(key):
                    if key not in idx or idx[key] >= len(cells): return None
                    v = cells[idx[key]].replace(',', '').replace('+', '').replace('%', '').replace('枚', '').replace('G', '').replace('台', '').strip()
                    try: return float(v) if '.' in v else int(v)
                    except: return None

                機種一覧.append({
                    '機種名': name,
                    '台数': 数値('daisuu'),
                    '平均差枚': 数値('avg_sa'),
                    '平均G数': 数値('avg_g'),
                    '出率': 数値('payout'),
                })
            except (IndexError, KeyError):
                continue

    # 全体統計
    text = soup.get_text()
    統計 = {}
    m = re.search(r'平均G数[：:]?\s*([\d,]+)', text)
    if m: 統計['平均G数'] = int(m.group(1).replace(',', ''))
    m = re.search(r'勝率[：:]?\s*(\d+)/(\d+)', text)
    if m:
        統計['勝ち台数'] = int(m.group(1))
        統計['総台数'] = int(m.group(2))
        統計['勝率'] = round(int(m.group(1)) / int(m.group(2)) * 100, 1)

    return 機種一覧, 統計


def main():
    print(f'🎰 スクレイピング開始: {datetime.now(JST).strftime("%Y-%m-%d %H:%M")} JST')
    print(f'   対象: {len(HALLS)}ホール\n')

    結果 = {
        '更新日時': datetime.now(JST).isoformat(),
        '出典': 'みんレポ (https://min-repo.com/)',
        '対象ホール数': len(HALLS),
        'ホール': []
    }

    成功 = 0
    全機種数 = 0

    for i, hall in enumerate(HALLS, 1):
        print(f'[{i:>2}/{len(HALLS)}] ▶ {hall["エリア"]} | {hall["名"]}')

        ホールデータ = {
            'エリア': hall['エリア'],
            '名': hall['名'],
            'イベント日': hall['イベント日'],
        }

        detail_url, date_str = 最新ページURL取得(hall['tag'])
        if detail_url:
            time.sleep(1)
            機種, 統計 = 機種データ抽出(detail_url)
            機種_有効 = [m for m in 機種 if m.get('平均差枚') is not None]
            機種_有効.sort(key=lambda x: x['平均差枚'], reverse=True)

            if 機種_有効:
                ホールデータ['データ日'] = date_str
                ホールデータ['出典URL'] = detail_url
                ホールデータ['統計'] = 統計
                ホールデータ['機種数'] = len(機種_有効)
                ホールデータ['機種'] = 機種_有効[:30]
                成功 += 1
                全機種数 += len(機種_有効)
                print(f'    ✓ {len(機種_有効)} 機種取得 ({date_str})')
            else:
                print(f'    ⚠ 機種データなし')
        else:
            print(f'    ✗ ページ取得失敗')

        結果['ホール'].append(ホールデータ)
        time.sleep(2)

    結果['集計'] = {
        '成功ホール数': 成功,
        '失敗ホール数': len(HALLS) - 成功,
        '総機種データ': 全機種数,
    }

    出力先 = Path('data/halls.json')
    出力先.parent.mkdir(parents=True, exist_ok=True)
    出力先.write_text(json.dumps(結果, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n💾 保存完了: {出力先}')
    print(f'   成功: {成功}/{len(HALLS)} ホール')
    print(f'   総機種データ: {全機種数} 機種')


if __name__ == '__main__':
    main()
