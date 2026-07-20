"""Rotate the BYOK encryption key.

Usage:
  1. Generate a new key:
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  2. Prepend it to ENCRYPTION_KEYS in your .env, comma-separated, newest first,
     keeping the old key(s) in the list — e.g.:
       ENCRYPTION_KEYS=new-key-here,old-key-here
  3. Run this script to re-encrypt every stored API key with the new primary key:
       python -m scripts.rotate_encryption_key
  4. Only after this completes successfully, you may remove the old key(s) from
     ENCRYPTION_KEYS. Removing an old key BEFORE running this script will make any
     API key still encrypted with it permanently undecryptable.
"""
from app.auth.encryption import EncryptionService
from app.db import SessionLocal, get_engine
from app.infrastructure.models import UserApiKeyModel


def main() -> None:
    get_engine()
    session = SessionLocal()
    service = EncryptionService()
    try:
        rows = session.query(UserApiKeyModel).all()
        rotated = 0
        for row in rows:
            plaintext = service.decrypt(row.encrypted_key)
            row.encrypted_key = service.encrypt(plaintext)
            rotated += 1
        session.commit()
        print(f"Rotated {rotated} stored API key(s) to the current primary encryption key.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
