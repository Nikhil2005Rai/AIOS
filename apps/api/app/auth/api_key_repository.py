from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import UserApiKey
from app.infrastructure.models import UserApiKeyModel


class UserApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_user_provider(self, user_id: str, provider: str) -> UserApiKey | None:
        api_key = self.session.scalar(
            select(UserApiKeyModel).where(
                UserApiKeyModel.user_id == user_id,
                UserApiKeyModel.provider == provider.lower(),
            )
        )
        return self._to_entity(api_key) if api_key else None

    def list_for_user(self, user_id: str) -> list[UserApiKey]:
        api_keys = self.session.scalars(
            select(UserApiKeyModel).where(UserApiKeyModel.user_id == user_id).order_by(UserApiKeyModel.created_at.asc())
        ).all()
        return [self._to_entity(api_key) for api_key in api_keys]

    def upsert(self, user_id: str, provider: str, encrypted_key: str) -> UserApiKey:
        normalized_provider = provider.lower()
        api_key = self.session.scalar(
            select(UserApiKeyModel).where(
                UserApiKeyModel.user_id == user_id,
                UserApiKeyModel.provider == normalized_provider,
            )
        )
        if api_key is None:
            api_key = UserApiKeyModel(user_id=user_id, provider=normalized_provider, encrypted_key=encrypted_key)
            self.session.add(api_key)
        else:
            api_key.encrypted_key = encrypted_key

        self.session.commit()
        self.session.refresh(api_key)
        return self._to_entity(api_key)

    def delete(self, user_id: str, provider: str) -> bool:
        api_key = self.session.scalar(
            select(UserApiKeyModel).where(
                UserApiKeyModel.user_id == user_id,
                UserApiKeyModel.provider == provider.lower(),
            )
        )
        if api_key is None:
            return False
        self.session.delete(api_key)
        self.session.commit()
        return True

    @staticmethod
    def _to_entity(api_key: UserApiKeyModel) -> UserApiKey:
        return UserApiKey(
            id=api_key.id,
            user_id=api_key.user_id,
            provider=api_key.provider,
            encrypted_key=api_key.encrypted_key,
            created_at=api_key.created_at,
        )
