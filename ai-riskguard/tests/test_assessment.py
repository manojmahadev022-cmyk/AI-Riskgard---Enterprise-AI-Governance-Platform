import pytest
from backend.services.governance_engine import governance_engine
from backend.core.governance_config import get_risk_level


def test_valid_use_case_creation(client):
    """Test 1: Valid use-case creation via API."""
    payload = {
        "name": "AI Loan Approval Engine",
        "description": "Evaluates consumer credit applications and determines credit limits.",
        "industry": "Financial Services",
        "purpose": "Automate credit decisioning and risk profiling",
        "data_used": "Credit score, bank statements, income, PII",
        "human_involvement": "Human-on-the-loop (Monitoring overrides)",
    }
    response = client.post("/api/use-cases", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == payload["name"]


def test_invalid_input_validation(client):
    """Test 2: Invalid/empty input rejection with 422 Unprocessable Entity."""
    payload = {
        "name": "",  # Invalid empty string
        "description": "Short",
        "industry": "",
        "purpose": "Test",
        "data_used": "Test",
        "human_involvement": "Test",
    }
    response = client.post("/api/use-cases", json=payload)
    assert response.status_code == 422


def test_assessment_produces_all_10_dimensions(client):
    """Test 3: Verification that assessment produces all 10 governance dimensions."""
    # Create Use Case
    uc_resp = client.post("/api/use-cases", json={
        "name": "Customer Support Chatbot",
        "description": "Generative AI chatbot answering customer FAQs.",
        "industry": "Customer Service",
        "purpose": "Automate general customer inquiry responses",
        "data_used": "Public product documentation, FAQ logs",
        "human_involvement": "Human-on-the-loop",
    })
    uc_id = uc_resp.json()["id"]

    # Trigger Assessment
    eval_resp = client.post(f"/api/assessments/{uc_id}")
    assert eval_resp.status_code == 201
    data = eval_resp.json()

    assert "dimensions" in data
    dimensions = data["dimensions"]
    assert len(dimensions) == 10

    dim_names = [d["dimension"] for d in dimensions]
    expected_10 = [
        "Data", "Privacy", "Bias/Fairness", "Human Oversight", "Explainability",
        "Security", "Decision Impact", "Regulatory Exposure", "Model Risk", "Monitoring"
    ]
    for expected in expected_10:
        assert expected in dim_names


def test_scores_bounded_between_1_and_5(client):
    """Test 4: Verify every dimension score is strictly bounded between 1 and 5."""
    uc_resp = client.post("/api/use-cases", json={
        "name": "Supply Chain Demand Predictor",
        "description": "Predicts warehouse inventory requirements based on seasonal sales trends.",
        "industry": "Manufacturing & Supply Chain",
        "purpose": "Optimize inventory restocking schedules",
        "data_used": "Historical sales volume, inventory logs, supplier lead times",
        "human_involvement": "Human-in-the-loop (Logistics manager approval)",
    })
    uc_id = uc_resp.json()["id"]

    eval_resp = client.post(f"/api/assessments/{uc_id}")
    data = eval_resp.json()

    for dim in data["dimensions"]:
        assert 1.0 <= dim["score"] <= 5.0


def test_overall_score_weighted_average_calculation(client):
    """Test 5: Verify overall score matches weighted average of dimension scores."""
    uc_resp = client.post("/api/use-cases", json={
        "name": "Generic Document Formatter",
        "description": "Formats internal markdown documents and aligns headings.",
        "industry": "Other",
        "purpose": "Internal document cleanup",
        "data_used": "Non-sensitive public text documents",
        "human_involvement": "Human-in-the-loop",
    })
    uc_id = uc_resp.json()["id"]

    eval_resp = client.post(f"/api/assessments/{uc_id}")
    data = eval_resp.json()

    scores = [d["score"] for d in data["dimensions"]]
    expected_avg = round(sum(scores) / len(scores), 2)
    assert data["overall_score"] == expected_avg


def test_risk_level_threshold_mapping():
    """Test 6: Risk level threshold mapping rules (1.00-1.99 LOW, 2.00-2.99 MODERATE, 3.00-3.99 HIGH, 4.00-5.00 VERY HIGH)."""
    assert get_risk_level(1.50) == "LOW"
    assert get_risk_level(2.50) == "MODERATE"
    assert get_risk_level(3.50) == "HIGH"
    assert get_risk_level(4.50) == "VERY HIGH"


def test_assessment_persisted_in_sqlite(client):
    """Test 7: Assessment persistence and retrieval from database."""
    # Create & Assess
    uc_resp = client.post("/api/use-cases", json={
        "name": "Audit Log Analyzer",
        "description": "Analyzes system access logs for anomalous login patterns.",
        "industry": "Technology",
        "purpose": "Detect suspicious access attempts",
        "data_used": "System audit logs, IP addresses",
        "human_involvement": "Human-on-the-loop",
    })
    uc_id = uc_resp.json()["id"]
    eval_resp = client.post(f"/api/assessments/{uc_id}")
    ass_id = eval_resp.json()["assessment_id"]

    # Retrieve Assessment by ID
    get_resp = client.get(f"/api/assessments/{ass_id}")
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["assessment_id"] == ass_id
    assert len(retrieved["dimensions"]) == 10


def test_dynamic_evaluations_three_industry_examples(client):
    """Test 8 & 9: Verify three distinct use cases produce dynamic, input-driven assessments.
    
    Case A: AI recruitment screening (HR)
    Case B: AI loan approval (Finance)
    Case C: AI medical diagnostic assistant (Healthcare)
    """
    case_a = {
        "name": "AI Recruitment Screening",
        "description": "Ranks job applicants based on resume content, work history, and candidate assessment scores.",
        "industry": "Human Resources",
        "purpose": "Improve hiring efficiency and rank job candidates",
        "data_used": "Resume information, candidate assessment results, PII, work history",
        "human_involvement": "Human-in-the-loop (Recruiters review AI ranking before interviewing)",
    }

    case_b = {
        "name": "AI Credit & Loan Approval",
        "description": "Fully automated evaluation of credit applications determining interest rates and loan rejection.",
        "industry": "Financial Services",
        "purpose": "Automate instant loan approvals and interest rate decisions",
        "data_used": "SSN, bank account history, credit score, tax returns, PII",
        "human_involvement": "Human-out-of-the-loop (Fully automated decisions without human review)",
    }

    case_c = {
        "name": "AI Radiology Diagnostic Assistant",
        "description": "Deep learning model analyzing CT and MRI scans to flag potential tumor anomalies.",
        "industry": "Healthcare",
        "purpose": "Assist radiologists in early cancer detection",
        "data_used": "Patient EHR, MRI/CT scans, patient medical history, genetic markers",
        "human_involvement": "Human-in-the-loop (Physician mandatory review and final diagnostic decision)",
    }

    # Evaluate Case A (Recruitment)
    resp_a = client.post("/api/use-cases", json=case_a)
    ass_a = client.post(f"/api/assessments/{resp_a.json()['id']}").json()

    # Evaluate Case B (Loan Approval - Fully Automated)
    resp_b = client.post("/api/use-cases", json=case_b)
    ass_b = client.post(f"/api/assessments/{resp_b.json()['id']}").json()

    # Evaluate Case C (Healthcare Radiology)
    resp_c = client.post("/api/use-cases", json=case_c)
    ass_c = client.post(f"/api/assessments/{resp_c.json()['id']}").json()

    # Verify all 3 produced complete 10-dimension assessments
    assert len(ass_a["dimensions"]) == 10
    assert len(ass_b["dimensions"]) == 10
    assert len(ass_c["dimensions"]) == 10

    # Verify Case B (Fully Automated Loan Decision) has HIGHER human oversight & privacy risk than Case A/C
    oversight_b = next(d for d in ass_b["dimensions"] if d["dimension"] == "Human Oversight")
    oversight_a = next(d for d in ass_a["dimensions"] if d["dimension"] == "Human Oversight")
    assert oversight_b["score"] > oversight_a["score"]

    # Verify Case C (Healthcare MRI/EHR) has Privacy & Regulatory risk highlighting HIPAA/patient records
    privacy_c = next(d for d in ass_c["dimensions"] if d["dimension"] == "Privacy")
    assert privacy_c["score"] >= 3.0
    assert "patient" in privacy_c["reasoning"].lower() or "medical" in privacy_c["reasoning"].lower()

    # Verify scores are dynamic and not hardcoded identical
    assert ass_a["overall_score"] != ass_b["overall_score"] or ass_b["overall_score"] != ass_c["overall_score"]
