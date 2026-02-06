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

# ログにはホスト情報のみ出力（パスワードを含めない）
try:
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    safe_db_info = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
    logger.info(f"Database connection: {safe_db_info}")
except Exception:
    logger.info("Database connection configured")

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
        # 既存テーブルのスキーマを確認して必要なカラムを追加
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        # usersテーブルが存在する場合、必要なカラムを追加
        if 'users' in inspector.get_table_names():
            existing_columns = {col['name'] for col in inspector.get_columns('users')}
            required_columns = {
                'email_verified': 'BOOLEAN DEFAULT FALSE',
                'verification_token': 'VARCHAR',
                'oauth_provider': 'VARCHAR',
                'oauth_id': 'VARCHAR UNIQUE',
                'active_guild_id': 'INTEGER'
            }
            
            with engine.connect() as conn:
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        logger.info(f"カラムを追加: users.{col_name}")
                        # PostgreSQLではUNIQUE制約を別途追加
                        if 'UNIQUE' in col_def:
                            col_def_without_unique = col_def.replace(' UNIQUE', '')
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def_without_unique}"))
                            # oauth_idのみUNIQUE制約を追加（NULL許容）
                            if col_name == 'oauth_id':
                                try:
                                    conn.execute(text(f"ALTER TABLE users ADD CONSTRAINT uq_users_{col_name} UNIQUE ({col_name})"))
                                except Exception:
                                    pass  # 制約が既に存在する場合はスキップ
                        else:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
        
        # guildsテーブルが存在する場合、必要なカラムを追加
        if 'guilds' in inspector.get_table_names():
            existing_columns = {col['name'] for col in inspector.get_columns('guilds')}
            if 'user_id' not in existing_columns:
                logger.info("カラムを追加: guilds.user_id")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE guilds ADD COLUMN user_id INTEGER"))
                    conn.commit()
            
            # guild_idのユニーク制約を削除（既に存在する場合）
            try:
                with engine.connect() as conn:
                    # PostgreSQL用
                    conn.execute(text("ALTER TABLE guilds DROP CONSTRAINT IF EXISTS guilds_guild_id_key"))
                    conn.commit()
                    logger.info("guilds.guild_idのユニーク制約を削除しました（マルチテナント対応）")
            except Exception:
                pass  # 制約が存在しない場合はスキップ
        
        # テーブル作成（存在しない場合のみ）
        Base.metadata.create_all(bind=engine)
        logger.info("✓ データベーステーブルの作成が完了しました")
        
        # 作成されたテーブル一覧を表示
        tables = inspector.get_table_names()
        logger.info(f"✓ 作成されたテーブル: {', '.join(tables)}")
    except Exception as e:
        logger.error(f"✗ データベース初期化エラー: {e}")
        raise
