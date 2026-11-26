"""Database engine and schema bootstrap helpers."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base


class Database:
    """Small SQLAlchemy database wrapper; PostgreSQL is the target, SQLite supports tests."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        if not url:
            raise ValueError("Database URL is required")
        self.engine: Engine = create_engine(url, echo=echo, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def create_schema(self) -> None:
        """Create PoC tables. Use versioned migrations before production deployment."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()
