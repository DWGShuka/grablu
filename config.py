"""設定ファイルの読み込みと出力設定を管理"""
import logging
import os
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


def load_config(path="config.yaml"):
    """config.yamlを読み込む"""
    try:
        with open(path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            logger.info(f"設定ファイルを読み込みました: {path}")
            return config
    except FileNotFoundError:
        logger.error(f"設定ファイルが見つかりません: {path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"YAML解析エラー: {e}")
        raise


class OutputConfig:
    """出力ファイル設定を管理するクラス"""
    
    @staticmethod
    def generate_filename(prefix="output", extension="png"):
        """日付を含むファイル名を生成
        
        Args:
            prefix: ファイル名のプレフィックス (デフォルト: "output")
            extension: ファイル拡張子 (デフォルト: "png")
        
        Returns:
            生成されたファイル名 (例: "output_20260120.png")
        """
        today = datetime.now().strftime("%Y%m%d")
        return f"{prefix}_{today}.{extension}"
    
    @staticmethod
    def ensure_directory(directory_path):
        """ディレクトリが存在することを確認、なければ作成
        
        Args:
            directory_path: ディレクトリパス
        
        Returns:
            正規化されたディレクトリパス
        
        Raises:
            OSError: ディレクトリ作成失敗時
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            logger.info(f"出力ディレクトリを確認しました: {directory_path}")
            return os.path.abspath(directory_path)
        except OSError as e:
            logger.error(f"ディレクトリの作成に失敗しました: {directory_path} - {e}")
            raise
    
    @staticmethod
    def get_output_path(directory, prefix="output", extension="png"):
        """完全な出力ファイルパスを取得
        
        Args:
            directory: 出力ディレクトリ
            prefix: ファイル名のプレフィックス
            extension: ファイル拡張子
        
        Returns:
            完全なファイルパス
        """
        OutputConfig.ensure_directory(directory)
        filename = OutputConfig.generate_filename(prefix, extension)
        return os.path.join(directory, filename)
