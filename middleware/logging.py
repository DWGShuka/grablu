"""
リクエストロギングミドルウェア
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストログを記録するミドルウェア"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        各リクエストの処理時間とステータスコードをログに記録
        
        Args:
            request: HTTPリクエスト
            call_next: 次の処理を呼び出す関数
            
        Returns:
            Response: HTTPレスポンス
        """
        # 開始時刻
        start_time = time.time()
        
        # パスとメソッド
        path = request.url.path
        method = request.method
        
        # 静的ファイルはログスキップ
        if path.startswith("/static"):
            return await call_next(request)
        
        # リクエスト処理
        try:
            response = await call_next(request)
            
            # 処理時間計算
            process_time = time.time() - start_time
            
            # ステータスコード
            status_code = response.status_code
            
            # ログレベル決定
            if status_code >= 500:
                log_level = logging.ERROR
            elif status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            
            # ログ出力
            logger.log(
                log_level,
                f"{method} {path} - {status_code} ({process_time:.3f}s)"
            )
            
            # レスポンスヘッダーに処理時間を追加
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"{method} {path} - ERROR ({process_time:.3f}s): {str(e)}"
            )
            raise
