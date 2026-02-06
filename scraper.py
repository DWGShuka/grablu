"""Webスクレイピング機能"""
import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from utils import remove_ads, wait_for_element, safe_js_click, safe_click_element

logger = logging.getLogger(__name__)


class GuildScraper:
    """ギルド情報のスクレイピングクラス"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def get_event_number_from_dropdown(self):
        """<select id='day-select'> から '第n回' を取得"""
        try:
            select = Select(self.driver.find_element(By.ID, "day-select"))
            selected_option = select.first_selected_option
            text = selected_option.text.strip()  # 例：'78回 本戦終了'
            match = re.search(r'(\d+)回', text)
            if match:
                event_num = int(match.group(1))
                logger.info(f"イベント番号を取得しました: 第{event_num}回")
                return event_num
            else:
                logger.warning("イベント番号が見つかりません")
                return None
        except Exception as e:
            logger.error(f"ドロップダウン取得エラー: {e}")
            raise
    
    def get_all_available_events(self):
        """ドロップダウンから利用可能な全イベント番号を取得"""
        try:
            select = Select(self.driver.find_element(By.ID, "day-select"))
            options = select.options
            
            event_numbers = []
            for option in options:
                text = option.text.strip()
                match = re.search(r'(\d+)回', text)
                if match:
                    event_num = int(match.group(1))
                    event_numbers.append(event_num)
            
            logger.info(f"利用可能なイベント: {len(event_numbers)}回分 ({min(event_numbers)}回〜{max(event_numbers)}回)")
            return sorted(event_numbers)
        except Exception as e:
            logger.error(f"イベント一覧取得エラー: {e}")
            raise
    
    def select_event(self, event_number: int):
        """ドロップダウンから特定のイベントを選択"""
        try:
            select = Select(self.driver.find_element(By.ID, "day-select"))
            options = select.options
            
            for option in options:
                text = option.text.strip()
                match = re.search(r'(\d+)回', text)
                if match and int(match.group(1)) == event_number:
                    select.select_by_visible_text(text)
                    logger.info(f"第{event_number}回を選択しました")
                    # ページが更新されるまで待機
                    import time
                    time.sleep(1)
                    
                    # 実際に選択されたか確認
                    selected = self.get_event_number_from_dropdown()
                    if selected != event_number:
                        logger.warning(f"選択が反映されませんでした: 期待{event_number}回, 実際{selected}回")
                        return False
                    return True
            
            logger.warning(f"第{event_number}回が見つかりません")
            return False
        except Exception as e:
            logger.error(f"イベント選択エラー: {e}")
            raise
    
    def open_guild_page(self, guild_name, base_url):
        """総合ページからギルド名で検索し、団員一覧を開く"""
        try:
            self.driver.get(base_url)
            logger.info(f"ベースURLにアクセスしました: {base_url}")
            remove_ads(self.driver)

            # 「総合」をクリック
            safe_js_click(self.driver, By.LINK_TEXT, "総合")
            logger.info("「総合」をクリックしました")
            remove_ads(self.driver)

            # ギルド名で検索
            search_box = wait_for_element(self.driver, By.NAME, "q")
            search_box.send_keys(guild_name)
            safe_js_click(self.driver, By.XPATH, '//form//button')
            logger.info(f"ギルド名で検索しました: {guild_name}")

            # ギルド行を取得
            row = wait_for_element(
                self.driver, By.XPATH,
                f'//tr[td/a[contains(text(), "{guild_name}")]]'
            )
            links = row.find_elements(By.TAG_NAME, "a")
            if len(links) < 2:
                raise Exception("団員一覧リンクが見つかりません")

            remove_ads(self.driver)
            safe_click_element(self.driver, links[1])
            logger.info("団員一覧ページを開きました")
            remove_ads(self.driver)
        except Exception as e:
            logger.error(f"ギルドページ開きエラー: {e}")
            raise
    
    def scrape_member_table(self):
        """団員テーブルから名前・ID・順位を取得"""
        try:
            wait_for_element(self.driver, By.CSS_SELECTOR, "table.table")
            results = []

            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 3:
                    # 名前とIDを取得
                    name_col = cols[0]
                    name = name_col.text.strip()
                    
                    # IDをリンクから取得
                    player_id = None
                    links = name_col.find_elements(By.TAG_NAME, "a")
                    if links:
                        href = links[0].get_attribute("href")
                        # https://gbfdata.com/ja/user/21032052 からIDを抽出
                        if href and "/user/" in href:
                            player_id = href.split("/user/")[-1]
                    
                    rank = cols[2].text.strip()
                    results.append({
                        "name": name,
                        "player_id": player_id,
                        "rank": rank
                    })
            
            logger.info(f"{len(results)}人の団員データを取得しました")
            return results
        except Exception as e:
            logger.error(f"テーブルスクレイピングエラー: {e}")
            raise
