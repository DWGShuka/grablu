"""
認証・認可関連の例外
"""
from .base import GrabluException


class AuthenticationError(GrabluException):
    """認証エラー"""
    
    def __init__(self, message: str = "認証に失敗しました"):
        super().__init__(message, status_code=401)


class AuthorizationError(GrabluException):
    """認可エラー（権限不足）"""
    
    def __init__(self, message: str = "この操作を実行する権限がありません"):
        super().__init__(message, status_code=403)


class EmailVerificationError(GrabluException):
    """メール認証エラー"""
    
    def __init__(self, message: str = "メール認証に失敗しました"):
        super().__init__(message, status_code=400)
