from fastapi import APIRouter

from app.services.health_service import get_health_status


router = APIRouter()


@router.get("/health")
def get_health():
    return get_health_status()
