"""設定ファイルの読み込みを管理"""
import logging
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
