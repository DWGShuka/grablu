"""MemberTrackerクラスのテスト"""
import pytest
from member_tracker import MemberTracker
from models import Member, NameHistory, EventData, MemberRanking


class TestMemberTracker:
    """MemberTrackerクラスのテストクラス"""
    
    def test_update_members_new(self, db_session, test_guild):
        """新規団員の追加をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        members_data = [
            {"player_id": "99999999", "name": "新規プレイヤー", "rank": "10000"}
        ]
        
        changes = tracker.update_members(members_data)
        
        # 名前変更なし
        assert len(changes) == 0
        
        # 団員が登録されたか確認
        member = tracker.get_member_by_id("99999999")
        assert member is not None
        assert member.player_id == "99999999"
        assert member.current_name == "新規プレイヤー"
        assert member.guild_id == test_guild.id
    
    def test_update_members_name_change(self, db_session, test_guild, test_member):
        """既存団員の名前変更をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 名前を変更
        members_data = [
            {"player_id": "12345678", "name": "変更後の名前", "rank": "5000"}
        ]
        
        changes = tracker.update_members(members_data)
        
        # 名前変更が検出されたか確認
        assert len(changes) == 1
        assert "12345678" in changes
        assert changes["12345678"]["old_name"] == "テストプレイヤー"
        assert changes["12345678"]["new_name"] == "変更後の名前"
        
        # データベースが更新されたか確認
        member = tracker.get_member_by_id("12345678")
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
        members_data = [
            {"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"},
            {"player_id": "22222222", "name": "プレイヤー2", "rank": "2000"},
            {"player_id": "33333333", "name": "プレイヤー3", "rank": "3000"}
        ]
        tracker.update_members(members_data)
        
        members = tracker.get_all_members()
        
        assert len(members) >= 3
        player_ids = [m.player_id for m in members]
        assert "11111111" in player_ids
        assert "22222222" in player_ids
        assert "33333333" in player_ids
    
    def test_save_event_data(self, db_session, test_guild):
        """イベントデータ保存のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # まず団員を登録
        members_data = [
            {"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"},
            {"player_id": "22222222", "name": "プレイヤー2", "rank": "2000"}
        ]
        tracker.update_members(members_data)
        
        # イベントデータを保存
        event_number = 123
        tracker.save_event_data(event_number, members_data)
        
        # イベントデータが保存されたか確認
        event = db_session.query(EventData).filter(
            EventData.guild_id == test_guild.id,
            EventData.event_number == event_number
        ).first()
        
        assert event is not None
        assert event.event_number == event_number
        
        # ランキングデータが保存されたか確認
        rankings_count = db_session.query(MemberRanking).filter(
            MemberRanking.event_id == event.id
        ).count()
        
        assert rankings_count == 2
    
    def test_duplicate_event_data_prevention(self, db_session, test_guild):
        """重複イベントデータの確認をテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 団員を登録
        members_data = [
            {"player_id": "11111111", "name": "プレイヤー1", "rank": "1000"}
        ]
        tracker.update_members(members_data)
        
        event_number = 456
        
        # 1回目の保存
        assert tracker.is_already_fetched(event_number) is False
        tracker.save_event_data(event_number, members_data)
        
        # 2回目の確認（既に取得済み）
        assert tracker.is_already_fetched(event_number) is True
    
    def test_get_event_data(self, db_session, test_guild):
        """イベントデータ取得のテスト"""
        tracker = MemberTracker(db_session, test_guild.id)
        
        # 団員を登録
        members_data = [
            {"player_id": "77777777", "name": "テスト", "rank": "5000"}
        ]
        tracker.update_members(members_data)
        
        # イベントデータを保存
        event_number = 789
        tracker.save_event_data(event_number, members_data)
        
        # データを取得
        event_data = tracker.get_event_data(event_number)
        
        assert event_data is not None
        assert event_data["event_number"] == event_number
        assert len(event_data["members"]) == 1
        assert event_data["members"][0]["player_id"] == "77777777"

