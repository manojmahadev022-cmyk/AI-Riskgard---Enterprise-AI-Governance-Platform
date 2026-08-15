"""Research Service for AI RiskGuard.

Orchestrates the full research pipeline:
  1. Generate dimension-targeted search queries from use case fields
  2. Search public web (DuckDuckGo — free, no API key)
  3. Fetch and clean page content
  4. Filter sources for use-case relevance
  5. Classify source type
  6. Deduplicate by URL / content hash
  7. Store Source records
  8. Extract evidence sentences
  9. Detect conflicts
 10. Return research status

Important:
- Use-case context is derived dynamically from the AIUseCase fields.
- Irrelevant pages are rejected before evidence extraction.
- Cached sources are also checked for relevance before reuse.
- Governance dimension vocabulary is used only to validate dimension relevance.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.models import AIUseCase, ResearchQuery, Source, Evidence
from backend.services.source_classifier import source_classifier
from backend.services.evidence_service import evidence_service

logger = logging.getLogger(__name__)


DIMENSION_QUERY_SUFFIXES: Dict[str, List[str]] = {
    "Data": ["data governance requirements", "data quality AI"],
    "Privacy": ["privacy data protection AI requirements", "GDPR AI compliance"],
    "Bias/Fairness": ["bias fairness AI governance", "algorithmic fairness requirements"],
    "Human Oversight": ["human oversight AI regulation", "AI human control requirements"],
    "Explainability": ["explainability transparency AI regulation", "AI decision explanation"],
    "Security": ["AI security cybersecurity risks", "AI model security requirements"],
    "Decision Impact": ["AI decision impact assessment", "AI consequential decisions governance"],
    "Regulatory Exposure": ["AI regulatory compliance", "AI Act regulation requirements"],
    "Model Risk": ["AI model risk management", "AI model validation requirements"],
    "Monitoring": ["AI monitoring post-deployment", "AI audit logging requirements"],
}


# These terms describe the governance dimension itself. They are NOT
# application-specific and are used to stop clearly unrelated pages from
# being treated as evidence for a dimension.
DIMENSION_TERMS: Dict[str, Set[str]] = {
    "Data": {
        "data", "dataset", "datasets", "information", "records",
        "quality", "training", "data-governance",
    },
    "Privacy": {
        "privacy", "personal", "pii", "gdpr", "consent",
        "protection", "data-protection", "personal-data",
    },
    "Bias/Fairness": {
        "bias", "fairness", "discrimination", "discriminatory",
        "equity", "protected", "demographic", "fair",
    },
    "Human Oversight": {
        "human", "oversight", "review", "reviewer", "supervision",
        "intervention", "approval", "accountability", "human-in-the-loop",
    },
    "Explainability": {
        "explainability", "explanation", "transparency", "interpretable",
        "interpretability", "black-box", "reasoning",
    },
    "Security": {
        "security", "cybersecurity", "encryption", "encrypted",
        "access", "authentication", "authorization", "secure",
        "vulnerability",
    },
    "Decision Impact": {
        "decision", "impact", "outcome", "consequence", "critical",
        "employment", "health", "financial", "rights",
    },
    "Regulatory Exposure": {
        "regulation", "regulatory", "compliance", "law", "legal",
        "act", "gdpr", "requirement", "statutory",
    },
    "Model Risk": {
        "model", "validation", "performance", "accuracy", "drift",
        "robustness", "testing", "risk", "machine-learning",
    },
    "Monitoring": {
        "monitoring", "monitor", "audit", "logging", "drift",
        "post-deployment", "incident", "review", "audit-log",
    },
}


class ResearchService:
    """Orchestrates the full research and evidence pipeline for a use case."""

    def run_research(self, db: Session, use_case_id: int) -> Dict[str, Any]:
        """Run full research pipeline. Failures are captured in status."""
        use_case = (
            db.query(AIUseCase)
            .filter(AIUseCase.id == use_case_id)
            .first()
        )

        if not use_case:
            return self._empty_status(use_case_id, error="Use case not found")

        status: Dict[str, Any] = {
            "use_case_id": use_case_id,
            "queries_generated": 0,
            "sources_found": 0,
            "sources_fetched": 0,
            "sources_cached": 0,
            "sources_rejected": 0,
            "sources_failed": 0,
            "evidence_extracted": 0,
            "dimensions_supported": 0,
            "conflicts_detected": 0,
        }

        # ------------------------------------------------------------------
        # Step 1 — Generate research queries
        # ------------------------------------------------------------------
        queries = self.generate_queries(use_case)
        status["queries_generated"] = len(queries)

        query_records: Dict[str, ResearchQuery] = {}

        for dimension, query_text in queries.items():
            rq = ResearchQuery(
                use_case_id=use_case_id,
                query_text=query_text,
                dimension=dimension,
            )
            db.add(rq)
            query_records[dimension] = rq

        db.commit()

        for rq in query_records.values():
            db.refresh(rq)

        # ------------------------------------------------------------------
        # Step 2 — Search and deduplicate URLs
        # ------------------------------------------------------------------
        all_results: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        for dimension, query_text in queries.items():
            results = self._search(query_text)

            for result in results:
                raw_url = result.get("href") or result.get("url") or ""
                url = self._normalize_url(raw_url)

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                result["_dimension"] = dimension
                result["_query_text"] = query_text
                result["_raw_url"] = raw_url
                all_results.append(result)

            time.sleep(getattr(settings, "RESEARCH_REQUEST_DELAY", 0))

        status["sources_found"] = len(all_results)

        # ------------------------------------------------------------------
        # Step 3 — Fetch, filter, classify, deduplicate and store sources
        # ------------------------------------------------------------------
        stored_sources: List[Source] = []
        processed_sources = 0

        max_sources = getattr(settings, "RESEARCH_MAX_SOURCES", 20)

        # Build context once. This is derived from the actual use case.
        use_case_tokens = self._build_use_case_tokens(use_case)

        for result in all_results:
            if processed_sources >= max_sources:
                break

            url = self._normalize_url(
                result.get("href") or result.get("url") or ""
            )

            if not url or not url.startswith(("http://", "https://")):
                continue

            dimension = result.get("_dimension", "")
            title_hint = (result.get("title") or "").strip()

            # --------------------------------------------------------------
            # Reuse cached source only if the cached content is relevant.
            # The old implementation reused every cached URL, which allowed
            # previously stored irrelevant pages to enter new assessments.
            # --------------------------------------------------------------
            existing = db.query(Source).filter(Source.url == url).first()

            if existing:
                existing_text = (
                    f"{existing.title or ''} "
                    f"{existing.raw_content or ''}"
                )

                if self._is_relevant_source(
                    text=existing_text,
                    use_case_tokens=use_case_tokens,
                    dimension=dimension,
                ):
                    stored_sources.append(existing)
                    processed_sources += 1
                    status["sources_cached"] += 1
                else:
                    logger.info(
                        "Skipping cached irrelevant source: %s",
                        url,
                    )

                continue

            # --------------------------------------------------------------
            # Fetch page
            # --------------------------------------------------------------
            fetched = self._fetch_and_clean(url)

            if fetched is None:
                status["sources_failed"] += 1
                continue

            raw_content, page_title = fetched

            if not raw_content or len(raw_content.strip()) < 100:
                status["sources_failed"] += 1
                continue

            # --------------------------------------------------------------
            # Source-level relevance filtering
            # --------------------------------------------------------------
            source_text = f"{page_title or title_hint} {raw_content}"

            relevance = self._source_relevance_score(
                text=source_text,
                use_case_tokens=use_case_tokens,
                dimension=dimension,
            )

            min_relevance = float(
                getattr(settings, "RESEARCH_MIN_SOURCE_RELEVANCE", 0.20)
            )

            if relevance < min_relevance:
                status["sources_rejected"] += 1
                logger.info(
                    "Rejected irrelevant source %.3f < %.3f: %s",
                    relevance,
                    min_relevance,
                    url,
                )
                continue

            content_hash = hashlib.sha256(
                self._normalize_text(raw_content).encode("utf-8")
            ).hexdigest()

            # --------------------------------------------------------------
            # Duplicate content check
            # --------------------------------------------------------------
            dup = (
                db.query(Source)
                .filter(Source.content_hash == content_hash)
                .first()
            )

            if dup:
                if self._is_relevant_source(
                    text=f"{dup.title or ''} {dup.raw_content or ''}",
                    use_case_tokens=use_case_tokens,
                    dimension=dimension,
                ):
                    stored_sources.append(dup)
                    processed_sources += 1
                continue

            # --------------------------------------------------------------
            # Classify source
            # --------------------------------------------------------------
            classification = source_classifier.classify(
                url,
                page_title or title_hint,
            )

            source = Source(
                url=url,
                title=(page_title or title_hint or "Unknown")[:500],
                publisher=self._extract_publisher(url),
                source_type=classification["source_type"],
                classification_reason=classification["classification_reason"],
                credibility_level=classification["credibility_level"],
                content_hash=content_hash,
                raw_content=raw_content[
                    :getattr(settings, "RESEARCH_CONTENT_LIMIT", 100_000)
                ],
            )

            db.add(source)
            db.flush()

            stored_sources.append(source)
            processed_sources += 1
            status["sources_fetched"] += 1

        db.commit()

        # ------------------------------------------------------------------
        # Step 4 — Extract evidence
        # ------------------------------------------------------------------
        total_evidence = 0

        for source in stored_sources:
            try:
                evidence_items = evidence_service.extract_evidence_from_source(
                    db=db,
                    source=source,
                    use_case_id=use_case_id,
                    research_query_id=None,
                )
                total_evidence += len(evidence_items)
            except Exception as exc:
                logger.exception(
                    "Evidence extraction failed for source %s: %s",
                    getattr(source, "id", None),
                    exc,
                )

        db.commit()

        # ------------------------------------------------------------------
        # Step 5 — Conflict detection
        #
        # Conflict semantics are owned by evidence_service. This service
        # only orchestrates the call.
        # ------------------------------------------------------------------
        try:
            conflicts = evidence_service.detect_conflicts(db, use_case_id)
        except Exception as exc:
            logger.exception("Conflict detection failed: %s", exc)
            conflicts = 0

        db.commit()

        # ------------------------------------------------------------------
        # Step 6 — Count dimensions with evidence
        # ------------------------------------------------------------------
        dimensions_with_evidence = (
            db.query(Evidence.dimension)
            .filter(Evidence.use_case_id == use_case_id)
            .distinct()
            .count()
        )

        status["evidence_extracted"] = (
            db.query(Evidence)
            .filter(Evidence.use_case_id == use_case_id)
            .count()
        )

        status["dimensions_supported"] = dimensions_with_evidence
        status["conflicts_detected"] = conflicts

        return status

    # ======================================================================
    # Query generation
    # ======================================================================

    def generate_queries(self, use_case: AIUseCase) -> Dict[str, str]:
        """Generate one search query per governance dimension.

        All application-specific context comes from the actual use-case
        fields; governance dimension terms come from the fixed dimension
        vocabulary above.
        """
        context_parts: List[str] = []

        if use_case.name:
            context_parts.append(use_case.name)

        if use_case.industry:
            industry = use_case.industry.strip()
            if industry and industry.lower() not in use_case.name.lower():
                context_parts.append(industry)

        for field_name in (
            "description",
            "purpose",
            "data_used",
            "human_involvement",
        ):
            value = getattr(use_case, field_name, None)
            if value:
                key_terms = self._extract_key_nouns(value, max_words=4)
                if key_terms:
                    context_parts.append(key_terms)

        context = " ".join(context_parts).strip()

        queries: Dict[str, str] = {}

        for dimension, suffixes in DIMENSION_QUERY_SUFFIXES.items():
            queries[dimension] = f"{context} {suffixes[0]}".strip()

        return queries

    # ======================================================================
    # Search
    # ======================================================================

    def _search(
        self,
        query: str,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """Search DuckDuckGo. Returns [] on failure."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                return list(
                    ddgs.text(
                        query,
                        max_results=max_results,
                    )
                )

        except Exception as exc:
            logger.warning(
                "Search failed for '%s': %s",
                query,
                exc,
            )
            return []

    # ======================================================================
    # Fetch and clean
    # ======================================================================

    def _fetch_and_clean(
        self,
        url: str,
    ) -> Optional[Tuple[str, str]]:
        """Fetch URL and return (cleaned_text, page_title)."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; AIRiskGuard/1.0; "
                    "+research)"
                )
            }

            with httpx.Client(
                timeout=getattr(
                    settings,
                    "RESEARCH_FETCH_TIMEOUT",
                    15,
                ),
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)

            if response.status_code != 200:
                return None

            content_type = response.headers.get(
                "content-type",
                "",
            ).lower()

            if (
                "text/html" not in content_type
                and "text/plain" not in content_type
            ):
                return None

            soup = BeautifulSoup(response.text, "lxml")

            for tag in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "form",
                    "noscript",
                    "iframe",
                ]
            ):
                tag.decompose()

            title_tag = soup.find("title")
            page_title = (
                title_tag.get_text(" ", strip=True)
                if title_tag
                else ""
            )

            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("body")
            )

            text = (
                (main_content or soup)
                .get_text(separator=" ", strip=True)
            )

            text = self._normalize_text(text)

            limit = getattr(
                settings,
                "RESEARCH_CONTENT_LIMIT",
                100_000,
            )

            return (
                text[:limit],
                page_title,
            )

        except httpx.TimeoutException:
            logger.debug("Timeout fetching %s", url)
            return None

        except Exception as exc:
            logger.debug(
                "Fetch error for %s: %s",
                url,
                exc,
            )
            return None

    # ======================================================================
    # Relevance filtering
    # ======================================================================

    @classmethod
    def _is_relevant_source(
        cls,
        text: str,
        use_case_tokens: Set[str],
        dimension: str,
    ) -> bool:
        """Return True only when a page has enough use-case + dimension signal."""
        return (
            cls._source_relevance_score(
                text=text,
                use_case_tokens=use_case_tokens,
                dimension=dimension,
            )
            >= float(
                getattr(
                    settings,
                    "RESEARCH_MIN_SOURCE_RELEVANCE",
                    0.20,
                )
            )
        )

    @classmethod
    def _source_relevance_score(
        cls,
        text: str,
        use_case_tokens: Set[str],
        dimension: str,
    ) -> float:
        """Calculate a conservative lexical source relevance score.

        This intentionally does not claim semantic/LLM-level understanding.
        It is a safety filter to reject obviously unrelated pages before
        evidence extraction.
        """
        if not text:
            return 0.0

        normalized = cls._normalize_text(text)
        words = set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", normalized))

        if not words:
            return 0.0

        context_hits = len(words.intersection(use_case_tokens))
        context_coverage = min(
            context_hits / max(len(use_case_tokens), 1),
            1.0,
        )

        dimension_terms = DIMENSION_TERMS.get(
            dimension,
            set(),
        )

        dimension_hits = len(words.intersection(dimension_terms))
        dimension_signal = min(
            dimension_hits / 3.0,
            1.0,
        )

        # A source needs both application context and governance context.
        # The score is intentionally conservative.
        score = (
            0.65 * context_coverage
            + 0.35 * dimension_signal
        )

        return round(score, 3)

    @classmethod
    def _build_use_case_tokens(
        cls,
        use_case: AIUseCase,
    ) -> Set[str]:
        """Build application-specific tokens from the use-case record."""
        values: List[str] = []

        for field_name in (
            "name",
            "description",
            "industry",
            "purpose",
            "data_used",
            "human_involvement",
        ):
            value = getattr(use_case, field_name, None)
            if value:
                values.append(str(value))

        combined = cls._normalize_text(" ".join(values))

        raw_words = re.findall(
            r"[a-z0-9][a-z0-9_-]{2,}",
            combined,
        )

        stop_words = {
            "the", "and", "for", "with", "from", "that",
            "this", "into", "using", "used", "system",
            "human", "final", "decision", "improve",
            "while", "based", "data", "information",
            "results", "records", "process", "processes",
            "ai", "artificial", "intelligence",
        }

        tokens = {
            word
            for word in raw_words
            if word not in stop_words
        }

        # Keep the most useful application-specific tokens.
        return tokens

    # ======================================================================
    # Text helpers
    # ======================================================================

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text or ""
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URLs so trivial URL differences don't defeat dedup."""
        if not url:
            return ""

        try:
            parsed = urlparse(url.strip())

            if parsed.scheme not in {"http", "https"}:
                return ""

            # Drop fragments because they do not identify a separate page.
            normalized = parsed._replace(
                fragment="",
            )

            return urlunparse(normalized)

        except Exception:
            return url.strip()

    @staticmethod
    def _extract_publisher(url: str) -> Optional[str]:
        try:
            domain = (
                urlparse(url)
                .netloc
                .lower()
                .lstrip("www.")
            )

            parts = domain.split(".")

            return (
                parts[-2].upper()
                if len(parts) >= 2
                else domain.upper()
            )

        except Exception:
            return None

    @staticmethod
    def _extract_key_nouns(
        text: str,
        max_words: int = 3,
    ) -> str:
        if not text:
            return ""

        stop_words = {
            "the", "a", "an", "and", "or", "but",
            "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "is", "are",
            "was", "be", "will", "that", "this",
            "it", "its", "while", "into", "using",
        }

        words = [
            w.strip(".,;:!?\"'()[]{}")
            for w in text.split()
            if len(w) > 3
            and w.lower() not in stop_words
        ]

        return " ".join(words[:max_words])

    @staticmethod
    def _empty_status(
        use_case_id: int,
        error: str = "",
    ) -> Dict[str, Any]:
        return {
            "use_case_id": use_case_id,
            "queries_generated": 0,
            "sources_found": 0,
            "sources_fetched": 0,
            "sources_cached": 0,
            "sources_rejected": 0,
            "sources_failed": 0,
            "evidence_extracted": 0,
            "dimensions_supported": 0,
            "conflicts_detected": 0,
            "error": error,
        }


research_service = ResearchService()
