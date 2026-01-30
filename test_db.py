"""データベース接続テスト"""
import sys
from sqlalchemy import create_engine, text
from config import Config

print("1. 設定読み込み開始")
db_url = Config.get_database_url()
print(f"2. DB URL: {db_url.replace(db_url.split(':')[2].split('@')[0], '***')}")

print("3. エンジン作成開始")
engine = create_engine(db_url, connect_args={"connect_timeout": 5})
print("4. エンジン作成完了")

print("5. 接続テスト開始")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"6. 接続成功: {result.scalar()}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print("7. テーブル作成開始")
from models import Base
Base.metadata.create_all(engine)
print("8. テーブル作成完了")
