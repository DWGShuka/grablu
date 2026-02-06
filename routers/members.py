"""
団員管理ルーター
団員リスト、比較分析、履歴表示
"""
import logging
from typing import Dict

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from guild_manager import GuildManager
from member_tracker import MemberTracker
from models import NameHistory, Member

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/members")
templates = Jinja2Templates(directory="templates")


def get_current_user_id(request: Request) -> int:
    """セッションから現在のユーザーIDを取得"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return user_id


def require_auth(request: Request) -> str:
    """認証必須デコレータ"""
    username = request.session.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return username


@router.get("/compare", response_class=HTMLResponse)
async def view_members_compare(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """団員比較分析画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    tracker = MemberTracker(db, active_guild.id)
    
    # 全イベントリストを取得
    events = tracker.get_all_events()
    
    return templates.TemplateResponse(
        "members_compare.html",
        {
            "request": request,
            "username": username,
            "guild": {"guild_name": active_guild.name, "guild_id": active_guild.guild_id},
            "events": events
        }
    )


@router.get("", response_class=HTMLResponse)
async def view_members(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """団員リスト表示画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    tracker = MemberTracker(db, active_guild.id)
    
    # 全イベントリストを取得
    events = tracker.get_all_events()
    
    # 最新イベントのデータを取得
    latest_event_data = None
    if events:
        latest_event_data = tracker.get_event_data(events[0]["event_number"])
    
    return templates.TemplateResponse(
        "members.html",
        {
            "request": request,
            "username": username,
            "guild": {"guild_name": active_guild.name, "guild_id": active_guild.guild_id},
            "events": events,
            "latest_event": latest_event_data
        }
    )


@router.get("/event/{event_number}")
async def get_event_members(
    request: Request,
    event_number: int,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict:
    """特定イベントの団員データを取得（API）"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        raise HTTPException(status_code=404, detail="団が登録されていません")
    
    tracker = MemberTracker(db, active_guild.id)
    event_data = tracker.get_event_data(event_number)
    
    if not event_data:
        raise HTTPException(status_code=404, detail="イベントデータが見つかりません")
    
    return event_data
