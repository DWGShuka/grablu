"""
通知サービス
メール送信などの通知機能に関するビジネスロジック
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """メール送信設定"""
    smtp_host: Optional[str]
    smtp_port: int
    smtp_user: Optional[str]
    smtp_password: Optional[str]
    from_email: str
    sendgrid_api_key: Optional[str]
    
    @classmethod
    def from_env(cls) -> "EmailConfig":
        """環境変数から設定を読み込む"""
        smtp_from = os.environ.get('SMTP_FROM_EMAIL')
        sendgrid_from = os.environ.get('SENDGRID_FROM_EMAIL')
        default_from = 'noreply@gbf-guild-mng.com'
        
        return cls(
            smtp_host=os.environ.get('SMTP_HOST'),
            smtp_port=int(os.environ.get('SMTP_PORT', '587')),
            smtp_user=os.environ.get('SMTP_USER'),
            smtp_password=os.environ.get('SMTP_PASSWORD'),
            from_email=smtp_from or sendgrid_from or default_from,
            sendgrid_api_key=os.environ.get('SENDGRID_API_KEY')
        )


class NotificationService:
    """通知サービス"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Args:
            config: メール送信設定（Noneの場合は環境変数から読み込む）
        """
        self.config = config or EmailConfig.from_env()
    
    def _create_html_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> MIMEMultipart:
        """HTMLメールメッセージを作成
        
        Args:
            to_email: 送信先メールアドレス
            subject: 件名
            html_body: HTML本文
            text_body: テキスト本文（フォールバック用）
            
        Returns:
            MIMEMultipartメッセージ
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config.from_email
        msg['To'] = to_email
        
        # テキストとHTMLパートを追加
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        return msg
    
    def _send_via_smtp(self, msg: MIMEMultipart) -> bool:
        """SMTPでメールを送信
        
        Args:
            msg: 送信するメッセージ
            
        Returns:
            送信成功時True、失敗時False
        """
        if not all([
            self.config.smtp_host,
            self.config.smtp_user,
            self.config.smtp_password
        ]):
            return False
        
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()  # TLS開始
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✓ メール送信成功（SMTP）: {msg['To']}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠ SMTP送信エラー: {e}")
            return False
    
    def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_body: str
    ) -> bool:
        """SendGridでメールを送信
        
        Args:
            to_email: 送信先メールアドレス
            subject: 件名
            html_body: HTML本文
            
        Returns:
            送信成功時True、失敗時False
        """
        if not self.config.sendgrid_api_key:
            return False
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(self.config.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_body)
            )
            
            sg = SendGridAPIClient(self.config.sendgrid_api_key)
            response = sg.send(message)
            
            logger.info(
                f"✓ メール送信成功（SendGrid）: {to_email} "
                f"(ステータス: {response.status_code})"
            )
            return True
            
        except ImportError:
            logger.warning("⚠ SendGridがインストールされていません")
            return False
        except Exception as e:
            logger.error(f"✗ SendGrid送信エラー: {e}")
            return False
    
    def _log_dev_mode_email(
        self,
        to_email: str,
        subject: str,
        verification_url: Optional[str] = None
    ):
        """開発モードでメール内容をログ出力
        
        Args:
            to_email: 送信先メールアドレス
            subject: 件名
            verification_url: 認証URL（存在する場合）
        """
        logger.info(f"""
====== メール送信（開発モード） ======
宛先: {to_email}
件名: {subject}

{f'認証URL: {verification_url}' if verification_url else ''}

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
    
    def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        base_url: str
    ) -> bool:
        """認証メールを送信
        
        Args:
            to_email: 送信先メールアドレス
            verification_token: 認証トークン
            base_url: ベースURL
            
        Returns:
            送信成功時True
        """
        verification_url = f"{base_url}/verify-email?token={verification_token}"
        subject = '[Grablu] メールアドレスの確認'
        
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
        
        # メッセージ作成
        msg = self._create_html_email(to_email, subject, html_content, text_content)
        
        # SMTP送信を試みる
        if self._send_via_smtp(msg):
            return True
        
        # SendGrid送信を試みる
        if self._send_via_sendgrid(to_email, subject, html_content):
            return True
        
        # どちらも失敗した場合は開発モード
        self._log_dev_mode_email(to_email, subject, verification_url)
        return True  # 開発モードでは常に成功扱い
    
    def send_test_email(
        self,
        to_email: str,
        custom_message: Optional[str] = None
    ) -> bool:
        """テストメールを送信
        
        Args:
            to_email: 送信先メールアドレス
            custom_message: カスタムメッセージ（任意）
            
        Returns:
            送信成功時True
        """
        subject = '[Grablu] テストメール'
        
        message = custom_message or "これはGrabluからのテストメールです。"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>テストメール</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #667eea;">Grablu テストメール</h2>
            <p>{message}</p>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                メール送信が正常に機能しています。
            </p>
        </body>
        </html>
        """
        
        text_content = f"""
Grablu テストメール

{message}

メール送信が正常に機能しています。
        """
        
        # メッセージ作成
        msg = self._create_html_email(to_email, subject, html_content, text_content)
        
        # SMTP送信を試みる
        if self._send_via_smtp(msg):
            return True
        
        # SendGrid送信を試みる
        if self._send_via_sendgrid(to_email, subject, html_content):
            return True
        
        # どちらも失敗した場合は開発モード
        self._log_dev_mode_email(to_email, subject)
        return True  # 開発モードでは常に成功扱い
