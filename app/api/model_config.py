from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.permission import require_permission
from app.database.database import get_db
from app.models.user import User
from app.schemas.model_config import ModelConfigUpdate
from app.services.audit_service import write_audit_log
from app.services.model_config_crypto import ModelConfigCryptoError
from app.services.model_config_service import get_active_model_config, get_latest_model_config, serialize_model_config, test_model_connection, upsert_model_config


router = APIRouter(tags=["model-config"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/model-config")
def read_model_config(
    current_user: Annotated[User, Depends(require_permission("model_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    return serialize_model_config(get_latest_model_config(database))


@router.put("/model-config")
def update_model_config(
    payload: ModelConfigUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("model_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    try:
        config, rotated = upsert_model_config(database, provider=payload.provider, model_name=payload.model_name, base_url=str(payload.base_url), api_key=payload.api_key, is_active=payload.is_active)
    except ModelConfigCryptoError as exc:
        write_audit_log(
            database, action="model_config_update", resource_type="model_config", result="failed",
            user_id=current_user.id, resource_name=payload.provider,
            detail="encryption_unavailable", ip_address=_ip(request),
        )
        raise HTTPException(status_code=503, detail="模型配置加密服务不可用") from exc
    write_audit_log(
        database, action="model_config_update", resource_type="model_config", result="success",
        user_id=current_user.id, resource_id=config.id, resource_name=config.provider,
        detail=f"provider={config.provider};model_name={config.model_name};api_key_rotated={str(rotated).lower()}", ip_address=_ip(request),
    )
    return serialize_model_config(config)


@router.post("/model-config/test")
def test_connection(
    request: Request,
    current_user: Annotated[User, Depends(require_permission("model_manage"))],
    database: Annotated[Session, Depends(get_db)],
):
    config = get_active_model_config(database)
    try:
        test_model_connection(database)
    except Exception as exc:
        write_audit_log(
            database, action="model_config_test", resource_type="model_config", result="failed",
            user_id=current_user.id, resource_id=config.id if config else None,
            resource_name=config.provider if config else None, detail=f"connection_failed:{type(exc).__name__}", ip_address=_ip(request),
        )
        raise HTTPException(status_code=502, detail="模型连接测试失败") from exc
    write_audit_log(
        database, action="model_config_test", resource_type="model_config", result="success",
        user_id=current_user.id, resource_id=config.id if config else None,
        resource_name=config.provider if config else "environment_fallback", detail="connection_ok", ip_address=_ip(request),
    )
    return {"success": True}
