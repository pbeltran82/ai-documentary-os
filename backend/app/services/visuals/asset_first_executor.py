from __future__ import annotations

from fastapi import HTTPException

from ...schemas import ShotBrief, VisualDirectorResponse
from ..assets import PROVIDERS
from ..visual_director import director_shortlist, provider_priority, unique_phrases
from ..visual_feedback import scene_feedback
from .types import VisualPlan


def _media_word(media_type: str) -> str:
    return "documentary footage" if media_type == "video" else "documentary photo"


def build_architecture_shot_brief(
    scene,
    plan: VisualPlan,
    media_type: str,
) -> ShotBrief:
    """Build provider queries from the planned shot instead of generic narration."""
    media_word = _media_word(media_type)
    intent = plan.intent
    shot = plan.shot
    asset = plan.asset

    subject_terms = list(intent.subject_terms) or list(asset.search_terms[:2])
    action_terms = list(intent.action_terms)
    setting_terms = list(intent.setting_terms)
    concept_terms = list(intent.concept_terms)

    subject = shot.focal_subject or " ".join(subject_terms[:3]) or "documentary subject"
    action = (
        f"Observe the subject {action_terms[0]}ing in a believable moment"
        if action_terms
        else "Capture an authentic action or consequence rather than a posed explanation"
    )
    setting = (
        " ".join(setting_terms[:3])
        if setting_terms
        else shot.background
    )
    framing = (
        f"{shot.shot_type.value.replace('_', ' ')}; "
        f"{shot.composition.value.replace('_', ' ')}; "
        f"room for a {shot.camera_move.value.replace('_', ' ')}"
    )
    mood = f"{intent.emotional_tone}; {shot.atmosphere}"

    must_show = unique_phrases(
        [
            *subject_terms,
            *action_terms,
            *setting_terms,
            *concept_terms[:2],
            *asset.search_terms,
        ],
        5,
    )
    must_avoid = unique_phrases(asset.avoid_terms, 8)

    core = " ".join(asset.search_terms[:4]).strip()
    subject_query = " ".join(
        [
            *subject_terms[:2],
            *action_terms[:1],
            *setting_terms[:2],
        ]
    ).strip()
    concept_query = " ".join([*subject_terms[:2], *concept_terms[:2]]).strip()
    query_variants = unique_phrases(
        [
            f"{subject_query} {media_word}" if subject_query else "",
            f"{core} {media_word}" if core else "",
            f"{concept_query} cinematic {media_word}" if concept_query else "",
            f"{subject} {setting} {media_word}",
        ],
        4,
    )

    return ShotBrief(
        scene_id=scene.id,
        subject=subject,
        action=action,
        setting=setting,
        framing=framing,
        mood=mood,
        must_show=must_show or [subject],
        must_avoid=must_avoid,
        query_variants=query_variants,
    )


def search_architecture_candidates(
    scene,
    plan: VisualPlan,
    media_type: str,
    per_page: int = 6,
) -> VisualDirectorResponse:
    """Search every configured source using the architecture-owned shot brief."""
    brief = build_architecture_shot_brief(scene, plan, media_type)
    configured = [
        name
        for name, spec in PROVIDERS.items()
        if spec.configured and media_type in spec.media_types
    ]
    provider_names = provider_priority(media_type, brief, configured)
    all_candidates = []
    remaining_values: list[int] = []
    searched_providers: list[str] = []
    queries = brief.query_variants[:2]

    for provider_name in provider_names:
        provider = PROVIDERS[provider_name]
        provider_succeeded = False
        provider_queries = queries[:1] if provider_name == "wikimedia" else queries
        for query in provider_queries:
            try:
                candidates, remaining = provider.search(
                    query,
                    media_type,
                    max(6, per_page),
                )
            except HTTPException:
                continue
            provider_succeeded = True
            all_candidates.extend(
                candidate.model_copy(update={"query_variant": query})
                for candidate in candidates
            )
            if remaining is not None:
                remaining_values.append(remaining)
        if provider_succeeded:
            searched_providers.append(provider_name)

    feedback = scene_feedback(scene.project_id, scene.id)
    rejected_ids = {
        (str(item.get("provider") or ""), str(item.get("provider_asset_id") or ""))
        for item in feedback
    }
    candidates = director_shortlist(
        scene,
        brief,
        all_candidates,
        rejected_ids,
        per_page,
    )
    return VisualDirectorResponse(
        media_type=media_type,
        shot_brief=brief,
        search_queries=queries,
        providers_searched=searched_providers,
        rate_limit_remaining=min(remaining_values) if remaining_values else None,
        rejected_count=len(feedback),
        candidates=candidates,
    )
