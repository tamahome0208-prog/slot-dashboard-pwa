# Cycle#27 設計仕様: 超ミニマル化 + DraftKings風デザイン大刷新

**作成日**: 2026-05-27  
**CEO承認**: 機能A(超ミニマル5機能) + スポーツベッティング風デザイン

## 背景

26サイクル分の機能が積層し「多すぎて見えづらい・使いづらい」とCEO評価。Cycle#23でも削減したが不十分。今回は思い切って **5機能のみ + 3タブ** に絞り、デザインも勝負ツール風(DraftKings/FanDuel系)に大刷新する。

## スコープ

### 残す機能（5つだけ）
1. **🔥 鉄板3台** (ホーム)
2. **🎰 来店モード** (ホーム)
3. **📈 年間トラッカー** 円形プログレスのみ (ホーム)
4. **✏️ クイック記録** (記録タブ)
5. **💾 データバックアップ** (設定タブ)

### 削除する機能（多数）
- ホール/機種/ツール タブ全体
- 避けたい候補
- 月予算ガード
- 衝動チェック（CBT）
- カレンダー
- 月次レポート
- 収支グラフ
- Forward Test
- 今日スコアAI / 狙い目判定 / 天井期待値計算 / AI収支分析
- 動的エリアデータ / マイホール詳細 / 研究タブ
- データ鮮度バッジ（鉄板3台に統合）
- 3指標 / 3アクションボタン / ヒーロー描画
- アコーディオン群全部

---

## デザインシステム: "Pro Sportsbook"

DraftKings/FanDuel 系の高コントラスト勝負ツール風。

### カラーパレット
```css
:root {
  --bg:        #0a0d1a;  /* 極暗紺 */
  --bg2:       #14182a;  /* カード */
  --bg3:       #1d2238;  /* ホバー/サブ */
  --accent:    #ff6b00;  /* レッドオレンジ(メインアクション) */
  --accent2:   #00d68f;  /* 勝ち緑 */
  --danger:    #ff3b5c;  /* 負け赤 */
  --gold:      #ffc73e;  /* ハイライト */
  --text:      #f8f9fc;
  --text2:     #b8bcd0;
  --muted:     #6f7494;
  --border:    rgba(255,255,255,0.06);
  --font-display: 'Inter', 'Manrope', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

### スタイル方針
- **角丸控えめ** (10-12px、カードは8px)
- **太字主体** (フォントweight 700-900)
- **矩形ベース**: グラスは廃止、ソリッドカード
- **アクセント色は要所のみ**: ボタン、選択中、警告
- **アニメ控えめ**: 0.15s transition のみ、フェード/グロー類は最小限
- **数値巨大化**: 主要数値は font-size 32-56px、tabular-nums

### コンポーネント別

**カード**:
```css
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}
```

**メインボタン (CTA)**:
```css
.btn-primary {
  background: var(--accent);
  color: #000;
  border: none;
  padding: 16px 20px;
  border-radius: 10px;
  font-weight: 900;
  font-size: 15px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: 0 4px 0 #c54f00;
  transition: transform 0.1s;
}
.btn-primary:active { transform: translateY(2px); box-shadow: 0 0 0 #c54f00; }
```

**ナビバー** (底部固定):
```css
nav {
  background: var(--bg2);
  border-top: 2px solid var(--border);
  height: 64px;
}
nav button {
  color: var(--muted);
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
}
nav button.active {
  color: var(--accent);
  border-top: 3px solid var(--accent);
}
```

### Aurora 関連の完全廃止
- `body::before/::after` のオーロラブロブ削除
- `backdrop-filter: blur` 廃止（パフォーマンス向上にも寄与）
- グラデーション最小化、Glass調廃止

---

## レイアウト

### ナビバー (3タブ)
```
[🏠 ホーム]  [✏️ 記録]  [⚙️ 設定]
```

### ホーム画面 (page-home)
```
┌─────────────────────────┐
│ 📊 データ更新: 5/26       │ ← 小さく(鮮度+データ件数)
├─────────────────────────┤
│ 🔥 今日の鉄板3台          │
│ ┌──────────────────┐  │
│ │ 🥇 機種名         92 │ │ (金枠)
│ │ ⚙ 設定6:110% 天井:1480│  │
│ │ 朝1番乗り推奨 ★★★    │  │
│ └──────────────────┘  │
│ [🥈 機種名      78]     │
│ [🥉 機種名      71]     │
├─────────────────────────┤
│ 🎰 来店モード             │
│ [▶ LIVEを開始する]       │  ← レッドオレンジCTA
├─────────────────────────┤
│ 📈 年間100万円トラッカー   │
│      ⭕                 │
│     45%                 │ (円形プログレス + 大型数字のみ、月別バー廃止)
│  ¥450,000 / ¥1,000,000  │
└─────────────────────────┘
```

### 記録画面 (page-record)
```
┌─────────────────────────┐
│ ✏️ クイック記録            │
│ 機種を選ぶ                │
│ [機種1] [機種2] [機種3]  │
│ [+その他]                │
│ 差枚 +2,500              │
│ [-2k][-1k][-500][+500][+1k][+2k]│
│ [0クリア] [編集]          │
│ 投資 ¥5,000              │
│ [+1k][+5k][+10k][編集]   │
│ 撤退理由                  │
│ [損切り][勝ち逃げ][通常]   │
│ [💾 保存]                │
└─────────────────────────┘
```
※ OCR・詳細フォーム廃止、これ1画面だけ

### 設定画面 (page-settings)
```
┌─────────────────────────┐
│ 💾 データバックアップ      │
│ ✅ 最終: 今日             │
│ [📥 JSONで保存]          │
│ [📤 上書きインポート]     │
│ [📤 マージインポート]     │
├─────────────────────────┤
│ 🎯 年間目標               │
│ ¥1,000,000               │
│ [編集]                   │
├─────────────────────────┤
│ ℹ️ アプリ情報             │
│ Version: 27              │
└─────────────────────────┘
```

---

## 削除タスク詳細

### HTML削除
- `<div id="page-hall">`
- `<div id="page-area">`
- `<div id="page-research">`
- `<div id="page-machine">`
- `<div id="page-strategy">`
- `<div id="page-myhall">`
- `<div id="page-tools">`
- `<div id="page-history">`
- ナビバーの ホール/機種/ツール ボタン
- ホーム内: 鮮度バッジ(別位置)/3指標/3ボタン/避けたい/月予算/カレンダー/アコーディオン群すべて
- 記録ページ内: OCRカメラ/ファイル/詳細フォーム (アコーディオン丸ごと)

### JS関数削除
- `renderHall`, `renderArea`, `renderMyHall`, `研究タブ描画`, `攻略リスト描画`, `renderMachine`, `renderTools`
- `今日の狙い目スコア生成`, `今日の狙い目描画`
- `避けたい5台描画`, `今日の避けたい5台生成`
- `月予算計算`, `月予算描画`, `月予算編集`
- `衝動チェック開く`, `衝動チェック保存`, `衝動タイマー開始`, `衝動再評価`, `衝動ログ統計`, `衝動ログ描画`
- `カレンダー描画`, `カレンダー前月`, `カレンダー次月`, `カレンダーセル編集`
- `月次レポート生成`, `月次レポートモーダル`
- `収支グラフ_月別データ`, `収支グラフ_機種別データ`, `収支グラフ_週次勝率データ`, `収支グラフ描画`, `収支グラフタブ切替`, `年間スパークライン描画`
- `事前選択ForwardTest`, `事前選択ForwardTest描画`, `事前選択候補生成`, `事前選択描画`
- `今日の判断`, `ヒーロー描画`
- `日付ブースト判定` (鉄板3台で内部使用していなければ削除、内部使用なら維持)
- `OCR画像送信`, AI関連関数群
- `データ鮮度取得`, `データ鮮度表示`

### CSS削除
- 上記関連 CSS 全て (.preselect-*, .avoid-*, .urge-*, .cal-*, .report-*, .pnl-*, .signal-*, .kpi-trio*, .hero-*, .acc-card, .annual-monthly* など)
- Aurora関連 (body::before, body::after, @keyframes auroraFloat)
- backdrop-filter 全廃止

### 残す関数
- `showPage`, `_renderForPage`
- `renderHome` (内容超ミニマル化)
- `鉄板3台描画`, `今日の鉄板3台生成`, `鉄板3台拡張情報`, `機種スペック取得`, `MACHINE_SPEC_DB`
- `年間目標取得`, `年間目標保存`, `年間目標編集`, `年間進捗計算`, `年間進捗詳細`, `年間トラッカー描画` (シンプル化)
- `来店モード開始ダイアログ`, `来店モード描画`, `来店モード終了`, `来店セッション取得/保存/削除`, `来店差枚調整`, `来店差枚クリア`, `来店差枚編集`, `来店投資追加`, `来店投資クリア`, `来店投資編集`, `来店理由選択`, `来店アラートチェック`, `来店警告表示`, `来店タイマー開始`, `来店EV計算`, `来店振り返りモーダル`
- `よく打つ機種Top3`, `クイック機種候補描画`, `クイック機種選択`, `クイック機種その他`, `クイック差枚調整/クリア/編集/表示更新`, `クイック投資追加/クリア/編集/表示更新`, `クイック理由選択`, `クイック保存`, `クイック記録初期化`, `事前選択マッチ`
- `BACKUP_KEYS`, `データエクスポート`, `データインポート`, `バックアップ状態表示`
- `通知表示`, `Telemetry` (簡素化)

---

## 受け入れ基準

- [ ] ナビバーが3タブ (ホーム/記録/設定) のみ
- [ ] ホームに 鮮度バッジ+鉄板3台+来店モードCTA+年間トラッカー円形 だけ
- [ ] 記録ページにクイック記録のみ (OCR/詳細削除)
- [ ] 設定ページにバックアップ+年間目標編集+バージョン情報
- [ ] 削除リストの関数定義が0件
- [ ] 削除リストのCSS定義が0件
- [ ] Aurora body::before/::after 削除
- [ ] DraftKings風カラーパレット適用 (`--accent: #ff6b00`)
- [ ] 既存核機能(鉄板3台/来店モード/クイック記録/年間トラッカー/バックアップ)動作
- [ ] sw.js `v29-minimal-sportsbet`

## 検証スクリプト

```bash
cd /tmp/slot-dashboard-pwa && \
  echo "=== 削除関数 ===" && \
  for f in renderHall renderMyHall renderMachine renderTools 衝動チェック開く カレンダー描画 月次レポートモーダル 収支グラフ描画 事前選択描画 ヒーロー描画 月予算描画 避けたい5台描画 今日の判断 データ鮮度表示; do
    c=$(grep -c "function $f" index.html)
    [ "$c" = "0" ] && echo "  $f: ✅0" || echo "  $f: ❌$c"
  done && \
  echo "=== 削除タブ ===" && \
  for p in page-hall page-area page-research page-machine page-strategy page-myhall page-tools page-history; do
    c=$(grep -c "id=\"$p\"" index.html)
    [ "$c" = "0" ] && echo "  $p: ✅0" || echo "  $p: ❌$c"
  done && \
  echo "=== 残す関数 ===" && \
  for f in 鉄板3台描画 来店モード描画 クイック保存 年間トラッカー描画 データエクスポート; do
    c=$(grep -c "function $f" index.html)
    [ "$c" -ge "1" ] && echo "  $f: ✅$c" || echo "  $f: ❌MISSING"
  done && \
  echo "=== カラー ===" && grep -c "ff6b00" index.html
```

## リスク

| リスク | 緩和 |
|---|---|
| 大規模削除で既存リファレンス漏れ → ReferenceError | 削除後 grep で残存呼出ゼロを検証 |
| サブタブMAP(SUBTAB_MAP)構造変更で showPage 破壊 | 3タブのみのシンプルshowPageに書換 |
| backdrop-filter 削除で見た目スカスカ | ソリッドカード+太枠+大型数字で代替 |
| localStorage キーは保全 | データキー(records等)は触らず関数だけ削除 |
| GHA scrape/harness_daily の commitメッセージ生成は壊さない | data/ ファイル形式は変更なし |

## 実装単位

1サイクル(#27)で完結。約 4000-6000行削減見込み (前回 -2031 を大幅に超える)。

## Self-review
- [x] 残す機能5つ・削除リスト多数を明示
- [x] デザイン方針色コード明示
- [x] 検証スクリプト具体的
- [x] 既存データ保全明示
- [x] リスク緩和策あり
