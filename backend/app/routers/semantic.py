from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.pgvector_search import similar_questions, upsert_question_embedding
from app.sql_loader import execute_sql
from app.security import require_user

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic search"])


@router.post("/index", dependencies=[Depends(require_user)])
def index_questions(session: Session = Depends(get_session)):
    rows = execute_sql(session, "semantics.sql", "index_questions").all()
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
