"""
グラブルドロップ統計の分析ユーティリティ
統計計算と結果管理を担当
"""
import logging
from dataclasses import dataclass
import matplotlib.pyplot as plt
from scipy.stats import binom
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StatsResult:
    """統計計算結果を表すデータクラス"""
    expected: float
    stddev: float
    actual: int
    percentile: float
    probability: float = None  # 複合事象の場合のみ使用
    
    def __repr__(self):
        """見やすい文字列表現"""
        if self.probability is not None:
            return (f"StatsResult(期待値={self.expected:.2f}, "
                   f"標準偏差={self.stddev:.2f}, "
                   f"実績={self.actual}, "
                   f"パーセンタイル={self.percentile:.2f}%, "
                   f"確率={self.probability:.6f})")
        return (f"StatsResult(期待値={self.expected:.2f}, "
               f"標準偏差={self.stddev:.2f}, "
               f"実績={self.actual}, "
               f"パーセンタイル={self.percentile:.2f}%)")


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
        
        return StatsResult(
            expected=mu,
            stddev=sigma,
            actual=self.blue_chest_count,
            percentile=percentile
        )
    
    def calculate_q_stats(self):
        """ヒヒイロカネドロップの統計情報を計算（条件付き）"""
        if self.blue_chest_count == 0:
            return StatsResult(
                expected=0,
                stddev=0,
                actual=0,
                percentile=0
            )
        
        mu = self.blue_chest_count * self.hihi_prob
        sigma = np.sqrt(self.blue_chest_count * self.hihi_prob * (1 - self.hihi_prob))
        percentile = binom.cdf(self.hihi_count, self.blue_chest_count, self.hihi_prob) * 100
        
        return StatsResult(
            expected=mu,
            stddev=sigma,
            actual=self.hihi_count,
            percentile=percentile
        )
    
    def calculate_combined_stats(self):
        """複合事象（青箱かつヒヒ）の統計情報を計算"""
        combined_prob = self.blue_chest_prob * self.hihi_prob
        mu = self.trials * combined_prob
        sigma = np.sqrt(self.trials * combined_prob * (1 - combined_prob))
        percentile = binom.cdf(self.hihi_count, self.trials, combined_prob) * 100
        
        return StatsResult(
            expected=mu,
            stddev=sigma,
            actual=self.hihi_count,
            percentile=percentile,
            probability=combined_prob
        )
    
    def get_report(self):
        """統計情報を辞書形式で取得
        
        Returns:
            統計結果を含む辞書 {
                'blue_chest': StatsResult,
                'hihi': StatsResult,
                'combined': StatsResult
            }
        """
        return {
            'blue_chest': self.calculate_p_stats(),
            'hihi': self.calculate_q_stats(),
            'combined': self.calculate_combined_stats()
        }
    
    def print_report(self, dataset_name=""):
        """統計結果を見やすく出力
        
        Args:
            dataset_name: データセット名（「累計」「月」など）
        """
        report = self.get_report()
        
        print(f"\n【{dataset_name}データ】")
        
        # 青箱ドロップ
        blue_chest = report['blue_chest']
        print("\n  つよバハ青箱ドロップ率の統計")
        print(f"    期待値: {blue_chest.expected:.2f}")
        print(f"    標準偏差: {blue_chest.stddev:.2f}")
        print(f"    実績: {blue_chest.actual}")
        print(f"    パーセンタイル: {blue_chest.percentile:.2f}%")
        
        # ヒヒイロカネドロップ
        hihi = report['hihi']
        print("\n  ヒヒの青箱からのドロップ率の統計")
        print(f"    期待値: {hihi.expected:.2f}")
        print(f"    標準偏差: {hihi.stddev:.2f}")
        print(f"    実績: {hihi.actual}")
        print(f"    パーセンタイル: {hihi.percentile:.2f}%")
        
        # 複合事象
        combined = report['combined']
        print("\n  複合事象（青箱かつヒヒ）の統計")
        print(f"    複合確率: {combined.probability:.6f}")
        print(f"    期待値: {combined.expected:.2f}")
        print(f"    標準偏差: {combined.stddev:.2f}")
        print(f"    実績: {combined.actual}")
        print(f"    パーセンタイル: {combined.percentile:.2f}%")
    
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
            blue_chest_stats.expected,
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
                hihi_stats.expected,
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
            combined_stats.probability, 
            self.hihi_count,
            combined_stats.expected,
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
