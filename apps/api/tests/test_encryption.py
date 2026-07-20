import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.auth.encryption import EncryptionService


KEY_A = Fernet.generate_key().decode("utf-8")
KEY_B = Fernet.generate_key().decode("utf-8")


def test_round_trip_single_key() -> None:
    service = EncryptionService(keys=[KEY_A])
    ciphertext = service.encrypt("my-secret-api-key")
    assert service.decrypt(ciphertext) == "my-secret-api-key"


def test_rotation_compatibility_old_ciphertext_decrypts_with_new_key_list() -> None:
    old_service = EncryptionService(keys=[KEY_A])
    ciphertext = old_service.encrypt("rotated-secret")

    # Simulate rotation: new key prepended, old key retained
    rotated_service = EncryptionService(keys=[KEY_B, KEY_A])
    assert rotated_service.decrypt(ciphertext) == "rotated-secret"


def test_new_encryption_uses_primary_key() -> None:
    rotated_service = EncryptionService(keys=[KEY_B, KEY_A])
    ciphertext = rotated_service.encrypt("new-secret")

    # Old key alone cannot decrypt (proves new encryption used KEY_B, not KEY_A)
    old_only = EncryptionService(keys=[KEY_A])
    with pytest.raises(ValueError, match="could not be decrypted"):
        old_only.decrypt(ciphertext)

    # Primary key alone can decrypt
    primary_only = EncryptionService(keys=[KEY_B])
    assert primary_only.decrypt(ciphertext) == "new-secret"


def test_backward_compat_single_encryption_key_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "encryption_keys", "")
    monkeypatch.setattr(settings, "encryption_key", KEY_A)

    service = EncryptionService()
    ciphertext = service.encrypt("compat-secret")
    assert service.decrypt(ciphertext) == "compat-secret"


def test_load_keys_parses_comma_separated_with_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "encryption_keys", f"  {KEY_A} , {KEY_B} , ")
    monkeypatch.setattr(settings, "encryption_key", "")

    keys = EncryptionService._load_keys()
    assert keys == [KEY_A, KEY_B]


def test_rotation_script_reencrypts_stored_keys(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.models import UserApiKeyModel, UserModel
    from scripts.rotate_encryption_key import main

    # Create a user
    user = UserModel(
        id="rotate-user",
        email="rotate@example.com",
        password_hash="hash",
    )
    db_session.add(user)
    db_session.flush()

    # Encrypt a key with KEY_A
    old_service = EncryptionService(keys=[KEY_A])
    encrypted = old_service.encrypt("original-api-key")
    row = UserApiKeyModel(
        user_id=user.id,
        provider="gemini",
        encrypted_key=encrypted,
    )
    db_session.add(row)
    db_session.flush()

    # Monkeypatch the rotation script to use [KEY_B, KEY_A] and point at test DB
    monkeypatch.setattr("scripts.rotate_encryption_key.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.rotate_encryption_key.get_engine", lambda: db_session.bind)
    monkeypatch.setattr("scripts.rotate_encryption_key.EncryptionService", lambda: EncryptionService(keys=[KEY_B, KEY_A]))

    main()

    # The row should now decrypt with KEY_B alone
    from sqlalchemy import select
    updated_row = db_session.execute(
        select(UserApiKeyModel).where(UserApiKeyModel.id == row.id)
    ).scalar_one()
    new_only = EncryptionService(keys=[KEY_B])
    assert new_only.decrypt(updated_row.encrypted_key) == "original-api-key"
