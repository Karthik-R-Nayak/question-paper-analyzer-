import pytest
from sqlalchemy.sql.elements import TextClause

from app.sql_loader import SQL_FILES, load_sql


def test_loader_exposes_only_the_five_functional_sql_files():
    assert SQL_FILES == {
        "schema.sql",
        "questions.sql",
        "papers.sql",
        "analytics.sql",
        "semantics.sql",
    }


def test_loader_returns_named_sqlalchemy_text_and_expanding_parameters():
    statement = load_sql(
        "questions.sql",
        "question_topics_for_questions",
        expanding_parameters=("question_ids",),
    )

    assert isinstance(statement, TextClause)
    assert statement._bindparams["question_ids"].expanding
    assert "IN (__[POSTCOMPILE_question_ids])" in str(statement)


def test_loader_rejects_files_outside_the_sql_directory():
    with pytest.raises(ValueError, match="Unsupported SQL file"):
        load_sql("..\\..\\.env", "anything")


def test_demonstration_sql_is_not_a_loadable_application_statement():
    with pytest.raises(KeyError, match="not found"):
        load_sql("analytics.sql", "demonstration_window_functions")

    statement = load_sql("analytics.sql", "pattern_semester_trends")
    assert "DEMONSTRATION" not in str(statement)
