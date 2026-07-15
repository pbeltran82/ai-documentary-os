import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type {
  AssetCandidate,
  AssetSearchResponse,
  MediaType,
  PexelsStatus,
  ProjectDetail,
  Scene,
} from "../types";

interface AssetPlannerProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenScenes: () => void;
  onRefreshProject: () => Promise<void>;
}

function sceneQuery(scene: Scene): string {
  if (scene.search_keywords.length > 0) {
    return scene.search_keywords.slice(0, 5).join(" ");
  }
  return scene.visual_intent || scene.narration;
}

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(whole / 60);
  const remaining = whole % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

export function AssetPlanner({
  project,
  loading,
  error,
  onBack,
  onOpenScenes,
  onRefreshProject,
}: AssetPlannerProps) {
  const [activeSceneId, setActiveSceneId] = useState<number | null>(
    project.scenes[0]?.id ?? null,
  );
  const [query, setQuery] = useState("");
  const [mediaType, setMediaType] = useState<MediaType>("video");
  const [status, setStatus] = useState<PexelsStatus | null>(null);
  const [results, setResults] = useState<AssetSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [localError, setLocalError] = useState("");

  const activeScene = useMemo(
    () => project.scenes.find((scene) => scene.id === activeSceneId) ?? project.scenes[0],
    [activeSceneId, project.scenes],
  );

  const selectedCount = project.scenes.filter((scene) => scene.selected_asset).length;
  const completionPercent =
    project.scenes.length === 0
      ? 0
      : Math.round((selectedCount / project.scenes.length) * 100);

  useEffect(() => {
    void api
      .getPexelsStatus()
      .then(setStatus)
      .catch((err: unknown) =>
        setLocalError(err instanceof Error ? err.message : "Unable to check Pexels"),
      );
  }, []);

  useEffect(() => {
    if (!activeScene) return;
    setQuery(sceneQuery(activeScene));
    setMediaType(
      activeScene.preferred_asset_type === "stock_image" ? "photo" : "video",
    );
    setResults(null);
    setLocalError("");
  }, [activeScene?.id]);

  async function search() {
    if (!activeScene || query.trim().length < 2) return;
    setSearching(true);
    setLocalError("");
    try {
      setResults(
        await api.searchAssets(activeScene.id, {
          query: query.trim(),
          media_type: mediaType,
        }),
      );
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to search Pexels");
    } finally {
      setSearching(false);
    }
  }

  async function selectCandidate(candidate: AssetCandidate) {
    if (!activeScene) return;
    setSelectingId(candidate.provider_asset_id);
    setLocalError("");
    try {
      await api.selectAsset(activeScene.id, candidate);
      await onRefreshProject();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to select asset");
    } finally {
      setSelectingId(null);
    }
  }

  async function removeSelection() {
    if (!activeScene) return;
    setLocalError("");
    try {
      await api.removeSelectedAsset(activeScene.id);
      await onRefreshProject();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to remove asset");
    }
  }

  if (!activeScene) {
    return (
      <main className="workspace">
        <button className="back-button" onClick={onOpenScenes}>← Scene Engine</button>
        <section className="panel empty-state">
          <div className="empty-icon">🎞️</div>
          <h3>Create scenes before searching for assets.</h3>
          <button className="secondary-button" onClick={onOpenScenes}>
            Open Scene Engine
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="workspace asset-workspace">
      <header className="project-topbar">
        <div>
          <button className="back-button" onClick={onBack}>← Mission Control</button>
          <p className="eyebrow">ASSET PLANNER</p>
          <h2>{project.title}</h2>
          <p className="project-summary">
            Search, preview, attribute, and attach a visual to every timed scene.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={onOpenScenes}>Scene Engine</button>
          <span className="status-pill">Pexels MVP v0.3</span>
        </div>
      </header>

      {(error || localError) && (
        <div className="error-banner">{localError || error}</div>
      )}

      <section className="stats-grid four-up" aria-label="Asset overview">
        <article className="stat-card">
          <span>Scenes</span>
          <strong>{project.scenes.length}</strong>
        </article>
        <article className="stat-card">
          <span>Visuals selected</span>
          <strong>{selectedCount}</strong>
        </article>
        <article className="stat-card">
          <span>Still missing</span>
          <strong>{project.scenes.length - selectedCount}</strong>
        </article>
        <article className="stat-card accent">
          <span>Coverage</span>
          <strong>{completionPercent}%</strong>
        </article>
      </section>

      <div className="asset-layout">
        <aside className="panel scene-rail">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SCENE QUEUE</p>
              <h3>Visual decisions</h3>
            </div>
          </div>
          <div className="scene-rail-list">
            {project.scenes.map((scene) => (
              <button
                key={scene.id}
                className={`scene-rail-item ${scene.id === activeScene.id ? "active" : ""}`}
                onClick={() => setActiveSceneId(scene.id)}
              >
                <div>
                  <strong>Scene {String(scene.scene_number).padStart(2, "0")}</strong>
                  <span>
                    {formatTime(scene.start_seconds)}–{formatTime(scene.end_seconds)}
                  </span>
                </div>
                <span className={`asset-dot ${scene.selected_asset ? "selected" : "missing"}`} />
              </button>
            ))}
          </div>
        </aside>

        <section className="asset-main">
          <article className="panel scene-brief">
            <div className="section-heading">
              <div>
                <p className="eyebrow">
                  SCENE {String(activeScene.scene_number).padStart(2, "0")}
                </p>
                <h3>{formatTime(activeScene.start_seconds)}–{formatTime(activeScene.end_seconds)}</h3>
              </div>
              <span className={`asset-status ${activeScene.asset_status}`}>
                {activeScene.asset_status}
              </span>
            </div>
            <p className="scene-narration">{activeScene.narration}</p>
            <div className="brief-grid">
              <div>
                <span>Visual intent</span>
                <strong>{activeScene.visual_intent || "Not defined"}</strong>
              </div>
              <div>
                <span>Search keywords</span>
                <strong>{activeScene.search_keywords.join(", ") || "None"}</strong>
              </div>
            </div>
          </article>

          {activeScene.selected_asset && (
            <article className="panel selected-asset-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">SELECTED VISUAL</p>
                  <h3>Attached to this scene</h3>
                </div>
                <button className="danger-button" onClick={() => void removeSelection()}>
                  Remove
                </button>
              </div>
              <div className="selected-asset-card">
                <img
                  src={activeScene.selected_asset.preview_url}
                  alt={`Selected ${activeScene.selected_asset.media_type}`}
                />
                <div>
                  <strong>
                    {activeScene.selected_asset.media_type === "video" ? "Video" : "Photo"} ·{" "}
                    {activeScene.selected_asset.width}×{activeScene.selected_asset.height}
                  </strong>
                  <p>
                    By{" "}
                    <a href={activeScene.selected_asset.creator_url} target="_blank" rel="noreferrer">
                      {activeScene.selected_asset.creator || "Pexels creator"}
                    </a>
                  </p>
                  <div className="candidate-actions">
                    <a
                      className="ghost-link"
                      href={activeScene.selected_asset.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open on Pexels
                    </a>
                    <a
                      className="ghost-link"
                      href={activeScene.selected_asset.download_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open media file
                    </a>
                  </div>
                </div>
              </div>
            </article>
          )}

          <article className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">PEXELS SEARCH</p>
                <h3>Find candidates for this scene</h3>
              </div>
              <a
                className="provider-link"
                href="https://www.pexels.com"
                target="_blank"
                rel="noreferrer"
              >
                Media provided by Pexels
              </a>
            </div>

            <div className="asset-search-controls">
              <label>
                Search query
                <input value={query} onChange={(event) => setQuery(event.target.value)} />
              </label>
              <label>
                Media type
                <select
                  value={mediaType}
                  onChange={(event) => setMediaType(event.target.value as MediaType)}
                >
                  <option value="video">Stock video</option>
                  <option value="photo">Stock photo</option>
                </select>
              </label>
              <button
                className="primary-button"
                disabled={searching || loading || query.trim().length < 2}
                onClick={() => void search()}
              >
                {searching ? "Searching…" : "Search Pexels"}
              </button>
            </div>

            {status && !status.configured && (
              <div className="setup-card">
                <div>
                  <p className="eyebrow">ONE-TIME SETUP</p>
                  <h4>Connect your free Pexels API key</h4>
                  <p>{status.setup_hint}</p>
                </div>
                <code>PEXELS_API_KEY=your_key_here</code>
                <p>
                  Until connected, the planner still creates a direct Pexels search link.
                </p>
              </div>
            )}

            {results && !results.configured && (
              <div className="manual-search-card">
                <p>The local API key is not configured yet.</p>
                <a
                  className="secondary-button link-button"
                  href={results.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Search this scene directly on Pexels →
                </a>
              </div>
            )}

            {results?.configured && (
              <>
                <div className="result-summary">
                  <span>
                    {results.candidates.length} candidates for “{results.query}”
                  </span>
                  {results.rate_limit_remaining !== null && (
                    <span>{results.rate_limit_remaining} API requests remaining</span>
                  )}
                </div>
                {results.candidates.length === 0 ? (
                  <div className="empty-state compact-empty">
                    <h4>No matching media found.</h4>
                    <p>Try a shorter or more concrete search phrase.</p>
                  </div>
                ) : (
                  <div className="candidate-grid">
                    {results.candidates.map((candidate) => (
                      <article
                        className="candidate-card"
                        key={`${candidate.media_type}-${candidate.provider_asset_id}`}
                      >
                        <div className="candidate-preview">
                          <img
                            src={candidate.preview_url}
                            alt={`Pexels candidate by ${candidate.creator}`}
                            loading="lazy"
                          />
                          <span>{candidate.media_type}</span>
                        </div>
                        <div className="candidate-body">
                          <strong>
                            {candidate.width}×{candidate.height}
                            {candidate.duration_seconds
                              ? ` · ${Math.round(candidate.duration_seconds)}s`
                              : ""}
                          </strong>
                          <p>
                            By{" "}
                            <a href={candidate.creator_url} target="_blank" rel="noreferrer">
                              {candidate.creator || "Pexels creator"}
                            </a>
                          </p>
                          <div className="candidate-actions">
                            <a
                              className="ghost-link"
                              href={candidate.source_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Preview
                            </a>
                            <button
                              className="secondary-button"
                              disabled={selectingId === candidate.provider_asset_id}
                              onClick={() => void selectCandidate(candidate)}
                            >
                              {selectingId === candidate.provider_asset_id
                                ? "Selecting…"
                                : "Select visual"}
                            </button>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </>
            )}
          </article>
        </section>
      </div>
    </main>
  );
}
