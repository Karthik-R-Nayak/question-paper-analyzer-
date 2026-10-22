from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


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
SubjectCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
]
SubjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
DepartmentName = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=100),
]
AcademicYear = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=9),
]
UnitName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
TopicName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
QuestionTypeName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class SubjectCreate(BaseModel):
    subject_code: SubjectCode
    subject_name: SubjectName
    department: DepartmentName = None


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: int
    subject_code: str
    subject_name: str
    department: str | None


class SemesterCreate(BaseModel):
    semester_number: int = Field(ge=1, le=8)
    academic_year: AcademicYear


class SemesterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    semester_id: int
    semester_number: int
    academic_year: str


class UnitCreate(BaseModel):
    subject_id: int = Field(gt=0)
    unit_number: int = Field(gt=0)
    unit_name: UnitName


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: int
    subject_id: int
    unit_number: int
    unit_name: str


class TopicCreate(BaseModel):
    unit_id: int = Field(gt=0)
    topic_name: TopicName


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    unit_id: int
    topic_name: str


class QuestionTypeCreate(BaseModel):
    type_name: QuestionTypeName


class QuestionTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type_id: int
    type_name: str


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
