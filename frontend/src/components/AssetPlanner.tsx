import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type {
  AssetCandidate,
  AssetSearchResponse,
  MediaType,
  ProjectDetail,
  ProviderName,
  ProviderStatus,
  Scene,
  ShotBrief,
  VisualDirectorResponse,
  VisualFeedbackReason,
} from "../types";

interface AssetPlannerProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenScenes: () => void;
  onRefreshProject: () => Promise<void>;
}

const providerFallbackLabels: Record<ProviderName, string> = {
  pixabay: "Pixabay",
  unsplash: "Unsplash",
  wikimedia: "Open Archives",
  nasa: "NASA Images",
  pexels: "Pexels",
};

const feedbackLabels: Record<VisualFeedbackReason, string> = {
  wrong_concept: "Wrong concept",
  too_generic: "Too generic",
  repetitive: "Too repetitive",
  poor_quality: "Poor quality",
  bad_style: "Wrong style",
};

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

function defaultProvider(mediaType: MediaType): ProviderName {
  return mediaType === "video" ? "pixabay" : "unsplash";
}

function mediaLabel(mediaType: MediaType): string {
  return mediaType === "video" ? "Stock video" : "Stock photo";
}

function dimensionsLabel(candidate: AssetCandidate): string {
  if (candidate.width > 0 && candidate.height > 0) {
    return `${candidate.width}×${candidate.height}`;
  }
  return "Source resolution";
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
  const [provider, setProvider] = useState<ProviderName>("pixabay");
  const [statuses, setStatuses] = useState<ProviderStatus[]>([]);
  const [brief, setBrief] = useState<ShotBrief | null>(null);
  const [directorResults, setDirectorResults] = useState<VisualDirectorResponse | null>(null);
  const [results, setResults] = useState<AssetSearchResponse | null>(null);
  const [directing, setDirecting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [feedbackReason, setFeedbackReason] =
    useState<VisualFeedbackReason>("wrong_concept");
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

  const activeStatus = statuses.find((item) => item.provider === provider) ?? null;
  const compatibleStatuses = statuses.filter((item) =>
    item.supports_media_types.includes(mediaType),
  );
  const activeProviderLabel =
    activeStatus?.label ?? providerFallbackLabels[provider];

  useEffect(() => {
    void api
      .getProviderStatuses()
      .then(setStatuses)
      .catch((err: unknown) =>
        setLocalError(err instanceof Error ? err.message : "Unable to check providers"),
      );
  }, []);

  useEffect(() => {
    if (!activeScene) return;
    const nextMediaType: MediaType =
      activeScene.preferred_asset_type === "stock_image" ? "photo" : "video";
    setQuery(sceneQuery(activeScene));
    setMediaType(nextMediaType);
    setProvider(defaultProvider(nextMediaType));
    setBrief(null);
    setDirectorResults(null);
    setResults(null);
    setLocalError("");
  }, [activeScene?.id]);

  useEffect(() => {
    if (!activeScene) return;
    let cancelled = false;
    void api
      .getShotBrief(activeScene.id, mediaType)
      .then((nextBrief) => {
        if (!cancelled) setBrief(nextBrief);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLocalError(err instanceof Error ? err.message : "Unable to build shot brief");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeScene?.id, mediaType]);

  useEffect(() => {
    const current = statuses.find((item) => item.provider === provider);
    if (current && !current.supports_media_types.includes(mediaType)) {
      const fallback = statuses.find(
        (item) =>
          item.supports_media_types.includes(mediaType) &&
          (item.configured || !item.requires_key),
      );
      setProvider(fallback?.provider ?? defaultProvider(mediaType));
      setResults(null);
    }
  }, [mediaType, provider, statuses]);

  async function directVisuals() {
    if (!activeScene) return;
    setDirecting(true);
    setLocalError("");
    try {
      const response = await api.directVisuals(activeScene.id, {
        media_type: mediaType,
        provider: "auto",
        per_page: 6,
      });
      setBrief(response.shot_brief);
      setDirectorResults(response);
      setResults(null);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to build director shortlist");
    } finally {
      setDirecting(false);
    }
  }

  async function search() {
    if (!activeScene || query.trim().length < 2) return;
    setSearching(true);
    setLocalError("");
    try {
      setResults(
        await api.searchAssets(activeScene.id, {
          provider,
          query: query.trim(),
          media_type: mediaType,
        }),
      );
      setDirectorResults(null);
    } catch (err) {
      setLocalError(
        err instanceof Error ? err.message : `Unable to search ${activeProviderLabel}`,
      );
    } finally {
      setSearching(false);
    }
  }

  async function selectCandidate(candidate: AssetCandidate) {
    if (!activeScene) return;
    const candidateKey = `${candidate.provider}-${candidate.provider_asset_id}`;
    setSelectingId(candidateKey);
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

  async function rejectCandidate(candidate: AssetCandidate) {
    if (!activeScene || !directorResults) return;
    const candidateKey = `${candidate.provider}-${candidate.provider_asset_id}`;
    setRejectingId(candidateKey);
    setLocalError("");
    try {
      await api.rejectVisual(activeScene.id, candidate, feedbackReason);
      setDirectorResults({
        ...directorResults,
        rejected_count: directorResults.rejected_count + 1,
        candidates: directorResults.candidates.filter(
          (item) =>
            item.provider !== candidate.provider ||
            item.provider_asset_id !== candidate.provider_asset_id,
        ),
      });
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to save visual feedback");
    } finally {
      setRejectingId(null);
    }
  }

  async function resetFeedback() {
    if (!activeScene) return;
    setLocalError("");
    try {
      await api.resetVisualFeedback(activeScene.id);
      await directVisuals();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to reset feedback");
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

  function changeMediaType(nextMediaType: MediaType) {
    setMediaType(nextMediaType);
    setProvider(defaultProvider(nextMediaType));
    setDirectorResults(null);
    setResults(null);
    setLocalError("");
  }

  function changeProvider(nextProvider: ProviderName) {
    setProvider(nextProvider);
    setResults(null);
    setLocalError("");
  }

  function useQueryVariant(value: string) {
    setQuery(value);
    setResults(null);
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

  const selectedAsset = activeScene.selected_asset;
  const selectedProviderLabel = selectedAsset
    ? statuses.find((item) => item.provider === selectedAsset.provider)?.label ??
      providerFallbackLabels[selectedAsset.provider]
    : "";

  function candidateCard(candidate: AssetCandidate, directed: boolean) {
    const candidateKey = `${candidate.provider}-${candidate.provider_asset_id}`;
    const candidateProviderLabel =
      statuses.find((item) => item.provider === candidate.provider)?.label ??
      providerFallbackLabels[candidate.provider];
    return (
      <article className={`candidate-card ${directed ? "director-candidate" : ""}`} key={candidateKey}>
        <div className="candidate-preview">
          <img
            src={candidate.preview_url}
            alt={`${candidateProviderLabel} candidate by ${candidate.creator}`}
            loading="lazy"
          />
          <span>{candidate.media_type}</span>
          <span className="provider-badge">{candidateProviderLabel}</span>
          {directed && candidate.shortlist_rank && (
            <span className="director-rank">#{candidate.shortlist_rank}</span>
          )}
        </div>
        <div className="candidate-body">
          {directed && (
            <div className="director-score-row">
              <strong>{Math.round(candidate.director_score)} / 100</strong>
              <span>Director score</span>
            </div>
          )}
          <strong>
            {dimensionsLabel(candidate)}
            {candidate.duration_seconds
              ? ` · ${Math.round(candidate.duration_seconds)}s`
              : ""}
          </strong>
          {directed && candidate.query_variant && (
            <p className="query-match">Found through “{candidate.query_variant}”</p>
          )}
          {directed && candidate.director_reasons.length > 0 && (
            <ul className="director-reasons">
              {candidate.director_reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          )}
          {directed && candidate.director_warnings.length > 0 && (
            <ul className="director-warnings">
              {candidate.director_warnings.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          )}
          <p>
            By{" "}
            <a href={candidate.creator_url} target="_blank" rel="noreferrer">
              {candidate.creator || candidateProviderLabel}
            </a>
          </p>
          <div className="candidate-license">
            <span>{candidate.license_name || "Review source terms"}</span>
            {candidate.license_url && (
              <a href={candidate.license_url} target="_blank" rel="noreferrer">
                Rights
              </a>
            )}
          </div>
          <div className="candidate-actions">
            <a
              className="ghost-link"
              href={candidate.source_url}
              target="_blank"
              rel="noreferrer"
            >
              Source
            </a>
            {directed && (
              <button
                className="reject-button"
                disabled={rejectingId === candidateKey}
                onClick={() => void rejectCandidate(candidate)}
              >
                {rejectingId === candidateKey ? "Saving…" : "Reject"}
              </button>
            )}
            <button
              className="secondary-button"
              disabled={selectingId === candidateKey}
              onClick={() => void selectCandidate(candidate)}
            >
              {selectingId === candidateKey ? "Selecting…" : "Select visual"}
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <main className="workspace asset-workspace">
      <header className="project-topbar">
        <div>
          <button className="back-button" onClick={onBack}>← Mission Control</button>
          <p className="eyebrow">AI VISUAL DIRECTOR</p>
          <h2>{project.title}</h2>
          <p className="project-summary">
            Translate narration into concrete shots, reject weak concepts, and approve one defensible visual per scene.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={onOpenScenes}>Scene Engine</button>
          <span className="status-pill">Universal Visual Feed v0.9.2</span>
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

      <section className="provider-overview" aria-label="Connected asset providers">
        {statuses.map((item) => (
          <article
            key={item.provider}
            className={`provider-status-card ${item.configured ? "ready" : "waiting"}`}
          >
            <div>
              <strong>{item.label}</strong>
              <span>{item.supports_media_types.map(mediaLabel).join(" · ")}</span>
            </div>
            <span>{item.configured ? "Ready" : item.requires_key ? "Key needed" : "Available"}</span>
          </article>
        ))}
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

          {selectedAsset && (
            <article className="panel selected-asset-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">SELECTED VISUAL</p>
                  <h3>{selectedProviderLabel} asset attached</h3>
                </div>
                <button className="danger-button" onClick={() => void removeSelection()}>
                  Replace visual
                </button>
              </div>
              <div className="selected-asset-card">
                <img
                  src={selectedAsset.preview_url}
                  alt={`Selected ${selectedAsset.media_type} from ${selectedProviderLabel}`}
                />
                <div>
                  <strong>
                    {selectedAsset.media_type === "video" ? "Video" : "Photo"}
                    {selectedAsset.width > 0
                      ? ` · ${selectedAsset.width}×${selectedAsset.height}`
                      : ""}
                  </strong>
                  <p>
                    By{" "}
                    <a href={selectedAsset.creator_url} target="_blank" rel="noreferrer">
                      {selectedAsset.creator || selectedProviderLabel}
                    </a>
                  </p>
                  <div className="license-note">
                    <span>Rights record</span>
                    <strong>{selectedAsset.attribution || selectedAsset.license_name}</strong>
                    {selectedAsset.license_url && (
                      <a href={selectedAsset.license_url} target="_blank" rel="noreferrer">
                        {selectedAsset.license_name || "View usage terms"}
                      </a>
                    )}
                  </div>
                  <div className="candidate-actions">
                    <a className="ghost-link" href={selectedAsset.source_url} target="_blank" rel="noreferrer">
                      Open source page
                    </a>
                    <a className="ghost-link" href={selectedAsset.download_url} target="_blank" rel="noreferrer">
                      Open media file
                    </a>
                  </div>
                </div>
              </div>
            </article>
          )}

          <article className="panel director-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">DIRECTOR'S BRIEF</p>
                <h3>Define what belongs in this scene</h3>
              </div>
              <label className="director-media-picker">
                Format
                <select value={mediaType} onChange={(event) => changeMediaType(event.target.value as MediaType)}>
                  <option value="video">Stock video</option>
                  <option value="photo">Stock photo</option>
                </select>
              </label>
            </div>

            {brief ? (
              <div className="shot-brief-grid">
                <div className="shot-brief-primary">
                  <span>Subject</span>
                  <strong>{brief.subject}</strong>
                  <span>Action</span>
                  <strong>{brief.action}</strong>
                </div>
                <div><span>Setting</span><strong>{brief.setting}</strong></div>
                <div><span>Framing</span><strong>{brief.framing}</strong></div>
                <div><span>Mood</span><strong>{brief.mood}</strong></div>
              </div>
            ) : (
              <div className="empty-state compact-empty"><p>Building the shot brief…</p></div>
            )}

            {brief && (
              <>
                <div className="director-rules-grid">
                  <div>
                    <span>Must show</span>
                    <div className="director-chip-list positive">
                      {brief.must_show.map((item) => <span key={item}>{item}</span>)}
                    </div>
                  </div>
                  <div>
                    <span>Must avoid</span>
                    <div className="director-chip-list negative">
                      {brief.must_avoid.map((item) => <span key={item}>{item}</span>)}
                    </div>
                  </div>
                </div>
                <div className="query-variant-list">
                  {brief.query_variants.map((item) => (
                    <button key={item} onClick={() => useQueryVariant(item)}>{item}</button>
                  ))}
                </div>
              </>
            )}

            <div className="director-action-row">
              <div>
                <strong>Search every configured source in one global feed</strong>
                <p>Rights-filter, deduplicate, and rank the strongest matches regardless of provider.</p>
              </div>
              <button className="primary-button" disabled={directing || loading || !brief} onClick={() => void directVisuals()}>
                {directing ? "Ranking global feed…" : "Build universal shortlist"}
              </button>
            </div>

            {directorResults && (
              <div className="director-results">
                <div className="result-summary director-summary">
                  <span>
                    {directorResults.candidates.length} recommended visuals from{" "}
                    {directorResults.providers_searched.map((item) => providerFallbackLabels[item]).join(", ") || "connected providers"}
                  </span>
                  <div className="feedback-controls">
                    <label>
                      Reject as
                      <select value={feedbackReason} onChange={(event) => setFeedbackReason(event.target.value as VisualFeedbackReason)}>
                        {Object.entries(feedbackLabels).map(([value, label]) => (
                          <option value={value} key={value}>{label}</option>
                        ))}
                      </select>
                    </label>
                    {directorResults.rejected_count > 0 && (
                      <button className="ghost-button" onClick={() => void resetFeedback()}>
                        Reset {directorResults.rejected_count} rejection{directorResults.rejected_count === 1 ? "" : "s"}
                      </button>
                    )}
                  </div>
                </div>
                {directorResults.candidates.length === 0 ? (
                  <div className="empty-state compact-empty">
                    <h4>No defensible global shortlist yet.</h4>
                    <p>Try Stock photo, loosen the shot brief with a query chip, or reset rejected candidates.</p>
                  </div>
                ) : (
                  <div className="candidate-grid director-grid">
                    {directorResults.candidates.map((candidate) => candidateCard(candidate, true))}
                  </div>
                )}
              </div>
            )}
          </article>

          <details className="panel manual-search-panel">
            <summary>Manual provider search</summary>
            <div className="section-heading manual-heading">
              <div>
                <p className="eyebrow">FALLBACK SEARCH</p>
                <h3>Search one provider directly</h3>
              </div>
              {activeStatus && (
                <a className="provider-link" href={activeStatus.source_url} target="_blank" rel="noreferrer">
                  Visit {activeStatus.label}
                </a>
              )}
            </div>

            <div className="provider-picker">
              {compatibleStatuses.map((item) => (
                <button
                  key={item.provider}
                  className={`provider-choice ${provider === item.provider ? "active" : ""}`}
                  onClick={() => changeProvider(item.provider)}
                >
                  <strong>{item.label}</strong>
                  <span>{item.configured ? "Ready" : "Manual search"}</span>
                </button>
              ))}
            </div>

            <div className="asset-search-controls">
              <label>
                Search query
                <input value={query} onChange={(event) => setQuery(event.target.value)} />
              </label>
              <label>
                Media type
                <select value={mediaType} onChange={(event) => changeMediaType(event.target.value as MediaType)}>
                  <option value="video">Stock video</option>
                  <option value="photo">Stock photo</option>
                </select>
              </label>
              <button className="primary-button" disabled={searching || loading || query.trim().length < 2} onClick={() => void search()}>
                {searching ? "Searching…" : `Search ${activeProviderLabel}`}
              </button>
            </div>

            {activeStatus && !activeStatus.configured && (
              <div className="setup-card">
                <div>
                  <p className="eyebrow">PROVIDER NOT CONNECTED</p>
                  <h4>{activeStatus.label} will use manual-search mode</h4>
                  <p>{activeStatus.setup_hint}</p>
                </div>
                <p>The other connected and no-key providers remain fully usable.</p>
              </div>
            )}

            {results && !results.configured && (
              <div className="manual-search-card">
                <div>
                  <strong>{activeProviderLabel} is not connected locally.</strong>
                  <p>Open the prepared provider search while the API remains optional.</p>
                </div>
                <a className="secondary-button link-button" href={results.source_url} target="_blank" rel="noreferrer">
                  Search directly →
                </a>
              </div>
            )}

            {results?.configured && (
              <>
                <div className="result-summary">
                  <span>{results.candidates.length} {activeProviderLabel} candidates for “{results.query}”</span>
                  {results.rate_limit_remaining !== null && (
                    <span>{results.rate_limit_remaining} API requests remaining</span>
                  )}
                </div>
                {results.candidates.length === 0 ? (
                  <div className="empty-state compact-empty">
                    <h4>No matching media found.</h4>
                    <p>Try a shorter phrase or switch providers.</p>
                  </div>
                ) : (
                  <div className="candidate-grid">
                    {results.candidates.map((candidate) => candidateCard(candidate, false))}
                  </div>
                )}
              </>
            )}
          </details>
        </section>
      </div>
    </main>
  );
}
