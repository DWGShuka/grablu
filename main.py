from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

def main():
    # ─── Google認証
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    gc = gspread.authorize(creds)
    sheet = gc.open("GBF団員一覧").sheet1

    # ─── セレン操作開始
    driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.get("https://gbfdata.com/ja")
    
    # 総合 → しゃる鯖 検索
    driver.find_element(...総合タブのセレクタ...).click()
    time.sleep(1)
    search_box = driver.find_element(...検索入力のセレクタ...)
    search_box.send_keys("しゃる鯖")
    search_box.submit()
    time.sleep(2)

    # 団員一覧へリンクをクリック
    driver.find_element(...団員一覧リンクのセレクタ...).click()
    time.sleep(2)

    # ページ取得＆スクレイピング
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.select_one('table')  # 適切なセレクタ調整
    rows = [
        [td.get_text(strip=True) for td in tr.find_all('td')]
        for tr in table.find_all('tr')
    ]
    
    # ─── Googleスプレッドシートに転記
    sheet.clear()
    sheet.update('A1', [rows[0]] + rows[1:])
    driver.quit()

if __name__ == "__main__":
    main()
