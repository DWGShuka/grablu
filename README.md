# Grablu - グラブル団員管理ツール

Webスクレイピングでグラブルの団員データを取得し、Google Sheetsに自動記録するツールです。

## 機能

- 団員一覧ページから名前と順位を自動取得
- Google Sheetsに自動書き込み
- イベント回数ごとに列を追加
- ログファイル出力

## セットアップ

### 1. 仮想環境の作成と有効化

```powershell
# 仮想環境を作成
python -m venv .venv

# 有効化（PowerShell）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate

# 有効化（cmd）
.venv\Scripts\activate.bat
```

### 2. パッケージのインストール

```powershell
pip install -r requirements.txt
```

### 3. 設定ファイルの準備

`config.yaml` を作成：

```yaml
spreadsheet:
  url: "https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID"
  sheet_name: "団員管理"

guild:
  name: "あなたの団名"

site:
  base_url: "https://example.com"
```

### 4. Google認証情報の設定

1. Google Cloud Consoleでサービスアカウントを作成
2. `credentials.json` をダウンロードしてプロジェクトルートに配置
3. スプレッドシートにサービスアカウントのメールアドレスを共有

## 実行方法

```powershell
python main.py
```

## ログ

実行ログは `grablu.log` に出力されます。

## 注意事項

- `config.yaml` と `credentials.json` は機密情報のため、Gitに含めないでください（`.gitignore`に設定済み）
- Chromeブラウザが必要です（webdriver-managerが自動でChromeDriverをインストール）

## ライセンス

個人使用のみ
