from __future__ import annotations

import os
import shutil
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (BACKEND_DIR, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# This must be set before app.database is imported. The E2E harness is destructive
# by design, so it receives an isolated database that can never be the user's app DB.
E2E_DATA_DIR = BACKEND_DIR / "data" / "e2e"
E2E_DATA_DIR.mkdir(parents=True, exist_ok=True)
E2E_DATABASE_PATH = E2E_DATA_DIR / "asset-first-e2e.db"
os.environ["DATABASE_URL"] = f"sqlite:///{E2E_DATABASE_PATH}"

# The E2E test must validate the complete asset-first path without depending on
# third-party uptime, API keys, archive throttling, or changing search results.
os.environ.setdefault("ASSET_PROVIDER_TIMEOUT_SECONDS", "5")
os.environ["ASSET_PROVIDER_ALLOWLIST"] = "e2e_fixture"
os.environ["ASSET_PROVIDER_QUERY_LIMIT"] = "1"
os.environ.setdefault("PYTHONUNBUFFERED", "1")

configured_ffmpeg = os.getenv("FFMPEG_BIN", "").strip()
configured_path = Path(configured_ffmpeg).expanduser() if configured_ffmpeg else None
resolved_ffmpeg = (
    str(configured_path.resolve())
    if configured_path is not None and configured_path.is_file()
    else shutil.which(configured_ffmpeg or "ffmpeg")
)
if not resolved_ffmpeg:
    raise RuntimeError(
        "FFmpeg could not be resolved inside Python; "
        f"FFMPEG_BIN={configured_ffmpeg!r}, PATH={os.getenv('PATH', '')!r}"
    )

from app.schemas import AssetCandidate  # noqa: E402
from app.services import finance_motion as finance_engine  # noqa: E402
from app.services import finance_motion_art as finance_art  # noqa: E402
from app.services import timeline_builder as timeline_builder  # noqa: E402
from app.services import timeline_playback_polish as timeline_polish  # noqa: E402
from app.services.assets import PROVIDERS  # noqa: E402
from app.services.assets.common import ProviderSpec  # noqa: E402

finance_engine.FFMPEG_NAME = resolved_ffmpeg
finance_art.engine.FFMPEG_NAME = resolved_ffmpeg
timeline_builder.FFMPEG_NAME = resolved_ffmpeg
timeline_builder.ffmpeg_executable = lambda: resolved_ffmpeg
timeline_polish.base.FFMPEG_NAME = resolved_ffmpeg
timeline_polish.base.ffmpeg_executable = lambda: resolved_ffmpeg

FIXTURE_DIR = BACKEND_DIR / ".asset-first-e2e-fixture"
FIXTURE_PATH = FIXTURE_DIR / "documentary-source.jpg"


def _build_fixture() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1920, 1080), (7, 13, 28))
    draw = ImageDraw.Draw(image)
    for y in range(1080):
        shade = int(18 + (y / 1080) * 42)
        draw.line((0, y, 1920, y), fill=(8, shade, min(92, shade + 24)))
    draw.ellipse((1090, 120, 1810, 840), fill=(26, 72, 118), outline=(150, 210, 255), width=8)
    for x, y, radius in ((1240, 300, 10), (1360, 420, 8), (1510, 510, 12), (1630, 360, 7)):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 218, 118))
    draw.rounded_rectangle((130, 170, 780, 920), radius=44, fill=(14, 22, 38), outline=(112, 170, 220), width=6)
    draw.rounded_rectangle((270, 275, 640, 790), radius=36, fill=(22, 36, 58), outline=(170, 220, 255), width=5)
    draw.ellipse((390, 360, 520, 490), fill=(196, 154, 124))
    draw.rounded_rectangle((350, 480, 560, 705), radius=42, fill=(34, 78, 122))
    draw.rounded_rectangle((470, 520, 605, 760), radius=24, fill=(8, 12, 20), outline=(180, 225, 255), width=4)
    draw.text((125, 965), "PUBLIC-DOMAIN E2E DOCUMENTARY FIXTURE", fill=(225, 235, 245))
    image.save(FIXTURE_PATH, "JPEG", quality=94)


def _fixture_search(query: str, media_type: str, per_page: int):
    if media_type != "photo":
        return [], None
    url = f"{_fixture_base_url}/documentary-source.jpg"
    description = (
        "Earth at night city lights satellite orbit Apollo 11 astronaut moon NASA archive "
        "historical photograph person smartphone phone screen dark room over shoulder "
        "real documentary public domain source"
    )
    candidate = AssetCandidate(
        provider="e2e_fixture",
        provider_asset_id=f"fixture-{abs(hash(query))}",
        media_type="photo",
        source_url=url,
        preview_url=url,
        download_url=url,
        creator="AI Documentary OS E2E Fixture",
        creator_url="http://localhost",
        width=1920,
        height=1080,
        duration_seconds=None,
        license_name="Public Domain Test Fixture",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        attribution="Public-domain fixture generated locally for deterministic validation.",
        description=description,
        keywords=description.split(),
        query_variant=query,
    )
    return [candidate][: max(1, per_page)], None


_build_fixture()
_handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
_server = ThreadingHTTPServer(("127.0.0.1", 0), _handler)
_fixture_base_url = f"http://127.0.0.1:{_server.server_port}"
_thread = threading.Thread(target=_server.serve_forever, daemon=True)
_thread.start()

PROVIDERS["e2e_fixture"] = ProviderSpec(
    name="e2e_fixture",
    label="Deterministic Public-Domain E2E Fixture",
    media_types=("photo",),
    env_key=None,
    setup_hint="Built into the E2E harness only.",
    source_url=_fixture_base_url,
    search=_fixture_search,
)

from run_asset_first_e2e import main  # noqa: E402

print(
    {
        "resolved_ffmpeg": resolved_ffmpeg,
        "timeline_ffmpeg": timeline_builder.ffmpeg_executable(),
        "finance_ffmpeg": finance_engine.FFMPEG_NAME,
        "database_url": os.environ["DATABASE_URL"],
        "asset_provider_timeout_seconds": os.environ["ASSET_PROVIDER_TIMEOUT_SECONDS"],
        "asset_provider_allowlist": os.environ["ASSET_PROVIDER_ALLOWLIST"],
        "asset_provider_query_limit": os.environ["ASSET_PROVIDER_QUERY_LIMIT"],
        "fixture_base_url": _fixture_base_url,
    },
    flush=True,
)

try:
    main()
finally:
    _server.shutdown()
    _server.server_close()
    shutil.rmtree(FIXTURE_DIR, ignore_errors=True)
    E2E_DATABASE_PATH.unlink(missing_ok=True)
