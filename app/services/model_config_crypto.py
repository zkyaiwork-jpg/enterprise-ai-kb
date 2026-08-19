import os
from cryptography.fernet import Fernet, InvalidToken


class ModelConfigCryptoError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("MODEL_CONFIG_ENCRYPTION_KEY", "").strip()
    if not key:
        raise ModelConfigCryptoError("模型配置加密服务未配置")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ModelConfigCryptoError("模型配置加密密钥无效") from exc


def encrypt_api_key(api_key: str) -> str:
    if not api_key.strip():
        raise ModelConfigCryptoError("API Key不能为空")
    return _fernet().encrypt(api_key.strip().encode()).decode("ascii")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return _fernet().decrypt(encrypted_api_key.encode("ascii")).decode()
    except (InvalidToken, ValueError, UnicodeError) as exc:
        raise ModelConfigCryptoError("模型凭证无法解密") from exc
