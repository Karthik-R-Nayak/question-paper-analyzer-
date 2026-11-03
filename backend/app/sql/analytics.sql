-- Production analytics used by the API; all filters are bound parameters.

-- name: overview_totals
WITH question_scope AS (
    SELECT pq.question_id, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT
    (SELECT COUNT(*)
     FROM exam_paper AS ep
     WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
       AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
       AND (:exam_type IS NULL OR ep.exam_type = :exam_type)) AS papers,
    (SELECT COUNT(*) FROM question_scope) AS questions,
    (SELECT COUNT(*) FROM subject) AS subjects,
    (SELECT COUNT(*) FROM semester) AS semesters;

-- name: overview_question_types
WITH question_scope AS (
    SELECT pq.question_id, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT qt.type_name, COUNT(qs.question_id) AS count
FROM question_type AS qt
JOIN question AS q ON q.type_id = qt.type_id
JOIN question_scope AS qs ON qs.question_id = q.question_id
GROUP BY qt.type_name
ORDER BY COUNT(qs.question_id) DESC, qt.type_name;

-- name: overview_topics
WITH question_scope AS (
    SELECT pq.question_id, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT t.topic_name, COUNT(qs.question_id) AS count
FROM topic AS t
JOIN question_topic AS qt ON qt.topic_id = t.topic_id
JOIN question_scope AS qs ON qs.question_id = qt.question_id
GROUP BY t.topic_name
ORDER BY COUNT(qs.question_id) DESC, t.topic_name;

-- name: overview_semesters
WITH question_scope AS (
    SELECT pq.question_id, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT sem.semester_number, sem.academic_year, COUNT(qs.question_id) AS count
FROM semester AS sem
JOIN question_scope AS qs ON qs.semester_id = sem.semester_id
GROUP BY sem.semester_number, sem.academic_year
ORDER BY sem.semester_number;

-- name: compare_subject_semesters
SELECT s.subject_name, sem.semester_number, sem.academic_year,
       COUNT(q.question_id) AS question_count, SUM(pq.marks) AS total_marks
FROM subject AS s
JOIN exam_paper AS ep ON ep.subject_id = s.subject_id
JOIN semester AS sem ON sem.semester_id = ep.semester_id
JOIN paper_question AS pq ON pq.paper_id = ep.paper_id
JOIN question AS q ON q.question_id = pq.question_id
WHERE (:subject_id IS NULL OR s.subject_id = :subject_id)
GROUP BY s.subject_name, sem.semester_number, sem.academic_year
ORDER BY sem.semester_number;

-- name: pattern_unit_weightage
WITH question_scope AS (
    SELECT pq.paper_id, pq.question_id, pq.marks, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT s.subject_name, u.unit_name, SUM(qs.marks) AS total_marks
FROM question_scope AS qs
JOIN question_topic AS qt ON qt.question_id = qs.question_id
JOIN topic AS t ON t.topic_id = qt.topic_id
JOIN unit AS u ON u.unit_id = t.unit_id
JOIN subject AS s ON s.subject_id = u.subject_id
WHERE (:subject_id IS NULL OR s.subject_id = :subject_id)
GROUP BY s.subject_name, u.unit_name
ORDER BY SUM(qs.marks) DESC, u.unit_name;

-- name: pattern_topic_frequency
WITH question_scope AS (
    SELECT pq.paper_id, pq.question_id, pq.marks, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT s.subject_name, t.topic_name,
       COUNT(qs.question_id) AS frequency,
       SUM(qs.marks) AS total_marks,
       COUNT(DISTINCT qs.paper_id) AS paper_count
FROM question_scope AS qs
JOIN question_topic AS qt ON qt.question_id = qs.question_id
JOIN topic AS t ON t.topic_id = qt.topic_id
JOIN unit AS u ON u.unit_id = t.unit_id
JOIN subject AS s ON s.subject_id = u.subject_id
GROUP BY s.subject_name, t.topic_name
ORDER BY COUNT(qs.question_id) DESC, t.topic_name;

-- name: pattern_question_types
WITH question_scope AS (
    SELECT pq.paper_id, pq.question_id, pq.marks, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT qt.type_name, COUNT(qs.question_id) AS count, SUM(qs.marks) AS total_marks
FROM question_type AS qt
JOIN question AS q ON q.type_id = qt.type_id
JOIN question_scope AS qs ON qs.question_id = q.question_id
GROUP BY qt.type_name
ORDER BY COUNT(qs.question_id) DESC, qt.type_name;

-- name: pattern_recurring_concepts
WITH question_scope AS (
    SELECT pq.paper_id, pq.question_id, pq.marks, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT t.topic_name, COUNT(qs.question_id) AS frequency, SUM(qs.marks) AS total_marks
FROM topic AS t
JOIN question_topic AS qt ON qt.topic_id = t.topic_id
JOIN question_scope AS qs ON qs.question_id = qt.question_id
GROUP BY t.topic_name
ORDER BY COUNT(qs.question_id) DESC, t.topic_name;

-- name: pattern_semester_trends
WITH question_scope AS (
    SELECT pq.paper_id, pq.question_id, pq.marks, ep.subject_id, ep.semester_id, ep.exam_type
    FROM paper_question AS pq
    JOIN exam_paper AS ep ON ep.paper_id = pq.paper_id
    WHERE (:subject_id IS NULL OR ep.subject_id = :subject_id)
      AND (:semester_id IS NULL OR ep.semester_id = :semester_id)
      AND (:exam_type IS NULL OR ep.exam_type = :exam_type)
)
SELECT s.subject_name, sem.semester_number, sem.academic_year,
       COUNT(qs.question_id) AS question_count, SUM(qs.marks) AS total_marks
FROM question_scope AS qs
JOIN subject AS s ON s.subject_id = qs.subject_id
JOIN semester AS sem ON sem.semester_id = qs.semester_id
GROUP BY s.subject_name, sem.semester_number, sem.academic_year
ORDER BY sem.semester_number, sem.academic_year;

-- DEMONSTRATION QUERIES (commented out; not called by application endpoints).
-- These illustrate SQL patterns using the project's actual schema.
--
-- Aggregate example with INNER/LEFT JOIN, GROUP BY, HAVING, COUNT, SUM, AVG,
-- MIN, MAX, and CASE:
-- SELECT s.subject_name, sem.semester_number, ep.exam_type,
--        COUNT(pq.question_id) AS question_count,
--        SUM(pq.marks) AS total_marks,
--        AVG(pq.marks) AS average_question_marks,
--        MIN(pq.marks) AS minimum_question_marks,
--        MAX(pq.marks) AS maximum_question_marks,
--        CASE WHEN COUNT(pq.question_id) >= 10 THEN 'high volume'
--             ELSE 'low volume' END AS paper_volume
-- FROM subject AS s
-- INNER JOIN exam_paper AS ep ON ep.subject_id = s.subject_id
-- INNER JOIN semester AS sem ON sem.semester_id = ep.semester_id
-- LEFT JOIN paper_question AS pq ON pq.paper_id = ep.paper_id
-- GROUP BY s.subject_name, sem.semester_number, ep.exam_type
-- HAVING COUNT(pq.question_id) > 0;
--
-- Nested and correlated subquery examples, including EXISTS and NOT EXISTS:
-- SELECT s.subject_name
-- FROM subject AS s
-- WHERE EXISTS (
--     SELECT 1 FROM exam_paper AS ep
--     WHERE ep.subject_id = s.subject_id
--       AND ep.total_marks > (
--           SELECT AVG(ep2.total_marks) FROM exam_paper AS ep2
--       )
-- )
-- AND NOT EXISTS (
--     SELECT 1 FROM unit AS u
--     WHERE u.subject_id = s.subject_id
--       AND NOT EXISTS (
--           SELECT 1 FROM topic AS t WHERE t.unit_id = u.unit_id
--       )
-- );
--
-- CTE and window-function example with subject/semester performance ranking:
-- WITH semester_performance AS (
--     SELECT s.subject_name, sem.semester_number, sem.academic_year,
--            COUNT(pq.question_id) AS question_count,
--            SUM(pq.marks) AS total_marks
--     FROM subject AS s
--     JOIN exam_paper AS ep ON ep.subject_id = s.subject_id
--     JOIN semester AS sem ON sem.semester_id = ep.semester_id
--     JOIN paper_question AS pq ON pq.paper_id = ep.paper_id
--     GROUP BY s.subject_name, sem.semester_number, sem.academic_year
-- )
-- SELECT subject_name, semester_number, academic_year, question_count,
--        total_marks,
--        RANK() OVER (PARTITION BY semester_number ORDER BY total_marks DESC) AS rank,
--        DENSE_RANK() OVER (PARTITION BY semester_number ORDER BY total_marks DESC) AS dense_rank,
--        ROW_NUMBER() OVER (PARTITION BY subject_name ORDER BY semester_number) AS semester_row
-- FROM semester_performance;
