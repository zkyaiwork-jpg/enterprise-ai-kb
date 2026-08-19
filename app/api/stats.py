from fastapi import APIRouter

from app.services.stats_service import get_system_stats


router = APIRouter()


@router.get("/stats")
def get_stats():
    return get_system_stats()
