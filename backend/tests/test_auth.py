from app.core.security import get_password_hash
from app.db.models.user import User


def test_signup(client, db_session):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "test@example.com"


def test_login_success(client, db_session):
    # Setup user using actual model fields
    user = User(
        username="login@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Login User",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, db_session):
    # Setup user
    user = User(
        username="wrong@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Wrong User",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_me_endpoint(client, db_session):
    user = User(
        username="me@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Me User",
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/auth/login",
        data={"username": "me@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "me@example.com"


def test_me_endpoint_invalid_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
