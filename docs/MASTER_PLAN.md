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
- **Rights-aware:** Preserve source, creator, attribution, license, and usage-guideline metadata with selected media.
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

- Search multiple replaceable media providers from each scene
- Pixabay photo and video integration
- Unsplash photography integration and download-event tracking
- Wikimedia Commons historical-image integration
- NASA image and video integration
- Optional Pexels adapter
- Preview and attach candidate assets
- Persist provider, creator, attribution, source, media-file, and license metadata
- Track visual coverage across the documentary
- Download selected media into organized local project folders
- Add AI-generation fallbacks when stock and archival sources are insufficient

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

**Sprint 4: Multi-Provider Asset Planner**

Definition of done:

- A provider registry separates the Asset Planner from any single stock-media API.
- Pixabay and Unsplash use locally stored keys without exposing them to the frontend or GitHub.
- Wikimedia Commons and NASA work without keys.
- Pexels remains an optional adapter rather than a blocker.
- Provider capabilities determine whether photo or video search is available.
- Candidate cards display creator, source, provider, and rights information.
- Selected-asset rights metadata persists in SQLite.
- Existing local databases upgrade without losing projects or selections.
- Automated backend tests and a frontend production build run in CI.

## Next priority

Download selected media to a predictable local folder structure, create a per-project asset manifest, and generate the first machine-readable timeline assembly plan.
