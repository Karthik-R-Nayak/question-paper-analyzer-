-- Production question operations; values are supplied through named parameters.

-- name: search_questions
SELECT
    q.question_id,
    q.question_text,
    q.type_id,
    qt.type_name AS question_type,
    pq.question_number,
    pq.marks,
    ep.paper_id,
    ep.exam_type,
    s.subject_id,
    s.subject_name,
    sem.semester_id,
    sem.semester_number,
    sem.academic_year
FROM question AS q
JOIN paper_question AS pq ON pq.question_id = q.question_id
JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
JOIN subject AS s ON s.subject_id = ep.subject_id
JOIN semester AS sem ON sem.semester_id = ep.semester_id
JOIN question_type AS qt ON qt.type_id = q.type_id
WHERE (CAST(:search_pattern AS TEXT) IS NULL
       OR LOWER(q.question_text) LIKE CAST(:search_pattern AS TEXT))
  AND (CAST(:subject_id AS INTEGER) IS NULL
       OR s.subject_id = CAST(:subject_id AS INTEGER))
  AND (CAST(:semester_id AS INTEGER) IS NULL
       OR sem.semester_id = CAST(:semester_id AS INTEGER))
  AND (CAST(:exam_type AS VARCHAR(20)) IS NULL
       OR ep.exam_type = CAST(:exam_type AS VARCHAR(20)))
ORDER BY q.question_id DESC
LIMIT :limit;

-- name: question_topics_for_questions
SELECT qt.question_id, t.topic_name
FROM question_topic AS qt
JOIN topic AS t ON t.topic_id = qt.topic_id
WHERE qt.question_id IN :question_ids
ORDER BY t.topic_name;

-- name: insert_question
INSERT INTO question (type_id, question_text)
VALUES (:type_id, :question_text)
RETURNING question_id;

-- name: update_question
UPDATE question
SET type_id = :type_id,
    question_text = :question_text
WHERE question_id = :question_id;

-- name: delete_question
DELETE FROM question
WHERE question_id = :question_id;

-- name: question_type_is_used
SELECT question_id
FROM question
WHERE type_id = :type_id
LIMIT 1;

-- name: insert_question_topic
INSERT INTO question_topic (question_id, topic_id)
VALUES (:question_id, :topic_id);

-- name: delete_question_topics
DELETE FROM question_topic
WHERE question_id = :question_id;
