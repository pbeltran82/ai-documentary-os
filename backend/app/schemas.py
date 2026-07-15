from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    topic: str = Field(min_length=5, max_length=3000)
    target_minutes: int = Field(default=8, ge=1, le=180)
    audience: str = Field(default="General audience", min_length=2, max_length=200)
    tone: str = Field(default="Cinematic", min_length=2, max_length=120)
    visual_style: str = Field(
        default="Cinematic documentary", min_length=2, max_length=200
    )


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
