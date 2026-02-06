"""
エラーハンドラー

カスタム例外をHTTPレスポンスに変換
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from exceptions import GrabluException

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


async def grablu_exception_handler(request: Request, exc: GrabluException) -> JSONResponse:
    """
    Grabluカスタム例外ハンドラー
    
    Args:
        request: HTTPリクエスト
        exc: Grablu例外
        
    Returns:
        JSONResponse: エラーレスポンス
    """
    logger.warning(
        f"GrabluException: {exc.message} (status={exc.status_code})",
        extra={"details": exc.details}
    )
    
    # APIリクエスト（JSON形式で返答）
    if request.url.path.startswith("/api/") or request.headers.get("accept") == "application/json":
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    # Webリクエスト（HTMLテンプレートで返答）
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "message": exc.message,
            "details": exc.details
        },
        status_code=exc.status_code
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    一般的な例外ハンドラー
    
    Args:
        request: HTTPリクエスト
        exc: 例外
        
    Returns:
        JSONResponse: エラーレスポンス
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # APIリクエスト
    if request.url.path.startswith("/api/") or request.headers.get("accept") == "application/json":
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
                "details": {"error": str(exc)}
            }
        )
    
    # Webリクエスト
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "message": "サーバー内部エラーが発生しました",
            "details": {"error": str(exc)}
        },
        status_code=500
    )


def add_exception_handlers(app: FastAPI):
    """
    例外ハンドラーをアプリケーションに追加
    
    Args:
        app: FastAPIアプリケーション
    """
    # Grabluカスタム例外
    app.add_exception_handler(GrabluException, grablu_exception_handler)
    
    # 一般的な例外
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("✓ 例外ハンドラーを登録しました")
