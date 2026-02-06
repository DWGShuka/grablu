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
from services import MemberService
from exceptions import GuildNotFoundError, EventDataNotFoundError

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
    
    # MemberServiceを使用してデータ取得
    service = MemberService(db, user_id)
    
    try:
        result = service.get_member_compare_data()
    except GuildNotFoundError:
        # 団が登録されていない場合は団登録画面へリダイレクト
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "members_compare.html",
        {
            "request": request,
            "username": username,
            "guild": result.guild_info,
            "events": result.events
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
    
    # MemberServiceを使用してデータ取得
    service = MemberService(db, user_id)
    
    try:
        result = service.get_member_list_data()
    except GuildNotFoundError:
        # 団が登録されていない場合は団登録画面へリダイレクト
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "members.html",
        {
            "request": request,
            "username": username,
            "guild": result.guild_info,
            "events": result.events,
            "latest_event": result.latest_event
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
    
    # MemberServiceを使用してデータ取得
    service = MemberService(db, user_id)
    
    # カスタム例外がGrabluExceptionとしてハンドルされるので、そのまま使用
    event_data = service.get_event_members_data(event_number)
    return event_data
