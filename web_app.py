"""
Grablu Web Application
FastAPIベースのWebアプリケーション
"""
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Depends, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature
import secrets

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

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(title="Grablu 団員管理")

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
serializer = URLSafeTimedSerializer(SECRET_KEY)

# 認証情報（環境変数または設定ファイルから読み込むべき）
USERNAME = "admin"
PASSWORD = "grablu2026"  # 本番環境では環境変数から取得


def create_session_token(username: str) -> str:
    """セッショントークンを作成"""
    return serializer.dumps(username, salt="session")


def verify_session_token(token: str) -> Optional[str]:
    """セッショントークンを検証"""
    try:
        username = serializer.loads(token, salt="session", max_age=86400)  # 24時間有効
        return username
    except BadSignature:
        return None


def get_current_user(session: Optional[str] = Cookie(None)) -> Optional[str]:
    """セッションから現在のユーザーを取得"""
    if session:
        return verify_session_token(session)
    return None


def require_auth(session: Optional[str] = Cookie(None)) -> str:
    """認証必須のエンドポイント用"""
    username = get_current_user(session)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です"
        )
    return username


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session: Optional[str] = Cookie(None)):
    """ログイン画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(session):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """ログイン処理"""
    # データベースからメールアドレスでユーザーを検索
    user = db.query(User).filter(User.email == email).first()
    
    if user and user.is_active and user.verify_password(password):
        # 最終ログイン日時を更新
        user.last_login = datetime.now()
        db.commit()
        
        token = create_session_token(user.username)
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            max_age=86400,  # 24時間
            samesite="lax"
        )
        return response
    else:
        return RedirectResponse(
            url="/login?error=1",
            status_code=status.HTTP_302_FOUND
        )


@app.get("/logout")
async def logout():
    """ログアウト処理"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session")
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session: Optional[str] = Cookie(None)):
    """ユーザー登録画面"""
    # 既にログイン済みの場合はホームへリダイレクト
    if get_current_user(session):
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
    
    # 新規ユーザー作成（メール未認証状態）
    new_user = User(
        username=username,
        email=email,
        hashed_password=User.get_password_hash(password),
        is_active=False,  # メール認証後にTrueに変更
        email_verified=False,
        verification_token=verification_token,
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    
    logger.info(f"新規ユーザー登録: {username} ({email})")
    
    # 認証メールを送信
    base_url = os.environ.get("BASE_URL", "http://localhost:8080")
    send_verification_email(email, verification_token, base_url)
    
    # 登録完了ページにリダイレクト
    return RedirectResponse(
        url="/register-complete",
        status_code=status.HTTP_302_FOUND
    )


@app.get("/register-complete", response_class=HTMLResponse)
async def register_complete(request: Request):
    """登録完了画面"""
    return templates.TemplateResponse("register_complete.html", {"request": request})


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
    redirect_uri = request.url_for('google_callback')
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
        session_token = create_session_token(user.username)
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            max_age=86400,
            samesite="lax"
        )
        return response
        
    except Exception as e:
        logger.error(f"Google OAuth エラー: {e}")
        return RedirectResponse(
            url="/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """ホーム画面"""
    guild_manager = GuildManager(db)
    
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
    guild_manager = GuildManager(db)
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
    guild_id: str = Form(...),
    guild_name: str = Form(...),
    guild_url: str = Form(...),
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """団を登録"""
    try:
        guild_manager = GuildManager(db)
        guild_manager.add_guild(guild_id, guild_name)
        
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"団登録エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute")
async def execute_scraping(username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """団員データ取得実行"""
    try:
        logger.info(f"団員データ取得開始 (ユーザー: {username})")
        
        # 登録された団情報を取得
        guild_manager = GuildManager(db)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/members", response_class=HTMLResponse)
async def view_members(request: Request, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """団員リスト表示画面"""
    guild_manager = GuildManager(db)
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
async def get_event_members(event_number: int, username: str = Depends(require_auth), db: Session = Depends(get_db)):
    """特定イベントの団員データを取得（API）"""
    guild_manager = GuildManager(db)
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
    guild_manager = GuildManager(db)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
