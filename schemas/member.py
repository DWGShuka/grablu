"""
団員・イベント関連のスキーマ
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MemberResponse(BaseModel):
    """団員情報レスポンス"""
    id: int
    player_id: str
    current_name: str
    rank: Optional[int] = None
    last_seen: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class EventMemberData(BaseModel):
    """イベント団員データ"""
    player_id: str
    name: str
    contribution: int = 0
    rank: Optional[int] = None


class EventDataResponse(BaseModel):
    """イベントデータレスポンス"""
    event_number: int
    member_count: int
    members: list[EventMemberData]
    fetched_at: Optional[datetime] = None
