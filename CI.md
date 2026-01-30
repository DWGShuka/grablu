# Grablu CI/CD

このプロジェクトはGitHub Actionsを使用した継続的インテグレーション（CI）を実装しています。

## 自動テスト

プルリクエストやmain/developブランチへのプッシュ時に自動的にテストが実行されます。

### テスト内容

1. **Linting (flake8)**
   - Python構文エラーのチェック
   - コードスタイルの検証

2. **Unit Tests (pytest)**
   - Userモデルのテスト
   - MemberTrackerのテスト
   - GuildManagerのテスト
   - パスワードハッシュ化のテスト
   - データベース操作のテスト

3. **コードカバレッジ**
   - テストカバレッジの測定
   - Codecovへのアップロード

### ローカルでのテスト実行

```bash
# テスト用の依存関係をインストール
pip install pytest pytest-cov flake8

# Lintingを実行
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --exclude=.venv,__pycache__,.git

# テストを実行
pytest tests/ -v

# カバレッジ付きでテストを実行
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

### テスト用データベース

テストはPostgreSQLを使用します。ローカルで実行する場合：

```bash
# Dockerでテスト用DBを起動
docker run -d \
  --name grablu-test-db \
  -e POSTGRES_DB=grablu_test \
  -e POSTGRES_USER=grablu \
  -e POSTGRES_PASSWORD=grablu2026 \
  -p 5432:5432 \
  postgres:16-alpine

# 環境変数を設定
export DATABASE_URL=postgresql://grablu:grablu2026@localhost:5432/grablu_test

# テスト実行
pytest tests/ -v
```

## CI/CDワークフロー

### test.yml

- トリガー: push/PR to main, develop
- Python 3.12
- PostgreSQL 16
- flake8によるLinting
- pytestによるテスト実行
- コードカバレッジの測定

## バッジ

プロジェクトのREADMEにCIステータスバッジを追加できます：

```markdown
![CI Tests](https://github.com/yourusername/grablu/workflows/CI%20Tests/badge.svg)
[![codecov](https://codecov.io/gh/yourusername/grablu/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/grablu)
```

## トラブルシューティング

### テストが失敗する場合

1. データベース接続を確認
2. 環境変数が正しく設定されているか確認
3. 依存関係が最新かチェック

```bash
pip install -r requirements-web.txt --upgrade
```

### カバレッジが低い場合

```bash
# カバレッジレポートをHTML形式で確認
pytest tests/ --cov=. --cov-report=html
# ブラウザでhtmlcov/index.htmlを開く
```
