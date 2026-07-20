from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.rate_limit_dependencies import rate_limit_by_ip
from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.auth.jwt_service import JwtService
from app.auth.passwords import hash_password, verify_password
from app.auth.repository import UserRepository
from app.db import get_db_session
from app.domain.entities import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_ip("register", limit=2, window_seconds=60))],
)
def register(payload: RegisterRequest, session: Annotated[Session, Depends(get_db_session)]) -> TokenResponse:
    users = UserRepository(session)
    if users.get_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = users.create(email=payload.email, password_hash=hash_password(payload.password))
    token = JwtService().issue_access_token(subject=user.id)
    return TokenResponse(access_token=token.access_token, token_type=token.token_type)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_by_ip("login", limit=2, window_seconds=60))],
)
def login(payload: LoginRequest, session: Annotated[Session, Depends(get_db_session)]) -> TokenResponse:
    user = UserRepository(session).get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = JwtService().issue_access_token(subject=user.id)
    return TokenResponse(access_token=token.access_token, token_type=token.token_type)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        preferred_provider=current_user.preferred_provider,
    )
