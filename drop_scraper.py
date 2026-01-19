"""ドロップ統計用のWebスクレイピング機能"""
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from utils import wait_for_element, remove_ads

logger = logging.getLogger(__name__)


class DropScraper:
    """ドロップデータのスクレイピングクラス"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def scrape_drop_data(self, url, username=None, password=None):
        """
        ドロップデータを取得
        
        Args:
            url: スクレイピング対象のURL
            username: ログインユーザー名（メールアドレス）
            password: ログインパスワード
        
        Returns:
            dict: {
                'cumulative': 累計データ（同じ構造を繰り返す）,
                'monthly': 月データ
            }
            各データ内：{
                'trials': 試行回数,
                'blue_chest_count': つよバハ青箱ドロップ回数,
                'hihi_count': ヒヒイロカネドロップ回数
            }
        """
        try:
            self.driver.get(url)
            logger.info(f"URLにアクセスしました: {url}")
            time.sleep(2)  # ページ読み込み待機
            
            # ログイン処理
            if username and password:
                try:
                    logger.info("ログイン処理を開始します")
                    time.sleep(2)
                    
                    # 1. ログインモーダルを表示するボタンをクリック
                    login_button_modal = wait_for_element(
                        self.driver,
                        By.XPATH,
                        "//a[@data-bs-toggle='modal'][@data-bs-target='#loginModal']",
                        timeout=10
                    )
                    login_button_modal.click()
                    logger.info("ログインフォームのボタンをクリックしました")
                    
                    time.sleep(2)
                    
                    # 2. メールアドレス入力欄
                    email_input = wait_for_element(
                        self.driver,
                        By.ID,
                        "username",
                        timeout=10
                    )
                    email_input.clear()
                    email_input.send_keys(username)
                    logger.info("メールアドレスを入力しました")
                    
                    time.sleep(1)
                    
                    # 3. パスワード入力欄
                    password_input = wait_for_element(
                        self.driver,
                        By.ID,
                        "password",
                        timeout=10
                    )
                    password_input.clear()
                    password_input.send_keys(password)
                    logger.info("パスワードを入力しました")
                    
                    time.sleep(1)
                    
                    # 4. ログインボタンをクリック
                    login_submit_button = wait_for_element(
                        self.driver,
                        By.XPATH,
                        "//button[@type='submit'][contains(@class, 'btn-primary')]",
                        timeout=10
                    )
                    login_submit_button.click()
                    logger.info("ログインボタンをクリックしました")
                    
                    # ログイン完了待機
                    time.sleep(3)
                    logger.info("ログインが完了しました")
                    
                    # ログイン後、データページに移動
                    self.driver.get(url)
                    logger.info(f"ログイン後、URLに移動しました: {url}")
                    time.sleep(3)
                    
                except Exception as e:
                    logger.warning(f"ログイン処理中にエラー: {e}")
                    import traceback
                    traceback.print_exc()
                    logger.info("ページロードを継続します")
            
            remove_ads(self.driver)
            
            # マルチ選択ドロップダウンで「つよばは」を選択
            try:
                multi_dropdown = wait_for_element(self.driver, By.CSS_SELECTOR, "select", timeout=5)
                select_multi = Select(multi_dropdown)
                
                # 「つよばは」を選択（オプションのテキストで検索）
                for option in select_multi.options:
                    if "つよばは" in option.text or "つよバハ" in option.text:
                        select_multi.select_by_visible_text(option.text)
                        logger.info(f"マルチを選択: {option.text}")
                        break
                
                time.sleep(2)  # データ更新待機
            except Exception as e:
                logger.warning(f"マルチ選択スキップ（デフォルト値を使用）: {e}")
            
            # 累計データを取得
            cumulative_data = self._get_aggregated_data("累計")
            logger.info(f"累計データ取得完了: {cumulative_data}")
            
            # 月データを取得
            monthly_data = self._get_aggregated_data("月")
            logger.info(f"月データ取得完了: {monthly_data}")
            
            return {
                'cumulative': cumulative_data,
                'monthly': monthly_data
            }
            
        except Exception as e:
            logger.error(f"スクレイピングエラー: {e}")
            raise
    
    def _get_aggregated_data(self, aggregate_type):
        """
        指定した集計方法でドロップデータを取得
        
        Args:
            aggregate_type: "累計" または "月"
        
        Returns:
            dict: {
                'trials': 試行回数,
                'blue_chest_count': つよバハ青箱ドロップ回数,
                'hihi_count': ヒヒイロカネドロップ回数
            }
        """
        try:
            # 集計方法ドロップダウンで指定のタイプを選択
            try:
                dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select")
                if len(dropdowns) >= 2:
                    select_aggregate = Select(dropdowns[1])
                    
                    # 指定タイプを選択
                    for option in select_aggregate.options:
                        if aggregate_type in option.text:
                            select_aggregate.select_by_visible_text(option.text)
                            logger.info(f"集計方法を変更: {option.text}")
                            break
                    
                    time.sleep(2)  # データ更新待機
            except Exception as e:
                logger.warning(f"集計方法変更スキップ: {e}")
            
            remove_ads(self.driver)
            logger.info(f"{aggregate_type}データを取得します")
            
            # データ取得
            try:
                # 試行回数：討伐数アイコン（toubatsu64.webp）のimg[20]の次の兄弟
                trials = None
                trials_selectors = [
                    ("//img[contains(@src, 'toubatsu64')]/following-sibling::*[1]", "img src=toubatsu64 following sibling"),
                    ("//img[contains(@src, 'toubatsu')]/following-sibling::*[1]", "img src contains toubatsu following sibling"),
                    ("//img[@title='討伐数']/following-sibling::*[1]", "img title=討伐数 following sibling"),
                ]
                
                for selector, description in trials_selectors:
                    try:
                        trials_element = self.driver.find_element(By.XPATH, selector)
                        trials_text = trials_element.text.strip()
                        if trials_text and any(c.isdigit() for c in trials_text):
                            # 数字のみを抽出
                            trials = int(''.join(filter(str.isdigit, trials_text)))
                            logger.info(f"試行回数を取得しました: {trials} (セレクタ: {description})")
                            break
                    except Exception as e:
                        logger.debug(f"試行回数セレクタ失敗 ({description}): {str(e)[:100]}")
                        continue
                
                if trials is None:
                    logger.warning("セレクタで見つかりませんでした。代替方法を試します")
                    try:
                        # 代替案：すべてのテキストノードから「体」を含む行を探す
                        all_text = self.driver.find_element(By.TAG_NAME, "body").text
                        lines = all_text.split('\n')
                        for line in lines:
                            if '体' in line and any(c.isdigit() for c in line):
                                trials = int(''.join(filter(str.isdigit, line)))
                                logger.info(f"試行回数を取得しました（代替）: {trials}")
                                break
                    except Exception as e:
                        logger.debug(f"代替方法も失敗: {e}")
                
                if trials is None:
                    logger.error("試行回数を取得できません")
                    raise ValueError("試行回数が見つかりません")
                
            except Exception as e:
                logger.error(f"試行回数取得エラー: {e}")
                raise
            
            try:
                # 青箱数：青箱数アイコン（bluebox64.webp）のimg[21]の次の兄弟
                blue_chest_count = None
                logger.info("青箱数取得を試みます")
                
                try:
                    # すべてのbluebox画像を見つける
                    all_bluebox_imgs = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'bluebox')]")
                    logger.info(f"bluebox画像が{len(all_bluebox_imgs)}個見つかりました")
                    
                    # タイトルが「青箱数」のものを探す
                    for img in all_bluebox_imgs:
                        title = img.get_attribute("title")
                        if title == "青箱数":
                            logger.info(f"タイトル='青箱数'の画像を見つけました")
                            # 兄弟要素を取得
                            parent = img.find_element(By.XPATH, "..")
                            siblings = parent.find_elements(By.XPATH, "./following-sibling::*")
                            if siblings:
                                blue_chest_text = siblings[0].text.strip()
                                logger.info(f"次の兄弟のテキスト: '{blue_chest_text}'")
                                if blue_chest_text and any(c.isdigit() for c in blue_chest_text):
                                    blue_chest_count = int(''.join(filter(str.isdigit, blue_chest_text.split('(')[0])))
                                    logger.info(f"青箱数を取得しました: {blue_chest_count}")
                                    break
                except Exception as e:
                    logger.debug(f"青箱数取得エラー: {str(e)[:100]}")
                
                if blue_chest_count is None:
                    logger.warning("青箱数を取得できません。0として処理します")
                    blue_chest_count = 0
                    
            except Exception as e:
                logger.error(f"青箱数取得エラー: {e}")
                blue_chest_count = 0
            
            try:
                # ヒヒイロカネ数：「青箱ヒヒの数」アイコン（title=青箱ヒヒの数）のimg[99]の次の兄弟から取得
                hihi_count = None
                logger.info("ヒヒイロカネ数取得を試みます")
                
                try:
                    # すべての「青箱ヒヒの数」画像を見つける
                    hihi_imgs = self.driver.find_elements(By.XPATH, "//img[@title='青箱ヒヒの数']")
                    logger.info(f"タイトル='青箱ヒヒの数'の画像が{len(hihi_imgs)}個見つかりました")
                    
                    # 最初のテキストが空でない兄弟を探す
                    for i, hihi_img in enumerate(hihi_imgs):
                        try:
                            parent = hihi_img.find_element(By.XPATH, "..")
                            siblings = parent.find_elements(By.XPATH, "./following-sibling::*")
                            if siblings:
                                hihi_text = siblings[0].text.strip()
                                logger.info(f"img[{i}]の次の兄弟のテキスト: '{hihi_text}'")
                                if hihi_text and any(c.isdigit() for c in hihi_text):
                                    hihi_count = int(''.join(filter(str.isdigit, hihi_text.split('(')[0])))
                                    logger.info(f"ヒヒイロカネ数を取得しました: {hihi_count}")
                                    break
                        except Exception as e:
                            logger.debug(f"img[{i}]処理エラー: {str(e)[:50]}")
                            continue
                except Exception as e:
                    logger.debug(f"ヒヒイロカネ数取得エラー: {str(e)[:100]}")
                
                if hihi_count is None:
                    logger.warning("ヒヒイロカネ数を取得できません。0として処理します")
                    hihi_count = 0
                    
            except Exception as e:
                logger.error(f"ヒヒイロカネ数取得エラー: {e}")
                hihi_count = 0
            
            data = {
                'trials': trials,
                'blue_chest_count': blue_chest_count,
                'hihi_count': hihi_count
            }
            
            logger.info(f"データ取得完了: {data}")
            return data
            
        except Exception as e:
            logger.error(f"スクレイピングエラー: {e}")
            import traceback
            traceback.print_exc()
            raise
