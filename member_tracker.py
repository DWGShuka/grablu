"""団員追跡システム - データベース版"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from models import Guild, Member, NameHistory, EventData, MemberRanking

logger = logging.getLogger(__name__)


class MemberTracker:
    """団員の履歴を管理するクラス（DB版）"""
    
    def __init__(self, db: Session, guild_id: int):
        """
        Args:
            db: データベースセッション
            guild_id: 団のID（Guild.id）
        """
        self.db = db
        self.guild_id = guild_id
    
    def update_members(self, scraped_data: List[Dict]) -> Dict:
        """
        スクレイピングデータで履歴を更新（最新30人のみを現在のメンバーとする）
        
        Args:
            scraped_data: [{"name": "...", "player_id": "...", "rank": "..."}, ...]
        
        Returns:
            dict: 名前変更があった団員の情報 {player_id: {"old_name": "...", "new_name": "..."}}
        """
        name_changes = {}
        today = datetime.now()
        
        # 現在のメンバーのplayer_idセット
        current_player_ids = set()
        
        for member_data in scraped_data:
            player_id = member_data["player_id"]
            current_name = member_data["name"]
            
            if not player_id:
                logger.warning(f"IDが取得できませんでした: {current_name}")
                continue
            
            current_player_ids.add(player_id)
            
            # 既存団員を検索
            member = self.db.query(Member).filter(
                Member.player_id == player_id
            ).first()
            
            if member:
                # 既存団員
                old_name = member.current_name
                
                if old_name != current_name:
                    # 名前変更を検出
                    logger.info(f"名前変更を検出: {old_name} → {current_name} (ID: {player_id})")
                    name_changes[player_id] = {
                        "old_name": old_name,
                        "new_name": current_name
                    }
                    
                    # 名前履歴に追加
                    name_history = NameHistory(
                        member_id=member.id,
                        old_name=old_name,
                        new_name=current_name,
                        changed_at=today
                    )
                    self.db.add(name_history)
                    
                    member.current_name = current_name
                
                # 最終確認日を更新
                member.last_seen = today
                member.is_current_member = True
                member.guild_id = self.guild_id  # 復帰した場合に備えて団IDを更新
            else:
                # 新規団員
                logger.info(f"新規団員を登録: {current_name} (ID: {player_id})")
                member = Member(
                    player_id=player_id,
                    current_name=current_name,
                    guild_id=self.guild_id,
                    is_current_member=True,
                    first_seen=today,
                    last_seen=today
                )
                self.db.add(member)
        
        # 現在の30人に含まれないメンバーを非アクティブにする
        former_members = self.db.query(Member).filter(
            Member.guild_id == self.guild_id,
            Member.is_current_member == True,
            ~Member.player_id.in_(current_player_ids)
        ).all()
        
        for former_member in former_members:
            logger.info(f"メンバーが脱退しました: {former_member.current_name} (ID: {former_member.player_id})")
            former_member.is_current_member = False
        
        self.db.commit()
        return name_changes
    
    def get_member_by_id(self, player_id: str) -> Optional[Member]:
        """IDで団員情報を取得"""
        return self.db.query(Member).filter(
            Member.player_id == player_id
        ).first()
    
    def get_member_by_name(self, name: str) -> Optional[Member]:
        """名前で団員を検索（現在の名前のみ）"""
        return self.db.query(Member).filter(
            Member.current_name == name
        ).first()
    
    def get_registered_event_numbers(self) -> List[int]:
        """既に登録されているイベント番号のリストを取得"""
        events = self.db.query(EventData.event_number).filter(
            EventData.guild_id == self.guild_id
        ).distinct().all()
        return sorted([event[0] for event in events])
    
    def is_already_fetched(self, event_number: int) -> bool:
        """指定されたイベント番号のデータが既に取得済みか確認"""
        event = self.db.query(EventData).filter(
            and_(
                EventData.guild_id == self.guild_id,
                EventData.event_number == event_number
            )
        ).first()
        return event is not None
    
    def save_event_data(self, event_number: int, members_data: List[Dict]):
        """イベントのランキングデータを保存"""
        # イベントデータ作成
        event_data = EventData(
            guild_id=self.guild_id,
            event_number=event_number,
            fetched_at=datetime.now()
        )
        self.db.add(event_data)
        self.db.flush()  # event_data.idを取得するため
        
        # ランキングデータ保存
        for member_data in members_data:
            player_id = member_data["player_id"]
            if not player_id:
                continue
            
            # 団員を検索
            member = self.get_member_by_id(player_id)
            if not member:
                logger.warning(f"団員が見つかりません: {player_id}")
                continue
            
            # ランキング保存
            ranking = MemberRanking(
                event_id=event_data.id,
                member_id=member.id,
                rank=member_data["rank"]
            )
            self.db.add(ranking)
        
        self.db.commit()
        logger.info(f"第{event_number}回のデータを保存しました")
    
    def get_event_data(self, event_number: int) -> Optional[Dict]:
        """特定イベントのデータを取得"""
        event = self.db.query(EventData).filter(
            and_(
                EventData.guild_id == self.guild_id,
                EventData.event_number == event_number
            )
        ).first()
        
        if not event:
            return None
        
        # ランキングデータを取得
        rankings = self.db.query(
            MemberRanking, Member
        ).join(
            Member, MemberRanking.member_id == Member.id
        ).filter(
            MemberRanking.event_id == event.id
        ).all()
        
        members = []
        for ranking, member in rankings:
            members.append({
                "player_id": member.player_id,
                "name": member.current_name,
                "rank": ranking.rank
            })
        
        return {
            "event_number": event.event_number,
            "fetched_at": event.fetched_at.isoformat(),
            "members": members
        }
    
    def get_all_events(self) -> List[Dict]:
        """全イベントのリストを取得"""
        events = self.db.query(EventData).filter(
            EventData.guild_id == self.guild_id
        ).order_by(EventData.event_number.desc()).all()
        
        result = []
        for event in events:
            member_count = self.db.query(MemberRanking).filter(
                MemberRanking.event_id == event.id
            ).count()
            
            result.append({
                "event_number": event.event_number,
                "fetched_at": event.fetched_at.isoformat(),
                "member_count": member_count
            })
        
        return result
    
    def get_member_ranking_history(self, player_id: str) -> List[Dict]:
        """特定団員のランキング履歴を取得"""
        member = self.get_member_by_id(player_id)
        if not member:
            return []
        
        rankings = self.db.query(
            MemberRanking, EventData
        ).join(
            EventData, MemberRanking.event_id == EventData.id
        ).filter(
            and_(
                MemberRanking.member_id == member.id,
                EventData.guild_id == self.guild_id
            )
        ).order_by(EventData.event_number).all()
        
        history = []
        for ranking, event in rankings:
            history.append({
                "event_number": event.event_number,
                "rank": ranking.rank,
                "name": member.current_name
            })
        
        return history
    
    def get_all_members(self) -> List[Member]:
        """全団員を取得（現在の30人のみ）"""
        return self.db.query(Member).filter(
            Member.guild_id == self.guild_id,
            Member.is_current_member == True
        ).all()
