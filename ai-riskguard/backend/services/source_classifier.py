"""Source Type Classifier for AI RiskGuard Research Layer.

Classifies a URL + domain + page title into one of five controlled source types
and assigns a credibility level (1–5) based entirely on structural URL/domain
heuristics — no LLM required.

Controlled source_type values:
    LAW_REGULATION      — official legislation / legal text
    REGULATORY_GUIDANCE — regulator / government agency guidance
    INDUSTRY_STANDARD   — recognised standards bodies
    VENDOR_INFORMATION  — vendor documentation
    GENERAL_WEB_CONTENT — everything else
"""
from __future__ import annotations

import re
from typing import Dict, Any
from urllib.parse import urlparse


# ─── Domain / path pattern lists ────────────────────────────────────────────

# Authoritative legal repositories (legislation, statutes)
_LAW_DOMAINS: list[str] = [
    "legislation.gov.uk",
    "eur-lex.europa.eu",
    "law.cornell.edu",
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "congress.gov",
    "legislation.govt.nz",
]

_LAW_PATH_PATTERNS: list[str] = [
    r"/regulation/\d+/",
    r"/act/\d+",
    r"/statute",
    r"/legislation/",
    r"/legal-text",
    r"/EUR-Lex",
]

# Official regulator / government-agency guidance (not statutes)
_REGULATORY_DOMAINS: list[str] = [
    # EU
    "edpb.europa.eu",
    "ec.europa.eu",
    "digital-strategy.ec.europa.eu",
    "ema.europa.eu",
    "enisa.europa.eu",
    # UK
    "ico.org.uk",
    "fca.org.uk",
    "cma.gov.uk",
    "gov.uk",
    "ofcom.org.uk",
    # US
    "ftc.gov",
    "sec.gov",
    "eeoc.gov",
    "nih.gov",
    "hhs.gov",
    "dhs.gov",
    "nist.gov",
    "whitehouse.gov",
    "bls.gov",
    "fdic.gov",
    "cfpb.gov",
    # International
    "oecd.org",
    "un.org",
    "unesco.org",
    "wto.org",
    "imf.org",
]

# Recognised standards bodies
_STANDARDS_DOMAINS: list[str] = [
    "iso.org",
    "ieee.org",
    "ietf.org",
    "w3.org",
    "ansi.org",
    "bsi.biz",
    "bsigroup.com",
    "din.de",
    "etsi.org",
    "cen.eu",
    "nist.gov",    # NIST can be regulatory or standards; handled below
]

_STANDARDS_PATH_PATTERNS: list[str] = [
    r"/standard",
    r"/iso-\d+",
    r"/ieee-\d+",
    r"/nist\.\w+",
    r"/framework",
    r"/guidelines",
    r"/sp\d+",       # NIST Special Publications e.g. /sp800
]

# Major vendor domains
_VENDOR_DOMAINS: list[str] = [
    "microsoft.com",
    "azure.microsoft.com",
    "docs.microsoft.com",
    "learn.microsoft.com",
    "google.com",
    "cloud.google.com",
    "ai.google",
    "deepmind.com",
    "aws.amazon.com",
    "docs.aws.amazon.com",
    "ibm.com",
    "research.ibm.com",
    "nvidia.com",
    "openai.com",
    "anthropic.com",
    "meta.ai",
    "ai.meta.com",
    "huggingface.co",
    "sas.com",
    "oracle.com",
    "salesforce.com",
    "dataiku.com",
]

# Credibility by source type
_CREDIBILITY_MAP: Dict[str, int] = {
    "LAW_REGULATION": 5,
    "REGULATORY_GUIDANCE": 4,
    "INDUSTRY_STANDARD": 4,
    "VENDOR_INFORMATION": 2,
    "GENERAL_WEB_CONTENT": 1,
}


class SourceClassifier:
    """Classifies a URL into a source_type and assigns credibility."""

    def classify(self, url: str, title: str = "") -> Dict[str, Any]:
        """Return classification dict with source_type, credibility_level, and reason."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")
        path = parsed.path.lower()
        title_lower = (title or "").lower()

        source_type, reason = self._classify_domain(domain, path, title_lower)
        credibility = _CREDIBILITY_MAP.get(source_type, 1)

        return {
            "source_type": source_type,
            "credibility_level": credibility,
            "classification_reason": reason,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify_domain(self, domain: str, path: str, title: str) -> tuple[str, str]:
        # 1. Check known law repositories first (highest priority)
        if self._matches_domain(domain, _LAW_DOMAINS):
            return "LAW_REGULATION", f"Domain '{domain}' is a recognised official legal/legislation repository."

        # 1b. Path patterns on .gov sites suggesting actual legislation
        if domain.endswith(".gov") or domain.endswith(".gov.uk"):
            for pat in _LAW_PATH_PATTERNS:
                if re.search(pat, path):
                    return "LAW_REGULATION", f"Government domain with legal-text path pattern ('{pat}')."

        # 2. Regulatory/government guidance
        if self._matches_domain(domain, _REGULATORY_DOMAINS):
            return "REGULATORY_GUIDANCE", f"Domain '{domain}' is a recognised regulatory or government authority."

        # Generic .gov TLD (not already matched above) → regulatory guidance
        if domain.endswith(".gov") or domain.endswith(".gov.uk") or domain.endswith(".gov.au"):
            return "REGULATORY_GUIDANCE", f"Government TLD domain ('{domain}') — treated as regulatory guidance."

        # 3. Standards bodies
        if self._matches_domain(domain, _STANDARDS_DOMAINS):
            # NIST is standards when path looks like SP, otherwise regulatory
            if "nist.gov" in domain:
                for pat in _STANDARDS_PATH_PATTERNS:
                    if re.search(pat, path):
                        return "INDUSTRY_STANDARD", f"NIST domain with standards path pattern."
                return "REGULATORY_GUIDANCE", f"NIST domain — treated as regulatory guidance."
            return "INDUSTRY_STANDARD", f"Domain '{domain}' is a recognised standards organisation."

        # 4. Vendor documentation
        if self._matches_domain(domain, _VENDOR_DOMAINS):
            return "VENDOR_INFORMATION", f"Domain '{domain}' is a known AI/technology vendor."

        # 5. Academic / research institutions (heuristic)
        if domain.endswith(".edu") or domain.endswith(".ac.uk"):
            return "INDUSTRY_STANDARD", f"Academic domain ('{domain}') — treated as peer-reviewed / industry standard."

        # 6. Default
        return "GENERAL_WEB_CONTENT", f"Domain '{domain}' not matched to a known authority category."

    @staticmethod
    def _matches_domain(domain: str, domain_list: list[str]) -> bool:
        """True if domain exactly matches or is a subdomain of any entry in domain_list."""
        for d in domain_list:
            if domain == d or domain.endswith("." + d):
                return True
        return False


# Module-level singleton
source_classifier = SourceClassifier()
