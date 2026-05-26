# Cycle#23 設計仕様: 機能整理（削除+強化）

**作成日**: 2026-05-24  
**CEO承認**: 削除3項目+強化3項目を一気に実装

## 背景

22サイクル分の機能が積み重なり「多すぎて見づらい」状態。CEO直接ご指示で不要削除・主要強化を実行する。

## 削除セクション

### 削除1: GAMEタブ（ミリオンゴッドシミュレータ）

**目的**: 装飾的要素で勝率に無関係、依存リスクの観点でも削除推奨。

**対象**:
- ナビバー: `nav` 内の `🎮 GAME` ボタン
- ページ: `<div id="page-game">` 丸ごと
- 関数: `gInit, gSpin, gStopReel, gAfterStop, gDecideResult, gScreenEffect, gFreeze, gStartGG, gEndGGSet, gShowEndScreen, g偶奇示唆生成`
- 定数: `G_SYM_SVG, G_REELS_DEF, G_AT_RATE, G_CEILING`
- CSS: `.gMachine*, .gScreen*, .gReel*, .gFreeze*, .gGod*` 等全game関連
- showPage 内の `if (id === 'game') gInit();`

### 削除2: 信号機 (GO/CAUTION/STOP)

**対象**:
- `#hero-signal-area` 内の `.signal-banner` divを削除（`.kpi-trio`, `.hero-actions`, `.acc-hint` は維持）
- 関数: `今日の判断, ヒーロー描画` の signal-banner 操作部分を削除
- CSS: `.signal-banner, .signal-banner-compact, .signal-icon, .signal-verdict, .signal-reason, .signal-go, .signal-caution, .signal-stop`

### 削除3: 設定6アラート + ベイズ + 朝一抽選

**対象**:
- ホーム/マイホの `#設定6アラート_home` `#設定6アラート_myhall` DOM削除
- 関数 `設定6アラート描画` 削除
- ツールタブ内のベイズ推測カード+関数（`ベイズ推測実行`, `設定推測実行`等）削除
- 朝一抽選シミュレータカード+関数（`抽選シミュレーター実行`等）削除

**注**: 機種スペックDB（`MACHINE_SPEC_DB`）は鉄板3台と Forward Test で使うので**維持**。

## 強化セクション

### 強化1: 鉄板3台 — 主軸機能リッチ化

`MACHINE_SPEC_DB` に追加フィールド:
```js
"スマスロ北斗の拳 転生の章2": {
  ...既存,
  reset_advantage: "A",   // A=強, B=中, C=弱 (リセット恩恵)
  reset_note: "リセット後200G以内"
}
```

新計算ロジック `鉄板3台拡張情報(name)`:
```js
function 鉄板3台拡張情報(name, history) {
  const spec = 機種スペック取得(name);
  // 近接10日勝率
  const recent10 = history.slice(0, 10);
  let wins = 0, app = 0, sa10 = 0;
  recent10.forEach(d => {
    const ms = (d.machines||[]).filter(m => m.name === name && m.sa != null);
    ms.forEach(m => { app++; sa10 += m.sa; if (m.sa > 0) wins++; });
  });
  const winRate10 = app > 0 ? Math.round(wins/app*100) : null;
  // 見せうち推奨度
  const boost = (typeof 日付ブースト判定 === 'function') ? 日付ブースト判定(new Date()) : {boost:1.0};
  const showScore = (winRate10 || 50) * boost.boost;
  // アクション推奨
  let action = '通常狙い';
  if (spec && spec.reset_advantage === 'A') action = '⏰ 朝1番乗り推奨';
  else if (spec && spec.tenjo_g > 0) action = `🎯 ${spec.tenjo_g}G台があれば狙い`;
  return { reset_advantage: spec?.reset_advantage || null, winRate10, sa10, showScore: Math.round(showScore), action };
}
```

鉄板3台カードに追加表示:
- `⏰ 朝一推奨度: A` 行
- `📊 近10日勝率: 80% (4/5回出現)`
- `🎯 推奨アクション: 朝1番乗り推奨`

### 強化2: 年間トラッカー — 達成予測誠実化

新算出 `年間進捗詳細()`:
```js
function 年間進捗詳細() {
  const base = 年間進捗計算();
  const remaining = base.remaining_yen;
  // 今週あと何回打てば良いか（平均勝ち額1万円仮定で逆算）
  const weeklyNeeded = Math.ceil(remaining / 52 / 10000); // 残週数の必要回数
  // 込み状態
  let difficulty = '楽勝';
  if (base.needed_per_day_yen > 5000) difficulty = '厳しい';
  else if (base.needed_per_day_yen > 2000) difficulty = '普通';
  else if (base.needed_per_day_yen > 500) difficulty = '楽勝';
  else difficulty = '安全圏';
  if (remaining < 0) difficulty = '達成済';
  if (base.needed_per_day_yen > 10000) difficulty = '困難';
  // 直近30日トレンド
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const last30 = records.filter(r => new Date(r.date).getTime() >= Date.now() - 30*86400000);
  const prev30 = records.filter(r => {
    const t = new Date(r.date).getTime();
    return t < Date.now() - 30*86400000 && t >= Date.now() - 60*86400000;
  });
  const sumLast = last30.reduce((s,r) => s + (parseInt(r.差枚)||0), 0);
  const sumPrev = prev30.reduce((s,r) => s + (parseInt(r.差枚)||0), 0);
  const trend = sumLast > sumPrev * 1.1 ? '↑' : sumLast < sumPrev * 0.9 ? '↓' : '→';
  return { ...base, weeklyNeeded, difficulty, trend };
}
```

年間トラッカー描画に追加カード:
```
今週あと N回 打てば軌道
込み状態: 普通 (オレンジ)
直近トレンド: ↑改善中
```

スパークラインに「目標達成ライン」を破線で重ねる（既存Chart.jsの dataset 追加で実装）。

### 強化3: 来店LIVEモード — 期待値とクーリングオフ

新計算 `来店EV計算()`:
```js
function 来店EV計算(session) {
  const spec = (typeof 機種スペック取得 === 'function') ? 機種スペック取得(session.machine) : null;
  const elapsedMin = (Date.now() - new Date(session.start_time).getTime()) / 60000;
  // 推定G数（仮定: 1分あたり9G）
  const estimatedG = session.game_count || Math.round(elapsedMin * 9);
  // 1Gあたり実差枚
  const realPerG = estimatedG > 0 ? session.current_sa / estimatedG : 0;
  // 機種DB期待値（設定3-4想定 = 100%）
  const machineEV = spec ? ((spec.kikai_warii[4] - 100) / 100) * 3 : 0;  // 1Gあたり差枚 (3枚ベース)
  // クーリングオフ判定
  const isOverTenjo = spec && spec.tenjo_g > 0 && estimatedG >= spec.tenjo_g + 200;
  const isLongLoss = elapsedMin >= 30 && session.current_sa <= -1000;
  const isFastInvest = (session.investment_yen / Math.max(elapsedMin, 1)) > 666;  // 15分で1万円ペース超
  return { 
    estimatedG, realPerG: Math.round(realPerG * 100) / 100, 
    machineEV: Math.round(machineEV * 100) / 100,
    cooloff: isOverTenjo || isLongLoss, 
    fastInvest: isFastInvest,
    cooloffReason: isOverTenjo ? '天井超ハマり台' : isLongLoss ? '30分継続マイナス' : null
  };
}
```

LIVEカード内に新エリア:
```html
<div class="live-ev-area">
  <div>📈 1G実差枚: <strong id="live-real-per-g">--</strong></div>
  <div>🎯 機種DB期待値: <strong id="live-machine-ev">--</strong></div>
  <div id="live-cooloff" class="live-cooloff" style="display:none">⏸️ クーリングオフ推奨</div>
  <div id="live-fastinvest" class="live-warning" style="display:none">🚨 投資ペース注意</div>
</div>
```

`来店モード描画` の末尾で `来店EV計算` を呼び、上記要素を更新。

## sw.js
CACHE_NAME を `v25-cleanup-boost` に bump

## 受け入れ基準

### 削除
- [ ] ナビバーから GAME ボタン消失
- [ ] `page-game` div 存在せず
- [ ] `gInit, gSpin` 等の game 関数定義0
- [ ] `.signal-banner` CSS / `今日の判断, ヒーロー描画` 内の signal 操作削除
- [ ] `#設定6アラート_home/_myhall` 削除、`設定6アラート描画` 関数なし
- [ ] ツールタブからベイズ推測カード / 朝一抽選シミュ消失

### 強化
- [ ] 鉄板3台カードに「朝一推奨度」「近10日勝率」「推奨アクション」表示
- [ ] 年間トラッカーに「今週あとN回」「込み状態」「トレンド↑」表示
- [ ] 来店LIVEモードに「1G実差枚」「機種DB期待値」「クーリングオフ警告」表示

### 共通
- [ ] sw.js `v25-cleanup-boost`
- [ ] 既存核機能(鉄板3台/年間トラッカー/来店モード/クイック記録/月次レポート/カレンダー/収支グラフ) 動作

## リスク
| リスク | 緩和 |
|---|---|
| GAME関連の大規模削除で別機能を巻き添え | コミット前に grep で重要関数(renderHome等)の存在確認 |
| 信号機削除でレイアウト崩れ | ホーム再描画で空エリアが残らないか目視確認 |
| 強化部分の計算式不正確 | 仮定値（1分9G、設定3-4=100%）を spec doc に明示 |

## Self-review
- [x] プレースホルダー無し
- [x] 削除リストが具体的
- [x] 強化部分の関数仕様が完備
- [x] リスクと緩和策あり
