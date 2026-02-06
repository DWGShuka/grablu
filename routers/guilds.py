"""
団（ギルド）管理ルーター
団の登録、検索、追加
"""
import logging
import time
from typing import List, Dict

from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from database import get_db
from guild_manager import GuildManager
from utils import wait_for_element, safe_js_click, remove_ads

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guild")
templates = Jinja2Templates(directory="templates")


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


@router.get("/register", response_class=HTMLResponse)
async def guild_register_page(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """団登録画面"""
    user_id = get_current_user_id(request)
    guild_manager = GuildManager(db, user_id)
    
    # ユーザーの所属団のみを取得
    active_guild = guild_manager.get_active_guild()
    guilds = [active_guild] if active_guild else []
    
    return templates.TemplateResponse(
        "guild_register.html",
        {"request": request, "username": username, "guilds": guilds}
    )


@router.post("/search")
async def search_guild(
    guild_name: str = Form(...),
    username: str = Depends(require_auth)
) -> Dict:
    """団を検索してIDと名前を取得"""
    driver = None
    try:
        logger.info(f"団検索開始: {guild_name}")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        logger.info("Chromeドライバー起動中...")
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chromeドライバー起動完了")
        
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
        
        logger.info(f"団検索完了: {len(results)}件")
        return {"status": "success", "results": results}
            
    except Exception as e:
        logger.error(f"団検索エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"団検索に失敗しました: {str(e)}"
        )
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chromeドライバー終了")
            except Exception as e:
                logger.error(f"ドライバー終了エラー: {e}")


@router.post("/add")
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
