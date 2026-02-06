# Grablu テストガイド

## クイックスタート

### 基本的なテスト実行

```bash
# パスワードハッシュ化などの単純なテスト
pytest tests/test_models.py::TestUserModel::test_password_hashing -v

# 全テスト実行（DB接続不要のもののみ）
pytest tests/test_models.py::TestUserModel::test_password_hashing tests/test_models.py::TestUserModel::test_bcrypt_72_byte_limit -v
```

### データベースを使うテスト

データベースを使うテストを実行する場合、PostgreSQLが必要です：

```bash
# テスト用DBを起動
docker run -d \
  --name grablu-test-db \
  -e POSTGRES_DB=grablu_test \
  -e POSTGRES_USER=grablu \
  -e POSTGRES_PASSWORD=grablu2026 \
  -p 5432:5432 \
  postgres:16-alpine

# 環境変数を設定してテスト実行（PowerShell）
$env:DATABASE_URL="postgresql://grablu:grablu2026@localhost:5432/grablu_test"
pytest tests/ -v

# 環境変数を設定してテスト実行（Bash）
export DATABASE_URL=postgresql://grablu:grablu2026@localhost:5432/grablu_test
pytest tests/ -v
```

### カバレッジ付きテスト

```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

## テストファイル構成

```
tests/
├── __init__.py
├── conftest.py              # テスト設定とフィクスチャ
├── test_models.py           # Userモデルのテスト
├── test_member_tracker.py   # MemberTrackerのテスト
└── test_guild_manager.py    # GuildManagerのテスト
```

## GitHub Actions

GitHubにプッシュすると自動的にテストが実行されます：

- `.github/workflows/test.yml` - CIワークフロー定義
- PostgreSQL 16をサービスとして起動
- Python 3.12でテスト実行
- flake8によるLinting
- pytestによるテスト
- コードカバレッジの計測

## トラブルシューティング

### "ModuleNotFoundError: No module named 'xxx'"

```bash
# 依存関係を再インストール
pip install -r requirements.txt
pip install pytest pytest-cov flake8
```

### "connection refused" / データベース接続エラー

```bash
# PostgreSQLが起動しているか確認
docker ps | grep postgres

# 起動していない場合
docker run -d --name grablu-test-db -e POSTGRES_DB=grablu_test -e POSTGRES_USER=grablu -e POSTGRES_PASSWORD=grablu2026 -p 5432:5432 postgres:16-alpine
```

### テストDBをクリーンアップ

```bash
# コンテナ停止・削除
docker stop grablu-test-db
docker rm grablu-test-db
```
