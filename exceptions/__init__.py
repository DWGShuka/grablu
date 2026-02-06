"""
exceptions パッケージ

カスタム例外クラスを定義
"""

from .auth import AuthenticationError, AuthorizationError, EmailVerificationError
from .guild import GuildNotFoundError, GuildAlreadyExistsError, GuildCapacityError
from .member import MemberNotFoundError, EventDataNotFoundError
from .scraping import ScrapingError, EventSelectionError
from .base import GrabluException, ValidationError

__all__ = [
    # Base
    "GrabluException",
    "ValidationError",
    # Auth
    "AuthenticationError",
    "AuthorizationError",
    "EmailVerificationError",
    # Guild
    "GuildNotFoundError",
    "GuildAlreadyExistsError",
    "GuildCapacityError",
    # Member
    "MemberNotFoundError",
    "EventDataNotFoundError",
    # Scraping
    "ScrapingError",
    "EventSelectionError",
]
