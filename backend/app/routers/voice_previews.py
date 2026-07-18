from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project
from ..services.narration_synthesis import NarrationSynthesisError
from ..services.voice_previews import generate_voice_preview

router = APIRouter(prefix="/projects/{project_id}/production", tags=["voice-previews"])


class VoicePreviewRequest(BaseModel):
    voice_id: str = Field(min_length=1, max_length=120)
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    text: str = Field(default="", max_length=600)


@router.post("/narration/voice-preview")
def voice_preview(
    project_id: int,
    payload: VoicePreviewRequest,
    db: Session = Depends(get_db),
) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return generate_voice_preview(
            project_id,
            voice_id=payload.voice_id,
            speaking_rate=payload.speaking_rate,
            text=payload.text,
        )
    except NarrationSynthesisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
