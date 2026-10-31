import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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
def analytics_client():
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
    with session_factory() as session:
        subject = Subject(subject_code="DBMS", subject_name="Databases")
        semester_5 = Semester(semester_number=5, academic_year="2025-2026")
        semester_6 = Semester(semester_number=6, academic_year="2026-2027")
        long_answer = QuestionType(type_name="Long Answer")
        short_answer = QuestionType(type_name="Short Answer")
        session.add_all([subject, semester_5, semester_6, long_answer, short_answer])
        session.flush()

        unit_1 = Unit(subject_id=subject.subject_id, unit_number=1, unit_name="Models")
        unit_2 = Unit(subject_id=subject.subject_id, unit_number=2, unit_name="Transactions")
        session.add_all([unit_1, unit_2])
        session.flush()
        normalization = Topic(unit_id=unit_1.unit_id, topic_name="Normalization")
        transactions = Topic(unit_id=unit_2.unit_id, topic_name="Transactions")
        session.add_all([normalization, transactions])
        session.flush()

        paper_end = ExamPaper(
            subject_id=subject.subject_id,
            semester_id=semester_5.semester_id,
            exam_type="End",
            total_marks=15,
        )
        paper_mid = ExamPaper(
            subject_id=subject.subject_id,
            semester_id=semester_5.semester_id,
            exam_type="Mid",
            total_marks=8,
        )
        paper_next_semester = ExamPaper(
            subject_id=subject.subject_id,
            semester_id=semester_6.semester_id,
            exam_type="End",
            total_marks=7,
        )
        session.add_all([paper_end, paper_mid, paper_next_semester])
        session.flush()

        normalization_question = Question(
            type_id=long_answer.type_id,
            question_text="Explain database normalization.",
        )
        transactions_question = Question(
            type_id=short_answer.type_id,
            question_text="Explain database transactions.",
        )
        next_semester_question = Question(
            type_id=short_answer.type_id,
            question_text="Describe transaction isolation.",
        )
        session.add_all(
            [normalization_question, transactions_question, next_semester_question]
        )
        session.flush()
        session.add_all(
            [
                PaperQuestion(
                    paper_id=paper_end.paper_id,
                    question_id=normalization_question.question_id,
                    question_number="1a",
                    marks=10,
                ),
                PaperQuestion(
                    paper_id=paper_end.paper_id,
                    question_id=transactions_question.question_id,
                    question_number="1b",
                    marks=5,
                ),
                PaperQuestion(
                    paper_id=paper_mid.paper_id,
                    question_id=normalization_question.question_id,
                    question_number="2a",
                    marks=8,
                ),
                PaperQuestion(
                    paper_id=paper_next_semester.paper_id,
                    question_id=next_semester_question.question_id,
                    question_number="1a",
                    marks=7,
                ),
                QuestionTopic(
                    question_id=normalization_question.question_id,
                    topic_id=normalization.topic_id,
                ),
                QuestionTopic(
                    question_id=transactions_question.question_id,
                    topic_id=transactions.topic_id,
                ),
                QuestionTopic(
                    question_id=next_semester_question.question_id,
                    topic_id=transactions.topic_id,
                ),
            ]
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_overview_applies_all_filters_to_topic_frequency(analytics_client):
    response = analytics_client.get(
        "/api/v1/analytics/overview",
        params={"semester_id": 2, "exam_type": "End"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["papers"] == 1
    assert body["totals"]["questions"] == 1
    assert body["question_types"] == [{"type_name": "Short Answer", "count": 1}]
    assert body["topics"] == [{"topic_name": "Transactions", "count": 1}]
    assert body["semesters"] == [
        {"semester_number": 6, "academic_year": "2026-2027", "count": 1}
    ]


def test_pattern_analytics_counts_per_paper_question_and_marks(analytics_client):
    response = analytics_client.get("/api/v1/analytics/patterns")

    assert response.status_code == 200
    body = response.json()
    assert body["unit_weightage"] == [
        {
            "subject_name": "Databases",
            "unit_name": "Models",
            "total_marks": 18,
            "weightage_percent": 60.0,
        },
        {
            "subject_name": "Databases",
            "unit_name": "Transactions",
            "total_marks": 12,
            "weightage_percent": 40.0,
        },
    ]
    assert body["topic_frequency"] == [
        {
            "subject_name": "Databases",
            "topic_name": "Normalization",
            "frequency": 2,
            "total_marks": 18,
            "paper_count": 2,
        },
        {
            "subject_name": "Databases",
            "topic_name": "Transactions",
            "frequency": 2,
            "total_marks": 12,
            "paper_count": 2,
        },
    ]
    assert body["question_type_distribution"] == [
        {"type_name": "Long Answer", "count": 2, "total_marks": 18},
        {"type_name": "Short Answer", "count": 2, "total_marks": 12},
    ]
    assert body["recurring_concepts"] == [
        {"topic_name": "Normalization", "frequency": 2, "total_marks": 18},
        {"topic_name": "Transactions", "frequency": 2, "total_marks": 12},
    ]
    assert body["semester_trends"] == [
        {
            "subject_name": "Databases",
            "semester_number": 5,
            "academic_year": "2025-2026",
            "question_count": 3,
            "total_marks": 23,
        },
        {
            "subject_name": "Databases",
            "semester_number": 6,
            "academic_year": "2026-2027",
            "question_count": 1,
            "total_marks": 7,
        },
    ]


def test_pattern_analytics_filters_each_result_consistently(analytics_client):
    response = analytics_client.get(
        "/api/v1/analytics/patterns",
        params={"semester_id": 2, "exam_type": "End"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["unit_weightage"] == [
        {
            "subject_name": "Databases",
            "unit_name": "Transactions",
            "total_marks": 7,
            "weightage_percent": 100.0,
        }
    ]
    assert body["topic_frequency"] == [
        {
            "subject_name": "Databases",
            "topic_name": "Transactions",
            "frequency": 1,
            "total_marks": 7,
            "paper_count": 1,
        }
    ]
    assert body["question_type_distribution"] == [
        {"type_name": "Short Answer", "count": 1, "total_marks": 7}
    ]
    assert body["recurring_concepts"] == [
        {"topic_name": "Transactions", "frequency": 1, "total_marks": 7}
    ]
    assert body["semester_trends"] == [
        {
            "subject_name": "Databases",
            "semester_number": 6,
            "academic_year": "2026-2027",
            "question_count": 1,
            "total_marks": 7,
        }
    ]
