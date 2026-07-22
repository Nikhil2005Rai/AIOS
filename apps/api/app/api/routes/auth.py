from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.schemas import UserResponse, RegisterRequest, LoginRequest, TokenResponse
from app.auth.repository import UserRepository
from app.auth.security import hash_password, verify_password, create_access_token
from app.db import get_db_session
from app.domain.entities import User


router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        emailVerified=user.emailVerified,
        createdAt=user.createdAt,
        updatedAt=user.updatedAt,
        image=user.image,
        preferred_provider=user.preferred_provider,
    )


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    repo = UserRepository(session)
    existing_user = repo.get_by_email(body.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )

    pw_hash = hash_password(body.password)
    user = repo.create_user_with_password(
        email=body.email,
        password_hash=pw_hash,
        name=body.name,
    )
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=_to_user_response(user))


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    repo = UserRepository(session)
    user_model = repo.get_model_by_email(body.email)
    if not user_model or not verify_password(body.password, user_model.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = repo._to_entity(user_model)
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=_to_user_response(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _to_user_response(current_user)
