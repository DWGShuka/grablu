"""
認証関連のスキーマ
"""
from pydantic import BaseModel, EmailStr, Field, validator


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    username: str = Field(..., min_length=3, max_length=50, description="ユーザー名")
    password: str = Field(..., min_length=6, description="パスワード")


class RegisterRequest(BaseModel):
    """新規登録リクエスト"""
    username: str = Field(..., min_length=3, max_length=50, description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., min_length=6, description="パスワード")
    password_confirm: str = Field(..., min_length=6, description="パスワード（確認）")
    
    @validator("password_confirm")
    def passwords_match(cls, v, values):
        """パスワード一致確認"""
        if "password" in values and v != values["password"]:
            raise ValueError("パスワードが一致しません")
        return v


class UserResponse(BaseModel):
    """ユーザー情報レスポンス"""
    id: int
    username: str
    email: str
    is_admin: bool
    email_verified: bool
    
    model_config = {"from_attributes": True}
