from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# AI Use Case Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AIUseCaseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    industry: str = Field(..., min_length=2, max_length=100)
    purpose: str = Field(..., min_length=2)
    data_used: str = Field(..., min_length=2)
    human_involvement: str = Field(..., min_length=2)

    @field_validator("name", "description", "industry", "purpose", "data_used", "human_involvement")
    @classmethod
    def check_not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty or whitespace only.")
        return v.strip()


class AIUseCaseCreate(AIUseCaseBase):
    pass


class AIUseCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    purpose: Optional[str] = None
    data_used: Optional[str] = None
    human_involvement: Optional[str] = None


class AIUseCaseResponse(AIUseCaseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UseCaseSummarySchema(BaseModel):
    name: str
    industry: str


# ─────────────────────────────────────────────────────────────────────────────
# Assessment Schemas (Step 2 — unchanged)
# ─────────────────────────────────────────────────────────────────────────────

class DimensionResultSchema(BaseModel):
    dimension: str
    score: float
    reasoning: str
    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    use_case_id: int


class AssessmentSummaryResponse(BaseModel):
    id: int
    use_case_id: int
    overall_score: float
    risk_level: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssessmentDetailResponse(BaseModel):
    assessment_id: int
    use_case: UseCaseSummarySchema
    overall_score: float
    risk_level: str
    dimensions: List[DimensionResultSchema]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Research & Evidence Schemas (Step 3)
# ─────────────────────────────────────────────────────────────────────────────

class ResearchQueryResponse(BaseModel):
    id: int
    use_case_id: int
    query_text: str
    dimension: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SourceResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    publisher: Optional[str]
    source_type: str
    classification_reason: Optional[str]
    credibility_level: int
    retrieved_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvidenceResponse(BaseModel):
    id: int
    source_id: int
    use_case_id: int
    dimension: str
    evidence_text: str
    evidence_summary: Optional[str]
    relevance_score: float
    conflict_flag: bool
    # Nested source info for display
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    credibility_level: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class ResearchStatusResponse(BaseModel):
    use_case_id: int
    queries_generated: int
    sources_found: int
    sources_fetched: int
    sources_failed: int
    evidence_extracted: int
    dimensions_supported: int
    conflicts_detected: int


# ─── Research-backed assessment (enriched output) ────────────────────────────

class EvidenceInDimension(BaseModel):
    evidence_id: int
    source_id: int
    text: str
    source_title: Optional[str]
    source_type: Optional[str]
    url: Optional[str]
    publisher: Optional[str]
    credibility_level: Optional[int]
    conflict_flag: bool = False


class ResearchBackedDimensionResult(BaseModel):
    dimension: str
    score: float
    reasoning: str
    evidence_count: int
    evidence_confidence: str   # HIGH | MEDIUM | LOW | INSUFFICIENT
    evidence: List[EvidenceInDimension]


class ResearchBackedAssessmentResponse(BaseModel):
    assessment_id: int
    use_case: UseCaseSummarySchema
    overall_score: float
    risk_level: str
    research_status: ResearchStatusResponse
    dimensions: List[ResearchBackedDimensionResult]
    created_at: datetime
