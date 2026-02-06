"""認証関連のユーティリティ"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from config import settings

# メール認証用のシークレットキー
serializer = URLSafeTimedSerializer(settings.secret_key)

# OAuth設定
config = Config(environ=os.environ)
oauth = OAuth(config)

# Google OAuth設定（設定されている場合のみ）
if settings.is_oauth_configured:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
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
    """認証メールを送信
    
    SMTP または SendGrid を使用してメール送信を行います。
    
    SMTP送信（推奨・無料）:
        環境変数: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL
    
    SendGrid送信:
        環境変数: SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
    """
    verification_url = f"{base_url}/verify-email?token={token}"
    
    # HTMLメールコンテンツ
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>メールアドレスの確認</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0;">Grablu</h1>
            <p style="color: white; margin: 10px 0 0 0;">グラブル団員管理システム</p>
        </div>
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
            <h2 style="color: #667eea;">メールアドレスの確認</h2>
            <p>Grabluにご登録いただきありがとうございます。</p>
            <p>以下のボタンをクリックして、メールアドレスの確認を完了してください：</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    メールアドレスを確認
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">このリンクは1時間有効です。</p>
            <p style="color: #666; font-size: 14px;">
                ※ リンクをクリックできない場合は、以下のURLをブラウザにコピー＆ペーストしてください：<br>
                <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                このメールに心当たりがない場合は、無視してください。
            </p>
        </div>
    </body>
    </html>
    """
    
    # テキスト版（フォールバック）
    text_content = f"""
Grablu - グラブル団員管理システム

メールアドレスの確認

Grabluにご登録いただきありがとうございます。
以下のURLをクリックして、メールアドレスの確認を完了してください：

{verification_url}

このリンクは1時間有効です。

このメールに心当たりがない場合は、無視してください。
    """
    
    # SMTP送信を試みる
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_from_email = os.environ.get('SMTP_FROM_EMAIL') or os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@gbf-guild-mng.com')
    
    if smtp_host and smtp_user and smtp_password:
        # SMTP送信
        try:
            port = int(smtp_port) if smtp_port else 587
            
            # メッセージ作成
            msg = MIMEMultipart('alternative')
            msg['Subject'] = '[Grablu] メールアドレスの確認'
            msg['From'] = smtp_from_email
            msg['To'] = email
            
            # テキストとHTMLパートを追加
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            # SMTP接続と送信
            with smtplib.SMTP(smtp_host, port) as server:
                server.starttls()  # TLS開始
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print(f"✓ 認証メール送信成功（SMTP）: {email}")
            return
            
        except Exception as e:
            print(f"⚠ SMTP送信エラー: {e}")
            print(f"SendGridへフォールバック...")
    
    # SendGrid送信を試みる
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    
    if sendgrid_api_key:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(smtp_from_email),
                to_emails=To(email),
                subject='[Grablu] メールアドレスの確認',
                html_content=Content("text/html", html_content)
            )
            
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            
            print(f"✓ 認証メール送信成功（SendGrid）: {email} (ステータス: {response.status_code})")
            return
            
        except ImportError:
            print(f"⚠ SendGridがインストールされていません。pip install sendgrid を実行してください")
        except Exception as e:
            print(f"✗ SendGrid送信エラー: {e}")
    
    # どちらも設定されていない場合は開発モード
    print(f"""
    ====== メール認証（開発モード） ======
    宛先: {email}
    件名: [Grablu] メールアドレスの確認
    
    以下のURLをクリックしてメールアドレスを確認してください：
    {verification_url}
    
    このリンクは1時間有効です。
    
    ※ 本番環境ではSMTPまたはSendGridを設定してください
    
    【SMTP設定例（推奨・無料）】
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your@gmail.com
    SMTP_PASSWORD=your_app_password
    SMTP_FROM_EMAIL=noreply@gbf-guild-mng.com
    
    【SendGrid設定例】
    SENDGRID_API_KEY=SG.xxxxx
    SENDGRID_FROM_EMAIL=noreply@gbf-guild-mng.com
    =====================================
    """)
