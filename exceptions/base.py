"""
基底例外クラス
"""
from typing import Any, Optional


class GrabluException(Exception):
    """Grabluアプリケーションの基底例外"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        """
        Args:
            message: エラーメッセージ
            status_code: HTTPステータスコード
            details: 追加の詳細情報
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(GrabluException):
    """バリデーションエラー"""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)
