"""Deterministic Governance Assessment Engine for AI RiskGuard.

Evaluates an AI use case across 10 core governance dimensions using dynamic characteristic inspection
without relying on LLMs for numerical scores or using hardcoded use-case shortcuts.
"""
from typing import Dict, List, Any
import re
from backend.core.governance_config import (
    DEFAULT_DIMENSION_WEIGHTS,
    get_risk_level,
)


class GovernanceAssessmentEngine:
    """Repeatable, rule-based governance evaluation engine."""

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_DIMENSION_WEIGHTS

    def evaluate_use_case(self, use_case: Any) -> Dict[str, Any]:
        """Run all 10 governance dimension evaluations for a given AI use case."""

        dimension_evaluations = [
            self.assess_data(use_case),
            self.assess_privacy(use_case),
            self.assess_bias(use_case),
            self.assess_human_oversight(use_case),
            self.assess_explainability(use_case),
            self.assess_security(use_case),
            self.assess_decision_impact(use_case),
            self.assess_regulatory_exposure(use_case),
            self.assess_model_risk(use_case),
            self.assess_monitoring(use_case),
        ]

        # Calculate weighted average overall score
        total_weighted_score = 0.0
        total_weight = 0.0

        for evaluation in dimension_evaluations:
            dim_name = evaluation["dimension"]
            score = evaluation["score"]
            weight = self.weights.get(dim_name, 1.0)

            total_weighted_score += score * weight
            total_weight += weight

        overall_score = round(total_weighted_score / total_weight, 2) if total_weight > 0 else 1.0
        risk_level = get_risk_level(overall_score)

        return {
            "overall_score": overall_score,
            "risk_level": risk_level,
            "dimensions": dimension_evaluations,
        }

    # --- Individual Governance Dimension Functions ---

    def assess_data(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 1: Data Quality & Sensitivity Assessment."""
        data_text = f"{use_case.data_used} {use_case.description}".lower()
        score = 1.0
        reasons = []

        sensitive_terms = ["pii", "ssn", "medical", "ehr", "health", "financial", "credit", "biometric", "salary", "personal", "confidential"]
        operational_terms = ["sensor", "machine", "equipment", "temperature", "vibration", "maintenance", "operating hours", "equipment status", "telemetry"]
        unstructured_terms = ["scraped", "scraping", "social media", "third-party", "unstructured", "synthetic", "raw images", "audio"]

        matched_sensitive = [t for t in sensitive_terms if t in data_text]
        matched_operational = [t for t in operational_terms if t in data_text]
        matched_unstructured = [t for t in unstructured_terms if t in data_text]

        if matched_sensitive:
            score += 2.0
            reasons.append(f"Processes sensitive information types ({', '.join(matched_sensitive[:3])})")
        elif matched_operational:
            reasons.append(
                f"Uses operational equipment data ({', '.join(matched_operational[:4])}) "
                "rather than primarily personal data"
            )
        else:
            reasons.append("Data processed consists primarily of operational or standard non-sensitive data")

        if matched_unstructured:
            score += 1.5
            reasons.append(f"Relies on complex or external data sources ({', '.join(matched_unstructured[:2])}) requiring validation")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Data",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_privacy(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 2: Privacy & Data Protection Assessment."""
        combined_text = f"{use_case.data_used} {use_case.purpose} {use_case.description}".lower()
        score = 1.0
        reasons = []

        high_privacy = ["patient", "medical history", "ehr", "ssn", "passport", "bank account", "credit card", "biometric", "dna", "location tracking"]
        moderate_privacy = ["resume", "applicant", "employee", "customer", "email", "address", "phone", "user profile", "behavioral logs"]
        operational_terms = ["sensor", "machine", "equipment", "temperature", "vibration", "operating hours", "maintenance history", "equipment status"]

        if any(term in combined_text for term in high_privacy):
            score += 3.5
            reasons.append("High privacy risk due to processing highly sensitive personal identifiers or medical/financial records")
        elif any(term in combined_text for term in moderate_privacy):
            score += 2.0
            reasons.append("Moderate privacy exposure involving individual profiles, employment data, or behavioral records")
        elif any(term in combined_text for term in operational_terms):
            reasons.append("Limited direct privacy exposure because the primary data concerns equipment, sensor telemetry, or maintenance operations")
        else:
            reasons.append("Minimal individual privacy exposure identified in dataset scope")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Privacy",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_bias(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 3: Bias & Algorithmic Fairness Assessment."""
        combined_text = f"{use_case.name} {use_case.purpose} {use_case.description} {use_case.industry}".lower()
        score = 1.0
        reasons = []

        people_decision_terms = ["rank", "ranks", "ranking", "screen", "screening", "filter", "filtering", "approve", "approval", "hire", "hiring", "recruit", "applicant", "candidate", "credit", "loan", "triage", "score", "scoring"]
        protected_terms = ["gender", "age", "race", "ethnicity", "demographic", "zip code", "background", "history"]
        operational_risk_terms = ["predictive maintenance", "equipment failure", "machine failure", "failure prediction", "machine", "equipment", "sensor", "maintenance"]

        is_people_decision = any(term in combined_text for term in people_decision_terms)
        has_demographic_risk = any(term in combined_text for term in protected_terms)

        if is_people_decision:
            score += 2.5
            reasons.append("System directly evaluates, ranks, or screens individuals for critical life opportunities")
        else:
            reasons.append("System operates primarily on non-human processes or non-evaluative tasks")

        if has_demographic_risk:
            score += 1.5
            reasons.append("Input indicators suggest potential correlation with protected demographic attributes")
        elif any(term in combined_text for term in operational_risk_terms):
            reasons.append("Bias risk is lower because the system primarily evaluates equipment or operational conditions rather than protected characteristics")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Bias/Fairness",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_human_oversight(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 4: Human Oversight & Agency Assessment."""
        oversight_text = f"{use_case.human_involvement} {use_case.description}".lower()
        score = 2.0
        reasons = []

        if any(term in oversight_text for term in ["out-of-the-loop", "fully automated", "no human", "unattended", "autonomous"]):
            score = 5.0
            reasons.append("Fully automated execution without real-time human intervention or pre-execution approval")
        elif any(term in oversight_text for term in ["on-the-loop", "monitoring", "override", "periodic review", "exception-only"]):
            score = 3.5
            reasons.append("Human-on-the-loop structure where humans monitor operations but do not manually verify every decision")
        elif any(term in oversight_text for term in ["in-the-loop", "review before", "final decision", "physician", "recruiter", "approver", "manual approval"]):
            score = 1.5
            reasons.append("Human-in-the-loop mechanism maintained where human experts make or validate the final decision")
        else:
            score = 3.0
            reasons.append(f"Specified oversight pattern ('{use_case.human_involvement}') requires further verification of override controls")

        return {
            "dimension": "Human Oversight",
            "score": round(score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_explainability(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 5: Transparency & Explainability Assessment."""
        combined_text = f"{use_case.description} {use_case.purpose} {use_case.name}".lower()
        score = 2.0
        reasons = []

        complex_ai = ["llm", "deep learning", "neural network", "transformer", "nlp", "black-box", "genai", "generative"]
        high_transparency_need = ["denial", "rejection", "diagnosis", "credit", "loan", "hiring", "legal", "compliance", "maintenance", "failure prediction"]

        if any(term in combined_text for term in complex_ai):
            score += 2.0
            reasons.append("Uses complex or generative AI models with inherent interpretability challenges")
        else:
            reasons.append("Standard algorithmic architecture with manageable interpretability requirements")

        if any(term in combined_text for term in high_transparency_need):
            score += 1.0
            reasons.append("High demand for explainability due to regulatory disclosure requirements for adverse decisions")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Explainability",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_security(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 6: Cybersecurity & Robustness Assessment."""
        combined_text = f"{use_case.data_used} {use_case.description} {use_case.purpose}".lower()
        score = 1.5
        reasons = []

        public_exposure = ["user input", "web interface", "public", "customer-facing", "chatbot", "api", "integration"]
        critical_access = ["database", "financial records", "credentials", "ehr", "medical history", "payment", "machine controls", "industrial control", "sensor network", "equipment network"]

        if any(term in combined_text for term in public_exposure):
            score += 1.5
            reasons.append("Exposed to external or user-generated inputs susceptible to prompt injection or manipulation")

        if any(term in combined_text for term in critical_access):
            score += 1.5
            reasons.append("Integrated with sensitive data stores requiring robust data poisoning and security controls")
        else:
            reasons.append("Standard internal cybersecurity perimeter boundaries apply")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Security",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_decision_impact(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 7: Decision Impact & Harm Level Assessment."""
        combined_text = f"{use_case.purpose} {use_case.description} {use_case.industry}".lower()
        score = 1.0
        reasons = []

        critical_impact = ["healthcare", "patient", "triage", "medical", "treatment", "diagnosis", "loan", "credit", "hiring", "recruitment", "employment", "criminal"]
        operational_critical = ["predictive maintenance", "equipment failure", "machine failure", "failure prediction", "industrial safety", "production failure", "critical equipment", "infrastructure"]
        moderate_impact = ["customer service", "pricing", "claims", "marketing", "content", "inventory"]

        if any(term in combined_text for term in critical_impact):
            score += 3.5
            reasons.append("Direct impact on critical human outcomes such as health, financial livelihood, legal rights, or employment")
        elif any(term in combined_text for term in operational_critical):
            score += 2.5
            reasons.append("Meaningful operational and safety impact because incorrect predictions can cause equipment downtime, maintenance failures, or industrial risk")
        elif any(term in combined_text for term in moderate_impact):
            score += 2.0
            reasons.append("Moderate operational or commercial decision impact on organization or customers")
        else:
            reasons.append("Low direct impact on critical individual rights or core safety infrastructure")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Decision Impact",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_regulatory_exposure(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 8: Regulatory Exposure Assessment."""
        combined_text = f"{use_case.industry} {use_case.purpose} {use_case.description} {use_case.data_used}".lower()
        score = 1.0
        reasons = []

        heavy_regulated = ["healthcare", "medical", "financial", "banking", "insurance", "human resources", "hr", "recruitment", "hiring", "credit", "legal"]
        operational_regulated = ["industrial safety", "manufacturing safety", "critical infrastructure", "machine safety", "workplace safety", "industrial control"]
        compliance_regimes = ["hipaa", "gdpr", "eeoc", "sec", "ftc", "fcra", "eu ai act"]

        matched_regimes = [r.upper() for r in compliance_regimes if r in combined_text]

        if any(term in combined_text for term in heavy_regulated):
            score += 3.0
            reasons.append(f"Operates within a heavily regulated domain ({use_case.industry}) subject to statutory scrutiny")
        elif any(term in combined_text for term in operational_regulated):
            score += 2.0
            reasons.append("May be subject to industrial, workplace, or operational safety requirements depending on deployment context")

        if matched_regimes:
            score += 1.0
            reasons.append(f"Specific compliance frameworks triggered ({', '.join(matched_regimes)})")
        else:
            reasons.append("Subject to standard baseline consumer protection and enterprise compliance standards")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Regulatory Exposure",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_model_risk(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 9: Model Risk & Hallucination Assessment."""
        combined_text = f"{use_case.description} {use_case.purpose}".lower()
        score = 2.0
        reasons = []

        gen_ai_terms = ["llm", "generative", "nlp", "chat", "summarize", "generate", "text generation"]
        predictive_terms = ["predict", "prediction", "forecast", "failure", "maintenance", "sensor", "machine learning"]
        unverified_terms = ["automated", "direct output", "real-time action", "automatic"]

        if any(term in combined_text for term in gen_ai_terms):
            score += 2.0
            reasons.append("Generative or probabilistic language model components carry inherent hallucination and inaccuracy risks")
        elif any(term in combined_text for term in predictive_terms):
            score += 1.0
            reasons.append("Predictive modeling introduces risks from false positives, false negatives, sensor quality, model drift, and degradation")
        else:
            reasons.append("Model risk bounded by deterministic or structured machine learning mechanisms")

        if any(term in combined_text for term in unverified_terms):
            score += 1.0
            reasons.append("Unverified output generation could lead to downstream operational errors if unmonitored")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Model Risk",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }

    def assess_monitoring(self, use_case: Any) -> Dict[str, Any]:
        """Dimension 10: Continuous Monitoring & Auditability Assessment."""
        combined_text = f"{use_case.description} {use_case.human_involvement}".lower()
        score = 2.5
        reasons = []

        monitoring_terms = ["audit", "logging", "monitor", "tracking", "dashboard", "metrics", "review", "sensor", "equipment status", "drift", "maintenance"]

        if any(term in combined_text for term in monitoring_terms):
            score -= 1.0
            reasons.append("Explicit logging or monitoring controls indicated in process description")
        else:
            score += 1.0
            reasons.append("Lack of explicit post-deployment audit logging or drift tracking mechanisms detailed")

        final_score = min(5.0, max(1.0, score))
        return {
            "dimension": "Monitoring",
            "score": round(final_score, 1),
            "reasoning": ". ".join(reasons) + ".",
        }


governance_engine = GovernanceAssessmentEngine()