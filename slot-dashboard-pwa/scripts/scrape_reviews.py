#!/usr/bin/env python3
"""
ホール口コミ・評価データの収集スクリプト（週次実行）
データソース: みんパチ (minpachi.com)
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

# みんパチのホールスラッグ
HALLS = [
    {'エリア': '苫小牧', '名': 'ベガスベガス苫小牧店', 'slug': '%E3%83%99%E3%82%AC%E3%82%B9%E3%83%99%E3%82%AC%E3%82%B9%E8%8B%AB%E5%B0%8F%E7%89%A7%E5%BA%97'},
    {'エリア': '登別', '名': 'ロイヤル登別店', 'slug': '%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E7%99%BB%E5%88%A5%E5%BA%97'},
    {'エリア': '室蘭', '名': 'マルハン室蘭店', 'slug': '%E3%83%9E%E3%83%AB%E3%83%8F%E3%83%B3%E5%AE%A4%E8%98%AD%E5%BA%97'},
    {'エリア': '室蘭', '名': 'ZEUS', 'slug': '%E3%82%A2%E3%83%9F%E3%83%A5%E3%83%BC%E3%82%BA%E3%83%A1%E3%83%B3%E3%83%88%E3%83%91%E3%83%BC%E3%83%A9%E3%83%BCzeus'},
    {'エリア': '室蘭', '名': 'ひまわり室蘭店', 'slug': 'muroran-himawari'},
]


def fetch(url):
    for i in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except Exception as e:
            print(f'  ⚠ リトライ {i+1}/3: {e}')
            time.sleep(2)
    return None


def 口コミ取得(slug):
    """みんパチから口コミ・評価を取得"""
    url = f'https://minpachi.com/{slug}/'
    html = fetch(url)
    if not html: return None

    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text()

    結果 = {'出典URL': url}

    # 総合点
    m = re.search(r'総合(?:点|評価)[：:\s]*(\d+(?:\.\d+)?)', text)
    if m: 結果['総合点'] = float(m.group(1))

    # 各評価
    for label, key in [('営業', '営業評価'), ('接客', '接客評価'), ('設備', '設備評価')]:
        m = re.search(rf'{label}(?:評価)?[：:\s]*(\d+(?:\.\d+)?)', text)
        if m: 結果[key] = float(m.group(1))

    # 旧イベント日
    m = re.search(r'旧イベント日[：:\s]*([^\n]+)', text)
    if m: 結果['旧イベント日'] = m.group(1).strip()[:50]

    # 口コミ抽出（リスト形式 or 段落）
    口コミ = []
    for li in soup.find_all(['li', 'p']):
        t = li.get_text(strip=True)
        if 30 <= len(t) <= 300 and any(k in t for k in ['店員', '出', '回', '客', '台', '設定', '接客', 'スロ', 'パチ']):
            口コミ.append(t)
    結果['口コミ'] = 口コミ[:10]

    return 結果


def main():
    print(f'📝 口コミスクレイピング開始: {datetime.now(JST).strftime("%Y-%m-%d %H:%M")} JST')

    結果 = {
        '更新日時': datetime.now(JST).isoformat(),
        '出典': 'みんパチ (https://minpachi.com/)',
        'ホール': []
    }

    成功 = 0
    for i, hall in enumerate(HALLS, 1):
        print(f'[{i}/{len(HALLS)}] ▶ {hall["名"]}')
        data = 口コミ取得(hall['slug'])
        if data:
            data.update({'エリア': hall['エリア'], '名': hall['名']})
            結果['ホール'].append(data)
            成功 += 1
            print(f'  ✓ 総合{data.get("総合点", "-")}点 / 口コミ{len(data.get("口コミ", []))}件')
        else:
            print(f'  ✗ 取得失敗')
        time.sleep(2)

    出力先 = Path('data/reviews.json')
    出力先.parent.mkdir(parents=True, exist_ok=True)
    出力先.write_text(json.dumps(結果, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n💾 保存完了: {出力先} ({成功}/{len(HALLS)})')


if __name__ == '__main__':
    main()
