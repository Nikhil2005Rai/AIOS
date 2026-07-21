from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.schemas import UserResponse
from app.db import get_db_session
from app.domain.entities import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        emailVerified=current_user.emailVerified,
        createdAt=current_user.createdAt,
        updatedAt=current_user.updatedAt,
        image=current_user.image,
        preferred_provider=current_user.preferred_provider,
    )
