from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class SceneBase(BaseModel):
    narration: str = Field(min_length=1, max_length=5000)
    duration_seconds: float = Field(default=5, ge=1, le=60)
    visual_intent: str = Field(default="", max_length=2000)
    search_keywords: list[str] = Field(default_factory=list, max_length=20)
    preferred_asset_type: str = Field(default="stock_video", max_length=40)
    asset_status: str = Field(default="missing", max_length=40)

    @field_validator("search_keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            keyword = " ".join(value.strip().lower().split())
            if keyword and keyword not in seen:
                cleaned.append(keyword)
                seen.add(keyword)
        return cleaned[:20]


class SceneCreate(SceneBase):
    pass


class SceneUpdate(BaseModel):
    narration: str | None = Field(default=None, min_length=1, max_length=5000)
    duration_seconds: float | None = Field(default=None, ge=1, le=60)
    visual_intent: str | None = Field(default=None, max_length=2000)
    search_keywords: list[str] | None = Field(default=None, max_length=20)
    preferred_asset_type: str | None = Field(default=None, max_length=40)
    asset_status: str | None = Field(default=None, max_length=40)

    @field_validator("search_keywords")
    @classmethod
    def clean_keywords(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            keyword = " ".join(value.strip().lower().split())
            if keyword and keyword not in seen:
                cleaned.append(keyword)
                seen.add(keyword)
        return cleaned[:20]


class SceneRead(SceneBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    scene_number: int
    start_seconds: float
    end_seconds: float
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    scenes: list[SceneRead] = Field(default_factory=list)


class SceneGenerateRequest(BaseModel):
    narration: str = Field(min_length=5, max_length=100_000)
    target_scene_seconds: float = Field(default=5, ge=3, le=15)
    replace_existing: bool = True


class SceneGenerateResponse(BaseModel):
    project_id: int
    scene_count: int
    total_duration_seconds: float
    scenes: list[SceneRead]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
