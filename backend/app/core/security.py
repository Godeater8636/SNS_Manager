import base64
import os
import secrets
import string
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _get_private_key() -> str:
    return settings.JWT_PRIVATE_KEY.replace("\\n", "\n")


def _get_public_key() -> str:
    return settings.JWT_PUBLIC_KEY.replace("\\n", "\n")


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _get_public_key(), algorithms=[settings.JWT_ALGORITHM])


# ── AES-256-GCM Encryption ────────────────────────────────────────────────────

def _get_aes_key() -> bytes:
    raw = settings.AES_ENCRYPTION_KEY
    return base64.b64decode(raw) if raw else os.urandom(32)


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext → base64url(nonce || ciphertext || tag)"""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode()


def decrypt(token: str) -> str:
    """Decrypt base64url(nonce || ciphertext || tag) → plaintext"""
    key = _get_aes_key()
    raw = base64.urlsafe_b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


# ── Slug Generator ────────────────────────────────────────────────────────────

def generate_slug(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))
