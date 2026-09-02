-- Historical Examination Pattern Analysis System
-- DDL Statements 
CREATE DATABASE exam_pattern;
USE exam_pattern;


CREATE TABLE SUBJECT (
    subject_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code    VARCHAR(20)  NOT NULL UNIQUE,
    subject_name    VARCHAR(100) NOT NULL,
    department      VARCHAR(100)
);


CREATE TABLE SEMESTER (
    semester_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_number INTEGER NOT NULL CHECK (semester_number BETWEEN 1 AND 8),
    academic_year   VARCHAR(9)  NOT NULL,          -- e.g. '2023-2024'
    UNIQUE (semester_number, academic_year)
);


CREATE TABLE UNIT (
    unit_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id      INTEGER NOT NULL,
    unit_number     INTEGER NOT NULL,
    unit_name       VARCHAR(150) NOT NULL,
    UNIQUE (subject_id, unit_number),
    FOREIGN KEY (subject_id) REFERENCES SUBJECT(subject_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE TOPIC (
    topic_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id         INTEGER NOT NULL,
    topic_name      VARCHAR(150) NOT NULL,
    FOREIGN KEY (unit_id) REFERENCES UNIT(unit_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE QUESTION_TYPE (
    type_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name       VARCHAR(50) NOT NULL UNIQUE     -- MCQ, Short Answer, Long Answer, Numerical...
);



CREATE TABLE EXAM_PAPER (
    paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id      INTEGER NOT NULL,
    semester_id     INTEGER NOT NULL,
    exam_type       VARCHAR(20) NOT NULL CHECK (exam_type IN ('Internal','Mid','End','Supplementary')),
    total_marks     INTEGER NOT NULL CHECK (total_marks > 0),
    FOREIGN KEY (subject_id)  REFERENCES SUBJECT(subject_id)   ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES SEMESTER(semester_id) ON DELETE CASCADE ON UPDATE CASCADE
    
);


CREATE TABLE QUESTION (
    question_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id         INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    vector_id       VARCHAR(100),                   -- pointer/handle into the external vector DB
    FOREIGN KEY (type_id) REFERENCES QUESTION_TYPE(type_id) ON DELETE RESTRICT ON UPDATE CASCADE
);


CREATE TABLE PAPER_QUESTION (
    paper_id        INTEGER NOT NULL,
    question_id     INTEGER NOT NULL,
    question_number VARCHAR(10) NOT NULL,           -- e.g. '1a', '5' (as it appeared in this paper)
    marks           INTEGER NOT NULL CHECK (marks > 0),
    PRIMARY KEY (paper_id, question_id),
    FOREIGN KEY (paper_id)    REFERENCES EXAM_PAPER(paper_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (question_id) REFERENCES QUESTION(question_id) ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE QUESTION_TOPIC (
    question_id     INTEGER NOT NULL,
    topic_id        INTEGER NOT NULL,
    PRIMARY KEY (question_id, topic_id),
    FOREIGN KEY (question_id) REFERENCES QUESTION(question_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (topic_id)    REFERENCES TOPIC(topic_id)       ON DELETE CASCADE ON UPDATE CASCADE
);



