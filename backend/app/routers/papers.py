from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.pgvector_search import upsert_question_embedding
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
from app.schemas import (
    BulkImportPayload,
    BulkImportResult,
    PaperCreate,
    PaperQuestionCreate,
    PaperQuestionRead,
    PaperRead,
)

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
    upsert_question_embedding(
        session,
        question.question_id,
        question_data.question_text,
        commit=False,
    )
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
        upsert_question_embedding(
            session,
            question.question_id,
            question.question_text,
            commit=False,
        )
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


def _ensure_question_type(session: Session, type_name: str) -> QuestionType:
    label = (type_name or "").strip()
    if not label:
        raise HTTPException(status_code=422, detail="Question type name is required for import.")
    existing = session.scalar(
        select(QuestionType).where(func.lower(QuestionType.type_name) == label.lower())
    )
    if existing is not None:
        return existing
    question_type = QuestionType(type_name=label)
    session.add(question_type)
    session.flush()
    return question_type


def _ensure_subject(session: Session, subject_code: str | None, subject_name: str | None) -> Subject:
    input_code = (subject_code or "").strip()
    input_name = (subject_name or "").strip()
    if not input_code and not input_name:
        raise HTTPException(status_code=422, detail="Subject code or subject name is required for import.")

    if input_code:
        existing = session.scalar(select(Subject).where(func.lower(Subject.subject_code) == input_code.lower()))
        if existing is not None:
            return existing
    if input_name:
        existing = session.scalar(select(Subject).where(func.lower(Subject.subject_name) == input_name.lower()))
        if existing is not None:
            return existing

    code = input_code or input_name[:20].strip() or "SUBJ"
    name = input_name or code
    subject = Subject(subject_code=code, subject_name=name, department=None)
    session.add(subject)
    session.flush()
    return subject


def _ensure_semester(session: Session, semester_number: int, academic_year: str) -> Semester:
    year = (academic_year or "2026-2027").strip() or "2026-2027"
    existing = session.scalar(
        select(Semester).where(
            Semester.semester_number == semester_number,
            func.lower(Semester.academic_year) == year.lower(),
        )
    )
    if existing is not None:
        return existing
    semester = Semester(semester_number=semester_number, academic_year=year)
    session.add(semester)
    session.flush()
    return semester


def _ensure_unit(session: Session, subject_id: int, unit_name: str | None) -> Unit:
    label = (unit_name or "").strip()
    if not label:
        raise HTTPException(status_code=422, detail="Each imported question needs a unit or topic name.")
    existing = session.scalar(
        select(Unit).where(Unit.subject_id == subject_id, func.lower(Unit.unit_name) == label.lower())
    )
    if existing is not None:
        return existing

    next_number = (
        session.scalar(
            select(func.max(Unit.unit_number)).where(Unit.subject_id == subject_id)
        )
        or 0
    ) + 1
    unit = Unit(subject_id=subject_id, unit_number=next_number, unit_name=label)
    session.add(unit)
    session.flush()
    return unit


def _ensure_topic(session: Session, unit_id: int, topic_name: str) -> Topic:
    label = (topic_name or "").strip()
    if not label:
        raise HTTPException(status_code=422, detail="Topic name is required for import.")
    existing = session.scalar(
        select(Topic).where(Topic.unit_id == unit_id, func.lower(Topic.topic_name) == label.lower())
    )
    if existing is not None:
        return existing
    topic = Topic(unit_id=unit_id, topic_name=label)
    session.add(topic)
    session.flush()
    return topic


@router.post("/import", response_model=BulkImportResult, status_code=status.HTTP_201_CREATED)
def bulk_import_papers(
    payload: BulkImportPayload,
    session: Session = Depends(get_session),
) -> BulkImportResult:
    if not payload.papers:
        raise HTTPException(status_code=422, detail="At least one paper is required for import.")

    created_subjects = 0
    created_semesters = 0
    created_topics = 0
    created_question_types = 0
    created_papers = 0
    created_questions = 0

    with session.begin():
        for paper_data in payload.papers:
            subject = _ensure_subject(session, paper_data.subject_code, paper_data.subject_name)
            if subject.subject_id is None:
                session.flush()
            if subject.subject_id is None:
                raise HTTPException(status_code=500, detail="Failed to create subject for imported paper.")

            semester = _ensure_semester(session, paper_data.semester_number, paper_data.academic_year)
            if semester.semester_id is None:
                session.flush()

            paper = ExamPaper(
                subject_id=subject.subject_id,
                semester_id=semester.semester_id,
                exam_type=paper_data.exam_type.value,
                total_marks=paper_data.total_marks or 0,
            )
            session.add(paper)
            session.flush()
            created_papers += 1

            for question_data in paper_data.questions:
                question_type = _ensure_question_type(session, question_data.question_type)
                unit = _ensure_unit(
                    session,
                    subject.subject_id,
                    question_data.unit_name or question_data.topic_name or "General",
                )
                topic = _ensure_topic(session, unit.unit_id, question_data.topic_name or question_data.question_text[:30])

                question = Question(
                    type_id=question_type.type_id,
                    question_text=question_data.question_text,
                )
                session.add(question)
                session.flush()
                upsert_question_embedding(
                    session,
                    question.question_id,
                    question.question_text,
                    commit=False,
                )
                session.add(
                    PaperQuestion(
                        paper_id=paper.paper_id,
                        question_id=question.question_id,
                        question_number=question_data.question_number,
                        marks=question_data.marks,
                    )
                )
                session.add(
                    QuestionTopic(
                        question_id=question.question_id,
                        topic_id=topic.topic_id,
                    )
                )
                created_questions += 1
                created_topics += 0
                created_question_types += 0

            if not session.new and subject.subject_id is not None:
                created_subjects += 0
            if not session.new and semester.semester_id is not None:
                created_semesters += 0

    return BulkImportResult(
        created_papers=created_papers,
        created_questions=created_questions,
        created_subjects=created_subjects,
        created_semesters=created_semesters,
        created_topics=created_topics,
        created_question_types=created_question_types,
    )
