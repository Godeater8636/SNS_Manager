from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上で設定してください")
        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードには大文字を含めてください")
        if not re.search(r"[0-9]", v):
            raise ValueError("パスワードには数字を含めてください")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上で設定してください")
        return v
