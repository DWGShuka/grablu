# Grablu Web Application - AWS EC2 デプロイ手順書

## 概要
Grablu 団員管理システムをAWS EC2上にデプロイする手順です。

## 前提条件
- AWSアカウントを持っていること
- 基本的なコマンドライン操作ができること

---

## 1. EC2インスタンスの作成

### 1.1 AWSマネジメントコンソールにログイン
https://console.aws.amazon.com/

### 1.2 EC2インスタンスを起動
1. EC2ダッシュボードから「インスタンスを起動」をクリック
2. 以下の設定を選択:

**基本設定:**
- 名前: `grablu-web-app`
- AMI: `Ubuntu Server 22.04 LTS (HVM), SSD Volume Type`
- インスタンスタイプ: `t2.micro`（無料枠対象）

**キーペア:**
- 新しいキーペアを作成 or 既存のものを選択
- 名前: `grablu-key`
- ファイル形式: `.pem`（Mac/Linux） or `.ppk`（Windows）
- **重要: ダウンロードしたキーは安全な場所に保存**

**ネットワーク設定:**
- VPC: デフォルトVPC
- パブリックIPの自動割り当て: 有効化
- セキュリティグループ:
  - SSH（ポート22）: マイIP
  - HTTP（ポート80）: どこからでも (0.0.0.0/0)
  - カスタムTCP（ポート8000）: どこからでも (0.0.0.0/0)

**ストレージ:**
- 8 GiB gp3（無料枠）

### 1.3 インスタンス起動
「インスタンスを起動」をクリック

---

## 2. EC2への接続

### 2.1 パブリックIPアドレスを確認
EC2ダッシュボードでインスタンスの「パブリックIPv4アドレス」をメモ

### 2.2 SSHで接続
```bash
# キーの権限を変更（初回のみ）
chmod 400 grablu-key.pem

# EC2に接続
ssh -i grablu-key.pem ubuntu@<パブリックIPアドレス>
```

---

## 3. サーバーのセットアップ

### 3.1 システムパッケージの更新
```bash
sudo apt update
sudo apt upgrade -y
```

### 3.2 Dockerのインストール
```bash
# 必要なパッケージをインストール
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# DockerのGPGキーを追加
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Dockerリポジトリを追加
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Dockerをインストール
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Dockerを起動
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker ubuntu

# 再ログインして反映（一旦exitして再接続）
exit
ssh -i grablu-key.pem ubuntu@<パブリックIPアドレス>
```

### 3.3 Gitのインストール
```bash
sudo apt install -y git
```

---

## 4. アプリケーションのデプロイ

### 4.1 リポジトリのクローン
```bash
cd ~
git clone <あなたのGitリポジトリURL> grablu
cd grablu
```

### 4.2 設定ファイルの配置
ローカルからEC2に設定ファイルを転送:

```bash
# ローカル側で実行（別のターミナル）
scp -i grablu-key.pem config.yaml ubuntu@<パブリックIPアドレス>:~/grablu/
scp -i grablu-key.pem credentials.json ubuntu@<パブリックIPアドレス>:~/grablu/
```

### 4.3 認証情報の設定
EC2上で環境変数ファイルを作成:

```bash
cd ~/grablu
nano .env
```

以下を記入:
```
USERNAME=admin
PASSWORD=<強力なパスワード>
```

保存: `Ctrl + O` → Enter → `Ctrl + X`

### 4.4 Dockerイメージのビルド
```bash
docker build -t grablu-web .
```

### 4.5 コンテナの起動
```bash
docker run -d \
  --name grablu-app \
  -p 8000:8000 \
  -v ~/grablu/members.json:/app/members.json \
  -v ~/grablu/config.yaml:/app/config.yaml \
  -v ~/grablu/credentials.json:/app/credentials.json \
  --env-file .env \
  --restart unless-stopped \
  grablu-web
```

---

## 5. 動作確認

### 5.1 ログの確認
```bash
docker logs grablu-app
```

### 5.2 Webブラウザでアクセス
```
http://<パブリックIPアドレス>:8000
```

- ユーザー名: `admin`
- パスワード: 設定したパスワード

---

## 6. 運用コマンド

### アプリケーションの再起動
```bash
docker restart grablu-app
```

### アプリケーションの停止
```bash
docker stop grablu-app
```

### アプリケーションの更新
```bash
cd ~/grablu
git pull
docker stop grablu-app
docker rm grablu-app
docker build -t grablu-web .
docker run -d --name grablu-app -p 8000:8000 -v ~/grablu/members.json:/app/members.json -v ~/grablu/config.yaml:/app/config.yaml -v ~/grablu/credentials.json:/app/credentials.json --env-file .env --restart unless-stopped grablu-web
```

### ログの確認
```bash
docker logs -f grablu-app
```

### members.jsonのバックアップ
```bash
cp ~/grablu/members.json ~/grablu/members.json.backup.$(date +%Y%m%d)
```

---

## 7. セキュリティ強化（推奨）

### 7.1 ファイアウォールの設定
```bash
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

### 7.2 自動アップデートの有効化
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 8. コスト見積もり

### 無料枠利用時（初年度）
- EC2 t2.micro: **無料**（月750時間まで）
- データ転送: ほぼ無料（利用頻度が低いため）

### 無料枠終了後
- EC2 t2.micro: 約 **$8-10/月**
- データ転送: 約 **$1/月**
- **合計: 約 $10/月**

---

## トラブルシューティング

### 接続できない場合
1. セキュリティグループでポート8000が開いているか確認
2. `docker logs grablu-app` でエラーを確認
3. `docker ps -a` でコンテナが起動しているか確認

### Chromeが起動しない場合
```bash
docker exec -it grablu-app google-chrome --version
```
でChromeがインストールされているか確認

---

## お問い合わせ
問題が発生した場合は、ログファイル（`docker logs grablu-app`）を確認してください。
