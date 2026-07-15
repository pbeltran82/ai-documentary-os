# AI Documentary OS — Master Plan

## Vision

Build a local-first AI production operating system that transforms a documentary idea into an organized, editable, publishable production package.

## Mission

Reduce the time and friction required to produce documentaries by automating repetitive production work while preserving human creative control.

## North Star

> We do not automate storytelling. We automate everything around storytelling.

## Primary workflow

1. Idea and project brief
2. Research and source verification
3. Story architecture and script
4. Scene breakdown and timing
5. Asset search, selection, and generation
6. Automatic first-pass timeline assembly
7. Human polish and quality control
8. Export and publishing package

## Product principles

- **Local first:** Personal projects and media remain on the creator's machine by default.
- **Human approval:** The creator controls story, tone, sources, visuals, and final edits.
- **Automate repetition:** Search, file organization, timing, status tracking, and assembly are prime automation targets.
- **Structured data:** Projects, scenes, assets, sources, and exports are stored as editable records rather than disposable chat output.
- **Provider independence:** AI, stock-media, voice, and video providers should be replaceable.
- **Working milestones:** Every sprint ends with a runnable, testable improvement.

## Roadmap

### Phase 1 — Foundation ✅

- Local FastAPI backend
- React mission-control dashboard
- SQLite project storage
- Documentary project creation
- Bird's-eye production pipeline

### Phase 2 — Scene Engine ✅

- Import plain narration or a structured scene plan
- Split narration into timed scenes
- Preserve supplied timecodes and labeled production fields
- Store search keywords, visual intent, preferred asset type, and asset status
- Review and edit scene timing and metadata
- Recalculate downstream timestamps after edits or deletion

### Phase 3 — Asset Planner 🚧

- Search Pexels photos and videos from each scene
- Preview and attach candidate assets
- Persist provider, creator, attribution, source, preview, and media-file metadata
- Track visual coverage across the documentary
- Download selected media into organized local project folders
- Add provider-independent adapters and AI-generation fallbacks

### Phase 4 — Timeline Builder

- Align assets to narration timings
- Trim and sequence assets automatically
- Add simple motion to still images
- Produce a first-pass MP4 and editing manifest

### Phase 5 — Production Intelligence

- Research with citations
- Script and outline assistance
- Voiceover integration
- Music and sound recommendations
- Thumbnail and YouTube packaging

## Current sprint

**Sprint 3: Asset Planner MVP**

Definition of done:

- A project can switch between the Scene Engine and Asset Planner.
- Each scene opens with its narration, timing, visual intent, and suggested search query.
- Pexels photo and video results can be searched and previewed with attribution.
- A candidate visual can be selected, replaced, or removed.
- Selected-asset metadata persists in SQLite.
- The app works safely without an API key by showing setup guidance and a direct Pexels search link.

## Next priority

Download selected media to a predictable local folder structure and generate a machine-readable timeline manifest for the first automatic assembly pass.
