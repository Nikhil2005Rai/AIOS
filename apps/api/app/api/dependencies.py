from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_service import JwtService
from app.auth.repository import UserRepository
from app.db import get_db_session
from app.domain.entities import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db_session)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        user_id = JwtService().verify_access_token(credentials.credentials)
        user = UserRepository(session).get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
        return user
    except (ValueError, jwt.PyJWTError):
        pass # Try checking the Better Auth session table if it's not a JWT

    # Fallback to asking the Better Auth server to verify the session natively
    import os
    import httpx
    
    raw_token = credentials.credentials
    frontend_url = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    
    try:
        headers = {"cookie": f"better-auth.session_token={raw_token}"}
        with httpx.Client() as client:
            resp = client.get(f"{frontend_url}/api/auth/get-session", headers=headers, timeout=5.0)
            
        if resp.status_code == 200:
            data = resp.json()
            if data and "session" in data and "user" in data:
                user_id = data["user"]["id"]
            else:
                raise ValueError("Missing user in session data")
        else:
            raise ValueError(f"Better Auth rejected token with status {resp.status_code}")
            
    except Exception as e:
        print(f"DEBUG: Session verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token or session not found")

    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        print(f"DEBUG: User {user_id} no longer exists")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    
    return user
