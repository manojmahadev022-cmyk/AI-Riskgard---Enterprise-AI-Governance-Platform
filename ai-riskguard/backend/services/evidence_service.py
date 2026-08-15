"""Evidence Extraction Service for AI RiskGuard.

Scans cleaned source text to find sentences relevant to specific governance
dimensions. All evidence is verbatim text from the source — nothing is invented.
"""
from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from backend.models.models import Evidence, Source, ResearchQuery
from backend.services.ai_provider import ai_provider
from backend.services.retrieval_service import retriever

logger = logging.getLogger(__name__)


# ─── Dimension keyword mappings ────────────────────────────────────────────
# Used to locate sentences relevant to each governance dimension.

DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "Data": [
        "data quality", "data governance", "data lineage", "training data",
        "dataset", "data collection", "data integrity", "data management",
        "synthetic data", "data pipeline", "data provenance",
    ],
    "Privacy": [
        "privacy", "personal data", "gdpr", "data protection", "pii",
        "personally identifiable", "consent", "data subject", "right to erasure",
        "sensitive data", "confidentiality", "anonymisation", "pseudonymisation",
    ],
    "Bias/Fairness": [
        "bias", "fairness", "discrimination", "disparate impact", "demographic",
        "protected characteristic", "algorithmic fairness", "equal opportunity",
        "proxy variable", "unfair", "debiasing",
    ],
    "Human Oversight": [
        "human oversight", "human review", "human-in-the-loop", "human control",
        "meaningful human oversight", "right to explanation", "override",
        "human supervision", "accountability", "audit trail",
    ],
    "Explainability": [
        "explainability", "explainable", "transparency", "interpretability",
        "black box", "black-box", "decision explanation", "algorithmic transparency",
        "xai", "right to explanation", "model explanation",
    ],
    "Security": [
        "security", "cybersecurity", "adversarial", "data poisoning",
        "prompt injection", "attack", "vulnerability", "robustness",
        "threat", "access control", "authentication",
    ],
    "Decision Impact": [
        "decision", "impact", "harm", "risk to individuals", "life-altering",
        "critical decision", "consequential", "employment decision",
        "financial decision", "healthcare decision", "legal decision",
    ],
    "Regulatory Exposure": [
        "regulation", "regulatory", "compliance", "legal requirement",
        "eu ai act", "gdpr", "ccpa", "hipaa", "eeoc", "ftc", "sec",
        "supervisory authority", "enforcement", "obligation",
    ],
    "Model Risk": [
        "model risk", "hallucination", "accuracy", "reliability", "drift",
        "model failure", "false positive", "false negative", "uncertainty",
        "model validation", "overfitting", "degradation",
    ],
    "Monitoring": [
        "monitoring", "audit", "logging", "oversight mechanism", "post-deployment",
        "continuous monitoring", "performance tracking", "drift detection",
        "incident response", "feedback loop", "model monitoring",
    ],
}


class EvidenceService:
    """Extracts, stores, and retrieves governance evidence from source content."""

    def extract_evidence_from_source(
        self,
        db: Session,
        source: Source,
        use_case_id: int,
        research_query_id: Optional[int] = None,
    ) -> List[Evidence]:
        """Extract evidence sentences for each governance dimension from a source.

        Only verbatim sentences from source.raw_content are stored.
        Returns the list of Evidence ORM objects added to the session.
        """
        if not source.raw_content or len(source.raw_content.strip()) < 50:
            logger.debug("Source %d has no usable content — skipping.", source.id)
            return []

        text = source.raw_content
        sentences = self._split_sentences(text)
        extracted: List[Evidence] = []

        for dimension, keywords in DIMENSION_KEYWORDS.items():
            relevant = self._find_relevant_sentences(sentences, keywords, max_sentences=3)
            if not relevant:
                continue

            evidence_text = " ".join(relevant)
            relevance_score = self._compute_relevance(evidence_text, keywords)
            summary = ai_provider.extract_key_sentences(evidence_text, dimension, max_sentences=1)

            ev = Evidence(
                source_id=source.id,
                use_case_id=use_case_id,
                research_query_id=research_query_id,
                dimension=dimension,
                evidence_text=evidence_text[:2000],
                evidence_summary=summary[:500] if summary else None,
                relevance_score=round(relevance_score, 3),
                conflict_flag=False,
            )
            db.add(ev)
            extracted.append(ev)

        return extracted

    def detect_conflicts(self, db: Session, use_case_id: int) -> int:
        """Mark evidence as conflicting when two sources present contradictory signals.

        Returns count of conflicts detected.
        """
        evidences = (
            db.query(Evidence)
            .filter(Evidence.use_case_id == use_case_id)
            .all()
        )

        by_dimension: Dict[str, List[Evidence]] = {}
        for ev in evidences:
            by_dimension.setdefault(ev.dimension, []).append(ev)

        conflict_count = 0
        for dim_evs in by_dimension.values():
            if len(dim_evs) < 2:
                continue
            for i, ev_a in enumerate(dim_evs):
                for ev_b in dim_evs[i + 1:]:
                    if self._are_conflicting(ev_a.evidence_text, ev_b.evidence_text):
                        ev_a.conflict_flag = True
                        ev_b.conflict_flag = True
                        conflict_count += 1

        return conflict_count

    def get_evidence_for_dimension(
        self,
        db: Session,
        use_case_id: int,
        dimension: str,
        top_k: int = 5,
    ) -> List[Evidence]:
        """Return stored evidence for a dimension, ordered by relevance."""
        return (
            db.query(Evidence)
            .filter(
                Evidence.use_case_id == use_case_id,
                Evidence.dimension == dimension,
            )
            .order_by(Evidence.relevance_score.desc())
            .limit(top_k)
            .all()
        )

    def get_all_evidence(self, db: Session, use_case_id: int) -> List[Evidence]:
        """Return all evidence for a use case."""
        return (
            db.query(Evidence)
            .filter(Evidence.use_case_id == use_case_id)
            .order_by(Evidence.dimension, Evidence.relevance_score.desc())
            .all()
        )

    def load_retriever_from_db(self, db: Session, use_case_id: int) -> None:
        """Rebuild the in-memory retrieval index from stored evidence."""
        evidences = self.get_all_evidence(db, use_case_id)
        for ev in evidences:
            if ev.id:
                retriever.add_document(ev.id, f"{ev.dimension} {ev.evidence_text}")

    def compute_evidence_confidence(self, evidence_list: List[Evidence]) -> str:
        """Map number and quality of evidence items to a confidence label."""
        if not evidence_list:
            return "INSUFFICIENT"
        high_cred = [
            e for e in evidence_list
            if e.source and e.source.credibility_level >= 4
        ]
        if len(evidence_list) >= 3 and high_cred:
            return "HIGH"
        if len(evidence_list) >= 2:
            return "MEDIUM"
        if len(evidence_list) >= 1:
            return "LOW"
        return "INSUFFICIENT"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        return [s.strip() for s in raw if len(s.strip()) > 30]

    @staticmethod
    def _find_relevant_sentences(
        sentences: List[str],
        keywords: List[str],
        max_sentences: int = 3,
    ) -> List[str]:
        scored: List[tuple] = []
        for sent in sentences:
            sl = sent.lower()
            hits = sum(1 for kw in keywords if kw.lower() in sl)
            if hits > 0:
                scored.append((hits, sent))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_sentences]]

    @staticmethod
    def _compute_relevance(text: str, keywords: List[str]) -> float:
        if not text:
            return 0.0
        tl = text.lower()
        hits = sum(1 for kw in keywords if kw.lower() in tl)
        return min(1.0, hits / max(len(keywords), 1))

    @staticmethod
    def _are_conflicting(text_a: str, text_b: str) -> bool:
        negations = {"not", "no", "never", "without", "lack", "absent", "prohibited"}
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        a_neg = bool(tokens_a & negations)
        b_neg = bool(tokens_b & negations)
        return a_neg != b_neg


evidence_service = EvidenceService()
