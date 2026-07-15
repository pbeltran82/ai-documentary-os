from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, migrate_sqlite_schema
from .routers.assets import router as assets_router
from .routers.projects import router as projects_router
from .routers.scenes import router as scenes_router
from .schemas import HealthResponse

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

APP_NAME = os.getenv("APP_NAME", "AI Documentary OS")
VERSION = "0.4.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
    yield


app = FastAPI(
    title=f"{APP_NAME} API",
    version=VERSION,
    description="Local-first documentary production command center.",
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

app.include_router(projects_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(assets_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"{APP_NAME} API is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy", app=APP_NAME, version=VERSION)
