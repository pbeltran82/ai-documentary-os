from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from ..models import Scene
from ..schemas import AssetCandidate, ShotBrief

WORD_RE = re.compile(r"[a-z0-9]+")
GENERIC_QUERY_WORDS = {
    "animation",
    "cinematic",
    "concept",
    "footage",
    "photo",
    "stock",
    "video",
}


def words(value: str) -> set[str]:
    return set(WORD_RE.findall(value.lower()))


def clean_phrase(value: str) -> str:
    return " ".join(value.strip().split())


def unique_phrases(values: Iterable[str], limit: int = 8) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        phrase = clean_phrase(value)
        key = phrase.lower()
        if phrase and key not in seen:
            result.append(phrase)
            seen.add(key)
        if len(result) >= limit:
            break
    return result


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def brief_rule(text: str, media_type: str) -> dict[str, Any] | None:
    motion = "video" if media_type == "video" else "photo"

    if contains_any(text, ("never anything left", "nothing left", "no money left", "empty balance")):
        return {
            "subject": "An empty wallet or bank balance at zero",
            "action": "Show that the paycheck has been completely exhausted",
            "setting": "Personal banking, checkout, or an everyday wallet",
            "framing": "Tight, instantly readable close-up",
            "mood": "Consequential and slightly uncomfortable",
            "must_show": ["empty wallet", "zero bank balance", "declined card"],
            "must_avoid": ["dice", "casino", "gambling", "coin stacks", "cash pile"],
            "query_variants": [
                f"empty wallet no money {motion}",
                f"bank account zero balance {motion}",
                f"declined card payment {motion}",
            ],
        }

    if contains_any(text, ("s&p 500", "index fund", "automatic investment", "automatically into")):
        return {
            "subject": "An automatic investment into a broad stock-market index fund",
            "action": "A recurring transfer moves from a paycheck into an investment account",
            "setting": "Modern investing app, bank transfer screen, or market dashboard",
            "framing": "Readable screen or over-the-shoulder financial workflow",
            "mood": "Disciplined, modern, and credible",
            "must_show": ["automatic transfer", "investment app", "stock index chart"],
            "must_avoid": ["loose coins", "coin stacks", "cash pile", "piggy bank"],
            "query_variants": [
                f"automatic investment transfer app {motion}",
                f"index fund investing screen {motion}",
                f"stock market recurring investment {motion}",
            ],
        }

    if contains_any(text, ("like a bill", "legally have to pay", "mandatory payment")):
        return {
            "subject": "A recurring investment treated like a mandatory monthly bill",
            "action": "A scheduled payment is added beside rent and utilities",
            "setting": "Budget planner, recurring-payment screen, or banking calendar",
            "framing": "Clear top-down budget or readable interface",
            "mood": "Structured and non-negotiable",
            "must_show": ["monthly budget", "recurring payment", "scheduled transfer"],
            "must_avoid": ["falling dollar symbols", "cash rain", "generic coins"],
            "query_variants": [
                f"monthly budget recurring payment {motion}",
                f"scheduled bank transfer budget {motion}",
                f"automatic savings bill payment {motion}",
            ],
        }

    if contains_any(text, ("pay themselves first", "pay yourself first")):
        return {
            "subject": "A paycheck that funds savings before spending",
            "action": "Money moves into savings immediately after payday",
            "setting": "Direct-deposit notification or automatic bank transfer",
            "framing": "Close-up of a clear financial action",
            "mood": "Intentional and confident",
            "must_show": ["paycheck deposit", "automatic savings transfer", "savings account"],
            "must_avoid": ["cash pile", "luxury lifestyle", "generic rich person"],
            "query_variants": [
                f"paycheck automatic savings transfer {motion}",
                f"direct deposit savings account {motion}",
                f"pay yourself first banking {motion}",
            ],
        }

    if contains_any(text, ("first 10 percent", "10 percent of your paycheck", "future self")):
        return {
            "subject": "A paycheck split with ten percent reserved for the future",
            "action": "Ten percent routes away before bills and spending",
            "setting": "Paycheck, direct deposit, or simple percentage graphic",
            "framing": "Readable money split with a clear ten-percent cue",
            "mood": "Empowering and forward-looking",
            "must_show": ["paycheck", "ten percent", "savings transfer"],
            "must_avoid": ["random cash", "gambling", "luxury purchases"],
            "query_variants": [
                f"paycheck ten percent savings {motion}",
                f"salary automatic savings split {motion}",
                f"direct deposit future savings {motion}",
            ],
        }

    if contains_any(text, ("rent", "groceries", "go out", "whatever is left")):
        return {
            "subject": "Everyday expenses draining a paycheck",
            "action": "Rent, groceries, dining, and shopping consume the balance",
            "setting": "Household budget and ordinary purchases",
            "framing": "Fast readable expense montage or checkout sequence",
            "mood": "Familiar and slightly stressful",
            "must_show": ["rent payment", "grocery checkout", "spending expenses"],
            "must_avoid": ["empty shopping cart", "abstract person", "unrelated retail"],
            "query_variants": [
                f"rent groceries monthly expenses {motion}",
                f"paycheck spending bills montage {motion}",
                f"grocery checkout household budget {motion}",
            ],
        }

    if contains_any(text, ("invisible wealth machine", "wealth machine")):
        return {
            "subject": "A small automated system steadily producing wealth",
            "action": "Repeated deposits accumulate and grow over time",
            "setting": "Clean financial animation or automated workflow",
            "framing": "Simple visual metaphor with obvious input and growth",
            "mood": "Optimistic and systematic",
            "must_show": ["automatic deposits", "growing investment", "financial system"],
            "must_avoid": ["money rain", "slot machine", "industrial machinery"],
            "query_variants": [
                f"automatic deposits investment growth {motion}",
                f"automated wealth building animation {motion}",
                f"money growth system finance {motion}",
            ],
        }

    if contains_any(text, ("compound interest", "already working for you", "exponential growth")):
        return {
            "subject": "Compound investment growth accelerating over time",
            "action": "A graph curves upward while recurring deposits continue",
            "setting": "Long-term market chart or investment dashboard",
            "framing": "Clear upward curve with room for narration",
            "mood": "Credible, patient, and optimistic",
            "must_show": ["compound growth chart", "recurring deposits", "upward investment graph"],
            "must_avoid": ["generic coin stacks", "cash pile", "random business person"],
            "query_variants": [
                f"compound interest graph animation {motion}",
                f"investment growth curve recurring deposits {motion}",
                f"long term stock market growth chart {motion}",
            ],
        }

    if contains_any(text, ("subscribe", "call to action", "build your blueprint")):
        return {
            "subject": "A clean subscribe call to action",
            "action": "Subscribe, like, and notification controls animate on screen",
            "setting": "Minimal dark or brand-neutral end card",
            "framing": "Centered graphic with safe margins",
            "mood": "Clear and energetic",
            "must_show": ["subscribe button", "notification bell", "call to action"],
            "must_avoid": ["watermark", "channel logo", "busy background"],
            "query_variants": [
                f"subscribe button animation {motion}",
                f"like subscribe bell animation {motion}",
                f"youtube call to action end screen {motion}",
            ],
        }

    return None


def build_shot_brief(scene: Scene, media_type: str) -> ShotBrief:
    context = " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).strip()
    rule = brief_rule(context, media_type)
    if rule is None:
        keyword_phrases = unique_phrases(scene.search_keywords, 4)
        if scene.visual_intent.strip():
            subject = clean_phrase(scene.visual_intent)
        elif keyword_phrases:
            subject = keyword_phrases[0]
        else:
            subject = clean_phrase(scene.narration)
        query_variants = unique_phrases(
            [
                *keyword_phrases,
                scene.visual_intent,
                f"{subject} {'footage' if media_type == 'video' else 'photo'}",
            ],
            4,
        )
        must_show = keyword_phrases[:3] or [subject]
        rule = {
            "subject": subject,
            "action": "Show the narration idea literally and immediately",
            "setting": "A believable documentary context",
            "framing": "Landscape composition with one clear focal point",
            "mood": scene.project.tone if scene.project else "Cinematic and credible",
            "must_show": must_show,
            "must_avoid": ["unrelated nature", "generic filler", "visible watermark"],
            "query_variants": query_variants,
        }

    return ShotBrief(
        scene_id=scene.id,
        subject=rule["subject"],
        action=rule["action"],
        setting=rule["setting"],
        framing=rule["framing"],
        mood=rule["mood"],
        must_show=unique_phrases(rule["must_show"], 5),
        must_avoid=unique_phrases(rule["must_avoid"], 6),
        query_variants=unique_phrases(rule["query_variants"], 4),
    )


def provider_priority(media_type: str, brief: ShotBrief, configured: Iterable[str]) -> list[str]:
    available = set(configured)
    brief_words = words(" ".join([brief.subject, *brief.must_show, *brief.query_variants]))
    if media_type == "video":
        order = ["pixabay", "pexels"]
    else:
        order = ["unsplash", "pixabay", "wikimedia", "pexels"]

    if brief_words & {"space", "earth", "planet", "rocket", "nasa", "satellite"}:
        order = ["nasa", *[item for item in order if item != "nasa"]]
    elif brief_words & {"historic", "history", "archive", "painting", "map", "war"}:
        order = ["wikimedia", *[item for item in order if item != "wikimedia"]]

    return [name for name in order if name in available][:3]


def candidate_text(candidate: AssetCandidate) -> str:
    """Only provider-native descriptive metadata may count as concept evidence."""
    return " ".join(
        [
            candidate.description,
            " ".join(candidate.keywords),
        ]
    ).lower()


def phrase_words(phrase: str) -> set[str]:
    return words(phrase) - GENERIC_QUERY_WORDS


def phrase_match_score(phrase: str, candidate_words: set[str]) -> int:
    """Score complete evidence strongly and reject loose half-phrase coincidences."""
    required = phrase_words(phrase)
    if not required:
        return 0
    overlap = len(required & candidate_words)
    if overlap == len(required):
        return 24
    if len(required) >= 4 and overlap >= math.ceil(len(required) * 0.75):
        return 8
    return 0


def avoid_phrase_matches(phrase: str, candidate_words: set[str]) -> bool:
    required = phrase_words(phrase)
    if not required:
        return False
    overlap = len(required & candidate_words)
    if len(required) == 1:
        return overlap == 1
    return overlap == len(required)


def score_candidate(
    scene: Scene,
    brief: ShotBrief,
    candidate: AssetCandidate,
    selected_creators: set[str],
) -> AssetCandidate:
    candidate_words = words(candidate_text(candidate))
    score = 22.0
    reasons: list[str] = []
    warnings: list[str] = []

    matched_concepts = [
        phrase
        for phrase in brief.must_show
        if phrase_match_score(phrase, candidate_words) >= 24
    ]
    near_concepts = [
        phrase
        for phrase in brief.must_show
        if phrase_match_score(phrase, candidate_words) == 8
    ]

    if matched_concepts:
        score += 32
        score += min(16, max(0, len(matched_concepts) - 1) * 8)
        reasons.append(f"Provider metadata explicitly supports “{matched_concepts[0]}”")
        if len(matched_concepts) > 1:
            reasons.append("Multiple must-show concepts are supported")
    else:
        warnings.append("No complete must-show concept in provider metadata")
        if near_concepts:
            warnings.append("Partial keyword overlap was rejected as insufficient evidence")

    blocked_phrases = [
        phrase
        for phrase in brief.must_avoid
        if avoid_phrase_matches(phrase, candidate_words)
    ]
    if blocked_phrases:
        score -= 45
        warnings.append(f"Must-avoid evidence detected: {blocked_phrases[0]}")

    width = candidate.width
    height = candidate.height
    if width > 0 and height > 0:
        ratio = width / max(height, 1)
        if ratio >= 1.55:
            score += 8
            reasons.append("Landscape framing fits 16:9")
        elif ratio < 1.1:
            score -= 18
            warnings.append("Portrait framing will crop heavily")
        if width >= 1920:
            score += 8
            reasons.append("Full-HD or better source")
        elif width >= 1280:
            score += 4
        elif width < 900:
            score -= 10
            warnings.append("Low source resolution")

    if candidate.media_type == "video" and candidate.duration_seconds:
        if candidate.duration_seconds >= scene.duration_seconds:
            score += 6
            reasons.append("Source duration covers the scene slot")
        elif candidate.duration_seconds < max(1.5, scene.duration_seconds * 0.45):
            score -= 8
            warnings.append("Very short clip requires obvious looping")

    creator_key = candidate.creator.strip().lower()
    if creator_key and creator_key in selected_creators:
        score -= 7
        warnings.append("Creator already appears elsewhere in this project")

    if not matched_concepts:
        score = min(score, 39.0)
    if blocked_phrases:
        score = min(score, 20.0)

    score = max(0.0, min(100.0, round(score, 1)))
    if not reasons:
        reasons.append("Technically usable, but concept evidence is unverified")

    return candidate.model_copy(
        update={
            "director_score": score,
            "director_reasons": reasons[:3],
            "director_warnings": warnings[:3],
        }
    )


def director_shortlist(
    scene: Scene,
    brief: ShotBrief,
    candidates: Iterable[AssetCandidate],
    rejected_ids: set[tuple[str, str]],
    limit: int,
) -> list[AssetCandidate]:
    selected_creators = {
        item.selected_asset.creator.strip().lower()
        for item in scene.project.scenes
        if item.id != scene.id
        and item.selected_asset is not None
        and item.selected_asset.creator.strip()
    }
    scored = [
        score_candidate(scene, brief, candidate, selected_creators)
        for candidate in candidates
        if (candidate.provider, candidate.provider_asset_id) not in rejected_ids
    ]
    scored.sort(key=lambda item: item.director_score, reverse=True)

    shortlist: list[AssetCandidate] = []
    per_provider: dict[str, int] = {}
    per_query: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for candidate in scored:
        identity = (candidate.provider, candidate.provider_asset_id)
        if identity in seen or candidate.director_score < 58:
            continue
        if per_provider.get(candidate.provider, 0) >= 3:
            continue
        query_key = candidate.query_variant.lower()
        if query_key and per_query.get(query_key, 0) >= 2:
            continue
        shortlist.append(
            candidate.model_copy(update={"shortlist_rank": len(shortlist) + 1})
        )
        seen.add(identity)
        per_provider[candidate.provider] = per_provider.get(candidate.provider, 0) + 1
        if query_key:
            per_query[query_key] = per_query.get(query_key, 0) + 1
        if len(shortlist) >= limit:
            break
    return shortlist
