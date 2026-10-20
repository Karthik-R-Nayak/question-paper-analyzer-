import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import get_session
from app.main import app
from app.models import Base, QuestionType, Semester, Subject, Topic, Unit


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.add_all(
            [
                Subject(subject_id=1, subject_code="DBMS", subject_name="Databases"),
                Subject(subject_id=2, subject_code="OS", subject_name="Operating Systems"),
                Semester(semester_id=1, semester_number=5, academic_year="2026-2027"),
                QuestionType(type_id=1, type_name="Long Answer"),
                Unit(unit_id=1, subject_id=1, unit_number=1, unit_name="Models"),
                Topic(topic_id=1, unit_id=1, topic_name="Relational model"),
                Unit(unit_id=2, subject_id=2, unit_number=1, unit_name="Processes"),
                Topic(topic_id=2, unit_id=2, topic_name="Scheduling"),
            ]
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def sample_payload():
    return {
        "subject_id": 1,
        "semester_id": 1,
        "exam_type": "End",
        "total_marks": 10,
        "questions": [
            {
                "question_number": "1a",
                "marks": 10,
                "question_text": "Explain the relational model.",
                "question_type_id": 1,
                "topic_ids": [1],
            }
        ],
    }


def test_creates_paper_and_questions(client):
    response = client.post("/api/v1/papers", json=sample_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["paper_id"] == 1
    assert body["questions"][0]["question_number"] == "1a"
    assert body["questions"][0]["topic_ids"] == [1]


def test_rejects_unknown_subject(client):
    payload = sample_payload()
    payload["subject_id"] = 3

    response = client.post("/api/v1/papers", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown subject id: 3"


def test_rejects_duplicate_question_numbers(client):
    payload = sample_payload()
    payload["questions"].append({**payload["questions"][0], "question_text": "Another question"})

    response = client.post("/api/v1/papers", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "Question numbers must be unique within a paper."


def test_rejects_topic_belonging_to_another_subject(client):
    payload = sample_payload()
    payload["questions"][0]["topic_ids"] = [2]

    response = client.post("/api/v1/papers", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Topic id(s) do not belong to the paper's subject: 2"
    )
