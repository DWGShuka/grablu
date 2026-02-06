"""ギルド管理クラス - データベース版"""
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from models import Guild, User

logger = logging.getLogger(__name__)

# 1団あたりの最大メンバー数
MAX_GUILD_MEMBERS = 30


class GuildManager:
    """ギルド情報の管理クラス（DB版）"""
    
    def __init__(self, db: Session, user_id: int = None):
        """
        Args:
            db: データベースセッション
            user_id: ユーザーID
        """
        self.db = db
        self.user_id = user_id
        self.user = None
        if user_id:
            self.user = db.query(User).filter(User.id == user_id).first()
    
    def add_guild(self, guild_id: str, guild_name: str) -> bool:
        """団を追加（ユーザーが未所属の場合のみ）"""
        # ユーザーが既に団に所属しているかチェック
        if self.user and self.user.guild_id:
            logger.info(f"ユーザーは既に団に所属しています")
            return False
        
        # 既に存在する団かチェック
        existing_guild = self.db.query(Guild).filter(Guild.guild_id == guild_id).first()
        
        if existing_guild:
            # 既存の団に参加
            member_count = self.db.query(User).filter(User.guild_id == existing_guild.id).count()
            if member_count >= MAX_GUILD_MEMBERS:
                logger.warning(f"団は満員です（{MAX_GUILD_MEMBERS}人）: {guild_name}")
                return False
            
            # ユーザーを団に所属させる
            if self.user:
                self.user.guild_id = existing_guild.id
                self.db.commit()
                logger.info(f"既存の団に参加しました: {guild_name} (メンバー: {member_count + 1}/{MAX_GUILD_MEMBERS})")
            return True
        else:
            # 新規団を作成
            guild = Guild(
                guild_id=guild_id,
                name=guild_name
            )
            self.db.add(guild)
            self.db.flush()  # IDを取得
            
            # ユーザーを団に所属させる
            if self.user:
                self.user.guild_id = guild.id
            
            self.db.commit()
            logger.info(f"団を作成しました: {guild_name} (ID: {guild_id})")
            return True
    
    def get_active_guild(self) -> Optional[Guild]:
        """ユーザーの所属団を取得"""
        if self.user and self.user.guild:
            return self.user.guild
        return None
    
    def get_all_guilds(self) -> List[Guild]:
        """全ての団情報を取得（管理者用）"""
        return self.db.query(Guild).all()
    
    def is_registered(self) -> bool:
        """ユーザーが団に所属しているか確認"""
        return self.user and self.user.guild_id is not None
    
    def get_guild_by_id(self, guild_id: str) -> Optional[Guild]:
        """guild_idで団情報を取得"""
        return self.db.query(Guild).filter(Guild.guild_id == guild_id).first()
    
    def get_guild_members(self, guild: Guild) -> List[User]:
        """団のメンバー一覧を取得"""
        return self.db.query(User).filter(User.guild_id == guild.id).all()
    
    def leave_guild(self) -> bool:
        """団から脱退"""
        if self.user and self.user.guild_id:
            old_guild = self.user.guild
            self.user.guild_id = None
            self.db.commit()
            logger.info(f"団から脱退しました: {old_guild.name if old_guild else 'Unknown'}")
            return True
        return False
