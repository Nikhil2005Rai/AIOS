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
        token = jwt.encode(payload, settings.better_auth_secret, algorithm=settings.jwt_algorithm)
        return TokenPair(access_token=token)

    def verify_access_token(self, token: str) -> str:
        payload = jwt.decode(token, settings.better_auth_secret, algorithms=[settings.jwt_algorithm])
        
        # Better Auth JWT payload structure might contain 'user' object or 'userId' directly
        subject = payload.get("sub")
        
        if "user" in payload and isinstance(payload["user"], dict):
            subject = payload["user"].get("id") or subject
            
        subject = payload.get("userId") or subject
        
        if not isinstance(subject, str) or not subject:
            raise ValueError(f"Token subject is missing. Payload: {payload}")
        return subject
