"""データベース接続設定"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config import settings

logger = logging.getLogger(__name__)

# DATABASE_URLを設定から取得
DATABASE_URL = settings.database_url

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
                'guild_id': 'INTEGER'
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
                
                # active_guild_id を guild_id にリネーム（存在する場合）
                if 'active_guild_id' in existing_columns:
                    if 'guild_id' in existing_columns:
                        # 両方存在する場合は active_guild_id を削除
                        logger.info("カラムを削除: users.active_guild_id（guild_idが既に存在）")
                        conn.execute(text("ALTER TABLE users DROP COLUMN active_guild_id"))
                    else:
                        # active_guild_id のみ存在する場合はリネーム
                        logger.info("カラムをリネーム: users.active_guild_id -> guild_id")
                        conn.execute(text("ALTER TABLE users RENAME COLUMN active_guild_id TO guild_id"))
                    conn.commit()
        
        # guildsテーブルが存在する場合、不要なカラムを削除
        if 'guilds' in inspector.get_table_names():
            existing_columns = {col['name'] for col in inspector.get_columns('guilds')}
            
            # user_idカラムを削除（存在する場合）
            if 'user_id' in existing_columns:
                logger.info("カラムを削除: guilds.user_id（共有団モデルに変更）")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE guilds DROP COLUMN user_id"))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"カラム削除エラー: {e}")
            
            # is_activeカラムを削除（不要になった）
            if 'is_active' in existing_columns:
                logger.info("カラムを削除: guilds.is_active（ユーザー所属で判定）")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE guilds DROP COLUMN is_active"))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"カラム削除エラー: {e}")
            
            # guild_idにユニーク制約を追加（削除されていた場合）
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE guilds ADD CONSTRAINT guilds_guild_id_key UNIQUE (guild_id)"))
                    conn.commit()
                    logger.info("guilds.guild_idにユニーク制約を追加しました")
            except Exception:
                pass  # 制約が既に存在する場合はスキップ
        
        # membersテーブルにis_current_memberカラムを追加
        if 'members' in inspector.get_table_names():
            existing_columns = {col['name'] for col in inspector.get_columns('members')}
            
            if 'is_current_member' not in existing_columns:
                logger.info("カラムを追加: members.is_current_member")
                with engine.connect() as conn:
                    # デフォルトTrueで追加（既存メンバーは全て現在のメンバーとみなす）
                    conn.execute(text("ALTER TABLE members ADD COLUMN is_current_member BOOLEAN DEFAULT TRUE"))
                    conn.commit()
        
        # テーブル作成（存在しない場合のみ）
        Base.metadata.create_all(bind=engine)
        logger.info("✓ データベーステーブルの作成が完了しました")
        
        # 作成されたテーブル一覧を表示
        tables = inspector.get_table_names()
        logger.info(f"✓ 作成されたテーブル: {', '.join(tables)}")
    except Exception as e:
        logger.error(f"✗ データベース初期化エラー: {e}")
        raise
