"""
Grablu - グラブル団員管理ツール
メインエントリーポイント
"""
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import yaml

from config import load_config
from scraper import GuildScraper
from spreadsheet import SpreadsheetWriter

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('grablu.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger.info("処理を開始します")
    
    try:
        # 設定読み込み
        config = load_config()
        spreadsheet_url = config["spreadsheet"]["url"]
        sheet_name = config["spreadsheet"]["sheet_name"]
        guild_name = config["guild"]["name"]
        base_url = config["site"]["base_url"]

        # Chromeドライバー起動（Selenium Managerが自動で最新版を管理）
        driver = webdriver.Chrome()
        logger.info("Chromeドライバーを起動しました")

        try:
            # スクレイピング処理
            scraper = GuildScraper(driver)
            scraper.open_guild_page(guild_name=guild_name, base_url=base_url)
            event_number = scraper.get_event_number_from_dropdown()
            
            if event_number is None:
                logger.error("イベント番号が取得できません。処理を中断します")
                return
            
            members = scraper.scrape_member_table()
            
            # 取得データ表示
            for name, rank in members:
                print(f"{name}: {rank}")

            # スプレッドシート書き込み
            writer = SpreadsheetWriter()
            writer.write_to_spreadsheet(
                members, 
                spreadsheet_url, 
                sheet_name, 
                event_number=event_number
            )
            logger.info("処理が完了しました")

        finally:
            driver.quit()
            logger.info("Chromeドライバーを終了しました")
    
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML解析エラー: {e}")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()