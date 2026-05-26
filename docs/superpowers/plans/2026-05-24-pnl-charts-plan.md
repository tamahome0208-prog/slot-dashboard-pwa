# 収支グラフ可視化 Implementation Plan (Cycle#22)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ツールタブに3タブ収支グラフ(月別/機種別/週次勝率)、ホーム年間トラッカー内に直近30日スパークラインを実装し、進捗実感とリーク発見を可視化する。

**Architecture:** 単一HTML SPA (`index.html`) への CSS / HTML / JS 追加。既存ロード済み Chart.js (CDN) を活用。データは `localStorage.records` から算出。グラフ描画は表示時のみ、destroy/recreate でメモリリーク回避。

**Tech Stack:** Chart.js 4.4 (既存), localStorage, vanilla JS, single-file PWA

**仕様**: `docs/superpowers/specs/2026-05-24-pnl-charts-design.md`

---

## File Structure

- Modify: `index.html` 
  - CSS block: 約30行追加 (.pnl-tabs, .pnl-canvas-wrap, .pnl-summary, .annual-sparkline-wrap 等)
  - HTML: ツールタブカード末尾に「📈 収支グラフ」セクション(約20行)、年間トラッカー内にスパークラインwrap(5行)
  - JS: state変数2つ、データ算出関数3つ、描画関数1つ、タブ切替関数1つ、スパークライン関数1つ
  - renderTools / 年間トラッカー描画 末尾に呼出追加
- Modify: `sw.js` CACHE_NAME bump

---

## Task 1: 全実装を1コミットで完結（単一HTML+SW更新）

単一HTMLファイルへの追加なので、TDD的なテストファイル分離は不可能。代わりに**実装後の手動検証チェックリスト**で品質担保する。

**Files:**
- Modify: `C:\Users\tamah\slot-dashboard-pwa\index.html`
- Modify: `C:\Users\tamah\slot-dashboard-pwa\sw.js`

### Step 1: 最新化

- [ ] `cd /tmp/slot-dashboard-pwa && git pull --rebase` で最新を取得

### Step 2: CSS追加

index.html の既存 `<style>` ブロック末尾に以下を追加:

```css
/* ── 収支グラフ ── */
.pnl-tabs { display: flex; gap: 6px; margin-bottom: 12px; }
.pnl-tab { flex: 1; padding: 8px 4px; background: var(--bg3); border: 1px solid var(--border); color: var(--muted); border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.15s; }
.pnl-tab:hover { color: var(--text); }
.pnl-tab.active { background: rgba(124,92,255,0.15); border-color: var(--cyan); color: var(--cyan); }
.pnl-canvas-wrap { height: 300px; position: relative; padding: 4px; }
.pnl-summary { margin-top: 10px; padding: 10px 12px; background: var(--bg3); border-radius: 8px; }
.pnl-sum-row { display: flex; justify-content: space-between; font-size: 12px; }
.pnl-sum-row strong { font-family: var(--font-mono); font-size: 14px; }
.pnl-sum-row strong.pos { color: #22d3a3; }
.pnl-sum-row strong.neg { color: #ff4d6d; }

/* ── 年間スパークライン ── */
.annual-sparkline-wrap { margin-top: 12px; padding: 8px; background: var(--bg3); border-radius: 8px; }
.annual-sparkline-label { font-size: 10px; color: var(--muted); letter-spacing: 1px; margin-bottom: 4px; }
```

### Step 3: ツールタブ用HTML追加

`page-tools` ディビ内の既存カード群の末尾（最終要素として）以下を挿入:

```html
<div class="カード">
  <div class="カードタイトル">▶ 📈 収支グラフ</div>
  <div class="pnl-tabs">
    <button class="pnl-tab active" data-tab="monthly" onclick="収支グラフタブ切替('monthly', this)">月別推移</button>
    <button class="pnl-tab" data-tab="machine" onclick="収支グラフタブ切替('machine', this)">機種別</button>
    <button class="pnl-tab" data-tab="weekly" onclick="収支グラフタブ切替('weekly', this)">週次勝率</button>
  </div>
  <div class="pnl-canvas-wrap">
    <canvas id="pnl-chart"></canvas>
  </div>
  <div id="pnl-summary" class="pnl-summary"></div>
</div>
```

### Step 4: ホーム年間トラッカー内HTML追加

`#年間トラッカーエリア` 内の `#annual-monthly` の**直後**に挿入:

```html
<div class="annual-sparkline-wrap">
  <div class="annual-sparkline-label">直近30日推移</div>
  <canvas id="annual-sparkline" style="max-height:50px"></canvas>
</div>
```

### Step 5: JS state追加

既存スクリプト内、グローバル変数領域に追加:

```js
let _pnl_chart_instance = null;
let _pnl_current_tab = 'monthly';
```

### Step 6: データ算出関数3つ追加

```js
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

function 収支グラフ_機種別データ(days) {
  days = days || 90;
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
  return { labels: top.map(([n]) => String(n).slice(0,12)), values: top.map(([_,v]) => v) };
}

function 収支グラフ_週次勝率データ(weeks) {
  weeks = weeks || 12;
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
```

### Step 7: 描画関数 + タブ切替

```js
function 収支グラフ描画(tab) {
  const ctx = document.getElementById('pnl-chart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (_pnl_chart_instance) { _pnl_chart_instance.destroy(); _pnl_chart_instance = null; }
  const summary = document.getElementById('pnl-summary');

  if (tab === 'monthly') {
    const d = 収支グラフ_月別データ();
    const total = d.cumulative[d.cumulative.length - 1] || 0;
    _pnl_chart_instance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [
          { label: '月別', data: d.monthlyYen, backgroundColor: d.monthlyYen.map(v => v>=0 ? 'rgba(34,211,163,0.6)' : 'rgba(255,77,109,0.6)'), borderColor: d.monthlyYen.map(v => v>=0 ? '#22d3a3' : '#ff4d6d'), borderWidth: 1 },
          { label: '累積', data: d.cumulative, type: 'line', borderColor: '#7c5cff', backgroundColor: 'rgba(124,92,255,0.1)', tension: 0.3, borderWidth: 2, pointRadius: 3 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#c4c4cc' } } },
        scales: {
          y: { ticks: { color: '#c4c4cc', callback: v => (v/1000)+'k' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { ticks: { color: '#c4c4cc' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
    if (summary) summary.innerHTML = `<div class="pnl-sum-row"><span>年間累積</span><strong class="${total>=0?'pos':'neg'}">${total>=0?'+':''}${total.toLocaleString()}円</strong></div>`;
  } else if (tab === 'machine') {
    const d = 収支グラフ_機種別データ();
    if (!d.labels.length) {
      ctx.style.display = 'none';
      if (summary) summary.innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted)">過去90日の記録がありません</div>';
      return;
    }
    ctx.style.display = '';
    const colors = d.values.map(v => v>=0 ? `rgba(34,211,163,${0.45 + Math.min(0.5, Math.abs(v)/100000)})` : `rgba(255,77,109,${0.45 + Math.min(0.5, Math.abs(v)/100000)})`);
    _pnl_chart_instance = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: d.labels, datasets: [{ data: d.values.map(v => Math.abs(v) || 1), backgroundColor: colors, borderColor: '#0a0a0f', borderWidth: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#c4c4cc', font: { size: 10 }, generateLabels: (chart) => chart.data.labels.map((label, i) => ({
          text: label + ': ' + (d.values[i]>=0?'+':'') + Math.round(d.values[i]).toLocaleString() + '円',
          fillStyle: chart.data.datasets[0].backgroundColor[i],
          strokeStyle: chart.data.datasets[0].borderColor,
          lineWidth: 1, index: i
        })) } } }
      }
    });
    if (summary) summary.innerHTML = `<div class="pnl-sum-row"><span>過去90日</span><strong>${d.labels.length}機種</strong></div>`;
  } else if (tab === 'weekly') {
    const d = 収支グラフ_週次勝率データ();
    const valid = d.rates.filter(r => r !== null);
    const avg = valid.length ? Math.round(valid.reduce((s,v)=>s+v,0)/valid.length) : 0;
    _pnl_chart_instance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [
          { label: '勝率%', data: d.rates, backgroundColor: d.rates.map(r => r === null ? 'rgba(107,114,128,0.3)' : r>=50 ? 'rgba(34,211,163,0.6)' : 'rgba(255,77,109,0.6)'), borderColor: d.rates.map(r => r === null ? '#6b7280' : r>=50 ? '#22d3a3' : '#ff4d6d'), borderWidth: 1 },
          { label: `平均${avg}%`, data: Array(d.labels.length).fill(avg), type: 'line', borderColor: '#7c5cff', borderDash: [4,4], pointRadius: 0, borderWidth: 1.5, fill: false }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#c4c4cc' } } },
        scales: {
          y: { min: 0, max: 100, ticks: { color: '#c4c4cc', callback: v => v+'%' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { ticks: { color: '#c4c4cc' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
    if (summary) summary.innerHTML = `<div class="pnl-sum-row"><span>過去12週平均</span><strong class="${avg>=50?'pos':'neg'}">${avg}%</strong></div>`;
  }
}

function 収支グラフタブ切替(tab, btn) {
  _pnl_current_tab = tab;
  document.querySelectorAll('.pnl-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  収支グラフ描画(tab);
}
```

### Step 8: スパークライン関数

```js
function 年間スパークライン描画() {
  const ctx = document.getElementById('annual-sparkline');
  if (!ctx || typeof Chart === 'undefined') return;
  if (window._spark_instance) { window._spark_instance.destroy(); window._spark_instance = null; }
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { rate_yen_per_piece: 20 };
  const labels = [], values = [];
  let acc = 0;
  for (let i = 29; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    const dayRecs = records.filter(r => r.date === d);
    const daySa = dayRecs.reduce((s, r) => s + (parseInt(r.差枚) || 0), 0);
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

### Step 9: renderTools 連動

既存 `renderTools` 関数の末尾（return 直前 or 関数末尾）に:

```js
収支グラフ描画(_pnl_current_tab);
```

を追加。`renderTools` が無ければ、`showPage` 関数の `if (id === 'tools')` ブロックに追加。

### Step 10: 年間トラッカー描画フック

既存 `年間トラッカー描画` 関数の**末尾**に:

```js
年間スパークライン描画();
```

を追加。

### Step 11: sw.js bump

`sw.js` の `CACHE_NAME` を `'v24-pnl-charts'` に変更。

### Step 12: ローカル→クローン同期 + コミット

```bash
cp /c/Users/tamah/slot-dashboard-pwa/index.html /tmp/slot-dashboard-pwa/
cp /c/Users/tamah/slot-dashboard-pwa/sw.js /tmp/slot-dashboard-pwa/
cd /tmp/slot-dashboard-pwa
git add index.html sw.js
git commit -m "feat(cycle#22): 収支グラフ可視化(3タブ+スパークライン)

- ツールタブに月別/機種別/週次勝率の3タブグラフ
- ホーム年間トラッカー内に直近30日スパークライン
- Chart.js既存利用、destroy/recreate でメモリ管理
- 記録ゼロ時のフォールバック表示
- sw.js v24-pnl-charts"
git push
```

### Step 13: 手動検証チェックリスト

- [ ] ツールタブを開くと「📈 収支グラフ」セクションが表示
- [ ] 「月別推移」タブで棒+折れ線複合グラフ表示
- [ ] 「機種別」タブで Doughnut + 凡例表示
- [ ] 「週次勝率」タブで Bar + 平均線表示
- [ ] ホーム年間トラッカーの月別バーの下にスパークライン
- [ ] 記録ゼロ時にエラーなく「データ無し」表示
- [ ] 既存機能（衝動チェック・来店モード・カレンダー・月次レポート・クイック記録）の動作OK
- [ ] sw.js CACHE_NAME が `v24-pnl-charts`

---

## Self-Review

**Spec coverage:** spec の各受け入れ基準7項目に対し Task1 内のステップ全てがマッピング。

**Placeholder scan:** 「TBD」「TODO」「適切に」などの抽象表現なし。全てのコードブロック完備。

**Type consistency:** `_pnl_chart_instance` `_pnl_current_tab` `window._spark_instance` の3つのstateを使用、destroy パターン一貫、関数名は spec docと同一。

**完了。**

---

## Execution Handoff

Plan saved. CEO の fast cycle 方針に従い、**Subagent-Driven** で実装します。Task 1 全 13 ステップを 1 つの subagent に dispatch します。
