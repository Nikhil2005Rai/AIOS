from datetime import datetime, timezone, timedelta
import hashlib
import os
import secrets
from typing import Any

import jwt
from app.core.config import settings


JWT_SECRET = getattr(settings, "jwt_secret", None) or os.getenv("JWT_SECRET") or "aios-super-secret-jwt-key-2026"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA256 and a random salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, hashed_password: str | None) -> bool:
    """Verify password against stored salt$hash."""
    if not hashed_password or "$" not in hashed_password:
        return False
    try:
        salt_hex, key_hex = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(key, expected_key)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify JWT access token. Raises jwt.PyJWTError on invalid token."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": True})
    return payload
