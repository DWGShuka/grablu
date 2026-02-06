# メール認証機能 セットアップガイド

## 概要
Grabluのメール認証機能は、ユーザー登録時にメールアドレスの確認を行うための機能です。以下の2つの方法でメール送信が可能です：

### **方法1: SMTP（推奨・完全無料）** ⭐
- 自分のドメインのメールサーバーを使用
- Gmail、Google Workspace、独自SMTPサーバーなど
- **完全無料・追加コストなし**
- 設定が簡単

### **方法2: SendGrid**
- 専用のメール送信サービス
- 月100通まで無料（それ以降は有料）
- 高度な配信機能とログ

**推奨**: 自分のドメインがある場合は **SMTP（方法1）** が最適です。

---

## 方法1: SMTP設定（推奨・無料）

### オプションA: Gmail / Google Workspaceを使用（最も簡単）

**完全無料で使用可能**

#### ステップ1: Gmailアプリパスワードの取得

1. Googleアカウントにログイン
2. https://myaccount.google.com/apppasswords にアクセス
3. 「アプリを選択」→「その他（カスタム名）」→「Grablu」
4. 「生成」をクリック
5. **16桁のパスワードが表示される**（例：`abcd efgh ijkl mnop`）
6. このパスワードをコピー（スペースは不要）

**注意**: 2段階認証プロセスが有効になっている必要があります。

#### ステップ2: 環境変数を設定

Cloud Runの場合:
```bash
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --set-env-vars="SMTP_HOST=smtp.gmail.com" \
  --set-env-vars="SMTP_PORT=587" \
  --set-env-vars="SMTP_USER=your@gmail.com" \
  --set-env-vars="SMTP_PASSWORD=abcdefghijklmnop" \
  --set-env-vars="SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com" \
  --set-env-vars="BASE_URL=https://gbf-guild-mng.com"
```

ローカル開発（`.env`ファイル）:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com
BASE_URL=http://localhost:8080
```

#### Gmail送信制限
- **1日500通まで**（個人Gmail）
- **1日2,000通まで**（Google Workspace）
- 小規模サイトには十分

---

### オプションB: 独自のSMTPサーバー

お使いのドメインのメールサービスがSMTPをサポートしている場合:

#### 一般的なSMTP設定

環境変数:
```env
SMTP_HOST=mail.your-domain.com
SMTP_PORT=587
SMTP_USER=noreply@gbf-guild-mng.com
SMTP_PASSWORD=your_email_password
SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com
BASE_URL=https://gbf-guild-mng.com
```

#### 主要プロバイダーのSMTP設定

**さくらインターネット:**
```env
SMTP_HOST=SSS.sakura.ne.jp
SMTP_PORT=587
```

**Xserver:**
```env
SMTP_HOST=sv*****.xserver.jp
SMTP_PORT=465
```

**お名前.com:**
```env
SMTP_HOST=mail***.onamae.ne.jp
SMTP_PORT=465
```

**ロリポップ:**
```env
SMTP_HOST=smtp.lolipop.jp
SMTP_PORT=465
```

---

## 方法2: SendGrid設定（オプション）

SendGridを使いたい場合の設定手順です。

### ステップ1: SendGridアカウント作成

1. https://sendgrid.com/ でアカウント登録
2. メール認証を完了

**無料プラン**: 月100通まで無料

### ステップ2: API Key取得

1. SendGridダッシュボード → Settings → API Keys
2. 「Create API Key」をクリック
3. 名前: `Grablu-Production`
4. 権限: 「Mail Send」
5. APIキーをコピー（`SG.xxxxx...`）

### ステップ3: 送信元メールアドレス認証

1. Settings → Sender Authentication → Verify a Single Sender
2. メールアドレス入力（例: `noreply@gbf-guild-mng.com`）
3. 確認メールのリンクをクリック

### ステップ4: 環境変数設定

Cloud Runの場合:
```bash
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --set-env-vars="SENDGRID_API_KEY=SG.your_actual_api_key" \
  --set-env-vars="SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com" \
  --set-env-vars="BASE_URL=https://gbf-guild-mng.com"
```

ローカル開発（`.env`ファイル）:
```env
SENDGRID_API_KEY=SG.your_actual_api_key
SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com
BASE_URL=http://localhost:8080
```

**注意**: SendGridライブラリが必要です:
```bash
pip install sendgrid>=6.11.0
```

---

## 実装内容

### 1. メール送信機能
- **ファイル**: [auth_utils.py](auth_utils.py)
- **優先順位**: SMTP → SendGrid → 開発モード（ログ出力）
- **自動フォールバック**: SMTP失敗時はSendGridを試行

### 2. 管理者用テストエンドポイント
- **URL**: `/admin/test-email`
- **機能**: 本番環境でメール送信をテスト可能
- **アクセス**: 管理者アカウントのみ

---

## 本番環境でのテスト方法

### 方法1: 管理者用テストページ（推奨）

1. 管理者アカウントでログイン
2. ブラウザで以下にアクセス:
   ```
   https://your-app-url/admin/test-email
   ```
3. テスト用メールアドレスを入力
4. 「テストメールを送信」をクリック
5. メールが届くことを確認

### 方法2: 実際のユーザー登録

1. `/register` でユーザーを新規登録
2. 登録したメールアドレスにメールが届く
3. メール内のリンクをクリックして認証完了

### 方法3: ログで認証URLを確認（開発モード）

SendGrid未設定の場合、ログに認証URLが出力されます:

```bash
# Cloud Runの場合
gcloud run services logs tail grablu-web

# ローカルの場合
# コンソール出力を確認
```

ログ例:
```
====== メール認証（開発モード） ======
宛先: test@example.com
以下のURLをクリックしてメールアドレスを確認してください：
http://localhost:8080/verify-email?token=xxxxxxxx
=====================================
```

このURLをコピーしてブラウザでアクセスすれば、メール送信なしで認証できます。

## トラブルシューティング

### SMTPでメールが届かない

**確認項目:**

1. **環境変数が正しく設定されているか**
   ```bash
   # Cloud Runの場合
   gcloud run services describe grablu-web --region=asia-northeast1 \
     --format="value(spec.template.spec.containers[0].env)"
   ```

2. **Gmailアプリパスワードの問題**
   - 2段階認証プロセスが有効になっているか確認
   - アプリパスワードを再生成して試す
   - パスワードにスペースが含まれていないか確認

3. **SMTP接続エラー**
   ```
   エラー: [Errno 11001] getaddrinfo failed
   ```
   - `SMTP_HOST` が正しいか確認
   - DNS解決の問題の可能性

   ```
   エラー: [Errno 10060] タイムアウト
   ```
   - ファイアウォールでポート 587 がブロックされている可能性
   - Cloud RunのアウトバウンドトラフィックVPCを確認

4. **認証エラー**
   ```
   エラー: (535, b'5.7.8 Username and Password not accepted')
   ```
   - `SMTP_USER` がメールアドレス全体か確認
   - アプリパスワードが正しいか確認
   - Gmailで「安全性の低いアプリ」設定を確認（非推奨）

5. **アプリケーションログを確認**
   ```bash
   gcloud run services logs tail grablu-web
   ```

### SendGridでメールが届かない

**確認項目:**
1. SendGrid APIキーが正しく設定されているか
2. 送信元メールアドレスが認証済みか
   - SendGridダッシュボード → Sender Authentication で確認

3. SendGridのエラーログを確認
   - SendGridダッシュボード → Activity
   - 送信失敗の理由が表示されます

### よくあるエラーと解決方法

| エラー | 原因 | 解決方法 |
|--------|------|----------|
| `401 Unauthorized` (SendGrid) | APIキーが間違っている | APIキーを再確認・再生成 |
| `403 Forbidden` (SendGrid) | 送信元未認証 | SendGridで送信元認証を完了 |
| `SMTPAuthenticationError` | パスワードが間違い | アプリパスワードを再生成 |
| `Connection timeout` | ポート/FWブロック | ポート587が開いているか確認 |
| `開発モード` と表示 | SMTP/SendGrid未設定 | 環境変数を設定 |

### 認証URLの有効期限

- デフォルト: 1時間
- 期限切れの場合は、ユーザーに再登録を依頼
- 変更したい場合: [auth_utils.py](auth_utils.py) の `verify_verification_token` 関数の `max_age` パラメータを変更

## 料金と制限

### SMTP（Gmail）
- **完全無料**
- **送信制限**:
  - 個人Gmail: 1日500通
  - Google Workspace: 1日2,000通
- 小規模〜中規模サイトに最適

### SMTP（独自サーバー）
- **完全無料**（ドメインのメールサービスに含まれる）
- 送信制限はプロバイダーによる
- 追加コストなし

### SendGrid 無料プラン
- **月100通まで無料**
- 100通を超える場合は有料プラン（$19.95/月〜）
- より高度な配信機能とログ

### 推奨アプローチ

**小規模サイト（月100通未満）**:
- SMTP（Gmail）を使用 → 完全無料

**中規模サイト（月100〜1,000通）**:
- SMTP（Gmail または独自サーバー）→ 完全無料
- 1日の送信が500通を超える場合はSendGridを検討

**大規模サイト（月1,000通以上）**:
- SendGrid有料プラン
- より高度な配信管理が必要

### コスト削減のヒント
- 開発・テスト環境では開発モード（SendGrid未設定）を使用
- 本番環境のみSendGridを設定
- 不要な認証メール送信を抑制

## 環境変数一覧

### SMTP設定（推奨）

| 変数名 | 必須 | 説明 | 例 |
|--------|------|------|-----|
| `SMTP_HOST` | ○ | SMTPサーバーのホスト名 | `smtp.gmail.com` |
| `SMTP_PORT` | △ | SMTPポート（デフォルト: 587） | `587` |
| `SMTP_USER` | ○ | SMTPユーザー名（メールアドレス） | `your@gmail.com` |
| `SMTP_PASSWORD` | ○ | SMTPパスワード（アプリパスワード） | `abcdefghijklmnop` |
| `SMTP_FROM_EMAIL` | △ | 送信元メールアドレス | `noreply@gbf-guild-mng.com` |
| `BASE_URL` | ○ | アプリケーションのベースURL | `https://gbf-guild-mng.com` |
| `SECRET_KEY` | ○ | トークン生成用シークレットキー | ランダムな文字列 |

### SendGrid設定（オプション）

| 変数名 | 必須 | 説明 | 例 |
|--------|------|------|-----|
| `SENDGRID_API_KEY` | ○ | SendGrid APIキー | `SG.xxxxx...` |
| `SENDGRID_FROM_EMAIL` | ○ | 送信元メールアドレス | `noreply@gbf-guild-mng.com` |
| `BASE_URL` | ○ | アプリケーションのベースURL | `https://gbf-guild-mng.com` |
| `SECRET_KEY` | ○ | トークン生成用シークレットキー | ランダムな文字列 |

**優先順位**: SMTPが設定されている場合は SMTP が優先されます。SMTP失敗時は自動的にSendGridにフォールバックします。

## セキュリティ考慮事項

1. **APIキーの管理**
   - Gitにコミットしない
   - 環境変数で管理
   - 定期的にローテーション

2. **トークンの有効期限**
   - デフォルト1時間（調整可能）
   - 短すぎるとユーザビリティ低下
   - 長すぎるとセキュリティリスク

3. **送信元ドメインの信頼性**
   - SPF/DKIM/DMARCを設定（ドメイン認証時）
   - スパム判定を避けるため

## 関連ファイル

- [auth_utils.py](auth_utils.py): メール送信機能実装
- [web_app.py](web_app.py): テストエンドポイントとメール認証フロー
- [models.py](models.py): ユーザーモデル（email_verified フィールド）
- [DEPLOY.md](DEPLOY.md): デプロイ手順とSendGrid設定詳細
- [requirements.txt](requirements.txt): 依存関係（sendgrid含む）

## サポート

問題が解決しない場合:
- SendGridサポート: https://support.sendgrid.com/
- Cloud Runドキュメント: https://cloud.google.com/run/docs
- プロジェクトのIssue: GitHub Issues
