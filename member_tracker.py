"""団員追跡システム - IDベースの名前変更追跡"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MemberTracker:
    """団員の履歴を管理するクラス"""
    
    def __init__(self, json_path="members.json"):
        self.json_path = Path(json_path)
        self.members = {}
        self.last_event_number = None
        self.load()
    
    def load(self):
        """members.jsonから履歴を読み込む"""
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.members = data.get("members", {})
                    self.last_event_number = data.get("last_event_number")
                logger.info(f"{len(self.members)}人の団員履歴を読み込みました")
                if self.last_event_number:
                    logger.info(f"最後に取得したイベント: 第{self.last_event_number}回")
            except Exception as e:
                logger.error(f"履歴読み込みエラー: {e}")
                self.members = {}
                self.last_event_number = None
        else:
            logger.info("履歴ファイルが存在しないため、新規作成します")
            self.members = {}
            self.last_event_number = None
    
    def save(self, event_number=None):
        """members.jsonに履歴を保存"""
        try:
            if event_number is not None:
                self.last_event_number = event_number
            
            data = {
                "last_updated": datetime.now().isoformat(),
                "last_event_number": self.last_event_number,
                "members": self.members
            }
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"履歴を保存しました: {self.json_path}")
        except Exception as e:
            logger.error(f"履歴保存エラー: {e}")
            raise
    
    def update_members(self, scraped_data):
        """
        スクレイピングデータで履歴を更新
        
        Args:
            scraped_data: [{"name": "...", "player_id": "...", "rank": "..."}, ...]
        
        Returns:
            dict: 名前変更があった団員の情報 {player_id: {"old_name": "...", "new_name": "..."}}
        """
        name_changes = {}
        today = datetime.now().strftime("%Y-%m-%d")
        
        for member in scraped_data:
            player_id = member["player_id"]
            current_name = member["name"]
            
            if not player_id:
                logger.warning(f"IDが取得できませんでした: {current_name}")
                continue
            
            if player_id in self.members:
                # 既存団員
                old_data = self.members[player_id]
                old_name = old_data["current_name"]
                
                if old_name != current_name:
                    # 名前変更を検出
                    logger.info(f"名前変更を検出: {old_name} → {current_name} (ID: {player_id})")
                    name_changes[player_id] = {
                        "old_name": old_name,
                        "new_name": current_name
                    }
                    
                    # 履歴に追加
                    if "name_history" not in old_data:
                        old_data["name_history"] = [old_name]
                    if current_name not in old_data["name_history"]:
                        old_data["name_history"].append(current_name)
                    
                    old_data["current_name"] = current_name
                    old_data["last_name_changed"] = today
                
                # 最終確認日を更新
                old_data["last_seen"] = today
            else:
                # 新規団員
                logger.info(f"新規団員を登録: {current_name} (ID: {player_id})")
                self.members[player_id] = {
                    "player_id": player_id,
                    "current_name": current_name,
                    "name_history": [current_name],
                    "first_seen": today,
                    "last_seen": today
                }
        
        return name_changes
    
    def get_member_by_id(self, player_id):
        """IDで団員情報を取得"""
        return self.members.get(player_id)
    
    def get_member_by_name(self, name):
        """名前で団員を検索（現在の名前または過去の名前）"""
        for player_id, data in self.members.items():
            if data["current_name"] == name:
                return data
            if "name_history" in data and name in data["name_history"]:
                return data
        return None
    
    def is_already_fetched(self, event_number):
        """指定されたイベント番号のデータが既に取得済みか確認"""
        return self.last_event_number == event_number
