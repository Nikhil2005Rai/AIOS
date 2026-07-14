from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

@dataclass(slots=True)
class TokenPair:
    access_token: str
    token_type: str = "bearer"


class JwtService:
    def issue_access_token(self, subject: str) -> TokenPair:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expiry_minutes)
        payload = {"sub": subject, "exp": expires_at}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return TokenPair(access_token=token)

    def verify_access_token(self, token: str) -> str:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise ValueError("Token subject is missing")
        return subject
