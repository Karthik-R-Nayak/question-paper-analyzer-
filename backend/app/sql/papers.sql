-- Production paper and paper-question operations; values use named parameters.

-- name: list_papers
SELECT ep.paper_id, ep.subject_id, ep.semester_id, ep.exam_type, ep.total_marks,
       s.subject_name, sem.semester_number, sem.academic_year
FROM exam_paper AS ep
JOIN subject AS s ON s.subject_id = ep.subject_id
JOIN semester AS sem ON sem.semester_id = ep.semester_id
ORDER BY ep.paper_id;

-- name: get_paper
SELECT ep.paper_id, ep.subject_id, ep.semester_id, ep.exam_type, ep.total_marks,
       s.subject_name, sem.semester_number, sem.academic_year
FROM exam_paper AS ep
JOIN subject AS s ON s.subject_id = ep.subject_id
JOIN semester AS sem ON sem.semester_id = ep.semester_id
WHERE ep.paper_id = :paper_id;

-- name: paper_question_details
SELECT ep.paper_id, ep.subject_id, ep.semester_id, ep.exam_type, ep.total_marks,
       s.subject_name, sem.semester_number, sem.academic_year,
       pq.question_id, pq.question_number, pq.marks,
       q.question_text, q.type_id AS question_type_id
FROM exam_paper AS ep
JOIN subject AS s ON s.subject_id = ep.subject_id
JOIN semester AS sem ON sem.semester_id = ep.semester_id
LEFT JOIN paper_question AS pq ON pq.paper_id = ep.paper_id
LEFT JOIN question AS q ON q.question_id = pq.question_id
WHERE ep.paper_id = :paper_id
ORDER BY pq.question_number, pq.question_id;

-- name: paper_question_topic_ids
SELECT question_id, topic_id
FROM question_topic
WHERE question_id IN :question_ids
ORDER BY topic_id;

-- name: topic_subjects_for_paper
SELECT t.topic_id, u.subject_id
FROM topic AS t
JOIN unit AS u ON u.unit_id = t.unit_id
WHERE t.topic_id IN :topic_ids;

-- name: insert_paper
INSERT INTO exam_paper (subject_id, semester_id, exam_type, total_marks)
VALUES (:subject_id, :semester_id, :exam_type, :total_marks)
RETURNING paper_id;

-- name: update_paper
UPDATE exam_paper
SET subject_id = :subject_id,
    semester_id = :semester_id,
    exam_type = :exam_type,
    total_marks = :total_marks
WHERE paper_id = :paper_id;

-- name: delete_paper
DELETE FROM exam_paper
WHERE paper_id = :paper_id;

-- name: paper_question_ids
SELECT question_id
FROM paper_question
WHERE paper_id = :paper_id;

-- name: paper_question_exists
SELECT question_id
FROM paper_question
WHERE paper_id = :paper_id AND question_id = :question_id;

-- name: paper_question_ids_in_papers
SELECT question_id
FROM paper_question
WHERE question_id IN :question_ids;

-- name: insert_paper_question
INSERT INTO paper_question (paper_id, question_id, question_number, marks)
VALUES (:paper_id, :question_id, :question_number, :marks);

-- name: update_paper_question
UPDATE paper_question
SET question_number = :question_number,
    marks = :marks
WHERE paper_id = :paper_id AND question_id = :question_id;

-- name: delete_paper_questions
DELETE FROM paper_question
WHERE paper_id = :paper_id;

-- name: delete_paper_question
DELETE FROM paper_question
WHERE paper_id = :paper_id AND question_id = :question_id;

-- name: question_number_conflict
SELECT question_id
FROM paper_question
WHERE paper_id = :paper_id
  AND question_number = :question_number
  AND (CAST(:exclude_question_id AS INTEGER) IS NULL
       OR question_id <> CAST(:exclude_question_id AS INTEGER))
LIMIT 1;
