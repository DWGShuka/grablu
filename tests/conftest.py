"""テスト設定とフィクスチャ"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models import User, Guild, Member

# テスト用のデータベースURL
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://grablu:grablu2026@localhost:5432/grablu_test"
)


@pytest.fixture(scope="function")
def db_engine():
    """テスト用のデータベースエンジンを作成"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """テスト用のデータベースセッションを作成"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """テスト用ユーザーを作成"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=User.get_password_hash("testpass123"),
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_guild(db_session):
    """テスト用団を作成"""
    guild = Guild(
        guild_id="test_guild_001",
        name="テスト団",
        is_active=1
    )
    db_session.add(guild)
    db_session.commit()
    db_session.refresh(guild)
    return guild


@pytest.fixture
def test_member(db_session, test_guild):
    """テスト用団員を作成"""
    member = Member(
        guild_id=test_guild.id,
        player_id="12345678",
        current_name="テストプレイヤー"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member
