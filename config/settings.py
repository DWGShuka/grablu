"""
アプリケーション設定

Pydantic Settingsを使用した型安全な設定管理
環境変数と.envファイルから設定を読み込む
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # アプリケーション基本設定
    app_name: str = Field(default="Grablu", description="アプリケーション名")
    debug: bool = Field(default=False, description="デバッグモード")
    dev_mode: bool = Field(default=False, description="開発モード（メール認証スキップ）")
    base_url: str = Field(default="http://localhost:8080", description="ベースURL")
    
    # セキュリティ設定
    secret_key: str = Field(default="your-secret-key-here-change-in-production", description="セッション暗号化キー")
    
    # データベース設定
    database_url: Optional[str] = Field(default=None, description="データベース接続URL")
    postgres_user: str = Field(default="postgres", description="PostgreSQLユーザー名")
    postgres_password: str = Field(default="password", description="PostgreSQLパスワード")
    postgres_db: str = Field(default="grablu", description="PostgreSQLデータベース名")
    postgres_host: str = Field(default="db", description="PostgreSQLホスト")
    postgres_port: int = Field(default=5432, description="PostgreSQLポート")
    
    # メール設定（SMTP）
    smtp_host: Optional[str] = Field(default=None, description="SMTPホスト")
    smtp_port: int = Field(default=587, description="SMTPポート")
    smtp_user: Optional[str] = Field(default=None, description="SMTPユーザー名")
    smtp_password: Optional[str] = Field(default=None, description="SMTPパスワード")
    smtp_from_email: Optional[str] = Field(default=None, description="送信元メールアドレス")
    
    # メール設定（SendGrid）
    sendgrid_api_key: Optional[str] = Field(default=None, description="SendGrid APIキー")
    sendgrid_from_email: Optional[str] = Field(default=None, description="SendGrid送信元メールアドレス")
    
    # OAuth設定（Google）
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth クライアントID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth シークレット")
    
    # スクレイピング設定
    gbfdata_base_url: str = Field(default="https://gbfdata.com/ja", description="GBFDataベースURL")
    scraping_max_fetch: int = Field(default=5, description="1回の実行で取得する最大イベント数")
    
    # ロギング設定
    log_level: str = Field(default="INFO", description="ログレベル")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="ログフォーマット"
    )
    
    # CORS設定
    cors_origins: list[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        description="CORS許可オリジン"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @validator("database_url", pre=True, always=True)
    def assemble_database_url(cls, v: Optional[str], values: dict) -> str:
        """データベースURLを構築"""
        if v:
            return v
        
        user = values.get("postgres_user", "postgres")
        password = values.get("postgres_password", "password")
        host = values.get("postgres_host", "db")
        port = values.get("postgres_port", 5432)
        db = values.get("postgres_db", "grablu")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    @property
    def from_email(self) -> str:
        """メール送信元アドレスを取得（SMTP優先、次にSendGrid）"""
        return self.smtp_from_email or self.sendgrid_from_email or "noreply@gbf-guild-mng.com"
    
    @property
    def is_email_configured(self) -> bool:
        """メール送信が設定されているか確認"""
        smtp_configured = all([self.smtp_host, self.smtp_user, self.smtp_password])
        sendgrid_configured = bool(self.sendgrid_api_key)
        return smtp_configured or sendgrid_configured
    
    @property
    def is_oauth_configured(self) -> bool:
        """OAuth（Google）が設定されているか確認"""
        return bool(self.google_client_id and self.google_client_secret)


# シングルトンインスタンス
settings = Settings()


# 環境情報をログ出力（デバッグ用）
def log_settings():
    """設定情報をログ出力（機密情報はマスク）"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("アプリケーション設定")
    logger.info("=" * 60)
    logger.info(f"アプリケーション名: {settings.app_name}")
    logger.info(f"デバッグモード: {settings.debug}")
    logger.info(f"開発モード: {settings.dev_mode}")
    logger.info(f"ベースURL: {settings.base_url}")
    logger.info(f"データベース: postgresql://***:***@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"メール送信: {'設定済み' if settings.is_email_configured else '未設定（開発モード）'}")
    logger.info(f"OAuth (Google): {'設定済み' if settings.is_oauth_configured else '未設定'}")
    logger.info(f"GBFDataベースURL: {settings.gbfdata_base_url}")
    logger.info(f"スクレイピング最大取得数: {settings.scraping_max_fetch}")
    logger.info(f"ログレベル: {settings.log_level}")
    logger.info("=" * 60)
