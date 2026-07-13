# AI Prompt Library

Reusable prompts for producing cinematic, factual, high-retention documentaries with a consistent workflow.

## How to use this library

1. Replace every value inside `{{double_braces}}`.
2. Keep outputs grounded in verifiable sources.
3. Flag uncertainty instead of inventing details.
4. Optimize every stage for clarity, retention, and production efficiency.
5. Save episode-specific outputs inside the matching `episodes/episode-XXX/` folder.

---

## 1. Topic Opportunity Analyzer

```text
You are a YouTube documentary strategist.

Evaluate this topic:
{{topic}}

Target audience:
{{audience}}

Channel positioning:
{{channel_positioning}}

Analyze:
1. Audience curiosity and emotional pull
2. Strength of the central mystery, conflict, or transformation
3. Search and recommendation potential
4. Visual storytelling potential
5. Availability of credible sources
6. Competition and differentiation opportunities
7. Risks: weak evidence, legal sensitivity, graphic content, or limited visuals

Return:
- One-sentence verdict
- Opportunity score from 1-10
- Best documentary angle
- Core viewer promise
- Three stronger title directions
- Recommended runtime
- Go / revise / reject recommendation
```

## 2. Research Director

```text
Act as the lead researcher for a premium documentary.

Topic:
{{topic}}

Central question:
{{central_question}}

Research the subject as a structured investigation.

Create:
1. Background and timeline
2. Key people, organizations, and locations
3. Confirmed facts
4. Disputed claims and competing interpretations
5. Primary-source opportunities
6. Best secondary sources
7. Important statistics with dates and context
8. Visual evidence to locate: archives, maps, documents, footage, photographs, diagrams
9. Gaps that require further verification
10. A source log

Rules:
- Separate facts from allegations and interpretation.
- Never fabricate quotations, dates, statistics, or sources.
- Mark every uncertain claim clearly.
- Prefer primary and authoritative sources.
```

## 3. Story Angle Generator

```text
You are a documentary showrunner.

Using this research summary:
{{research_summary}}

Generate five distinct story angles.

For each angle include:
- Logline
- Central question
- Main conflict
- Emotional engine
- Why viewers will keep watching
- Best opening image
- Midpoint revelation
- Ending payoff
- Main weakness or production risk

Then rank all five and select the strongest angle for:
1. Viewer retention
2. Factual integrity
3. Visual potential
4. Originality
5. Production feasibility
```

## 4. Documentary Outline Architect

```text
Design a high-retention documentary outline.

Topic:
{{topic}}

Chosen angle:
{{angle}}

Target runtime:
{{runtime_minutes}} minutes

Audience:
{{audience}}

Build a scene-by-scene outline with:
- Cold open
- Inciting question
- Context setup
- Escalating discoveries
- Reversals or complications
- Midpoint revelation
- Final investigation or confrontation
- Resolution
- Lasting takeaway

For every section provide:
- Purpose
- Narration summary
- Key evidence
- Suggested visuals
- Emotional tone
- Open loop created
- Open loop resolved
- Estimated duration

Avoid repetitive exposition. Introduce a meaningful new question, fact, image, or emotional shift every 30-60 seconds.
```

## 5. Cinematic Scriptwriter

```text
You are writing a premium faceless YouTube documentary.

Outline:
{{outline}}

Tone:
{{tone}}

Target runtime:
{{runtime_minutes}} minutes

Write the complete narration script.

Requirements:
- Begin with a compelling cold open, not a generic introduction.
- Use clear, vivid, conversational language.
- Vary sentence length for rhythm.
- Build curiosity through unanswered questions and delayed reveals.
- Ground every factual claim in the supplied research.
- Clearly qualify disputed or uncertain claims.
- Avoid filler, clichés, fake drama, and repeated points.
- Add natural transitions between scenes.
- End with a satisfying answer, implication, or unresolved question.

Format each scene as:
SCENE NUMBER — SCENE TITLE
NARRATION:
[voice-over]

VISUAL DIRECTION:
[footage, archive, maps, graphics, text, or reenactment ideas]

AUDIO DIRECTION:
[music, ambience, silence, or sound design]
```

## 6. Retention Editor

```text
Act as a ruthless documentary retention editor.

Review this script:
{{script}}

Identify:
- Weak opening lines
- Slow exposition
- Repetition
- Predictable transitions
- Claims needing evidence
- Confusing chronology
- Sections with no visual change
- Missing stakes
- Open loops that are never resolved
- Moments where viewers may leave

Then provide:
1. A scene-by-scene retention diagnosis
2. Specific cuts and rewrites
3. A stronger cold open
4. Better transitions
5. Suggested pattern interrupts
6. A revised script preserving factual accuracy

Do not manufacture suspense or exaggerate claims.
```

## 7. Fact-Check and Source Audit

```text
Audit the documentary script below for factual integrity.

Script:
{{script}}

Source notes:
{{source_notes}}

For every factual claim, classify it as:
- Verified
- Supported but needs stronger sourcing
- Disputed
- Unverified
- Opinion or interpretation

Return a table with:
- Claim
- Classification
- Supporting source
- Publication date
- Required correction or qualification

Also flag:
- Misleading wording
- Missing context
- Outdated statistics
- Quotes without original sources
- Timeline inconsistencies
- Legal or reputational risk

Do not rewrite uncertainty as certainty.
```

## 8. Visual Storyboard Generator

```text
Turn this documentary scene into a practical visual storyboard.

Scene narration:
{{scene_narration}}

Available asset types:
{{available_assets}}

For each shot provide:
- Shot number
- Duration
- Visual description
- Camera movement
- Source type: archive, stock, AI-generated, map, document, motion graphic, screen capture, or original footage
- On-screen text
- Transition
- Sound cue
- Purpose in the story

Maintain visual variety and avoid showing generic stock footage that merely repeats the narration.
```

## 9. AI Image Prompt Builder

```text
Convert this shot description into a production-ready image-generation prompt.

Shot:
{{shot_description}}

Documentary visual identity:
{{visual_identity}}

Return:
- Main prompt
- Negative prompt
- Aspect ratio recommendation
- Composition notes
- Lighting notes
- Historical accuracy requirements
- Continuity details that must remain consistent across shots

Rules:
- Do not depict invented events as authentic archival evidence.
- Clearly label reenactments or illustrative visuals in the production notes.
- Avoid logos, watermarks, illegible text, and anachronisms.
```

## 10. Narration Performance Director

```text
Prepare this narration for an AI voice actor.

Narration:
{{narration}}

Desired voice:
{{voice_description}}

Add performance markup for:
- Pauses
- Emphasis
- Pace changes
- Emotional shifts
- Pronunciation guidance
- Sentence grouping

Keep the delivery credible and restrained. Avoid trailer-style overacting unless the scene explicitly requires it.
```

## 11. YouTube Packaging Strategist

```text
Create a complete YouTube packaging package for this documentary.

Documentary summary:
{{summary}}

Audience:
{{audience}}

Generate:
1. Ten title options under 70 characters
2. Three thumbnail concepts with one clear focal idea each
3. Thumbnail text options using no more than four words
4. A search-friendly description
5. Chapter titles
6. A pinned comment
7. Five community-post hooks

Titles must create curiosity without making claims the documentary cannot support.
```

## 12. Short-Form Repurposing Producer

```text
Repurpose this documentary into short-form videos.

Full script:
{{script}}

Create {{number_of_clips}} standalone clips for YouTube Shorts, TikTok, and Instagram Reels.

For each clip provide:
- Hook in the first two seconds
- 30-60 second script
- Visual sequence
- Caption text
- On-screen text
- Suggested title
- Call to action that leads naturally to the full documentary

Each clip must deliver a complete insight while preserving curiosity about the full story.
```

---

## Quality Gate

Before approving any AI output, confirm:

- [ ] The central viewer promise is clear.
- [ ] Claims are traceable to credible sources.
- [ ] Uncertainty is labeled honestly.
- [ ] The opening earns attention immediately.
- [ ] Each scene advances the investigation or emotional journey.
- [ ] Visuals add information rather than duplicate narration.
- [ ] The ending resolves the primary question or explains why it remains unresolved.
- [ ] The output can be reused or automated in future episodes.
