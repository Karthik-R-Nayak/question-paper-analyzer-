# question-paper-analyzer-
DBMS PROJECT USING VECTORS TO IDENTIFY SIMILARITIES IN PAPERS
title="Historical Examination Pattern Analysis System"
Abstract
Students often rely on previous question papers to understand examination patterns, identify important topics, and plan their preparation. However, manually analyzing multiple question papers to determine syllabus-wise weightage, frequently repeated topics, and patterns in question types can be time-consuming and inconsistent. This project proposes a Historical Examination Pattern Analysis System that organizes and analyzes previous question papers to provide students with meaningful insights into how a subject has historically been assessed.

The system stores question papers along with information such as subjects, units, topics, marks, question types, and semesters. It uses a relational database to manage structured academic data and a vector database to identify semantically similar questions even when their wording differs. The system analyzes historical data to determine unit-wise syllabus weightage, topic frequency, question-type distribution, recurring concepts, and changes in examination patterns across semesters. A web-based interface allows students to search questions, explore subject-wise statistics, compare examination patterns, and view historical trends.

The system is intended to provide evidence-based examination insights rather than predict or guarantee future questions, helping students make more informed study decisions based on historical patterns.
<img width="903" height="1310" alt="image" src="https://github.com/user-attachments/assets/29481e40-4abe-4578-8a8d-612d9420c7b4" />
<img width="1673" height="660" alt="image" src="https://github.com/user-attachments/assets/cab50a28-cad9-473b-9292-3a394fe498ca" />

## Suggested project modules

Build the first version as a **modular monolith**: one application with clear
module boundaries. This keeps deployment and development simple while making
each part easier to test and maintain.

| Module | Responsibilities |
| --- | --- |
| Paper ingestion | Add an exam paper, enter or extract its questions, and associate it with a subject, semester, and exam type. |
| Academic catalog | Manage subjects, semesters, units, topics, and question types. |
| Question and paper management | Store questions and their marks/question numbers on papers; connect questions to one or more syllabus topics. |
| Database access | Own relational persistence, transactions, validation, and queries for the tables in `exam_pattern_ddl.sql`. |
| Semantic search | Create embeddings for question text, store them in a vector index, and retrieve semantically similar questions. |
| Pattern analytics | Calculate topic and unit weightage, topic frequency, question-type distribution, recurring concepts, and trends across semesters. |
| API and user interface | Expose the application features and let students search questions, explore statistics, and compare historical patterns. |

### Suggested boundaries and data flow

1. Paper ingestion validates a paper and its questions, then asks the question/paper and academic catalog modules to save the structured data.
2. After a question is saved, semantic search generates and stores its embedding. Keep the relational `question_id` as the stable link to the vector record; do not treat a vector-store ID as the question itself.
3. Pattern analytics reads the relational data for counts and marks, and can use semantic search to group differently worded questions about similar concepts.
4. The API coordinates requests from the UI and calls the relevant modules. The UI should not access either database directly.

Keep the relational database as the source of truth for papers, marks, subjects,
and syllabus mappings. Treat embeddings as derived data that can be regenerated
from saved question text.

### Recommended starter stack

- **Backend/API:** Python with FastAPI
- **Relational and vector storage:** PostgreSQL with the `pgvector` extension
- **Embeddings:** a sentence-transformer model, wrapped behind the semantic search module
- **Frontend:** React with TypeScript

Using PostgreSQL with `pgvector` keeps structured records and vector search in
one database for an initial implementation. The current
`exam_pattern_ddl.sql` is PostgreSQL-compatible. Create and connect to the
`exam_pattern` database before running it.

### First module: paper ingestion

The initial FastAPI backend accepts an exam paper and its questions in one
request. It validates the subject, semester, question types, and topic mappings,
then saves the paper and all related records in one transaction. Referenced
subjects, semesters, question types, units, and topics must already exist;
catalog management is a separate module. A question's topics must belong to the
paper's subject. Embeddings are intentionally not generated during ingestion;
semantic search can add them later as derived data.

### Second module: academic catalog

The academic catalog API manages subjects, semesters, units, topics, and
question types under `/api/v1/catalog`. Each catalog resource supports
create, list, get, and replace operations, plus deletion. Updates use `PUT`.
Unique-key and relational conflicts return `409`; missing records return `404`.
Deletes follow the foreign-key behavior in `exam_pattern_ddl.sql`, so deleting
a subject, semester, unit, or topic can cascade to related historical records.
A question type cannot be deleted while questions use it.

### Fourth module: database access

The database layer owns SQLAlchemy engine and session creation. Set
`DATABASE_URL` to choose the database; SQLite connections enforce the schema's
foreign-key and cascade rules just like PostgreSQL. The API does not create the
schema automatically: apply `exam_pattern_ddl.sql` to PostgreSQL before
starting the application.

To run the API locally:

1. Create a PostgreSQL database named `exam_pattern` and run
   `exam_pattern_ddl.sql` against it.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Set `DATABASE_URL` using the format in `backend/.env.example`.
4. Start the API from the `backend` directory with
   `uvicorn app.main:app --reload`.
5. Open `/docs` on the local server to try the paper-ingestion and catalog APIs.

Install `backend/requirements-dev.txt` and run `pytest` from the `backend`
directory to execute the tests using an in-memory SQLite database.
