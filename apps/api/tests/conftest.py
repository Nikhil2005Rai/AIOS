import os
from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")
os.environ["UPSTASH_REDIS_REST_URL"] = ""
os.environ["UPSTASH_REDIS_REST_TOKEN"] = ""

from app.api.deps_providers import get_llm_provider
from app.auth.security import create_access_token
from app.auth.repository import UserRepository
from app.db import Base, get_db_session
from app.infrastructure import models  # noqa: F401
from app.main import app
from app.providers.base import LLMMessage, LLMProvider, LLMResponse, ToolSchema


class FakeLLMProvider(LLMProvider):
    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        return LLMResponse(content="ANSWER: Fake assistant reply")


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def create_auth_headers(client: TestClient, db_session: Session):
    def _create(email: str = "user@example.com") -> dict[str, str]:
        repo = UserRepository(db_session)
        user = repo.get_by_email(email)
        if not user:
            user = repo.create_user_with_password(email, "hashed_pw", "Test User")
        token = create_access_token({"sub": user.id, "email": user.email})
        return {"Authorization": f"Bearer {token}"}
    return _create


@pytest.fixture()
def auth_headers(create_auth_headers) -> dict[str, str]:
    return create_auth_headers("user@example.com")
