# Cycle#25-#26 設計仕様: バックアップ復元 + 来店振り返り

**作成日**: 2026-05-26  
**CEO承認**: A+B 両方を連続2サイクルで

## 背景・目的

24サイクル分のデータが localStorage に蓄積されたが、デバイス変更やキャッシュクリアで全消失する不安が残る。また LIVE 終了時の即時フィードバックが弱いため学習サイクルが遅い。これらを解消する。

## スコープ

| Cycle | 機能 | 種別 |
|---|---|---|
| #25 | データバックアップ/復元 (JSON export/import) | 品質 |
| #26 | 来店終了時の振り返りモーダル | UX |

---

## Cycle#25: データバックアップ/復元

### 配置
設定タブ末尾に「💾 データバックアップ」カードを新設。

### データ対象（localStorage 全キー）
- `records` (最重要)
- `annual_target` (年間目標設定)
- `monthly_loss_limit` (月予算)
- `calendar_marks` (カレンダー予定)
- `urge_log` (衝動チェックログ)
- `ai_picks_log` (AI推奨履歴)
- `default_hall`, `telemetry`, `harness_kpi`, `last_backup_at`

### UI

```html
<div class="カード">
  <div class="カードタイトル">▶ 💾 データバックアップ</div>
  <div id="backup-status" class="backup-status">最終バックアップ: --</div>
  <div class="backup-actions">
    <button class="ボタン主" onclick="データエクスポート()">📥 JSONで保存</button>
    <input id="backup-file-input" type="file" accept=".json" style="display:none" onchange="データインポート(event, false)">
    <input id="backup-file-merge" type="file" accept=".json" style="display:none" onchange="データインポート(event, true)">
    <button class="ボタン副" onclick="document.getElementById('backup-file-input').click()">📤 上書きインポート</button>
    <button class="ボタン副" onclick="document.getElementById('backup-file-merge').click()">📤 マージインポート(記録のみ)</button>
  </div>
  <div class="backup-note">バックアップは記録・年間目標・カレンダー・衝動ログ・AI推奨ログ等localStorage全データを含みます。</div>
</div>
```

### JS

```js
const BACKUP_KEYS = ['records','annual_target','monthly_loss_limit','calendar_marks','urge_log','ai_picks_log','default_hall','telemetry','harness_kpi','live_session'];

function データエクスポート() {
  const data = { _meta: { exported_at: new Date().toISOString(), version: 1, app: 'slot-dashboard-pwa' }};
  BACKUP_KEYS.forEach(k => { 
    const v = localStorage.getItem(k); 
    if (v != null) data[k] = v; 
  });
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const today = new Date().toISOString().slice(0,10);
  a.href = url;
  a.download = `slot-pwa-backup-${today}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  localStorage.setItem('last_backup_at', new Date().toISOString());
  バックアップ状態表示();
  if (typeof 通知表示 === 'function') 通知表示('✅ バックアップを保存しました');
}

function データインポート(event, mergeMode) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = JSON.parse(e.target.result);
      if (!data._meta || data._meta.app !== 'slot-dashboard-pwa') {
        if (!confirm('このファイルは本アプリのバックアップではない可能性があります。続行しますか？')) return;
      }
      if (mergeMode) {
        // マージ: records のみマージ、他のキーはスキップ
        const existing = JSON.parse(localStorage.getItem('records') || '[]');
        const incoming = JSON.parse(data.records || '[]');
        const seen = new Set(existing.map(r => `${r.date}|${r['機種']}|${r['差枚']}`));
        const merged = [...existing];
        incoming.forEach(r => {
          const k = `${r.date}|${r['機種']}|${r['差枚']}`;
          if (!seen.has(k)) { merged.push(r); seen.add(k); }
        });
        localStorage.setItem('records', JSON.stringify(merged));
        alert(`マージ完了: ${incoming.length}件 → 重複除去後 ${merged.length}件`);
      } else {
        if (!confirm(`現在のデータを完全に上書きします。よろしいですか？\n(エクスポート日時: ${data._meta?.exported_at || '不明'})`)) return;
        BACKUP_KEYS.forEach(k => {
          if (data[k] != null) localStorage.setItem(k, data[k]);
          else localStorage.removeItem(k);
        });
        alert('復元完了。ページを再読込します。');
        location.reload();
      }
    } catch(err) {
      alert('インポート失敗: ' + err.message);
    }
  };
  reader.readAsText(file);
  event.target.value = '';  // リセット
}

function バックアップ状態表示() {
  const el = document.getElementById('backup-status');
  if (!el) return;
  const ts = localStorage.getItem('last_backup_at');
  if (!ts) { el.innerHTML = '⚠️ 最終バックアップ: <strong>未実施</strong>'; el.className = 'backup-status warn'; return; }
  const days = Math.floor((Date.now() - new Date(ts).getTime()) / 86400000);
  let cls = 'backup-status ok', icon = '✅';
  if (days >= 14) { cls = 'backup-status warn'; icon = '⚠️'; }
  if (days >= 30) { cls = 'backup-status bad'; icon = '🚨'; }
  el.className = cls;
  el.innerHTML = `${icon} 最終バックアップ: <strong>${days === 0 ? '今日' : days + '日前'}</strong>`;
}
```

`renderSettings` の最後で `バックアップ状態表示()` を呼ぶ。

### CSS

```css
.backup-status { padding: 10px 12px; border-radius: 8px; background: var(--bg3); font-size: 12px; margin-bottom: 10px; }
.backup-status.ok { color: #22d3a3; }
.backup-status.warn { color: #ffb547; }
.backup-status.bad { color: #ff4d6d; }
.backup-actions { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 10px; }
@media (min-width: 480px) { .backup-actions { grid-template-columns: 1fr 1fr 1fr; } }
.backup-note { font-size: 11px; color: var(--muted); padding: 8px; background: var(--bg3); border-radius: 6px; }
```

### sw.js
CACHE_NAME を `v27-backup` に bump

---

## Cycle#26: 来店終了振り返りモーダル

### トリガー
既存 `来店モード終了()` 内で記録 push 後、`location.reload()` の代わりに振り返りモーダル表示。

### 内容
- 当日成績ヒーロー（差枚 + 円換算 + 投資差引）
- 滞在時間
- 撤退理由 + 賞賛/アドバイス1行
- 今月累計（既存年間目標から流用）
- 年間目標まで残額
- 「OK」で閉じる→renderHome

### JS

```js
function 来店振り返りモーダル(rec) {
  const conf = (typeof 年間目標取得 === 'function') ? 年間目標取得() : { target_yen: 1000000, rate_yen_per_piece: 20 };
  const sa = parseInt(rec['差枚']) || 0;
  const yen = sa * conf.rate_yen_per_piece;
  const invest = rec['投資'] || 0;
  const net = yen - invest;
  
  const startTime = rec['開始'] ? new Date(rec['開始']).getTime() : null;
  const endTime = rec['終了'] ? new Date(rec['終了']).getTime() : Date.now();
  const minutes = startTime ? Math.floor((endTime - startTime) / 60000) : null;
  
  // 月次累計
  const records = JSON.parse(localStorage.getItem('records') || '[]');
  const ym = new Date().toISOString().slice(0,7);
  const monthRecs = records.filter(r => (r.date||'').startsWith(ym));
  const monthSa = monthRecs.reduce((s,r) => s + (parseInt(r['差枚']) || 0), 0);
  const monthYen = monthSa * conf.rate_yen_per_piece;
  
  // 年間目標残
  const year = new Date().getFullYear();
  const yearRecs = records.filter(r => (r.date||'').startsWith(year + ''));
  const yearYen = yearRecs.reduce((s,r) => s + (parseInt(r['差枚']) || 0) * conf.rate_yen_per_piece, 0);
  const remain = conf.target_yen - yearYen;
  
  // アドバイス
  let praise = '';
  const reason = rec['撤退理由'];
  if (reason === '勝ち逃げ' && net > 0) praise = '🏆 完璧な勝ち逃げ！規律が育っています。';
  else if (reason === '損切り') praise = '🛡️ 損切り達成。次の機会へ。';
  else if (net > 0) praise = '✨ プラス収支。次も継続を。';
  else if (net < -3000) praise = '💡 機種選定を再考。鉄板3台優先で。';
  else praise = '📊 記録継続が勝利への第一歩。';
  
  const overlay = document.createElement('div');
  overlay.className = 'recap-modal';
  overlay.innerHTML = `
    <div class="recap-inner">
      <div class="recap-header">
        <div class="recap-title">🏁 来店終了 振り返り</div>
        <button class="recap-close-x" onclick="this.closest('.recap-modal').remove(); if(typeof renderHome==='function')renderHome();">✕</button>
      </div>
      <div class="recap-body">
        <div class="recap-hero ${net >= 0 ? 'positive' : 'negative'}">
          <div class="recap-hero-label">今回の収支</div>
          <div class="recap-hero-num">${net >= 0 ? '+' : ''}${net.toLocaleString()}円</div>
          <div class="recap-hero-sub">差枚 ${sa >= 0 ? '+' : ''}${sa.toLocaleString()} / 投資 ¥${invest.toLocaleString()}${minutes != null ? ' / 滞在 ' + minutes + '分' : ''}</div>
        </div>
        <div class="recap-praise">${praise}</div>
        <div class="recap-grid">
          <div class="recap-stat">
            <div class="recap-stat-label">今月累計</div>
            <div class="recap-stat-val ${monthYen >= 0 ? 'pos' : 'neg'}">${monthYen >= 0 ? '+' : ''}${monthYen.toLocaleString()}円</div>
          </div>
          <div class="recap-stat">
            <div class="recap-stat-label">年間目標まで</div>
            <div class="recap-stat-val">${remain.toLocaleString()}円</div>
          </div>
        </div>
      </div>
      <div class="recap-footer">
        <button class="recap-ok" onclick="this.closest('.recap-modal').remove(); if(typeof renderHome==='function')renderHome();">OK</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}
```

### 既存 `来店モード終了` の修正
最後の `location.reload()` 行 (or renderHome 行) を **削除** し、代わりに `来店振り返りモーダル(rec)` を呼ぶ。モーダルOKで renderHome が呼ばれる。

### CSS (月次レポートmodal流用 + 一部追加)

```css
.recap-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-y: auto; }
.recap-inner { background: var(--bg2); border: 2px solid var(--cyan); border-radius: 16px; padding: 0; max-width: 460px; width: 100%; box-shadow: 0 0 60px rgba(124,92,255,0.4); }
.recap-header { padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.recap-title { font-family: var(--font-display); font-weight: 900; font-size: 16px; }
.recap-close-x { background: transparent; border: none; color: var(--muted); font-size: 18px; cursor: pointer; }
.recap-body { padding: 16px 18px; }
.recap-hero { padding: 20px; text-align: center; border-radius: 12px; margin-bottom: 14px; }
.recap-hero.positive { background: linear-gradient(135deg, rgba(34,211,163,0.15), var(--bg3)); border: 1px solid rgba(34,211,163,0.3); }
.recap-hero.negative { background: linear-gradient(135deg, rgba(255,77,109,0.15), var(--bg3)); border: 1px solid rgba(255,77,109,0.3); }
.recap-hero-label { font-size: 11px; color: var(--muted); letter-spacing: 2px; }
.recap-hero-num { font-family: var(--font-mono); font-size: 36px; font-weight: 900; margin: 6px 0; }
.recap-hero.positive .recap-hero-num { color: #22d3a3; }
.recap-hero.negative .recap-hero-num { color: #ff4d6d; }
.recap-hero-sub { font-size: 11px; color: var(--text2); }
.recap-praise { padding: 12px; background: linear-gradient(135deg, rgba(124,92,255,0.08), var(--bg3)); border-radius: 10px; font-size: 13px; color: var(--text); text-align: center; margin-bottom: 12px; border: 1px solid rgba(124,92,255,0.2); }
.recap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.recap-stat { padding: 12px; background: var(--bg3); border-radius: 10px; text-align: center; }
.recap-stat-label { font-size: 10px; color: var(--muted); letter-spacing: 1px; }
.recap-stat-val { font-family: var(--font-mono); font-size: 16px; font-weight: 800; margin-top: 4px; }
.recap-stat-val.pos { color: #22d3a3; }
.recap-stat-val.neg { color: #ff4d6d; }
.recap-footer { padding: 12px 18px; border-top: 1px solid var(--border); }
.recap-ok { width: 100%; padding: 14px; background: linear-gradient(135deg, var(--cyan), #22d3a3); color: #fff; border: none; border-radius: 10px; font-weight: 900; cursor: pointer; }
```

### sw.js
CACHE_NAME を `v28-recap` に bump

---

## 受け入れ基準

### Cycle#25
- [ ] 設定タブに「💾 データバックアップ」カード
- [ ] エクスポートで JSON ダウンロード
- [ ] 上書きインポートで全データ復元
- [ ] マージインポートで records のみ重複除去マージ
- [ ] 最終バックアップ表示（0日/N日前、14日超で警告、30日超で赤）
- [ ] sw.js v27-backup

### Cycle#26
- [ ] LIVE終了時に振り返りモーダル
- [ ] 当日収支ヒーロー（緑/赤）
- [ ] アドバイス文（撤退理由・収支から自動生成）
- [ ] 今月累計 + 年間目標残
- [ ] OK or ✕ で閉じて renderHome
- [ ] sw.js v28-recap

### 共通
- [ ] 既存機能(鉄板3台/年間トラッカー/来店モード/クイック記録/月次レポート/カレンダー/収支グラフ/Forward Test/衝動チェック) 破壊なし

## リスク

| リスク | 緩和 |
|---|---|
| 大量データのJSON Blobで遅延 | 通常想定数千件レコードなら問題なし。Blob.size 警告は不要 |
| 不正なJSON取込でlocalStorage破壊 | try/catch + meta検証 + confirm |
| 重複判定が緩い | date+機種+差枚の3キー組合せ。同日同機種同差枚は実質ありえないので妥当 |
| recap-modal とその他modal重複 | z-index 10000で揃え、来店終了は他modal閉じてから |

## Self-review
- [x] プレースホルダーなし
- [x] 全エクスポートキー一覧明示
- [x] エラー処理あり
- [x] 既存機能影響明示
