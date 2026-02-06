"""
Grablu Web Application
FastAPIベースのWebアプリケーション（Phase 3: 設定・ミドルウェア統合版）
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import get_db, init_db
from guild_manager import GuildManager
from member_tracker import MemberTracker
from models import NameHistory, Member
from auth_utils import oauth
from middleware import RequestLoggingMiddleware, add_exception_handlers

# ルーターインポート
from routers import auth, guilds, members, scraping, admin

# ロギング設定
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    description="グラブル団員管理システム"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストロギングミドルウェア
app.add_middleware(RequestLoggingMiddleware)

# セッションミドルウェア
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="session",
    max_age=86400,  # 24時間
    same_site="lax",
    https_only=not settings.debug  # デバッグモードではHTTPも許可
)

# 例外ハンドラー登録
add_exception_handlers(app)

# データベース初期化
logger.info("=" * 60)
logger.info(f"{settings.app_name} 起動中...")
logger.info("=" * 60)
init_db()
logger.info("=" * 60)
logger.info("✓ アプリケーションの初期化が完了しました")
logger.info("=" * 60)

# 設定情報をログ出力（デバッグモード時のみ）
if settings.debug:
    from config.settings import log_settings
    log_settings()

# テンプレート設定
templates = Jinja2Templates(directory="templates")


def get_current_user(request: Request) -> Optional[str]:
    """セッションから現在のユーザーを取得"""
    return request.session.get("username")


def get_current_user_id(request: Request) -> Optional[int]:
    """セッションから現在のユーザーIDを取得"""
    return request.session.get("user_id")


async def require_auth(request: Request) -> str:
    """認証必須のエンドポイント用"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です"
        )
    return username


# ルーターをマウント
app.include_router(auth.router, tags=["認証"])
app.include_router(guilds.router, tags=["団管理"])
app.include_router(members.router, tags=["団員管理"])
app.include_router(scraping.router, tags=["データ取得"])
app.include_router(admin.router, tags=["管理者機能"])

logger.info("✓ ルーター登録完了: auth, guilds, members, scraping, admin")


# ホーム画面（ルート）
@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """ホーム画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    
    # 団が未登録の場合は登録画面へリダイレクト
    if not guild_manager.is_registered():
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    # アクティブな団情報を取得
    active_guild = guild_manager.get_active_guild()
    
    # 履歴情報を取得
    tracker = MemberTracker(db, active_guild.id)
    
    history_info = {
        "last_event": None,
        "member_count": len(tracker.get_all_members()),
        "last_updated": None
    }
    
    # 最新イベント情報を取得
    events = tracker.get_all_events()
    if events:
        history_info["last_event"] = events[0]["event_number"]
        history_info["last_updated"] = events[0]["fetched_at"]
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "username": username,
            "history": history_info,
            "guild": {"guild_name": active_guild.name, "guild_id": active_guild.guild_id}
        }
    )


@app.get("/history", response_class=HTMLResponse)
async def view_history(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """履歴・名前変更履歴画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    tracker = MemberTracker(db, active_guild.id)
    
    # 名前変更履歴を抽出
    name_changes_query = db.query(
        NameHistory, Member
    ).join(
        Member, NameHistory.member_id == Member.id
    ).filter(
        Member.guild_id == active_guild.id
    ).order_by(
        NameHistory.changed_at.desc()
    ).all()
    
    name_changes = []
    for history, member in name_changes_query:
        name_changes.append({
            "player_id": member.player_id,
            "current_name": member.current_name,
            "old_name": history.old_name,
            "new_name": history.new_name,
            "last_changed": history.changed_at.strftime("%Y-%m-%d %H:%M")
        })
    
    total_members = len(tracker.get_all_members())
    
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "username": username,
            "name_changes": name_changes,
            "total_members": total_members
        }
    )


# エラーハンドラー
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """未認証の場合はログインページへリダイレクト"""
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """権限がない場合のエラーページ"""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "403",
            "error_icon": "🚫",
            "error_title": "アクセス権限がありません",
            "error_message": "このページを閲覧する権限がありません。管理者権限が必要なページです。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "管理者権限が必要な場合は、システム管理者にお問い合わせください。"
        },
        status_code=403
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """ページが見つからない場合のエラーページ"""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "404",
            "error_icon": "🔍",
            "error_title": "ページが見つかりません",
            "error_message": "お探しのページは存在しないか、移動または削除された可能性があります。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "URLが正しいかご確認ください。"
        },
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """サーバーエラーの場合のエラーページ"""
    logger.error(f"Internal Server Error: {str(exc)}", exc_info=True)
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "500",
            "error_icon": "⚠️",
            "error_title": "サーバーエラーが発生しました",
            "error_message": "申し訳ございません。システムエラーが発生しました。しばらく経ってから再度お試しください。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "問題が続く場合は、システム管理者にお問い合わせください。"
        },
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
