"""認証関連のユーティリティ"""
import os
import secrets
from typing import Optional
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# メール認証用のシークレットキー
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
serializer = URLSafeTimedSerializer(SECRET_KEY)

# OAuth設定
config = Config(environ=os.environ)
oauth = OAuth(config)

# Google OAuth設定
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


def generate_verification_token(email: str) -> str:
    """メール認証トークンを生成"""
    return serializer.dumps(email, salt='email-verification')


def verify_verification_token(token: str, max_age: int = 3600) -> Optional[str]:
    """メール認証トークンを検証（有効期限: デフォルト1時間）"""
    try:
        email = serializer.loads(token, salt='email-verification', max_age=max_age)
        return email
    except Exception:
        return None


def send_verification_email(email: str, token: str, base_url: str):
    """認証メールを送信（実装例）
    
    本番環境ではSendGrid、AWS SES、Gmail API等を使用してください。
    """
    verification_url = f"{base_url}/verify-email?token={token}"
    
    # TODO: 実際のメール送信実装
    # 開発中はログに出力
    print(f"""
    ====== メール認証 ======
    宛先: {email}
    件名: [Grablu] メールアドレスの確認
    
    以下のURLをクリックしてメールアドレスを確認してください：
    {verification_url}
    
    このリンクは1時間有効です。
    =======================
    """)
    
    # SendGrid実装例:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    # 
    # message = Mail(
    #     from_email='noreply@gbf-guild-mng.com',
    #     to_emails=email,
    #     subject='[Grablu] メールアドレスの確認',
    #     html_content=f'<a href="{verification_url}">メールアドレスを確認</a>'
    # )
    # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    # sg.send(message)
