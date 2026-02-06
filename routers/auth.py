"""
認証ルーター
ログイン、登録、OAuth、メール認証
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth_utils import (
    oauth,
    generate_verification_token,
    verify_verification_token,
    send_verification_email
)

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ベースURL（OAuth リダイレクト用）
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")


def get_current_user(request: Request) -> Optional[str]:
    """セッションから現在のユーザーを取得"""
    return request.session.get("username")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """ログイン画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """ログイン処理"""
    # データベースからメールアドレスでユーザーを検索
    user = db.query(User).filter(User.email == email).first()
    
    if user and user.is_active and user.verify_password(password):
        # 最終ログイン日時を更新
        user.last_login = datetime.now()
        db.commit()
        
        # セッションに保存
        request.session["username"] = user.username
        request.session["user_id"] = user.id
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(
            url="/login?error=1",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/logout")
async def logout(request: Request):
    """ログアウト処理"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """ユーザー登録画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """ユーザー登録処理"""
    # バリデーション
    if password != password_confirm:
        return RedirectResponse(
            url="/register?error=password_mismatch",
            status_code=status.HTTP_302_FOUND
        )
    
    if len(password) < 8:
        return RedirectResponse(
            url="/register?error=password_too_short",
            status_code=status.HTTP_302_FOUND
        )
    
    # メールアドレスの必須チェック
    if not email or not email.strip():
        return RedirectResponse(
            url="/register?error=email_required",
            status_code=status.HTTP_302_FOUND
        )
    
    # メールアドレスの重複チェック
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        return RedirectResponse(
            url="/register?error=email_exists",
            status_code=status.HTTP_302_FOUND
        )
    
    # メール認証トークンを生成
    verification_token = generate_verification_token(email)
    
    # 最初のユーザーかどうかチェック
    user_count = db.query(User).count()
    is_first_user = (user_count == 0)
    
    # 開発モードチェック
    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
    
    # 新規ユーザー作成（メール未認証状態）
    new_user = User(
        username=username,
        email=email,
        hashed_password=User.get_password_hash(password),
        is_active=True if dev_mode else False,  # 開発モードでは即座にアクティブ
        email_verified=True if dev_mode else False,  # 開発モードでは認証済み扱い
        verification_token=verification_token,
        is_admin=is_first_user  # 最初のユーザーは自動的に管理者
    )
    db.add(new_user)
    db.commit()
    
    if is_first_user:
        logger.info(f"🎉 初期管理者アカウント作成: {username} ({email})")
    else:
        logger.info(f"新規ユーザー登録: {username} ({email})")
    
    # 開発モードではメール送信をスキップ
    if not dev_mode:
        base_url = os.environ.get("BASE_URL", "http://localhost:8080")
        send_verification_email(email, verification_token, base_url)
    else:
        logger.info(f"📧 開発モード: メール認証をスキップしました ({email})")
    
    # 登録完了ページにリダイレクト
    return RedirectResponse(
        url="/register-complete",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/register-complete", response_class=HTMLResponse)
async def register_complete(request: Request):
    """登録完了画面"""
    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
    return templates.TemplateResponse("register_complete.html", {
        "request": request,
        "dev_mode": dev_mode
    })


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """メールアドレス認証"""
    email = verify_verification_token(token)
    
    if not email:
        raise HTTPException(status_code=400, detail="無効または期限切れのトークンです")
    
    # ユーザーを検索して認証状態を更新
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    if user.email_verified:
        return RedirectResponse(url="/login?verified=already", status_code=status.HTTP_302_FOUND)
    
    user.email_verified = True
    user.is_active = True
    user.verification_token = None
    db.commit()
    
    logger.info(f"メール認証完了: {email}")
    
    return RedirectResponse(url="/login?verified=success", status_code=status.HTTP_302_FOUND)


@router.get("/auth/google")
async def google_login(request: Request):
    """Google OAuth ログイン"""
    redirect_uri = f"{BASE_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Google OAuth コールバック"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="ユーザー情報を取得できませんでした")
        
        email = user_info.get('email')
        name = user_info.get('name')
        oauth_id = user_info.get('sub')
        
        # 既存ユーザーを検索（メールまたはOAuth IDで）
        user = db.query(User).filter(
            (User.email == email) | (User.oauth_id == oauth_id)
        ).first()
        
        if user:
            # 既存ユーザーのログイン
            if not user.oauth_id:
                # OAuth情報を追加
                user.oauth_provider = 'google'
                user.oauth_id = oauth_id
                user.email_verified = True
                user.is_active = True
            user.last_login = datetime.now()
            db.commit()
        else:
            # 新規ユーザー作成
            user = User(
                username=name or email.split('@')[0],
                email=email,
                hashed_password=None,  # OAuth登録のためパスワード不要
                oauth_provider='google',
                oauth_id=oauth_id,
                is_active=True,
                email_verified=True,
                is_admin=False
            )
            db.add(user)
            db.commit()
            logger.info(f"Google OAuth新規登録: {email}")
        
        # セッション作成してログイン
        request.session["username"] = user.username
        request.session["user_id"] = user.id
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Google OAuth エラー: {e}")
        return RedirectResponse(
            url="/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )
