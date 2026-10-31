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


def test_lists_and_gets_papers_with_questions(client):
    created = client.post("/api/v1/papers", json=sample_payload()).json()

    listed = client.get("/api/v1/papers")
    fetched = client.get(f"/api/v1/papers/{created['paper_id']}")

    assert listed.status_code == 200
    assert listed.json() == [created]
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_replaces_paper_and_its_questions(client):
    created = client.post("/api/v1/papers", json=sample_payload()).json()
    payload = sample_payload()
    payload["exam_type"] = "Mid"
    payload["questions"][0]["question_number"] = "2a"
    payload["questions"][0]["question_text"] = "Describe relational algebra."

    response = client.put(f"/api/v1/papers/{created['paper_id']}", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["exam_type"] == "Mid"
    assert body["questions"][0]["question_number"] == "2a"
    assert body["questions"][0]["question_text"] == "Describe relational algebra."
    assert body["questions"][0]["question_id"] != created["questions"][0]["question_id"]


def test_adds_updates_and_deletes_a_paper_question(client):
    paper = client.post("/api/v1/papers", json=sample_payload()).json()
    new_question = {
        "question_number": "2",
        "marks": 5,
        "question_text": "Define a relation.",
        "question_type_id": 1,
        "topic_ids": [1],
    }

    added = client.post(
        f"/api/v1/papers/{paper['paper_id']}/questions",
        json=new_question,
    )
    assert added.status_code == 201
    question_id = added.json()["question_id"]

    updated_question = {**new_question, "marks": 7, "question_text": "Define a table."}
    updated = client.put(
        f"/api/v1/papers/{paper['paper_id']}/questions/{question_id}",
        json=updated_question,
    )
    assert updated.status_code == 200
    assert updated.json()["marks"] == 7
    assert updated.json()["question_text"] == "Define a table."

    deleted = client.delete(
        f"/api/v1/papers/{paper['paper_id']}/questions/{question_id}"
    )
    assert deleted.status_code == 204
    assert len(client.get(f"/api/v1/papers/{paper['paper_id']}").json()["questions"]) == 1


def test_rejects_duplicate_question_number_when_adding(client):
    paper = client.post("/api/v1/papers", json=sample_payload()).json()
    payload = {
        "question_number": "1a",
        "marks": 5,
        "question_text": "Another question.",
        "question_type_id": 1,
        "topic_ids": [1],
    }

    response = client.post(
        f"/api/v1/papers/{paper['paper_id']}/questions",
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Question number already exists in this paper."


def test_deletes_paper_and_returns_not_found_afterward(client):
    created = client.post("/api/v1/papers", json=sample_payload()).json()

    deleted = client.delete(f"/api/v1/papers/{created['paper_id']}")
    fetched = client.get(f"/api/v1/papers/{created['paper_id']}")

    assert deleted.status_code == 204
    assert fetched.status_code == 404
    assert fetched.json()["detail"] == f"Paper not found: {created['paper_id']}"
