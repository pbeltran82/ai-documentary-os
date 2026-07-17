from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DATABASE_URL = f"sqlite:///{DATA_DIR / 'documentary_os.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _add_missing_columns(connection, table: str, additions: dict[str, str]) -> None:
    table_exists = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table"),
        {"table": table},
    ).scalar_one_or_none()
    if not table_exists:
        return
    existing = {
        row[1]
        for row in connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    }
    for column, definition in additions.items():
        if column not in existing:
            connection.exec_driver_sql(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )


def migrate_sqlite_schema() -> None:
    """Apply small additive migrations for existing local SQLite databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        _add_missing_columns(
            connection,
            "projects",
            {"video_format": "VARCHAR(20) NOT NULL DEFAULT 'youtube'"},
        )
        _add_missing_columns(
            connection,
            "assets",
            {
                "license_name": "VARCHAR(200) NOT NULL DEFAULT ''",
                "license_url": "TEXT NOT NULL DEFAULT ''",
                "attribution": "TEXT NOT NULL DEFAULT ''",
                "remote_download_url": "TEXT NOT NULL DEFAULT ''",
                "local_path": "TEXT NOT NULL DEFAULT ''",
                "local_preview_path": "TEXT NOT NULL DEFAULT ''",
                "content_type": "VARCHAR(120) NOT NULL DEFAULT ''",
                "file_size_bytes": "INTEGER NOT NULL DEFAULT 0",
                "checksum_sha256": "VARCHAR(64) NOT NULL DEFAULT ''",
                "downloaded_at": "DATETIME",
            },
        )
        _add_missing_columns(
            connection,
            "scenes",
            {"animation_plan": "JSON NOT NULL DEFAULT '{}'"},
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
