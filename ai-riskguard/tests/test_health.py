def test_health_check_endpoint(client):
    """Test the /api/v1/health API endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["database"] == "connected"
    assert "version" in data


def test_root_endpoint(client):
    """Test root welcome endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI RiskGuard"
    assert "docs" in data
