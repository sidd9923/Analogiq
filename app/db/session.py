"""Database session management."""

from __future__ import annotations

from contextlib import contextmanager

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from config.settings import settings

_engine = None
_SessionFactory = None


def init_db(app: Flask) -> None:
    global _engine, _SessionFactory
    _engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=settings.DB_ECHO,
    )
    _SessionFactory = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)
    app.logger.info("Database initialised at %s", settings.DATABASE_URL)


@contextmanager
def get_session() -> Session:
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
