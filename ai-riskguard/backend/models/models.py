from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.database.session import Base


def utc_now():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Core Entities
# ─────────────────────────────────────────────────────────────────────────────

class AIUseCase(Base):
    """Represents an AI use case submitted for governance assessment."""
    __tablename__ = "ai_use_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    industry = Column(String(100), nullable=False, index=True)
    purpose = Column(Text, nullable=False)
    data_used = Column(Text, nullable=False)
    human_involvement = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    assessments = relationship("Assessment", back_populates="use_case", cascade="all, delete-orphan")
    research_queries = relationship("ResearchQuery", back_populates="use_case", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="use_case", cascade="all, delete-orphan")


class Assessment(Base):
    """Represents a governance risk assessment run for an AI use case."""
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    use_case_id = Column(Integer, ForeignKey("ai_use_cases.id"), nullable=False)
    overall_score = Column(Float, default=1.0)
    risk_level = Column(String(50), default="LOW")
    status = Column(String(50), default="Completed")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    use_case = relationship("AIUseCase", back_populates="assessments")
    results = relationship("AssessmentResult", back_populates="assessment", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="assessment", cascade="all, delete-orphan")
    assessment_evidences = relationship("AssessmentEvidence", back_populates="assessment", cascade="all, delete-orphan")


class RiskDimension(Base):
    """Represents one of the 10 core governance risk dimensions."""
    __tablename__ = "risk_dimensions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)

    # Relationships
    recommendations = relationship("Recommendation", back_populates="dimension")


class AssessmentResult(Base):
    """Stores the deterministic score and reasoning for one governance dimension."""
    __tablename__ = "assessment_results"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    dimension = Column(String(100), nullable=False)
    score = Column(Float, default=1.0)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    assessment = relationship("Assessment", back_populates="results")
    evidences = relationship("Evidence", back_populates="assessment_result")


class Recommendation(Base):
    """Actionable remediation recommendation generated for an assessment."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    dimension_id = Column(Integer, ForeignKey("risk_dimensions.id"), nullable=True)
    text = Column(Text, nullable=False)
    priority = Column(String(50), default="Medium")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    assessment = relationship("Assessment", back_populates="recommendations")
    dimension = relationship("RiskDimension", back_populates="recommendations")


# ─────────────────────────────────────────────────────────────────────────────
# Research & Evidence Layer (Step 3)
# ─────────────────────────────────────────────────────────────────────────────

class ResearchQuery(Base):
    """Records a search query generated for a use case's research run."""
    __tablename__ = "research_queries"

    id = Column(Integer, primary_key=True, index=True)
    use_case_id = Column(Integer, ForeignKey("ai_use_cases.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    dimension = Column(String(100), nullable=True)   # which dimension this query targets
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    use_case = relationship("AIUseCase", back_populates="research_queries")
    evidences = relationship("Evidence", back_populates="research_query")


class Source(Base):
    """A web source retrieved during research — carries full metadata and classified type."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False, unique=True)
    title = Column(String(500), nullable=True)
    publisher = Column(String(255), nullable=True)

    # Controlled vocabulary: LAW_REGULATION | REGULATORY_GUIDANCE | INDUSTRY_STANDARD |
    #                        VENDOR_INFORMATION | GENERAL_WEB_CONTENT
    source_type = Column(String(50), nullable=False, default="GENERAL_WEB_CONTENT")
    classification_reason = Column(Text, nullable=True)

    # credibility_level 1 (low) – 5 (highest), derived from source_type
    credibility_level = Column(Integer, default=1)

    retrieved_at = Column(DateTime(timezone=True), default=utc_now)
    content_hash = Column(String(64), nullable=True, index=True)   # SHA-256 hex
    raw_content = Column(Text, nullable=True)    # cleaned plain-text, max ~8 000 chars

    # Relationships
    evidences = relationship("Evidence", back_populates="source")


class Evidence(Base):
    """An extracted evidence sentence/paragraph linked to a governance dimension."""
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    use_case_id = Column(Integer, ForeignKey("ai_use_cases.id"), nullable=False)
    research_query_id = Column(Integer, ForeignKey("research_queries.id"), nullable=True)
    assessment_result_id = Column(Integer, ForeignKey("assessment_results.id"), nullable=True)

    dimension = Column(String(100), nullable=False)
    evidence_text = Column(Text, nullable=False)       # verbatim extracted sentence(s)
    evidence_summary = Column(Text, nullable=True)     # short summary / first sentence
    relevance_score = Column(Float, default=0.0)       # 0.0 – 1.0
    conflict_flag = Column(Boolean, default=False)     # True if conflicts with another source

    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    source = relationship("Source", back_populates="evidences")
    use_case = relationship("AIUseCase", back_populates="evidences")
    research_query = relationship("ResearchQuery", back_populates="evidences")
    assessment_result = relationship("AssessmentResult", back_populates="evidences")
    assessment_evidences = relationship("AssessmentEvidence", back_populates="evidence", cascade="all, delete-orphan")


class AssessmentEvidence(Base):
    """Linking table — connects a completed assessment to supporting evidence records."""
    __tablename__ = "assessment_evidences"

    assessment_id = Column(Integer, ForeignKey("assessments.id"), primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id"), primary_key=True)

    # Relationships
    assessment = relationship("Assessment", back_populates="assessment_evidences")
    evidence = relationship("Evidence", back_populates="assessment_evidences")
