# Grablu Web Application - Docker Image
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# 環境変数の設定
ENV DEBIAN_FRONTEND=noninteractive

# システムパッケージのインストール（Chrome + 依存関係）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# アプリケーションファイルをコピー
COPY . .

# ポート公開
EXPOSE 8000

# アプリケーション起動
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
