"""
スクレイピング関連のスキーマ
"""
from pydantic import BaseModel, Field
from typing import Optional


class ScrapingEventResult(BaseModel):
    """スクレイピング単一イベント結果"""
    event_number: int
    member_count: int
    name_changes: int


class ScrapingResponse(BaseModel):
    """スクレイピング実行結果"""
    status: str = Field(..., description="ステータス (success/info/error)")
    message: str = Field(..., description="メッセージ")
    fetched_events: Optional[list[ScrapingEventResult]] = None
    remaining_events: Optional[int] = None
    available_events: Optional[int] = None
    registered_events: Optional[int] = None
