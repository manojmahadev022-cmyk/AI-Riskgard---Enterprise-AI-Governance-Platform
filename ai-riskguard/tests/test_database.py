from backend.models.models import AIUseCase, RiskDimension


def test_db_create_and_read_use_case(client, db_session):
    """Test creating and retrieving an AI Use Case in the database."""
    payload = {
        "name": "Clinical Trial Matching System",
        "description": "Matching oncology patients with eligible clinical trials using NLP.",
        "industry": "Healthcare",
        "purpose": "Accelerate clinical trial enrollment",
        "data_used": "Patient EHR records, genetic markers",
        "human_involvement": "Human-in-the-loop (Physician final decision)",
    }

    # Test API creation
    response = client.post("/api/v1/use-cases", json=payload)
    assert response.status_code == 201
    created_data = response.json()
    assert created_data["id"] is not None
    assert created_data["name"] == payload["name"]

    # Test Direct DB Query
    uc = db_session.query(AIUseCase).filter(AIUseCase.id == created_data["id"]).first()
    assert uc is not None
    assert uc.industry == "Healthcare"

    # Test API Listing
    list_response = client.get("/api/v1/use-cases")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) == 1
    assert list_data[0]["id"] == created_data["id"]


def test_seed_risk_dimensions(db_session):
    """Test that the 10 core governance risk dimensions are properly seeded."""
    dimensions = db_session.query(RiskDimension).all()
    assert len(dimensions) == 10
    codes = [d.code for d in dimensions]
    assert "DATA" in codes
    assert "PRIVACY" in codes
    assert "REGULATORY_EXPOSURE" in codes
