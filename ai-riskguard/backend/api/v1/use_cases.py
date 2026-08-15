from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database.session import get_db
from backend.schemas.schemas import AIUseCaseCreate, AIUseCaseResponse
from backend.services.assessment_service import assessment_service

router = APIRouter()


@router.post("/use-cases", response_model=AIUseCaseResponse, status_code=status.HTTP_201_CREATED, tags=["AI Use Cases"])
def create_use_case(use_case: AIUseCaseCreate, db: Session = Depends(get_db)):
    """Create and register a new AI use case for assessment."""
    return assessment_service.create_use_case(db=db, use_case_in=use_case)


@router.get("/use-cases", response_model=List[AIUseCaseResponse], tags=["AI Use Cases"])
def list_use_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all registered AI use cases."""
    return assessment_service.get_use_cases(db=db, skip=skip, limit=limit)


@router.get("/use-cases/{use_case_id}", response_model=AIUseCaseResponse, tags=["AI Use Cases"])
def get_use_case(use_case_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a specific AI use case."""
    use_case = assessment_service.get_use_case_by_id(db=db, use_case_id=use_case_id)
    if not use_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Use Case with ID {use_case_id} not found",
        )
    return use_case
