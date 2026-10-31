from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
    ExamPaper,
    PaperQuestion,
    Question,
    QuestionTopic,
    QuestionType,
    Semester,
    Subject,
    Topic,
    Unit,
)
from app.schemas import PaperCreate, PaperQuestionCreate, PaperQuestionRead, PaperRead

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])


def _require_paper(session: Session, paper_id: int) -> ExamPaper:
    paper = session.get(ExamPaper, paper_id)
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

    topic_subjects = session.execute(
        select(Topic.topic_id, Unit.subject_id)
        .join(Unit, Topic.unit_id == Unit.unit_id)
        .where(Topic.topic_id.in_(topic_ids))
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
    question = Question(
        type_id=question_data.question_type_id,
        question_text=question_data.question_text,
    )
    session.add(question)
    session.flush()
    session.add(
        PaperQuestion(
            paper_id=paper_id,
            question_id=question.question_id,
            question_number=question_data.question_number,
            marks=question_data.marks,
        )
    )
    session.add_all(
        QuestionTopic(question_id=question.question_id, topic_id=topic_id)
        for topic_id in question_data.topic_ids
    )
    return PaperQuestionRead(
        question_id=question.question_id,
        question_number=question_data.question_number,
        marks=question_data.marks,
        question_text=question_data.question_text,
        question_type_id=question_data.question_type_id,
        topic_ids=question_data.topic_ids,
    )


def _paper_read(session: Session, paper: ExamPaper) -> PaperRead:
    rows = session.execute(
        select(PaperQuestion, Question)
        .join(Question, Question.question_id == PaperQuestion.question_id)
        .where(PaperQuestion.paper_id == paper.paper_id)
        .order_by(PaperQuestion.question_number, PaperQuestion.question_id)
    ).all()
    question_ids = [question.question_id for _link, question in rows]
    topic_rows = session.execute(
        select(QuestionTopic.question_id, QuestionTopic.topic_id)
        .where(QuestionTopic.question_id.in_(question_ids))
        .order_by(QuestionTopic.topic_id)
    ).all() if question_ids else []
    topic_ids_by_question: dict[int, list[int]] = {}
    for question_id, topic_id in topic_rows:
        topic_ids_by_question.setdefault(question_id, []).append(topic_id)

    return PaperRead(
        paper_id=paper.paper_id,
        subject_id=paper.subject_id,
        semester_id=paper.semester_id,
        exam_type=paper.exam_type,
        total_marks=paper.total_marks,
        questions=[
            PaperQuestionRead(
                question_id=question.question_id,
                question_number=link.question_number,
                marks=link.marks,
                question_text=question.question_text,
                question_type_id=question.type_id,
                topic_ids=topic_ids_by_question.get(question.question_id, []),
            )
            for link, question in rows
        ],
    )


def _delete_orphaned_questions(session: Session, question_ids: set[int]) -> None:
    if not question_ids:
        return
    session.flush()
    remaining_ids = set(
        session.scalars(
            select(PaperQuestion.question_id).where(
                PaperQuestion.question_id.in_(question_ids)
            )
        )
    )
    for question_id in question_ids - remaining_ids:
        question = session.get(Question, question_id)
        if question is not None:
            session.delete(question)


@router.post("", response_model=PaperRead, status_code=status.HTTP_201_CREATED)
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

        paper = ExamPaper(
            subject_id=payload.subject_id,
            semester_id=payload.semester_id,
            exam_type=payload.exam_type.value,
            total_marks=payload.total_marks,
        )
        session.add(paper)
        session.flush()

        response_questions = [
            _add_question(session, paper.paper_id, question_data)
            for question_data in payload.questions
        ]
        session.flush()
        response = PaperRead(
            paper_id=paper.paper_id,
            subject_id=paper.subject_id,
            semester_id=paper.semester_id,
            exam_type=payload.exam_type,
            total_marks=paper.total_marks,
            questions=response_questions,
        )

    return response


@router.get("", response_model=list[PaperRead])
def list_papers(session: Session = Depends(get_session)) -> list[PaperRead]:
    papers = session.scalars(select(ExamPaper).order_by(ExamPaper.paper_id)).all()
    return [_paper_read(session, paper) for paper in papers]


@router.get("/{paper_id}", response_model=PaperRead)
def get_paper(
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperRead:
    return _paper_read(session, _require_paper(session, paper_id))


@router.put("/{paper_id}", response_model=PaperRead)
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
        paper = _require_paper(session, paper_id)
        _require_existing(session, Subject, payload.subject_id, "subject")
        _require_existing(session, Semester, payload.semester_id, "semester")
        _validate_questions(session, payload.subject_id, payload.questions)

        old_question_ids = set(
            session.scalars(
                select(PaperQuestion.question_id).where(
                    PaperQuestion.paper_id == paper_id
                )
            )
        )
        session.query(PaperQuestion).filter(
            PaperQuestion.paper_id == paper_id
        ).delete(synchronize_session=False)
        paper.subject_id = payload.subject_id
        paper.semester_id = payload.semester_id
        paper.exam_type = payload.exam_type.value
        paper.total_marks = payload.total_marks
        _delete_orphaned_questions(session, old_question_ids)

        for question_data in payload.questions:
            _add_question(session, paper.paper_id, question_data)
        session.flush()
        response = _paper_read(session, paper)

    return response


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        paper = _require_paper(session, paper_id)
        question_ids = set(
            session.scalars(
                select(PaperQuestion.question_id).where(
                    PaperQuestion.paper_id == paper_id
                )
            )
        )
        session.delete(paper)
        session.flush()
        _delete_orphaned_questions(session, question_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{paper_id}/questions",
    response_model=PaperQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_paper_question(
    payload: PaperQuestionCreate,
    paper_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperQuestionRead:
    with session.begin():
        paper = _require_paper(session, paper_id)
        _validate_questions(session, paper.subject_id, [payload])
        duplicate_number = session.scalar(
            select(PaperQuestion.question_id).where(
                PaperQuestion.paper_id == paper_id,
                PaperQuestion.question_number == payload.question_number,
            )
        )
        if duplicate_number is not None:
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
)
def update_paper_question(
    payload: PaperQuestionCreate,
    paper_id: int = Path(gt=0),
    question_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> PaperQuestionRead:
    with session.begin():
        paper = _require_paper(session, paper_id)
        link = session.get(PaperQuestion, (paper_id, question_id))
        if link is None:
            raise HTTPException(
                status_code=404,
                detail=f"Question {question_id} not found in paper {paper_id}.",
            )
        _validate_questions(session, paper.subject_id, [payload])
        duplicate_number = session.scalar(
            select(PaperQuestion.question_id).where(
                PaperQuestion.paper_id == paper_id,
                PaperQuestion.question_number == payload.question_number,
                PaperQuestion.question_id != question_id,
            )
        )
        if duplicate_number is not None:
            raise HTTPException(
                status_code=409,
                detail="Question number already exists in this paper.",
            )

        question = session.get(Question, question_id)
        link.question_number = payload.question_number
        link.marks = payload.marks
        question.type_id = payload.question_type_id
        question.question_text = payload.question_text
        session.query(QuestionTopic).filter(
            QuestionTopic.question_id == question_id
        ).delete(synchronize_session=False)
        session.add_all(
            QuestionTopic(question_id=question_id, topic_id=topic_id)
            for topic_id in payload.topic_ids
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
)
def delete_paper_question(
    paper_id: int = Path(gt=0),
    question_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        _require_paper(session, paper_id)
        link = session.get(PaperQuestion, (paper_id, question_id))
        if link is None:
            raise HTTPException(
                status_code=404,
                detail=f"Question {question_id} not found in paper {paper_id}.",
            )
        session.delete(link)
        _delete_orphaned_questions(session, {question_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
