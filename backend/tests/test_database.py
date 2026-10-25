import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import create_database_engine, get_session_factory
from app.models import Base, ExamPaper, Semester, Subject


def test_sqlite_engine_enforces_foreign_keys():
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            ExamPaper(
                subject_id=999,
                semester_id=999,
                exam_type="End",
                total_marks=100,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    engine.dispose()


def test_sqlite_subject_delete_cascades_to_exam_papers():
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        subject = Subject(subject_code="DBMS", subject_name="Databases")
        semester = Semester(semester_number=5, academic_year="2026-2027")
        session.add_all([subject, semester])
        session.flush()
        paper = ExamPaper(
            subject_id=subject.subject_id,
            semester_id=semester.semester_id,
            exam_type="End",
            total_marks=100,
        )
        session.add(paper)
        session.commit()
        paper_id = paper.paper_id

        session.delete(subject)
        session.commit()

        assert session.scalar(
            select(ExamPaper.paper_id).where(ExamPaper.paper_id == paper_id)
        ) is None

    engine.dispose()


def test_session_factory_reuses_configured_engine():
    assert get_session_factory() is get_session_factory()
