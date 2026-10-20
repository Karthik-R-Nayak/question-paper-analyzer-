from fastapi import APIRouter, Depends, HTTPException, status
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
from app.schemas import PaperCreate, PaperQuestionRead, PaperRead

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])


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

        type_ids = {question.question_type_id for question in payload.questions}
        for type_id in type_ids:
            _require_existing(session, QuestionType, type_id, "question type")

        topic_ids = {
            topic_id for question in payload.questions for topic_id in question.topic_ids
        }
        if topic_ids:
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
                for topic_id, subject_id in subjects_by_topic.items()
                if subject_id != payload.subject_id
            }
            if unrelated_topics:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Topic id(s) do not belong to the paper's subject: "
                        f"{', '.join(map(str, sorted(unrelated_topics)))}"
                    ),
                )

        paper = ExamPaper(
            subject_id=payload.subject_id,
            semester_id=payload.semester_id,
            exam_type=payload.exam_type.value,
            total_marks=payload.total_marks,
        )
        session.add(paper)
        session.flush()

        response_questions = []
        for question_data in payload.questions:
            question = Question(
                type_id=question_data.question_type_id,
                question_text=question_data.question_text,
            )
            session.add(question)
            session.flush()
            session.add(
                PaperQuestion(
                    paper_id=paper.paper_id,
                    question_id=question.question_id,
                    question_number=question_data.question_number,
                    marks=question_data.marks,
                )
            )
            session.add_all(
                QuestionTopic(question_id=question.question_id, topic_id=topic_id)
                for topic_id in question_data.topic_ids
            )
            response_questions.append(
                PaperQuestionRead(
                    question_id=question.question_id,
                    question_number=question_data.question_number,
                    marks=question_data.marks,
                    question_text=question_data.question_text,
                    question_type_id=question_data.question_type_id,
                    topic_ids=question_data.topic_ids,
                )
            )

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
