"""
管理者機能ルーター
メールテスト送信
"""
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth_utils import generate_verification_token
from services import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


def get_current_user_id(request: Request) -> int:
    """セッションから現在のユーザーIDを取得"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return user_id


def require_auth(request: Request) -> str:
    """認証必須デコレータ"""
    username = request.session.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return username


def require_admin(request: Request, db: Session) -> User:
    """管理者権限チェック"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    
    return user


@router.get("/test-email", response_class=HTMLResponse)
async def test_email_page(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """メールテスト画面（管理者のみ）"""
    require_admin(request, db)
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>メール送信テスト - Grablu</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 {
                color: #667eea;
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                color: #333;
                font-weight: bold;
            }
            input, textarea {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                box-sizing: border-box;
            }
            input:focus, textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                font-weight: bold;
            }
            button:hover {
                opacity: 0.9;
            }
            .info {
                background: #f0f7ff;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .info p {
                margin: 5px 0;
                color: #555;
                font-size: 14px;
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #667eea;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            #result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }
            .success {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .error {
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 メール送信テスト</h1>
            <div class="info">
                <p><strong>管理者機能</strong></p>
                <p>メール認証機能のテストを行います。</p>
                <p>指定したメールアドレスにテスト用の認証メールを送信します。</p>
            </div>
            <form id="testForm">
                <div class="form-group">
                    <label for="email">送信先メールアドレス</label>
                    <input type="email" id="email" name="email" required 
                           placeholder="test@example.com">
                </div>
                <div class="form-group">
                    <label for="test_name">テスト名（オプション）</label>
                    <input type="text" id="test_name" name="test_name" 
                           placeholder="例: 本番環境テスト">
                </div>
                <button type="submit">テストメールを送信</button>
            </form>
            <div id="result"></div>
            <a href="/" class="back-link">← ホームに戻る</a>
        </div>
        <script>
            document.getElementById('testForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const email = document.getElementById('email').value;
                const testName = document.getElementById('test_name').value;
                const resultDiv = document.getElementById('result');
                const button = e.target.querySelector('button');
                
                button.disabled = true;
                button.textContent = '送信中...';
                resultDiv.style.display = 'none';
                
                try {
                    const response = await fetch('/admin/test-email/send', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ email, test_name: testName })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        resultDiv.className = 'success';
                        resultDiv.innerHTML = `
                            <strong>✓ 送信成功</strong><br>
                            ${data.message}<br>
                            ${data.debug_url ? `<br><small>デバッグURL: ${data.debug_url}</small>` : ''}
                        `;
                    } else {
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `<strong>✗ 送信失敗</strong><br>${data.detail}`;
                    }
                } catch (error) {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<strong>✗ エラー</strong><br>${error.message}`;
                }
                
                resultDiv.style.display = 'block';
                button.disabled = false;
                button.textContent = 'テストメールを送信';
            });
        </script>
    </body>
    </html>
    """)


@router.post("/test-email/send")
async def test_email_send(
    request: Request,
    username: str = Depends(require_auth), 
    db: Session = Depends(get_db)
):
    """メールテスト送信API（管理者のみ）"""
    require_admin(request, db)
    
    try:
        # リクエストボディをJSON形式で取得
        body = await request.json()
        email = body.get("email")
        test_name = body.get("test_name")
        
        if not email:
            raise HTTPException(status_code=400, detail="メールアドレスが必要です")
        
        # テスト用トークンを生成
        token = generate_verification_token(email)
        
        # メール送信
        base_url = os.environ.get("BASE_URL", "http://localhost:8080")
        notification_service = NotificationService()
        notification_service.send_verification_email(email, token, base_url)
        
        # デバッグ用URLを生成（開発モードのみ）
        debug_url = None
        if not os.environ.get('SENDGRID_API_KEY'):
            debug_url = f"{base_url}/verify-email?token={token}"
        
        logger.info(f"テストメール送信: {email} (送信者: {username}, テスト名: {test_name or 'なし'})")
        
        response_data = {
            "message": f"テストメールを {email} に送信しました。",
            "timestamp": datetime.now().isoformat()
        }
        
        if debug_url:
            response_data["debug_url"] = debug_url
            response_data["message"] += " (開発モード: SendGrid未設定)"
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"テストメール送信エラー: {e}")
        raise HTTPException(status_code=500, detail=f"メール送信に失敗しました: {str(e)}")
