"""SQLAlchemy incident model."""
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(80), unique=True, index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="Autre", nullable=False)
    priority: Mapped[str] = mapped_column(String(30), default="moyenne", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="résolu", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
