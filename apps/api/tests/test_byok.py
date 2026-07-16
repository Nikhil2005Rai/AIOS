from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key_repository import UserApiKeyRepository
from app.auth.encryption import EncryptionService
from app.api.deps_providers import get_llm_provider
from app.core.config import settings
from app.domain.entities import User
from app.providers.groq import GroqProvider


def test_set_update_and_delete_user_api_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create = client.post(
        "/users/me/api-keys",
        headers=auth_headers,
        json={"provider": "gemini", "api_key": "user-key-one"},
    )
    assert create.status_code == 200
    assert create.json()["provider"] == "gemini"
    assert "api_key" not in create.json()
    assert "encrypted_key" not in create.json()

    update = client.post(
        "/users/me/api-keys",
        headers=auth_headers,
        json={"provider": "gemini", "api_key": "user-key-two"},
    )
    assert update.status_code == 200
    assert update.json()["provider"] == "gemini"

    delete = client.delete("/users/me/api-keys/gemini", headers=auth_headers)
    assert delete.status_code == 204


def test_llm_provider_prefers_user_key_over_server_key(
    db_session: Session,
    monkeypatch,
) -> None:
    user = User(
        id="user-1",
        email="user@example.com",
        password_hash="hash",
        created_at=None,
    )
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.5-flash")
    monkeypatch.setattr(settings, "llm_api_key", "server-key")

    provider_without_user_key = get_llm_provider(current_user=user, session=db_session)
    assert provider_without_user_key.api_key == "server-key"

    encrypted_key = EncryptionService().encrypt("user-key")
    UserApiKeyRepository(db_session).upsert(
        user_id=user.id,
        provider="gemini",
        encrypted_key=encrypted_key,
    )

    provider_with_user_key = get_llm_provider(current_user=user, session=db_session)
    assert provider_with_user_key.api_key == "user-key"


def test_llm_provider_uses_single_saved_groq_key_when_server_default_is_gemini(
    db_session: Session,
    monkeypatch,
) -> None:
    user = User(
        id="user-2",
        email="groq@example.com",
        password_hash="hash",
        created_at=None,
    )
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "llama-3.1-8b-instant")
    monkeypatch.setattr(settings, "llm_api_key", "server-gemini-key")

    encrypted_key = EncryptionService().encrypt("user-groq-key")
    UserApiKeyRepository(db_session).upsert(
        user_id=user.id,
        provider="groq",
        encrypted_key=encrypted_key,
    )

    provider = get_llm_provider(current_user=user, session=db_session)

    assert isinstance(provider, GroqProvider)
    assert provider.api_key == "user-groq-key"
    assert provider.model == "llama-3.1-8b-instant"
