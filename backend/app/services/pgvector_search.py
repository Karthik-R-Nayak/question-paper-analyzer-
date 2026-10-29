import json
import os
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_database_engine
from app.models import Question

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - optional pgvector dependency
    Vector = None


def is_postgres_enabled() -> bool:
    url = (os.getenv("DATABASE_URL") or "").lower()
    return url.startswith("postgres") or url.startswith("postgresql")


def ensure_pgvector_extension(session: Session) -> None:
    if not is_postgres_enabled():
        return
    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    session.commit()


def get_embedding_dimensions() -> int:
    return 384


def model_encode_text(text: str) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embedding = model.encode(text, normalize_embeddings=True)
        return [float(value) for value in embedding]
    except Exception:
        tokens = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
        if not tokens:
            return [0.0] * get_embedding_dimensions()

        values = [0.0] * get_embedding_dimensions()
        for token in tokens:
            idx = abs(hash(token)) % get_embedding_dimensions()
            values[idx] += 1.0

        norm = sum(v * v for v in values) ** 0.5
        if norm:
            values = [v / norm for v in values]
        return values


def upsert_question_embedding(session: Session, question_id: int, question_text: str) -> dict[str, Any]:
    embedding = model_encode_text(question_text)

    if is_postgres_enabled():
        ensure_pgvector_extension(session)
        result = session.execute(
            text(
                "INSERT INTO question_embedding (question_id, embedding) VALUES (:question_id, :embedding) "
                "ON CONFLICT (question_id) DO UPDATE SET embedding = EXCLUDED.embedding"
            ),
            {"question_id": question_id, "embedding": embedding},
        )
        session.commit()
        return {"question_id": question_id, "updated": result.rowcount or 0}

    session.execute(
        text(
            "INSERT OR REPLACE INTO question_embedding (question_id, embedding) VALUES (:question_id, :embedding)"
        ),
        {"question_id": question_id, "embedding": json.dumps(embedding)},
    )
    session.commit()
    return {"question_id": question_id, "updated": 1}


def similar_questions(session: Session, query: str, limit: int = 5):
    query_embedding = model_encode_text(query)

    if is_postgres_enabled():
        ensure_pgvector_extension(session)
        rows = session.execute(
            text(
                "SELECT q.question_id, q.question_text, 1 - (qe.embedding <=> :query_embedding) AS similarity "
                "FROM question q JOIN question_embedding qe ON qe.question_id = q.question_id "
                "ORDER BY qe.embedding <=> :query_embedding LIMIT :limit"
            ),
            {"query_embedding": query_embedding, "limit": limit},
        ).all()
        return [{
            "question_id": row.question_id,
            "question_text": row.question_text,
            "similarity_score": round(float(row.similarity), 4),
        } for row in rows]

    rows = session.execute(
        text("SELECT question_id, embedding FROM question_embedding")
    ).all()
    scored = []
    for row in rows:
        stored = json.loads(row.embedding)
        score = cosine_similarity(query_embedding, stored)
        scored.append({
            "question_id": row.question_id,
            "question_text": session.get(Question, row.question_id).question_text,
            "score": score,
        })

    scored.sort(key=lambda item: item["score"], reverse=True)
    return [{
        "question_id": item["question_id"],
        "question_text": item["question_text"],
        "similarity_score": round(float(item["score"]), 4),
    } for item in scored[:limit]]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    min_len = min(len(left), len(right))
    left = left[:min_len]
    right = right[:min_len]
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
