import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or os.getenv("DATABASE_URL") or "sqlite:///./app.db"
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_database_engine() -> Engine:
    return create_database_engine()


def get_session() -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=get_database_engine())
    with session_factory() as session:
        yield session
