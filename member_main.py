"""
Grablu - グラブル団員管理ツール
メインエントリーポイント
"""
import logging
from selenium import webdriver
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import load_config, Config
from scraper import GuildScraper
from member_tracker import MemberTracker
from models import Base, Guild

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('member.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """団員管理メイン処理"""
    logger.info("団員管理処理を開始します")
    
    try:
        # 設定読み込み
        config = load_config()
        guild_name = config["guild"]["name"]
        base_url = config["member_stats"]["guild_database_url"]

        # データベース接続
        engine = create_engine(
            Config.get_database_url(),
            connect_args={
                "connect_timeout": 10  # 10秒でタイムアウト
            },
            pool_pre_ping=True  # 接続確認
        )
        logger.info("データベースエンジンを作成しました")
        Base.metadata.create_all(engine)
        logger.info("テーブルを作成しました")
        Session = sessionmaker(bind=engine)
        db = Session()
        
        try:
            # 団を取得または作成
            guild = db.query(Guild).filter(Guild.name == guild_name).first()
            if not guild:
                # 団IDは一意の識別子として名前をベースに生成
                import hashlib
                guild_id_str = hashlib.md5(guild_name.encode('utf-8')).hexdigest()[:16]
                guild = Guild(name=guild_name, guild_id=guild_id_str, is_active=1)
                db.add(guild)
                db.commit()
                logger.info(f"団を作成しました: {guild_name} (ID: {guild_id_str})")
            
            guild_id = guild.id

            # Chromeドライバー起動（Selenium Managerが自動で最新版を管理）
            driver = webdriver.Chrome()
            logger.info("Chromeドライバーを起動しました")

            try:
                # スクレイピング処理
                scraper = GuildScraper(driver)
                scraper.open_guild_page(guild_name=guild_name, base_url=base_url)
                event_number = scraper.get_event_number_from_dropdown()
                
                if event_number is None:
                    logger.error("イベント番号が取得できません。処理を中断します")
                    return
                
                # 取得済みチェック
                tracker = MemberTracker(db, guild_id)
                if tracker.is_already_fetched(event_number):
                    logger.warning("="*60)
                    logger.warning(f"第{event_number}回のデータは既に取得済みです")
                    logger.warning("重複して実行しますか？")
                    logger.warning("="*60)
                    response = input("続行する場合は 'yes' と入力してください: ")
                    if response.lower() != 'yes':
                        logger.info("処理を中断しました")
                        return
                
                members = scraper.scrape_member_table()
                
                # 取得データ表示
                for member in members:
                    print(f"{member['name']} (ID: {member['player_id']}): {member['rank']}")

                # 団員追跡システムで名前変更を検出
                name_changes = tracker.update_members(members)
                
                # 名前変更があった場合は表示
                if name_changes:
                    logger.info("=" * 60)
                    logger.info("名前変更を検出しました:")
                    for player_id, change in name_changes.items():
                        logger.info(f"  {change['old_name']} → {change['new_name']} (ID: {player_id})")
                    logger.info("=" * 60)
                
                # 履歴を保存（イベント番号も記録）
                tracker.save_event_data(event_number, members)
                
                logger.info("団員管理処理が完了しました")

            finally:
                driver.quit()
                logger.info("Chromeドライバーを終了しました")
        
        finally:
            db.close()
    
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML解析エラー: {e}")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
