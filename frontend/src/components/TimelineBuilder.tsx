import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
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

function formatPreciseTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${remaining.toFixed(2).padStart(5, "0")}`;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "Not rendered";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  const [uploading, setUploading] = useState(false);
  const [removingAudio, setRemovingAudio] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const readyAssets = project.scenes.filter(
    (scene) => scene.asset_status === "ready" && scene.selected_asset,
  ).length;
  const previewUrl = useMemo(() => {
    if (!plan?.output_exists) return "";
    const cacheKey = encodeURIComponent(plan.rendered_at ?? plan.generated_at);
    return `${plan.output_url}?v=${cacheKey}`;
  }, [plan]);
  const renderStatus = plan?.output_exists
    ? plan.voiceover
      ? "Rendered with narration"
      : "Rendered"
    : plan?.ready
      ? "Ready to render"
      : "Assets missing";

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

  function chooseNarration(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setLocalError("");
  }

  async function uploadNarration() {
    if (!selectedFile) return;
    setUploading(true);
    setLocalError("");
    try {
      setPlan(await api.uploadNarration(project.id, selectedFile));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to upload narration");
    } finally {
      setUploading(false);
    }
  }

  async function removeNarration() {
    const confirmed = window.confirm("Remove the narration audio from this project?");
    if (!confirmed) return;
    setRemovingAudio(true);
    setLocalError("");
    try {
      setPlan(await api.removeNarration(project.id));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to remove narration");
    } finally {
      setRemovingAudio(false);
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
            Convert approved local assets into an exact first cut, then align and attach the project narration.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={onOpenAssets}>Asset Planner</button>
          <span className="status-pill">Narration Alignment v0.7</span>
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
          <span>Narration</span>
          <strong>{plan?.voiceover ? formatTime(plan.voiceover.duration_seconds) : "Missing"}</strong>
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
          <span className={`asset-status ${plan?.output_exists || plan?.ready ? "ready" : "missing"}`}>
            {renderStatus}
          </span>
        </div>

        <div className="timeline-action-grid">
          <div className="timeline-readiness">
            <strong>{readyAssets} of {project.scenes.length} scenes ready</strong>
            <p>
              Videos are looped when necessary, trimmed to the scene slot, normalized to 1080p, and concatenated in scene order.
            </p>
            {plan && !plan.ffmpeg_available && (
              <p className="timeline-warning">FFmpeg is not available. Install it with <code>brew install ffmpeg</code>.</p>
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
              {rendering
                ? "Rendering with FFmpeg…"
                : plan?.voiceover
                  ? "Render voiced first cut"
                  : "Render silent first cut"}
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

      <section className="panel narration-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">NARRATION AUDIO</p>
            <h3>Upload and align the voiceover</h3>
          </div>
          <span className={`asset-status ${plan?.voiceover ? (plan.alignment_status === "aligned" ? "ready" : "searching") : "missing"}`}>
            {plan?.voiceover
              ? plan.alignment_status === "aligned"
                ? "Aligned"
                : "Timing warning"
              : "Audio missing"}
          </span>
        </div>

        {plan?.voiceover ? (
          <div className="narration-attached">
            <div className="narration-file-card">
              <div>
                <span className="eyebrow">LOCAL VOICEOVER</span>
                <strong>{plan.voiceover.original_filename}</strong>
                <small>
                  {formatBytes(plan.voiceover.file_size_bytes)} · {formatPreciseTime(plan.voiceover.duration_seconds)}
                </small>
              </div>
              <audio controls preload="metadata" src={plan.voiceover.public_url} />
            </div>
            <div className={`alignment-note ${plan.alignment_status}`}>
              <strong>{plan.alignment_message}</strong>
              <span>
                Visual timeline {formatPreciseTime(plan.runtime_seconds)} · Narration {formatPreciseTime(plan.voiceover.duration_seconds)}
              </span>
            </div>
          </div>
        ) : (
          <div className="narration-empty">
            <strong>Add the final voiceover file</strong>
            <p>Supported formats: MP3, WAV, M4A, AAC, FLAC, OGG, and WebM audio.</p>
          </div>
        )}

        <div className="narration-upload-row">
          <label className="audio-file-picker">
            <span>{selectedFile ? selectedFile.name : plan?.voiceover ? "Choose replacement audio" : "Choose narration audio"}</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg,.webm"
              onChange={chooseNarration}
            />
          </label>
          <button
            className="secondary-button"
            disabled={!selectedFile || uploading || removingAudio}
            onClick={() => void uploadNarration()}
          >
            {uploading ? "Analyzing with FFprobe…" : plan?.voiceover ? "Replace narration" : "Upload narration"}
          </button>
          {plan?.voiceover && (
            <button
              className="danger-button"
              disabled={uploading || removingAudio}
              onClick={() => void removeNarration()}
            >
              {removingAudio ? "Removing…" : "Remove audio"}
            </button>
          )}
        </div>
      </section>

      {plan?.output_exists && (
        <section className="panel render-preview-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">FIRST-CUT PREVIEW</p>
              <h3>Playable local assembly</h3>
            </div>
            <span className="status-pill">{plan.voiceover ? "Narrated preview" : "Silent preview"}</span>
          </div>
          <video key={previewUrl} className="timeline-video" controls playsInline src={previewUrl} />
          <div className="render-meta">
            <span>{formatBytes(plan.output_size_bytes)}</span>
            <span>{formatTime(plan.runtime_seconds)}</span>
            <span>{plan.voiceover ? "AAC narration" : "No audio"}</span>
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
          {plan && <span className="subtle-text">{plan.clip_count} clips · {plan.settings.fps} fps</span>}
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
                    <span>{clip.duration_seconds}s</span>
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
