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


class Config:
    """アプリケーション設定を管理するクラス"""
    
    _config = None
    _database_url = None
    
    @classmethod
    def load(cls, path="config.yaml"):
        """設定を読み込む"""
        if cls._config is None:
            cls._config = load_config(path)
        return cls._config
    
    @classmethod
    def get(cls, key=None):
        """設定値を取得"""
        if cls._config is None:
            cls.load()
        if key:
            return cls._config.get(key)
        return cls._config
    
    @classmethod
    def get_database_url(cls):
        """データベース接続URLを取得"""
        if cls._database_url is not None:
            return cls._database_url
            
        # 環境変数から直接DATABASE_URLを取得（Cloud Run用）
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            cls._database_url = database_url
            return cls._database_url
            
        if cls._config is None:
            cls.load()
        
        db = cls._config.get('database', {})
        host = db.get('host', 'localhost')
        port = db.get('port', 5432)
        name = db.get('name', 'grablu')
        user = db.get('user', 'grablu')
        
        # Secret ManagerからDB_PASSWORDを取得（Cloud Run用）
        password = os.environ.get('DB_PASSWORD', db.get('password', ''))
        
        cls._database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        return cls._database_url
    
    # プロパティとして使えるようにする
    DATABASE_URL = property(lambda self: Config.get_database_url())


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
        """完全な出力ファイルパスを取得。同名ファイル存在時は連番を付与
        
        Args:
            directory: 出力ディレクトリ
            prefix: ファイル名のプレフィックス
            extension: ファイル拡張子
        
        Returns:
            完全なファイルパス (同名ファイル存在時は連番付き)
        """
        filename = OutputConfig.generate_filename(prefix, extension)
        filepath = os.path.join(directory, filename)
        
        # 同名ファイルが存在する場合、連番を付与
        if os.path.exists(filepath):
            name_without_ext = os.path.splitext(filename)[0]
            counter = 1
            while True:
                numbered_filename = f"{name_without_ext}_{counter:02d}.{extension}"
                filepath = os.path.join(directory, numbered_filename)
                if not os.path.exists(filepath):
                    logger.info(f"同名ファイルが存在するため連番を付与します: {numbered_filename}")
                    break
                counter += 1
        
        return filepath
