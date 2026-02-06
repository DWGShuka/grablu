"""
団関連のスキーマ
"""
from pydantic import BaseModel, Field
from typing import Optional


class GuildCreate(BaseModel):
    """団作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=100, description="団名")
    guild_id: str = Field(..., min_length=1, max_length=50, description="団ID")


class GuildSearchRequest(BaseModel):
    """団検索リクエスト"""
    guild_name: str = Field(..., min_length=1, description="団名（検索）")


class GuildResponse(BaseModel):
    """団情報レスポンス"""
    id: int
    name: str
    guild_id: str
    member_count: Optional[int] = None
    
    model_config = {"from_attributes": True}
