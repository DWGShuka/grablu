# Grablu Web Application - ローカル開発ガイド

## ローカルでの起動方法

### 方法1: Docker Compose（推奨）

```bash
# Dockerイメージをビルドして起動
docker-compose up --build

# バックグラウンドで起動
docker-compose up -d

# 停止
docker-compose down
```

ブラウザで http://localhost:8000 にアクセス

**認証情報:**
- ユーザー名: `admin`
- パスワード: `grablu2026`

### 方法2: 直接実行

```bash
# 仮想環境をアクティベート
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# 必要なパッケージをインストール
pip install fastapi uvicorn jinja2 python-multipart

# アプリケーション起動
python web_app.py
```

ブラウザで http://localhost:8000 にアクセス

## 機能説明

### ホーム画面 (/)
- 最新の取得状況を表示
- 「データ取得開始」ボタンで団員データを取得
- 自動的に名前変更を検出
- スプレッドシートに反映

### 履歴画面 (/history)
- 名前変更履歴を一覧表示
- プレイヤーIDと変更履歴を確認

## 認証について

現在の認証はHTTP Basic認証です。
本番環境では以下を推奨:

1. 環境変数でユーザー名/パスワードを設定
2. パスワードを強力なものに変更
3. HTTPS化（Let's Encrypt等）

## 開発時のヒント

### ログの確認
```bash
# web_app.log ファイルを確認
tail -f web_app.log
```

### Dockerログの確認
```bash
docker-compose logs -f
```

### コンテナに入る
```bash
docker-compose exec web bash
```

### members.jsonの確認
```bash
cat members.json | python -m json.tool
```

## トラブルシューティング

### ポート8000が既に使用中
別のアプリケーションがポート8000を使用している場合:

```bash
# docker-compose.yml を編集してポートを変更
ports:
  - "8080:8000"  # 8080に変更
```

### Chromeドライバーのエラー
Selenium Managerが自動でChromeドライバーを管理しますが、
エラーが出る場合はChromeを最新版に更新してください。

## セキュリティ注意事項

⚠️ **重要:**
- `credentials.json` や `config.yaml` は絶対にGitにコミットしない
- 本番環境では必ずパスワードを変更する
- HTTPS通信を使用する（Let's Encrypt等）
- ファイアウォールでポートを制限する
