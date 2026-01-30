"""Userモデルのテスト"""
import pytest
from models import User


class TestUserModel:
    """Userモデルのテストクラス"""
    
    def test_create_user(self, db_session):
        """ユーザー作成のテスト"""
        user = User(
            username="newuser",
            email="newuser@example.com",
            hashed_password=User.get_password_hash("password123"),
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_admin is False
    
    def test_password_hashing(self):
        """パスワードハッシュ化のテスト"""
        password = "testpassword123"
        hashed = User.get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_password_verification(self, test_user):
        """パスワード検証のテスト"""
        # 正しいパスワード
        assert test_user.verify_password("testpass123") is True
        
        # 間違ったパスワード
        assert test_user.verify_password("wrongpassword") is False
    
    def test_email_uniqueness(self, db_session, test_user):
        """メールアドレスの一意性制約のテスト"""
        # 同じメールアドレスで別のユーザーを作成しようとする
        duplicate_user = User(
            username="anotheruser",
            email="test@example.com",  # 既存のメールアドレス
            hashed_password=User.get_password_hash("password"),
            is_active=True
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_username_not_unique(self, db_session, test_user):
        """ユーザー名は重複可能であることをテスト"""
        # 同じusernameで別のユーザーを作成
        user2 = User(
            username="testuser",  # 既存のusernameと同じ
            email="another@example.com",
            hashed_password=User.get_password_hash("password"),
            is_active=True
        )
        db_session.add(user2)
        db_session.commit()
        
        # 正常に作成できることを確認
        assert user2.id is not None
        assert user2.username == test_user.username
        assert user2.email != test_user.email
    
    def test_bcrypt_72_byte_limit(self):
        """bcryptの72バイト制限への対応をテスト"""
        # 72バイトを超える長いパスワード
        long_password = "a" * 100
        
        # エラーが発生しないことを確認
        hashed = User.get_password_hash(long_password)
        assert len(hashed) > 0
        
        # 検証も正常に動作することを確認
        user = User(
            username="test",
            email="test@test.com",
            hashed_password=hashed
        )
        assert user.verify_password(long_password) is True
