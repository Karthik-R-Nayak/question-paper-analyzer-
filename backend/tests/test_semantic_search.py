import sys
from types import ModuleType

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Base, Question, QuestionType
from app.services import pgvector_search


def test_sentence_transformer_model_is_loaded_once_and_reused(monkeypatch):
    initialization_count = 0

    class FakeSentenceTransformer:
        def __init__(self, _model_name):
            nonlocal initialization_count
            initialization_count += 1

        def encode(self, text, normalize_embeddings):
            assert normalize_embeddings is True
            return [float(len(text)), 1.0]

    module = ModuleType("sentence_transformers")
    module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    pgvector_search._get_sentence_transformer.cache_clear()

    try:
        first_embedding = pgvector_search.model_encode_text("first")
        second_embedding = pgvector_search.model_encode_text("second")

        assert first_embedding == [5.0, 1.0]
        assert second_embedding == [6.0, 1.0]
        assert initialization_count == 1
    finally:
        pgvector_search._get_sentence_transformer.cache_clear()


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
        with TestClient(app, base_url="https://testserver") as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={"username": "semantic-user", "password": "semantic-password"},
            )
            index_response = client.post("/api/v1/semantic/index")
            search_response = client.get(
                "/api/v1/semantic/similar",
                params={"q": "Explain the relational model."},
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert registration.status_code == 201
    assert index_response.status_code == 200
    assert index_response.json() == {"indexed_count": 2}
    assert search_response.status_code == 200
    results = search_response.json()
    assert results[0]["question_text"] == "Explain the relational model."
    assert results[0]["similarity_score"] == 1.0
