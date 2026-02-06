"""
スクレイピングルーター
団員データの取得処理
"""
import logging
from typing import Dict, List

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from database import get_db
from guild_manager import GuildManager
from member_tracker import MemberTracker
from scraper import GuildScraper
from config import load_config

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/execute")
async def execute_scraping(
    request: Request,
    username: str = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict:
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
            
            # 利用可能な全イベントを取得
            available_events = scraper.get_all_available_events()
            
            if not available_events:
                raise Exception("利用可能なイベントが見つかりません")
            
            # 既にDB登録済みのイベントを取得
            tracker = MemberTracker(db, active_guild.id)
            registered_events = tracker.get_registered_event_numbers()
            
            # 未登録のイベントを抽出（降順でソート：新しい回から取得）
            unregistered_events = [e for e in available_events if e not in registered_events]
            unregistered_events.sort(reverse=True)
            
            logger.info(f"利用可能イベント: {len(available_events)}回分")
            logger.info(f"登録済みイベント: {len(registered_events)}回分")
            logger.info(f"未登録イベント: {len(unregistered_events)}回分")
            
            if not unregistered_events:
                logger.info("全てのイベントデータは取得済みです")
                return {
                    "status": "info",
                    "message": "全てのイベントデータは既に取得済みです。",
                    "available_events": len(available_events),
                    "registered_events": len(registered_events)
                }
            
            # 未登録イベントを順番に取得（最大5件まで）
            max_fetch = min(5, len(unregistered_events))
            results = []
            successfully_fetched = 0
            
            for i, event_number in enumerate(unregistered_events[:max_fetch]):
                logger.info(f"第{event_number}回のデータを取得中... ({successfully_fetched+1}/{max_fetch})")
                
                # 既に保存済みか再確認（並行実行の場合に備えて）
                if tracker.is_already_fetched(event_number):
                    logger.info(f"第{event_number}回は既に保存済みのためスキップします")
                    continue
                
                # イベントを選択
                if not scraper.select_event(event_number):
                    logger.warning(f"第{event_number}回の選択に失敗しました")
                    continue
                
                # データ取得
                members = scraper.scrape_member_table()
                
                # 名前変更検出
                name_changes = tracker.update_members(members)
                
                # イベントデータを保存（再度チェックしてから保存）
                if not tracker.is_already_fetched(event_number):
                    tracker.save_event_data(event_number, members)
                    
                    results.append({
                        "event_number": event_number,
                        "member_count": len(members),
                        "name_changes": len(name_changes)
                    })
                    
                    successfully_fetched += 1
                    logger.info(f"第{event_number}回のデータ取得完了 (団員: {len(members)}人, 名前変更: {len(name_changes)}件)")
                    
                    # 目標数に到達したら終了
                    if successfully_fetched >= max_fetch:
                        break
                else:
                    logger.info(f"第{event_number}回は既に保存済みのためスキップします")
            
            remaining = len(unregistered_events) - successfully_fetched
            message = f"{successfully_fetched}回分のデータを取得しました。"
            if remaining > 0:
                message += f" (残り未登録: {remaining}回分)"
            
            return {
                "status": "success",
                "message": message,
                "fetched_events": results,
                "remaining_events": remaining
            }
            
        finally:
            driver.quit()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        error_message = str(e)
        if "duplicate key" in error_message.lower():
            return {
                "status": "error",
                "message": "データの重複エラーが発生しました。既に取得済みのデータがあります。"
            }
        elif "timeout" in error_message.lower():
            return {
                "status": "error", 
                "message": "接続がタイムアウトしました。しばらく待ってから再試行してください。"
            }
        else:
            return {
                "status": "error",
                "message": f"データ取得中にエラーが発生しました: {error_message[:100]}"
            }
