"""
Grablu - グラブルドロップ統計ツール
ドロップ確率の期待値とパーセンタイル評価
"""
import logging
import os
from datetime import datetime
from selenium import webdriver
import yaml
import matplotlib.pyplot as plt
from scipy.stats import binom
import numpy as np

from config import load_config
from drop_scraper import DropScraper

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

# 日本語フォント設定（matplotlib）
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False


class DropAnalyzer:
    """ドロップ確率の分析クラス"""
    
    def __init__(self, trials, blue_chest_count, hihi_count, blue_chest_prob, hihi_prob):
        """
        Args:
            trials: 試行回数
            blue_chest_count: つよバハ青箱ドロップ回数
            hihi_count: ヒヒイロカネドロップ回数
            blue_chest_prob: 青箱ドロップ確率
            hihi_prob: 青箱からのヒヒイロカネドロップ確率（条件付き確率）
        """
        self.trials = trials
        self.blue_chest_count = blue_chest_count
        self.hihi_count = hihi_count
        self.blue_chest_prob = blue_chest_prob
        self.hihi_prob = hihi_prob
    
    def calculate_p_stats(self):
        """青箱ドロップの統計情報を計算"""
        mu = self.trials * self.blue_chest_prob
        sigma = np.sqrt(self.trials * self.blue_chest_prob * (1 - self.blue_chest_prob))
        percentile = binom.cdf(self.blue_chest_count, self.trials, self.blue_chest_prob) * 100
        
        return {
            'expected': mu,
            'stddev': sigma,
            'actual': self.blue_chest_count,
            'percentile': percentile
        }
    
    def calculate_q_stats(self):
        """ヒヒイロカネドロップの統計情報を計算（条件付き）"""
        if self.blue_chest_count == 0:
            return {
                'expected': 0,
                'stddev': 0,
                'actual': 0,
                'percentile': 0
            }
        
        mu = self.blue_chest_count * self.hihi_prob
        sigma = np.sqrt(self.blue_chest_count * self.hihi_prob * (1 - self.hihi_prob))
        percentile = binom.cdf(self.hihi_count, self.blue_chest_count, self.hihi_prob) * 100
        
        return {
            'expected': mu,
            'stddev': sigma,
            'actual': self.hihi_count,
            'percentile': percentile
        }
    
    def calculate_combined_stats(self):
        """複合事象（青箱かつヒヒ）の統計情報を計算"""
        combined_prob = self.blue_chest_prob * self.hihi_prob
        mu = self.trials * combined_prob
        sigma = np.sqrt(self.trials * combined_prob * (1 - combined_prob))
        percentile = binom.cdf(self.hihi_count, self.trials, combined_prob) * 100
        
        return {
            'expected': mu,
            'stddev': sigma,
            'actual': self.hihi_count,
            'percentile': percentile,
            'probability': combined_prob
        }
    
    def plot_distributions(self, filename='drop_distribution.png'):
        """確率分布をグラフ表示"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # 青箱ドロップ
        blue_chest_stats = self.calculate_p_stats()
        self._plot_binomial(
            axes[0], 
            self.trials, 
            self.blue_chest_prob, 
            self.blue_chest_count,
            blue_chest_stats['expected'],
            "つよバハ青箱ドロップ率の分布"
        )
        
        # ヒヒイロカネドロップ
        if self.blue_chest_count > 0:
            hihi_stats = self.calculate_q_stats()
            self._plot_binomial(
                axes[1], 
                self.blue_chest_count, 
                self.hihi_prob, 
                self.hihi_count,
                hihi_stats['expected'],
                "ヒヒの青箱からのドロップ率の分布"
            )
        else:
            axes[1].text(0.5, 0.5, '青箱ドロップが発生していません', 
                        ha='center', va='center', fontsize=14)
            axes[1].set_title("ヒヒの青箱からのドロップ率の分布")
        
        # 複合事象
        combined_stats = self.calculate_combined_stats()
        self._plot_binomial(
            axes[2], 
            self.trials, 
            combined_stats['probability'], 
            self.hihi_count,
            combined_stats['expected'],
            "複合事象（青箱かつヒヒ）の分布"
        )
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        logger.info(f"グラフを保存しました: {filename}")
        plt.close()  # グラフを閉じて自動終了
    
    def _plot_binomial(self, ax, n, p, actual, expected, title):
        """二項分布のプロット"""
        # 分布の範囲を計算
        mu = n * p
        sigma = np.sqrt(n * p * (1 - p))
        x_min = max(0, int(mu - 4 * sigma))
        x_max = min(n, int(mu + 4 * sigma))
        
        x = np.arange(x_min, x_max + 1)
        y = binom.pmf(x, n, p)
        
        ax.bar(x, y, alpha=0.6, color='steelblue', label='確率分布')
        ax.axvline(expected, color='green', linestyle='--', linewidth=2, label=f'期待値: {expected:.1f}')
        ax.axvline(actual, color='red', linestyle='-', linewidth=2, label=f'実績: {actual}')
        
        ax.set_xlabel('ドロップ数')
        ax.set_ylabel('確率')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)


def _plot_combined_distributions(analyzer_cumulative, analyzer_monthly, output_dir="."):
    """累計と月のグラフを並列表示"""
    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # 累計データ（上段）
    # 青箱ドロップ
    blue_chest_stats_cumulative = analyzer_cumulative.calculate_p_stats()
    analyzer_cumulative._plot_binomial(
        axes[0, 0], 
        analyzer_cumulative.trials, 
        analyzer_cumulative.blue_chest_prob, 
        analyzer_cumulative.blue_chest_count,
        blue_chest_stats_cumulative['expected'],
        "つよバハ青箱ドロップの分布"
    )
    
    # ヒヒイロカネドロップ
    if analyzer_cumulative.blue_chest_count > 0:
        hihi_stats_cumulative = analyzer_cumulative.calculate_q_stats()
        analyzer_cumulative._plot_binomial(
            axes[0, 1], 
            analyzer_cumulative.blue_chest_count, 
            analyzer_cumulative.hihi_prob, 
            analyzer_cumulative.hihi_count,
            hihi_stats_cumulative['expected'],
            "ヒヒの青箱からのドロップの分布"
        )
    else:
        axes[0, 1].text(0.5, 0.5, '青箱ドロップが発生していません', 
                    ha='center', va='center', fontsize=14)
        axes[0, 1].set_title("ヒヒの青箱からのドロップの分布")
    
    # 複合事象
    combined_stats_cumulative = analyzer_cumulative.calculate_combined_stats()
    analyzer_cumulative._plot_binomial(
        axes[0, 2], 
        analyzer_cumulative.trials, 
        combined_stats_cumulative['probability'], 
        analyzer_cumulative.hihi_count,
        combined_stats_cumulative['expected'],
        "複合事象（青箱かつヒヒ）の分布"
    )
    
    # 月データ（下段）
    # 青箱ドロップ
    blue_chest_stats_monthly = analyzer_monthly.calculate_p_stats()
    analyzer_monthly._plot_binomial(
        axes[1, 0], 
        analyzer_monthly.trials, 
        analyzer_monthly.blue_chest_prob, 
        analyzer_monthly.blue_chest_count,
        blue_chest_stats_monthly['expected'],
        "つよバハ青箱ドロップの分布"
    )
    
    # ヒヒイロカネドロップ
    if analyzer_monthly.blue_chest_count > 0:
        hihi_stats_monthly = analyzer_monthly.calculate_q_stats()
        analyzer_monthly._plot_binomial(
            axes[1, 1], 
            analyzer_monthly.blue_chest_count, 
            analyzer_monthly.hihi_prob, 
            analyzer_monthly.hihi_count,
            hihi_stats_monthly['expected'],
            "ヒヒの青箱からのドロップの分布"
        )
    else:
        axes[1, 1].text(0.5, 0.5, '青箱ドロップが発生していません', 
                    ha='center', va='center', fontsize=14)
        axes[1, 1].set_title("ヒヒの青箱からのドロップの分布")
    
    # 複合事象
    combined_stats_monthly = analyzer_monthly.calculate_combined_stats()
    analyzer_monthly._plot_binomial(
        axes[1, 2], 
        analyzer_monthly.trials, 
        combined_stats_monthly['probability'], 
        analyzer_monthly.hihi_count,
        combined_stats_monthly['expected'],
        "複合事象（青箱かつヒヒ）の分布"
    )
    
    # 上段に「累計」、下段に「月」のラベルを追加
    fig.text(0.02, 0.75, '累計', fontsize=16, fontweight='bold', rotation=90, va='center')
    fig.text(0.02, 0.25, '月', fontsize=16, fontweight='bold', rotation=90, va='center')
    
    # 日付をファイル名に含める
    today = datetime.now().strftime("%Y%m%d")
    filename = os.path.join(output_dir, f'drop_distribution_{today}.png')
    
    plt.tight_layout(rect=[0.03, 0, 1, 1])
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    logger.info(f"グラフを保存しました: {filename}")
    plt.close()  # グラフを閉じて自動終了


def main():
    """ドロップ統計メイン処理"""
    logger.info("ドロップ統計処理を開始します")
    
    try:
        # 設定読み込み
        config = load_config()
        drop_config = config.get("drop_stats", {})
        
        if not drop_config:
            logger.error("config.yamlに'drop_stats'セクションが見つかりません")
            return
        
        url = drop_config.get("url")
        blue_chest_prob = drop_config.get("blue_chest_probability")
        hihi_prob = drop_config.get("hihi_probability")
        output_dir = drop_config.get("output_directory", ".")  # デフォルトはカレントディレクトリ
        
        if not all([url, blue_chest_prob, hihi_prob]):
            logger.error("設定が不完全です。url, blue_chest_probability, hihi_probabilityを確認してください")
            return
        
        # Chromeドライバー起動
        driver = webdriver.Chrome()
        logger.info("Chromeドライバーを起動しました")
        
        try:
            # スクレイピング処理
            scraper = DropScraper(driver)
            
            # config.yaml からログイン情報を取得
            login_username = drop_config.get("login", {}).get("username")
            login_password = drop_config.get("login", {}).get("password")
            
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
            
            # 両方のデータを並列表示
            print("\n" + "="*60)
            print("【データ分析】")
            print("="*60)
            
            # 累計データの分析
            print("\n【累計データ】")
            analyzer_cumulative = DropAnalyzer(
                trials_cumulative, 
                blue_chest_cumulative, 
                hihi_cumulative, 
                blue_chest_prob, 
                hihi_prob
            )
            
            # 青箱ドロップの統計（累計）
            blue_chest_stats_cumulative = analyzer_cumulative.calculate_p_stats()
            print("\n  つよバハ青箱ドロップ率の統計（累計）")
            print(f"    期待値: {blue_chest_stats_cumulative['expected']:.2f}")
            print(f"    標準偏差: {blue_chest_stats_cumulative['stddev']:.2f}")
            print(f"    実績: {blue_chest_stats_cumulative['actual']}")
            print(f"    パーセンタイル: {blue_chest_stats_cumulative['percentile']:.2f}%")
            
            # ヒヒイロカネドロップの統計（累計）
            hihi_stats_cumulative = analyzer_cumulative.calculate_q_stats()
            print("\n  ヒヒの青箱からのドロップ率の統計（累計）")
            print(f"    期待値: {hihi_stats_cumulative['expected']:.2f}")
            print(f"    標準偏差: {hihi_stats_cumulative['stddev']:.2f}")
            print(f"    実績: {hihi_stats_cumulative['actual']}")
            print(f"    パーセンタイル: {hihi_stats_cumulative['percentile']:.2f}%")
            
            # 複合事象の統計（累計）
            combined_stats_cumulative = analyzer_cumulative.calculate_combined_stats()
            print("\n  複合事象（青箱かつヒヒ）の統計（累計）")
            print(f"    複合確率: {combined_stats_cumulative['probability']:.6f}")
            print(f"    期待値: {combined_stats_cumulative['expected']:.2f}")
            print(f"    標準偏差: {combined_stats_cumulative['stddev']:.2f}")
            print(f"    実績: {combined_stats_cumulative['actual']}")
            print(f"    パーセンタイル: {combined_stats_cumulative['percentile']:.2f}%")
            
            # 月データの分析
            print("\n【月データ】")
            analyzer_monthly = DropAnalyzer(
                trials_monthly, 
                blue_chest_monthly, 
                hihi_monthly, 
                blue_chest_prob, 
                hihi_prob
            )
            
            # 青箱ドロップの統計（月）
            blue_chest_stats_monthly = analyzer_monthly.calculate_p_stats()
            print("\n  つよバハ青箱ドロップ率の統計（月）")
            print(f"    期待値: {blue_chest_stats_monthly['expected']:.2f}")
            print(f"    標準偏差: {blue_chest_stats_monthly['stddev']:.2f}")
            print(f"    実績: {blue_chest_stats_monthly['actual']}")
            print(f"    パーセンタイル: {blue_chest_stats_monthly['percentile']:.2f}%")
            
            # ヒヒイロカネドロップの統計（月）
            hihi_stats_monthly = analyzer_monthly.calculate_q_stats()
            print("\n  ヒヒの青箱からのドロップ率の統計（月）")
            print(f"    期待値: {hihi_stats_monthly['expected']:.2f}")
            print(f"    標準偏差: {hihi_stats_monthly['stddev']:.2f}")
            print(f"    実績: {hihi_stats_monthly['actual']}")
            print(f"    パーセンタイル: {hihi_stats_monthly['percentile']:.2f}%")
            
            # 複合事象の統計（月）
            combined_stats_monthly = analyzer_monthly.calculate_combined_stats()
            print("\n  複合事象（青箱かつヒヒ）の統計（月）")
            print(f"    複合確率: {combined_stats_monthly['probability']:.6f}")
            print(f"    期待値: {combined_stats_monthly['expected']:.2f}")
            print(f"    標準偏差: {combined_stats_monthly['stddev']:.2f}")
            print(f"    実績: {combined_stats_monthly['actual']}")
            print(f"    パーセンタイル: {combined_stats_monthly['percentile']:.2f}%")
            
            # グラフを並列表示（累計と月を1つの画像に）
            _plot_combined_distributions(analyzer_cumulative, analyzer_monthly, output_dir)
            
            logger.info("ドロップ統計処理が完了しました")
        
        finally:
            driver.quit()
            logger.info("Chromeドライバーを終了しました")
    
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML解析エラー: {e}")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
