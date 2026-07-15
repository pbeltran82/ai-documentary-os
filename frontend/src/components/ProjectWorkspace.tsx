import { FormEvent, useMemo, useState } from "react";
import type { ProjectDetail, Scene, SceneUpdate } from "../types";
import { SceneEditor } from "./SceneEditor";

interface ProjectWorkspaceProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenAssets: () => void;
  onGenerate: (narration: string, targetSeconds: number) => Promise<void>;
  onUpdateScene: (sceneId: number, payload: SceneUpdate) => Promise<void>;
  onDeleteScene: (scene: Scene) => Promise<void>;
}

function formatRuntime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export function ProjectWorkspace({
  project,
  loading,
  error,
  onBack,
  onOpenAssets,
  onGenerate,
  onUpdateScene,
  onDeleteScene,
}: ProjectWorkspaceProps) {
  const [narration, setNarration] = useState("");
  const [targetSeconds, setTargetSeconds] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [savingSceneId, setSavingSceneId] = useState<number | null>(null);

  const totalDuration = useMemo(
    () => project.scenes.reduce((total, scene) => total + scene.duration_seconds, 0),
    [project.scenes],
  );
  const missingAssets = useMemo(
    () => project.scenes.filter((scene) => !scene.selected_asset).length,
    [project.scenes],
  );

  async function submitNarration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (project.scenes.length > 0) {
      const confirmed = window.confirm(
        `Replace the existing ${project.scenes.length} scenes with a new breakdown?`,
      );
      if (!confirmed) return;
    }

    setGenerating(true);
    try {
      await onGenerate(narration, targetSeconds);
    } finally {
      setGenerating(false);
    }
  }

  async function saveScene(sceneId: number, payload: SceneUpdate) {
    setSavingSceneId(sceneId);
    try {
      await onUpdateScene(sceneId, payload);
    } finally {
      setSavingSceneId(null);
    }
  }

  return (
    <main className="workspace">
      <header className="project-topbar">
        <div>
          <button className="back-button" onClick={onBack}>← Mission Control</button>
          <p className="eyebrow">SCENE ENGINE</p>
          <h2>{project.title}</h2>
          <p className="project-summary">{project.topic}</p>
        </div>
        <div className="header-actions">
          {project.scenes.length > 0 && (
            <button className="primary-button" onClick={onOpenAssets}>
              Open Asset Planner →
            </button>
          )}
          <span className="status-pill">{project.status}</span>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="stats-grid four-up" aria-label="Scene overview">
        <article className="stat-card">
          <span>Scenes</span>
          <strong>{project.scenes.length}</strong>
        </article>
        <article className="stat-card">
          <span>Estimated runtime</span>
          <strong>{formatRuntime(totalDuration)}</strong>
        </article>
        <article className="stat-card">
          <span>Missing visuals</span>
          <strong>{missingAssets}</strong>
        </article>
        <article className="stat-card accent">
          <span>Target slot</span>
          <strong>{targetSeconds}s</strong>
        </article>
      </section>

      <section className="panel narration-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">NARRATION → VISUAL SLOTS</p>
            <h3>Generate or import a timed scene plan</h3>
          </div>
          <span className="status-pill">Smart Import v0.2.1</span>
        </div>

        <form className="narration-form" onSubmit={submitNarration}>
          <label className="wide-field">
            Paste plain narration or a structured scene plan
            <textarea
              required
              minLength={5}
              rows={11}
              value={narration}
              placeholder={`Plain narration is split automatically. Structured plans are imported field-by-field, for example:\n\nScene 01\n00:00–00:05\nNarration: Most people underestimate the power of time.\nVisual intent: Calendar pages and long-term market growth\nSearch terms: calendar time lapse, investment growth, stock chart\nPreferred visual: Stock video\nAsset status: Missing`}
              onChange={(event) => setNarration(event.target.value)}
            />
          </label>

          <label>
            Desired visual duration
            <div className="input-with-suffix">
              <input
                type="number"
                min={3}
                max={15}
                step={1}
                value={targetSeconds}
                onChange={(event) => setTargetSeconds(Number(event.target.value))}
              />
              <span>seconds</span>
            </div>
          </label>

          <div className="generation-note">
            <strong>Accepted input</strong>
            <span>Plain narration · scene headings · timecodes · labeled production fields</span>
          </div>

          <button className="primary-button wide-field" disabled={generating || loading}>
            {generating
              ? "Building scene plan…"
              : project.scenes.length > 0
                ? "Replace scene plan"
                : "Generate / import scene plan"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PRODUCTION BOARD</p>
            <h3>Timed visual slots</h3>
          </div>
          <span className="subtle-text">
            {loading ? "Loading…" : `${project.scenes.length} scenes`}
          </span>
        </div>

        {project.scenes.length === 0 ? (
          <div className="empty-state compact-empty">
            <div className="empty-icon">🎞️</div>
            <h4>No scenes yet.</h4>
            <p>Paste narration or a structured scene plan above to create timed visual slots.</p>
          </div>
        ) : (
          <div className="scene-list">
            {project.scenes.map((scene) => (
              <SceneEditor
                key={scene.id}
                scene={scene}
                saving={savingSceneId === scene.id}
                onSave={saveScene}
                onDelete={onDeleteScene}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
