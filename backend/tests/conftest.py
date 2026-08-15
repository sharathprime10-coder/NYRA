import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create an isolated sqlite database for testing
os.environ["NYRA_ENV"] = "test"
os.environ["JWT_SECRET"] = "dummy_secret_for_tests"
os.environ["GEMINI_API_KEY"] = "dummy_gemini_key"
os.environ["GOOGLE_CLIENT_ID"] = "dummy_google_id"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import after setting env vars so config loads correctly
from app.db.database import Base, get_db
from app.db.models.chat import *
from app.db.models.document import *
from app.db.models.user import *
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def db_session():
    # Start a nested transaction
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
