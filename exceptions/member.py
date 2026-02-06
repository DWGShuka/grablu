"""
団員・イベント関連の例外
"""
from .base import GrabluException


class MemberNotFoundError(GrabluException):
    """団員が見つからない"""
    
    def __init__(self, message: str = "団員が見つかりません"):
        super().__init__(message, status_code=404)


class EventDataNotFoundError(GrabluException):
    """イベントデータが見つからない"""
    
    def __init__(self, event_number: int):
        message = f"イベント番号{event_number}のデータが見つかりません"
        super().__init__(message, status_code=404)
