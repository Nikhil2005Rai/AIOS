from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.models import UserModel


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        user = self.session.scalar(select(UserModel).where(UserModel.email == email.lower()))
        return self._to_entity(user) if user else None

    def get_by_id(self, user_id: str) -> User | None:
        user = self.session.get(UserModel, user_id)
        return self._to_entity(user) if user else None

    def create(self, email: str, password_hash: str) -> User:
        user = UserModel(email=email.lower(), password_hash=password_hash)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return self._to_entity(user)

    def set_preferred_provider(self, user_id: str, provider: str | None) -> User | None:
        user = self.session.get(UserModel, user_id)
        if user is None:
            return None
        user.preferred_provider = provider.lower() if provider else None
        self.session.commit()
        self.session.refresh(user)
        return self._to_entity(user)

    @staticmethod
    def _to_entity(user: UserModel) -> User:
        return User(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            created_at=user.created_at,
            preferred_provider=user.preferred_provider,
        )
