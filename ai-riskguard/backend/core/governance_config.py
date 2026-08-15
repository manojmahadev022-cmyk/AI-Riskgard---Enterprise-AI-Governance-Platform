"""Centralized Governance Configuration for AI RiskGuard.

Defines the 10 core governance dimensions, configurable weights, and risk level threshold ranges.
"""
from typing import Dict, Any, List

# The 10 Core Governance Dimensions defined by the MODUS framework
GOVERNANCE_DIMENSIONS: List[Dict[str, str]] = [
    {
        "code": "DATA",
        "name": "Data",
        "description": "Evaluates data sensitivity, dataset quality, lineage, and synthetic/unverified source risks.",
    },
    {
        "code": "PRIVACY",
        "name": "Privacy",
        "description": "Evaluates exposure of personal identifiers, sensitive records, consent, and privacy compliance.",
    },
    {
        "code": "BIAS_FAIRNESS",
        "name": "Bias/Fairness",
        "description": "Evaluates potential for disparate impact, demographic bias, and unfair treatment in individual outcomes.",
    },
    {
        "code": "HUMAN_OVERSIGHT",
        "name": "Human Oversight",
        "description": "Evaluates human control level, manual override capability, and meaningful human review.",
    },
    {
        "code": "EXPLAINABILITY",
        "name": "Explainability",
        "description": "Evaluates model transparency, interpretability of decision logic, and disclosure requirements.",
    },
    {
        "code": "SECURITY",
        "name": "Security",
        "description": "Evaluates cybersecurity attack surface, prompt injection, data poisoning, and system robustness.",
    },
    {
        "code": "DECISION_IMPACT",
        "name": "Decision Impact",
        "description": "Evaluates severity of impact on human life, health, legal rights, finances, or enterprise operations.",
    },
    {
        "code": "REGULATORY_EXPOSURE",
        "name": "Regulatory Exposure",
        "description": "Evaluates compliance obligations under EU AI Act, FTC/SEC guidance, HIPAA, and industry regulations.",
    },
    {
        "code": "MODEL_RISK",
        "name": "Model Risk",
        "description": "Evaluates hallucination probability, output unpredictability, model drift, and unverified automated actions.",
    },
    {
        "code": "MONITORING",
        "name": "Monitoring",
        "description": "Evaluates post-deployment audit logging, real-time performance tracking, and incident response readiness.",
    },
]

# Configurable Dimension Weights (Default: Equal weight = 1.0)
DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    "Data": 1.0,
    "Privacy": 1.0,
    "Bias/Fairness": 1.0,
    "Human Oversight": 1.0,
    "Explainability": 1.0,
    "Security": 1.0,
    "Decision Impact": 1.0,
    "Regulatory Exposure": 1.0,
    "Model Risk": 1.0,
    "Monitoring": 1.0,
}

# Configurable Risk Score Thresholds (Score Scale 1.00 - 5.00)
# 1.00–1.99 → LOW
# 2.00–2.99 → MODERATE
# 3.00–3.99 → HIGH
# 4.00–5.00 → VERY HIGH
RISK_THRESHOLDS: List[Dict[str, Any]] = [
    {"level": "LOW", "min_score": 1.00, "max_score": 1.99},
    {"level": "MODERATE", "min_score": 2.00, "max_score": 2.99},
    {"level": "HIGH", "min_score": 3.00, "max_score": 3.99},
    {"level": "VERY HIGH", "min_score": 4.00, "max_score": 5.00},
]


def get_risk_level(score: float) -> str:
    """Map a numerical score (1.0 - 5.0) to a risk level string based on configured thresholds."""
    clamped_score = max(1.0, min(5.0, score))
    for threshold in RISK_THRESHOLDS:
        if threshold["min_score"] <= clamped_score <= threshold["max_score"]:
            return threshold["level"]
    return "VERY HIGH" if clamped_score >= 4.0 else "LOW"
