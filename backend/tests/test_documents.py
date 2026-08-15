import io

from app.core.security import get_password_hash
from app.db.models.document import Document
from app.db.models.user import User


def get_auth_token(client, db_session, email="docuser@example.com"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash("password123"),
            name="Doc User",
        )
        db_session.add(user)
        db_session.commit()

    login_response = client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    return login_response.json()["access_token"]


def test_upload_invalid_extension(client, db_session):
    token = get_auth_token(client, db_session)

    file_content = b"fake executable content"
    file = io.BytesIO(file_content)
    file.name = "test.exe"

    response = client.post(
        "/api/documents/",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.exe", file, "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "File extension not allowed" in response.json()["detail"]


def test_list_documents_ownership(client, db_session):
    token1 = get_auth_token(client, db_session, "user1@example.com")
    token2 = get_auth_token(client, db_session, "user2@example.com")

    user1 = db_session.query(User).filter(User.email == "user1@example.com").first()
    user2 = db_session.query(User).filter(User.email == "user2@example.com").first()

    # Create documents
    doc1 = Document(
        filename="doc1.pdf",
        content_type="application/pdf",
        file_path="/fake/doc1.pdf",
        user_id=user1.id,
        status="ready",
    )
    doc2 = Document(
        filename="doc2.pdf",
        content_type="application/pdf",
        file_path="/fake/doc2.pdf",
        user_id=user2.id,
        status="ready",
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # User 1 should only see doc1
    response1 = client.get(
        "/api/documents/", headers={"Authorization": f"Bearer {token1}"}
    )
    assert response1.status_code == 200
    docs1 = response1.json()
    assert len(docs1) == 1
    assert docs1[0]["filename"] == "doc1.pdf"

    # User 2 should only see doc2
    response2 = client.get(
        "/api/documents/", headers={"Authorization": f"Bearer {token2}"}
    )
    assert response2.status_code == 200
    docs2 = response2.json()
    assert len(docs2) == 1
    assert docs2[0]["filename"] == "doc2.pdf"
