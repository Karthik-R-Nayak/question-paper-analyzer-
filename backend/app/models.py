from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - optional dependency on PostgreSQL only
    Vector = None


class Base(DeclarativeBase):
    pass


class QuestionEmbedding(Base):
    __tablename__ = "question_embedding"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.question_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    embedding = mapped_column(
        Vector(384) if Vector is not None else Text,
        nullable=False,
    )


class Subject(Base):
    __tablename__ = "subject"

    subject_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))


class Semester(Base):
    __tablename__ = "semester"
    __table_args__ = (
        CheckConstraint("semester_number BETWEEN 1 AND 8"),
        UniqueConstraint("semester_number", "academic_year"),
    )

    semester_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)


class Unit(Base):
    __tablename__ = "unit"
    __table_args__ = (UniqueConstraint("subject_id", "unit_number"),)

    unit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subject.subject_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    unit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_name: Mapped[str] = mapped_column(String(150), nullable=False)


class Topic(Base):
    __tablename__ = "topic"

    topic_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("unit.unit_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    topic_name: Mapped[str] = mapped_column(String(150), nullable=False)


class QuestionType(Base):
    __tablename__ = "question_type"

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)


class ExamPaper(Base):
    __tablename__ = "exam_paper"
    __table_args__ = (
        CheckConstraint(
            "exam_type IN ('Internal', 'Mid', 'End', 'Supplementary')"
        ),
        CheckConstraint("total_marks > 0"),
    )

    paper_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subject.subject_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semester.semester_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    exam_type: Mapped[str] = mapped_column(String(20), nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False)


class Question(Base):
    __tablename__ = "question"

    question_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("question_type.type_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(100))


class PaperQuestion(Base):
    __tablename__ = "paper_question"
    __table_args__ = (
        CheckConstraint("marks > 0"),
        UniqueConstraint("paper_id", "question_number"),
    )

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("exam_paper.paper_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.question_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    question_number: Mapped[str] = mapped_column(String(10), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)


class QuestionTopic(Base):
    __tablename__ = "question_topic"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.question_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topic.topic_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
