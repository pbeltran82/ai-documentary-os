from __future__ import annotations

from typing import Any


FINANCE_FAMILY_ID = "finance_motion"
SUBSCRIBE_CTA_TEMPLATE_ID = "subscribe_cta"
SUBSCRIBE_CTA_MINIMUM_DURATION_SECONDS = 4.0


def effective_exact_visual_duration(
    family_id: str,
    template_id: str,
    requested_duration_seconds: float,
) -> float:
    """Return the editorially safe duration for a generated exact visual."""
    duration = max(1.0, float(requested_duration_seconds))
    if (
        family_id == FINANCE_FAMILY_ID
        and template_id == SUBSCRIBE_CTA_TEMPLATE_ID
    ):
        return max(duration, SUBSCRIBE_CTA_MINIMUM_DURATION_SECONDS)
    return duration


def exact_visual_identity(asset: Any) -> tuple[str | None, str | None]:
    """Read an exact-visual family and template from persisted asset metadata."""
    if asset is None or str(getattr(asset, "provider", "")).lower() != "generated":
        return None, None

    source_url = str(getattr(asset, "source_url", ""))
    prefix = "local://exact-visual/"
    if source_url.startswith(prefix):
        path = source_url[len(prefix):].split("/")
        if len(path) >= 2:
            return path[0] or None, path[1] or None

    provider_asset_id = str(getattr(asset, "provider_asset_id", ""))
    if "subscribe_cta" in provider_asset_id:
        return FINANCE_FAMILY_ID, SUBSCRIBE_CTA_TEMPLATE_ID
    return None, None


def effective_scene_duration(scene: Any) -> float:
    """Extend only generated scenes with an explicit minimum-hold rule."""
    requested = max(1.0, float(scene.duration_seconds))
    family_id, template_id = exact_visual_identity(scene.selected_asset)
    if family_id is None or template_id is None:
        return requested
    return effective_exact_visual_duration(family_id, template_id, requested)


def is_subscribe_cta_clip(clip: dict[str, Any]) -> bool:
    return (
        str(clip.get("exact_visual_family_id", "")) == FINANCE_FAMILY_ID
        and str(clip.get("exact_visual_template_id", ""))
        == SUBSCRIBE_CTA_TEMPLATE_ID
    )
