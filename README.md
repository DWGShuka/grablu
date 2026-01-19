# Grablu - グラブル団員管理・ドロップ統計ツール

Webスクレイピングでグラブルの団員データを取得し、Google Sheetsに自動記録するツールです。  
さらに、ドロップ確率を統計分析し、期待値とパーセンタイル評価を行う機能を搭載しています。

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

## ライセンス

個人使用のみ
