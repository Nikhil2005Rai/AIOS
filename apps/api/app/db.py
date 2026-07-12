from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import sqlalchemy_database_url, validate_runtime_settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine() -> Engine:
    global engine
    validate_runtime_settings()
    if engine is None:
        engine = create_engine(sqlalchemy_database_url(), pool_pre_ping=True)
        SessionLocal.configure(bind=engine)
    return engine


def get_db_session() -> Generator[Session, None, None]:
    get_engine()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_db_schema() -> None:
    from app.infrastructure import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
