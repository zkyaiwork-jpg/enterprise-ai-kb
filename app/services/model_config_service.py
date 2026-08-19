import os
from dataclasses import dataclass

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig
from app.services.model_config_crypto import ModelConfigCryptoError, decrypt_api_key, encrypt_api_key
from app.utils.datetime import serialize_utc_datetime


@dataclass(frozen=True)
class RuntimeModelConfig:
    provider: str
    model_name: str
    base_url: str
    api_key: str
    source: str


def get_active_model_config(database: Session) -> ModelConfig | None:
    return database.scalar(select(ModelConfig).where(ModelConfig.is_active.is_(True)).order_by(ModelConfig.id.desc()).limit(1))


def get_latest_model_config(database: Session) -> ModelConfig | None:
    return database.scalar(select(ModelConfig).order_by(ModelConfig.id.desc()).limit(1))


def serialize_model_config(config: ModelConfig | None) -> dict:
    if config is None:
        return {"provider": None, "model_name": None, "base_url": None, "is_active": False, "api_key_configured": False, "updated_time": None}
    return {
        "provider": config.provider,
        "model_name": config.model_name,
        "base_url": config.base_url,
        "is_active": config.is_active,
        "api_key_configured": bool(config.encrypted_api_key),
        "updated_time": serialize_utc_datetime(config.updated_time),
    }


def upsert_model_config(database: Session, *, provider: str, model_name: str, base_url: str, api_key: str | None, is_active: bool) -> tuple[ModelConfig, bool]:
    existing = get_latest_model_config(database)
    if existing is None:
        if not api_key:
            raise HTTPException(status_code=400, detail="首次配置必须提供API Key")
        encrypted = encrypt_api_key(api_key)
        existing = ModelConfig(provider=provider.lower(), model_name=model_name, base_url=base_url, encrypted_api_key=encrypted, is_active=is_active)
        database.add(existing)
        rotated = True
    else:
        rotated = api_key is not None
        if api_key is not None:
            existing.encrypted_api_key = encrypt_api_key(api_key)
        existing.provider = provider.lower()
        existing.model_name = model_name
        existing.base_url = base_url
        existing.is_active = is_active
    if is_active:
        database.execute(update(ModelConfig).where(ModelConfig.id != existing.id).values(is_active=False))
    database.commit()
    database.refresh(existing)
    return existing, rotated


def resolve_runtime_model_config(database: Session) -> RuntimeModelConfig:
    config = get_active_model_config(database)
    if config is not None:
        try:
            key = decrypt_api_key(config.encrypted_api_key)
        except ModelConfigCryptoError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型服务配置不可用") from exc
        return RuntimeModelConfig(config.provider, config.model_name, config.base_url, key, "database")

    # Development compatibility only. Production should store an encrypted DB
    # configuration and set MODEL_CONFIG_ENCRYPTION_KEY.
    fallback_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if fallback_key:
        return RuntimeModelConfig("deepseek", "deepseek-chat", "https://api.deepseek.com", fallback_key, "environment_fallback")
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型服务尚未配置")


def create_model_client(config: RuntimeModelConfig) -> OpenAI:
    if config.provider not in {"deepseek", "openai", "qwen"}:
        raise HTTPException(status_code=400, detail="暂不支持该模型供应商")
    return OpenAI(api_key=config.api_key, base_url=config.base_url)


def test_model_connection(database: Session) -> None:
    config = resolve_runtime_model_config(database)
    client = create_model_client(config)
    client.chat.completions.create(
        model=config.model_name,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1,
    )
