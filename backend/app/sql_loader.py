import re
from functools import lru_cache
from pathlib import Path
from collections.abc import Iterable, Mapping

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

SQL_DIRECTORY = Path(__file__).with_name("sql")
SQL_FILES = frozenset(
    {
        "schema.sql",
        "questions.sql",
        "papers.sql",
        "analytics.sql",
        "semantics.sql",
    }
)
_QUERY_MARKER = re.compile(r"(?m)^-- name: ([a-z][a-z0-9_]*)\s*$")
_DEMONSTRATION_MARKER = re.compile(r"(?m)^-- DEMONSTRATION QUERIES\b")


@lru_cache(maxsize=len(SQL_FILES))
def _read_sql_file(file_name: str) -> dict[str, str]:
    if file_name not in SQL_FILES:
        raise ValueError(f"Unsupported SQL file: {file_name}")

    source = (SQL_DIRECTORY / file_name).read_text(encoding="utf-8")
    markers = list(_QUERY_MARKER.finditer(source))
    demonstrations = _DEMONSTRATION_MARKER.search(source)
    if not markers:
        raise ValueError(f"No named SQL statements found in {file_name}")

    statements: dict[str, str] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(source)
        if demonstrations and demonstrations.start() > marker.end():
            end = min(end, demonstrations.start())
        name = marker.group(1)
        if name in statements:
            raise ValueError(f"Duplicate SQL statement name {name!r} in {file_name}")
        statement = source[marker.end() : end].strip()
        if not statement:
            raise ValueError(f"SQL statement {name!r} in {file_name} is empty")
        statements[name] = statement
    return statements


def load_sql(
    file_name: str,
    statement_name: str,
    *,
    expanding_parameters: Iterable[str] = (),
) -> TextClause:
    statements = _read_sql_file(file_name)
    if statement_name not in statements:
        raise KeyError(
            f"SQL statement {statement_name!r} was not found in {file_name}"
        )

    statement = text(statements[statement_name])
    expanding = tuple(
        bindparam(parameter_name, expanding=True)
        for parameter_name in expanding_parameters
    )
    return statement.bindparams(*expanding) if expanding else statement


def execute_sql(
    session: Session,
    file_name: str,
    statement_name: str,
    parameters: Mapping[str, object] | None = None,
    *,
    expanding_parameters: Iterable[str] = (),
) -> Result:
    statement = load_sql(
        file_name,
        statement_name,
        expanding_parameters=expanding_parameters,
    )
    return session.execute(statement, parameters or {})
