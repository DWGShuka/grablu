"""ギルド管理クラス - データベース版"""
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from models import Guild

logger = logging.getLogger(__name__)


class GuildManager:
    """ギルド情報の管理クラス（DB版）"""
    
    def __init__(self, db: Session, user_id: int = None):
        """
        Args:
            db: データベースセッション
            user_id: ユーザーID（マルチテナント対応）
        """
        self.db = db
        self.user_id = user_id
    
    def add_guild(self, guild_id: str, guild_name: str) -> bool:
        """団を追加"""
        # 既に存在するかチェック（同じユーザーの）
        existing = self.db.query(Guild).filter(
            Guild.guild_id == guild_id,
            Guild.user_id == self.user_id
        ).first()
        if existing:
            logger.info(f"団は既に登録済みです: {guild_name}")
            return False
        
        # 新規登録
        guild = Guild(
            guild_id=guild_id,
            name=guild_name,
            user_id=self.user_id,
            is_active=0
        )
        self.db.add(guild)
        
        # このユーザーの初回登録の場合はアクティブに設定
        user_guild_count = self.db.query(Guild).filter(Guild.user_id == self.user_id).count()
        if user_guild_count == 0:
            guild.is_active = 1
        
        self.db.commit()
        logger.info(f"団を登録しました: {guild_name} (ID: {guild_id}, ユーザー: {self.user_id})")
        return True
    
    def get_active_guild(self) -> Optional[Guild]:
        """アクティブな団情報を取得"""
        return self.db.query(Guild).filter(
            Guild.is_active == 1,
            Guild.user_id == self.user_id
        ).first()
    
    def set_active_guild(self, guild_id: str) -> bool:
        """アクティブな団を設定"""
        # このユーザーの既存のアクティブ団を非アクティブに
        self.db.query(Guild).filter(Guild.user_id == self.user_id).update({Guild.is_active: 0})
        
        # 指定の団をアクティブに
        guild = self.db.query(Guild).filter(
            Guild.guild_id == guild_id,
            Guild.user_id == self.user_id
        ).first()
        if guild:
            guild.is_active = 1
            self.db.commit()
            logger.info(f"アクティブ団を設定: {guild.name}")
            return True
        return False
    
    def get_all_guilds(self) -> List[Guild]:
        """全ての団情報を取得（このユーザーの）"""
        return self.db.query(Guild).filter(Guild.user_id == self.user_id).all()
    
    def is_registered(self) -> bool:
        """団が登録済みか確認"""
        return self.db.query(Guild).filter(Guild.user_id == self.user_id).count() > 0
    
    def get_guild_by_id(self, guild_id: str) -> Optional[Guild]:
        """guild_idで団情報を取得"""
        return self.db.query(Guild).filter(
            Guild.guild_id == guild_id,
            Guild.user_id == self.user_id
        ).first()
