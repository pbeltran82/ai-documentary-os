from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_minutes: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    audience: Mapped[str] = mapped_column(String(200), default="General audience", nullable=False)
    tone: Mapped[str] = mapped_column(String(120), default="Cinematic", nullable=False)
    visual_style: Mapped[str] = mapped_column(
        String(200), default="Cinematic documentary", nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="planning", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
