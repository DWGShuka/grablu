"""
Grablu - グラブルドロップ統計ツール
ドロップ確率の期待値とパーセンタイル評価
"""
import logging
import os
from selenium import webdriver
import yaml

from config import load_config
from drop_scraper import DropScraper
from drop_analyzer import DropAnalyzer
from drop_plotter import plot_combined_distributions

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drop.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _initialize():
    """設定の読み込みと検証
    
    Returns:
        (config, drop_config) のタプル
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない
        ValueError: 設定が不完全
    """
    config = load_config()
    drop_config = config.get("drop_stats", {})
    
    if not drop_config:
        raise ValueError("config.yamlに'drop_stats'セクションが見つかりません")
    
    url = drop_config.get("url")
    blue_chest_prob = drop_config.get("blue_chest_probability")
    hihi_prob = drop_config.get("hihi_probability")
    
    if not all([url, blue_chest_prob, hihi_prob]):
        raise ValueError("設定が不完全です。url, blue_chest_probability, hihi_probabilityを確認してください")
    
    logger.info("設定ファイルを読み込みました")
    return config, drop_config


def _scrape_and_analyze(driver, drop_config):
    """スクレイピングと分析実行
    
    Args:
        driver: Seleniumドライバー
        drop_config: drop_stats設定辞書
    
    Returns:
        (analyzer_cumulative, analyzer_monthly) のタプル
    """
    scraper = DropScraper(driver)
    
    # config.yaml からログイン情報を取得
    login_username = drop_config.get("login", {}).get("username")
    login_password = drop_config.get("login", {}).get("password")
    url = drop_config.get("url")
    blue_chest_prob = drop_config.get("blue_chest_probability")
    hihi_prob = drop_config.get("hihi_probability")
    
    # スクレイピング実行
    data = scraper.scrape_drop_data(url, login_username, login_password)
    
    # 累計データを処理
    cumulative_data = data['cumulative']
    trials_cumulative = cumulative_data['trials']
    blue_chest_cumulative = cumulative_data['blue_chest_count']
    hihi_cumulative = cumulative_data['hihi_count']
    
    logger.info("===== 累計データ =====")
    logger.info(f"試行回数: {trials_cumulative}")
    logger.info(f"青箱ドロップ回数: {blue_chest_cumulative}")
    logger.info(f"ヒヒイロカネドロップ回数: {hihi_cumulative}")
    
    # 月データを処理
    monthly_data = data['monthly']
    trials_monthly = monthly_data['trials']
    blue_chest_monthly = monthly_data['blue_chest_count']
    hihi_monthly = monthly_data['hihi_count']
    
    logger.info("===== 月データ =====")
    logger.info(f"試行回数: {trials_monthly}")
    logger.info(f"青箱ドロップ回数: {blue_chest_monthly}")
    logger.info(f"ヒヒイロカネドロップ回数: {hihi_monthly}")
    
    # アナライザーを作成
    analyzer_cumulative = DropAnalyzer(
        trials_cumulative, 
        blue_chest_cumulative, 
        hihi_cumulative, 
        blue_chest_prob, 
        hihi_prob
    )
    
    analyzer_monthly = DropAnalyzer(
        trials_monthly, 
        blue_chest_monthly, 
        hihi_monthly, 
        blue_chest_prob, 
        hihi_prob
    )
    
    return analyzer_cumulative, analyzer_monthly


def _output_results(analyzer_cumulative, analyzer_monthly, output_dir):
    """結果をレポート出力とグラフで表示
    
    Args:
        analyzer_cumulative: 累計データアナライザー
        analyzer_monthly: 月データアナライザー
        output_dir: 出力ディレクトリ
    """
    # 統計情報をコンソール出力
    print("\n" + "="*60)
    print("【データ分析】")
    print("="*60)
    
    analyzer_cumulative.print_report("累計")
    analyzer_monthly.print_report("月")
    
    # グラフを並列表示
    plot_combined_distributions(analyzer_cumulative, analyzer_monthly, output_dir)
    logger.info("ドロップ統計処理が完了しました")


def main():
    """ドロップ統計メイン処理"""
    logger.info("ドロップ統計処理を開始します")
    
    driver = None
    
    try:
        # 初期化
        config, drop_config = _initialize()
        output_dir = drop_config.get("output_directory", ".")
        
        # Chromeドライバー起動
        driver = webdriver.Chrome()
        logger.info("Chromeドライバーを起動しました")
        
        # スクレイピングと分析
        analyzer_cumulative, analyzer_monthly = _scrape_and_analyze(driver, drop_config)
        
        # 結果出力
        _output_results(analyzer_cumulative, analyzer_monthly, output_dir)
    
    except ValueError as e:
        logger.error(f"設定エラー: {e}")
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML解析エラー: {e}")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            logger.info("Chromeドライバーを終了しました")


if __name__ == "__main__":
    main()
