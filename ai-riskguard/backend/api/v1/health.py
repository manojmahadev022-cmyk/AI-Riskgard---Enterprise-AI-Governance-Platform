from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database.session import get_db
from backend.schemas.schemas import HealthResponse
from backend.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System Health"])
def get_health_status(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend service and database connectivity."""
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        version=settings.VERSION,
    )
