"""ユーティリティ関数"""
import logging
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def remove_ads(driver):
    """広告要素を非表示にするJSスクリプトを実行"""
    driver.execute_script("""
        let ads = document.querySelectorAll('.adsbygoogle, .ad, iframe, .banner');
        ads.forEach(ad => ad.style.display = 'none');
    """)


def wait_for_element(driver, by, value, timeout=10):
    """要素の表示を待って返す"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception as e:
        logger.error(f"要素待機タイムアウト ({by}='{value}'): {e}")
        raise


def safe_click_element(driver, element):
    """取得済みのWebElementに対して安全にクリックする"""
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", element)


def safe_js_click(driver, by, value):
    """セレクターから要素を取得してクリック"""
    element = wait_for_element(driver, by, value)
    safe_click_element(driver, element)
