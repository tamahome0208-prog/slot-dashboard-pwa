# Claude API常駐化セットアップ手順（CEO向け）

完全自動ハーネスを動かすために、Anthropic APIキーが必要です。**アカウント作成と支払い設定はCEO自身で行ってください**（安全ルールにより代行不可）。

## 予算設計

| 項目 | 推定 |
|---|---|
| 1サイクルあたり | 約 $0.30 〜 $0.80（Claude Haiku使用） |
| 週1実行 | 月額 約 $1.20 〜 $3.20 |
| 上限ガード | スクリプト内で月$5まで（超過で自動停止） |

## セットアップ手順

### 1. Anthropic アカウント作成・APIキー発行
1. https://console.anthropic.com/ にアクセス
2. アカウント作成（新規なら $5 試用クレジット付与）
3. 支払い方法を登録（クレジットカード）
4. **重要: 「Usage limits」で月額上限を設定**（推奨: $5/月）
5. 「API Keys」→「Create Key」で新規キー発行
6. キー文字列（`sk-ant-...`）をコピー

### 2. GitHub Secrets 登録
1. https://github.com/tamahome0208-prog/slot-dashboard-pwa/settings/secrets/actions
2. 「New repository secret」をクリック
3. Name: `ANTHROPIC_API_KEY` / Value: 先ほどのキー
4. 「Add secret」で保存

### 3. 動作確認（任意）
1. リポジトリの Actions タブ
2. 「ハーネス週次サイクル(AI)」を選択
3. 「Run workflow」で手動実行
4. ログで「✅ サイクル完了」を確認

## 月次コスト確認

`harness/state/cost_ledger.json` に累積コストが記録されます。

## 緊急停止方法

- **即時停止**: GitHub Actions の Settings → Actions → 「Disable Actions」
- **API停止**: console.anthropic.com で API キーを「Revoke」

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 401 Unauthorized | APIキー失効。Secrets再登録 |
| 429 Rate Limit | Anthropic側の制限。1時間待機 |
| 月予算超過アラート | Anthropic Console で上限引き上げ or 待機 |
| GHA失敗継続 | Actions タブで詳細ログ確認 |
