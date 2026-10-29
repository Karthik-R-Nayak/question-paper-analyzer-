from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Base, Question, QuestionType
from app.services import pgvector_search


def test_indexes_questions_and_returns_similar_questions(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def encode_test_text(text):
        return [1.0, 0.0] if "relational" in text.lower() else [0.0, 1.0]

    monkeypatch.setattr(pgvector_search, "model_encode_text", encode_test_text)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.add(QuestionType(type_id=1, type_name="Short Answer"))
        session.add_all(
            [
                Question(type_id=1, question_text="Explain the relational model."),
                Question(type_id=1, question_text="Describe process scheduling."),
            ]
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            index_response = client.post("/api/v1/semantic/index")
            search_response = client.get(
                "/api/v1/semantic/similar",
                params={"q": "Explain the relational model."},
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert index_response.status_code == 200
    assert index_response.json() == {"indexed_count": 2}
    assert search_response.status_code == 200
    results = search_response.json()
    assert results[0]["question_text"] == "Explain the relational model."
    assert results[0]["similarity_score"] == 1.0
