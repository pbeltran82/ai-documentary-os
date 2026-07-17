import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type {
  PhotoMotion,
  ProjectDetail,
  TimelinePlan,
  TimelineStyle,
  TransitionStyle,
  VideoFormat,
} from "../types";

interface TimelineBuilderProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenAssets: () => void;
  onOpenScenes: () => void;
  onProjectChanged: () => Promise<void> | void;
}

const defaultTimelineStyle: TimelineStyle = {
  transition_style: "crossfade",
  transition_duration_seconds: 0.35,
  photo_motion: "editorial",
  edge_fade_seconds: 0.35,
};

const transitionLabels: Record<TransitionStyle, string> = {
  cut: "Clean cuts",
  crossfade: "Crossfade",
  fade_black: "Fade through black",
};

const motionLabels: Record<PhotoMotion, string> = {
  editorial: "Editorial auto-direction",
  static: "Static stills",
  zoom_in: "Gentle zoom in",
  zoom_out: "Gentle zoom out",
  alternate: "Alternate zoom in/out",
};

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

function formatSeconds(seconds: number): string {
  return `${seconds.toFixed(seconds >= 10 ? 1 : 2)}s`;
}

function styleFromPlan(plan: TimelinePlan): TimelineStyle {
  return {
    transition_style: plan.settings.transition_style,
    transition_duration_seconds: plan.settings.transition_duration_seconds,
    photo_motion: plan.settings.photo_motion,
    edge_fade_seconds: plan.settings.edge_fade_seconds,
  };
}

function clipMotionLabel(value: string): string {
  if (value === "zoom_in") return "Zoom in";
  if (value === "zoom_out") return "Zoom out";
  if (value === "pan_left") return "Pan left";
  if (value === "pan_right") return "Pan right";
  return "Static";
}

function clipTransitionLabel(value: TransitionStyle, seconds: number): string {
  if (value === "crossfade") return `${seconds}s crossfade`;
  if (value === "fade_black") return `${seconds}s fade black`;
  return "Clean cut";
}

export function TimelineBuilder({
  project,
  loading,
  error,
  onBack,
  onOpenAssets,
  onOpenScenes,
  onProjectChanged,
}: TimelineBuilderProps) {
  const [plan, setPlan] = useState<TimelinePlan | null>(null);
  const [style, setStyle] = useState<TimelineStyle>(defaultTimelineStyle);
  const [styleDirty, setStyleDirty] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [removingAudio, setRemovingAudio] = useState(false);
  const [switchingFormat, setSwitchingFormat] = useState(false);
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

  const narrationCoverage = useMemo(() => {
    if (!plan?.voiceover) return null;
    const narrationSeconds = plan.voiceover.duration_seconds;
    const timelineSeconds = plan.runtime_seconds;
    const coveragePercent = narrationSeconds > 0
      ? Math.min(100, (timelineSeconds / narrationSeconds) * 100)
      : 100;
    const uncoveredSeconds = Math.max(0, narrationSeconds - timelineSeconds);
    const currentSceneCount = Math.max(1, project.scenes.length);
    const currentAverageSlot = timelineSeconds > 0
      ? timelineSeconds / currentSceneCount
      : 5;
    const targetSceneSeconds = Math.min(15, Math.max(3, currentAverageSlot || 5));
    const recommendedSceneCount = Math.max(
      currentSceneCount,
      Math.ceil(narrationSeconds / targetSceneSeconds),
    );

    return {
      coveragePercent,
      uncoveredSeconds,
      targetSceneSeconds,
      recommendedSceneCount,
      additionalScenesNeeded: Math.max(0, recommendedSceneCount - currentSceneCount),
    };
  }, [plan, project.scenes.length]);

  const isTrimmedExcerpt = Boolean(
    plan?.voiceover && plan.alignment_status === "longer",
  );
  const isPaddedNarration = Boolean(
    plan?.voiceover && plan.alignment_status === "shorter",
  );

  const renderStatus = plan?.output_exists
    ? isTrimmedExcerpt
      ? "Rendered excerpt"
      : isPaddedNarration
        ? "Rendered with silence"
        : plan.voiceover
          ? "Rendered with narration"
          : "Rendered"
    : plan?.ready
      ? "Ready to render"
      : "Assets missing";

  const renderButtonLabel = rendering
    ? "Rendering motion cut…"
    : isTrimmedExcerpt
      ? `Render ${formatTime(plan?.runtime_seconds ?? 0)} narrated excerpt`
      : isPaddedNarration
        ? "Render narrated cut + silence"
        : plan?.voiceover
          ? "Render motion first cut"
          : "Render silent motion cut";

  function acceptPlan(nextPlan: TimelinePlan) {
    setPlan(nextPlan);
    setStyle(styleFromPlan(nextPlan));
    setStyleDirty(false);
  }

  async function buildPlan(nextStyle?: TimelineStyle) {
    setPlanning(true);
    setLocalError("");
    try {
      acceptPlan(await api.buildTimelinePlan(project.id, nextStyle));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to build timeline plan");
    } finally {
      setPlanning(false);
    }
  }

  async function applyMotionPlan() {
    await buildPlan(style);
  }

  async function switchVideoFormat(nextFormat: VideoFormat) {
    if (nextFormat === project.video_format) return;
    setSwitchingFormat(true);
    setLocalError("");
    try {
      await api.updateProject(project.id, { video_format: nextFormat });
      await onProjectChanged();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to switch video format");
    } finally {
      setSwitchingFormat(false);
    }
  }

  async function renderFirstCut() {
    setRendering(true);
    setLocalError("");
    try {
      acceptPlan(await api.renderTimeline(project.id, style));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Unable to render first cut");
    } finally {
      setRendering(false);
    }
  }

  function updateStyle<K extends keyof TimelineStyle>(
    key: K,
    value: TimelineStyle[K],
  ) {
    setStyle((current) => ({ ...current, [key]: value }));
    setStyleDirty(true);
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
      acceptPlan(await api.uploadNarration(project.id, selectedFile));
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
      acceptPlan(await api.removeNarration(project.id));
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
            Assemble exact scene timing, add restrained documentary motion, and attach the project narration.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={onOpenAssets}>Asset Planner</button>
          <span className="status-pill">Editorial Motion v0.9.2</span>
        </div>
      </header>

      {(error || localError) && <div className="error-banner">{localError || error}</div>}

      <section className="stats-grid four-up" aria-label="Timeline overview">
        <article className="stat-card">
          <span>Timeline clips</span>
          <strong>{plan?.clip_count ?? readyAssets}</strong>
        </article>
        <article className="stat-card">
          <span>Visual runtime</span>
          <strong>{formatTime(plan?.runtime_seconds ?? 0)}</strong>
        </article>
        <article className="stat-card">
          <span>Narration</span>
          <strong>{plan?.voiceover ? formatTime(plan.voiceover.duration_seconds) : "Missing"}</strong>
        </article>
        <article className="stat-card accent">
          <span>{isTrimmedExcerpt ? "Narration covered" : "First cut"}</span>
          <strong>
            {isTrimmedExcerpt && narrationCoverage
              ? `${Math.round(narrationCoverage.coveragePercent)}%`
              : plan?.output_exists
                ? formatBytes(plan.output_size_bytes)
                : "Pending"}
          </strong>
        </article>
      </section>

      <section className="panel format-control-panel">
        <div className="format-control-copy">
          <p className="eyebrow">DELIVERY FORMAT</p>
          <h3>Choose the canvas before the final render</h3>
          <p>
            This setting controls exact visuals, still-photo treatment, stock-footage framing,
            preview shape, and final FFmpeg output for the whole project.
          </p>
        </div>
        <div className="format-switch" role="group" aria-label="Video format">
          <button
            className={project.video_format === "youtube" ? "active" : ""}
            aria-pressed={project.video_format === "youtube"}
            disabled={switchingFormat || rendering}
            onClick={() => void switchVideoFormat("youtube")}
          >
            <span className="format-glyph landscape" aria-hidden="true" />
            <strong>YouTube</strong>
            <small>16:9 · 1920×1080</small>
          </button>
          <button
            className={project.video_format === "shorts" ? "active" : ""}
            aria-pressed={project.video_format === "shorts"}
            disabled={switchingFormat || rendering}
            onClick={() => void switchVideoFormat("shorts")}
          >
            <span className="format-glyph portrait" aria-hidden="true" />
            <strong>Shorts</strong>
            <small>9:16 · 1080×1920</small>
          </button>
        </div>
        <p className="format-control-note">
          {switchingFormat
            ? "Switching canvas and rebuilding the render plan…"
            : project.video_format === "shorts"
              ? "Vertical-safe reflow is active. Regenerate exact visuals for the strongest native Shorts composition."
              : "Landscape production is active. Existing projects remain on this format by default."}
        </p>
      </section>

      <section className="panel motion-control-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">MOTION & TRANSITIONS</p>
            <h3>Choose the editorial movement</h3>
          </div>
          <span className={`asset-status ${styleDirty ? "searching" : "ready"}`}>
            {styleDirty ? "Changes pending" : "Plan saved"}
          </span>
        </div>

        <div className="motion-control-grid">
          <label>
            <span>Scene transition</span>
            <select
              value={style.transition_style}
              onChange={(event) => updateStyle(
                "transition_style",
                event.target.value as TransitionStyle,
              )}
            >
              <option value="crossfade">Crossfade</option>
              <option value="fade_black">Fade through black</option>
              <option value="cut">Clean cut</option>
            </select>
          </label>
          <label>
            <span>Transition length</span>
            <select
              value={style.transition_duration_seconds}
              disabled={style.transition_style === "cut"}
              onChange={(event) => updateStyle(
                "transition_duration_seconds",
                Number(event.target.value),
              )}
            >
              <option value={0.25}>0.25s · crisp</option>
              <option value={0.35}>0.35s · documentary</option>
              <option value={0.5}>0.50s · smooth</option>
              <option value={0.65}>0.65s · deliberate</option>
            </select>
          </label>
          <label>
            <span>Still-photo motion</span>
            <select
              value={style.photo_motion}
              onChange={(event) => updateStyle(
                "photo_motion",
                event.target.value as PhotoMotion,
              )}
            >
              <option value="editorial">Editorial auto-direction</option>
              <option value="alternate">Alternate zoom in/out</option>
              <option value="zoom_in">Gentle zoom in</option>
              <option value="zoom_out">Gentle zoom out</option>
              <option value="static">Static stills</option>
            </select>
          </label>
          <label>
            <span>Opening & closing fade</span>
            <select
              value={style.edge_fade_seconds}
              onChange={(event) => updateStyle(
                "edge_fade_seconds",
                Number(event.target.value),
              )}
            >
              <option value={0}>None</option>
              <option value={0.25}>0.25s</option>
              <option value={0.35}>0.35s</option>
              <option value={0.5}>0.50s</option>
            </select>
          </label>
        </div>

        <div className="motion-control-footer">
          <p>
            Crossfade handles overlap outside the scene slots, so the narration and final runtime stay exact.
            Editorial mode chooses a restrained push, pull, pan, or steady hold per scene. Still photos use a soft {project.video_format === "shorts" ? "9:16" : "16:9"} background; stock videos keep native motion.
          </p>
          <button
            className="secondary-button"
            disabled={!styleDirty || planning || rendering || loading}
            onClick={() => void applyMotionPlan()}
          >
            {planning ? "Saving motion plan…" : "Apply motion plan"}
          </button>
        </div>
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
              Clips are normalized to {project.video_format === "shorts" ? "1080×1920 Shorts" : "1920×1080 YouTube"}, timed exactly, given the saved motion treatment, and assembled in narration order.
            </p>
            <p className="motion-summary">
              {transitionLabels[style.transition_style]} · {motionLabels[style.photo_motion]} · {style.edge_fade_seconds}s edge fade
            </p>
            {styleDirty && (
              <p className="timeline-warning">
                Motion settings changed. Rendering will save and use the new plan.
              </p>
            )}
            {isTrimmedExcerpt && (
              <p className="timeline-warning">
                This render is an excerpt. Only the first {formatTime(plan?.runtime_seconds ?? 0)} of the narration will be included.
              </p>
            )}
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
              {planning ? "Building…" : "Refresh saved plan"}
            </button>
            <button
              className="primary-button"
              disabled={rendering || planning || loading || !plan?.ready || !plan.ffmpeg_available}
              onClick={() => void renderFirstCut()}
            >
              {renderButtonLabel}
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

        {isTrimmedExcerpt && narrationCoverage && (
          <div className="narration-coverage-card">
            <div className="coverage-heading">
              <div>
                <span className="eyebrow">VISUAL COVERAGE GAP</span>
                <strong>{Math.round(narrationCoverage.coveragePercent)}% of narration has visuals</strong>
              </div>
              <span>{formatSeconds(narrationCoverage.uncoveredSeconds)} uncovered</span>
            </div>
            <div
              className="coverage-track"
              role="progressbar"
              aria-label="Narration visual coverage"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(narrationCoverage.coveragePercent)}
            >
              <div
                className="coverage-fill"
                style={{ width: `${narrationCoverage.coveragePercent}%` }}
              />
            </div>
            <p>
              At the current {narrationCoverage.targetSceneSeconds.toFixed(1)}-second visual pace,
              expand this project from {project.scenes.length} to about {narrationCoverage.recommendedSceneCount} scenes.
              {narrationCoverage.additionalScenesNeeded > 0
                ? ` That is roughly ${narrationCoverage.additionalScenesNeeded} more visual decisions.`
                : ""}
            </p>
            <div className="coverage-actions">
              <button className="primary-button" onClick={onOpenScenes}>Expand scene plan</button>
              <span>Paste the complete narration transcript into Smart Import, then return for asset selection.</span>
            </div>
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
              <h3>{isTrimmedExcerpt ? "Playable narrated excerpt" : "Playable motion assembly"}</h3>
            </div>
            <span className="status-pill">
              {isTrimmedExcerpt
                ? "Narrated excerpt"
                : plan.voiceover
                  ? "Motion + narration"
                  : "Motion preview"}
            </span>
          </div>
          <video
            key={previewUrl}
            className={`timeline-video ${plan.settings.video_format}`}
            controls
            playsInline
            src={previewUrl}
          />
          <div className="render-meta">
            <span>{formatBytes(plan.output_size_bytes)}</span>
            <span>{formatTime(plan.runtime_seconds)}</span>
            <span>{plan.voiceover ? "AAC narration" : "No audio"}</span>
            {plan.captions?.exists && (
              <a href={plan.captions.public_url} target="_blank" rel="noreferrer">
                Download captions ({plan.captions.cue_count})
              </a>
            )}
            <span>{transitionLabels[plan.settings.transition_style]}</span>
            <span>{motionLabels[plan.settings.photo_motion]}</span>
            <span>{plan.settings.format_label} · {plan.settings.aspect_ratio}</span>
            {isTrimmedExcerpt && narrationCoverage && (
              <span>{formatSeconds(narrationCoverage.uncoveredSeconds)} narration not yet covered</span>
            )}
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
            {plan.clips.map((clip, index) => (
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
                    {clip.media_type === "photo" && <span title={clip.motion_reason}>{clipMotionLabel(clip.motion_effect)}</span>}
                    {index < plan.clips.length - 1 && (
                      <span>{clipTransitionLabel(clip.transition_out, clip.transition_duration_seconds)}</span>
                    )}
                  </div>
                  <small>{clip.assembly_action}</small>
                  {clip.media_type === "photo" && <small>{clip.motion_reason}</small>}
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
