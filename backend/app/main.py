from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, migrate_sqlite_schema
from .routers.adaptive_assets import router as adaptive_assets_router
from .routers.animation_plans import router as animation_plans_router
from .routers.assets import router as assets_router
from .routers.finance_motion import router as finance_motion_router
from .routers.projects import router as projects_router
from .routers.scenes import router as scenes_router
from .routers.timeline import router as timeline_router
from .schemas import HealthResponse
from .services import animation_script_runtime as _animation_script_runtime
from .services import manifest_events as _manifest_events
from .services.media_library import MEDIA_ROOT

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

APP_NAME = os.getenv("APP_NAME", "AI Documentary OS")
VERSION = "1.9.1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=f"{APP_NAME} API",
    version=VERSION,
    description="Local-first documentary command center with editable animation scripts, expressive character performances, project-wide batch generation, and modular exact visual families.",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")
app.include_router(projects_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(animation_plans_router, prefix="/api")
app.include_router(assets_router, prefix="/api")
app.include_router(adaptive_assets_router, prefix="/api")
app.include_router(finance_motion_router, prefix="/api")
app.include_router(timeline_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"{APP_NAME} API is running",
        "docs": "/docs",
        "health": "/health",
        "media": "/media",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy", app=APP_NAME, version=VERSION)
