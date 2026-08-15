from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.core.config import settings
from backend.database.session import init_db, SessionLocal
from backend.models.models import RiskDimension
from backend.api.v1 import health, use_cases, assessments, research


def seed_risk_dimensions(db_session=None):
    """Seed the 10 core governance risk dimensions if not already present."""
    dimensions = [
        {"code": "DATA", "name": "Data", "weight": 1.0, "description": "Evaluates data sensitivity, quality, lineage, and synthetic source risks."},
        {"code": "PRIVACY", "name": "Privacy", "weight": 1.0, "description": "Evaluates exposure of personal identifiers, sensitive records, and consent."},
        {"code": "BIAS_FAIRNESS", "name": "Bias/Fairness", "weight": 1.0, "description": "Evaluates potential for disparate impact and demographic bias."},
        {"code": "HUMAN_OVERSIGHT", "name": "Human Oversight", "weight": 1.0, "description": "Evaluates human control level, manual override capability, and meaningful review."},
        {"code": "EXPLAINABILITY", "name": "Explainability", "weight": 1.0, "description": "Evaluates model transparency, decision logic interpretability, and disclosures."},
        {"code": "SECURITY", "name": "Security", "weight": 1.0, "description": "Evaluates attack surface, prompt injection, and operational robustness."},
        {"code": "DECISION_IMPACT", "name": "Decision Impact", "weight": 1.0, "description": "Evaluates impact severity on human life, health, rights, or financial livelihood."},
        {"code": "REGULATORY_EXPOSURE", "name": "Regulatory Exposure", "weight": 1.0, "description": "Evaluates statutory compliance obligations under AI regulations."},
        {"code": "MODEL_RISK", "name": "Model Risk", "weight": 1.0, "description": "Evaluates hallucination probability, output drift, and error severity."},
        {"code": "MONITORING", "name": "Monitoring", "weight": 1.0, "description": "Evaluates post-deployment audit logging and real-time performance tracking."},
    ]

    db = db_session if db_session else SessionLocal()
    try:
        for dim in dimensions:
            existing = db.query(RiskDimension).filter(RiskDimension.code == dim["code"]).first()
            if not existing:
                db.add(RiskDimension(**dim))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Could not seed risk dimensions: {e}")
    finally:
        if not db_session:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB schema and seed reference data."""
    init_db()
    seed_risk_dimensions()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Enterprise AI Governance Research & Assessment Platform — "
        "MODUS AI Build Challenge, Assignment 7"
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api/v1
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(use_cases.router, prefix=settings.API_V1_STR)
app.include_router(assessments.router, prefix=settings.API_V1_STR)
app.include_router(research.router, prefix=settings.API_V1_STR)

# Also register under /api for backward compatibility
app.include_router(use_cases.router, prefix="/api")
app.include_router(assessments.router, prefix="/api")
app.include_router(research.router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "step": "3 — Research + Evidence + RAG",
    }
