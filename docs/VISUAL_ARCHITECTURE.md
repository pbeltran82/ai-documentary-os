# Visual Architecture v1

AI Documentary OS now plans visuals from scene meaning before selecting a renderer.
The goal is to prevent future documentaries from falling back to repeated slides,
primitive diagrams, or topic-specific rescue patches.

## Pipeline

1. `scene_intent.py` extracts human subjects, environments, interfaces, data,
   comparisons, history, tone, and closing intent from narration and direction.
2. `visual_strategy.py` chooses a reusable visual family and sets hard text,
   label, subject, realism, source, and depth requirements.
3. `shot_planner.py` assigns shot size, composition, camera move, focal subject,
   foreground, background, atmosphere, and minimum depth.
4. A renderer or asset provider executes the provider-neutral `VisualPlan`.
5. `quality_gate.py` rejects frames that are too textual, panel-heavy, centered,
   empty, flat, static, or missing a subject.

## Visual families

- `cinematic_real_world`
- `editorial_symbolic`
- `interface_observational`
- `data_explainer`
- `timeline_historical`
- `comparison_contrast`
- `conclusion_cta`

Real-world and subject-led scenes are preferred. `data_explainer` is intentionally
restricted to narration that truly depends on quantities, ranking, process, or a
timeline. Consecutive explainer scenes are automatically rerouted for variety.

## Current renderer integration

`visuals/runtime.py` registers the first cinematic editorial renderer family with
Tech & Behavior Motion. It replaces the old grid, repeated panels, and large
instructional headings with full-frame environments, human-scale subjects,
foreground framing, atmospheric depth, observational phone shots, perspective
roads, physical data trails, mirror metaphors, and a thesis-led ending.

Registration is idempotent and does not wrap render functions, avoiding the
recursive reload failure fixed in PR #42.

## Next renderer milestones

- Execute `stock_or_generated` plans with rights-safe real-world media.
- Add generated-image provider adapters behind the same `VisualPlan` contract.
- Persist quality metrics and retry decisions per scene.
- Track recent families and compositions project-wide during batch production.
- Add contact-sheet review and automatic low-score regeneration.
