"""
グラブルドロップ統計のグラフ描画ユーティリティ
並列表示やグラフ生成を担当
"""
import logging
import os
import warnings
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binom

# 日本語フォント対応設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'MS PGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# matplotlib フォント警告を非表示
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

from config import OutputConfig

logger = logging.getLogger(__name__)


def plot_combined_distributions(analyzer_cumulative, analyzer_monthly, output_dir="."):
    """累計と月のグラフを並列表示
    
    Args:
        analyzer_cumulative: 累計データのDropAnalyzerインスタンス
        analyzer_monthly: 月データのDropAnalyzerインスタンス
        output_dir: 出力ディレクトリ
    """
    # 出力ディレクトリを確認・作成
    output_dir = OutputConfig.ensure_directory(output_dir)
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # 累計データ（上段）
    # 青箱ドロップ
    blue_chest_stats_cumulative = analyzer_cumulative.calculate_p_stats()
    _plot_binomial_on_axes(
        axes[0, 0], 
        analyzer_cumulative.trials, 
        analyzer_cumulative.blue_chest_prob, 
        analyzer_cumulative.blue_chest_count,
        blue_chest_stats_cumulative.expected,
        "つよバハ青箱ドロップの分布"
    )
    
    # ヒヒイロカネドロップ
    if analyzer_cumulative.blue_chest_count > 0:
        hihi_stats_cumulative = analyzer_cumulative.calculate_q_stats()
        _plot_binomial_on_axes(
            axes[0, 1], 
            analyzer_cumulative.blue_chest_count, 
            analyzer_cumulative.hihi_prob, 
            analyzer_cumulative.hihi_count,
            hihi_stats_cumulative.expected,
            "ヒヒの青箱からのドロップの分布"
        )
    else:
        axes[0, 1].text(0.5, 0.5, '青箱ドロップが発生していません', 
                    ha='center', va='center', fontsize=14)
        axes[0, 1].set_title("ヒヒの青箱からのドロップの分布")
    
    # 複合事象
    combined_stats_cumulative = analyzer_cumulative.calculate_combined_stats()
    _plot_binomial_on_axes(
        axes[0, 2], 
        analyzer_cumulative.trials, 
        combined_stats_cumulative.probability, 
        analyzer_cumulative.hihi_count,
        combined_stats_cumulative.expected,
        "複合事象（青箱かつヒヒ）の分布"
    )
    
    # 月データ（下段）
    # 青箱ドロップ
    blue_chest_stats_monthly = analyzer_monthly.calculate_p_stats()
    _plot_binomial_on_axes(
        axes[1, 0], 
        analyzer_monthly.trials, 
        analyzer_monthly.blue_chest_prob, 
        analyzer_monthly.blue_chest_count,
        blue_chest_stats_monthly.expected,
        "つよバハ青箱ドロップの分布"
    )
    
    # ヒヒイロカネドロップ
    if analyzer_monthly.blue_chest_count > 0:
        hihi_stats_monthly = analyzer_monthly.calculate_q_stats()
        _plot_binomial_on_axes(
            axes[1, 1], 
            analyzer_monthly.blue_chest_count, 
            analyzer_monthly.hihi_prob, 
            analyzer_monthly.hihi_count,
            hihi_stats_monthly.expected,
            "ヒヒの青箱からのドロップの分布"
        )
    else:
        axes[1, 1].text(0.5, 0.5, '青箱ドロップが発生していません', 
                    ha='center', va='center', fontsize=14)
        axes[1, 1].set_title("ヒヒの青箱からのドロップの分布")
    
    # 複合事象
    combined_stats_monthly = analyzer_monthly.calculate_combined_stats()
    _plot_binomial_on_axes(
        axes[1, 2], 
        analyzer_monthly.trials, 
        combined_stats_monthly.probability, 
        analyzer_monthly.hihi_count,
        combined_stats_monthly.expected,
        "複合事象（青箱かつヒヒ）の分布"
    )
    
    # 上段に「累計」、下段に「月」のラベルを追加
    fig.text(0.02, 0.75, '累計', fontsize=16, fontweight='bold', rotation=90, va='center')
    fig.text(0.02, 0.25, '月', fontsize=16, fontweight='bold', rotation=90, va='center')
    
    # 出力ファイルパスを生成
    filename = OutputConfig.get_output_path(output_dir, 'drop_distribution', 'png')
    
    plt.tight_layout(rect=[0.03, 0, 1, 1])
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    logger.info(f"グラフを保存しました: {filename}")
    plt.close()  # グラフを閉じて自動終了


def _plot_binomial_on_axes(ax, n, p, actual, expected, title):
    """二項分布のプロット（軸指定版）
    
    Args:
        ax: matplotlib軸オブジェクト
        n: 試行回数
        p: 成功確率
        actual: 実績値
        expected: 期待値
        title: グラフタイトル
    """
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
