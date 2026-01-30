"""データベース接続設定"""
import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# 環境変数からDB接続情報を取得
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://grablu:grablu2026@db:5432/grablu"
)

logger.info(f"Database URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], '***')}")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 接続確認
    pool_size=5,
    max_overflow=10,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """データベースセッションを取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """データベースを初期化"""
    logger.info("データベース初期化を開始します...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ データベーステーブルの作成が完了しました")
        
        # 作成されたテーブル一覧を表示
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✓ 作成されたテーブル: {', '.join(tables)}")
    except Exception as e:
        logger.error(f"✗ データベース初期化エラー: {e}")
        raise
