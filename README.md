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
| Database access | Own relational persistence, transactions, validation, and queries for the tables in `backend/app/sql/schema.sql`. |
| Semantic search | Create embeddings for question text, store them in a vector index, and retrieve semantically similar questions. |
| Pattern analytics | Calculate topic and unit weightage, topic frequency, question-type distribution, recurring concepts, and trends across semesters. |
| API and user interface | FastAPI exposes the application features; a Next.js frontend lets students search questions, explore statistics, and compare historical patterns. |

### Suggested boundaries and data flow

1. Paper ingestion validates a paper and its questions, then asks the question/paper and academic catalog modules to save the structured data.
2. When a question is saved or updated, semantic search generates and stores its embedding in the same transaction. Keep the relational `question_id` as the stable link to the vector record; do not treat a vector-store ID as the question itself.
3. Pattern analytics reads the relational data for counts and marks, and can use semantic search to group differently worded questions about similar concepts.
4. The API coordinates requests from the UI and calls the relevant modules. The UI should not access either database directly.

Keep the relational database as the source of truth for papers, marks, subjects,
and syllabus mappings. Treat embeddings as derived data that can be regenerated
from saved question text.

### Recommended starter stack

- **Backend/API:** Python with FastAPI
- **Relational and vector storage:** PostgreSQL with the `pgvector` extension
- **Embeddings:** a sentence-transformer model, wrapped behind the semantic search module
- **Frontend:** Next.js App Router with React and JavaScript (`frontend/`)

Using PostgreSQL with `pgvector` keeps structured records and vector search in
one database for an initial implementation. The current
`backend/app/sql/schema.sql` is the canonical PostgreSQL schema. Create and connect to the
`exam_pattern` database before running it.

### First module: paper ingestion

The initial FastAPI backend accepts an exam paper and its questions in one
request. It validates the subject, semester, question types, and topic mappings,
then saves the paper and all related records in one transaction. Referenced
subjects, semesters, question types, units, and topics must already exist;
catalog management is a separate module. A question's topics must belong to the
paper's subject. Embeddings are generated automatically during ingestion and
when question text is updated. The semantic indexing endpoint can be used to
backfill embeddings for questions saved before indexing was automatic.

### Second module: academic catalog

The academic catalog API manages subjects, semesters, units, topics, and
question types under `/api/v1/catalog`. Each catalog resource supports
create, list, get, and replace operations, plus deletion. Updates use `PUT`.
Unique-key and relational conflicts return `409`; missing records return `404`.
Deletes follow the foreign-key behavior in `backend/app/sql/schema.sql`, so deleting
a subject, semester, unit, or topic can cascade to related historical records.
A question type cannot be deleted while questions use it.

### Third module: question and paper management

The paper API under `/api/v1/papers` supports listing and retrieving papers,
replacing a paper and its complete question list with `PUT`, and deleting a
paper. Questions can also be added, replaced, and removed individually through
`/{paper_id}/questions`. Missing papers or paper-question associations return
`404`; duplicate question numbers within a paper return `409`. Question topic
mappings are validated against the paper's subject. Updating a question updates
the question record itself, so changes are visible anywhere that question is
referenced; removing a paper-question association preserves the question if
another paper still references it.

### User registration and login

Users can register and log in with a username and password. Usernames are
case-insensitively unique and must contain 3–32 characters; passwords must
contain at least 8 characters. Passwords are stored as scrypt hashes. Login
creates an opaque, revocable session in the database and sets an HttpOnly,
Secure, SameSite=Lax cookie that expires after seven days. Logout revokes the
current session.

Read-only search, analytics, semantic similarity, paper, and catalog endpoints
remain public. Paper, question, catalog, and semantic-index mutations require
an authenticated session. Set `SESSION_COOKIE_SECURE=false` only for local
development over plain HTTP; the default requires HTTPS.

### Fourth module: database access

The database layer owns SQLAlchemy engine and session creation. Set
`DATABASE_URL` to choose the database; SQLite connections enforce the schema's
foreign-key and cascade rules just like PostgreSQL. On startup, the API creates
missing tables automatically for SQLite databases. For PostgreSQL, apply
`backend/app/sql/schema.sql` before starting the application.

To run the API locally:

1. Install PostgreSQL and the pgvector server extension. From the repository
   root, create the database, enable pgvector in that database, then apply the
   schema:

   ```sh
   createdb exam_pattern
   psql -d exam_pattern -f backend/app/sql/schema.sql
   ```

   The schema enables pgvector and creates only missing tables/indexes; it does
   not alter or drop existing objects. `QUESTION_EMBEDDING.embedding` uses
   PostgreSQL `VECTOR(384)`.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Set `DATABASE_URL` to
   `postgresql+psycopg://USER:PASSWORD@localhost:5432/exam_pattern` in
   `backend/.env`, replacing the role and password with your local PostgreSQL
   credentials. For local HTTP development, set `SESSION_COOKIE_SECURE=false`
   in the same file.
4. Start the API from the `backend` directory with
   `uvicorn app.main:app --reload`.
5. Open `/docs` on the local server to try the paper-ingestion and catalog APIs.

Install `backend/requirements-dev.txt` and run `pytest` from the `backend`
directory to execute the tests using an in-memory SQLite database.

### Consolidated SQL resources

Production SQL is organized by application functionality under
`backend/app/sql/`. The Python `app.sql_loader` reads named statements from
these files and executes them through SQLAlchemy `text()` with bound named
parameters. SQLAlchemy continues to own connections, sessions, transactions,
and ORM operations. SQLite tests continue to create their schema from the
SQLAlchemy models; PostgreSQL setup uses `schema.sql`.

```text
backend/app/sql/
├── schema.sql      # PostgreSQL tables, constraints, indexes, and pgvector
├── questions.sql   # Question CRUD, search, filters, and topic joins
├── papers.sql      # Paper CRUD, paper-question relations, retrieval joins
├── analytics.sql   # Production analytics and commented SQL demonstrations
└── semantics.sql   # Embedding operations and semantic retrieval
```

In `analytics.sql`, statements marked as production are the ones called by the
API. Demonstration queries are commented out and are not loaded or executed.

## Next.js frontend

The Next.js App Router frontend is the user-facing application. It calls the
existing FastAPI REST API; PostgreSQL and pgvector remain behind FastAPI. The
original HTML/vanilla JavaScript UI remains available from the backend's `/`
route while the migration is in use.

```text
frontend/
├── app/
│   ├── globals.css
│   ├── layout.js
│   └── page.js
├── lib/
│   ├── api.js
│   └── api.test.js
├── .env.local.example
├── package-lock.json
├── next.config.mjs
└── package.json
```

### Configure and start both applications

1. Follow the PostgreSQL/pgvector setup above. In `backend/.env`, set
   `DATABASE_URL` to
   `postgresql+psycopg://USER:PASSWORD@localhost:5432/exam_pattern`.
2. For local HTTP development, set `SESSION_COOKIE_SECURE=false` in
   `backend/.env`. The default is secure cookies, which require HTTPS.
3. Configure the allowed browser origin in `backend/.env`:
   `FRONTEND_ORIGIN=http://localhost:3000`. FastAPI permits credentialed CORS
   requests from this single configured origin.
4. In a backend terminal:

   ```sh
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host localhost --port 8000
   ```

5. In another terminal, copy `frontend/.env.local.example` to
   `frontend/.env.local`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` if
   the API uses a different address. Then start Next.js:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

6. Open `http://localhost:3000`. The API can also be explored at
   `http://localhost:8000/docs`.

The frontend API client centralizes JSON/error handling and sends requests with
`credentials: "include"` so the browser stores and returns FastAPI's HttpOnly
session cookie. Keep the frontend and API on `localhost` during HTTP
development; do not put database credentials or session secrets in
`NEXT_PUBLIC_*` variables.

### Migrated frontend features

- Overview totals, question-type/topic charts, semester comparison, unit
  weightage, and recurring concepts use the existing analytics APIs. Subject,
  semester, and exam-type filters apply to overview and pattern analytics; the
  existing semester-comparison endpoint supports only a subject filter.
- Question search uses `/api/v1/search/questions` with text and catalog filters.
- Semantic search uses `/api/v1/semantic/similar`, displays ranked similarity
  scores, and shows API errors such as HTTP 503 when the embedding model is
  unavailable.
- Login/register, current-session restoration, and logout use the existing
  cookie-backed `/api/v1/auth` endpoints.
- Paper creation (including multiple questions in one request), listing,
  editing, and deletion use the existing `/api/v1/papers` endpoints.

There is no CSV or file-upload endpoint in the current backend. Bulk question
entry is supported by submitting multiple questions as part of a paper JSON
request. No new import endpoint or database schema is introduced by this
frontend migration.

Frontend checks: `npm test` and `npm run build` from `frontend/`. Backend
checks: install `backend/requirements-dev.txt` and run `pytest` from `backend/`.
