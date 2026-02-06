"""
団関連の例外
"""
from .base import GrabluException


class GuildNotFoundError(GrabluException):
    """団が見つからない"""
    
    def __init__(self, message: str = "団が登録されていません"):
        super().__init__(message, status_code=404)


class GuildAlreadyExistsError(GrabluException):
    """団が既に存在する"""
    
    def __init__(self, message: str = "この団は既に登録されています"):
        super().__init__(message, status_code=409)


class GuildCapacityError(GrabluException):
    """団の定員超過"""
    
    def __init__(self, message: str = "団の定員に達しています（最大30名）"):
        super().__init__(message, status_code=400)
