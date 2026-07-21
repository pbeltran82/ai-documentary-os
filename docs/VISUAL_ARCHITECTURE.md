# Visual Architecture v2

AI Documentary OS now plans visuals from scene meaning before selecting either a
real asset or a procedural renderer. The goal is to prevent future documentaries
from falling back to repeated slides, primitive diagrams, or topic-specific rescue
patches.

## Pipeline

1. `scene_intent.py` extracts human subjects, environments, interfaces, data,
   comparisons, history, tone, and closing intent from narration and direction.
2. `visual_strategy.py` chooses a reusable visual family and source mode.
3. `shot_planner.py` assigns shot size, composition, camera move, focal subject,
   foreground, background, atmosphere, and minimum depth.
4. `asset_director.py` converts the plan into an executable source decision:
   `asset_first` or `exact_visual`.
5. The project executor uses the rights-aware Visual Director for real footage and
   photography, or Exact Visual Studio only when a controlled explainer is justified.
6. `quality_gate.py` rejects generated frames that are too textual, panel-heavy,
   centered, empty, flat, static, or missing a subject.

## Source policy

The default hierarchy is:

1. defensible stock video
2. defensible documentary photography with editorial motion
3. generated cinematic stills when a provider is added behind the same contract
4. procedural graphics only for true data/process explanation and the final CTA

Human, environmental, device-use, historical, comparison, and metaphor scenes are
asset-first. This is the central anti-slide rule.

## Visual families

- `cinematic_real_world`
- `editorial_symbolic`
- `interface_observational`
- `data_explainer`
- `timeline_historical`
- `comparison_contrast`
- `conclusion_cta`

`data_explainer` is intentionally restricted to narration that truly depends on
quantities, ranking, or process. Consecutive explainers are rerouted to asset-led
metaphors for pacing variety.

## API

- `GET /api/scenes/{scene_id}/visual-architecture-plan`
- `GET /api/projects/{project_id}/visual-architecture-plan`
- `POST /api/scenes/{scene_id}/visual-architecture-execute`
- `POST /api/projects/{project_id}/visual-architecture-execute`

The project executor preserves existing visuals unless `replace_existing=true`.
Asset-first scenes search all configured providers, apply rights, evidence, quality,
and diversity gates, then download and attach the highest-ranked surviving asset.
Procedural scenes use the existing exact-visual renderer and refresh project manifests
once execution completes.

## App control

The **Visual Architecture** launcher shows the project-wide split between real assets
and exact visuals, the planned shot language for each scene, and the execution result.
This makes the source decision reviewable instead of hiding it inside topic-specific
renderer code.

## Procedural fallback

`visuals/runtime.py` keeps the cinematic editorial renderer available for explainers
and explicit manual fallback. Registration is idempotent and does not wrap render
functions, avoiding the recursive reload failure fixed in PR #42. The GitHub preview
workflow renders this fallback only; it is no longer evidence of the default visual
path for human or environmental scenes.

## Current milestone

This branch now delivers source planning and project-wide execution. Its next visual
proof must use selected real assets from configured providers, not the rejected vector
contact sheet from the first iteration.

## Next milestones

- Add a cinematic generated-image provider behind `AssetDirective`.
- Persist visual plans and quality decisions with scene history.
- Add automatic contact sheets using selected real assets and exact-visual frames.
- Add scene-to-scene color, lens, and motion continuity scoring.
