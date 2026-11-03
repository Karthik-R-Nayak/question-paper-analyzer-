from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.pgvector_search import upsert_question_embedding
from app.sql_loader import execute_sql
from app.models import (
    QuestionType,
    Semester,
    Subject,
)
from app.schemas import PaperCreate, PaperQuestionCreate, PaperQuestionRead, PaperRead
from app.security import require_user

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])


def _require_paper(session: Session, paper_id: int):
    paper = execute_sql(
        session,
        "papers.sql",
        "get_paper",
        {"paper_id": paper_id},
    ).first()
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    return paper


def _require_existing(
    session: Session,
    model: type[Subject] | type[Semester] | type[QuestionType],
    identifier: int,
    label: str,
) -> None:
    if session.get(model, identifier) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown {label} id: {identifier}",
        )


def _validate_questions(
    session: Session,
    subject_id: int,
    questions: list[PaperQuestionCreate],
) -> None:
    type_ids = {question.question_type_id for question in questions}
    for type_id in type_ids:
        _require_existing(session, QuestionType, type_id, "question type")

    topic_ids = {topic_id for question in questions for topic_id in question.topic_ids}
    if not topic_ids:
        return

    topic_subjects = execute_sql(
        session,
        "papers.sql",
        "topic_subjects_for_paper",
        {"topic_ids": sorted(topic_ids)},
        expanding_parameters=("topic_ids",),
    ).all()
    subjects_by_topic = {topic_id: subject_id for topic_id, subject_id in topic_subjects}
    missing_topics = topic_ids - subjects_by_topic.keys()
    if missing_topics:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown topic id(s): {', '.join(map(str, sorted(missing_topics)))}",
        )
    unrelated_topics = {
        topic_id
        for topic_id, topic_subject_id in subjects_by_topic.items()
        if topic_subject_id != subject_id
    }
    if unrelated_topics:
        raise HTTPException(
            status_code=422,
            detail=(
                "Topic id(s) do not belong to the paper's subject: "
                f"{', '.join(map(str, sorted(unrelated_topics)))}"
            ),
        )


def _add_question(
    session: Session,
    paper_id: int,
    question_data: PaperQuestionCreate,
) -> PaperQuestionRead:
    question_id = execute_sql(
        session,
        "questions.sql",
        "insert_question",
        {
            "type_id": question_data.question_type_id,
            "question_text": question_data.question_text,
        },
    ).scalar_one()
    upsert_question_embedding(
        session,
        question_id,
        question_data.question_text,
        commit=False,
    )
    execute_sql(
        session,
        "papers.sql",
        "insert_paper_question",
        {
            "paper_id": paper_id,
            "question_id": question_id,
            "question_number": question_data.question_number,
            "marks": question_data.marks,
        },
    )
    for topic_id in question_data.topic_ids:
        execute_sql(
            session,
            "questions.sql",
            "insert_question_topic",
            {"question_id": question_id, "topic_id": topic_id},
        )
    return PaperQuestionRead(
        question_id=question_id,
        question_number=question_data.question_number,
        marks=question_data.marks,
        question_text=question_data.question_text,
        question_type_id=question_data.question_type_id,
        topic_ids=question_data.topic_ids,
    )


def _paper_read(session: Session, paper_id: int) -> PaperRead:
    rows = execute_sql(
        session,
        "papers.sql",
        "paper_question_details",
        {"paper_id": paper_id},
    ).all()
    first_row = rows[0]
    question_ids = [row.question_id for row in rows if row.question_id is not None]
    topic_rows = (
        execute_sql(
            session,
            "papers.sql",
            "paper_question_topic_ids",
            {"question_ids": question_ids},
            expanding_parameters=("question_ids",),
        ).all()
        if question_ids
        else []
    )
    topic_ids_by_question: dict[int, list[int]] = {}
    for question_id, topic_id in topic_rows:
        topic_ids_by_question.setdefault(question_id, []).append(topic_id)

    return PaperRead(
        paper_id=first_row.paper_id,
        subject_id=first_row.subject_id,
        semester_id=first_row.semester_id,
        exam_type=first_row.exam_type,
        total_marks=first_row.total_marks,
        questions=[
            PaperQuestionRead(
                question_id=row.question_id,
                question_number=row.question_number,
                marks=row.marks,
                question_text=row.question_text,
                question_type_id=row.question_type_id,
                topic_ids=topic_ids_by_question.get(row.question_id, []),
            )
            for row in rows
            if row.question_id is not None
        ],
    )


def _delete_orphaned_questions(session: Session, question_ids: set[int]) -> None:
    if not question_ids:
        return
    session.flush()
    remaining_ids = set(
        row.question_id
        for row in execute_sql(
            session,
            "papers.sql",
            "paper_question_ids_in_papers",
            {"question_ids": sorted(question_ids)},
            expanding_parameters=("question_ids",),
        ).all()
    )
    for question_id in question_ids - remaining_ids:
        execute_sql(
            session,
            "questions.sql",
            "delete_question_topics",
            {"question_id": question_id},
        )
        execute_sql(
            session,
            "semantics.sql",
            "delete_question_embedding",
            {"question_id": question_id},
        )
        execute_sql(
            session,
            "questions.sql",
            "delete_question",
            {"question_id": question_id},
        )


@router.post(
    "",
    response_model=PaperRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_user)],
)
def create_paper(payload: PaperCreate, session: Session = Depends(get_session)) -> PaperRead:
    question_numbers = [question.question_number for question in payload.questions]
    if len(question_numbers) != len(set(question_numbers)):
        raise HTTPException(
            status_code=422,
            detail="Question numbers must be unique within a paper.",
        )

    with session.begin():
        _require_existing(session, Subject, payload.subject_id, "subject")
        _require_existing(session, Semester, payload.semester_id, "semester")
        _validate_questions(session, payload.subject_id, payload.questions)

        paper_id = execute_sql(
            session,
            "papers.sql",
            "insert_paper",
            {
                "subject_id": payload.subject_id,
                "semester_id": payload.semester_id,
                "exam_type": payload.exam_type.value,
                "total_marks": payload.total_marks,
            },
        ).scalar_one()

        response_questions = [
            _add_question(session, paper_id, question_data)
            for question_data in payload.questions
        ]
        response = PaperRead(
            paper_id=paper_id,
            subject_id=payload.subject_id,
            semester_id=payload.semester_id,
            exam_type=payload.exam_type,
            total_marks=payload.total_marks,
            questions=response_questions,
        )

    return response


@router.get("", response_model=list[PaperRead])
def list_papers(session: Session = Depends(get_session)) -> list[PaperRead]:
    papers = execute_sql(session, "papers.sql", "list_papers").all()
    return [_paper_read(session, paper.paper_id) for paper in papers]


@router.get("/{paper_id}", response_model=PaperRead)
def get_paper(
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperRead:
    _require_paper(session, paper_id)
    return _paper_read(session, paper_id)


@router.put(
    "/{paper_id}",
    response_model=PaperRead,
    dependencies=[Depends(require_user)],
)
def update_paper(
    payload: PaperCreate,
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperRead:
    question_numbers = [question.question_number for question in payload.questions]
    if len(question_numbers) != len(set(question_numbers)):
        raise HTTPException(
            status_code=422,
            detail="Question numbers must be unique within a paper.",
        )

    with session.begin():
        _require_paper(session, paper_id)
        _require_existing(session, Subject, payload.subject_id, "subject")
        _require_existing(session, Semester, payload.semester_id, "semester")
        _validate_questions(session, payload.subject_id, payload.questions)

        old_question_ids = {
            row.question_id
            for row in execute_sql(
                session,
                "papers.sql",
                "paper_question_ids",
                {"paper_id": paper_id},
            ).all()
        }
        execute_sql(
            session,
            "papers.sql",
            "delete_paper_questions",
            {"paper_id": paper_id},
        )
        execute_sql(
            session,
            "papers.sql",
            "update_paper",
            {
                "paper_id": paper_id,
                "subject_id": payload.subject_id,
                "semester_id": payload.semester_id,
                "exam_type": payload.exam_type.value,
                "total_marks": payload.total_marks,
            },
        )

        for question_data in payload.questions:
            _add_question(session, paper_id, question_data)
        _delete_orphaned_questions(session, old_question_ids)
        response = _paper_read(session, paper_id)

    return response


@router.delete(
    "/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_user)],
)
def delete_paper(
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        _require_paper(session, paper_id)
        question_ids = {
            row.question_id
            for row in execute_sql(
                session,
                "papers.sql",
                "paper_question_ids",
                {"paper_id": paper_id},
            ).all()
        }
        execute_sql(
            session,
            "papers.sql",
            "delete_paper",
            {"paper_id": paper_id},
        )
        _delete_orphaned_questions(session, question_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{paper_id}/questions",
    response_model=PaperQuestionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_user)],
)
def add_paper_question(
    payload: PaperQuestionCreate,
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperQuestionRead:
    with session.begin():
        paper = _require_paper(session, paper_id)
        _validate_questions(session, paper.subject_id, [payload])
        duplicate_number = execute_sql(
            session,
            "papers.sql",
            "question_number_conflict",
            {
                "paper_id": paper_id,
                "question_number": payload.question_number,
                "exclude_question_id": None,
            },
        )
        if duplicate_number.first() is not None:
            raise HTTPException(
                status_code=409,
                detail="Question number already exists in this paper.",
            )
        response = _add_question(session, paper_id, payload)
        session.flush()
    return response


@router.put(
    "/{paper_id}/questions/{question_id}",
    response_model=PaperQuestionRead,
    dependencies=[Depends(require_user)],
)
def update_paper_question(
    payload: PaperQuestionCreate,
    paper_id: int = Path(gt=0),
    question_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperQuestionRead:
    with session.begin():
        paper = _require_paper(session, paper_id)
        link = execute_sql(
            session,
            "papers.sql",
            "paper_question_exists",
            {"paper_id": paper_id, "question_id": question_id},
        ).first()
        if link is None:
            raise HTTPException(
                status_code=404,
                detail=f"Question {question_id} not found in paper {paper_id}.",
            )
        _validate_questions(session, paper.subject_id, [payload])
        duplicate_number = execute_sql(
            session,
            "papers.sql",
            "question_number_conflict",
            {
                "paper_id": paper_id,
                "question_number": payload.question_number,
                "exclude_question_id": question_id,
            },
        )
        if duplicate_number.first() is not None:
            raise HTTPException(
                status_code=409,
                detail="Question number already exists in this paper.",
            )

        execute_sql(
            session,
            "papers.sql",
            "update_paper_question",
            {
                "paper_id": paper_id,
                "question_id": question_id,
                "question_number": payload.question_number,
                "marks": payload.marks,
            },
        )
        execute_sql(
            session,
            "questions.sql",
            "update_question",
            {
                "question_id": question_id,
                "type_id": payload.question_type_id,
                "question_text": payload.question_text,
            },
        )
        upsert_question_embedding(
            session,
            question_id,
            payload.question_text,
            commit=False,
        )
        execute_sql(
            session,
            "questions.sql",
            "delete_question_topics",
            {"question_id": question_id},
        )
        for topic_id in payload.topic_ids:
            execute_sql(
                session,
                "questions.sql",
                "insert_question_topic",
                {"question_id": question_id, "topic_id": topic_id},
            )
        response = PaperQuestionRead(
            question_id=question_id,
            question_number=payload.question_number,
            marks=payload.marks,
            question_text=payload.question_text,
            question_type_id=payload.question_type_id,
            topic_ids=payload.topic_ids,
        )
    return response


@router.delete(
    "/{paper_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_user)],
)
def delete_paper_question(
    paper_id: int = Path(gt=0),
    question_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        _require_paper(session, paper_id)
        link = execute_sql(
            session,
            "papers.sql",
            "paper_question_exists",
            {"paper_id": paper_id, "question_id": question_id},
        ).first()
        if link is None:
            raise HTTPException(
                status_code=404,
                detail=f"Question {question_id} not found in paper {paper_id}.",
            )
        execute_sql(
            session,
            "papers.sql",
            "delete_paper_question",
            {"paper_id": paper_id, "question_id": question_id},
        )
        _delete_orphaned_questions(session, {question_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
