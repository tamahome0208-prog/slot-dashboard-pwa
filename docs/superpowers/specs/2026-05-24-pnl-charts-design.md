# Cycle#22 設計仕様: 収支グラフ可視化

**作成日**: 2026-05-24  
**CEO承認**: 案A (3グラフ + ホームスパークライン)、spec→実装即進行

## 背景・目的

21サイクル完了時点で「鉄板3台」「年間トラッカー(円形プログレス)」「月予算プログレス」など数値ベースの可視化はあるが、**時系列推移**と**機種別の収支シェア**が見えない。年間100万円達成への進捗実感とリーク発見のためチャート可視化を導入。

## スコープ

新規UI:
1. **ツールタブ**に「📈 収支グラフ」セクション（3タブ切替: 月別 / 機種別 / 週次勝率）
2. **ホーム**の年間トラッカー直下にミニスパークライン（直近30日）

依存: 既存 Chart.js (CDN: cdn.jsdelivr) を活用、追加ライブラリなし。

## 設計

### 1. ツールタブ収支グラフセクション

#### HTML（ツールタブ末尾に追加）
```html
<div class="カード">
  <div class="カードタイトル">▶ 📈 収支グラフ</div>
  <div class="pnl-tabs">
    <button class="pnl-tab active" data-tab="monthly" onclick="収支グラフタブ切替('monthly', this)">月別推移</button>
    <button class="pnl-tab" data-tab="machine" onclick="収支グラフタブ切替('machine', this)">機種別</button>
    <button class="pnl-tab" data-tab="weekly" onclick="収支グラフタブ切替('weekly', this)">週次勝率</button>
  </div>
  <div class="pnl-canvas-wrap">
    <canvas id="pnl-chart" style="max-height:300px"></canvas>
  </div>
  <div id="pnl-summary" class="pnl-summary"></div>
</div>
```

#### JS state とロジック
```js
let _pnl_chart_instance = null;
let _pnl_current_tab = 'monthly';

function 収支グラフ_月別データ() {
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { rate_yen_per_piece: 20 };
  const year = new Date().getFullYear();
  const monthlySa = Array(12).fill(0);
  records.forEach(r => {
    const d = (r.date||'').split('-');
    if (parseInt(d[0]) !== year) return;
    const m = parseInt(d[1]) - 1;
    if (m >= 0 && m < 12) monthlySa[m] += (parseInt(r.差枚) || 0);
  });
  const monthlyYen = monthlySa.map(sa => sa * conf.rate_yen_per_piece);
  const cumulative = [];
  let acc = 0;
  monthlyYen.forEach(v => { acc += v; cumulative.push(acc); });
  return { labels: [...Array(12)].map((_,i) => (i+1)+'月'), monthlyYen, cumulative };
}

function 収支グラフ_機種別データ(days = 90) {
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { rate_yen_per_piece: 20 };
  const since = Date.now() - days*86400000;
  const recent = records.filter(r => new Date(r.date).getTime() >= since);
  const byMachine = {};
  recent.forEach(r => {
    const n = r['機種'] || '未指定';
    byMachine[n] = (byMachine[n] || 0) + (parseInt(r.差枚) || 0) * conf.rate_yen_per_piece;
  });
  const sorted = Object.entries(byMachine).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1]));
  const top = sorted.slice(0, 8);
  const others = sorted.slice(8);
  if (others.length) {
    const otherSum = others.reduce((s, [_,v]) => s + v, 0);
    top.push(['その他', otherSum]);
  }
  return {
    labels: top.map(([n]) => n.slice(0,12)),
    values: top.map(([_,v]) => v),
  };
}

function 収支グラフ_週次勝率データ(weeks = 12) {
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const labels = [], rates = [];
  for (let w = weeks - 1; w >= 0; w--) {
    const end = Date.now() - w * 7 * 86400000;
    const start = end - 7 * 86400000;
    const inWeek = records.filter(r => {
      const t = new Date(r.date).getTime();
      return t >= start && t < end;
    });
    const wins = inWeek.filter(r => (parseInt(r.差枚) || 0) > 0).length;
    const total = inWeek.length;
    const rate = total ? Math.round(wins / total * 100) : null;
    const endDate = new Date(end);
    labels.push(`${endDate.getMonth()+1}/${endDate.getDate()}`);
    rates.push(rate);
  }
  return { labels, rates };
}

function 収支グラフ描画(tab) {
  const ctx = document.getElementById('pnl-chart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (_pnl_chart_instance) { _pnl_chart_instance.destroy(); _pnl_chart_instance = null; }
  
  const summary = document.getElementById('pnl-summary');
  
  if (tab === 'monthly') {
    const d = 収支グラフ_月別データ();
    const total = d.cumulative[d.cumulative.length-1] || 0;
    _pnl_chart_instance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [
          { label: '月別収支', data: d.monthlyYen, backgroundColor: d.monthlyYen.map(v => v>=0 ? 'rgba(34,211,163,0.6)' : 'rgba(255,77,109,0.6)'), borderColor: d.monthlyYen.map(v => v>=0 ? '#22d3a3' : '#ff4d6d'), borderWidth: 1, yAxisID: 'y' },
          { label: '累積収支', data: d.cumulative, type: 'line', borderColor: '#7c5cff', backgroundColor: 'rgba(124,92,255,0.1)', tension: 0.3, yAxisID: 'y', borderWidth: 2 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#c4c4cc', font: { family: 'JetBrains Mono' } } } },
        scales: {
          y: { ticks: { color: '#c4c4cc', font: { family: 'JetBrains Mono' }, callback: v => (v/1000)+'k' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { ticks: { color: '#c4c4cc' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
    summary.innerHTML = `<div class="pnl-sum-row"><span>年間累積</span><strong class="${total>=0?'pos':'neg'}">${total>=0?'+':''}${total.toLocaleString()}円</strong></div>`;
  } else if (tab === 'machine') {
    const d = 収支グラフ_機種別データ();
    if (d.labels.length === 0) {
      ctx.style.display = 'none';
      summary.innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted)">過去90日の記録がありません</div>';
      return;
    }
    ctx.style.display = '';
    const colors = d.values.map(v => v>=0 ? `rgba(34,211,163,${0.4 + Math.min(0.5, Math.abs(v)/100000)})` : `rgba(255,77,109,${0.4 + Math.min(0.5, Math.abs(v)/100000)})`);
    _pnl_chart_instance = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: d.labels, datasets: [{ data: d.values.map(Math.abs), backgroundColor: colors, borderColor: '#0a0a0f', borderWidth: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: '#c4c4cc', font: { size: 10 }, generateLabels: (chart) => chart.data.labels.map((label, i) => ({
            text: label + ': ' + (d.values[i]>=0?'+':'') + Math.round(d.values[i]).toLocaleString() + '円',
            fillStyle: chart.data.datasets[0].backgroundColor[i],
            strokeStyle: chart.data.datasets[0].borderColor,
            lineWidth: 1, index: i
          })) } }
        }
      }
    });
    summary.innerHTML = `<div class="pnl-sum-row"><span>過去90日</span><strong>${d.labels.length}機種</strong></div>`;
  } else if (tab === 'weekly') {
    const d = 収支グラフ_週次勝率データ();
    const validRates = d.rates.filter(r => r !== null);
    const avg = validRates.length ? Math.round(validRates.reduce((s,v)=>s+v,0)/validRates.length) : 0;
    _pnl_chart_instance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [{ label: '勝率%', data: d.rates, backgroundColor: d.rates.map(r => r === null ? 'rgba(107,114,128,0.3)' : r>=50 ? 'rgba(34,211,163,0.6)' : 'rgba(255,77,109,0.6)'), borderColor: d.rates.map(r => r === null ? '#6b7280' : r>=50 ? '#22d3a3' : '#ff4d6d'), borderWidth: 1 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#c4c4cc' } },
          annotation: { annotations: { avgline: { type: 'line', yMin: avg, yMax: avg, borderColor: '#7c5cff', borderWidth: 2, borderDash: [4,4], label: { display: true, content: `平均${avg}%`, color: '#7c5cff', position: 'end' } } } }
        },
        scales: {
          y: { min: 0, max: 100, ticks: { color: '#c4c4cc', callback: v => v+'%' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { ticks: { color: '#c4c4cc' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
    summary.innerHTML = `<div class="pnl-sum-row"><span>過去12週平均勝率</span><strong class="${avg>=50?'pos':'neg'}">${avg}%</strong></div>`;
  }
}

function 収支グラフタブ切替(tab, btn) {
  _pnl_current_tab = tab;
  document.querySelectorAll('.pnl-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  収支グラフ描画(tab);
}
```

#### renderTools連動
`renderTools` 内で初期描画 `収支グラフ描画(_pnl_current_tab)` を呼ぶ。

### 2. ホームスパークライン

#### HTML（年間トラッカーカードの annual-monthly の下）
```html
<div class="annual-sparkline-wrap">
  <div class="annual-sparkline-label">直近30日推移</div>
  <canvas id="annual-sparkline" style="max-height:50px"></canvas>
</div>
```

#### JS
```js
function 年間スパークライン描画() {
  const ctx = document.getElementById('annual-sparkline');
  if (!ctx || typeof Chart === 'undefined') return;
  if (window._spark_instance) { window._spark_instance.destroy(); window._spark_instance = null; }
  
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { rate_yen_per_piece: 20 };
  const since = Date.now() - 30*86400000;
  const recent = records.filter(r => new Date(r.date).getTime() >= since);
  
  // 日付ごとの収支を累積
  const labels = [], values = [];
  let acc = 0;
  for (let i = 29; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000).toISOString().slice(0,10);
    const dayRecs = recent.filter(r => r.date === d);
    const daySa = dayRecs.reduce((s,r) => s + (parseInt(r.差枚) || 0), 0);
    acc += daySa * conf.rate_yen_per_piece;
    labels.push(d.slice(5));
    values.push(acc);
  }
  
  window._spark_instance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ data: values, borderColor: '#7c5cff', backgroundColor: 'rgba(124,92,255,0.15)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 1.5 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true, callbacks: { label: c => '¥' + c.parsed.y.toLocaleString() } } },
      scales: { x: { display: false }, y: { display: false } }
    }
  });
}
```

`年間トラッカー描画()` の末尾で `年間スパークライン描画()` を呼ぶ。

### 3. CSS

```css
.pnl-tabs { display: flex; gap: 6px; margin-bottom: 12px; }
.pnl-tab { flex: 1; padding: 8px 4px; background: var(--bg3); border: 1px solid var(--border); color: var(--muted); border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.15s; }
.pnl-tab.active { background: rgba(124,92,255,0.15); border-color: var(--cyan); color: var(--cyan); }
.pnl-canvas-wrap { height: 300px; position: relative; padding: 4px; }
.pnl-summary { margin-top: 10px; padding: 10px 12px; background: var(--bg3); border-radius: 8px; }
.pnl-sum-row { display: flex; justify-content: space-between; font-size: 12px; }
.pnl-sum-row strong { font-family: var(--font-mono); font-size: 14px; }
.pnl-sum-row strong.pos { color: #22d3a3; }
.pnl-sum-row strong.neg { color: #ff4d6d; }

.annual-sparkline-wrap { margin-top: 12px; padding: 8px; background: var(--bg3); border-radius: 8px; }
.annual-sparkline-label { font-size: 10px; color: var(--muted); letter-spacing: 1px; margin-bottom: 4px; }
```

### 4. sw.js
CACHE_NAME を `v24-pnl-charts` に bump

## 受け入れ基準

- [ ] ツールタブに「📈 収支グラフ」セクションが見える
- [ ] 3タブ切替(月別/機種別/週次勝率) 動作
- [ ] 月別: 棒+折れ線複合、累積表示
- [ ] 機種別: ドーナツ+凡例で金額付き
- [ ] 週次勝率: バー+平均線
- [ ] ホーム年間トラッカー内にスパークライン
- [ ] 記録ゼロ時にフォールバック表示
- [ ] 既存機能(衝動チェック/来店モード/月次レポート/カレンダー/クイック記録)破壊なし

## リスク

| リスク | 緩和策 |
|---|---|
| Chart.js重複描画でメモリリーク | 既存インスタンス destroy() 必須 |
| 記録ゼロでクラッシュ | データ長0チェック + フォールバック |
| Chart.js annotation plugin未ロード | 平均線は plugin なしで dataset 追加で代替（必要時） |

## Self-review

- [x] プレースホルダーなし
- [x] data flow 明示
- [x] エラー処理あり
- [x] 既存機能への影響明示
