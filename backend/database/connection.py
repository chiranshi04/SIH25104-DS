"""
connection.py
-------------
Yahan database engine aur session dependency define hoti hai.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Saare SQLAlchemy models isi base se inherit karenge."""


def get_db() -> Generator[Session, None, None]:
    """Request ke liye session do aur hamesha close karo."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Saare registered models ke tables create karo."""
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
