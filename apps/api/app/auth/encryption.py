import base64
import hashlib
import logging
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_KEY_SEED = "aios-default-encryption-key-fallback-2026"


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

    @staticmethod
    def _get_fallback_fernet_key() -> str:
        seed = settings.better_auth_secret or DEFAULT_FALLBACK_KEY_SEED
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        return self._multi_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._multi_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Stored API key could not be decrypted") from exc

    def _multi_fernet(self) -> MultiFernet:
        valid_fernets = []
        if self.keys:
            for key in self.keys:
                clean_key = key.strip("'\" \t\r\n")
                try:
                    valid_fernets.append(Fernet(clean_key.encode("utf-8")))
                except Exception:
                    logger.warning(f"Invalid Fernet key in configuration: '{clean_key[:10]}...'")
                    continue

        if not valid_fernets:
            logger.warning("No valid ENCRYPTION_KEYS configured in environment. Using deterministic fallback key.")
            fallback_key = self._get_fallback_fernet_key()
            valid_fernets.append(Fernet(fallback_key.encode("utf-8")))

        return MultiFernet(valid_fernets)
