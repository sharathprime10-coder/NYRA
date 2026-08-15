from app.db.models.user import User
from app.core.security import get_password_hash

def test_signup(client, db_session):
    response = client.post("/api/auth/signup", json={"email": "test@example.com", "password": "password123", "name": "Test User"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    
    # Verify in DB
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert user.name == "Test User"

def test_login_success(client, db_session):
    # Setup user
    user = User(email="login@example.com", hashed_password=get_password_hash("password123"), name="Login User")
    db_session.add(user)
    db_session.commit()
    
    response = client.post("/api/auth/login", data={"username": "login@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, db_session):
    # Setup user
    user = User(email="wrong@example.com", hashed_password=get_password_hash("password123"), name="Wrong User")
    db_session.add(user)
    db_session.commit()
    
    response = client.post("/api/auth/login", data={"username": "wrong@example.com", "password": "wrongpassword"})
    assert response.status_code == 401

def test_me_endpoint(client, db_session):
    user = User(email="me@example.com", hashed_password=get_password_hash("password123"), name="Me User")
    db_session.add(user)
    db_session.commit()
    
    login_response = client.post("/api/auth/login", data={"username": "me@example.com", "password": "password123"})
    token = login_response.json()["access_token"]
    
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"

def test_me_endpoint_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
