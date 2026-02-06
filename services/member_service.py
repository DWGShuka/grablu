"""
メンバー管理サービス
団員データの取得と分析に関するビジネスロジック
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Guild, NameHistory, Member
from guild_manager import GuildManager
from member_tracker import MemberTracker

logger = logging.getLogger(__name__)


@dataclass
class MemberListResult:
    """団員リスト取得結果"""
    guild_info: Dict  # guild_name, guild_id
    events: List[Dict]  # 全イベントリスト
    latest_event: Optional[Dict] = None  # 最新イベントデータ


@dataclass
class MemberCompareResult:
    """団員比較分析結果"""
    guild_info: Dict  # guild_name, guild_id
    events: List[Dict]  # 全イベントリスト


class MemberService:
    """団員管理サービス"""
    
    def __init__(self, db: Session, user_id: int):
        """
        Args:
            db: データベースセッション
            user_id: ユーザーID
        """
        self.db = db
        self.user_id = user_id
        self.guild_manager = GuildManager(db, user_id)
        self.active_guild: Optional[Guild] = None
        self.tracker: Optional[MemberTracker] = None
    
    def _validate_and_setup(self) -> Guild:
        """団情報の検証とTrackerのセットアップ
        
        Returns:
            Guild: アクティブな団情報
            
        Raises:
            ValueError: 団が登録されていない場合
        """
        self.active_guild = self.guild_manager.get_active_guild()
        if not self.active_guild:
            raise ValueError("団が登録されていません")
        
        self.tracker = MemberTracker(self.db, self.active_guild.id)
        return self.active_guild
    
    def _get_guild_info_dict(self, guild: Guild) -> Dict:
        """団情報を辞書形式で返す
        
        Args:
            guild: 団オブジェクト
            
        Returns:
            団名とIDを含む辞書
        """
        return {
            "guild_name": guild.name,
            "guild_id": guild.guild_id
        }
    
    def get_member_list_data(self) -> MemberListResult:
        """団員リスト表示用のデータを取得
        
        Returns:
            MemberListResult: 団員リストデータ
            
        Raises:
            ValueError: 団が登録されていない場合
        """
        guild = self._validate_and_setup()
        
        # 全イベントリストを取得
        events = self.tracker.get_all_events()
        
        # 最新イベントのデータを取得
        latest_event_data = None
        if events:
            latest_event_data = self.tracker.get_event_data(events[0]["event_number"])
        
        return MemberListResult(
            guild_info=self._get_guild_info_dict(guild),
            events=events,
            latest_event=latest_event_data
        )
    
    def get_member_compare_data(self) -> MemberCompareResult:
        """団員比較分析用のデータを取得
        
        Returns:
            MemberCompareResult: 比較分析データ
            
        Raises:
            ValueError: 団が登録されていない場合
        """
        guild = self._validate_and_setup()
        
        # 全イベントリストを取得
        events = self.tracker.get_all_events()
        
        return MemberCompareResult(
            guild_info=self._get_guild_info_dict(guild),
            events=events
        )
    
    def get_event_members_data(self, event_number: int) -> Dict:
        """特定イベントの団員データを取得
        
        Args:
            event_number: イベント番号
            
        Returns:
            イベントデータ
            
        Raises:
            ValueError: 団が登録されていない、またはイベントデータが見つからない場合
        """
        guild = self._validate_and_setup()
        
        event_data = self.tracker.get_event_data(event_number)
        
        if not event_data:
            raise ValueError(f"イベント番号{event_number}のデータが見つかりません")
        
        return event_data
    
    def get_name_history(self, member_id: int) -> List[NameHistory]:
        """特定団員の名前変更履歴を取得
        
        Args:
            member_id: 団員ID
            
        Returns:
            名前変更履歴のリスト
        """
        return self.db.query(NameHistory).filter(
            NameHistory.member_id == member_id
        ).order_by(NameHistory.changed_at.desc()).all()
    
    def get_member_by_player_id(self, player_id: str) -> Optional[Member]:
        """プレイヤーIDから団員情報を取得
        
        Args:
            player_id: プレイヤーID
            
        Returns:
            団員情報、見つからない場合はNone
        """
        guild = self._validate_and_setup()
        
        return self.db.query(Member).filter(
            Member.guild_id == guild.id,
            Member.player_id == player_id
        ).first()
    
    def search_members(
        self,
        search_name: Optional[str] = None,
        search_player_id: Optional[str] = None
    ) -> List[Member]:
        """団員を検索
        
        Args:
            search_name: 検索する団員名（部分一致）
            search_player_id: 検索するプレイヤーID（部分一致）
            
        Returns:
            検索結果の団員リスト
        """
        guild = self._validate_and_setup()
        
        query = self.db.query(Member).filter(Member.guild_id == guild.id)
        
        if search_name:
            query = query.filter(Member.current_name.ilike(f"%{search_name}%"))
        
        if search_player_id:
            query = query.filter(Member.player_id.ilike(f"%{search_player_id}%"))
        
        return query.order_by(Member.last_seen.desc()).all()
