# Cycle#31 設計仕様: ハイエナ判定 + 現場デザイン刷新

**作成日**: 2026-06-03  
**CEO承認**: ハイエナ判定機能 + デザイン刷新

## 背景

「店でスマホ片手に、この台打つべきか3秒で判断」が最大の実用ニーズ。現状、天井期待値計算がCycle#23/27で削除され現場判断ができない。これを **ハイエナ判定** として復活・強化し、現場で使える大型UIに刷新する。

## 機能設計

### 機能1: ハイエナ判定モーダル

ホーム最上部に「🎰 ハイエナ判定」大ボタン → タップでフルスクリーンモーダル。

**入力**:
1. 機種選択 (よく打つ機種3 + その他)
2. 現在G数 (大型テンキー or +100/+50ボタン)

**出力(即計算)**:
```
スマスロ北斗の拳 転生の章2
現在 920G

┌──────────────────────┐
│  💰 期待値              │
│   +1,850円            │  ← 特大、緑/赤
│                        │
│  🎯 天井まで: 560G     │
│  ⏱️ 想定投資: ¥8,400   │
│  📊 ボーダー: 600G     │
│                        │
│  🟢 打つ価値あり        │  ← 判定バッジ
└──────────────────────┘
```

### 期待値計算ロジック

```js
function ハイエナ期待値計算(machineName, currentG) {
  const spec = (typeof 機種スペック取得 === 'function') ? 機種スペック取得(machineName) : null;
  if (!spec || !spec.tenjo_g || spec.tenjo_g === 0) {
    return { applicable: false, reason: '天井のない機種(ノーマルタイプ等)' };
  }
  const tenjoG = spec.tenjo_g;
  const borderG = spec.ev_threshold_g || Math.round(tenjoG * 0.4);
  const remainG = Math.max(0, tenjoG - currentG);
  
  // 投資見込み: 残りG × 1Gあたりコスト(約3円: 50枚/1000円 → 1G=約3.3円, 通常時)
  const costPerG = 3.3;
  const estimatedInvest = Math.round(remainG * costPerG);
  
  // 天井到達時の期待出玉(機種別、平均的なAT/ART初当たり出玉を仮定)
  // 簡易: 天井恩恵 = 機種の1撃平均(2400枚相当を等価換算) を上限に、現在地点での期待値
  // EV = (天井到達による期待差枚×レート) - 投資
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { rate_yen_per_piece: 20 };
  
  // 天井到達時の平均獲得枚数(機種タイプ別の概算)
  const tenjoReward = spec.type === 'AT' ? 1500 : spec.type === 'ART' ? 1200 : 800; // 枚
  const rewardYen = tenjoReward * conf.rate_yen_per_piece;
  
  // 期待値 = 天井期待出玉円 - 投資円 (現在Gがボーダー以降なら基本プラス)
  const ev = rewardYen - estimatedInvest;
  
  // 判定
  let verdict, color;
  if (currentG >= borderG) { verdict = '打つ価値あり'; color = 'go'; }
  else if (currentG >= borderG * 0.7) { verdict = 'ボーダー手前・微妙'; color = 'caution'; }
  else { verdict = '早い・見送り推奨'; color = 'stop'; }
  
  return {
    applicable: true,
    tenjo_g: tenjoG, border_g: borderG, remain_g: remainG,
    estimated_invest: estimatedInvest, ev: ev,
    verdict, color,
  };
}
```

**注**: 期待値は概算（機種別の正確なシミュレーション値ではない）。spec で「目安」と明示。

### 機能2: 来店モード統合

来店モードのLIVEカード内に「📊 今から続行？」ボタン追加。タップで現在セッションの機種・推定G数(既存`来店EV計算`の estimatedG)を使い `ハイエナ期待値計算` を実行、結果を inline 表示。

### 機能3: 大型タップUI

ハイエナ判定モーダルの入力:
- 機種ボタン: 高さ56px以上
- G数入力: `[+500][+100][+50][-50]` の大ボタン + 直接編集
- 判定結果: 期待値を font-size 48px 特大

## デザイン刷新（現場最適化）

DraftKings風を維持しつつ、現場での視認性を上げる微調整:
- **タップターゲット最小48px** (Appleガイドライン準拠)
- **判定色の明確化**: 🟢GO=緑グロー / 🟡注意=黄 / 🔴見送り=赤
- ホームの主要ボタン(ハイエナ判定/LIVE)を**画面幅いっぱいの大型CTA**に
- セクション間の余白を増やし、屋内照明下でも各要素が分離して見える
- 数値は全て tabular-nums + 大型

## HTML/CSS/JS

### HTML (ホーム最上部、データ更新バッジの下)
```html
<button class="hyena-btn" onclick="ハイエナ判定開く()">
  🎰 ハイエナ判定 <span class="hyena-btn-sub">この台、打つべき？</span>
</button>

<div id="hyena-modal" class="hyena-modal" style="display:none">
  <div class="hyena-inner">
    <div class="hyena-header">
      <div class="hyena-title">🎰 ハイエナ判定</div>
      <button class="hyena-close" onclick="ハイエナ判定閉じる()">✕</button>
    </div>
    <div class="hyena-body">
      <div class="hyena-label">機種を選ぶ</div>
      <div id="hyena-machines" class="hyena-machines"></div>
      <div class="hyena-label">現在のG数</div>
      <div class="hyena-g-display" id="hyena-g">0</div>
      <div class="hyena-g-buttons">
        <button onclick="ハイエナG調整(500)">+500</button>
        <button onclick="ハイエナG調整(100)">+100</button>
        <button onclick="ハイエナG調整(50)">+50</button>
        <button onclick="ハイエナG調整(-50)">-50</button>
        <button onclick="ハイエナGクリア()">C</button>
      </div>
      <div id="hyena-result" class="hyena-result"></div>
    </div>
  </div>
</div>
```

### JS関数
- `ハイエナ判定開く()` / `ハイエナ判定閉じる()`
- `ハイエナ機種候補描画()` (よく打つ機種Top3 + 主要機種)
- `ハイエナ機種選択(name)`
- `ハイエナG調整(delta)` / `ハイエナGクリア()`
- `ハイエナ期待値計算(name, g)` (上記)
- `ハイエナ結果描画()` (機種・G選択時に自動呼出)

### CSS (主要)
```css
.hyena-btn {
  width: 100%; padding: 20px; margin-bottom: 16px;
  background: linear-gradient(135deg, #ff6b00, #ffc73e);
  color: #000; border: none; border-radius: 12px;
  font-weight: 900; font-size: 20px; cursor: pointer;
  box-shadow: 0 4px 0 #c54f00;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.hyena-btn-sub { font-size: 12px; font-weight: 700; opacity: 0.8; }
.hyena-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 10000; display: flex; align-items: flex-start; justify-content: center; padding: 16px; overflow-y: auto; }
.hyena-inner { background: var(--bg2); border-radius: 16px; max-width: 480px; width: 100%; margin-top: 20px; }
.hyena-header { display: flex; justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid var(--border); }
.hyena-title { font-size: 18px; font-weight: 900; }
.hyena-close { background: transparent; border: none; color: var(--muted); font-size: 20px; cursor: pointer; }
.hyena-body { padding: 16px; }
.hyena-label { font-size: 11px; color: var(--muted); letter-spacing: 2px; margin: 12px 0 8px; text-transform: uppercase; }
.hyena-machines { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.hyena-mbtn { padding: 16px 10px; background: var(--bg3); border: 2px solid var(--border); border-radius: 10px; color: var(--text); font-weight: 700; font-size: 13px; cursor: pointer; min-height: 56px; }
.hyena-mbtn.active { border-color: var(--accent); background: rgba(255,107,0,0.15); }
.hyena-g-display { font-family: var(--font-mono); font-size: 48px; font-weight: 900; text-align: center; color: var(--accent); padding: 12px; background: var(--bg3); border-radius: 12px; margin-bottom: 8px; }
.hyena-g-buttons { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
.hyena-g-buttons button { padding: 16px 4px; background: var(--bg3); border: 1px solid var(--border); color: var(--text); border-radius: 8px; font-weight: 700; font-family: var(--font-mono); cursor: pointer; min-height: 48px; }
.hyena-result { margin-top: 16px; padding: 20px; border-radius: 12px; text-align: center; }
.hyena-result.go { background: rgba(0,214,143,0.12); border: 2px solid var(--accent2); }
.hyena-result.caution { background: rgba(255,199,62,0.12); border: 2px solid var(--gold); }
.hyena-result.stop { background: rgba(255,59,92,0.12); border: 2px solid var(--danger); }
.hyena-ev { font-family: var(--font-mono); font-size: 48px; font-weight: 900; margin: 8px 0; }
.hyena-ev.pos { color: var(--accent2); }
.hyena-ev.neg { color: var(--danger); }
.hyena-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }
.hyena-detail { padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; }
.hyena-detail-label { font-size: 10px; color: var(--muted); }
.hyena-detail-val { font-family: var(--font-mono); font-size: 16px; font-weight: 700; margin-top: 2px; }
.hyena-verdict { font-size: 20px; font-weight: 900; margin-top: 8px; }
.hyena-verdict.go { color: var(--accent2); }
.hyena-verdict.caution { color: var(--gold); }
.hyena-verdict.stop { color: var(--danger); }
.hyena-na { padding: 20px; text-align: center; color: var(--muted); }
```

## sw.js
CACHE_NAME を `v33-hyena` に bump

## 受け入れ基準
- [ ] ホーム最上部に「🎰 ハイエナ判定」大ボタン
- [ ] タップでモーダル(機種選択+G数入力)
- [ ] 機種+G数選択で期待値・天井まで・想定投資・判定を即表示
- [ ] 判定色 🟢/🟡/🔴 で分岐
- [ ] 天井のない機種は「対象外」表示
- [ ] 来店モードに「今から続行？」判定統合
- [ ] タップターゲット48px以上
- [ ] sw.js v33-hyena
- [ ] 既存機能(鉄板3台/来店モード/年間トラッカー/クイック記録/バックアップ/札幌注目台)破壊なし

## リスク
| リスク | 緩和 |
|---|---|
| 期待値が概算で不正確 | 「目安」明示、ボーダー判定を主軸に |
| 天井G未設定機種でcrash | applicable:false でフォールバック |
| モーダルが既存モーダルとz-index競合 | z-index 10000 統一 |

## Self-review
- [x] プレースホルダーなし
- [x] 計算ロジック完備
- [x] 概算の旨を明示
- [x] フォールバックあり
- [x] 既存影響明示
