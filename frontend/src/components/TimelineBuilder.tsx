import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { ProjectDetail, TimelinePlan } from "../types";

interface TimelineBuilderProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenAssets: () => void;
}

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(whole / 60);
  const remaining = whole % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "Not rendered";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number): string {
  return Number.isInteger(seconds) ? `${seconds}s` : `${seconds.toFixed(1)}s`;
}

export function TimelineBuilder({
  project,
  loading,
  error,
  onBack,
  onOpenAssets,
}: TimelineBuilderProps) {
  const [plan, setPlan] = useState<TimelinePlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [localError, setLocalError] = useState("");

  const readyAssets = project.scenes.filter(
    (scene) => scene.asset_status === "ready" && scene.selected_asset,
  ).length;
  const previewUrl = useMemo(() => {
    if (!plan?.output_exists) return "";
    const cacheKey = encodeURIComponent(plan.rendered_at ?? plan.generated_at);
    return `${plan.output_url}?v=${cacheKey}`;
  }, [plan]);

  async function buildPlan() {
    setPlanning(true);
    setLocalError("");
    try {
      setPlan(await api.buildTimelinePlan(project.id));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to build timeline plan");
    } finally {
      setPlanning(false);
    }
  }

  async function renderFirstCut() {
    setRendering(true);
    setLocalError("");
    try {
      setPlan(await api.renderTimeline(project.id));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to render first cut");
    } finally {
      setRendering(false);
    }
  }

  useEffect(() => {
    void buildPlan();
  }, [project.id, project.updated_at]);

  return (
    <main className="workspace timeline-workspace">
      <header className="project-topbar">
        <div>
          <button className="back-button" onClick={onBack}>← Mission Control</button>
          <p className="eyebrow">TIMELINE BUILDER</p>
          <h2>{project.title}</h2>
          <p className="project-summary">
            Convert approved local assets into an exact, silent first-cut preview with one timed clip per scene.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={onOpenAssets}>Asset Planner</button>
          <span className="status-pill">Assembly Engine v0.6</span>
        </div>
      </header>

      {(error || localError) && <div className="error-banner">{localError || error}</div>}

      <section className="stats-grid four-up" aria-label="Timeline overview">
        <article className="stat-card">
          <span>Timeline clips</span>
          <strong>{plan?.clip_count ?? readyAssets}</strong>
        </article>
        <article className="stat-card">
          <span>Runtime</span>
          <strong>{formatTime(plan?.runtime_seconds ?? 0)}</strong>
        </article>
        <article className="stat-card">
          <span>Output</span>
          <strong>{plan ? `${plan.settings.width}×${plan.settings.height}` : "1080p"}</strong>
        </article>
        <article className="stat-card accent">
          <span>First cut</span>
          <strong>{plan?.output_exists ? formatBytes(plan.output_size_bytes) : "Pending"}</strong>
        </article>
      </section>

      <section className="panel timeline-command-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">ASSEMBLY CONTROL</p>
            <h3>Build and render the first cut</h3>
          </div>
          <span className={`asset-status ${plan?.ready ? "ready" : "missing"}`}>
            {plan?.ready ? "Ready to render" : "Assets missing"}
          </span>
        </div>

        <div className="timeline-action-grid">
          <div className="timeline-readiness">
            <strong>{readyAssets} of {project.scenes.length} scenes ready</strong>
            <p>
              Videos are looped when necessary, trimmed to the scene slot, normalized to 1080p, and concatenated in scene order.
            </p>
            {plan && !plan.ffmpeg_available && (
              <p className="timeline-warning">
                FFmpeg is not available. Install it with <code>brew install ffmpeg</code>.
              </p>
            )}
          </div>
          <div className="timeline-actions">
            <button
              className="ghost-button"
              disabled={planning || rendering || loading}
              onClick={() => void buildPlan()}
            >
              {planning ? "Building…" : "Refresh plan"}
            </button>
            <button
              className="primary-button"
              disabled={rendering || planning || loading || !plan?.ready || !plan.ffmpeg_available}
              onClick={() => void renderFirstCut()}
            >
              {rendering ? "Rendering with FFmpeg…" : "Render first cut"}
            </button>
          </div>
        </div>

        {plan?.missing_scenes.length ? (
          <div className="timeline-missing-list">
            {plan.missing_scenes.map((item) => (
              <div key={item.scene_id}>
                <strong>Scene {String(item.scene_number).padStart(2, "0")}</strong>
                <span>{item.reason}</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {plan?.output_exists && (
        <section className="panel render-preview-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">FIRST-CUT PREVIEW</p>
              <h3>Playable local assembly</h3>
            </div>
            <span className="status-pill">Silent preview</span>
          </div>
          <video key={previewUrl} className="timeline-video" controls playsInline src={previewUrl} />
          <div className="render-meta">
            <span>{formatBytes(plan.output_size_bytes)}</span>
            <span>{formatTime(plan.runtime_seconds)}</span>
            <a href={plan.output_url} target="_blank" rel="noreferrer">Open video file</a>
          </div>
        </section>
      )}

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">ASSEMBLY PLAN</p>
            <h3>Scene-by-scene edit decisions</h3>
          </div>
          {plan && (
            <span className="subtle-text">{plan.clip_count} clips · {plan.settings.fps} fps</span>
          )}
        </div>

        {!plan || planning ? (
          <div className="empty-state compact-empty"><p>Building the timeline plan…</p></div>
        ) : plan.clips.length === 0 ? (
          <div className="empty-state compact-empty">
            <h4>No clips are ready yet.</h4>
            <p>Return to the Asset Planner and approve a local visual for every scene.</p>
            <button className="secondary-button" onClick={onOpenAssets}>Open Asset Planner</button>
          </div>
        ) : (
          <div className="timeline-clip-list">
            {plan.clips.map((clip) => (
              <article className="timeline-clip-card" key={clip.scene_id}>
                <img src={clip.preview_url} alt={`Scene ${clip.scene_number} selected visual`} />
                <div className="timeline-clip-copy">
                  <div className="timeline-clip-heading">
                    <strong>Scene {String(clip.scene_number).padStart(2, "0")}</strong>
                    <span>{formatTime(clip.start_seconds)}–{formatTime(clip.end_seconds)}</span>
                  </div>
                  <p>{clip.narration}</p>
                  <div className="clip-tags">
                    <span>{clip.media_type}</span>
                    <span>{clip.provider}</span>
                    <span>{formatDuration(clip.duration_seconds)}</span>
                  </div>
                  <small>{clip.assembly_action}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {plan && (
        <section className="panel technical-plan-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">REPRODUCIBLE BUILD</p>
              <h3>Render artifacts</h3>
            </div>
          </div>
          <div className="artifact-links">
            <a href={plan.plan_url} target="_blank" rel="noreferrer">Render plan JSON</a>
            <a href={plan.script_url} target="_blank" rel="noreferrer">FFmpeg shell script</a>
          </div>
          <details>
            <summary>Show FFmpeg command</summary>
            <pre>{plan.command.length ? plan.command.join(" ") : "Timeline is not ready."}</pre>
          </details>
        </section>
      )}
    </main>
  );
}
