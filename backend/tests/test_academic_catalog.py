import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import (
    Base,
    ExamPaper,
    PaperQuestion,
    Question,
    QuestionTopic,
    QuestionType,
    Semester,
    Subject,
    Topic,
    Unit,
)


@pytest.fixture
def catalog():
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
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def test_catalog_resources_support_create_list_get_update_and_delete(catalog):
    client, _ = catalog

    subject_response = client.post(
        "/api/v1/catalog/subjects",
        json={"subject_code": "DBMS", "subject_name": "Databases"},
    )
    assert subject_response.status_code == 201
    subject = subject_response.json()
    assert subject["department"] is None
    assert client.get("/api/v1/catalog/subjects").json() == [subject]
    assert client.get(f"/api/v1/catalog/subjects/{subject['subject_id']}").json() == subject

    semester_response = client.post(
        "/api/v1/catalog/semesters",
        json={"semester_number": 5, "academic_year": "2026-2027"},
    )
    assert semester_response.status_code == 201
    semester = semester_response.json()
    assert client.get("/api/v1/catalog/semesters").json() == [semester]
    assert client.get(
        f"/api/v1/catalog/semesters/{semester['semester_id']}"
    ).json() == semester

    unit_response = client.post(
        "/api/v1/catalog/units",
        json={
            "subject_id": subject["subject_id"],
            "unit_number": 1,
            "unit_name": "Models",
        },
    )
    assert unit_response.status_code == 201
    unit = unit_response.json()
    assert client.get("/api/v1/catalog/units").json() == [unit]
    assert client.get(f"/api/v1/catalog/units/{unit['unit_id']}").json() == unit

    topic_response = client.post(
        "/api/v1/catalog/topics",
        json={"unit_id": unit["unit_id"], "topic_name": "Relational model"},
    )
    assert topic_response.status_code == 201
    topic = topic_response.json()
    assert client.get("/api/v1/catalog/topics").json() == [topic]
    assert client.get(f"/api/v1/catalog/topics/{topic['topic_id']}").json() == topic

    question_type_response = client.post(
        "/api/v1/catalog/question-types",
        json={"type_name": "Long Answer"},
    )
    assert question_type_response.status_code == 201
    question_type = question_type_response.json()
    assert client.get("/api/v1/catalog/question-types").json() == [question_type]
    assert client.get(
        f"/api/v1/catalog/question-types/{question_type['type_id']}"
    ).json() == question_type

    assert client.put(
        f"/api/v1/catalog/subjects/{subject['subject_id']}",
        json={
            "subject_code": "DBMS2",
            "subject_name": "Database Systems",
            "department": "Computer Science",
        },
    ).json()["subject_name"] == "Database Systems"
    assert client.put(
        f"/api/v1/catalog/semesters/{semester['semester_id']}",
        json={"semester_number": 6, "academic_year": "2027-2028"},
    ).json()["semester_number"] == 6
    assert client.put(
        f"/api/v1/catalog/units/{unit['unit_id']}",
        json={
            "subject_id": subject["subject_id"],
            "unit_number": 2,
            "unit_name": "Relational databases",
        },
    ).json()["unit_number"] == 2
    assert client.put(
        f"/api/v1/catalog/topics/{topic['topic_id']}",
        json={"unit_id": unit["unit_id"], "topic_name": "Normalization"},
    ).json()["topic_name"] == "Normalization"
    assert client.put(
        f"/api/v1/catalog/question-types/{question_type['type_id']}",
        json={"type_name": "Short Answer"},
    ).json()["type_name"] == "Short Answer"

    assert client.delete(f"/api/v1/catalog/topics/{topic['topic_id']}").status_code == 204
    assert client.get("/api/v1/catalog/topics").json() == []
    assert client.delete(f"/api/v1/catalog/units/{unit['unit_id']}").status_code == 204
    assert client.delete(
        f"/api/v1/catalog/semesters/{semester['semester_id']}"
    ).status_code == 204
    assert client.delete(
        f"/api/v1/catalog/question-types/{question_type['type_id']}"
    ).status_code == 204
    assert client.delete(
        f"/api/v1/catalog/subjects/{subject['subject_id']}"
    ).status_code == 204


def test_catalog_validates_references_and_reports_missing_records(catalog):
    client, _ = catalog

    response = client.post(
        "/api/v1/catalog/units",
        json={"subject_id": 99, "unit_number": 1, "unit_name": "Models"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Subject not found: 99"
    assert client.get("/api/v1/catalog/subjects/99").status_code == 404
    assert client.post(
        "/api/v1/catalog/semesters",
        json={"semester_number": 9, "academic_year": "2026-2027"},
    ).status_code == 422


def test_catalog_rejects_duplicate_unique_values(catalog):
    client, _ = catalog
    payload = {"subject_code": "DBMS", "subject_name": "Databases"}

    assert client.post("/api/v1/catalog/subjects", json=payload).status_code == 201
    response = client.post("/api/v1/catalog/subjects", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalog record conflicts with existing data."


def test_deleting_catalog_records_applies_schema_cascades(catalog):
    client, session_factory = catalog
    with session_factory() as session:
        subject = Subject(subject_code="DBMS", subject_name="Databases")
        semester = Semester(semester_number=5, academic_year="2026-2027")
        question_type = QuestionType(type_name="Long Answer")
        session.add_all([subject, semester, question_type])
        session.flush()

        unit = Unit(subject_id=subject.subject_id, unit_number=1, unit_name="Models")
        session.add(unit)
        session.flush()
        topic = Topic(unit_id=unit.unit_id, topic_name="Relational model")
        paper = ExamPaper(
            subject_id=subject.subject_id,
            semester_id=semester.semester_id,
            exam_type="End",
            total_marks=10,
        )
        session.add_all([topic, paper])
        session.flush()
        question = Question(
            type_id=question_type.type_id,
            question_text="Explain the relational model.",
        )
        session.add(question)
        session.flush()
        session.add_all(
            [
                PaperQuestion(
                    paper_id=paper.paper_id,
                    question_id=question.question_id,
                    question_number="1",
                    marks=10,
                ),
                QuestionTopic(question_id=question.question_id, topic_id=topic.topic_id),
            ]
        )
        session.commit()
        subject_id = subject.subject_id
        type_id = question_type.type_id

    response = client.delete(f"/api/v1/catalog/subjects/{subject_id}")
    assert response.status_code == 204

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ExamPaper)) == 0
        assert session.scalar(select(func.count()).select_from(PaperQuestion)) == 0
        assert session.scalar(select(func.count()).select_from(Unit)) == 0
        assert session.scalar(select(func.count()).select_from(Topic)) == 0
        assert session.scalar(select(func.count()).select_from(QuestionTopic)) == 0
        assert session.scalar(select(func.count()).select_from(Question)) == 1

    response = client.delete(f"/api/v1/catalog/question-types/{type_id}")
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot delete a question type that is used by questions."
    )
