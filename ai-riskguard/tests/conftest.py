import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.database.session import Base, get_db
from backend.main import app, seed_risk_dimensions

# Use in-memory SQLite database with StaticPool for thread-safe test isolation
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database session for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seed_risk_dimensions(db_session=session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)



@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient fixture overriding the database dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
