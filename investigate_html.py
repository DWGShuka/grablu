"""HTML構造調査スクリプト"""
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
import yaml

from config import load_config
from scraper import GuildScraper
from utils import wait_for_element

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def investigate_member_table():
    """団員テーブルのHTML構造を詳しく調査"""
    config = load_config()
    guild_name = config["guild"]["name"]
    base_url = config["member_stats"]["guild_database_url"]
    
    # 調査対象
    TARGET_NAME = "藤田ことね"
    TARGET_ID = "21032052"
    
    driver = webdriver.Chrome()
    
    try:
        # ギルドページを開く
        scraper = GuildScraper(driver)
        scraper.open_guild_page(guild_name=guild_name, base_url=base_url)
        
        # テーブルを待機
        wait_for_element(driver, By.CSS_SELECTOR, "table.table")
        
        print("\n" + "="*80)
        print(f"団員テーブルのHTML構造調査（対象: {TARGET_NAME} / ID: {TARGET_ID}）")
        print("="*80)
        
        # テーブル全体のHTML取得
        table = driver.find_element(By.CSS_SELECTOR, "table.table")
        
        # ヘッダー行を確認
        print("\n【ヘッダー行】")
        thead = table.find_element(By.TAG_NAME, "thead")
        headers = thead.find_elements(By.TAG_NAME, "th")
        for i, th in enumerate(headers):
            print(f"  列{i}: {th.text}")
        
        # 全行から藤田ことねを探す
        print(f"\n【{TARGET_NAME} の行を検索中...】")
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
        
        target_row = None
        for idx, row in enumerate(rows):
            cols = row.find_elements(By.TAG_NAME, "td")
            if cols and TARGET_NAME in cols[0].text:
                target_row = row
                print(f"✓ 見つかりました: {idx + 1}行目")
                break
        
        if target_row:
            print(f"\n【{TARGET_NAME} の行の詳細】")
            print(f"行全体のHTML:\n{target_row.get_attribute('outerHTML')}\n")
            
            cols = target_row.find_elements(By.TAG_NAME, "td")
            for col_idx, col in enumerate(cols):
                print(f"\n  列{col_idx}:")
                print(f"    テキスト: {col.text}")
                print(f"    innerHTML: {col.get_attribute('innerHTML')}")
                
                # リンク要素を確認
                links = col.find_elements(By.TAG_NAME, "a")
                if links:
                    for link_idx, link in enumerate(links):
                        href = link.get_attribute("href")
                        text = link.text
                        print(f"    <a>リンク{link_idx}:")
                        print(f"      href: {href}")
                        print(f"      text: {text}")
                        
                        # IDが含まれているか確認
                        if TARGET_ID in str(href):
                            print(f"      ★★★ IDを発見！ ★★★")
        else:
            print(f"✗ {TARGET_NAME} が見つかりませんでした")
            print("\n【最初の3行を表示】")
            for idx, row in enumerate(rows[:3]):
                cols = row.find_elements(By.TAG_NAME, "td")
                if cols:
                    print(f"  行{idx+1}: {cols[0].text}")
        
        # ページ全体のURLも確認
        print(f"\n【現在のページURL】\n{driver.current_url}")
        
        print("\n" + "="*80)
        print("調査完了")
        print("="*80)
        
    except Exception as e:
        logger.error(f"調査エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nEnterキーを押すとブラウザを閉じます...")
        driver.quit()


if __name__ == "__main__":
    investigate_member_table()
