from typing import Dict, List, Any


class ScoringService:
    """Deterministic scoring engine combining governance rules, evidence, and AI classifications.
    
    Prevents LLMs from arbitrarily inventing numerical risk scores.
    """

    # Configurable weights across the 10 governance dimensions
    DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
        "DATA": 1.0,
        "PRIVACY": 1.2,
        "BIAS_FAIRNESS": 1.1,
        "HUMAN_OVERSIGHT": 1.2,
        "EXPLAINABILITY": 1.0,
        "SECURITY": 1.3,
        "DECISION_IMPACT": 1.4,
        "REGULATORY_EXPOSURE": 1.3,
        "MODEL_RISK": 1.0,
        "MONITORING": 1.0,
    }

    def calculate_dimension_score(
        self,
        dimension_code: str,
        rule_findings: List[Dict[str, Any]],
        evidence_findings: List[Dict[str, Any]],
    ) -> float:
        """Calculate a deterministic score (0.0 - 100.0) for a single dimension."""
        # Baseline score calculation skeleton
        base_score = 20.0  # Default low baseline
        for finding in rule_findings:
            base_score += finding.get("impact", 0.0)
        return min(100.0, max(0.0, base_score))

    def calculate_overall_risk(
        self, dimension_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Aggregate dimension scores using weighted averages to determine overall risk level."""
        total_weighted_score = 0.0
        total_weight = 0.0

        for dim, score in dimension_scores.items():
            weight = self.DEFAULT_DIMENSION_WEIGHTS.get(dim, 1.0)
            total_weighted_score += score * weight
            total_weight += weight

        final_score = round(total_weighted_score / total_weight, 2) if total_weight > 0 else 0.0

        if final_score < 30.0:
            level = "Low"
        elif final_score < 60.0:
            level = "Medium"
        elif final_score < 80.0:
            level = "High"
        else:
            level = "Critical"

        return {
            "overall_score": final_score,
            "overall_level": level,
            "dimension_scores": dimension_scores,
        }


scoring_service = ScoringService()
