from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionService:
    """Temporary Fernet encryption for BYOK.

    Phase 7 security hardening should replace this single server-held key with
    real KMS/secret-manager backed envelope encryption and rotation.
    """

    def __init__(self, key: str | None = None) -> None:
        self.key = key if key is not None else settings.encryption_key

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        return self._fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Stored API key could not be decrypted") from exc

    def _fernet(self) -> Fernet:
        if not self.key:
            raise RuntimeError(
                "ENCRYPTION_KEY is required for BYOK. Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return Fernet(self.key.encode("utf-8"))
