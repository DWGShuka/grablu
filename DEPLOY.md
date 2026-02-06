# Grablu Web Application - GCP Cloud Run デプロイ手順書

## 概要
Grablu 団員管理システムをGCP Cloud Runにデプロイする手順です。Cloud Runはサーバーレスでコンテナを実行でき、無料枠が充実しています。

## 料金について
**無料枠（毎月）:**
- リクエスト: 200万回
- CPU時間: 360,000 vCPU秒
- メモリ: 180,000 GiB秒
- Cloud SQL（PostgreSQL）: 小規模インスタンス無料枠あり

**推定コスト:**
- 小規模利用: 無料枠内で収まる
- 中規模利用: 月数百円程度

---

## 前提条件
- Googleアカウント
- クレジットカード（無料枠内でも登録必須）
- gcloud CLI（インストール手順は後述）

---

## 1. GCPプロジェクトのセットアップ

### 1.1 GCPコンソールにアクセス
https://console.cloud.google.com/

### 1.2 新しいプロジェクトを作成
1. プロジェクトセレクタから「新しいプロジェクト」をクリック
2. プロジェクト名: `grablu-app`
3. 組織: なし（個人利用の場合）
4. 「作成」をクリック

### 1.3 請求先アカウントの設定
1. 左メニュー → 「お支払い」
2. 新しい請求先アカウントを作成
3. クレジットカード情報を入力
   - **注意**: 無料枠内なら課金されません

### 1.4 必要なAPIを有効化
以下のAPIを有効にします：

```bash
# Cloud Run API
# Cloud SQL Admin API
# Artifact Registry API
# Cloud Build API
```

GCPコンソールで「APIとサービス」→「ライブラリ」から検索して有効化

---

## 2. gcloud CLIのセットアップ

### 2.1 gcloud CLIのインストール

**Windows:**
```powershell
# インストーラをダウンロード
# https://cloud.google.com/sdk/docs/install

# または Chocolateyを使用
choco install gcloudsdk
```

**Mac:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 2.2 gcloud認証
```bash
# Googleアカウントで認証
gcloud auth login

# プロジェクトを設定
gcloud config set project grablu-app

# デフォルトリージョンを設定
gcloud config set run/region asia-northeast1  # 東京リージョン
```

---

## 3. Cloud SQLのセットアップ

### 3.1 PostgreSQLインスタンスを作成

**注意**: PostgreSQL 16では`db-f1-micro`が使えません。以下のオプションから選択してください。

**オプション1: PostgreSQL 14（推奨、低コスト）**

Windows (PowerShell):
```powershell
# Cloud SQLインスタンスを作成（最小構成）
gcloud sql instances create grablu-db `
  --database-version=POSTGRES_14 `
  --tier=db-f1-micro `
  --region=asia-northeast1 `
  --root-password=YOUR_STRONG_PASSWORD `
  --storage-size=10GB `
  --storage-type=HDD

# データベースを作成
gcloud sql databases create grablu --instance=grablu-db

# ユーザーを作成（1行版 - コマンドプロンプト/PowerShell両対応）
gcloud sql users create grablu --instance=grablu-db --password=YOUR_DB_PASSWORD

# または複数行版（PowerShell専用）
# gcloud sql users create grablu `
#   --instance=grablu-db `
#   --password=YOUR_DB_PASSWORD
```

Mac/Linux (Bash):
```bash
# Cloud SQLインスタンスを作成（最小構成）
gcloud sql instances create grablu-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=asia-northeast1 \
  --root-password=YOUR_STRONG_PASSWORD \
  --storage-size=10GB \
  --storage-type=HDD

# データベースを作成
gcloud sql databases create grablu --instance=grablu-db

# ユーザーを作成（1行版推奨）
gcloud sql users create grablu --instance=grablu-db --password=YOUR_DB_PASSWORD

# または複数行版
# gcloud sql users create grablu \
#   --instance=grablu-db \
#   --password=YOUR_DB_PASSWORD
```

**オプション2: PostgreSQL 16（新しいバージョン、少し高い）**

Windows (PowerShell):
```powershell
# Cloud SQLインスタンスを作成（PostgreSQL 16対応）
gcloud sql instances create grablu-db `
  --database-version=POSTGRES_16 `
  --tier=db-n1-standard-1 `
  --region=asia-northeast1 `
  --root-password=YOUR_STRONG_PASSWORD `
  --storage-size=10GB `
  --storage-type=SSD

# データベースを作成
gcloud sql databases create grablu --instance=grablu-db

# ユーザーを作成
gcloud sql users create grablu `
  --instance=grablu-db `
  --password=YOUR_DB_PASSWORD
```

Mac/Linux (Bash):
```bash
# Cloud SQLインスタンスを作成（PostgreSQL 16対応）
gcloud sql instances create grablu-db \
  --database-version=POSTGRES_16 \
  --tier=db-n1-standard-1 \
  --region=asia-northeast1 \
  --root-password=YOUR_STRONG_PASSWORD \
  --storage-size=10GB \
  --storage-type=SSD

# データベースを作成
gcloud sql databases create grablu --instance=grablu-db

# ユーザーを作成
gcloud sql users create grablu \
  --instance=grablu-db \
  --password=YOUR_DB_PASSWORD
```

**料金比較:**
- PostgreSQL 14 + db-f1-micro: 月額 約$7-10
- PostgreSQL 16 + db-n1-standard-1: 月額 約$25-30

個人プロジェクトでは**オプション1（PostgreSQL 14）を推奨**します。

**注意**: `YOUR_STRONG_PASSWORD`と`YOUR_DB_PASSWORD`は強力なパスワードに置き換えてください。

### 3.2 Cloud SQL Proxyの設定（オプション、ローカルテスト用）

```bash
# Cloud SQL Proxyをダウンロード
# Windows
curl -o cloud-sql-proxy.exe https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.x64.exe

# Mac/Linux
curl -o cloud-sql-proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud-sql-proxy

# 接続
./cloud-sql-proxy grablu-app:asia-northeast1:grablu-db
```

---

## 4. Artifact Registryのセットアップ

### 4.1 Dockerリポジトリを作成

**Windows (PowerShell):**
```powershell
# リポジトリ作成
gcloud artifacts repositories create grablu-repo `
  --repository-format=docker `
  --location=asia-northeast1 `
  --description="Grablu application repository"

# Docker認証を設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

**Mac/Linux (Bash):**
```bash
# リポジトリ作成
gcloud artifacts repositories create grablu-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Grablu application repository"

# Docker認証を設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

---

## 5. アプリケーションのビルドとプッシュ

### 5.1 本番用Dockerfileの準備

プロジェクトルートの`Dockerfile`を確認（既に存在します）

### 5.2 環境変数ファイルの準備

`.env.production`を作成（**Gitにコミットしない**）:

**SMTP使用の場合（推奨・無料）:**
```env
DATABASE_URL=postgresql://grablu:YOUR_DB_PASSWORD@/grablu?host=/cloudsql/grablu-app:asia-northeast1:grablu-db
USERNAME=admin
PASSWORD=your_admin_password
SECRET_KEY=your_secret_key_for_email_tokens_and_sessions
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
BASE_URL=https://gbf-guild-mng.com
```

**SendGrid使用の場合:**
```env
DATABASE_URL=postgresql://grablu:YOUR_DB_PASSWORD@/grablu?host=/cloudsql/grablu-app:asia-northeast1:grablu-db
USERNAME=admin
PASSWORD=your_admin_password
SECRET_KEY=your_secret_key_for_email_tokens_and_sessions
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
BASE_URL=https://gbf-guild-mng.com
```

**環境変数の説明:**
- `DATABASE_URL`: PostgreSQL接続文字列（Cloud SQL用）
- `USERNAME` / `PASSWORD`: 管理者アカウント（初期認証用）
- `SECRET_KEY`: メール認証トークンとセッション用のシークレットキー
- **SMTP設定（推奨）**:
  - `SMTP_HOST`: SMTPサーバーホスト
  - `SMTP_PORT`: SMTPポート（通常587）
  - `SMTP_USER`: SMTPユーザー名（メールアドレス）
  - `SMTP_PASSWORD`: SMTPパスワード（Gmailアプリパスワード）
  - `SMTP_FROM_EMAIL`: メール送信元アドレス
- **SendGrid設定（オプション）**:
  - `SENDGRID_API_KEY`: SendGridのAPIキー
  - `SENDGRID_FROM_EMAIL`: メール送信元アドレス
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Google OAuth認証用
- `BASE_URL`: アプリケーションのベースURL（メール内リンク生成用）

### 5.3 Dockerイメージのビルドとプッシュ

```bash
**Windows (PowerShell) - SMTP使用:**
```powershell
gcloud run deploy grablu-web `
  --image=asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest `
  --platform=managed `
  --region=asia-northeast1 `
  --allow-unauthenticated `
  --add-cloudsql-instances=grablu-app:asia-northeast1:grablu-db `
  --set-env-vars="DATABASE_URL=postgresql://grablu:YOUR_DB_PASSWORD@/grablu?host=/cloudsql/grablu-app:asia-northeast1:grablu-db" `
  --set-env-vars="USERNAME=admin" `
  --set-env-vars="PASSWORD=your_admin_password" `
  --set-env-vars="SECRET_KEY=your_secret_key_change_in_production" `
  --set-env-vars="SMTP_HOST=smtp.gmail.com" `
  --set-env-vars="SMTP_PORT=587" `
  --set-env-vars="SMTP_USER=your@gmail.com" `
  --set-env-vars="SMTP_PASSWORD=your_gmail_app_password" `
  --set-env-vars="SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com" `
  --set-env-vars="BASE_URL=https://grablu-web-xxxxxxxxxx-an.a.run.app" `
  --memory=512Mi `
  --cpu=1 `
  --max-instances=10 `
  --min-instances=0
```

**Windows (PowerShell) - SendGrid使用:**
```powershell
gcloud run deploy grablu-web `
  --image=asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest `
  --platform=managed `
  --region=asia-northeast1 `
  --allow-unauthenticated `
  --add-cloudsql-instances=grablu-app:asia-northeast1:grablu-db `
  --set-env-vars="DATABASE_URL=postgresql://grablu:YOUR_DB_PASSWORD@/grablu?host=/cloudsql/grablu-app:asia-northeast1:grablu-db" `
  --set-env-vars="USERNAME=admin" `
  --set-env-vars="PASSWORD=your_admin_password" `
  --set-env-vars="SECRET_KEY=your_secret_key_change_in_production" `
  --set-env-vars="SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxx" `
  --set-env-vars="SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com" `
  --set-env-vars="BASE_URL=https://grablu-web-xxxxxxxxxx-an.a.run.app" `
  --memory=512Mi `
  --cpu=1 `
  --max-instances=10 `
  --min-instances=0
```

**Mac/Linux (Bash):**
# イメージをビルド
docker build -t asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest .

# プッシュ
docker push asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest
```

---

## 6. Cloud Runへのデプロイ

### 6.1 Cloud Runサービスをデプロイ

```bash
gcloud run deploy grablu-web \
  --image=asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest \
  --platform=managed \
  --region=asia-northeast1 \
  --allow-unauthenticated \
  --add-cloudsql-instances=grablu-app:asia-northeast1:grablu-db \
  --set-env-vars="DATABASE_URL=postgresql://grablu:YOUR_DB_PASSWORD@/grablu?host=/cloudsql/grablu-app:asia-northeast1:grablu-db" \
  --set-env-vars="USERNAME=admin" \
  --set-env-vars="PASSWORD=your_admin_password" \
  --set-env-vars="SECRET_KEY=your_secret_key_change_in_production" \
  --set-env-vars="SMTP_HOST=smtp.gmail.com" \
  --set-env-vars="SMTP_PORT=587" \
  --set-env-vars="SMTP_USER=your@gmail.com" \
  --set-env-vars="SMTP_PASSWORD=your_gmail_app_password" \
  --set-env-vars="SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com" \
  --set-env-vars="BASE_URL=https://grablu-web-xxxxxxxxxx-an.a.run.app" \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=10 \
  --min-instances=0
```

※ SendGrid使用時は、SMTP_* の代わりに SENDGRID_API_KEY と SENDGRID_FROM_EMAIL を設定してください。

### 6.2 デプロイ完了

デプロイが完了すると、URLが表示されます：
```
Service URL: https://grablu-web-xxxxxxxxxx-an.a.run.app
```

このURLにアクセスしてアプリケーションを確認してください。

---

## 7. メール認証設定

メール送信には2つの方法があります：

### 方法1: SMTP（推奨・完全無料）

自分のドメインのメールサーバーを使う方法です。

#### オプションA: Gmail / Google Workspace

**ステップ1: Gmailアプリパスワードの取得**

1. https://myaccount.google.com/apppasswords にアクセス
2. 「アプリを選択」→「その他（カスタム名）」→「Grablu」
3. 「生成」をクリック
4. **16桁のパスワードをコピー**（スペースなし）

**ステップ2: Cloud Runに環境変数を設定**

```bash
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --set-env-vars="SMTP_HOST=smtp.gmail.com" \
  --set-env-vars="SMTP_PORT=587" \
  --set-env-vars="SMTP_USER=your@gmail.com" \
  --set-env-vars="SMTP_PASSWORD=your_app_password" \
  --set-env-vars="SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com"
```

**送信制限**: 1日500通（個人Gmail）/ 2,000通（Google Workspace）

#### オプションB: 独自SMTPサーバー

ドメインのメールサービスのSMTP設定を使用:

```bash
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --set-env-vars="SMTP_HOST=mail.your-domain.com" \
  --set-env-vars="SMTP_PORT=587" \
  --set-env-vars="SMTP_USER=noreply@gbf-guild-mng.com" \
  --set-env-vars="SMTP_PASSWORD=your_email_password" \
  --set-env-vars="SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com"
```

### 方法2: SendGrid（オプション）

### 方法2: SendGrid（オプション）

SendGridを使う場合の手順です。

#### ステップ1: SendGridアカウント作成

1. https://sendgrid.com/ にアクセス
2. 「Start for Free」をクリック
3. アカウント情報を入力して登録
4. メール認証を完了

**無料プラン**: 月100通まで無料

#### ステップ2: SendGrid API Key の取得

1. SendGridダッシュボードにログイン
2. 左メニュー → 「Settings」→ 「API Keys」
3. 「Create API Key」をクリック
4. API Key名: `Grablu-Production`
5. アクセス権限: 「Mail Send」
6. 「Create & View」をクリック
7. **表示されたAPIキーをコピー**（再表示不可）

APIキーの形式: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### ステップ3: 送信元メールアドレスの認証

1. SendGridダッシュボード → 「Settings」→ 「Sender Authentication」
2. 「Verify a Single Sender」をクリック
3. メールアドレス（例: `noreply@gbf-guild-mng.com`）を入力
4. 送信された確認メールのリンクをクリック

#### ステップ4: Cloud Runに環境変数を設定

```bash
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --set-env-vars="SENDGRID_API_KEY=SG.your_actual_api_key_here" \
  --set-env-vars="SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com"
```

**注意**: SendGridライブラリが必要です（requirements.txtに含まれています）

### メール送信テスト

デプロイ完了後、管理者アカウントでログインして以下のURLにアクセス:

```
https://your-app-url/admin/test-email
```

1. テスト用メールアドレスを入力
2. 「テストメールを送信」をクリック
3. メールが届くことを確認

**トラブルシューティング:**

- **SMTP送信エラー**:
  - Gmailアプリパスワードが正しいか確認
  - 2段階認証プロセスが有効か確認
  - ログを確認: `gcloud run services logs tail grablu-web`

- **SendGrid送信エラー**:
  - SendGrid APIキーが正しく設定されているか確認
  - 送信元メールアドレスが認証済みか確認
  - SendGrid ダッシュボードの「Activity」でエラーログを確認

- **開発モード**（メール未設定）:
  - ログに認証URLが出力されます
  - ログから認証URLをコピーしてブラウザでアクセス可能

### 送信制限と料金

**SMTP（推奨・無料）:**
- Gmail: 1日500通まで無料
- Google Workspace: 1日2,000通まで無料
- 独自サーバー: プロバイダーによる（通常無料）

**SendGrid:**
- 無料プラン: 月100通まで
- 有料プラン: 月$19.95〜

詳細は [EMAIL_SETUP.md](EMAIL_SETUP.md) を参照してください。

---

## 8. CI/CDの設定（オプション）

### 8.1 Cloud Buildを使った自動デプロイ

`cloudbuild.yaml`を作成:

```yaml
steps:
  # Dockerイメージをビルド
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/grablu-repo/web:$COMMIT_SHA', '.']
  
  # Artifact Registryにプッシュ
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/grablu-repo/web:$COMMIT_SHA']
  
  # Cloud Runにデプロイ
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'grablu-web'
      - '--image=asia-northeast1-docker.pkg.dev/$PROJECT_ID/grablu-repo/web:$COMMIT_SHA'
      - '--region=asia-northeast1'
      - '--platform=managed'

images:
  - 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/grablu-repo/web:$COMMIT_SHA'
```

### 7.2 GitHub連携

```bash
# Cloud Buildトリガーを作成
gcloud builds triggers create github \
  --repo-name=grablu \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## 9. データベース初期化

### 9.1 初回デプロイ後のデータベース確認

デプロイ後、初めてアプリケーションにアクセスすると自動的にテーブルが作成されます。

ログを確認:
```bash
gcloud run services logs read grablu-web --limit=50
```

### 9.2 手動でのテーブル確認（オプション）

```bash
# Cloud SQLに接続
gcloud sql connect grablu-db --user=grablu --quiet

# PostgreSQL内で確認
\c grablu
\dt
```

---

## 10. 運用と監視

### 10.1 ログの確認

```bash
# リアルタイムログ
gcloud run services logs tail grablu-web

# 最新50件
gcloud run services logs read grablu-web --limit=50
```

### 10.2 メトリクスの確認

GCPコンソール → Cloud Run → grablu-web → 「メトリクス」タブ

以下を確認できます：
- リクエスト数
- レスポンスタイム
- エラー率
- CPU/メモリ使用率

### 10.3 アラート設定

1. GCPコンソール → Monitoring → Alerting
2. 「ポリシーを作成」をクリック
3. 条件を設定:
   - エラー率が5%を超えたら
   - レスポンスタイムが3秒を超えたら
4. 通知先を設定（メール、Slack等）

---

## 11. コスト最適化

### 11.1 無料枠の確認

GCPコンソール → お支払い → 「レポート」

### 11.2 コスト削減のヒント

1. **最小インスタンス数を0に設定**
   ```bash
   --min-instances=0
   ```
   アクセスがない時は完全に停止

2. **リソース制限**
   ```bash
   --memory=512Mi  # 必要最小限
   --cpu=1         # 1コアで十分
   ```

3. **Cloud SQLを停止**（開発中）
   ```bash
   gcloud sql instances patch grablu-db --activation-policy=NEVER
   ```
   使用時のみ起動:
   ```bash
   gcloud sql instances patch grablu-db --activation-policy=ALWAYS
   ```

---

## 12. トラブルシューティング

### 12.1 デプロイが失敗する

```bash
# ログを確認
gcloud run services logs read grablu-web --limit=100

# サービスの状態を確認
gcloud run services describe grablu-web --region=asia-northeast1
```

### 12.2 データベース接続エラー

```bash
# Cloud SQLインスタンスの状態確認
gcloud sql instances describe grablu-db

# 接続文字列の確認
gcloud sql instances describe grablu-db --format="value(connectionName)"
```

正しい形式: `grablu-app:asia-northeast1:grablu-db`

### 12.3 アプリケーションが起動しない

1. ローカルでDockerイメージをテスト:
   ```bash
   docker run -p 8000:8000 \
     -e DATABASE_URL="postgresql://..." \
     asia-northeast1-docker.pkg.dev/grablu-app/grablu-repo/web:latest
   ```

2. ログを確認:
   ```bash
   gcloud run services logs tail grablu-web
   ```

---

## 13. カスタムドメインの設定（オプション）

### 13.1 ドメインのマッピング

```bash
# ドメインを追加
gcloud run domain-mappings create \
  --service=grablu-web \
  --domain=grablu.yourdomain.com \
  --region=asia-northeast1
```

### 13.2 DNSレコードの設定

Cloud Runが表示するDNSレコードを、ドメインレジストラで設定してください。

---

## 14. セキュリティ強化

### 14.1 認証の追加

Cloud Run IAMで特定のユーザーのみアクセス可能に:

```bash
# 認証を必須に変更
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --no-allow-unauthenticated

# 特定のユーザーに権限付与
gcloud run services add-iam-policy-binding grablu-web \
  --region=asia-northeast1 \
  --member="user:someone@example.com" \
  --role="roles/run.invoker"
```

### 14.2 Secret Managerの使用

機密情報をSecret Managerに保存:

```bash
# シークレット作成
echo -n "your_db_password" | gcloud secrets create db-password --data-file=-

# Cloud Runでシークレットを使用
gcloud run services update grablu-web \
  --region=asia-northeast1 \
  --update-secrets=DB_PASSWORD=db-password:latest
```

---

## まとめ

GCP Cloud Runを使ったデプロイの流れ：

1. ✅ GCPプロジェクト作成
2. ✅ Cloud SQL（PostgreSQL）セットアップ
3. ✅ Artifact RegistryでDockerリポジトリ作成
4. ✅ Dockerイメージをビルド＆プッシュ
5. ✅ Cloud Runにデプロイ
6. ✅ 自動スケーリングと監視

**メリット:**
- サーバー管理不要
- 自動スケーリング
- 使った分だけ課金
- 無料枠が充実

**参考リンク:**
- [Cloud Run公式ドキュメント](https://cloud.google.com/run/docs)
- [Cloud SQL公式ドキュメント](https://cloud.google.com/sql/docs)
- [料金計算ツール](https://cloud.google.com/products/calculator)
