"""GuildManagerクラスのテスト"""
import pytest
from guild_manager import GuildManager
from models import Guild, User


class TestGuildManager:
    """GuildManagerクラスのテストクラス"""
    
    def test_add_guild(self, db_session, test_user):
        """団の登録をテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        result = manager.add_guild("test_001", "テスト団A")
        
        assert result is True
        
        # ユーザーが団に所属しているか確認
        db_session.refresh(test_user)
        assert test_user.guild_id is not None
        assert test_user.guild.guild_id == "test_001"
        assert test_user.guild.name == "テスト団A"
    
    def test_is_registered(self, db_session, test_user):
        """団の登録確認をテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        # 初期状態では未登録
        assert manager.is_registered() is False
        
        # 団を登録
        manager.add_guild("test_002", "テスト団B")
        
        # 登録済みになる
        assert manager.is_registered() is True
    
    def test_join_existing_guild(self, db_session):
        """既存の団に参加するテスト"""
        # 最初のユーザーが団を作成
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password=User.get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(user1)
        db_session.commit()
        db_session.refresh(user1)
        
        manager1 = GuildManager(db_session, user1.id)
        manager1.add_guild("test_003", "テスト団C")
        
        # 2番目のユーザーが同じ団に参加
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password=User.get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user2)
        
        manager2 = GuildManager(db_session, user2.id)
        result = manager2.add_guild("test_003", "テスト団C")
        
        assert result is True
        
        # 両方のユーザーが同じ団に所属
        db_session.refresh(user1)
        db_session.refresh(user2)
        assert user1.guild_id == user2.guild_id
    
    def test_get_active_guild(self, db_session, test_user):
        """所属団の取得をテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        # 所属団がない場合
        assert manager.get_active_guild() is None
        
        # 団を登録
        manager.add_guild("test_004", "テスト団D")
        
        # マネージャーを再作成してユーザーを再取得
        manager = GuildManager(db_session, test_user.id)
        active_guild = manager.get_active_guild()
        assert active_guild is not None
        assert active_guild.guild_id == "test_004"
        assert active_guild.name == "テスト団D"
    
    def test_get_all_guilds(self, db_session):
        """全団取得をテスト"""
        # 複数のユーザーと団を作成
        last_user = None
        for i in range(3):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password=User.get_password_hash("pass123"),
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            manager = GuildManager(db_session, user.id)
            manager.add_guild(f"test_00{i+5}", f"テスト団{chr(69+i)}")
            last_user = user
        
        # どのユーザーからも全団が見える
        manager = GuildManager(db_session, last_user.id)
        guilds = manager.get_all_guilds()
        
        assert len(guilds) >= 3
        guild_ids = [g.guild_id for g in guilds]
        assert "test_005" in guild_ids
        assert "test_006" in guild_ids
        assert "test_007" in guild_ids
    
    def test_get_guild_by_id(self, db_session, test_user, test_guild):
        """IDによる団取得をテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        guild = manager.get_guild_by_id("test_guild_001")
        
        assert guild is not None
        assert guild.guild_id == "test_guild_001"
        assert guild.name == "テスト団"
    
    def test_duplicate_guild_add(self, db_session, test_user):
        """同じユーザーが重複登録しようとするをテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        # 1回目の登録
        result1 = manager.add_guild("duplicate_001", "重複テスト団")
        assert result1 is True
        
        # 2回目の登録（同じユーザー、別のguild_id）- 既に所属しているので失敗
        manager = GuildManager(db_session, test_user.id)  # マネージャーを再作成
        result2 = manager.add_guild("duplicate_002", "別の団")
        assert result2 is False
        
        # 最初の団にのみ所属
        db_session.refresh(test_user)
        assert test_user.guild.guild_id == "duplicate_001"
    
    def test_max_guild_members(self, db_session):
        """団の最大人数制限をテスト"""
        # 団を作成
        user1 = User(
            username="creator",
            email="creator@example.com",
            hashed_password=User.get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(user1)
        db_session.commit()
        db_session.refresh(user1)
        
        manager1 = GuildManager(db_session, user1.id)
        manager1.add_guild("full_guild", "満員団")
        
        # 29人追加（合計30人）
        for i in range(29):
            user = User(
                username=f"member{i}",
                email=f"member{i}@example.com",
                hashed_password=User.get_password_hash("pass123"),
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            manager = GuildManager(db_session, user.id)
            result = manager.add_guild("full_guild", "満員団")
            assert result is True
        
        # 31人目は失敗
        user31 = User(
            username="member31",
            email="member31@example.com",
            hashed_password=User.get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(user31)
        db_session.commit()
        db_session.refresh(user31)
        
        manager31 = GuildManager(db_session, user31.id)
        result = manager31.add_guild("full_guild", "満員団")
        assert result is False
    
    def test_leave_guild(self, db_session, test_user):
        """団からの脱退をテスト"""
        manager = GuildManager(db_session, test_user.id)
        
        # 団に参加
        manager.add_guild("leave_test", "脱退テスト団")
        db_session.refresh(test_user)
        assert test_user.guild_id is not None
        
        # 脱退
        result = manager.leave_guild()
        assert result is True
        
        db_session.refresh(test_user)
        assert test_user.guild_id is None

