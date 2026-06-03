# Cycle#29 設計仕様: 札幌5店舗データ収集+台番予想カード

**作成日**: 2026-05-29  
**CEO承認**: 札幌5店舗で進行  
**法令準拠**: 「過去データに基づく統計参考」明示、絶対表現禁止

## 背景

CEO要求「札幌周辺パチ屋データ収集+台番予想機能」に応えるため、min-repo.com 経由で台番別データ公開店5店舗を日次収集し、鉄板3台の下に「📍 札幌の注目台」カードを追加する。

## スコープ

### 対象5店舗
1. **プレイランドハッピー南6条店** (札幌市豊平区)
2. **プレイランドハッピー麻生店** (札幌市北区)
3. **KEIZ手稲店** (札幌市手稲区)
4. **ベガスベガス札幌店** (札幌市中央区)
5. **ひまわり札幌駅前タワー店** (札幌市中央区)

各店のmin-repo.com URLは Implementer が WebSearch で正確なIDを取得して使う。取得できない店舗は調査結果を spec で記録し、4店舗以上確保で進行可。

## 設計

### A: スクレイパー `scripts/sapporo_daily.py`

`royal_daily.py` のパターンを流用:
- 5店舗それぞれの最新ページから取得 (min-repo.com 経由)
- 各店舗の最新10日分を取得
- データ構造:
```json
{
  "store_name": "プレイランドハッピー南6条店",
  "store_id": "sapporo_hp_minami6",
  "history": [
    {
      "date": "2026-05-29",
      "machines": [
        { "name": "スマスロ北斗の拳", "unit": "128", "sa": 1200, "g": 4500, "shutsu_ritsu": 105.3 }
      ]
    }
  ]
}
```

保存先: `data/sapporo_history.json` (1ファイルに5店舗集約)

エチケット:
- アクセス間隔: 2秒以上
- User-Agent: 既存 `Mozilla/5.0` 維持
- 1日1回(GHA cron)のみ実行
- 失敗時は continue-on-error せずエラー報告

### B: GHA連携 `.github/workflows/scrape.yml`

既存に1ステップ追加:
```yaml
- name: 札幌データ収集
  run: python scripts/sapporo_daily.py
```
既存の commit ブロックの `git add data/` でカバーされる。

### C: PWA UI 「📍 札幌の注目台」カード

**配置**: ホーム画面、鉄板3台エリアの**直下**

```html
<div id="札幌注目台エリア" class="card">
  <div class="section-title">📍 札幌の注目台 (直近5日)</div>
  <div id="札幌注目台リスト">分析中...</div>
  <div class="sapporo-disclaimer">過去データの統計値です。未来を保証するものではありません。</div>
</div>
```

**描画関数** `札幌注目台描画()` (async):
```js
async function 札幌注目台描画() {
  const el = document.getElementById('札幌注目台リスト');
  if (!el) return;
  try {
    const r = await fetch('data/sapporo_history.json', {cache:'no-store'});
    const data = await r.json();
    
    const stores = data.stores || [];
    if (!stores.length) {
      el.innerHTML = '<div class="empty-msg">データ収集中(初回データ取得待ち)</div>';
      return;
    }
    
    // 各店舗で直近5日の台番別avg差枚 を計算、Top3を取る
    const safe = s => String(s||'').replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
    
    let html = '';
    stores.forEach(store => {
      const recent5 = (store.history || []).slice(0, 5);
      const unitStats = {}; // unit -> { sum, days, name }
      recent5.forEach(day => {
        (day.machines || []).forEach(m => {
          const key = m.unit + '|' + m.name;
          if (!unitStats[key]) unitStats[key] = { unit: m.unit, name: m.name, sum: 0, days: 0 };
          unitStats[key].sum += (m.sa || 0);
          unitStats[key].days += 1;
        });
      });
      const top3 = Object.values(unitStats)
        .filter(u => u.days >= 2 && u.sum > 0)
        .map(u => ({ ...u, avg: Math.round(u.sum / u.days) }))
        .sort((a,b) => b.avg - a.avg)
        .slice(0, 3);
      
      if (!top3.length) return;
      
      html += `<div class="sapporo-store">
        <div class="sapporo-store-name">${safe(store.store_name)}</div>`;
      const medals = ['🥇','🥈','🥉'];
      top3.forEach((u, i) => {
        html += `<div class="sapporo-row">
          <span class="sapporo-medal">${medals[i]}</span>
          <span class="sapporo-unit">#${safe(u.unit)}</span>
          <span class="sapporo-machine">${safe(u.name).slice(0,16)}</span>
          <span class="sapporo-avg">+${u.avg.toLocaleString()}枚/${u.days}日</span>
        </div>`;
      });
      html += '</div>';
    });
    
    el.innerHTML = html || '<div class="empty-msg">直近5日でプラスの台がありません</div>';
  } catch(e) {
    el.innerHTML = '<div class="empty-msg">データ取得失敗</div>';
    console.warn('札幌注目台描画失敗', e);
  }
}
```

`renderHome` で `鉄板3台描画()` の直後に `札幌注目台描画()` を呼ぶ。

### D: CSS

```css
#札幌注目台エリア { margin-bottom: 16px; }
.sapporo-store { background: var(--bg3); border-radius: 8px; padding: 12px; margin-bottom: 8px; border-left: 3px solid var(--accent); }
.sapporo-store-name { font-size: 12px; font-weight: 900; color: var(--accent); margin-bottom: 8px; letter-spacing: 0.5px; }
.sapporo-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
.sapporo-medal { font-size: 16px; width: 22px; }
.sapporo-unit { font-family: var(--font-mono); font-weight: 700; color: var(--gold); min-width: 50px; }
.sapporo-machine { flex: 1; color: var(--text); }
.sapporo-avg { color: var(--accent2); font-family: var(--font-mono); font-weight: 700; }
.sapporo-disclaimer { font-size: 10px; color: var(--muted); padding: 8px; text-align: center; margin-top: 6px; line-height: 1.4; }
.empty-msg { padding: 16px; color: var(--muted); text-align: center; font-size: 12px; }
```

### E: sw.js
CACHE_NAME を `v31-sapporo` に bump

## 受け入れ基準

- [ ] `scripts/sapporo_daily.py` 実装、最低4店舗のデータ取得成功
- [ ] `data/sapporo_history.json` 生成
- [ ] `.github/workflows/scrape.yml` に sapporo ステップ追加
- [ ] PWA に「📍 札幌の注目台」カード表示 (鉄板3台直下)
- [ ] 各店舗の台番×機種×平均差枚 Top3表示
- [ ] 「未来を保証しない」ディスクレーマー表示
- [ ] sw.js v31-sapporo
- [ ] 既存機能(鉄板3台/来店モード/年間トラッカー/クイック記録/バックアップ)破壊なし

## 法令準拠
- 「予想」「絶対」「必勝」表現は使用しない
- 「過去5日の統計値」「未来を保証するものではありません」明示
- スクレイピングは2秒以上の間隔
- robots.txt 遵守 (min-repo.com 検証済)
- 引用ソースは集計加工後

## リスク

| リスク | 緩和 |
|---|---|
| min-repo.com 各店URL ID 不明 | Implementer が WebSearch で確認、不明店は除外し残りで実装 |
| 初回データ取得タイミングで空表示 | 「データ収集中」フォールバック表示 |
| サイト構造変更でパース失敗 | try/catch + 失敗時 console.warn でアプリは落ちない |
| 「予想」表現で景表法リスク | ディスクレーマー必須、表現は「直近平均」など中立的に |
| GHA scrape時間増加 | 1店舗あたり10-15秒×5店舗 = 約1-1.5分追加、許容範囲 |

## Self-review
- [x] プレースホルダー無し
- [x] 各セクション関数定義完備
- [x] 法令配慮明示
- [x] フォールバックあり
- [x] 既存影響明示
