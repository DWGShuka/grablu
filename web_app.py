"""
Grablu Web Application
FastAPIベースのWebアプリケーション
"""
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import load_config
from scraper import GuildScraper
from spreadsheet import SpreadsheetWriter
from member_tracker import MemberTracker
from guild_manager import GuildManager
from database import get_db, init_db
from sqlalchemy.orm import Session
from models import User
from auth_utils import (
    oauth, 
    generate_verification_token, 
    verify_verification_token, 
    send_verification_email
)

# ロギング設定（Cloud Runでは標準出力のみ使用）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(title="Grablu 団員管理")

# セッションミドルウェアを追加
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "grablu-secret-key-change-in-production-2026"),
    session_cookie="session",
    max_age=86400,  # 24時間
    same_site="lax",
    https_only=True  # HTTPS必須（本番環境）
)

# データベース初期化
logger.info("=" * 60)
logger.info("Grablu Web Application 起動中...")
logger.info("=" * 60)
init_db()
logger.info("=" * 60)
logger.info("✓ アプリケーションの初期化が完了しました")
logger.info("=" * 60)

# テンプレート設定
templates = Jinja2Templates(directory="templates")

# セッション管理
SECRET_KEY = "grablu-secret-key-change-in-production-2026"  # 本番では環境変数から

# ベースURL（OAuth リダイレクト用）
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")

# 認証情報（環境変数または設定ファイルから読み込むべき）
USERNAME = "admin"
PASSWORD = "grablu2026"  # 本番環境では環境変数から取得


def get_current_user(request: Request) -> Optional[str]:
    """セッションから現在のユーザーを取得"""
    return request.session.get("username")


def get_current_user_id(request: Request) -> Optional[int]:
    """セッションから現在のユーザーIDを取得"""
    return request.session.get("user_id")


async def require_auth(request: Request) -> str:
    """認証必須のエンドポイント用"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です"
        )
    return username


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """ログイン画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
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


@app.get("/logout")
async def logout(request: Request):
    """ログアウト処理"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """ユーザー登録画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
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


@app.get("/register-complete", response_class=HTMLResponse)
async def register_complete(request: Request):
    """登録完了画面"""
    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
    return templates.TemplateResponse("register_complete.html", {
        "request": request,
        "dev_mode": dev_mode
    })


@app.get("/verify-email")
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


@app.get("/auth/google")
async def google_login(request: Request):
    """Google OAuth ログイン"""
    redirect_uri = f"{BASE_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """ホーム画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    
    # 団が未登録の場合は登録画面へリダイレクト
    if not guild_manager.is_registered():
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    # アクティブな団情報を取得
    active_guild = guild_manager.get_active_guild()
    
    # 履歴情報を取得
    tracker = MemberTracker(db, active_guild.id)
    
    history_info = {
        "last_event": None,
        "member_count": len(tracker.get_all_members()),
        "last_updated": None
    }
    
    # 最新イベント情報を取得
    events = tracker.get_all_events()
    if events:
        history_info["last_event"] = events[0]["event_number"]
        history_info["last_updated"] = events[0]["fetched_at"]
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "username": username,
            "history": history_info,
            "guild": {"guild_name": active_guild.name, "guild_id": active_guild.guild_id}
        }
    )


@app.get("/guild/register", response_class=HTMLResponse)
async def guild_register_page(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """団登録画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    guilds = guild_manager.get_all_guilds()
    
    return templates.TemplateResponse(
        "guild_register.html",
        {"request": request, "username": username, "guilds": guilds}
    )


@app.post("/guild/search")
async def search_guild(guild_name: str = Form(...), username: str = Depends(require_auth)):
    """団を検索"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            from selenium.webdriver.common.by import By
            from utils import wait_for_element, safe_js_click, remove_ads
            
            base_url = "https://gbfdata.com/ja"
            driver.get(base_url)
            remove_ads(driver)
            
            # 「総合」をクリック
            safe_js_click(driver, By.LINK_TEXT, "総合")
            remove_ads(driver)
            
            # 団名で検索
            search_box = wait_for_element(driver, By.NAME, "q")
            search_box.send_keys(guild_name)
            safe_js_click(driver, By.XPATH, '//form//button')
            
            # 検索結果を取得
            import time
            time.sleep(2)
            
            results = []
            rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            
            for row in rows[:10]:  # 上位10件
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 2:
                    name_cell = cols[0]
                    links = name_cell.find_elements(By.TAG_NAME, "a")
                    if links:
                        guild_link = links[0].get_attribute("href")
                        guild_text = links[0].text.strip()
                        
                        # guild_id を URL から抽出
                        if "/guild/" in guild_link:
                            guild_id = guild_link.split("/guild/")[-1]
                            results.append({
                                "guild_id": guild_id,
                                "guild_name": guild_text,
                                "guild_url": guild_link
                            })
            
            return {"status": "success", "results": results}
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"団検索エラー: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/guild/add")
async def add_guild(
    request: Request,
    guild_id: str = Form(...),
    guild_name: str = Form(...),
    guild_url: str = Form(...),
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """団を登録"""
    try:
        user_id = get_current_user_id(request)
        guild_manager = GuildManager(db, user_id)
        guild_manager.add_guild(guild_id, guild_name)
        
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"団登録エラー: {e}")
        raise HTTPException(status_code=500, detail="団の登録に失敗しました")


@app.post("/execute")
async def execute_scraping(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """団員データ取得実行"""
    try:
        logger.info(f"団員データ取得開始 (ユーザー: {username})")
        
        # 登録された団情報を取得
        user_id = get_current_user_id(request)
        guild_manager = GuildManager(db, user_id)
        active_guild = guild_manager.get_active_guild()
        
        if not active_guild:
            raise Exception("団が登録されていません")
        
        # 設定読み込み
        config = load_config()
        spreadsheet_url = config["spreadsheet"]["sheet_url"]
        sheet_name = config["spreadsheet"]["sheet_name"]
        guild_name = active_guild.name
        base_url = "https://gbfdata.com/ja"
        
        # Chromeオプション（ヘッドレスモード）
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # スクレイピング処理
            scraper = GuildScraper(driver)
            scraper.open_guild_page(guild_name=guild_name, base_url=base_url)
            event_number = scraper.get_event_number_from_dropdown()
            
            if event_number is None:
                raise Exception("イベント番号が取得できませんでした")
            
            # 取得済みチェック
            tracker = MemberTracker(db, active_guild.id)
            if tracker.is_already_fetched(event_number):
                logger.warning(f"第{event_number}回のデータは既に取得済みです")
                return {
                    "status": "warning",
                    "message": f"第{event_number}回のデータは既に取得済みです。",
                    "event_number": event_number
                }
            
            # データ取得
            members = scraper.scrape_member_table()
            
            # 名前変更検出
            name_changes = tracker.update_members(members)
            
            # イベントデータを保存
            tracker.save_event_data(event_number, members)
            
            # スプレッドシート書き込み（オプション）
            # writer = SpreadsheetWriter()
            # writer.write_to_spreadsheet(
            #     members,
            #     spreadsheet_url,
            #     sheet_name,
            #     event_number=event_number,
            #     name_changes=name_changes
            # )
            
            logger.info("団員データ取得完了")
            
            return {
                "status": "success",
                "message": f"第{event_number}回のデータを取得しました",
                "event_number": event_number,
                "member_count": len(members),
                "name_changes": len(name_changes)
            }
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        raise HTTPException(status_code=500, detail="データ取得に失敗しました")


@app.get("/members", response_class=HTMLResponse)
async def view_members(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """団員リスト表示画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    tracker = MemberTracker(db, active_guild.id)
    
    # 全イベントリストを取得
    events = tracker.get_all_events()
    
    # 最新イベントのデータを取得
    latest_event_data = None
    if events:
        latest_event_data = tracker.get_event_data(events[0]["event_number"])
    
    return templates.TemplateResponse(
        "members.html",
        {
            "request": request,
            "username": username,
            "guild": {"guild_name": active_guild.name, "guild_id": active_guild.guild_id},
            "events": events,
            "latest_event": latest_event_data
        }
    )


@app.get("/members/event/{event_number}")
async def get_event_members(request: Request, event_number: int, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """特定イベントの団員データを取得（API）"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        raise HTTPException(status_code=404, detail="団が登録されていません")
    
    tracker = MemberTracker(db, active_guild.id)
    event_data = tracker.get_event_data(event_number)
    
    if not event_data:
        raise HTTPException(status_code=404, detail="イベントデータが見つかりません")
    
    return event_data


@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """履歴・名前変更履歴画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    active_guild = guild_manager.get_active_guild()
    
    if not active_guild:
        return RedirectResponse(url="/guild/register", status_code=status.HTTP_302_FOUND)
    
    tracker = MemberTracker(db, active_guild.id)
    
    # 名前変更履歴を抽出
    from models import NameHistory, Member
    name_changes_query = db.query(
        NameHistory, Member
    ).join(
        Member, NameHistory.member_id == Member.id
    ).filter(
        Member.guild_id == active_guild.id
    ).order_by(
        NameHistory.changed_at.desc()
    ).all()
    
    name_changes = []
    for history, member in name_changes_query:
        name_changes.append({
            "player_id": member.player_id,
            "current_name": member.current_name,
            "old_name": history.old_name,
            "new_name": history.new_name,
            "last_changed": history.changed_at.strftime("%Y-%m-%d %H:%M")
        })
    
    total_members = len(tracker.get_all_members())
    
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "username": username,
            "name_changes": name_changes,
            "total_members": total_members
        }
    )


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """未認証の場合はログインページへリダイレクト"""
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """権限がない場合のエラーページ"""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "403",
            "error_icon": "🚫",
            "error_title": "アクセス権限がありません",
            "error_message": "このページを閲覧する権限がありません。管理者権限が必要なページです。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "管理者権限が必要な場合は、システム管理者にお問い合わせください。"
        },
        status_code=403
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """ページが見つからない場合のエラーページ"""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "404",
            "error_icon": "🔍",
            "error_title": "ページが見つかりません",
            "error_message": "お探しのページは存在しないか、移動または削除された可能性があります。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "URLが正しいかご確認ください。"
        },
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """サーバーエラーの場合のエラーページ"""
    logger.error(f"Internal Server Error: {str(exc)}", exc_info=True)
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": "500",
            "error_icon": "⚠️",
            "error_title": "サーバーエラーが発生しました",
            "error_message": "申し訳ございません。システムエラーが発生しました。しばらく経ってから再度お試しください。",
            "show_home_button": True,
            "show_login_button": False,
            "additional_info": "問題が続く場合は、システム管理者にお問い合わせください。"
        },
        status_code=500
    )


@app.get("/admin/test-email")
async def test_email_page(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """メールテスト画面（管理者のみ）"""
    # 管理者権限チェック
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    
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


@app.post("/admin/test-email/send")
async def test_email_send(
    request: Request,
    username: str = Depends(require_auth), 
    db: Session = Depends(get_db)
):
    """メールテスト送信API（管理者のみ）"""
    # 管理者権限チェック
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    
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
        send_verification_email(email, token, base_url)
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
