# 🎰 スロット管理システム セットアップガイド

## 📁 フォルダ構成

```
slot-dashboard-pwa/
├── index.html              ← メインアプリ
├── manifest.json           ← PWA設定
├── sw.js                   ← オフライン対応
├── icon-192.svg            ← アプリアイコン
├── README.txt              ← 基本手順
├── SETUP.md                ← このファイル
├── .github/
│   └── workflows/
│       └── scrape.yml      ← 毎日自動実行設定
├── scripts/
│   └── scrape.py           ← データ収集スクリプト
└── data/
    └── halls.json          ← 自動更新される台データ（初回実行後）
```

---

## 🚀 セットアップ手順（30分）

### ステップ1: GitHubアカウント作成（5分）

1. https://github.com にアクセス
2. 「Sign up」から無料アカウントを作成
3. メール認証を完了

### ステップ2: リポジトリ作成（3分）

1. GitHubログイン後、右上「+」→「New repository」
2. Repository name: `slot-dashboard-pwa`（任意）
3. **Public** を選択（PrivateでもOKだが、Publicの方が後の手順が簡単）
4. 「Create repository」をクリック

### ステップ3: ファイルアップロード（5分）

1. 作成されたリポジトリ画面で「uploading an existing file」をクリック
2. **このフォルダ（slot-dashboard-pwa）の中身を全部ドラッグ＆ドロップ**
   - `index.html`, `manifest.json`, `sw.js`, `icon-192.svg`
   - `.github` フォルダごと
   - `scripts` フォルダごと
3. 下にスクロールして「Commit changes」をクリック

### ステップ4: GitHub Actions を有効化（2分）

1. リポジトリ上部の「Actions」タブを開く
2. 「I understand my workflows, go ahead and enable them」をクリック
3. 「台データ自動収集」というワークフローが表示される
4. クリックして「Run workflow」→「Run workflow」（緑ボタン）で初回実行
5. **2〜3分待つと完了** → `data/halls.json` が自動生成される

### ステップ5: Netlifyにデプロイ（5分）

1. https://app.netlify.com にアクセス
2. 「Add new site」→「Import from Git」
3. GitHubを選び、`slot-dashboard-pwa` リポジトリを選択
4. デフォルト設定のまま「Deploy site」
5. 数秒でURL発行（例: `https://amazing-site-123.netlify.app`）

※ **Netlifyを使う理由**: GitHubに更新があると自動でサイトも更新される

### ステップ6: アプリにGitHub URLを設定（2分）

1. 発行されたNetlify URLをスマホで開く
2. 「⚙️設定」タブを開く
3. 「GitHub データURL」欄に下記を入力（`yourname` を自分のGitHubユーザー名に置き換え）

   ```
   https://raw.githubusercontent.com/yourname/slot-dashboard-pwa/main/data/halls.json
   ```

4. 「URL保存」→「📥 今すぐ最新データを取得」をタップ
5. 「✅ 6ホール分のデータを取得しました」と出れば成功

### ステップ7: スマホにインストール（1分）

**📱 Android (Chrome)**
- 「⚙️設定」→「📲 アプリをインストール」をタップ

**🍎 iPhone (Safari)**
- 共有ボタン[ ↑ ]→「ホーム画面に追加」

---

## ⏰ 自動更新のしくみ

- **毎日朝7時（日本時間）**にGitHub Actionsが自動でスクレイピング
- 最新データを `data/halls.json` にコミット
- アプリ起動時、前回から6時間以上経過していれば自動でJSONを再取得
- 手動で「📥 今すぐ最新データを取得」も可能

---

## 🔧 トラブルシューティング

### Q. GitHub Actionsが失敗する
- リポジトリの「Settings」→「Actions」→「General」
- 「Workflow permissions」を **Read and write permissions** に変更
- 「Save」をクリック後、Actionsタブから再実行

### Q. データが取得できない
- GitHub URLが正しいか確認（`raw.githubusercontent.com` から始まる）
- リポジトリがPrivateの場合は、Publicに変更するか、Personal Access Tokenが必要
- ブラウザのコンソール（F12）でエラー内容を確認

### Q. スクレイピングが空データになる
- みんレポ側のHTML構造が変わった可能性
- `scripts/scrape.py` の調整が必要 → Claudeに「スクレイパー修正して」と依頼

### Q. アプリ更新が反映されない（PWA）
- スマホで一度アプリを削除して再インストール
- またはブラウザのキャッシュをクリア

---

## 📊 取得できるデータ

### 毎日自動取得（毎朝7時 JST）→ `data/halls.json`

**データソース1: みんレポ (min-repo.com)**
- 機種別の平均差枚・平均G数・出率
- 全体勝率・総台数
- 上位30機種を差枚順で

**データソース2: DMMぱちタウン (p-town.dmm.com)**
- 出玉ランキングTOP10（パチンコ・スロット別）
- 機種名・差玉/差枚・台番号

**データソース3: アナスロ (ana-slo.com) ⭐NEW**
- 台番号レベルの超詳細データ（最大価値）
- 機種別: 平均差枚・最大/最小差枚・勝率・平均BB/RB回数
- Cloudflare保護を回避（Refererヘッダー方式）

### 週次自動取得（毎週月曜朝7時 JST）→ `data/reviews.json`

**データソース3: みんパチ (minpachi.com)**
- 総合評価点・営業/接客/設備の3指標
- ユーザー口コミ最大10件

### 対象ホール（13店舗）

**苫小牧エリア（7店）**
- ベガスベガス苫小牧店 ⭐DMM対応
- マルハン苫小牧駅前店
- プレイランドハッピー三光店
- コアシティ
- ひまわり苫小牧店
- ロイヤル沼ノ端店
- ロイヤル苫小牧店 ⭐DMM対応

**登別エリア（2店）**
- ロイヤル登別店 ⭐DMM対応
- ダイナム登別店

**室蘭エリア（4店）**
- ビクトリア室蘭店 ⭐DMM対応
- ひまわり室蘭店
- マルハン室蘭店
- ZEUS

---

## 💡 ヒント

- 通信エラー時はバンドル済みの初期データが使われます
- データはローカル保存されるためオフライン閲覧可能
- 他のホールを追加したい場合は `scripts/scrape.py` の `HALLS` に追記
