from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.schemas import ApiKeyMetadataResponse, ApiKeyUpsertRequest
from app.auth.api_key_repository import UserApiKeyRepository
from app.auth.encryption import EncryptionService
from app.auth.repository import UserRepository
from app.db import get_db_session
from app.domain.entities import User
from app.providers.registry import PROVIDERS


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/api-keys", response_model=ApiKeyMetadataResponse)
def set_api_key(
    payload: ApiKeyUpsertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> ApiKeyMetadataResponse:
    provider = payload.provider.lower()
    if provider not in PROVIDERS:
        supported = ", ".join(sorted(PROVIDERS))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider. Use one of: {supported}.")

    encrypted_key = EncryptionService().encrypt(payload.api_key)
    api_key = UserApiKeyRepository(session).upsert(
        user_id=current_user.id,
        provider=provider,
        encrypted_key=encrypted_key,
    )
    UserRepository(session).set_preferred_provider(current_user.id, provider)
    return ApiKeyMetadataResponse(provider=api_key.provider, created_at=api_key.created_at)


@router.delete("/me/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    keys = UserApiKeyRepository(session)
    keys.delete(user_id=current_user.id, provider=provider)
    if current_user.preferred_provider == provider.lower():
        remaining_keys = keys.list_for_user(current_user.id)
        next_provider = remaining_keys[0].provider if len(remaining_keys) == 1 else None
        UserRepository(session).set_preferred_provider(current_user.id, next_provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
