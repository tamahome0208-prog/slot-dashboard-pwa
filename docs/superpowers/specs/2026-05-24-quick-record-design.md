# Cycle#21 設計仕様: クイック記録（1タップ入力）

**作成日**: 2026-05-24  
**CEO承認方針**: 案A + 差枚ショートカット + 投資予算ボタンも追加

## 背景・目的

現状の記録フォームはOCR画像取込+多項目フィールドで入力に2-3分かかる。**1タップ操作**で30秒以内に記録完了する画面を新設し、データ蓄積を加速する。年間トラッカー・Forward Test精度向上に直結。

## スコープ

新規UI: クイック記録モード（記録ページの上位として）  
既存維持: 詳細入力フォーム（アコーディオンで保全）

## 設計

### 1. UI構成（page-record の最上部に追加）

```
🎰 クイック記録
─────────────────────────
機種を選ぶ
[頻度Top1] [頻度Top2] [頻度Top3] [+その他]
─────────────────────────
差枚  +2,500
[-2000][-1000][-500] [+500][+1000][+2000]
[0クリア][⌫][直接編集]
─────────────────────────
投資
[+1k][+5k][+10k][編集]
─────────────────────────
撤退理由
[🛡️損切り] [🏆勝ち逃げ] [通常]
─────────────────────────
⚙️ 詳細入力（店舗・台番号・G数・OCR等）▼
─────────────────────────
[💾 1タップ保存]
```

### 2. 「よく打つ機種」推定ロジック

```js
function よく打つ機種Top3() {
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const since = Date.now() - 30*86400000;
  const recent = records.filter(r => new Date(r.date).getTime() >= since);
  const count = {};
  recent.forEach(r => { 
    const n = r['機種']; 
    if (n) count[n] = (count[n] || 0) + 1; 
  });
  const sorted = Object.entries(count).sort((a,b) => b[1] - a[1]).slice(0, 3);
  // 不足時は鉄板3台で補完（実装時に取得済みなら）
  return sorted.map(([n]) => n);
}
```

### 3. データ構造

既存 `records` 配列に追加フィールドなし。クイック記録でも詳細記録でも同じ形式で保存:
```js
{ date, hall, 機種, 台番号, 差枚, 投資, 撤退理由, source: 'quick'|'detail'|'live_session' }
```

### 4. 差枚クイック入力ロジック

```js
let _quick_sa = 0;
function クイック差枚調整(delta) { _quick_sa += delta; クイック差枚表示更新(); }
function クイック差枚クリア() { _quick_sa = 0; クイック差枚表示更新(); }
function クイック差枚編集() { 
  const v = parseInt(prompt('差枚を直接入力', _quick_sa)); 
  if (!isNaN(v)) { _quick_sa = v; クイック差枚表示更新(); } 
}
```

### 5. 投資クイック入力

同様に `_quick_invest = 0`、`+1000` `+5000` `+10000` ボタン3つと編集ボタン1つ。

### 6. 機種選択ロジック

ボタンクリックで `_quick_machine` に文字列セット、選択中ボタンに視覚フィードバック（cyan枠）。「+その他」で datalist 付き input を展開（既存機種リストから候補）。

### 7. 保存処理

```js
async function クイック保存() {
  if (!_quick_machine) { alert('機種を選んでください'); return; }
  const today = new Date().toISOString().slice(0, 10);
  const rec = {
    date: today,
    hall: localStorage.getItem('default_hall') || 'ロイヤル登別店',
    機種: _quick_machine,
    台番号: '',
    差枚: _quick_sa,
    投資: _quick_invest,
    撤退理由: _quick_reason || '通常終了',
    source: 'quick',
    pre_selected: await 事前選択マッチ(_quick_machine)  // 既存関数活用
  };
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  records.push(rec);
  localStorage.setItem('records', JSON.stringify(records));
  // リセット
  _quick_sa = 0; _quick_invest = 0; _quick_machine = null; _quick_reason = null;
  if (typeof renderHome === 'function') renderHome();
  通知表示 && 通知表示('✅ 記録を保存しました');
}
```

### 8. 既存フォーム保全

既存の page-record 内 OCR / 詳細フォームは `<details class="acc-card">` で包む。デフォルト closed。

### 9. ホームからの動線

ホームの「✏️記録する」ボタンは既に showPage('record') で記録ページへ遷移。新しいクイック記録UIが最上部に来るので動線変更不要。

### 10. CSS

```css
.qrec-section { padding: 14px; background: var(--glass-bg); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 12px; margin-bottom: 12px; }
.qrec-section-title { font-size: 11px; color: var(--muted); letter-spacing: 2px; margin-bottom: 8px; }
.qrec-machine-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.qrec-mbtn { padding: 14px 10px; background: var(--bg3); border: 1.5px solid var(--border); color: var(--text); border-radius: 10px; font-weight: 700; font-size: 13px; cursor: pointer; text-align: left; }
.qrec-mbtn.active { border-color: var(--cyan); background: rgba(124,92,255,0.15); }
.qrec-mbtn-spec { font-size: 10px; color: var(--muted); margin-top: 2px; font-family: var(--font-mono); }

.qrec-sa-display { text-align: center; padding: 16px; background: var(--bg3); border-radius: 10px; margin-bottom: 10px; }
.qrec-sa-num { font-family: var(--font-mono); font-size: 42px; font-weight: 900; }
.qrec-sa-num.pos { color: #22d3a3; } .qrec-sa-num.neg { color: #ff4d6d; }

.qrec-sa-buttons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 6px; }
.qrec-sa-btn { padding: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text); border-radius: 8px; font-weight: 700; font-family: var(--font-mono); cursor: pointer; }
.qrec-sa-btn.minus { color: #ff4d6d; } .qrec-sa-btn.plus { color: #22d3a3; }

.qrec-reason-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.qrec-rbtn { padding: 12px; background: var(--bg3); border: 1px solid var(--border); color: var(--text); border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 12px; }
.qrec-rbtn.active { border-color: var(--cyan); background: rgba(124,92,255,0.15); }

.qrec-save-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #7c5cff, #22d3a3); color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 20px rgba(124,92,255,0.3); margin-top: 14px; }
```

## 受け入れ基準

- [ ] 記録ページ最上部に「🎰クイック記録」エリア表示
- [ ] よく打つ機種Top3が自動表示・選択可
- [ ] 差枚 ±500/±1000/±2000 + クリア/編集 動作
- [ ] 投資 +1k/+5k/+10k + 編集 動作
- [ ] 撤退理由3ボタン動作
- [ ] 1タップ保存で records に追加
- [ ] 事前選択マッチング自動付与
- [ ] 既存詳細フォームは折りたたみで保全
- [ ] 既存機能（OCR/年間トラッカー/来店モード等）破壊なし

## デプロイ

- sw.js CACHE_NAME を `v23-quick-record` に bump
- 単一コミットで push

## リスク

| リスク | 緩和策 |
|---|---|
| 既存records構造変更で他機能破壊 | 新規フィールドは source/pre_selected のみで非破壊 |
| 「機種未選択」のまま保存 | 保存前バリデーション |
| 既存OCR/詳細フォームが見えなくなる | アコーディオンで「⚙️詳細入力」として保全 |

## Self-review

- [x] プレースホルダーなし
- [x] 各セクションが独立して読める
- [x] 受け入れ基準がチェック可能
- [x] 既存機能への影響を明示
