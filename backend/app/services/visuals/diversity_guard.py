from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


def canonical_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value.strip().lower())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


@dataclass
class VisualDiversityGuard:
    """Track project-level visual reuse while scenes are executed in order."""

    asset_ids: set[tuple[str, str]] = field(default_factory=set)
    media_urls: set[str] = field(default_factory=set)
    exact_templates: set[tuple[str, str]] = field(default_factory=set)
    recent_providers: list[str] = field(default_factory=list)
    recent_media_types: list[str] = field(default_factory=list)
    recent_modes: list[str] = field(default_factory=list)

    @classmethod
    def from_project(cls, project, *, ignore_existing: bool = False) -> "VisualDiversityGuard":
        guard = cls()
        if ignore_existing:
            return guard
        for scene in project.scenes:
            asset = scene.selected_asset
            if asset is None:
                continue
            guard.register_asset(asset.provider, asset.provider_asset_id, asset.download_url, asset.media_type)
            if asset.provider == "generated":
                route = str(asset.source_url or "").split("/exact-visual/", 1)
                if len(route) == 2:
                    parts = route[1].split("/")
                    if len(parts) >= 2:
                        guard.exact_templates.add((parts[0], parts[1]))
        return guard

    def rejects_candidate(self, candidate) -> bool:
        identity = (candidate.provider, candidate.provider_asset_id)
        if identity in self.asset_ids:
            return True
        media_url = canonical_url(candidate.download_url or candidate.preview_url)
        if media_url and media_url in self.media_urls:
            return True
        if len(self.recent_providers) >= 2 and self.recent_providers[-2:] == [candidate.provider] * 2:
            return True
        if len(self.recent_media_types) >= 2 and self.recent_media_types[-2:] == [candidate.media_type] * 2:
            return True
        return False

    def register_asset(self, provider: str, provider_asset_id: str, media_url: str, media_type: str) -> None:
        self.asset_ids.add((provider, provider_asset_id))
        normalized = canonical_url(media_url)
        if normalized:
            self.media_urls.add(normalized)
        self.recent_providers.append(provider)
        self.recent_media_types.append(media_type)
        self.recent_modes.append("asset_first")
        del self.recent_providers[:-4]
        del self.recent_media_types[:-4]
        del self.recent_modes[:-4]

    def template_available(self, family_id: str, template_id: str) -> bool:
        return (family_id, template_id) not in self.exact_templates

    def register_exact(self, family_id: str, template_id: str) -> None:
        self.exact_templates.add((family_id, template_id))
        self.recent_providers.append("generated")
        self.recent_media_types.append("video")
        self.recent_modes.append("exact_visual")
        del self.recent_providers[:-4]
        del self.recent_media_types[:-4]
        del self.recent_modes[:-4]


TECH_TEMPLATE_ROTATION = (
    "behavior_prediction_engine",
    "algorithm_chose_you",
    "behavioral_twin",
    "attention_auction",
    "machine_choice_explainer",
    "consequence_map",
)


def choose_unused_exact_template(family_id: str, preferred: str | None, guard: VisualDiversityGuard) -> str | None:
    if family_id != "tech_behavior_motion":
        return preferred
    candidates = [preferred, *TECH_TEMPLATE_ROTATION]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if guard.template_available(family_id, candidate):
            return candidate
    return preferred
