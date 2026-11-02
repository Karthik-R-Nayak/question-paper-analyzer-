from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Base, UserAccount, UserSession
from app.security import hash_session_token


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app, base_url="https://testserver") as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def test_register_login_and_logout_use_hashed_credentials_and_revocable_cookie(auth_client):
    client, session_factory = auth_client
    registration = client.post(
        "/api/v1/auth/register",
        json={"username": "NewUser", "password": "correct horse"},
    )

    assert registration.status_code == 201
    assert registration.json()["username"] == "newuser"
    cookie = client.cookies.get("session")
    assert cookie
    set_cookie = registration.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "max-age=604800" in set_cookie
    assert client.get("/api/v1/auth/me").json() == registration.json()

    with session_factory() as session:
        user = session.scalar(select(UserAccount))
        auth_session = session.scalar(select(UserSession))
        assert user.password_hash != "correct horse"
        assert user.password_hash.startswith("scrypt$")
        assert auth_session.token_hash == hash_session_token(cookie)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        assert auth_session.expires_at <= now + timedelta(days=7)
        assert auth_session.expires_at > now

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "NEWUSER", "password": "correct horse"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_registration_validation_and_duplicate_username(auth_client):
    client, _session_factory = auth_client

    assert client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "long-enough"},
    ).status_code == 422
    assert client.post(
        "/api/v1/auth/register",
        json={"username": "first-user", "password": "short"},
    ).status_code == 422
    assert client.post(
        "/api/v1/auth/register",
        json={"username": "First-User", "password": "long-enough"},
    ).status_code == 201
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"username": "first-user", "password": "another-password"},
    )
    assert duplicate.status_code == 409


def test_login_rejects_invalid_password_and_mutations_require_auth(auth_client):
    client, _session_factory = auth_client
    assert client.post(
        "/api/v1/auth/register",
        json={"username": "reader", "password": "reader-password"},
    ).status_code == 201
    client.post("/api/v1/auth/logout")

    assert client.get("/api/v1/catalog/subjects").status_code == 200
    assert client.get("/api/v1/papers").status_code == 200
    assert client.get("/api/v1/semantic/similar", params={"q": "database"}).status_code == 200
    assert client.post(
        "/api/v1/papers",
        json={
            "subject_id": 1,
            "semester_id": 1,
            "exam_type": "End",
            "total_marks": 10,
            "questions": [],
        },
    ).status_code == 401
    assert client.post(
        "/api/v1/catalog/subjects",
        json={"subject_code": "DBMS", "subject_name": "Databases"},
    ).status_code == 401
    assert client.post("/api/v1/semantic/index").status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "reader", "password": "wrong-password"},
    ).status_code == 401


def test_expired_session_is_rejected(auth_client):
    client, session_factory = auth_client
    assert client.post(
        "/api/v1/auth/register",
        json={"username": "expired-user", "password": "expired-password"},
    ).status_code == 201
    token = client.cookies.get("session")

    with session_factory() as session:
        auth_session = session.scalar(
            select(UserSession).where(
                UserSession.token_hash == hash_session_token(token)
            )
        )
        auth_session.expires_at = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        )
        session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401
