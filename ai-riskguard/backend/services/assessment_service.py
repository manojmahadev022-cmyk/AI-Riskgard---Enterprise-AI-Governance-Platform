from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from backend.models.models import AIUseCase, Assessment, AssessmentResult
from backend.schemas.schemas import AIUseCaseCreate, AssessmentDetailResponse
from backend.services.governance_engine import governance_engine


class AssessmentService:
    """Core orchestration service handling AI use cases and governance risk assessments."""

    def create_use_case(self, db: Session, use_case_in: AIUseCaseCreate) -> AIUseCase:
        """Persist a new AI use case in the database."""
        db_obj = AIUseCase(
            name=use_case_in.name,
            description=use_case_in.description,
            industry=use_case_in.industry,
            purpose=use_case_in.purpose,
            data_used=use_case_in.data_used,
            human_involvement=use_case_in.human_involvement,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_use_cases(self, db: Session, skip: int = 0, limit: int = 100) -> List[AIUseCase]:
        """Retrieve list of registered AI use cases."""
        return db.query(AIUseCase).offset(skip).limit(limit).all()

    def get_use_case_by_id(self, db: Session, use_case_id: int) -> Optional[AIUseCase]:
        """Retrieve single AI use case by ID."""
        return db.query(AIUseCase).filter(AIUseCase.id == use_case_id).first()

    def run_assessment(self, db: Session, use_case_id: int) -> AssessmentDetailResponse:
        """Evaluate an AI use case across 10 governance dimensions and persist the assessment."""
        use_case = self.get_use_case_by_id(db, use_case_id)
        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI Use Case with ID {use_case_id} not found",
            )

        # Run deterministic governance evaluation engine
        evaluation = governance_engine.evaluate_use_case(use_case)

        # Create Assessment record
        assessment = Assessment(
            use_case_id=use_case.id,
            overall_score=evaluation["overall_score"],
            risk_level=evaluation["risk_level"],
            status="Completed",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # Create AssessmentResult records for all 10 dimensions
        for dim_eval in evaluation["dimensions"]:
            result = AssessmentResult(
                assessment_id=assessment.id,
                dimension=dim_eval["dimension"],
                score=dim_eval["score"],
                reasoning=dim_eval["reasoning"],
            )
            db.add(result)

        db.commit()
        db.refresh(assessment)

        return self.format_assessment_detail(assessment)

    def get_assessments(self, db: Session, skip: int = 0, limit: int = 100) -> List[Assessment]:
        """Retrieve all completed governance assessments."""
        return db.query(Assessment).offset(skip).limit(limit).all()

    def get_assessment_by_id(self, db: Session, assessment_id: int) -> AssessmentDetailResponse:
        """Retrieve a specific assessment by ID with all 10 dimension results."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found",
            )
        return self.format_assessment_detail(assessment)

    def format_assessment_detail(self, assessment: Assessment) -> AssessmentDetailResponse:
        """Format an Assessment SQLAlchemy object into the specified AssessmentDetailResponse JSON model."""
        dimensions_list = [
            {
                "dimension": res.dimension,
                "score": res.score,
                "reasoning": res.reasoning,
            }
            for res in assessment.results
        ]

        return AssessmentDetailResponse(
            assessment_id=assessment.id,
            use_case={
                "name": assessment.use_case.name,
                "industry": assessment.use_case.industry,
            },
            overall_score=assessment.overall_score,
            risk_level=assessment.risk_level,
            dimensions=dimensions_list,
            created_at=assessment.created_at,
        )


assessment_service = AssessmentService()
