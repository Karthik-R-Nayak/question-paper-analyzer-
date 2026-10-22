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
)

router = APIRouter(prefix="/api/v1", tags=["analytics"])


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
    paper_stmt = select(func.count(ExamPaper.paper_id))
    question_stmt = (
        select(func.count(Question.question_id))
        .join(PaperQuestion, PaperQuestion.question_id == Question.question_id)
        .join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id)
    )

    if subject_id is not None:
        paper_stmt = paper_stmt.where(ExamPaper.subject_id == subject_id)
        question_stmt = question_stmt.where(ExamPaper.subject_id == subject_id)
    if semester_id is not None:
        paper_stmt = paper_stmt.where(ExamPaper.semester_id == semester_id)
        question_stmt = question_stmt.where(ExamPaper.semester_id == semester_id)
    if exam_type:
        paper_stmt = paper_stmt.where(ExamPaper.exam_type == exam_type)
        question_stmt = question_stmt.where(ExamPaper.exam_type == exam_type)

    question_type_stmt = (
        select(QuestionType.type_name, func.count(Question.question_id).label("count"))
        .join(Question, Question.type_id == QuestionType.type_id)
        .join(PaperQuestion, PaperQuestion.question_id == Question.question_id)
        .join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id)
        .group_by(QuestionType.type_name)
        .order_by(func.count(Question.question_id).desc())
    )
    topic_stmt = (
        select(Topic.topic_name, func.count(QuestionTopic.question_id).label("count"))
        .join(QuestionTopic, QuestionTopic.topic_id == Topic.topic_id)
        .group_by(Topic.topic_name)
        .order_by(func.count(QuestionTopic.question_id).desc())
    )
    semester_stmt = (
        select(
            Semester.semester_number,
            Semester.academic_year,
            func.count(Question.question_id).label("count"),
        )
        .join(ExamPaper, ExamPaper.semester_id == Semester.semester_id)
        .join(PaperQuestion, PaperQuestion.paper_id == ExamPaper.paper_id)
        .join(Question, Question.question_id == PaperQuestion.question_id)
        .group_by(Semester.semester_number, Semester.academic_year)
        .order_by(Semester.semester_number)
    )

    if subject_id is not None:
        question_type_stmt = question_type_stmt.where(ExamPaper.subject_id == subject_id)
        topic_stmt = topic_stmt.join(Question, Question.question_id == QuestionTopic.question_id).join(
            PaperQuestion,
            PaperQuestion.question_id == Question.question_id,
        ).join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id).where(ExamPaper.subject_id == subject_id)
        semester_stmt = semester_stmt.where(ExamPaper.subject_id == subject_id)
    if semester_id is not None:
        question_type_stmt = question_type_stmt.where(ExamPaper.semester_id == semester_id)
        topic_stmt = topic_stmt.join(Question, Question.question_id == QuestionTopic.question_id).join(
            PaperQuestion,
            PaperQuestion.question_id == Question.question_id,
        ).join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id).where(ExamPaper.semester_id == semester_id)
        semester_stmt = semester_stmt.where(ExamPaper.semester_id == semester_id)
    if exam_type:
        question_type_stmt = question_type_stmt.where(ExamPaper.exam_type == exam_type)
        topic_stmt = topic_stmt.join(Question, Question.question_id == QuestionTopic.question_id).join(
            PaperQuestion,
            PaperQuestion.question_id == Question.question_id,
        ).join(ExamPaper, ExamPaper.paper_id == PaperQuestion.paper_id).where(ExamPaper.exam_type == exam_type)
        semester_stmt = semester_stmt.where(ExamPaper.exam_type == exam_type)

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
