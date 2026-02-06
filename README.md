# Grablu - グラブル団員管理・ドロップ統計ツール

![CI Tests](https://github.com/YOUR_USERNAME/grablu/workflows/CI%20Tests/badge.svg)

Webスクレイピングでグラブルの団員データを取得し、Google Sheetsに自動記録するツールです。  
さらに、ドロップ確率を統計分析し、期待値とパーセンタイル評価を行う機能を搭載しています。

**🎉 Webアプリケーション版が利用可能です！**

- **ローカル開発**: [LOCAL_DEV.md](LOCAL_DEV.md)
- **GCPデプロイ**: [DEPLOY.md](DEPLOY.md) - Cloud Run（無料枠充実）

## 開発に参加する

開発に参加する場合は[CONTRIBUTING.md](CONTRIBUTING.md)をご覧ください。

- **デフォルトブランチ**: `develop`
- **本番ブランチ**: `main`
- **CI/CD**: GitHub Actions (自動テスト実行)

## 機能

### 団員管理
- 団員一覧ページから名前と順位を自動取得
- Google Sheetsに自動書き込み
- イベント回数ごとに列を追加
- ログファイル出力

### ドロップ統計
- つよバハ青箱ドロップ確率の統計分析
- ヒヒイロカネドロップ確率の統計分析
- 複合事象（青箱かつヒヒ）の統計分析
- 期待値、標準偏差、パーセンタイルの計算
- 累計データと月データの個別分析
- グラフ出力（二項分布の可視化）

## セットアップ

### 1. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、必要な値を設定してください：

```bash
cp .env.example .env
```

**Google OAuth設定（必須）:**
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. OAuth 2.0クライアントIDを作成
3. 承認済みのリダイレクトURIに追加：
   - `http://localhost:8080/auth/google/callback`（開発環境）
   - `https://gbf-guild-mng.com/auth/google/callback`（本番環境）
4. `.env`にクライアントIDとシークレットを設定

**メール送信設定（オプション）:**
- SendGrid、AWS SES、Gmail API等を使用する場合は`auth_utils.py`の`send_verification_email`関数を実装してください

### 2. 仮想環境の作成と有効化

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
  sheet_url: "https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID"
  sheet_name: "団員管理"

guild:
  name: "あなたの団名"

# 団員管理設定
member_stats:
  # グラブル攻略データベースのURL（団員スクレイピング時に使用）
  guild_database_url: "https://gbfdata.com/ja"

# ドロップ統計設定
drop_stats:
  # gbfdrop.jpのドロップ記録ページURL（スクレイピング対象）
  drop_record_url: "https://gbfdrop.jp/record"
  
  # ログイン情報
  login:
    username: "your_email@example.com"
    password: "your_password"
  
  # ドロップ確率設定
  blue_chest_probability: 0.1            # つよバハ青箱ドロップ確率
  hihi_probability: 0.02                  # 青箱からのヒヒイロカネドロップ確率（条件付き確率）
  
  # 出力設定
  output_directory: "./graphs"           # グラフの保存先ディレクトリ
```

### 4. Google認証情報の設定（団員管理機能を使用する場合）

1. Google Cloud Consoleでサービスアカウントを作成
2. `credentials.json` をダウンロードしてプロジェクトルートに配置
3. スプレッドシートにサービスアカウントのメールアドレスを共有

## 実行方法

### 団員管理

```powershell
python member_main.py
```

または `団員管理.bat` をダブルクリック

### ドロップ統計

```powershell
python drop_main.py
```

または `ドロップ統計.bat` をダブルクリック

実行結果：
- コンソールに統計情報が表示されます
- グラフが `output_directory` で指定したフォルダに `drop_distribution_YYYYMMDD.png` で保存されます

## 出力ファイル

### ログファイル
- 団員管理: `member.log`
- ドロップ統計: `drop.log`

### グラフファイル
- ドロップ統計: `output/drop_distribution_YYYYMMDD.png`
  - 上段：累計データの分析グラフ（青箱、ヒヒ、複合事象）
  - 下段：月データの分析グラフ（青箱、ヒヒ、複合事象）

## ドロップ統計について

### 分析内容

#### 青箱ドロップ率
- 設定した青箱ドロップ確率をもとに、実績値とのズレを評価
- パーセンタイルが高い → 期待値より良い運
- パーセンタイルが低い → 期待値より悪い運

#### ヒヒドロップ率（条件付き）
- 青箱からのヒヒドロップ確率を分析
- 青箱が出た場合のみカウント

#### 複合事象
- 青箱かつヒヒの両方がドロップする確率を分析

### グラフの読み方

- **青い棒グラフ** - 二項分布の確率分布
- **緑の点線** - 期待値
- **赤い実線** - 実績値

## トラブルシューティング

### ドロップ統計がエラーになる場合

1. `config.yaml` のログイン情報が正しいか確認
2. gbfdrop.jpにアクセスできるか確認
3. ネットワーク接続を確認

### グラフが保存されない場合

1. `output_directory` で指定したフォルダが存在するか確認
2. フォルダへの書き込み権限があるか確認

## 注意事項

- `config.yaml` と `credentials.json` は機密情報のため、Gitに含めないでください（`.gitignore`に設定済み）
- Chromeブラウザが必要です（Selenium Managerが自動でChromeDriverをインストール）
- ドロップ統計は定期的に実行して、月ごとのデータを記録することで傾向を分析できます

## 仕様

### 確率計算

複合事象（青箱かつヒヒ）の確率：
```
P(PかつQ) = P(青箱) × P(ヒヒ|青箱) = blue_chest_prob × hihi_prob
```

## プロジェクト構造

```
grablu/
├── web_app.py              # メインアプリケーション（ホーム、履歴、エラーハンドラー）
├── config/                 # 設定管理（Phase 3で追加）
│   └── settings.py        # Pydantic Settings
├── exceptions/             # カスタム例外（Phase 3で追加）
│   ├── base.py            # 基底例外
│   ├── auth.py            # 認証例外
│   ├── guild.py           # 団例外
│   ├── member.py          # 団員例外
│   └── scraping.py        # スクレイピング例外
├── schemas/                # 型定義（Phase 3で追加）
│   ├── auth.py            # 認証スキーマ
│   ├── guild.py           # 団スキーマ
│   ├── member.py          # 団員スキーマ
│   └── scraping.py        # スクレイピングスキーマ
├── middleware/             # ミドルウェア（Phase 3で追加）
│   ├── logging.py         # リクエストロギング
│   └── error_handler.py   # エラーハンドラー
├── routers/                # エンドポイントルーター（機能別分割）
│   ├── auth.py            # 認証（ログイン、登録、OAuth）
│   ├── guilds.py          # 団管理（登録、検索、追加）
│   ├── members.py         # 団員管理（リスト、比較、イベントAPI）
│   ├── scraping.py        # データ取得処理
│   └── admin.py           # 管理者機能（メールテスト）
├── services/               # ビジネスロジック層（Phase 2で追加）
│   ├── scraping_service.py    # スクレイピングロジック
│   ├── member_service.py      # メンバー管理ロジック
│   └── notification_service.py # 通知機能（メール送信）
├── models.py              # データベースモデル
├── database.py            # DB接続・初期化
├── member_tracker.py      # 団員履歴管理
├── guild_manager.py       # 団管理ロジック
├── scraper.py             # Webスクレイピング
├── auth_utils.py          # 認証ユーティリティ
├── config.py              # 設定管理
├── utils.py               # 共通ユーティリティ
├── templates/             # HTMLテンプレート
├── tests/                 # テストコード
└── docker-compose.yml     # Docker構成
```

**リファクタリング履歴:**
- 2026-02-06: Phase 1完了 - web_app.py（1033行）を6ファイルに分割
- 2026-02-06: Phase 2完了 - サービス層導入、ビジネスロジック分離
- 2026-02-07: Phase 3完了 - 設定管理、エラーハンドリング、型ヒント、ミドルウェア統合
- 詳細: [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md)

## ライセンス

個人使用のみ
