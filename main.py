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

def write_to_spreadsheet(data, spreadsheet_url, sheet_name="Sheet1", event_number=None):

    # 認証処理
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(spreadsheet_url).worksheet(sheet_name)

    # 全データ取得
    all_values = sheet.get_all_values()
    if not all_values:
        raise ValueError("シートが空です")

    header = all_values[0]
    name_list = [row[1] for row in all_values[1:] if len(row) > 1]  # B列（名前）

    # イベントタイトル（列のタイトル）
    new_col_title = f"第{event_number}回" if event_number else "新規"

    # C列に新しい列を挿入（順位列の先頭）
    sheet.insert_cols([[new_col_title]], col=3)

    # 書き込み処理
    for name, rank in data:
        try:
            row_index = name_list.index(name) + 2  # ヘッダ+1行目から開始
        except ValueError:
            # 新規追加（A: 空, B: 名前, C: 順位）
            sheet.append_row(["", name, rank])
        else:
            # 既存行 → C列に順位追加
            sheet.update_cell(row_index, 3, rank)

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
