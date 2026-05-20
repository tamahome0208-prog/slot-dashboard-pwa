# AdBlocker (Android, Pixel 10a 想定)

AdGuard / Blokada / DNS66 と同じ仕組みの DNS ベース広告ブロッカー。
端末内に擬似 VPN (`VpnService`) を立て、`10.215.173.2:53` 宛 DNS クエリだけを捕捉して

- ブロックリスト一致 → `NXDOMAIN` を即返す
- 非一致 → 上流 DNS (既定 `1.1.1.1`, fallback `1.0.0.1`) に転送して応答を返す

ルートは DNS 専用 (`10.215.173.2/32`) のみで、それ以外のトラフィックには触らない。
**root 不要・追加証明書不要・全アプリに効く** (Chrome, ゲーム, 他社アプリ含む)。
HTTPS の中身は復号しないので、HTTPS 内のページ広告は完全には消えないが、
広告 / 計測ドメインへの接続自体を遮断するので大半の広告と追跡は止まる。

## 構成

```
android/
├── settings.gradle.kts / build.gradle.kts / gradle.properties
├── gradle/wrapper/                    # Gradle 8.7 wrapper
├── gradlew / gradlew.bat
└── app/
    ├── build.gradle.kts               # AGP 8.5.2, Kotlin 1.9.24, minSdk 26, targetSdk 34
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── assets/blocklist.txt       # 同梱の最小ブロックリスト (約 80 件)
        ├── java/app/adblocker/
        │   ├── AdBlockerApp.kt        # Application + 通知チャンネル
        │   ├── data/
        │   │   ├── Settings.kt         # SharedPreferences ラッパ
        │   │   ├── Stats.kt            # ブロック数・最近のクエリ履歴
        │   │   └── BlocklistRepository.kt # hosts ファイルのパース + DL
        │   ├── vpn/
        │   │   ├── AdBlockVpnService.kt # VpnService 本体
        │   │   ├── DnsPacket.kt         # DNS パーサ / NXDOMAIN ビルダ
        │   │   ├── IpPacket.kt          # IPv4 + UDP ヘッダ操作 / チェックサム
        │   │   └── BootReceiver.kt      # 端末起動時の自動開始
        │   └── ui/
        │       ├── MainActivity.kt      # ON/OFF, 統計, 最近のクエリ
        │       └── BlocklistActivity.kt # 設定 + カスタム/許可ドメイン編集
        └── res/{layout,values,values-ja,xml,drawable,mipmap-anydpi-v26}/...
```

## ビルド方法

### Android Studio (推奨)

1. Android Studio Hedgehog 以降を開く
2. `File > Open` → `slot-dashboard-pwa/android` を選択
3. SDK が自動で入る (Android 14, SDK 34)。Sync が終わったら `Run` で Pixel 10a に直接インストール

### コマンドライン

事前準備: Android SDK (API 34) と JDK 17 を入れて `ANDROID_HOME` を設定する。

```bash
cd slot-dashboard-pwa/android
./gradlew assembleDebug
# 出力: app/build/outputs/apk/debug/app-debug.apk
```

Pixel 10a を USB で繋いで開発者モードを有効にしてから:

```bash
./gradlew installDebug
```

## 動作

1. アプリを開いて「広告とトラッカーをブロック」をオン
2. Android の VPN 許可ダイアログで「OK」(初回のみ)
3. ステータスバーに鍵アイコン + 通知が出れば動作中
4. 「リモートリストを更新」ボタンで StevenBlack hosts (約 15 万件) をダウンロード
5. 「ブロックリスト・設定」から
   - 上流 DNS (既定 1.1.1.1) を変更
   - 独自ドメインの追加 (1 行 1 ドメイン、サブドメイン自動マッチ)
   - 許可ドメイン (ホワイトリスト) の追加
   - 端末起動時の自動開始

## 仕組み (内部)

```
[App] → DNS query (UDP/53 to 10.215.173.2)
   ↓
[Android tun device]
   ↓ raw IP packet
[AdBlockVpnService.runLoop]
   ↓ parse IPv4 + UDP + DNS question
   │
   ├─ blocked? → build NXDOMAIN, swap src/dst, write back to tun
   │
   └─ not blocked? → forward via VpnService.protect()'d DatagramSocket
                      to upstream (1.1.1.1:53)
                      ↓ response
                      wrap in UDP + IPv4 (swapped), write back to tun
   ↓
[App] gets either NXDOMAIN (広告サーバに繋がらない) or real answer
```

## 制限事項

- **DNS over HTTPS / DNS over TLS** を直接サーバ指定で使うアプリ (Chrome の DoH や
  Firefox の Trusted Recursive Resolver) はこの DNS フィルタを完全に迂回する。
  対策: ユーザーが各アプリの DoH を切る、または Android の Private DNS を `off` にする。
- **YouTube アプリ内広告**は同一ドメインから配信されるため DNS ブロックでは消せない
  (これは AdGuard 等も同じで、SponsorBlock 系の別レイヤが必要)。
- **既に他の VPN が動いている**と Android の制約上同時に動かせない。1 つしか起動できない。
- IPv6 経路は今回は捕捉していない (10.215.173.2/32 のみ追加)。Pixel の DNS は通常 IPv4 にフォールバックするので実用上問題ないが、IPv6 only DNS にしている場合は届かない。

## 法的・倫理面

- 自分の端末・自分が管理する通信のみで使用すること。
- ブロックリスト (StevenBlack hosts 等) のライセンスを確認すること。
- 広告で運営されているサイトの広告を消すことは、運営者の収益を減らす行為であることを
  理解した上で使用すること。

## ライセンス

このアプリのコードは MIT。同梱 `assets/blocklist.txt` は public domain 相当。
ダウンロードする StevenBlack hosts は MIT。
