"""GuildManagerクラスのテスト"""
import pytest
from guild_manager import GuildManager
from models import Guild


class TestGuildManager:
    """GuildManagerクラスのテストクラス"""
    
    def test_add_guild(self, db_session):
        """団の登録をテスト"""
        manager = GuildManager(db_session)
        
        result = manager.add_guild("test_001", "テスト団A")
        
        assert result is True
        
        # データベースに保存されているか確認
        guild = manager.get_guild_by_id("test_001")
        assert guild is not None
        assert guild.guild_id == "test_001"
        assert guild.name == "テスト団A"
    
    def test_is_registered(self, db_session):
        """団の登録確認をテスト"""
        manager = GuildManager(db_session)
        
        # 初期状態では未登録
        assert manager.is_registered() is False
        
        # 団を登録
        manager.add_guild("test_002", "テスト団B")
        
        # 登録済みになる
        assert manager.is_registered() is True
    
    def test_set_active_guild(self, db_session, test_guild):
        """アクティブ団の設定をテスト"""
        manager = GuildManager(db_session)
        
        # 別の団を追加
        manager.add_guild("test_003", "テスト団C")
        
        # 新しい団をアクティブ化
        result = manager.set_active_guild("test_003")
        assert result is True
        
        # 新しい団がアクティブになる
        active_guild = manager.get_active_guild()
        assert active_guild is not None
        assert active_guild.guild_id == "test_003"
        
        # 古い団は非アクティブになる
        db_session.refresh(test_guild)
        assert test_guild.is_active == 0
    
    def test_get_active_guild(self, db_session):
        """アクティブ団の取得をテスト"""
        manager = GuildManager(db_session)
        
        # アクティブな団がない場合
        assert manager.get_active_guild() is None
        
        # 団を登録してアクティブ化
        manager.add_guild("test_004", "テスト団D")
        manager.set_active_guild("test_004")
        
        active_guild = manager.get_active_guild()
        assert active_guild is not None
        assert active_guild.guild_id == "test_004"
        assert active_guild.name == "テスト団D"
    
    def test_get_all_guilds(self, db_session):
        """全団取得をテスト"""
        manager = GuildManager(db_session)
        
        # 複数の団を登録
        manager.add_guild("test_005", "テスト団E")
        manager.add_guild("test_006", "テスト団F")
        manager.add_guild("test_007", "テスト団G")
        
        guilds = manager.get_all_guilds()
        
        assert len(guilds) >= 3
        guild_ids = [g.guild_id for g in guilds]
        assert "test_005" in guild_ids
        assert "test_006" in guild_ids
        assert "test_007" in guild_ids
    
    def test_get_guild_by_id(self, db_session, test_guild):
        """IDによる団取得をテスト"""
        manager = GuildManager(db_session)
        
        guild = manager.get_guild_by_id("test_guild_001")
        
        assert guild is not None
        assert guild.guild_id == "test_guild_001"
        assert guild.name == "テスト団"
    
    def test_duplicate_guild_add(self, db_session):
        """重複する団IDの登録をテスト"""
        manager = GuildManager(db_session)
        
        # 1回目の登録
        result1 = manager.add_guild("duplicate_001", "重複テスト団")
        assert result1 is True
        
        # 2回目の登録（同じguild_id）
        result2 = manager.add_guild("duplicate_001", "別の名前")
        assert result2 is False  # 重複なので失敗
        
        # 団は1つのみ
        guilds = db_session.query(Guild).filter(
            Guild.guild_id == "duplicate_001"
        ).all()
        assert len(guilds) == 1
        assert guilds[0].name == "重複テスト団"  # 最初の名前のまま

