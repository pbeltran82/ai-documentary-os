from __future__ import annotations

from datetime import datetime
from typing import Any

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


class AssetBase(BaseModel):
    provider: str = Field(default="pixabay", max_length=40)
    provider_asset_id: str = Field(min_length=1, max_length=200)
    media_type: str = Field(pattern="^(video|photo)$")
    source_url: str
    preview_url: str
    download_url: str
    creator: str = Field(default="", max_length=200)
    creator_url: str = ""
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    license_name: str = Field(default="", max_length=200)
    license_url: str = ""
    attribution: str = Field(default="", max_length=5000)


class AssetCandidate(AssetBase):
    description: str = Field(default="", max_length=5000)
    keywords: list[str] = Field(default_factory=list, max_length=40)
    query_variant: str = Field(default="", max_length=200)
    director_score: float = Field(default=0, ge=0, le=100)
    director_reasons: list[str] = Field(default_factory=list, max_length=6)
    director_warnings: list[str] = Field(default_factory=list, max_length=6)
    shortlist_rank: int | None = Field(default=None, ge=1, le=30)


class AssetSelect(AssetBase):
    pass


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scene_id: int
    remote_download_url: str = ""
    local_path: str = ""
    local_preview_path: str = ""
    content_type: str = ""
    file_size_bytes: int = 0
    checksum_sha256: str = ""
    downloaded_at: datetime | None = None
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
    selected_asset: AssetRead | None = None
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


class ProviderStatusResponse(BaseModel):
    provider: str
    label: str
    configured: bool
    requires_key: bool
    supports_media_types: list[str]
    setup_hint: str
    source_url: str


class ShotBrief(BaseModel):
    scene_id: int
    subject: str
    action: str
    setting: str
    framing: str
    mood: str
    must_show: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    query_variants: list[str] = Field(default_factory=list)


class AssetSearchResponse(BaseModel):
    provider: str
    configured: bool
    query: str
    media_type: str
    source_url: str
    rate_limit_remaining: int | None = None
    candidates: list[AssetCandidate] = Field(default_factory=list)


class VisualDirectorResponse(BaseModel):
    media_type: str
    shot_brief: ShotBrief
    search_queries: list[str] = Field(default_factory=list)
    providers_searched: list[str] = Field(default_factory=list)
    rate_limit_remaining: int | None = None
    rejected_count: int = 0
    candidates: list[AssetCandidate] = Field(default_factory=list)


class VisualFeedbackCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    provider_asset_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(
        default="wrong_concept",
        pattern="^(wrong_concept|too_generic|repetitive|poor_quality|bad_style)$",
    )


class VisualFeedbackRead(VisualFeedbackCreate):
    scene_id: int
    created_at: str


class VisualFeedbackReset(BaseModel):
    removed: int


class TimelineManifestResponse(BaseModel):
    project_id: int
    relative_path: str
    public_url: str
    manifest: dict[str, Any]


class TimelineMissingScene(BaseModel):
    scene_id: int
    scene_number: int
    reason: str


class TimelineClipRead(BaseModel):
    scene_id: int
    scene_number: int
    input_index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    narration: str
    visual_intent: str
    provider: str
    provider_asset_id: str
    media_type: str
    local_path: str
    local_url: str
    preview_url: str
    source_url: str
    creator: str
    license_name: str
    attribution: str
    source_file: str
    assembly_action: str


class VoiceoverRead(BaseModel):
    original_filename: str
    relative_path: str
    public_url: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    duration_seconds: float
    uploaded_at: str


class TimelinePlanResponse(BaseModel):
    schema_version: str
    generated_at: str
    project_id: int
    project_title: str
    ready: bool
    ffmpeg_available: bool
    runtime_seconds: float
    clip_count: int
    missing_scenes: list[TimelineMissingScene] = Field(default_factory=list)
    settings: dict[str, Any]
    voiceover: VoiceoverRead | None = None
    alignment_status: str
    duration_delta_seconds: float | None = None
    alignment_message: str
    clips: list[TimelineClipRead] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
    output_relative_path: str
    output_url: str
    output_exists: bool
    output_size_bytes: int
    rendered_at: str | None = None
    plan_relative_path: str
    plan_url: str
    script_relative_path: str
    script_url: str
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
