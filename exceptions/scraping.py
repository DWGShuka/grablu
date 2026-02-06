"""
スクレイピング関連の例外
"""
from .base import GrabluException


class ScrapingError(GrabluException):
    """スクレイピングエラー"""
    
    def __init__(self, message: str = "データ取得中にエラーが発生しました"):
        super().__init__(message, status_code=500)


class EventSelectionError(ScrapingError):
    """イベント選択エラー"""
    
    def __init__(self, event_number: int):
        message = f"第{event_number}回のイベントを選択できませんでした"
        super().__init__(message)
