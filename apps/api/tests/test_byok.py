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
    if hasattr(provider_without_user_key, "inner"):
        provider_without_user_key = getattr(provider_without_user_key, "inner")
    assert provider_without_user_key.api_key == "server-key"

    encrypted_key = EncryptionService().encrypt("user-key")
    UserApiKeyRepository(db_session).upsert(
        user_id=user.id,
        provider="gemini",
        encrypted_key=encrypted_key,
    )

    provider_with_user_key = get_llm_provider(current_user=user, session=db_session)
    if hasattr(provider_with_user_key, "inner"):
        provider_with_user_key = getattr(provider_with_user_key, "inner")
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
    if hasattr(provider, "inner"):
        provider = getattr(provider, "inner")

    assert isinstance(provider, GroqProvider)
    assert provider.api_key == "user-groq-key"
    assert provider.model == "llama-3.1-8b-instant"


def test_list_user_api_keys(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    list_empty = client.get("/users/me/api-keys", headers=auth_headers)
    assert list_empty.status_code == 200
    assert list_empty.json()["providers"] == []

    save = client.post(
        "/users/me/api-keys",
        headers=auth_headers,
        json={"provider": "gemini", "api_key": "user-key-gemini"},
    )
    assert save.status_code == 200

    list_one = client.get("/users/me/api-keys", headers=auth_headers)
    assert list_one.status_code == 200
    providers = list_one.json()["providers"]
    assert len(providers) == 1
    assert providers[0]["provider"] == "gemini"
    assert "api_key" not in providers[0]
    assert "encrypted_key" not in providers[0]

    save_groq = client.post(
        "/users/me/api-keys",
        headers=auth_headers,
        json={"provider": "groq", "api_key": "user-key-groq"},
    )
    assert save_groq.status_code == 200

    list_two = client.get("/users/me/api-keys", headers=auth_headers)
    assert list_two.status_code == 200
    providers_two = list_two.json()["providers"]
    assert len(providers_two) == 2
    providers_names = {p["provider"] for p in providers_two}
    assert providers_names == {"gemini", "groq"}

    resp_text = list_two.text
    assert "user-key" not in resp_text
    assert "encrypted" not in resp_text


def test_decryption_failure_raises_400(
    db_session: Session,
    monkeypatch,
) -> None:
    import pytest
    from fastapi import HTTPException
    user = User(
        id="user-decrypt-fail",
        email="fail@example.com",
        password_hash="hash",
        created_at=None,
    )
    UserApiKeyRepository(db_session).upsert(
        user_id=user.id,
        provider="gemini",
        encrypted_key="corrupted-invalid-token",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        get_llm_provider(current_user=user, session=db_session)
    
    assert exc_info.value.status_code == 400
    assert "could not be decrypted and needs to be re-saved" in exc_info.value.detail
