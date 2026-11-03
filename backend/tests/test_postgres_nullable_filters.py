import os

import pytest
from sqlalchemy import create_engine, text

from app.sql_loader import execute_sql


@pytest.fixture
def postgres_nullable_filter_connection():
    database_url = os.getenv("TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("Set TEST_POSTGRES_URL to run PostgreSQL integration tests.")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in (
                """
                CREATE TEMP TABLE subject (
                    subject_id INTEGER,
                    subject_name VARCHAR(100)
                )
                """,
                """
                CREATE TEMP TABLE semester (
                    semester_id INTEGER,
                    semester_number INTEGER,
                    academic_year VARCHAR(9)
                )
                """,
                """
                CREATE TEMP TABLE question_type (
                    type_id INTEGER,
                    type_name VARCHAR(50)
                )
                """,
                """
                CREATE TEMP TABLE exam_paper (
                    paper_id INTEGER,
                    subject_id INTEGER,
                    semester_id INTEGER,
                    exam_type VARCHAR(20),
                    total_marks INTEGER
                )
                """,
                """
                CREATE TEMP TABLE question (
                    question_id INTEGER,
                    type_id INTEGER,
                    question_text TEXT
                )
                """,
                """
                CREATE TEMP TABLE paper_question (
                    paper_id INTEGER,
                    question_id INTEGER,
                    question_number VARCHAR(10),
                    marks INTEGER
                )
                """,
                """
                CREATE TEMP TABLE unit (
                    unit_id INTEGER,
                    subject_id INTEGER,
                    unit_name VARCHAR(150)
                )
                """,
                """
                CREATE TEMP TABLE topic (
                    topic_id INTEGER,
                    unit_id INTEGER,
                    topic_name VARCHAR(150)
                )
                """,
                """
                CREATE TEMP TABLE question_topic (
                    question_id INTEGER,
                    topic_id INTEGER
                )
                """,
            ):
                connection.exec_driver_sql(statement)

            connection.execute(
                text(
                    "INSERT INTO subject (subject_id, subject_name) "
                    "VALUES (:id, :name)"
                ),
                [
                    {"id": 11, "name": "Databases"},
                    {"id": 12, "name": "Operating Systems"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO semester "
                    "(semester_id, semester_number, academic_year) "
                    "VALUES (:id, :number, :year)"
                ),
                [
                    {"id": 21, "number": 5, "year": "2025-2026"},
                    {"id": 22, "number": 6, "year": "2026-2027"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO question_type (type_id, type_name) "
                    "VALUES (:id, :name)"
                ),
                [
                    {"id": 31, "name": "Long Answer"},
                    {"id": 32, "name": "Short Answer"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO exam_paper "
                    "(paper_id, subject_id, semester_id, exam_type, total_marks) "
                    "VALUES (:id, :subject_id, :semester_id, :exam_type, :marks)"
                ),
                [
                    {
                        "id": 51,
                        "subject_id": 11,
                        "semester_id": 21,
                        "exam_type": "End",
                        "marks": 10,
                    },
                    {
                        "id": 52,
                        "subject_id": 12,
                        "semester_id": 22,
                        "exam_type": "Mid",
                        "marks": 5,
                    },
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO question (question_id, type_id, question_text) "
                    "VALUES (:id, :type_id, :question_text)"
                ),
                [
                    {
                        "id": 41,
                        "type_id": 31,
                        "question_text": "Explain database normalization.",
                    },
                    {
                        "id": 42,
                        "type_id": 32,
                        "question_text": "Describe process scheduling.",
                    },
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO paper_question "
                    "(paper_id, question_id, question_number, marks) "
                    "VALUES (:paper_id, :question_id, :number, :marks)"
                ),
                [
                    {
                        "paper_id": 51,
                        "question_id": 41,
                        "number": "1a",
                        "marks": 10,
                    },
                    {
                        "paper_id": 52,
                        "question_id": 42,
                        "number": "1a",
                        "marks": 5,
                    },
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO unit (unit_id, subject_id, unit_name) "
                    "VALUES (:id, :subject_id, :name)"
                ),
                [
                    {"id": 61, "subject_id": 11, "name": "Data Models"},
                    {"id": 62, "subject_id": 12, "name": "Processes"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO topic (topic_id, unit_id, topic_name) "
                    "VALUES (:id, :unit_id, :name)"
                ),
                [
                    {"id": 71, "unit_id": 61, "name": "Normalization"},
                    {"id": 72, "unit_id": 62, "name": "Scheduling"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO question_topic (question_id, topic_id) "
                    "VALUES (:question_id, :topic_id)"
                ),
                [
                    {"question_id": 41, "topic_id": 71},
                    {"question_id": 42, "topic_id": 72},
                ],
            )
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()


def test_postgresql_nullable_question_paper_and_analytics_filters(
    postgres_nullable_filter_connection,
):
    connection = postgres_nullable_filter_connection

    unfiltered_questions = execute_sql(
        connection,
        "questions.sql",
        "search_questions",
        {
            "search_pattern": None,
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
            "limit": 20,
        },
    ).all()
    assert {row.question_id for row in unfiltered_questions} == {41, 42}

    filtered_questions = execute_sql(
        connection,
        "questions.sql",
        "search_questions",
        {
            "search_pattern": "%normalization%",
            "subject_id": 11,
            "semester_id": 21,
            "exam_type": "End",
            "limit": 20,
        },
    ).all()
    assert [row.question_id for row in filtered_questions] == [41]

    analytics_parameters = {
        "overview_totals": {"subject_id": None, "semester_id": None, "exam_type": None},
        "overview_question_types": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "overview_topics": {"subject_id": None, "semester_id": None, "exam_type": None},
        "overview_semesters": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "compare_subject_semesters": {"subject_id": None},
        "pattern_unit_weightage": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "pattern_topic_frequency": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "pattern_question_types": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "pattern_recurring_concepts": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
        "pattern_semester_trends": {
            "subject_id": None,
            "semester_id": None,
            "exam_type": None,
        },
    }
    for statement_name, parameters in analytics_parameters.items():
        execute_sql(
            connection, "analytics.sql", statement_name, parameters
        ).all()

    filtered_analytics_parameters = {
        "subject_id": 11,
        "semester_id": 21,
        "exam_type": "End",
    }
    totals = execute_sql(
        connection,
        "analytics.sql",
        "overview_totals",
        filtered_analytics_parameters,
    ).one()
    assert totals.papers == 1
    assert totals.questions == 1

    for statement_name, parameters in analytics_parameters.items():
        filtered_parameters = {
            key: filtered_analytics_parameters[key] for key in parameters
        }
        execute_sql(
            connection,
            "analytics.sql",
            statement_name,
            filtered_parameters,
        ).all()

    unexcluded_question = execute_sql(
        connection,
        "papers.sql",
        "question_number_conflict",
        {
            "paper_id": 51,
            "question_number": "1a",
            "exclude_question_id": None,
        },
    ).first()
    assert unexcluded_question.question_id == 41

    excluded_question = execute_sql(
        connection,
        "papers.sql",
        "question_number_conflict",
        {
            "paper_id": 51,
            "question_number": "1a",
            "exclude_question_id": 41,
        },
    ).first()
    assert excluded_question is None
