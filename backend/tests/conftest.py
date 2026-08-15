import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Environment must be set BEFORE any app imports so pydantic Settings loads
# ---------------------------------------------------------------------------
os.environ["NYRA_ENV"] = "test"
os.environ["JWT_SECRET"] = "dummy_secret_for_tests"
os.environ["GEMINI_API_KEY"] = "dummy_gemini_key"
os.environ["GOOGLE_CLIENT_ID"] = "dummy_google_id"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Import app modules AFTER env vars are set
# ---------------------------------------------------------------------------
from app.core.rate_limit import limiter  # noqa: E402
from app.db.database import Base, get_db  # noqa: E402
from app.db.models import advanced, chat, document, user  # noqa: F401, E402
from app.main import app  # noqa: E402

# Disable rate limiting for tests
limiter.enabled = False


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the SQLite test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except PermissionError:
            pass


@pytest.fixture
def db_session():
    """Provide a transactional scope around each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a TestClient that uses the test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
