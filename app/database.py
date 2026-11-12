"""Portable transactional snapshots; schema is managed only through Alembic."""

import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SavedAnalysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    snapshot: Mapped[dict] = mapped_column(JSON)


class SavedScenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    definition: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)


class SavedDraft(Base):
    __tablename__ = "drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    snapshot: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 -- SQLAlchemy declarative configuration


def make_engine():
    """Create a configured engine without changing its schema."""
    return create_engine(os.getenv("DATABASE_URL", "sqlite:///./reality.db"), pool_pre_ping=True)
