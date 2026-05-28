# Cycle#28 設計仕様: 鉄板3台への勝率情報統合

**作成日**: 2026-05-27  
**CEO承認**: A+B+C 全部を鉄板3台に集約 (新タブ・新カード追加なし)

## 背景

Cycle#27で超ミニマル化(5機能)した直後。新機能追加はNGだが、CEOから「勝率上げる情報を集めて反映」要求。**鉄板3台カード内に折りたたみで情報密度を上げる**方式でミニマル維持しつつ実現する。

## スコープ

鉄板3台カードに「💡 もっと詳しく」展開を追加し、A機種攻略+B店舗傾向+C個人パターン を統合表示。

## 設計

### Section A: 機種攻略情報

`MACHINE_SPEC_DB` の主要機種に以下フィールド追加:
```js
"スマスロ北斗の拳 転生の章2": {
  ...既存,
  uchikata: "順押し→中右で1枚役獲得を狙う",
  yamedoki: "AT後即/300G/600G/天井1480G到達後",
  settei_diff: "中段チェリー高設定1/655 vs 低設定1/630",
  reset_target: "リセット後0-200G狙い目"
}
```

対象機種(20機種、実機攻略情報をWebSearchで取得):
- スマスロ北斗の拳 転生の章2
- L東京喰種  
- スマスロ甲鉄城のカバネリ 海門決戦
- スマスロとある科学の超電磁砲2
- スマスロ鉄拳6
- L咲-Saki-頂上決戦
- L虚構推理
- スマスロ サンダーV
- スマスロ ハナビ
- A-SLOT+ ディスクアップ ULTRAREMIX
- スマスロ新鬼武者3
- L ULTRAMAN
- スマスロ北斗の拳
- スマスロ デビルメイクライ5 スタイリッシュトライブ
- L無職転生
- パチスロ わたしの幸せな結婚
- パチスロ 転生したら剣でした
- スマスロ化物語
- A-SLOT+異世界かるてっとBT
- 残り20機種は実装時に追加

新関数 `機種攻略情報取得(name)`:
```js
function 機種攻略情報取得(name) {
  const spec = 機種スペック取得(name);
  if (!spec) return null;
  return {
    uchikata: spec.uchikata || null,
    yamedoki: spec.yamedoki || null,
    settei_diff: spec.settei_diff || null,
    reset_target: spec.reset_target || null,
  };
}
```

### Section B: 店舗傾向情報

新関数 `今日の店舗傾向()`:
- 日付ブースト判定取得 (既存 `日付ブースト判定` 関数)
- royal_history.json から該当日タイプ(8のつく日/5のつく日)の過去 avg_sa を集計
- 機種別の店舗実績(過去90日平均)を返す

```js
async function 今日の店舗傾向(machineName) {
  const boost = 日付ブースト判定(new Date());
  let r = null;
  try {
    const res = await fetch('data/royal_history.json', {cache:'no-store'});
    const hist = await res.json();
    hist.sort((a,b) => (parseInt(b.id)||0) - (parseInt(a.id)||0));
    
    // 該当日タイプの過去平均
    const todayDigit = new Date().getDate() % 10;
    const sameDigitDays = hist.filter(d => {
      const day = parseInt((d.date_str||'').split('/')[1] || 0);
      return day % 10 === todayDigit;
    });
    let typeAvg = null;
    if (sameDigitDays.length >= 3) {
      const sums = sameDigitDays.map(d => (d.machines||[]).reduce((s,m) => s + (m.sa||0), 0));
      typeAvg = Math.round(sums.reduce((s,v)=>s+v,0) / sums.length);
    }
    
    // 機種別の店舗実績(過去90日平均)
    let machineAvg = null;
    if (machineName) {
      const recent = hist.slice(0, 90);
      let sum = 0, count = 0;
      recent.forEach(d => {
        const ms = (d.machines||[]).filter(m => m.name === machineName && m.sa != null);
        ms.forEach(m => { sum += m.sa; count++; });
      });
      if (count >= 3) machineAvg = Math.round(sum / count);
    }
    r = { boost_label: boost.label, type_avg: typeAvg, machine_avg: machineAvg };
  } catch(e) { console.warn(e); }
  return r;
}
```

### Section C: 個人勝ちパターン

新関数 `個人勝ちパターン(name)`:
```js
function 個人勝ちパターン(machineName) {
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const machineRecs = records.filter(r => r['機種'] === machineName);
  if (machineRecs.length < 3) return null;
  
  // 曜日別勝率
  const dowMap = { 0:'日', 1:'月', 2:'火', 3:'水', 4:'木', 5:'金', 6:'土' };
  const dowStats = {};
  machineRecs.forEach(r => {
    const dow = dowMap[new Date(r.date).getDay()];
    if (!dowStats[dow]) dowStats[dow] = { wins: 0, total: 0, sumSa: 0 };
    dowStats[dow].total++;
    const sa = parseInt(r['差枚']) || 0;
    if (sa > 0) dowStats[dow].wins++;
    dowStats[dow].sumSa += sa;
  });
  
  // 最も勝率が高い曜日(n>=2)
  let bestDow = null, bestRate = 0;
  Object.entries(dowStats).forEach(([dow, s]) => {
    if (s.total < 2) return;
    const rate = Math.round(s.wins/s.total*100);
    if (rate > bestRate) { bestRate = rate; bestDow = dow; }
  });
  
  // 通算
  const totalWins = machineRecs.filter(r => (parseInt(r['差枚'])||0) > 0).length;
  const totalSa = machineRecs.reduce((s,r) => s + (parseInt(r['差枚'])||0), 0);
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : {rate_yen_per_piece:20};
  const totalYen = totalSa * conf.rate_yen_per_piece;
  
  return {
    plays: machineRecs.length,
    best_dow: bestDow,
    best_rate: bestRate,
    total_yen: totalYen,
    overall_rate: Math.round(totalWins / machineRecs.length * 100),
  };
}
```

### Section D: UI実装

鉄板3台カード末尾に追加:
```html
<button class="info-toggle" onclick="情報展開('detail-${rank}')">💡 もっと詳しく</button>
<div class="info-detail" id="detail-${rank}" style="display:none">
  <!-- 動的に挿入 -->
</div>
```

展開時の動的描画関数 `鉄板詳細描画(rank, machineName)`:
```js
async function 鉄板詳細描画(rank, machineName) {
  const el = document.getElementById('detail-' + rank);
  if (!el) return;
  
  const safe = s => String(s||'').replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
  
  const guide = 機種攻略情報取得(machineName);
  const hall = await 今日の店舗傾向(machineName);
  const personal = 個人勝ちパターン(machineName);
  
  let html = '';
  
  // A: 攻略
  if (guide && (guide.uchikata || guide.yamedoki || guide.settei_diff || guide.reset_target)) {
    html += '<div class="detail-section"><div class="detail-section-title">📖 機種攻略</div>';
    if (guide.uchikata) html += `<div class="detail-row">✋ 打ち方: ${safe(guide.uchikata)}</div>`;
    if (guide.yamedoki) html += `<div class="detail-row">🛑 辞め時: ${safe(guide.yamedoki)}</div>`;
    if (guide.settei_diff) html += `<div class="detail-row">🔍 設定差: ${safe(guide.settei_diff)}</div>`;
    if (guide.reset_target) html += `<div class="detail-row">🔄 リセット: ${safe(guide.reset_target)}</div>`;
    html += '</div>';
  }
  
  // B: 店舗傾向
  if (hall) {
    html += '<div class="detail-section"><div class="detail-section-title">🏢 店舗傾向</div>';
    if (hall.boost_label && hall.boost_label !== '通常') {
      html += `<div class="detail-row">📅 今日: <strong>${safe(hall.boost_label)}</strong></div>`;
    }
    if (hall.type_avg !== null) {
      const sign = hall.type_avg >= 0 ? '+' : '';
      html += `<div class="detail-row">📊 同日タイプ過去avg: <strong class="${hall.type_avg >= 0 ? 'pos' : 'neg'}">${sign}${hall.type_avg.toLocaleString()}枚/日</strong></div>`;
    }
    if (hall.machine_avg !== null) {
      const sign = hall.machine_avg >= 0 ? '+' : '';
      html += `<div class="detail-row">🎰 この機種の店舗実績(90日): <strong class="${hall.machine_avg >= 0 ? 'pos' : 'neg'}">${sign}${hall.machine_avg.toLocaleString()}枚</strong></div>`;
    }
    html += '</div>';
  }
  
  // C: 個人パターン
  if (personal) {
    html += '<div class="detail-section"><div class="detail-section-title">🎯 あなたのパターン</div>';
    if (personal.best_dow && personal.best_rate > 0) {
      html += `<div class="detail-row">🏆 ${personal.best_dow}曜が得意: <strong>${personal.best_rate}%</strong>勝率</div>`;
    }
    html += `<div class="detail-row">📈 通算: ${personal.plays}戦 / 勝率${personal.overall_rate}% / <strong class="${personal.total_yen >= 0 ? 'pos' : 'neg'}">${personal.total_yen >= 0 ? '+' : ''}${personal.total_yen.toLocaleString()}円</strong></div>`;
    html += '</div>';
  } else {
    html += '<div class="detail-section"><div class="detail-row" style="color:var(--muted)">🎯 個人実績: この機種の記録が3戦未満</div></div>';
  }
  
  if (!html) html = '<div class="detail-row" style="color:var(--muted)">情報がまだ収集できていません</div>';
  el.innerHTML = html;
}

function 情報展開(id) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.style.display === 'none') {
    el.style.display = 'block';
    // rank/machineName は dataset から取得 or 別途保持
    const rank = id.replace('detail-', '');
    const machineName = el.dataset.machine;
    if (machineName) 鉄板詳細描画(rank, machineName);
  } else {
    el.style.display = 'none';
  }
}
```

`鉄板3台描画` で各カード生成時に `el.dataset.machine = m.name;` を info-detail に設定するため、HTMLを以下に修正:
```html
<button class="info-toggle" onclick="情報展開('detail-${rank}')">💡 もっと詳しく</button>
<div class="info-detail" id="detail-${rank}" data-machine="${safe(m.name)}" style="display:none"></div>
```

### Section E: CSS

```css
.info-toggle {
  width: 100%; margin-top: 10px; padding: 8px 12px;
  background: var(--bg3); color: var(--accent);
  border: 1px solid rgba(255,107,0,0.3); border-radius: 8px;
  font-weight: 700; font-size: 11px; cursor: pointer;
  text-transform: uppercase; letter-spacing: 0.5px;
  transition: all 0.15s;
  font-family: inherit;
}
.info-toggle:hover { background: rgba(255,107,0,0.10); }
.info-detail {
  margin-top: 8px; padding: 10px;
  background: rgba(0,0,0,0.25); border-radius: 8px;
  border-left: 3px solid var(--accent);
}
.detail-section { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.detail-section:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.detail-section-title {
  font-size: 11px; font-weight: 900; color: var(--accent);
  letter-spacing: 1px; margin-bottom: 6px; text-transform: uppercase;
}
.detail-row { padding: 3px 0; font-size: 12px; color: var(--text2); line-height: 1.5; }
.detail-row strong { color: var(--text); font-family: var(--font-mono); }
.detail-row strong.pos { color: var(--accent2); }
.detail-row strong.neg { color: var(--danger); }
```

### Section F: sw.js
CACHE_NAME を `v30-info-density` に bump

## 受け入れ基準

- [ ] `MACHINE_SPEC_DB` の主要20機種に `uchikata/yamedoki/settei_diff/reset_target` 追加
- [ ] `機種攻略情報取得`, `今日の店舗傾向`, `個人勝ちパターン`, `鉄板詳細描画`, `情報展開` 関数定義
- [ ] 鉄板3台カードに「💡 もっと詳しく」ボタン (各カードに1個、計3個)
- [ ] 展開時にA/B/Cの3セクション表示
- [ ] データ無しのフォールバック表示
- [ ] sw.js v30-info-density
- [ ] 既存機能(鉄板3台/来店モード/年間トラッカー/クイック記録/バックアップ)破壊なし

## リスク

| リスク | 緩和 |
|---|---|
| 機種攻略情報がWebSearchで集めきれない | 著名な5-10機種だけ満タン、他は空欄でフォールバック |
| 個人パターンが薄いn数で誤判定 | n>=3戦の条件、曜日別はn>=2戦の条件 |
| 折りたたみ展開で読み込み遅延 | クリック時のみfetch、結果はDOMに残る |
| MACHINE_SPEC_DB 文字数が大きくなる | JSON-likeで圧縮、コメントなし |

## 情報収集ソース (実装時にWebSearchで取得)

- 1geki.jp (一撃)
- pachi7.com
- すろぱちくえすと
- 解析サイト各種
- 取得時の引用は1行程度・出典URL付き

## Self-review
- [x] プレースホルダーなし
- [x] 各セクション関数定義完備
- [x] フォールバック表示あり
- [x] 既存機能影響明示
