import math
from typing import Iterable

from app.services.pgvector_search import model_encode_text
from app.sql_loader import execute_sql


class VectorIndex:
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self.vectors: dict[int, list[float]] = {}
        self.text_by_question: dict[int, str] = {}

    def encode(self, text: str) -> list[float]:
        cleaned = (text or "").strip()
        if not cleaned:
            return [0.0] * self.dimensions

        return model_encode_text(cleaned)

    def upsert(self, question_id: int, text: str) -> list[float]:
        embedding = self.encode(text)
        self.vectors[question_id] = embedding
        self.text_by_question[question_id] = text
        return embedding

    def search(self, query: str, candidate_ids: Iterable[int] | None = None, top_k: int = 5):
        query_embedding = self.encode(query)
        candidate_set = set(candidate_ids) if candidate_ids is not None else set(self.vectors)

        scored: list[dict] = []
        for question_id in candidate_set:
            if question_id not in self.vectors:
                continue
            stored = self.vectors[question_id]
            score = cosine_similarity(query_embedding, stored)
            scored.append({
                "question_id": question_id,
                "question_text": self.text_by_question.get(question_id, ""),
                "score": score,
            })

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]


_semantic_index = VectorIndex()


def get_vector_index() -> VectorIndex:
    return _semantic_index


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) != len(right):
        common = min(len(left), len(right))
        left = left[:common]
        right = right[:common]

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def index_all_questions(session) -> int:
    index = get_vector_index()
    rows = execute_sql(session, "semantics.sql", "index_questions").all()
    for question_id, question_text in rows:
        index.upsert(question_id, question_text)
    return len(rows)
