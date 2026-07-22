from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.models import UserModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        user = self.session.scalar(select(UserModel).where(UserModel.email == email.lower()))
        return self._to_entity(user) if user else None

    def get_model_by_email(self, email: str) -> UserModel | None:
        return self.session.scalar(select(UserModel).where(UserModel.email == email.lower()))

    def get_by_id(self, user_id: str) -> User | None:
        user = self.session.get(UserModel, user_id)
        return self._to_entity(user) if user else None

    def create_user_with_password(self, email: str, password_hash: str, name: str) -> User:
        from uuid import uuid4
        now = utc_now()
        user_id = f"usr_{uuid4().hex[:16]}"
        user = UserModel(
            id=user_id,
            name=name or email.split("@")[0].capitalize(),
            email=email.lower(),
            password_hash=password_hash,
            emailVerified=True,
            createdAt=now,
            updatedAt=now,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return self._to_entity(user)

    def get_or_create_by_clerk_id(self, clerk_user_id: str, email: str = "", name: str = "") -> User:
        user = self.session.get(UserModel, clerk_user_id)
        if user is not None:
            return self._to_entity(user)

        now = utc_now()
        user = UserModel(
            id=clerk_user_id,
            name=name,
            email=email or f"{clerk_user_id}@clerk.user",
            emailVerified=True,
            createdAt=now,
            updatedAt=now,
        )
        try:
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return self._to_entity(user)
        except Exception:
            self.session.rollback()
            user = self.session.get(UserModel, clerk_user_id)
            if user is not None:
                return self._to_entity(user)
            raise

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
            name=user.name,
            emailVerified=user.emailVerified,
            createdAt=user.createdAt,
            updatedAt=user.updatedAt,
            image=user.image,
            preferred_provider=user.preferred_provider,
        )
