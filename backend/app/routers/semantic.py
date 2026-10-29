from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Question
from app.services.pgvector_search import similar_questions, upsert_question_embedding

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic search"])


@router.post("/index")
def index_questions(session: Session = Depends(get_session)):
    rows = session.query(Question.question_id, Question.question_text).all()
    for question_id, question_text in rows:
        upsert_question_embedding(session, question_id, question_text)
    return {"indexed_count": len(rows)}


@router.get("/similar")
def similar_questions_endpoint(
    q: str = Query(..., min_length=1, description="Question text or concept to search."),
    limit: int = Query(5, ge=1, le=20),
    session: Session = Depends(get_session),
):
    return similar_questions(session, q, limit=limit)
