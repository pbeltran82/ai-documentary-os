import { FormEvent, useMemo, useState } from "react";
import { api } from "../api";
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

type SceneWithBeats = Scene & { animation_plan?: { visual_beats?: unknown[] } };

function formatRuntime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export function ProjectWorkspace({ project, loading, error, onBack, onOpenAssets, onGenerate, onUpdateScene, onDeleteScene }: ProjectWorkspaceProps) {
  const [narration, setNarration] = useState("");
  const [targetSeconds, setTargetSeconds] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [planningBeats, setPlanningBeats] = useState(false);
  const [beatMessage, setBeatMessage] = useState("");
  const [beatError, setBeatError] = useState("");
  const [savingSceneId, setSavingSceneId] = useState<number | null>(null);

  const totalDuration = useMemo(() => project.scenes.reduce((total, scene) => total + scene.duration_seconds, 0), [project.scenes]);
  const missingAssets = useMemo(() => project.scenes.filter((scene) => !scene.selected_asset).length, [project.scenes]);
  const visualBeatCount = useMemo(() => project.scenes.reduce((total, scene) => total + (((scene as SceneWithBeats).animation_plan?.visual_beats?.length) ?? 0), 0), [project.scenes]);

  async function submitNarration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (project.scenes.length > 0 && !window.confirm(`Replace the existing ${project.scenes.length} scenes with a new breakdown?`)) return;
    setGenerating(true);
    try { await onGenerate(narration, targetSeconds); } finally { setGenerating(false); }
  }

  async function planBeats() {
    setPlanningBeats(true);
    setBeatError("");
    setBeatMessage("");
    try {
      const result = await api.planVisualBeats(project.id, targetSeconds);
      setBeatMessage(`${result.visual_beat_count} visual beats planned across ${result.scene_count} narrated scenes.`);
      window.setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      setBeatError(err instanceof Error ? err.message : "Unable to plan visual beats");
    } finally { setPlanningBeats(false); }
  }

  async function saveScene(sceneId: number, payload: SceneUpdate) {
    setSavingSceneId(sceneId);
    try { await onUpdateScene(sceneId, payload); } finally { setSavingSceneId(null); }
  }

  return (
    <main className="workspace">
      <header className="project-topbar">
        <div><button className="back-button" onClick={onBack}>← Mission Control</button><p className="eyebrow">SCENE ENGINE</p><h2>{project.title}</h2><p className="project-summary">{project.topic}</p></div>
        <div className="header-actions">{project.scenes.length > 0 && <button className="primary-button" onClick={onOpenAssets}>Open Asset Planner →</button>}<span className="status-pill">{project.status}</span></div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {beatError && <div className="error-banner">{beatError}</div>}
      {beatMessage && <div className="studio-message">{beatMessage}</div>}

      <section className="stats-grid four-up" aria-label="Scene overview">
        <article className="stat-card"><span>Narration scenes</span><strong>{project.scenes.length}</strong></article>
        <article className="stat-card"><span>Estimated runtime</span><strong>{formatRuntime(totalDuration)}</strong></article>
        <article className="stat-card"><span>Visual beats</span><strong>{visualBeatCount || "—"}</strong></article>
        <article className="stat-card accent"><span>Target beat</span><strong>{targetSeconds}s</strong></article>
      </section>

      <section className="panel narration-panel">
        <div className="section-heading"><div><p className="eyebrow">NARRATION → VISUAL BEATS</p><h3>Plan short visual changes beneath continuous audio</h3></div><span className="status-pill">Audio-safe planning</span></div>
        <div className="narration-form">
          <label>Desired visual duration<div className="input-with-suffix"><input type="number" min={3} max={15} step={1} value={targetSeconds} onChange={(event) => setTargetSeconds(Number(event.target.value))} /><span>seconds</span></div></label>
          <div className="generation-note"><strong>Preserves narration</strong><span>Scene WAV mapping and timing stay intact; only visual beats are added.</span></div>
          <button type="button" className="primary-button wide-field" disabled={planningBeats || loading || project.scenes.length === 0} onClick={() => void planBeats()}>{planningBeats ? "Planning visual beats…" : visualBeatCount ? "Replan visual beats" : "Plan visual beats"}</button>
        </div>
      </section>

      <section className="panel narration-panel">
        <div className="section-heading"><div><p className="eyebrow">MANUAL IMPORT</p><h3>Replace the narrated plan only when needed</h3></div><span className="status-pill">Smart Import v0.2.1</span></div>
        <form className="narration-form" onSubmit={submitNarration}>
          <label className="wide-field">Paste plain narration or a structured scene plan<textarea required minLength={5} rows={7} value={narration} placeholder="Use this only to replace the current scene plan manually." onChange={(event) => setNarration(event.target.value)} /></label>
          <button className="ghost-button wide-field" disabled={generating || loading}>{generating ? "Building scene plan…" : "Replace scene plan"}</button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading"><div><p className="eyebrow">PRODUCTION BOARD</p><h3>Narrated scenes</h3></div><span className="subtle-text">{loading ? "Loading…" : `${project.scenes.length} scenes · ${visualBeatCount} visual beats`}</span></div>
        {project.scenes.length === 0 ? <div className="empty-state compact-empty"><div className="empty-icon">🎞️</div><h4>No scenes yet.</h4></div> : <div className="scene-list">{project.scenes.map((scene) => <SceneEditor key={scene.id} scene={scene} saving={savingSceneId === scene.id} onSave={saveScene} onDelete={onDeleteScene} />)}</div>}
      </section>
    </main>
  );
}
