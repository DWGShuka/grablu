"""データベースモデル"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from passlib.context import CryptContext

# パスワードハッシュ化
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """ユーザー情報"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)  # 表示名（重複可能）
    email = Column(String, unique=True, index=True, nullable=False)  # ログインID（ユニーク）
    hashed_password = Column(String, nullable=True)  # OAuth登録時はNULL可能
    is_active = Column(Boolean, default=False)  # メール認証後にTrue
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)  # メール認証済みフラグ
    verification_token = Column(String, nullable=True)  # メール認証トークン
    oauth_provider = Column(String, nullable=True)  # OAuth プロバイダー (google, etc)
    oauth_id = Column(String, nullable=True, unique=True)  # OAuth ID
    active_guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=True)  # アクティブな団
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # リレーション
    active_guild = relationship("Guild", foreign_keys=[active_guild_id])
    guilds = relationship("Guild", foreign_keys="Guild.user_id", back_populates="owner")
    
    def verify_password(self, password: str) -> bool:
        """パスワード検証"""
        if not self.hashed_password:
            return False
        # bcryptは72文字まで処理可能（実際にはバイト数制限だが、安全のため文字数で制限）
        password_limited = password[:72] if len(password) > 72 else password
        return pwd_context.verify(password_limited, self.hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """パスワードハッシュ化"""
        # bcryptは72文字まで処理可能（実際にはバイト数制限だが、安全のため文字数で制限）
        password_limited = password[:72] if len(password) > 72 else password
        return pwd_context.hash(password_limited)


class Guild(Base):
    """団情報"""
    __tablename__ = "guilds"
    
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, index=True, nullable=False)  # gbfdataの団ID（ユニーク制約削除）
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 所有ユーザー
    is_active = Column(Integer, default=0)  # 0 or 1 (SQLiteにbool型がない)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーション
    owner = relationship("User", foreign_keys=[user_id], back_populates="guilds")
    members = relationship("Member", back_populates="guild", cascade="all, delete-orphan")
    event_data = relationship("EventData", back_populates="guild", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'guild_id', name='uix_user_guild'),
    )


class Member(Base):
    """団員情報"""
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(String, unique=True, index=True, nullable=False)  # プレイヤーID
    current_name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    
    # リレーション
    guild = relationship("Guild", back_populates="members")
    name_history = relationship("NameHistory", back_populates="member", cascade="all, delete-orphan")
    rankings = relationship("MemberRanking", back_populates="member", cascade="all, delete-orphan")


class NameHistory(Base):
    """名前変更履歴"""
    __tablename__ = "name_history"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    old_name = Column(String, nullable=False)
    new_name = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.now)
    
    # リレーション
    member = relationship("Member", back_populates="name_history")


class EventData(Base):
    """イベント情報"""
    __tablename__ = "event_data"
    
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    event_number = Column(Integer, nullable=False)
    fetched_at = Column(DateTime, default=datetime.now)
    
    # リレーション
    guild = relationship("Guild", back_populates="event_data")
    rankings = relationship("MemberRanking", back_populates="event", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'event_number', name='uix_guild_event'),
    )


class MemberRanking(Base):
    """団員のイベントごとのランキング"""
    __tablename__ = "member_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("event_data.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    rank = Column(String, nullable=False)  # 順位（文字列形式: "1位", "2位"など）
    
    # リレーション
    event = relationship("EventData", back_populates="rankings")
    member = relationship("Member", back_populates="rankings")
    
    __table_args__ = (
        UniqueConstraint('event_id', 'member_id', name='uix_event_member'),
    )
