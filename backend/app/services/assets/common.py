from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from ...schemas import AssetCandidate


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    label: str
    media_types: tuple[str, ...]
    env_key: str | None
    setup_hint: str
    source_url: str
    search: Callable[[str, str, int], tuple[list[AssetCandidate], int | None]]
    track_selection: Callable[[str], None] | None = None

    @property
    def configured(self) -> bool:
        return self.env_key is None or bool(os.getenv(self.env_key, "").strip())


def _provider_timeout(default: int) -> int:
    raw = os.getenv("ASSET_PROVIDER_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(3, min(value, 60))


def json_request(
    url: str,
    *,
    provider_label: str,
    headers: dict[str, str] | None = None,
    timeout: int = 25,
) -> tuple[dict[str, Any], dict[str, str]]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Documentary-OS/0.9.1",
            **(headers or {}),
        },
    )
    effective_timeout = _provider_timeout(timeout)
    try:
        with urlopen(request, timeout=effective_timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload, dict(response.headers.items())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"{provider_label} request failed ({exc.code}): {detail[:300]}",
        ) from exc
    except (URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", str(exc))
        raise HTTPException(
            status_code=502,
            detail=(
                f"Could not reach {provider_label} within {effective_timeout}s: {reason}"
            ),
        ) from exc


def rate_limit_remaining(headers: dict[str, str]) -> int | None:
    value = {key.lower(): value for key, value in headers.items()}.get(
        "x-ratelimit-remaining"
    )
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def public_search_url(provider: str, query: str, media_type: str) -> str:
    encoded = quote(query.strip(), safe="")
    if provider == "pixabay":
        return (
            f"https://pixabay.com/videos/search/{encoded}/"
            if media_type == "video"
            else f"https://pixabay.com/images/search/{encoded}/"
        )
    if provider == "unsplash":
        return f"https://unsplash.com/s/photos/{encoded}"
    if provider == "wikimedia":
        return (
            "https://commons.wikimedia.org/w/index.php?"
            f"search={encoded}&title=Special:MediaSearch&type=image"
        )
    if provider == "nasa":
        return f"https://images.nasa.gov/search?q={encoded}&media={media_type}"
    return (
        f"https://www.pexels.com/search/videos/{encoded}/"
        if media_type == "video"
        else f"https://www.pexels.com/search/{encoded}/"
    )
