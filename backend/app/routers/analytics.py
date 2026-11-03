from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.sql_loader import execute_sql

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
    rows = execute_sql(
        session,
        "questions.sql",
        "search_questions",
        {
            "search_pattern": f"%{q.strip().lower()}%" if q.strip() else None,
            "subject_id": subject_id,
            "semester_id": semester_id,
            "exam_type": exam_type,
            "limit": limit,
        },
    ).all()
    if not rows:
        return []

    question_ids = [row.question_id for row in rows]
    topic_rows = execute_sql(
        session,
        "questions.sql",
        "question_topics_for_questions",
        {"question_ids": question_ids},
        expanding_parameters=("question_ids",),
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
    filters = {
        "subject_id": subject_id,
        "semester_id": semester_id,
        "exam_type": exam_type,
    }
    totals = execute_sql(
        session, "analytics.sql", "overview_totals", filters
    ).one()

    return {
        "totals": {
            "papers": totals.papers or 0,
            "questions": totals.questions or 0,
            "subjects": totals.subjects or 0,
            "semesters": totals.semesters or 0,
        },
        "question_types": [
            {"type_name": row.type_name, "count": row.count}
            for row in execute_sql(
                session, "analytics.sql", "overview_question_types", filters
            ).all()
        ],
        "topics": [
            {"topic_name": row.topic_name, "count": row.count}
            for row in execute_sql(
                session, "analytics.sql", "overview_topics", filters
            ).all()
        ],
        "semesters": [
            {
                "semester_number": row.semester_number,
                "academic_year": row.academic_year,
                "count": row.count,
            }
            for row in execute_sql(
                session, "analytics.sql", "overview_semesters", filters
            ).all()
        ],
    }


@router.get("/analytics/compare")
def compare_patterns(
    subject_id: int | None = None,
    session: Session = Depends(get_session),
):
    rows = execute_sql(
        session,
        "analytics.sql",
        "compare_subject_semesters",
        {"subject_id": subject_id},
    ).all()
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
    filters = {
        "subject_id": subject_id,
        "semester_id": semester_id,
        "exam_type": exam_type,
    }
    total_marks_for_units = execute_sql(
        session, "analytics.sql", "pattern_unit_weightage", filters
    ).all()
    topic_rows = execute_sql(
        session, "analytics.sql", "pattern_topic_frequency", filters
    ).all()
    type_rows = execute_sql(
        session, "analytics.sql", "pattern_question_types", filters
    ).all()
    recurring_rows = execute_sql(
        session, "analytics.sql", "pattern_recurring_concepts", filters
    ).all()
    trends = execute_sql(
        session, "analytics.sql", "pattern_semester_trends", filters
    ).all()

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
