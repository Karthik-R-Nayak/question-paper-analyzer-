from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Question, QuestionType, Semester, Subject, Topic, Unit
from app.schemas import (
    QuestionTypeCreate,
    QuestionTypeRead,
    SemesterCreate,
    SemesterRead,
    SubjectCreate,
    SubjectRead,
    TopicCreate,
    TopicRead,
    UnitCreate,
    UnitRead,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["academic catalog"])

CatalogEntity = TypeVar(
    "CatalogEntity",
    Subject,
    Semester,
    Unit,
    Topic,
    QuestionType,
)


def _require_existing(
    session: Session,
    model: type[CatalogEntity],
    identifier: int,
    label: str,
) -> CatalogEntity:
    entity = session.get(model, identifier)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{label} not found: {identifier}")
    return entity


def _flush_or_conflict(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Catalog record conflicts with existing data.",
        ) from exc


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(session: Session = Depends(get_session)) -> list[Subject]:
    return list(session.scalars(select(Subject).order_by(Subject.subject_id)))


@router.post(
    "/subjects",
    response_model=SubjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    session: Session = Depends(get_session),
) -> Subject:
    with session.begin():
        subject = Subject(**payload.model_dump())
        session.add(subject)
        _flush_or_conflict(session)
        return subject


@router.get("/subjects/{subject_id}", response_model=SubjectRead)
def get_subject(
    subject_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Subject:
    return _require_existing(session, Subject, subject_id, "Subject")


@router.put("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(
    payload: SubjectCreate,
    subject_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Subject:
    with session.begin():
        subject = _require_existing(session, Subject, subject_id, "Subject")
        for field, value in payload.model_dump().items():
            setattr(subject, field, value)
        _flush_or_conflict(session)
        return subject


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        subject = _require_existing(session, Subject, subject_id, "Subject")
        session.delete(subject)
        _flush_or_conflict(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/semesters", response_model=list[SemesterRead])
def list_semesters(session: Session = Depends(get_session)) -> list[Semester]:
    return list(session.scalars(select(Semester).order_by(Semester.semester_id)))


@router.post(
    "/semesters",
    response_model=SemesterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_semester(
    payload: SemesterCreate,
    session: Session = Depends(get_session),
) -> Semester:
    with session.begin():
        semester = Semester(**payload.model_dump())
        session.add(semester)
        _flush_or_conflict(session)
        return semester


@router.get("/semesters/{semester_id}", response_model=SemesterRead)
def get_semester(
    semester_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Semester:
    return _require_existing(session, Semester, semester_id, "Semester")


@router.put("/semesters/{semester_id}", response_model=SemesterRead)
def update_semester(
    payload: SemesterCreate,
    semester_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Semester:
    with session.begin():
        semester = _require_existing(session, Semester, semester_id, "Semester")
        semester.semester_number = payload.semester_number
        semester.academic_year = payload.academic_year
        _flush_or_conflict(session)
        return semester


@router.delete("/semesters/{semester_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_semester(
    semester_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        semester = _require_existing(session, Semester, semester_id, "Semester")
        session.delete(semester)
        _flush_or_conflict(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/units", response_model=list[UnitRead])
def list_units(session: Session = Depends(get_session)) -> list[Unit]:
    return list(session.scalars(select(Unit).order_by(Unit.unit_id)))


@router.post("/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    session: Session = Depends(get_session),
) -> Unit:
    with session.begin():
        _require_existing(session, Subject, payload.subject_id, "Subject")
        unit = Unit(**payload.model_dump())
        session.add(unit)
        _flush_or_conflict(session)
        return unit


@router.get("/units/{unit_id}", response_model=UnitRead)
def get_unit(
    unit_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Unit:
    return _require_existing(session, Unit, unit_id, "Unit")


@router.put("/units/{unit_id}", response_model=UnitRead)
def update_unit(
    payload: UnitCreate,
    unit_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Unit:
    with session.begin():
        unit = _require_existing(session, Unit, unit_id, "Unit")
        _require_existing(session, Subject, payload.subject_id, "Subject")
        unit.subject_id = payload.subject_id
        unit.unit_number = payload.unit_number
        unit.unit_name = payload.unit_name
        _flush_or_conflict(session)
        return unit


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        unit = _require_existing(session, Unit, unit_id, "Unit")
        session.delete(unit)
        _flush_or_conflict(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/topics", response_model=list[TopicRead])
def list_topics(session: Session = Depends(get_session)) -> list[Topic]:
    return list(session.scalars(select(Topic).order_by(Topic.topic_id)))


@router.post("/topics", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate,
    session: Session = Depends(get_session),
) -> Topic:
    with session.begin():
        _require_existing(session, Unit, payload.unit_id, "Unit")
        topic = Topic(**payload.model_dump())
        session.add(topic)
        _flush_or_conflict(session)
        return topic


@router.get("/topics/{topic_id}", response_model=TopicRead)
def get_topic(
    topic_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Topic:
    return _require_existing(session, Topic, topic_id, "Topic")


@router.put("/topics/{topic_id}", response_model=TopicRead)
def update_topic(
    payload: TopicCreate,
    topic_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Topic:
    with session.begin():
        topic = _require_existing(session, Topic, topic_id, "Topic")
        _require_existing(session, Unit, payload.unit_id, "Unit")
        topic.unit_id = payload.unit_id
        topic.topic_name = payload.topic_name
        _flush_or_conflict(session)
        return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    topic_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        topic = _require_existing(session, Topic, topic_id, "Topic")
        session.delete(topic)
        _flush_or_conflict(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/question-types", response_model=list[QuestionTypeRead])
def list_question_types(session: Session = Depends(get_session)) -> list[QuestionType]:
    return list(
        session.scalars(select(QuestionType).order_by(QuestionType.type_id))
    )


@router.post(
    "/question-types",
    response_model=QuestionTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_question_type(
    payload: QuestionTypeCreate,
    session: Session = Depends(get_session),
) -> QuestionType:
    with session.begin():
        question_type = QuestionType(**payload.model_dump())
        session.add(question_type)
        _flush_or_conflict(session)
        return question_type


@router.get("/question-types/{type_id}", response_model=QuestionTypeRead)
def get_question_type(
    type_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> QuestionType:
    return _require_existing(session, QuestionType, type_id, "Question type")


@router.put("/question-types/{type_id}", response_model=QuestionTypeRead)
def update_question_type(
    payload: QuestionTypeCreate,
    type_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> QuestionType:
    with session.begin():
        question_type = _require_existing(session, QuestionType, type_id, "Question type")
        question_type.type_name = payload.type_name
        _flush_or_conflict(session)
        return question_type


@router.delete("/question-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_type(
    type_id: int = Path(gt=0),
    session: Session = Depends(get_session),
) -> Response:
    with session.begin():
        question_type = _require_existing(session, QuestionType, type_id, "Question type")
        if session.scalar(
            select(Question.question_id).where(Question.type_id == type_id).limit(1)
        ):
            raise HTTPException(
                status_code=409,
                detail="Cannot delete a question type that is used by questions.",
            )
        session.delete(question_type)
        _flush_or_conflict(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
