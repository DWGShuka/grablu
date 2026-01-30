"""MemberTrackerクラスのテスト"""
import pytest
from member_tracker import MemberTracker
from models import Member, NameHistory, EventData


class TestMemberTracker:
    """MemberTrackerクラスのテストクラス"""
    
    def test_add_or_update_member_new(self, db_session, test_guild):
        """新規団員の追加をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        member_data = {
            "player_id": "99999999",
            "name": "新規プレイヤー",
            "rank": "10000"
        }
        
        member = tracker.add_or_update_member(member_data)
        
        assert member.player_id == "99999999"
        assert member.current_name == "新規プレイヤー"
        assert member.guild_id == test_guild.id
    
    def test_add_or_update_member_existing(self, db_session, test_guild, test_member):
        """既存団員の更新をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 名前を変更
        member_data = {
            "player_id": "12345678",
            "name": "変更後の名前",
            "rank": "5000"
        }
        
        member = tracker.add_or_update_member(member_data)
        
        assert member.player_id == "12345678"
        assert member.current_name == "変更後の名前"
        
        # 名前変更履歴が記録されているか確認
        history = db_session.query(NameHistory).filter(
            NameHistory.member_id == member.id
        ).first()
        
        assert history is not None
        assert history.old_name == "テストプレイヤー"
        assert history.new_name == "変更後の名前"
    
    def test_get_member_by_id(self, db_session, test_guild, test_member):
        """IDによる団員取得のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        member = tracker.get_member_by_id("12345678")
        
        assert member is not None
        assert member.player_id == "12345678"
        assert member.current_name == "テストプレイヤー"
    
    def test_get_all_members(self, db_session, test_guild):
        """全団員取得のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 複数の団員を追加
        tracker.add_or_update_member({"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"})
        tracker.add_or_update_member({"player_id": "22222222", "name": "プレイヤー2", "rank": "2000"})
        tracker.add_or_update_member({"player_id": "33333333", "name": "プレイヤー3", "rank": "3000"})
        
        members = tracker.get_all_members()
        
        assert len(members) >= 3
    
    def test_save_event_data(self, db_session, test_guild):
        """イベントデータ保存のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        members_data = [
            {"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"},
            {"player_id": "22222222", "name": "プレイヤー2", "rank": "2000"}
        ]
        
        event_number = "123"
        tracker.save_event_data(event_number, members_data)
        
        # イベントデータが保存されたか確認
        event_count = db_session.query(EventData).filter(
            EventData.guild_id == test_guild.id,
            EventData.event_number == event_number
        ).count()
        
        assert event_count == 2
    
    def test_duplicate_event_data_prevention(self, db_session, test_guild):
        """重複イベントデータの防止をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        members_data = [
            {"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"}
        ]
        
        event_number = "456"
        
        # 1回目の保存
        tracker.save_event_data(event_number, members_data)
        
        # 2回目の保存（重複）
        tracker.save_event_data(event_number, members_data)
        
        # 重複が除外されているか確認
        event_count = db_session.query(EventData).filter(
            EventData.guild_id == test_guild.id,
            EventData.event_number == event_number,
            EventData.player_id == "11111111"
        ).count()
        
        assert event_count == 1
    
    def test_name_change_detection(self, db_session, test_guild):
        """名前変更検出のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 初回登録
        tracker.add_or_update_member({
            "player_id": "77777777",
            "name": "元の名前",
            "rank": "5000"
        })
        
        # 名前変更
        tracker.add_or_update_member({
            "player_id": "77777777",
            "name": "新しい名前",
            "rank": "4900"
        })
        
        # 履歴確認
        member = tracker.get_member_by_id("77777777")
        history_count = db_session.query(NameHistory).filter(
            NameHistory.member_id == member.id
        ).count()
        
        assert history_count >= 1
