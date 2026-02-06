"""
スクレイピングルーター
団員データの取得処理
"""
import logging
from typing import Dict

from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from services import ScrapingService

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/execute")
async def execute_scraping(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict:
    """団員データ取得実行"""
    logger.info(f"団員データ取得開始 (ユーザー: {username})")
    
    # ユーザーIDを取得
    user_id = get_current_user_id(request)
    
    # スクレイピングサービスを使用して実行
    service = ScrapingService(db, user_id)
    result = service.execute_batch_scraping()
    
    # ScrapingResultをJSONレスポンス用の辞書に変換
    response = {
        "status": result.status,
        "message": result.message,
    }
    
    if result.status == "success":
        response["fetched_events"] = result.fetched_events
        response["remaining_events"] = result.remaining_events
    elif result.status == "info":
        response["available_events"] = result.available_events
        response["registered_events"] = result.registered_events
    
    return response
