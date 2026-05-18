#!/usr/bin/env python3
"""
室蘭・登別・苫小牧エリアのスロット台データ自動収集スクリプト

データソース:
  1. みんレポ (min-repo.com) - 機種別差枚データ（メイン）
  2. DMMぱちタウン (p-town.dmm.com) - 出玉ランキングTOP10
  3. アナスロ (ana-slo.com) - 台番号別詳細データ（BB/RB回数・合算確率）
  4. みんパチ (minpachi.com) - 口コミ・評価（週次）

GitHub Actions から毎日実行され、data/halls.json に出力します。
"""

import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# curl_cffi: ブラウザのTLSフィンガープリント偽装でCloudflareを回避
try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False
    print('⚠ curl_cffi未インストール（アナスロ・DMM取得不可）')

JST = timezone(timedelta(hours=9))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# アナスロ用ヘッダー（Referer必須）
ANASLO_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en;q=0.9',
    'Referer': 'https://ana-slo.com/ホールデータ/北海道/',
}

# ──────────────────────────────────────
# 対象ホール一覧（13店舗）
# ──────────────────────────────────────
HALLS = [
    # ▼ 苫小牧エリア
    {
        'エリア': '苫小牧', '名': 'ベガスベガス苫小牧店',
        'min_repo_tag': 'https://min-repo.com/tag/%e3%83%99%e3%82%ac%e3%82%b9%e3%83%99%e3%82%ac%e3%82%b9%e8%8b%ab%e5%b0%8f%e7%89%a7%e5%ba%97/',
        'dmm_id': '12391',
        'anaslo_slug': '%e3%83%99%e3%82%ac%e3%82%b9%e3%83%99%e3%82%ac%e3%82%b9%e8%8b%ab%e5%b0%8f%e7%89%a7%e5%ba%97',
        'minpachi_slug': 'vegasvegas-tomakomai',
        'イベント日': '5のつく日・11日・22日',
        '台数': 449,
    },
    {
        'エリア': '苫小牧', '名': 'マルハン苫小牧駅前店',
        'min_repo_tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e8%8b%ab%e5%b0%8f%e7%89%a7%e9%a7%85%e5%89%8d%e5%ba%97/',
        'dmm_id': None,
        'anaslo_slug': '%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e8%8b%ab%e5%b0%8f%e7%89%a7%e9%a7%85%e5%89%8d%e5%ba%97',
        'イベント日': '7のつく日・毎週金曜',
    },
    {
        'エリア': '苫小牧', '名': 'プレイランドハッピー三光店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC%E4%B8%89%E5%85%89%E5%BA%97/',
        'dmm_id': None,
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'コアシティ',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%82%B3%E3%82%A2%E3%82%B7%E3%83%86%E3%82%A3/',
        'dmm_id': None,
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'ひまわり苫小牧店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%81%B2%E3%81%BE%E3%82%8F%E3%82%8A%E8%8B%AB%E5%B0%8F%E7%89%A7%E5%BA%97/',
        'dmm_id': None,
        'anaslo_slug': '%e3%81%b2%e3%81%be%e3%82%8f%e3%82%8a%e8%8b%ab%e5%b0%8f%e7%89%a7%e5%ba%97',
        'イベント日': '0のつく日',
    },
    {
        'エリア': '苫小牧', '名': 'がちゃぽん苫小牧店',
        'min_repo_tag': None,
        'dmm_id': None,
        'anaslo_slug': '%e3%81%8c%e3%81%a1%e3%82%83%e3%81%bd%e3%82%93%e8%8b%ab%e5%b0%8f%e7%89%a7%e5%ba%97',
        'イベント日': '6のつく日',
    },
    {
        'エリア': '苫小牧', '名': 'ロイヤル沼ノ端店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E6%B2%BC%E3%83%8E%E7%AB%AF%E5%BA%97/',
        'dmm_id': None,
        'イベント日': '要調査',
    },
    {
        'エリア': '苫小牧', '名': 'ロイヤル苫小牧店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E8%8B%AB%E5%B0%8F%E7%89%A7%E5%BA%97/',
        'dmm_id': '1354',
        'イベント日': '要調査',
    },

    # ▼ 登別エリア
    {
        'エリア': '登別', '名': 'ロイヤル登別店',
        'min_repo_tag': 'https://min-repo.com/tag/%e3%83%ad%e3%82%a4%e3%83%a4%e3%83%ab%e7%99%bb%e5%88%a5%e5%ba%97/',
        'dmm_id': '1429',
        'anaslo_slug': '%e3%83%ad%e3%82%a4%e3%83%a4%e3%83%ab%e7%99%bb%e5%88%a5%e5%ba%97',
        'イベント日': '8のつく日',
        '台数': 240,
    },
    {
        'エリア': '登別', '名': 'ダイナム登別店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%83%80%E3%82%A4%E3%83%8A%E3%83%A0%E7%99%BB%E5%88%A5%E5%BA%97/',
        'dmm_id': None,
        'イベント日': '7のつく日',
    },

    # ▼ 室蘭エリア
    {
        'エリア': '室蘭', '名': 'ビクトリア室蘭店',
        'min_repo_tag': 'https://min-repo.com/tag/%E3%83%93%E3%82%AF%E3%83%88%E3%83%AA%E3%82%A2%E5%AE%A4%E8%98%AD%E5%BA%97/',
        'dmm_id': '1258',
        'anaslo_slug': '%e3%83%93%e3%82%af%e3%83%88%e3%83%aa%e3%82%a2%e5%ae%a4%e8%98%ad%e5%ba%97',
        'イベント日': '5のつく日',
        '台数': 252,
    },
    {
        'エリア': '室蘭', '名': 'ひまわり室蘭店',
        'min_repo_tag': 'https://min-repo.com/tag/%e3%81%b2%e3%81%be%e3%82%8f%e3%82%8a%e5%ae%a4%e8%98%ad%e5%ba%97/',
        'dmm_id': None,
        'anaslo_slug': '%e3%81%b2%e3%81%be%e3%82%8f%e3%82%8a%e5%ae%a4%e8%98%ad%e5%ba%97',
        'イベント日': '0のつく日',
    },
    {
        'エリア': '室蘭', '名': 'マルハン室蘭店',
        'min_repo_tag': 'https://min-repo.com/tag/%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e5%ae%a4%e8%98%ad%e5%ba%97/',
        'dmm_id': None,
        'anaslo_slug': '%e3%83%9e%e3%83%ab%e3%83%8f%e3%83%b3%e5%ae%a4%e8%98%ad%e5%ba%97',
        'イベント日': '7のつく日',
    },
    {
        'エリア': '室蘭', '名': 'ZEUS',
        'min_repo_tag': 'https://min-repo.com/tag/zeus/',
        'dmm_id': None,
        'イベント日': '毎週金曜日',
        '台数': 84,
    },
]


def fetch(url, retries=3, timeout=20):
    """URLからHTMLを取得（リトライ付き）"""
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except Exception as e:
            if i < retries - 1:
                print(f'    ⚠ リトライ {i+1}/{retries}: {e}')
                time.sleep(2)
            else:
                print(f'    ✗ 取得失敗: {e}')
    return None


# ──────────────────────────────────────
# ソース1: みんレポ (機種別差枚データ)
# ──────────────────────────────────────
def min_repo_最新URL(tag_url):
    html = fetch(tag_url)
    if not html: return None, None
    soup = BeautifulSoup(html, 'lxml')
    for a in soup.select('a[href*="min-repo.com/"]'):
        href = a.get('href', '')
        m = re.match(r'^https://min-repo\.com/(\d+)/?$', href)
        if m:
            text = a.get_text(strip=True)
            date_match = re.search(r'(\d+)/(\d+)', text)
            date_str = date_match.group(0) if date_match else ''
            return href, date_str
    return None, None


def min_repo_機種データ抽出(detail_url):
    """機種別差枚データを抽出"""
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
                    '勝率テキスト': cells[idx['win']] if 'win' in idx and idx['win'] < len(cells) else '',
                })
            except (IndexError, KeyError): continue

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


# ──────────────────────────────────────
# ソース2: DMMぱちタウン (出玉ランキングTOP10)
# ──────────────────────────────────────
def dmm_出玉ランキング(shop_id):
    """DMMぱちタウンの出玉ランキングTOP10を取得（curl_cffiでブラウザTLS偽装）"""
    if not shop_id or not HAS_CFFI: return None
    url = f'https://p-town.dmm.com/shops/hokkaido/{shop_id}/jackpot'
    try:
        r = cffi_requests.get(url, headers={'Accept-Language': 'ja,en;q=0.9'}, impersonate='chrome120', timeout=20)
        if r.status_code != 200:
            print(f'    ⚠ DMM {r.status_code}')
            return None
        html = r.text
    except Exception as e:
        print(f'    ⚠ DMMエラー: {e}')
        return None

    soup = BeautifulSoup(html, 'lxml')
    ランキング = {'パチンコ': [], 'スロット': []}

    # ランキングテキストを解析
    text = soup.get_text(separator='\n')
    sections = re.split(r'(パチンコランキング|パチスロランキング|スロットランキング)', text)

    current_section = None
    for part in sections:
        if 'パチンコ' in part: current_section = 'パチンコ'
        elif 'パチスロ' in part or 'スロット' in part: current_section = 'スロット'
        elif current_section:
            # 各行を解析: 順位、機種名、差玉/差枚、台番号
            entries = re.findall(r'(\d+)\s+([^\n]+?)\s+(\d{2,6})\s*(?:玉|枚)\s+(\d+)', part)
            for rank, name, diff,台番号 in entries[:10]:
                ランキング[current_section].append({
                    '順位': int(rank),
                    '機種名': name.strip(),
                    '差' + ('玉' if current_section == 'パチンコ' else '枚'): int(diff),
                    '台番号': 台番号,
                })

    return ランキング if (ランキング['パチンコ'] or ランキング['スロット']) else None


# ──────────────────────────────────────
# ソース3: アナスロ (台番号レベル詳細データ)
# ──────────────────────────────────────
def anaslo_fetch(url):
    """アナスロ用：curl_cffiでブラウザTLS偽装してCloudflare回避"""
    if not HAS_CFFI:
        return None
    for i in range(3):
        try:
            r = cffi_requests.get(url, headers=ANASLO_HEADERS, impersonate='chrome120', timeout=25)
            if r.status_code == 200:
                return r.text
            print(f'    ⚠ アナスロ {r.status_code}: リトライ {i+1}/3')
            time.sleep(3)
        except Exception as e:
            print(f'    ⚠ アナスロエラー: {e}')
            time.sleep(3)
    return None


def anaslo_最新日付取得(slug):
    """ホール一覧ページから最新のデータページURLを取得"""
    list_url = f'https://ana-slo.com/%e3%83%9b%e3%83%bc%e3%83%ab%e3%83%87%e3%83%bc%e3%82%bf/%e5%8c%97%e6%b5%b7%e9%81%93/{slug}-%e3%83%87%e3%83%bc%e3%82%bf%e4%b8%80%e8%a6%a7/'
    html = anaslo_fetch(list_url)
    if not html: return None, None
    # YYYY-MM-DD のURL抽出
    pattern = re.compile(rf'href="(https://ana-slo\.com/(\d{{4}}-\d{{2}}-\d{{2}})-{re.escape(slug)}-data/)"')
    matches = pattern.findall(html)
    if matches:
        return matches[0][0], matches[0][1]  # URL, 日付
    return None, None


def anaslo_台別データ抽出(detail_url):
    """個別ページから台番号別データを抽出して機種別集計"""
    html = anaslo_fetch(detail_url)
    if not html: return [], {}

    soup = BeautifulSoup(html, 'lxml')
    台別 = []
    現在機種 = None

    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells: continue

            # 機種名セル（fixed01クラス）
            first = cells[0]
            if 'fixed01' in (first.get('class') or []):
                機種名 = first.get_text(strip=True)
                if 機種名: 現在機種 = 機種名

                if 現在機種 and len(cells) >= 6:
                    try:
                        台番号 = cells[1].get_text(strip=True)
                        g数 = cells[2].get_text(strip=True).replace(',', '')
                        差枚 = cells[3].get_text(strip=True).replace(',', '').replace('+', '')
                        bb = cells[4].get_text(strip=True)
                        rb = cells[5].get_text(strip=True)
                        合算 = cells[6].get_text(strip=True) if len(cells) > 6 else ''

                        if g数.isdigit():
                            台別.append({
                                '機種名': 現在機種,
                                '台番号': 台番号,
                                'G数': int(g数),
                                '差枚': int(差枚) if 差枚.lstrip('-').isdigit() else 0,
                                'BB': int(bb) if bb.isdigit() else 0,
                                'RB': int(rb) if rb.isdigit() else 0,
                                '合算': 合算,
                            })
                    except (ValueError, IndexError):
                        continue

    # 機種別に集計
    機種集計 = {}
    for d in 台別:
        m = d['機種名']
        if m not in 機種集計:
            機種集計[m] = {'機種名': m, '台数': 0, '総G数': 0, '総差枚': 0, '総BB': 0, '総RB': 0, '最大差枚': -99999, '最小差枚': 99999, '勝ち台数': 0}
        c = 機種集計[m]
        c['台数'] += 1
        c['総G数'] += d['G数']
        c['総差枚'] += d['差枚']
        c['総BB'] += d['BB']
        c['総RB'] += d['RB']
        c['最大差枚'] = max(c['最大差枚'], d['差枚'])
        c['最小差枚'] = min(c['最小差枚'], d['差枚'])
        if d['差枚'] > 0: c['勝ち台数'] += 1

    # 平均値計算
    集計結果 = []
    for m, c in 機種集計.items():
        if c['台数'] > 0:
            集計結果.append({
                '機種名': m,
                '台数': c['台数'],
                '平均G数': c['総G数'] // c['台数'],
                '平均差枚': c['総差枚'] // c['台数'],
                '合計差枚': c['総差枚'],
                '最大差枚': c['最大差枚'],
                '最小差枚': c['最小差枚'],
                '勝率': round(c['勝ち台数'] / c['台数'] * 100, 1),
                '平均BB': round(c['総BB'] / c['台数'], 1),
                '平均RB': round(c['総RB'] / c['台数'], 1),
            })

    集計結果.sort(key=lambda x: x['平均差枚'], reverse=True)

    # 全体統計
    統計 = {
        '総台数': len(台別),
        '勝ち台数': sum(1 for d in 台別 if d['差枚'] > 0),
        '総差枚': sum(d['差枚'] for d in 台別),
        '平均G数': sum(d['G数'] for d in 台別) // len(台別) if 台別 else 0,
    }
    if 統計['総台数'] > 0:
        統計['勝率'] = round(統計['勝ち台数'] / 統計['総台数'] * 100, 1)

    return 集計結果, 統計, len(台別)


# ──────────────────────────────────────
# メイン処理
# ──────────────────────────────────────
def main():
    print(f'🎰 スクレイピング開始: {datetime.now(JST).strftime("%Y-%m-%d %H:%M")} JST')
    print(f'   対象: {len(HALLS)}ホール / 2データソース\n')

    結果 = {
        '更新日時': datetime.now(JST).isoformat(),
        '出典': {
            'みんレポ': 'https://min-repo.com/',
            'DMMぱちタウン': 'https://p-town.dmm.com/',
            'アナスロ': 'https://ana-slo.com/',
        },
        '対象ホール数': len(HALLS),
        'ホール': []
    }

    成功 = {'min_repo': 0, 'dmm': 0, 'anaslo': 0}

    for i, hall in enumerate(HALLS, 1):
        print(f'[{i}/{len(HALLS)}] ▶ {hall["名"]} ({hall["エリア"]})')

        ホールデータ = {
            'エリア': hall['エリア'],
            '名': hall['名'],
            'イベント日': hall['イベント日'],
        }
        if '台数' in hall:
            ホールデータ['基本台数'] = hall['台数']

        # ▼ ソース1: みんレポ
        if hall.get('min_repo_tag'):
            detail_url, date_str = min_repo_最新URL(hall['min_repo_tag'])
            if detail_url:
                time.sleep(1)
                機種, 統計 = min_repo_機種データ抽出(detail_url)
                機種_有効 = [m for m in 機種 if m.get('平均差枚') is not None]
                機種_有効.sort(key=lambda x: x['平均差枚'], reverse=True)
                ホールデータ['みんレポ'] = {
                    'データ日': date_str,
                    '出典URL': detail_url,
                    '統計': 統計,
                    '機種数': len(機種_有効),
                    '機種': 機種_有効[:30],
                }
                if 機種_有効:
                    成功['min_repo'] += 1
                    print(f'    ✓ みんレポ: {len(機種_有効)}機種 ({date_str})')
            else:
                print(f'    ✗ みんレポ: ページ取得失敗')

        # ▼ ソース2: DMMぱちタウン
        if hall.get('dmm_id'):
            time.sleep(1)
            ランキング = dmm_出玉ランキング(hall['dmm_id'])
            if ランキング:
                ホールデータ['DMMぱちタウン'] = {
                    '出典URL': f'https://p-town.dmm.com/shops/hokkaido/{hall["dmm_id"]}/jackpot',
                    '出玉TOP10': ランキング,
                }
                成功['dmm'] += 1
                p_count = len(ランキング.get('パチンコ', []))
                s_count = len(ランキング.get('スロット', []))
                print(f'    ✓ DMM出玉TOP: パチンコ{p_count}件 / スロット{s_count}件')

        # ▼ ソース3: アナスロ（台番号レベル詳細データ）
        if hall.get('anaslo_slug'):
            time.sleep(1)
            anaslo_url, anaslo_date = anaslo_最新日付取得(hall['anaslo_slug'])
            if anaslo_url:
                time.sleep(1)
                anaslo_機種, anaslo_統計, 総台数 = anaslo_台別データ抽出(anaslo_url)
                if anaslo_機種:
                    ホールデータ['アナスロ'] = {
                        'データ日': anaslo_date,
                        '出典URL': anaslo_url,
                        '統計': anaslo_統計,
                        '集計台数': 総台数,
                        '機種数': len(anaslo_機種),
                        '機種': anaslo_機種[:30],
                    }
                    成功['anaslo'] += 1
                    print(f'    ✓ アナスロ: {len(anaslo_機種)}機種 / {総台数}台 ({anaslo_date})')
            else:
                print(f'    ✗ アナスロ: 取得失敗')

        結果['ホール'].append(ホールデータ)
        time.sleep(1)

    # 集計サマリー
    結果['集計'] = {
        'みんレポ取得成功': 成功['min_repo'],
        'DMMぱちタウン取得成功': 成功['dmm'],
        'アナスロ取得成功': 成功['anaslo'],
    }

    # 保存
    出力先 = Path('data/halls.json')
    出力先.parent.mkdir(parents=True, exist_ok=True)
    出力先.write_text(json.dumps(結果, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n💾 保存完了: {出力先}')
    print(f'   みんレポ成功: {成功["min_repo"]}/{len(HALLS)}')
    print(f'   DMM成功: {成功["dmm"]}/{sum(1 for h in HALLS if h.get("dmm_id"))}')
    print(f'   アナスロ成功: {成功["anaslo"]}/{sum(1 for h in HALLS if h.get("anaslo_slug"))}')


if __name__ == '__main__':
    main()
