from fastapi import APIRouter
from app.core.database import check_db_connection
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
def health_check():
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status["connected"] else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }
