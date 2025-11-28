from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import re
import time
import gspread
import yaml
from oauth2client.service_account import ServiceAccountCredentials

def get_event_number_from_dropdown(driver):
    """<select id='day-select'> から '第n回' を取得"""
    select = Select(driver.find_element(By.ID, "day-select"))
    selected_option = select.first_selected_option
    text = selected_option.text.strip()  # 例：'78回 本戦終了'
    match = re.search(r'(\d+)回', text)
    if match:
        return int(match.group(1))
    else:
        return None  # 見つからない場合


def load_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def write_to_spreadsheet(data, spreadsheet_url, sheet_name="団員管理", event_number=None):

    # スプレッドシート認証
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # シート取得
    sheet = client.open_by_url(spreadsheet_url).worksheet(sheet_name)

    # 名前一覧（B列）を取得（1行目はヘッダー）
    name_cells = sheet.col_values(2)
    name_list = [name.strip() for name in name_cells[1:]]  # indexは2行目から

    # 新しい順位列の挿入（C列に挿入 → 既存列が右にずれる）
    new_col_title = f"第{event_number}回"
    sheet.insert_cols([[new_col_title] + [""] * len(name_list)], col=3)

    # データの書き込み
    for name, rank in data:
        name = name.strip()
        if name in name_list:
            row_index = name_list.index(name) + 2  # 1ベース + ヘッダー
            sheet.update_cell(row_index, 3, rank)
        else:
            # 新規団員の行を末尾に追加
            new_row_index = len(name_list) + 2
            sheet.update_cell(new_row_index, 2, name)  # 名前（B列）
            sheet.update_cell(new_row_index, 3, rank)  # 新しい順位（C列）
            name_list.append(name)

# -------------------------------
# 共通ユーティリティ
# -------------------------------

def remove_ads(driver):
    """広告要素を非表示にするJSスクリプトを実行"""
    driver.execute_script("""
        let ads = document.querySelectorAll('.adsbygoogle, .ad, iframe, .banner');
        ads.forEach(ad => ad.style.display = 'none');
    """)


def wait_for_element(driver, by, value, timeout=10):
    """要素の表示を待って返す"""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def safe_click_element(driver, element):
    """取得済みのWebElementに対して安全にクリックする"""
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", element)


def safe_js_click(driver, by, value):
    """スクロール＆JSでクリック"""
    element = wait_for_element(driver, by, value)
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", element)


# -------------------------------
# スクレイピング本体処理
# -------------------------------

def open_guild_page(driver, guild_name,base_url):
    """総合ページからギルド名で検索し、団員一覧を開く"""
    driver.get(base_url)
    remove_ads(driver)

    # 「総合」をクリック
    safe_js_click(driver, By.LINK_TEXT, "総合")
    remove_ads(driver)

    # ギルド名で検索
    search_box = wait_for_element(driver, By.NAME, "q")
    search_box.send_keys(guild_name)
    safe_js_click(driver, By.XPATH, '//form//button')

    # ギルド行を取得
    row = wait_for_element(
        driver, By.XPATH,
        f'//tr[td/a[contains(text(), "{guild_name}")]]'
    )
    links = row.find_elements(By.TAG_NAME, "a")
    if len(links) < 2:
        raise Exception("団員一覧リンクが見つかりません")

    remove_ads(driver)
    safe_click_element(driver, links[1])
    remove_ads(driver)



def scrape_member_table(driver):
    """団員テーブルから名前・順位を取得"""
    wait_for_element(driver, By.CSS_SELECTOR, "table.table")
    results = []

    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 3:
            name = cols[0].text.strip()
            rank = cols[2].text.strip()
            results.append((name, rank))
    return results


# -------------------------------
# メイン関数
# -------------------------------

def main():
    config = load_config()
    # 各項目の取得
    spreadsheet_url = config["spreadsheet"]["url"]
    sheet_name = config["spreadsheet"]["sheet_name"]
    guild_name = config["guild"]["name"]
    base_url = config["site"]["base_url"]

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        open_guild_page(driver, guild_name=guild_name,base_url=base_url)
        event_number = get_event_number_from_dropdown(driver)
        members = scrape_member_table(driver)
        for name, rank in members:
            print(f"{name}: {rank}")

        write_to_spreadsheet(members, spreadsheet_url, sheet_name,event_number=event_number)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
