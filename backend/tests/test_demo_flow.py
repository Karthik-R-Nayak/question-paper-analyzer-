from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.services import pgvector_search
from app.models import Base


def test_demo_flow(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        pgvector_search,
        "model_encode_text",
        lambda text: [1.0, 0.0] if "normalization" in text.lower() else [0.0, 1.0],
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            homepage = client.get("/")
            assert homepage.status_code == 200
            assert client.get("/static/app.js").status_code == 200
            assert client.get("/static/styles.css").status_code == 200

            subject = client.post(
                "/api/v1/catalog/subjects",
                json={"subject_code": "DBMS", "subject_name": "Databases"},
            )
            semester = client.post(
                "/api/v1/catalog/semesters",
                json={"semester_number": 5, "academic_year": "2026-2027"},
            )
            question_type = client.post(
                "/api/v1/catalog/question-types",
                json={"type_name": "Long Answer"},
            )
            assert subject.status_code == semester.status_code == question_type.status_code == 201

            unit = client.post(
                "/api/v1/catalog/units",
                json={
                    "subject_id": subject.json()["subject_id"],
                    "unit_number": 1,
                    "unit_name": "Relational Databases",
                },
            )
            topic = client.post(
                "/api/v1/catalog/topics",
                json={
                    "unit_id": unit.json()["unit_id"],
                    "topic_name": "Normalization",
                },
            )
            assert unit.status_code == topic.status_code == 201

            paper = client.post(
                "/api/v1/papers",
                json={
                    "subject_id": subject.json()["subject_id"],
                    "semester_id": semester.json()["semester_id"],
                    "exam_type": "End",
                    "total_marks": 10,
                    "questions": [
                        {
                            "question_number": "1a",
                            "marks": 10,
                            "question_text": "Explain database normalization.",
                            "question_type_id": question_type.json()["type_id"],
                            "topic_ids": [topic.json()["topic_id"]],
                        }
                    ],
                },
            )
            assert paper.status_code == 201

            search = client.get(
                "/api/v1/search/questions",
                params={"q": "normalization", "subject_id": subject.json()["subject_id"]},
            )
            assert search.status_code == 200
            assert len(search.json()) == 1
            assert search.json()[0]["topics"] == ["Normalization"]

            overview = client.get(
                "/api/v1/analytics/overview",
                params={"subject_id": subject.json()["subject_id"]},
            )
            assert overview.status_code == 200
            assert overview.json()["totals"]["papers"] == 1
            assert overview.json()["totals"]["questions"] == 1
            assert overview.json()["topics"] == [{"topic_name": "Normalization", "count": 1}]

            comparison = client.get(
                "/api/v1/analytics/compare",
                params={"subject_id": subject.json()["subject_id"]},
            )
            assert comparison.status_code == 200
            assert comparison.json()[0]["total_marks"] == 10

            indexed = client.post("/api/v1/semantic/index")
            similar = client.get(
                "/api/v1/semantic/similar",
                params={"q": "Explain database normalization."},
            )
            assert indexed.status_code == 200
            assert indexed.json() == {"indexed_count": 1}
            assert similar.status_code == 200
            assert similar.json()[0]["question_text"] == "Explain database normalization."
            assert similar.json()[0]["similarity_score"] == 1.0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
