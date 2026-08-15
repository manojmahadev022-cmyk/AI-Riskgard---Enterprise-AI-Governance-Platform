"""Research API Router for AI RiskGuard.

Endpoints:
    POST /research/{use_case_id}              — run research pipeline
    GET  /research/{use_case_id}              — get queries + research status
    GET  /sources/{use_case_id}               — list sources for a use case
    GET  /evidence/{use_case_id}              — list all evidence
    GET  /evidence/{use_case_id}/{dimension}  — evidence for one dimension
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database.session import get_db
from backend.models.models import ResearchQuery, Source, Evidence, AIUseCase
from backend.schemas.schemas import (
    ResearchQueryResponse,
    SourceResponse,
    EvidenceResponse,
    ResearchStatusResponse,
)
from backend.services.research_service import research_service
from backend.services.evidence_service import evidence_service

router = APIRouter()


@router.post(
    "/research/{use_case_id}",
    response_model=ResearchStatusResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Research & Evidence"],
)
def run_research(use_case_id: int, db: Session = Depends(get_db)):
    """Trigger research pipeline for a use case: search → fetch → classify → extract evidence."""
    use_case = db.query(AIUseCase).filter(AIUseCase.id == use_case_id).first()
    if not use_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Use Case with ID {use_case_id} not found",
        )
    result = research_service.run_research(db=db, use_case_id=use_case_id)
    return ResearchStatusResponse(**result)


@router.get(
    "/research/{use_case_id}",
    response_model=ResearchStatusResponse,
    tags=["Research & Evidence"],
)
def get_research_status(use_case_id: int, db: Session = Depends(get_db)):
    """Return current research status and query count for a use case."""
    queries = db.query(ResearchQuery).filter(ResearchQuery.use_case_id == use_case_id).all()
    sources = db.query(Source).join(
        Evidence, Source.id == Evidence.source_id
    ).filter(Evidence.use_case_id == use_case_id).distinct().all()
    evidences = evidence_service.get_all_evidence(db, use_case_id)
    dims = len(set(e.dimension for e in evidences))
    conflicts = sum(1 for e in evidences if e.conflict_flag)

    return ResearchStatusResponse(
        use_case_id=use_case_id,
        queries_generated=len(queries),
        sources_found=len(sources),
        sources_fetched=len(sources),
        sources_failed=0,
        evidence_extracted=len(evidences),
        dimensions_supported=dims,
        conflicts_detected=conflicts,
    )


@router.get(
    "/sources/{use_case_id}",
    response_model=List[SourceResponse],
    tags=["Research & Evidence"],
)
def get_sources(use_case_id: int, db: Session = Depends(get_db)):
    """Return all sources retrieved for a use case."""
    sources = (
        db.query(Source)
        .join(Evidence, Source.id == Evidence.source_id)
        .filter(Evidence.use_case_id == use_case_id)
        .distinct()
        .all()
    )
    return sources


@router.get(
    "/evidence/{use_case_id}",
    response_model=List[EvidenceResponse],
    tags=["Research & Evidence"],
)
def get_evidence(use_case_id: int, db: Session = Depends(get_db)):
    """Return all stored evidence for a use case with source metadata."""
    evidences = evidence_service.get_all_evidence(db, use_case_id)
    return _build_evidence_responses(evidences)


@router.get(
    "/evidence/{use_case_id}/{dimension}",
    response_model=List[EvidenceResponse],
    tags=["Research & Evidence"],
)
def get_evidence_for_dimension(
    use_case_id: int,
    dimension: str,
    db: Session = Depends(get_db),
):
    """Return evidence for a specific governance dimension."""
    evidences = evidence_service.get_evidence_for_dimension(
        db=db, use_case_id=use_case_id, dimension=dimension
    )
    return _build_evidence_responses(evidences)


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_evidence_responses(evidences) -> List[EvidenceResponse]:
    result = []
    for ev in evidences:
        result.append(EvidenceResponse(
            id=ev.id,
            source_id=ev.source_id,
            use_case_id=ev.use_case_id,
            dimension=ev.dimension,
            evidence_text=ev.evidence_text,
            evidence_summary=ev.evidence_summary,
            relevance_score=ev.relevance_score,
            conflict_flag=ev.conflict_flag,
            source_title=ev.source.title if ev.source else None,
            source_type=ev.source.source_type if ev.source else None,
            source_url=ev.source.url if ev.source else None,
            publisher=ev.source.publisher if ev.source else None,
            credibility_level=ev.source.credibility_level if ev.source else None,
        ))
    return result
