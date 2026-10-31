from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
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

router = APIRouter(prefix="/api/v1", tags=["analytics"])


def _apply_filters(stmt, *, subject_id=None, semester_id=None, exam_type=None):
    if subject_id is not None:
        stmt = stmt.where(ExamPaper.subject_id == subject_id)
    if semester_id is not None:
        stmt = stmt.where(ExamPaper.semester_id == semester_id)
    if exam_type:
        stmt = stmt.where(ExamPaper.exam_type == exam_type)
    return stmt


def _filtered_paper_questions(*, subject_id=None, semester_id=None, exam_type=None):
    stmt = (
        select(
            PaperQuestion.paper_id,
            PaperQuestion.question_id,
            PaperQuestion.marks,
            ExamPaper.subject_id,
            ExamPaper.semester_id,
            ExamPaper.exam_type,
        )
        .join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id)
    )
    return _apply_filters(
        stmt,
        subject_id=subject_id,
        semester_id=semester_id,
        exam_type=exam_type,
    ).subquery()


@router.get("/search/questions")
def search_questions(
    q: str = Query(default="", description="Keyword to search in the question text."),
    subject_id: int | None = None,
    semester_id: int | None = None,
    exam_type: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    stmt = (
        select(
            Question.question_id,
            Question.question_text,
            Question.type_id,
            QuestionType.type_name.label("question_type"),
            PaperQuestion.question_number,
            PaperQuestion.marks,
            ExamPaper.paper_id,
            ExamPaper.exam_type,
            Subject.subject_id,
            Subject.subject_name,
            Semester.semester_id,
            Semester.semester_number,
            Semester.academic_year,
        )
        .join(PaperQuestion, PaperQuestion.question_id == Question.question_id)
        .join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id)
        .join(Subject, Subject.subject_id == ExamPaper.subject_id)
        .join(Semester, Semester.semester_id == ExamPaper.semester_id)
        .join(QuestionType, QuestionType.type_id == Question.type_id)
    )

    if q.strip():
        stmt = stmt.where(func.lower(Question.question_text).like(f"%{q.strip().lower()}%"))
    if subject_id is not None:
        stmt = stmt.where(Subject.subject_id == subject_id)
    if semester_id is not None:
        stmt = stmt.where(Semester.semester_id == semester_id)
    if exam_type:
        stmt = stmt.where(ExamPaper.exam_type == exam_type)

    rows = session.execute(stmt.order_by(Question.question_id.desc()).limit(limit)).all()
    if not rows:
        return []

    question_ids = [row.question_id for row in rows]
    topic_rows = session.execute(
        select(QuestionTopic.question_id, Topic.topic_name)
        .join(Topic, Topic.topic_id == QuestionTopic.topic_id)
        .where(QuestionTopic.question_id.in_(question_ids))
        .order_by(Topic.topic_name)
    ).all()

    topic_map: dict[int, list[str]] = defaultdict(list)
    for question_id, topic_name in topic_rows:
        topic_map[question_id].append(topic_name)

    results = []
    for row in rows:
        results.append(
            {
                "question_id": row.question_id,
                "question_text": row.question_text,
                "question_type": row.question_type,
                "question_type_id": row.type_id,
                "question_number": row.question_number,
                "marks": row.marks,
                "paper_id": row.paper_id,
                "exam_type": row.exam_type,
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "semester_id": row.semester_id,
                "semester_number": row.semester_number,
                "academic_year": row.academic_year,
                "topics": topic_map.get(row.question_id, []),
            }
        )

    return results


@router.get("/analytics/overview")
def analytics_overview(
    subject_id: int | None = None,
    semester_id: int | None = None,
    exam_type: str | None = None,
    session: Session = Depends(get_session),
):
    question_scope = _filtered_paper_questions(
        subject_id=subject_id,
        semester_id=semester_id,
        exam_type=exam_type,
    )
    paper_stmt = select(func.count(ExamPaper.paper_id))
    question_stmt = select(func.count(question_scope.c.question_id))

    if subject_id is not None:
        paper_stmt = paper_stmt.where(ExamPaper.subject_id == subject_id)
    if semester_id is not None:
        paper_stmt = paper_stmt.where(ExamPaper.semester_id == semester_id)
    if exam_type:
        paper_stmt = paper_stmt.where(ExamPaper.exam_type == exam_type)

    question_type_stmt = (
        select(QuestionType.type_name, func.count(question_scope.c.question_id).label("count"))
        .join(Question, Question.type_id == QuestionType.type_id)
        .join(question_scope, question_scope.c.question_id == Question.question_id)
        .group_by(QuestionType.type_name)
        .order_by(
            func.count(question_scope.c.question_id).desc(),
            QuestionType.type_name,
        )
    )
    topic_stmt = (
        select(Topic.topic_name, func.count(question_scope.c.question_id).label("count"))
        .join(QuestionTopic, QuestionTopic.topic_id == Topic.topic_id)
        .join(question_scope, question_scope.c.question_id == QuestionTopic.question_id)
        .group_by(Topic.topic_name)
        .order_by(
            func.count(question_scope.c.question_id).desc(),
            Topic.topic_name,
        )
    )
    semester_stmt = (
        select(
            Semester.semester_number,
            Semester.academic_year,
            func.count(question_scope.c.question_id).label("count"),
        )
        .join(question_scope, question_scope.c.semester_id == Semester.semester_id)
        .group_by(Semester.semester_number, Semester.academic_year)
        .order_by(Semester.semester_number)
    )

    return {
        "totals": {
            "papers": session.scalar(paper_stmt) or 0,
            "questions": session.scalar(question_stmt) or 0,
            "subjects": session.scalar(select(func.count(Subject.subject_id))) or 0,
            "semesters": session.scalar(select(func.count(Semester.semester_id))) or 0,
        },
        "question_types": [
            {"type_name": row.type_name, "count": row.count}
            for row in session.execute(question_type_stmt).all()
        ],
        "topics": [
            {"topic_name": row.topic_name, "count": row.count}
            for row in session.execute(topic_stmt).all()
        ],
        "semesters": [
            {
                "semester_number": row.semester_number,
                "academic_year": row.academic_year,
                "count": row.count,
            }
            for row in session.execute(semester_stmt).all()
        ],
    }


@router.get("/analytics/compare")
def compare_patterns(
    subject_id: int | None = None,
    session: Session = Depends(get_session),
):
    stmt = (
        select(
            Subject.subject_name,
            Semester.semester_number,
            Semester.academic_year,
            func.count(Question.question_id).label("question_count"),
            func.sum(PaperQuestion.marks).label("total_marks"),
        )
        .join(ExamPaper, ExamPaper.subject_id == Subject.subject_id)
        .join(Semester, Semester.semester_id == ExamPaper.semester_id)
        .join(PaperQuestion, PaperQuestion.paper_id == ExamPaper.paper_id)
        .join(Question, Question.question_id == PaperQuestion.question_id)
        .group_by(Subject.subject_name, Semester.semester_number, Semester.academic_year)
        .order_by(Semester.semester_number)
    )
    if subject_id is not None:
        stmt = stmt.where(Subject.subject_id == subject_id)

    rows = session.execute(stmt).all()
    return [
        {
            "subject_name": row.subject_name,
            "semester_number": row.semester_number,
            "academic_year": row.academic_year,
            "question_count": row.question_count,
            "total_marks": row.total_marks or 0,
        }
        for row in rows
    ]


@router.get("/analytics/patterns")
def pattern_analytics(
    subject_id: int | None = None,
    semester_id: int | None = None,
    exam_type: str | None = None,
    session: Session = Depends(get_session),
):
    question_scope = _filtered_paper_questions(
        subject_id=subject_id,
        semester_id=semester_id,
        exam_type=exam_type,
    )

    unit_weightage_stmt = (
        select(
            Subject.subject_name,
            Unit.unit_name,
            func.sum(question_scope.c.marks).label("total_marks"),
        )
        .join(QuestionTopic, QuestionTopic.question_id == question_scope.c.question_id)
        .join(Topic, Topic.topic_id == QuestionTopic.topic_id)
        .join(Unit, Unit.unit_id == Topic.unit_id)
        .join(Subject, Subject.subject_id == Unit.subject_id)
        .group_by(Subject.subject_name, Unit.unit_name)
        .order_by(func.sum(question_scope.c.marks).desc(), Unit.unit_name)
    )

    topic_frequency_stmt = (
        select(
            Subject.subject_name,
            Topic.topic_name,
            func.count(question_scope.c.question_id).label("frequency"),
            func.sum(question_scope.c.marks).label("total_marks"),
            func.count(func.distinct(question_scope.c.paper_id)).label("paper_count"),
        )
        .join(QuestionTopic, QuestionTopic.question_id == question_scope.c.question_id)
        .join(Topic, Topic.topic_id == QuestionTopic.topic_id)
        .join(Unit, Unit.unit_id == Topic.unit_id)
        .join(Subject, Subject.subject_id == Unit.subject_id)
        .group_by(Subject.subject_name, Topic.topic_name)
        .order_by(
            func.count(question_scope.c.question_id).desc(),
            Topic.topic_name,
        )
    )

    question_type_stmt = (
        select(
            QuestionType.type_name,
            func.count(question_scope.c.question_id).label("count"),
            func.sum(question_scope.c.marks).label("total_marks"),
        )
        .join(Question, Question.type_id == QuestionType.type_id)
        .join(question_scope, question_scope.c.question_id == Question.question_id)
        .group_by(QuestionType.type_name)
        .order_by(
            func.count(question_scope.c.question_id).desc(),
            QuestionType.type_name,
        )
    )

    recurring_concepts_stmt = (
        select(
            Topic.topic_name,
            func.count(question_scope.c.question_id).label("frequency"),
            func.sum(question_scope.c.marks).label("total_marks"),
        )
        .join(QuestionTopic, QuestionTopic.topic_id == Topic.topic_id)
        .join(question_scope, question_scope.c.question_id == QuestionTopic.question_id)
        .group_by(Topic.topic_name)
        .order_by(
            func.count(question_scope.c.question_id).desc(),
            Topic.topic_name,
        )
    )

    semester_trend_stmt = (
        select(
            Subject.subject_name,
            Semester.semester_number,
            Semester.academic_year,
            func.count(question_scope.c.question_id).label("question_count"),
            func.sum(question_scope.c.marks).label("total_marks"),
        )
        .join(question_scope, question_scope.c.subject_id == Subject.subject_id)
        .join(Semester, Semester.semester_id == question_scope.c.semester_id)
        .group_by(Subject.subject_name, Semester.semester_number, Semester.academic_year)
        .order_by(Semester.semester_number, Semester.academic_year)
    )

    if subject_id is not None:
        unit_weightage_stmt = unit_weightage_stmt.where(Subject.subject_id == subject_id)
        topic_frequency_stmt = topic_frequency_stmt.where(Subject.subject_id == subject_id)
        semester_trend_stmt = semester_trend_stmt.where(Subject.subject_id == subject_id)

    total_marks_for_units = session.execute(unit_weightage_stmt).all()
    topic_rows = session.execute(topic_frequency_stmt).all()
    type_rows = session.execute(question_type_stmt).all()
    recurring_rows = session.execute(recurring_concepts_stmt).all()
    trends = session.execute(semester_trend_stmt).all()

    total = sum(row.total_marks or 0 for row in total_marks_for_units)
    unit_weightage = [
        {
            "subject_name": row.subject_name,
            "unit_name": row.unit_name,
            "total_marks": row.total_marks or 0,
            "weightage_percent": round(((row.total_marks or 0) / total * 100), 2) if total else 0,
        }
        for row in total_marks_for_units
    ]

    return {
        "unit_weightage": unit_weightage,
        "topic_frequency": [
            {
                "subject_name": row.subject_name,
                "topic_name": row.topic_name,
                "frequency": row.frequency,
                "total_marks": row.total_marks or 0,
                "paper_count": row.paper_count,
            }
            for row in topic_rows
        ],
        "question_type_distribution": [
            {
                "type_name": row.type_name,
                "count": row.count,
                "total_marks": row.total_marks or 0,
            }
            for row in type_rows
        ],
        "recurring_concepts": [
            {
                "topic_name": row.topic_name,
                "frequency": row.frequency,
                "total_marks": row.total_marks or 0,
            }
            for row in recurring_rows
        ],
        "semester_trends": [
            {
                "subject_name": row.subject_name,
                "semester_number": row.semester_number,
                "academic_year": row.academic_year,
                "question_count": row.question_count,
                "total_marks": row.total_marks or 0,
            }
            for row in trends
        ],
    }
