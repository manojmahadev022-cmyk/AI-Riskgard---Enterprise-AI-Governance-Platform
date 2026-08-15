"""Governance Assessment API Router for AI RiskGuard.

Endpoints:
    POST /assessments/{use_case_id}                   — deterministic assessment (Step 2)
    GET  /assessments                                  — list all assessments
    GET  /assessments/{id}                             — get assessment detail
    POST /assessments/{use_case_id}/research-backed    — research + evidence + assessment (Step 3)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database.session import get_db
from backend.models.models import (
    AIUseCase, Assessment, AssessmentResult, AssessmentEvidence, Evidence
)
from backend.schemas.schemas import (
    AssessmentDetailResponse,
    AssessmentSummaryResponse,
    ResearchBackedAssessmentResponse,
    ResearchBackedDimensionResult,
    EvidenceInDimension,
    ResearchStatusResponse,
    UseCaseSummarySchema,
)
from backend.services.assessment_service import assessment_service
from backend.services.research_service import research_service
from backend.services.evidence_service import evidence_service
from backend.services.governance_engine import governance_engine

router = APIRouter()


# ─── Step 2: Deterministic assessment (unchanged) ───────────────────────────

@router.post(
    "/assessments/{use_case_id}",
    response_model=AssessmentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Governance Assessment Engine"],
)
def run_assessment(use_case_id: int, db: Session = Depends(get_db)):
    """Run deterministic governance assessment for a use case and persist results."""
    return assessment_service.run_assessment(db=db, use_case_id=use_case_id)


@router.get(
    "/assessments",
    response_model=List[AssessmentSummaryResponse],
    tags=["Governance Assessment Engine"],
)
def list_assessments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve history of all completed governance assessments."""
    return assessment_service.get_assessments(db=db, skip=skip, limit=limit)


@router.get(
    "/assessments/{id}",
    response_model=AssessmentDetailResponse,
    tags=["Governance Assessment Engine"],
)
def get_assessment(id: int, db: Session = Depends(get_db)):
    """Retrieve detailed assessment report including all 10 dimension scores."""
    return assessment_service.get_assessment_by_id(db=db, assessment_id=id)


# ─── Step 3: Research-backed assessment ─────────────────────────────────────

@router.post(
    "/assessments/{use_case_id}/research-backed",
    response_model=ResearchBackedAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Research-Backed Assessment"],
)
def run_research_backed_assessment(use_case_id: int, db: Session = Depends(get_db)):
    """Full pipeline: research → evidence extraction → governance assessment.

    Steps:
      1. Load AI use case
      2. Run research pipeline (search, fetch, classify, store sources + evidence)
      3. Run deterministic governance scoring engine
      4. For each dimension: attach retrieved evidence + compute confidence
      5. Link evidence to assessment
      6. Return enriched assessment response
    """
    # Step 1 — Load use case
    use_case = db.query(AIUseCase).filter(AIUseCase.id == use_case_id).first()
    if not use_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Use Case with ID {use_case_id} not found",
        )

    # Step 2 — Research pipeline
    research_status = research_service.run_research(db=db, use_case_id=use_case_id)

    # Step 3 — Deterministic governance scoring (unchanged engine)
    evaluation = governance_engine.evaluate_use_case(use_case)

    # Step 4 — Persist assessment
    assessment = Assessment(
        use_case_id=use_case.id,
        overall_score=evaluation["overall_score"],
        risk_level=evaluation["risk_level"],
        status="Completed",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Step 5 — Persist dimension results and attach evidence
    dimension_results: List[ResearchBackedDimensionResult] = []
    linked_evidence_ids: set = set()

    for dim_eval in evaluation["dimensions"]:
        dim_name = dim_eval["dimension"]

        # Persist AssessmentResult
        ar = AssessmentResult(
            assessment_id=assessment.id,
            dimension=dim_name,
            score=dim_eval["score"],
            reasoning=dim_eval["reasoning"],
        )
        db.add(ar)
        db.flush()

        # Retrieve stored evidence for this dimension
        evidences = evidence_service.get_evidence_for_dimension(
            db=db, use_case_id=use_case_id, dimension=dim_name, top_k=5
        )

        # Link evidence to assessment
        for ev in evidences:
            if ev.id not in linked_evidence_ids:
                ae = AssessmentEvidence(
                    assessment_id=assessment.id,
                    evidence_id=ev.id,
                )
                db.merge(ae)
                linked_evidence_ids.add(ev.id)
            # Also update assessment_result_id on the evidence
            ev.assessment_result_id = ar.id

        confidence = evidence_service.compute_evidence_confidence(evidences)

        # Build evidence response items
        evidence_items: List[EvidenceInDimension] = []
        for ev in evidences:
            evidence_items.append(EvidenceInDimension(
                evidence_id=ev.id,
                source_id=ev.source_id,
                text=ev.evidence_text[:500],
                source_title=ev.source.title if ev.source else None,
                source_type=ev.source.source_type if ev.source else None,
                url=ev.source.url if ev.source else None,
                publisher=ev.source.publisher if ev.source else None,
                credibility_level=ev.source.credibility_level if ev.source else None,
                conflict_flag=ev.conflict_flag,
            ))

        dimension_results.append(ResearchBackedDimensionResult(
            dimension=dim_name,
            score=dim_eval["score"],
            reasoning=dim_eval["reasoning"],
            evidence_count=len(evidence_items),
            evidence_confidence=confidence,
            evidence=evidence_items,
        ))

    db.commit()

    return ResearchBackedAssessmentResponse(
        assessment_id=assessment.id,
        use_case=UseCaseSummarySchema(
            name=use_case.name,
            industry=use_case.industry,
        ),
        overall_score=evaluation["overall_score"],
        risk_level=evaluation["risk_level"],
        research_status=ResearchStatusResponse(**research_status),
        dimensions=dimension_results,
        created_at=assessment.created_at,
    )
