from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints
from pydantic import field_validator


class ExamType(str, Enum):
    INTERNAL = "Internal"
    MID = "Mid"
    END = "End"
    SUPPLEMENTARY = "Supplementary"


QuestionNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=10),
]
QuestionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class PaperQuestionCreate(BaseModel):
    question_number: QuestionNumber
    marks: int = Field(gt=0)
    question_text: QuestionText
    question_type_id: int = Field(gt=0)
    topic_ids: list[int] = Field(default_factory=list)

    @field_validator("topic_ids")
    @classmethod
    def require_unique_topic_ids(cls, topic_ids: list[int]) -> list[int]:
        if len(topic_ids) != len(set(topic_ids)):
            raise ValueError("Topic ids must be unique within a question.")
        if any(topic_id <= 0 for topic_id in topic_ids):
            raise ValueError("Topic ids must be positive.")
        return topic_ids


class PaperCreate(BaseModel):
    subject_id: int = Field(gt=0)
    semester_id: int = Field(gt=0)
    exam_type: ExamType
    total_marks: int = Field(gt=0)
    questions: list[PaperQuestionCreate] = Field(min_length=1)


class PaperQuestionRead(BaseModel):
    question_id: int
    question_number: str
    marks: int
    question_text: str
    question_type_id: int
    topic_ids: list[int]


class PaperRead(BaseModel):
    paper_id: int
    subject_id: int
    semester_id: int
    exam_type: ExamType
    total_marks: int
    questions: list[PaperQuestionRead]
