from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    scenes: Mapped[list[Scene]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Scene.scene_number",
    )


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, default=5, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=5, nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    visual_intent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    search_keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_asset_type: Mapped[str] = mapped_column(
        String(40), default="stock_video", nullable=False
    )
    asset_status: Mapped[str] = mapped_column(
        String(40), default="missing", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="scenes")
    selected_asset: Mapped[Asset | None] = relationship(
        back_populates="scene",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), default="pixabay", nullable=False)
    provider_asset_id: Mapped[str] = mapped_column(String(200), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    preview_url: Mapped[str] = mapped_column(Text, nullable=False)
    download_url: Mapped[str] = mapped_column(Text, nullable=False)
    remote_download_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    creator: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    creator_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    license_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    license_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attribution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    local_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    local_preview_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    downloaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    scene: Mapped[Scene] = relationship(back_populates="selected_asset")
