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
        """団員テーブルから名前・順位を取得"""
        try:
            wait_for_element(self.driver, By.CSS_SELECTOR, "table.table")
            results = []

            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 3:
                    name = cols[0].text.strip()
                    rank = cols[2].text.strip()
                    results.append((name, rank))
            
            logger.info(f"{len(results)}人の団員データを取得しました")
            return results
        except Exception as e:
            logger.error(f"テーブルスクレイピングエラー: {e}")
            raise
