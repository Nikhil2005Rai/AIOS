from cryptography.fernet import Fernet, MultiFernet, InvalidToken

from app.core.config import settings


class EncryptionService:
    """Envelope-style key rotation for BYOK using MultiFernet: new encryptions
    always use the first (primary) key in the list; decryption tries every
    configured key in order, so old ciphertexts keep working after rotation."""

    def __init__(self, keys: list[str] | None = None) -> None:
        self.keys = keys if keys is not None else self._load_keys()

    @staticmethod
    def _load_keys() -> list[str]:
        if settings.encryption_keys:
            parsed = [key.strip() for key in settings.encryption_keys.split(",") if key.strip()]
            if parsed:
                return parsed
        if settings.encryption_key:
            return [settings.encryption_key]
        return []

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        return self._multi_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._multi_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Stored API key could not be decrypted") from exc

    def _multi_fernet(self) -> MultiFernet:
        if not self.keys:
            raise RuntimeError(
                "ENCRYPTION_KEYS (or ENCRYPTION_KEY) is required for BYOK. Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return MultiFernet([Fernet(key.encode("utf-8")) for key in self.keys])
