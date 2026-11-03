-- Production semantic-search operations.

-- name: upsert_embedding_postgresql
INSERT INTO question_embedding (question_id, embedding)
VALUES (:question_id, :embedding)
ON CONFLICT (question_id) DO UPDATE
SET embedding = EXCLUDED.embedding;

-- name: upsert_embedding_sqlite
INSERT OR REPLACE INTO question_embedding (question_id, embedding)
VALUES (:question_id, :embedding);

-- name: delete_question_embedding
DELETE FROM question_embedding
WHERE question_id = :question_id;

-- name: index_questions
SELECT question_id, question_text
FROM question
ORDER BY question_id;

-- name: similar_questions_postgresql
SELECT
    q.question_id,
    q.question_text,
    1 - (qe.embedding <=> CAST(:query_embedding AS vector)) AS similarity
FROM question AS q
JOIN question_embedding AS qe ON qe.question_id = q.question_id
ORDER BY qe.embedding <=> CAST(:query_embedding AS vector)
LIMIT :limit;

-- name: similar_questions_sqlite
SELECT qe.question_id, q.question_text, qe.embedding
FROM question_embedding AS qe
JOIN question AS q ON q.question_id = qe.question_id;
