"""
スクレイピングサービス
団員データ取得に関するビジネスロジック
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy.orm import Session

from config import settings
from models import Guild
from guild_manager import GuildManager
from member_tracker import MemberTracker
from scraper import GuildScraper
from exceptions import GuildNotFoundError, ScrapingError

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """スクレイピング結果"""
    status: str  # "success", "info", "error"
    message: str
    fetched_events: List[Dict] = None
    remaining_events: int = 0
    available_events: int = 0
    registered_events: int = 0
    
    def __post_init__(self):
        if self.fetched_events is None:
            self.fetched_events = []


class ScrapingService:
    """スクレイピング処理を管理するサービス"""
    
    def __init__(self, db: Session, user_id: int):
        """
        Args:
            db: データベースセッション
            user_id: ユーザーID
        """
        self.db = db
        self.user_id = user_id
        self.guild_manager = GuildManager(db, user_id)
        self.tracker: Optional[MemberTracker] = None
        self.active_guild: Optional[Guild] = None
        self.base_url = settings.gbfdata_base_url
        self.max_fetch = settings.scraping_max_fetch
    
    def _setup_chrome_driver(self) -> webdriver.Chrome:
        """Chromeドライバーをセットアップ（ヘッドレスモード）"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=chrome_options)
    
    def _validate_guild(self) -> Guild:
        """団情報のバリデーション
        
        Returns:
            Guild: アクティブな団情報
            
        Raises:
            GuildNotFoundError: 団が登録されていない場合
        """
        self.active_guild = self.guild_manager.get_active_guild()
        if not self.active_guild:
            raise GuildNotFoundError()
        
        self.tracker = MemberTracker(self.db, self.active_guild.id)
        return self.active_guild
    
    def _get_unregistered_events(
        self,
        available_events: List[int],
        registered_events: List[int]
    ) -> List[int]:
        """未登録のイベントを抽出
        
        Args:
            available_events: 利用可能な全イベント番号
            registered_events: 既に登録済みのイベント番号
            
        Returns:
            未登録のイベント番号リスト（新しい順）
        """
        unregistered = [e for e in available_events if e not in registered_events]
        unregistered.sort(reverse=True)  # 新しい回から取得
        return unregistered
    
    def _fetch_single_event(
        self,
        scraper: GuildScraper,
        event_number: int
    ) -> Optional[Dict]:
        """単一イベントのデータを取得
        
        Args:
            scraper: スクレイパーインスタンス
            event_number: イベント番号
            
        Returns:
            取得結果の辞書、失敗時はNone
        """
        # 既に保存済みか再確認（並行実行対策）
        if self.tracker.is_already_fetched(event_number):
            logger.info(f"第{event_number}回は既に保存済みのためスキップします")
            return None
        
        # イベントを選択
        if not scraper.select_event(event_number):
            logger.warning(f"第{event_number}回の選択に失敗しました")
            return None
        
        # データ取得
        members = scraper.scrape_member_table()
        
        # 名前変更検出
        name_changes = self.tracker.update_members(members)
        
        # イベントデータを保存（再度チェックしてから保存）
        if not self.tracker.is_already_fetched(event_number):
            self.tracker.save_event_data(event_number, members)
            
            logger.info(
                f"第{event_number}回のデータ取得完了 "
                f"(団員: {len(members)}人, 名前変更: {len(name_changes)}件)"
            )
            
            return {
                "event_number": event_number,
                "member_count": len(members),
                "name_changes": len(name_changes)
            }
        else:
            logger.info(f"第{event_number}回は既に保存済みのためスキップします")
            return None
    
    def execute_batch_scraping(self) -> ScrapingResult:
        """団員データのバッチ取得を実行
        
        最大5件の未登録イベントデータを取得
        
        Returns:
            ScrapingResult: 取得結果
        """
        try:
            # 団情報のバリデーション
            guild = self._validate_guild()
            logger.info(f"団員データ取得開始 (団: {guild.name})")
            
            driver = self._setup_chrome_driver()
            
            try:
                # スクレイピング処理の初期化
                scraper = GuildScraper(driver)
                scraper.open_guild_page(guild_name=guild.name, base_url=self.base_url)
                
                # 利用可能な全イベントを取得
                available_events = scraper.get_all_available_events()
                
                if not available_events:
                    raise ValueError("利用可能なイベントが見つかりません")
                
                # 既にDB登録済みのイベントを取得
                registered_events = self.tracker.get_registered_event_numbers()
                
                # 未登録のイベントを抽出
                unregistered_events = self._get_unregistered_events(
                    available_events,
                    registered_events
                )
                
                logger.info(f"利用可能イベント: {len(available_events)}回分")
                logger.info(f"登録済みイベント: {len(registered_events)}回分")
                logger.info(f"未登録イベント: {len(unregistered_events)}回分")
                
                # 全て取得済みの場合
                if not unregistered_events:
                    logger.info("全てのイベントデータは取得済みです")
                    return ScrapingResult(
                        status="info",
                        message="全てのイベントデータは既に取得済みです。",
                        available_events=len(available_events),
                        registered_events=len(registered_events)
                    )
                
                # 未登録イベントを順番に取得（最大5件まで）
                max_fetch = min(self.max_fetch, len(unregistered_events))
                results = []
                successfully_fetched = 0
                
                for event_number in unregistered_events[:max_fetch]:
                    logger.info(
                        f"第{event_number}回のデータを取得中... "
                        f"({successfully_fetched+1}/{max_fetch})"
                    )
                    
                    result = self._fetch_single_event(scraper, event_number)
                    if result:
                        results.append(result)
                        successfully_fetched += 1
                        
                        # 目標数に到達したら終了
                        if successfully_fetched >= max_fetch:
                            break
                
                remaining = len(unregistered_events) - successfully_fetched
                message = f"{successfully_fetched}回分のデータを取得しました。"
                if remaining > 0:
                    message += f" (残り未登録: {remaining}回分)"
                
                return ScrapingResult(
                    status="success",
                    message=message,
                    fetched_events=results,
                    remaining_events=remaining
                )
                
            finally:
                driver.quit()
                
        except GuildNotFoundError:
            raise
        except Exception as e:
            # その他のエラー
            logger.error(f"エラーが発生しました: {e}", exc_info=True)
            error_message = str(e)
            
            if "duplicate key" in error_message.lower():
                message = "データの重複エラーが発生しました。既に取得済みのデータがあります。"
            elif "timeout" in error_message.lower():
                message = "接続がタイムアウトしました。しばらく待ってから再試行してください。"
            else:
                message = f"データ取得中にエラーが発生しました: {error_message[:100]}"
            
            return ScrapingResult(
                status="error",
                message=message
            )
