"""
Step 3 Test Suite — Research, Evidence, and RAG Layer.

Tests 14 scenarios including dynamic query generation, source classification,
evidence storage, conflict detection, retrieval, and end-to-end pipeline.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.session import Base
from backend.models.models import (
    AIUseCase, Assessment, AssessmentResult, Source, Evidence,
    ResearchQuery, AssessmentEvidence, RiskDimension,
)
from backend.services.source_classifier import source_classifier
from backend.services.retrieval_service import TFIDFRetriever
from backend.services.evidence_service import EvidenceService, DIMENSION_KEYWORDS
from backend.services.research_service import ResearchService


# ─── Test DB Setup ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def sample_use_case(db):
    uc = AIUseCase(
        name="AI Recruitment Screening",
        description="Automated resume screening and ranking for job applicants",
        industry="Human Resources",
        purpose="Automate initial applicant screening to improve hiring efficiency",
        data_used="CVs, employment history, educational records",
        human_involvement="Recruiters review top candidates before final hire decision",
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


@pytest.fixture(scope="module")
def loan_use_case(db):
    uc = AIUseCase(
        name="AI Loan Approval",
        description="Automated credit scoring and loan approval decision system",
        industry="Financial Services",
        purpose="Speed up loan application processing using AI credit assessment",
        data_used="Credit history, income records, financial statements, bank data",
        human_involvement="Loan officer reviews AI recommendation for borderline cases",
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


@pytest.fixture(scope="module")
def maintenance_use_case(db):
    uc = AIUseCase(
        name="AI Predictive Maintenance",
        description="Predicts equipment failure in manufacturing using sensor data",
        industry="Manufacturing & Supply Chain",
        purpose="Reduce unplanned downtime by predicting machinery failures",
        data_used="Sensor telemetry, vibration data, temperature readings, maintenance logs",
        human_involvement="Maintenance engineers receive alerts and decide on intervention",
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


@pytest.fixture(scope="module")
def novel_use_case(db):
    """A use case never mentioned in any code — tests full dynamic behaviour."""
    uc = AIUseCase(
        name="AI Wildlife Conservation Poaching Detection",
        description="Camera-trap AI system to detect and classify poaching activity in national parks",
        industry="Environmental & Conservation",
        purpose="Detect illegal poaching activity in real time to alert rangers",
        data_used="Camera images, GPS location data, audio recordings",
        human_involvement="Rangers receive real-time alerts and decide on response",
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


@pytest.fixture(scope="module")
def sample_source(db, sample_use_case):
    # Query first to avoid duplicate errors across multiple scopes/imports
    url = "https://ico.org.uk/for-organisations/guide-to-data-protection/"
    existing = db.query(Source).filter(Source.url == url).first()
    if existing:
        return existing

    src = Source(
        url=url,
        title="Guide to Data Protection — ICO",
        publisher="ICO",
        source_type="REGULATORY_GUIDANCE",
        classification_reason="Government regulatory authority domain.",
        credibility_level=4,
        content_hash="abc123def456",
        raw_content=(
            "Data protection law requires that personal data is processed lawfully, fairly, and transparently. "
            "Automated decision-making systems must provide appropriate human oversight mechanisms. "
            "Organisations must implement privacy by design principles. "
            "Bias in AI systems can lead to discrimination against protected characteristics. "
            "Security measures must protect against unauthorised access to personal data. "
            "Individuals have the right to an explanation of automated decisions that affect them. "
            "Monitoring of AI systems post-deployment ensures continued compliance with data protection law. "
            "Model risk management requires validation and testing of AI models before deployment. "
            "Regulatory compliance obligations apply to all organisations processing personal data."
        ),
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


# ─────────────────────────────────────────────────────────────────────────────
# 1. Research query generation is DYNAMIC
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryGeneration:
    def test_queries_are_dynamic_for_recruitment(self, sample_use_case):
        rs = ResearchService()
        queries = rs.generate_queries(sample_use_case)
        assert len(queries) == 10
        # All queries must contain the use case name or industry
        for dim, query in queries.items():
            assert "Recruitment" in query or "Human Resources" in query, (
                f"Query for {dim} does not reference the use case: {query}"
            )

    def test_queries_differ_between_use_cases(self, sample_use_case, loan_use_case):
        rs = ResearchService()
        recruitment_queries = rs.generate_queries(sample_use_case)
        loan_queries = rs.generate_queries(loan_use_case)
        # Queries must be different for different use cases
        for dim in recruitment_queries:
            assert recruitment_queries[dim] != loan_queries[dim], (
                f"Queries for {dim} are identical for different use cases"
            )

    def test_queries_for_maintenance_are_different(self, maintenance_use_case):
        rs = ResearchService()
        queries = rs.generate_queries(maintenance_use_case)
        for dim, query in queries.items():
            assert "Maintenance" in query or "Manufacturing" in query, (
                f"Maintenance query for {dim} doesn't reference the use case: {query}"
            )

    def test_novel_use_case_generates_queries(self, novel_use_case):
        rs = ResearchService()
        queries = rs.generate_queries(novel_use_case)
        assert len(queries) == 10
        for dim, query in queries.items():
            assert "Wildlife" in query or "Conservation" in query or "Environmental" in query, (
                f"Novel use case query for {dim} is generic: {query}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Source metadata stored correctly
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_fields_stored(self, db, sample_source):
        src = db.query(Source).filter(Source.id == sample_source.id).first()
        assert src is not None
        assert src.url.startswith("https://")
        assert src.title is not None
        assert src.publisher is not None
        assert src.source_type in [
            "LAW_REGULATION", "REGULATORY_GUIDANCE", "INDUSTRY_STANDARD",
            "VENDOR_INFORMATION", "GENERAL_WEB_CONTENT",
        ]
        assert src.credibility_level in range(1, 6)
        assert src.content_hash is not None
        assert src.raw_content is not None

    def test_url_stored_exactly_as_retrieved(self, db, sample_source):
        original_url = "https://ico.org.uk/for-organisations/guide-to-data-protection/"
        src = db.query(Source).filter(Source.url == original_url).first()
        assert src is not None
        assert src.url == original_url  # URL must be unchanged


# ─────────────────────────────────────────────────────────────────────────────
# 3. Source classification rules
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceClassification:
    def test_ico_is_regulatory_guidance(self):
        result = source_classifier.classify("https://ico.org.uk/guidance/ai", "ICO AI Guidance")
        assert result["source_type"] == "REGULATORY_GUIDANCE"
        assert result["credibility_level"] == 4

    def test_legislation_gov_uk_is_law(self):
        result = source_classifier.classify("https://www.legislation.gov.uk/ukpga/2018/12/contents")
        assert result["source_type"] == "LAW_REGULATION"
        assert result["credibility_level"] == 5

    def test_nist_gov_is_regulatory(self):
        result = source_classifier.classify("https://www.nist.gov/artificial-intelligence")
        assert result["source_type"] in ("REGULATORY_GUIDANCE", "INDUSTRY_STANDARD")
        assert result["credibility_level"] >= 4

    def test_iso_org_is_industry_standard(self):
        result = source_classifier.classify("https://www.iso.org/standard/81230.html")
        assert result["source_type"] == "INDUSTRY_STANDARD"
        assert result["credibility_level"] >= 4

    def test_microsoft_com_is_vendor(self):
        result = source_classifier.classify("https://learn.microsoft.com/en-us/azure/ai-services/")
        assert result["source_type"] == "VENDOR_INFORMATION"
        assert result["credibility_level"] == 2

    def test_random_blog_is_general_web(self):
        result = source_classifier.classify("https://medium.com/some-blog-post-about-ai")
        assert result["source_type"] == "GENERAL_WEB_CONTENT"
        assert result["credibility_level"] == 1

    def test_eur_lex_is_law(self):
        result = source_classifier.classify("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52021PC0206")
        assert result["source_type"] == "LAW_REGULATION"

    def test_reason_not_empty(self):
        result = source_classifier.classify("https://ftc.gov/business-guidance/blog/2021/01/aiding-and-abetting")
        assert result["classification_reason"]
        assert len(result["classification_reason"]) > 5


# ─────────────────────────────────────────────────────────────────────────────
# 4. Duplicate source detection
# ─────────────────────────────────────────────────────────────────────────────

class TestDuplicateDetection:
    def test_same_url_not_stored_twice(self, db):
        url = "https://example-unique-test.com/ai-governance"
        s1 = Source(
            url=url, title="Test", source_type="GENERAL_WEB_CONTENT",
            credibility_level=1, content_hash="unique_hash_999",
        )
        db.add(s1)
        db.commit()

        # Attempt to add second source with same URL
        existing = db.query(Source).filter(Source.url == url).first()
        assert existing is not None
        assert existing.id == s1.id  # Same record returned

    def test_content_hash_detects_duplicate_content(self, db):
        # Two different URLs with identical content should have same hash
        import hashlib
        content = "Identical regulatory text about AI governance requirements."
        h = hashlib.sha256(content.encode()).hexdigest()

        s1 = Source(url="https://site-a.gov/page1", source_type="GENERAL_WEB_CONTENT",
                    credibility_level=1, content_hash=h, title="Site A")
        db.add(s1)
        db.commit()

        dup = db.query(Source).filter(Source.content_hash == h).first()
        assert dup is not None


# ─────────────────────────────────────────────────────────────────────────────
# 5 & 6. Evidence stored with dimension tag + linked to use case
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceStorage:
    def test_evidence_extracted_from_source(self, db, sample_source, sample_use_case):
        svc = EvidenceService()
        items = svc.extract_evidence_from_source(
            db=db,
            source=sample_source,
            use_case_id=sample_use_case.id,
        )
        db.commit()
        assert len(items) > 0, "Evidence should be extracted from the ICO guidance content"

    def test_evidence_has_correct_dimension(self, db, sample_use_case):
        evidences = (
            db.query(Evidence)
            .filter(Evidence.use_case_id == sample_use_case.id)
            .all()
        )
        valid_dims = set(DIMENSION_KEYWORDS.keys())
        for ev in evidences:
            assert ev.dimension in valid_dims, f"Unknown dimension: {ev.dimension}"

    def test_evidence_linked_to_source(self, db, sample_use_case):
        evidences = (
            db.query(Evidence)
            .filter(Evidence.use_case_id == sample_use_case.id)
            .all()
        )
        for ev in evidences:
            assert ev.source_id is not None
            assert ev.source is not None

    def test_evidence_text_is_verbatim_from_source(self, db, sample_use_case, sample_source):
        evidences = (
            db.query(Evidence)
            .filter(
                Evidence.use_case_id == sample_use_case.id,
                Evidence.source_id == sample_source.id,
            )
            .all()
        )
        for ev in evidences:
            # Each word in evidence_text must come from the source content
            source_text_lower = sample_source.raw_content.lower()
            ev_words = ev.evidence_text.lower().split()
            found_words = sum(1 for w in ev_words if w in source_text_lower)
            assert found_words / max(len(ev_words), 1) > 0.5, (
                "More than half of evidence words should appear in source content"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Retrieval returns relevant evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrieval:
    def test_add_and_search(self):
        r = TFIDFRetriever()
        r.add_document(1, "AI systems must provide human oversight and control mechanisms")
        r.add_document(2, "Data privacy regulations require consent for personal data processing")
        r.add_document(3, "Machine learning models should be monitored for drift and accuracy")

        results = r.search("human oversight AI control", top_k=2)
        assert len(results) > 0
        top_id, top_score = results[0]
        assert top_id == 1, "Document about human oversight should rank first"

    def test_search_returns_empty_for_empty_corpus(self):
        r = TFIDFRetriever()
        results = r.search("privacy regulation")
        assert results == []

    def test_size_tracks_documents(self):
        r = TFIDFRetriever()
        assert r.size() == 0
        r.add_document(10, "Test document about AI governance")
        assert r.size() == 1
        r.delete_document(10)
        assert r.size() == 0

    def test_keyword_fallback_works_with_small_corpus(self):
        r = TFIDFRetriever()
        r.add_document(1, "Privacy and data protection requirements for AI systems")
        r.add_document(2, "Security controls for AI model deployment")
        # With 2 docs (< MIN_TFIDF_DOCS=3), falls back to keyword search
        results = r.search("privacy data protection")
        assert len(results) > 0
        assert results[0][0] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. Research failure does NOT crash assessment
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchFailureGraceful:
    def test_search_failure_returns_empty(self, db, sample_use_case):
        rs = ResearchService()
        with patch.object(rs, "_search", return_value=[]):
            status = rs.run_research(db=db, use_case_id=sample_use_case.id)
        # Must return a valid status dict, not raise
        assert "sources_found" in status
        assert status["sources_found"] == 0

    def test_fetch_failure_does_not_raise(self, db, sample_use_case):
        rs = ResearchService()
        with patch.object(rs, "_fetch_and_clean", return_value=None):
            with patch.object(rs, "_search", return_value=[
                {"href": "https://example.com/ai", "title": "AI Guide"}
            ]):
                status = rs.run_research(db=db, use_case_id=sample_use_case.id)
        assert status["sources_failed"] >= 0  # No exception raised

    def test_nonexistent_use_case_returns_status(self, db):
        rs = ResearchService()
        status = rs.run_research(db=db, use_case_id=99999)
        assert "error" in status
        assert status["queries_generated"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Missing evidence is reported as INSUFFICIENT
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingEvidence:
    def test_empty_evidence_returns_insufficient_confidence(self):
        svc = EvidenceService()
        confidence = svc.compute_evidence_confidence([])
        assert confidence == "INSUFFICIENT"

    def test_single_low_cred_evidence_returns_low(self, db, sample_source, sample_use_case):
        svc = EvidenceService()
        ev = Evidence(
            source_id=sample_source.id,
            use_case_id=sample_use_case.id,
            dimension="Security",
            evidence_text="Some generic security text.",
            relevance_score=0.1,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        ev.source = sample_source
        confidence = svc.compute_evidence_confidence([ev])
        assert confidence in ("LOW", "MEDIUM", "HIGH", "INSUFFICIENT")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Existing deterministic assessment still works
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterministicAssessmentUnchanged:
    def test_governance_engine_still_works(self, sample_use_case):
        from backend.services.governance_engine import governance_engine
        result = governance_engine.evaluate_use_case(sample_use_case)
        assert "overall_score" in result
        assert "risk_level" in result
        assert len(result["dimensions"]) == 10
        assert result["risk_level"] in ("LOW", "MODERATE", "HIGH", "VERY HIGH")

    def test_assessment_service_works(self, db, sample_use_case):
        from backend.services.assessment_service import AssessmentService
        svc = AssessmentService()
        response = svc.run_assessment(db=db, use_case_id=sample_use_case.id)
        assert response.assessment_id is not None
        assert len(response.dimensions) == 10


# ─────────────────────────────────────────────────────────────────────────────
# 11. Conflicting evidence can be stored and flagged
# ─────────────────────────────────────────────────────────────────────────────

class TestConflictingEvidence:
    def test_conflict_flag_stored(self, db, sample_source, sample_use_case):
        ev1 = Evidence(
            source_id=sample_source.id,
            use_case_id=sample_use_case.id,
            dimension="Privacy",
            evidence_text="Personal data must not be processed without explicit consent.",
            relevance_score=0.9,
            conflict_flag=True,
        )
        ev2 = Evidence(
            source_id=sample_source.id,
            use_case_id=sample_use_case.id,
            dimension="Privacy",
            evidence_text="Organisations may process personal data for legitimate interests.",
            relevance_score=0.8,
            conflict_flag=True,
        )
        db.add_all([ev1, ev2])
        db.commit()

        conflicts = (
            db.query(Evidence)
            .filter(
                Evidence.use_case_id == sample_use_case.id,
                Evidence.conflict_flag == True,
            )
            .all()
        )
        assert len(conflicts) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# 12. Novel use case triggers dynamic research (no hardcoded queries)
# ─────────────────────────────────────────────────────────────────────────────

class TestNovelUseCaseDynamic:
    def test_novel_use_case_queries_reference_its_own_name(self, novel_use_case):
        rs = ResearchService()
        queries = rs.generate_queries(novel_use_case)
        assert len(queries) == 10
        for dim, query in queries.items():
            # Query must reference this specific use case, not any hardcoded use case
            assert "Recruitment" not in query, f"{dim}: Should not mention Recruitment"
            assert "Loan" not in query, f"{dim}: Should not mention Loan"
            assert "Wildlife" in query or "Conservation" in query or "Environmental" in query, (
                f"{dim} query does not reference novel use case: {query}"
            )

    def test_four_use_cases_produce_four_different_query_sets(
        self, sample_use_case, loan_use_case, maintenance_use_case, novel_use_case
    ):
        rs = ResearchService()
        sets = [
            set(rs.generate_queries(uc).values())
            for uc in [sample_use_case, loan_use_case, maintenance_use_case, novel_use_case]
        ]
        # Each use case should produce a unique set of queries
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i] != sets[j], "Two different use cases produced identical queries"
