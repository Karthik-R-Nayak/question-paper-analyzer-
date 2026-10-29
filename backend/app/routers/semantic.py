from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Question
from app.services.semantic_search import get_vector_index, index_all_questions

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic search"])


@router.post("/index")
def index_questions(session: Session = Depends(get_session)):
    count = index_all_questions(session)
    return {"indexed_count": count}


@router.get("/similar")
def similar_questions(
    q: str = Query(..., min_length=1, description="Question text or concept to search."),
    limit: int = Query(5, ge=1, le=20),
    session: Session = Depends(get_session),
):
    index = get_vector_index()

    rows = session.query(Question.question_id, Question.question_text).all()
    for question_id, question_text in rows:
        index.upsert(question_id, question_text)

    results = index.search(q, top_k=limit)
    if not results:
        return []

    return [{
        "question_id": item["question_id"],
        "question_text": item["question_text"],
        "similarity_score": round(float(item["score"]), 4),
    } for item in results]
