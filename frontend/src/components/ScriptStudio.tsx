import { useEffect, useMemo, useState } from "react";
import type { ProjectDetail } from "../types";
import "./ScriptStudio.css";

type ScriptSegment = {
  segment_id: string;
  scene_number: number;
  act: string;
  narration: string;
  visual_intent: string;
  search_keywords: string[];
  estimated_duration_seconds: number;
  status: string;
};

type DocumentaryScript = {
  title: string;
  thesis: string;
  angle?: string;
  editor_notes?: string;
  status: string;
  revision: number;
  word_count: number;
  estimated_runtime_seconds: number;
  segments: ScriptSegment[];
};

type AudioSegment = {
  segment_id: string;
  scene_number: number;
  status: string;
  actual_duration_seconds: number | null;
};

type NarrationManifest = {
  status: string;
  segment_count: number;
  voice_id: string;
  speaking_rate: number;
  segments: AudioSegment[];
  last_run: { completed: number; failed: number; skipped: number; filtered_out?: number; repaired?: number };
};

type Props = {
  project: ProjectDetail;
  onBack: () => void;
  onOpenScenes: () => void;
  onProjectChanged: () => Promise<void>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const voices = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"];

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (typeof options.body === "string") headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function cloneSegments(segments: ScriptSegment[]) {
  return segments.map((segment) => ({ ...segment, search_keywords: [...segment.search_keywords] }));
}

export function ScriptStudio({ project, onBack, onOpenScenes, onProjectChanged }: Props) {
  const [script, setScript] = useState<DocumentaryScript | null>(null);
  const [segments, setSegments] = useState<ScriptSegment[]>([]);
  const [narration, setNarration] = useState<NarrationManifest | null>(null);
  const [provider, setProvider] = useState<"openai" | "local-outline">("openai");
  const [angle, setAngle] = useState("");
  const [researchNotes, setResearchNotes] = useState("");
  const [voice, setVoice] = useState("alloy");
  const [rate, setRate] = useState(1);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const completeCount = useMemo(
    () => narration?.segments.filter((item) => item.status === "complete").length ?? 0,
    [narration],
  );

  async function loadArtifacts() {
    const [scriptResult, narrationResult] = await Promise.allSettled([
      request<DocumentaryScript>(`/projects/${project.id}/production/script`),
      request<NarrationManifest>(`/projects/${project.id}/production/narration`),
    ]);
    if (scriptResult.status === "fulfilled") {
      setScript(scriptResult.value);
      setSegments(cloneSegments(scriptResult.value.segments));
      setAngle(scriptResult.value.angle ?? "");
    }
    if (narrationResult.status === "fulfilled") {
      setNarration(narrationResult.value);
      setVoice(narrationResult.value.voice_id);
      setRate(narrationResult.value.speaking_rate);
    }
  }

  useEffect(() => { void loadArtifacts(); }, [project.id]);

  async function run<T>(name: string, action: () => Promise<T>, success: (value: T) => void) {
    setBusy(name);
    setError("");
    setMessage("");
    try { success(await action()); }
    catch (err) { setError(err instanceof Error ? err.message : "Production request failed"); }
    finally { setBusy(""); }
  }

  async function generateScript() {
    await run("generate", () => request<DocumentaryScript>(`/projects/${project.id}/production/script/generate`, {
      method: "POST",
      body: JSON.stringify({ provider, angle, research_notes: researchNotes, target_scene_seconds: 8, replace_scenes: false }),
    }), (generated) => {
      setScript(generated);
      setSegments(cloneSegments(generated.segments));
      setMessage(`Draft revision ${generated.revision} generated.`);
    });
  }

  function updateSegment(index: number, patch: Partial<ScriptSegment>) {
    setSegments((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function editPayload() {
    if (!script) throw new Error("Generate a script first");
    return {
      title: script.title,
      thesis: script.thesis,
      editor_notes: script.editor_notes ?? "",
      segments: segments.map(({ act, narration, visual_intent, search_keywords }) => ({ act, narration, visual_intent, search_keywords })),
      replace_scenes: false,
    };
  }

  async function saveDraft() {
    await run("save", () => request<DocumentaryScript>(`/projects/${project.id}/production/script`, {
      method: "PUT", body: JSON.stringify(editPayload()),
    }), (saved) => {
      setScript(saved);
      setSegments(cloneSegments(saved.segments));
      setMessage(`Draft revision ${saved.revision} saved.`);
    });
  }

  async function approveAndApply() {
    setBusy("approve");
    setError("");
    setMessage("");
    try {
      const saved = await request<DocumentaryScript>(`/projects/${project.id}/production/script`, {
        method: "PUT", body: JSON.stringify(editPayload()),
      });
      const approved = await request<DocumentaryScript>(`/projects/${project.id}/production/script/approve`, {
        method: "POST",
        body: JSON.stringify({ notes: "Approved in Script Studio", replace_scenes: true }),
      });
      setScript(approved);
      setSegments(cloneSegments(saved.segments));
      await onProjectChanged();
      setMessage("Script approved and applied to project scenes.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to approve script");
    } finally { setBusy(""); }
  }

  async function planNarration() {
    await run("plan", () => request<NarrationManifest>(`/projects/${project.id}/production/narration/plan`, {
      method: "POST", body: JSON.stringify({ provider: "openai", voice_id: voice, speaking_rate: rate }),
    }), (plan) => { setNarration(plan); setMessage(`${plan.segment_count} narration segments planned.`); });
  }

  async function synthesize(force = false) {
    await run("synthesize", () => request<NarrationManifest>(`/projects/${project.id}/production/narration/synthesize`, {
      method: "POST", body: JSON.stringify({ scene_numbers: [], force, retime_scenes: true }),
    }), (result) => {
      setNarration(result);
      void onProjectChanged();
      const repaired = result.last_run.repaired ?? 0;
      setMessage(`Narration ${result.status}: ${result.last_run.completed} completed, ${repaired} repaired, ${result.last_run.failed} failed.`);
    });
  }

  return (
    <main className="workspace script-studio">
      <header className="topbar">
        <div><p className="eyebrow">SCRIPT + NARRATION STUDIO</p><h2>{project.title}</h2><p>Write, edit, approve, voice, and retime the documentary from one production desk.</p></div>
        <div className="studio-actions"><button className="ghost-button" onClick={onBack}>Mission Control</button><button className="ghost-button" onClick={onOpenScenes}>Open scenes</button></div>
      </header>
      {error && <div className="error-banner">{error}</div>}
      {message && <div className="studio-message">{message}</div>}

      <section className="panel studio-grid">
        <div>
          <p className="eyebrow">01 · WRITER</p><h3>Generate the documentary draft</h3>
          <label>Writer provider<select value={provider} onChange={(event) => setProvider(event.target.value as typeof provider)}><option value="openai">OpenAI documentary writer</option><option value="local-outline">Local outline fallback</option></select></label>
          <label>Editorial angle<textarea rows={3} value={angle} onChange={(event) => setAngle(event.target.value)} /></label>
          <label>Verified research notes<textarea rows={7} value={researchNotes} onChange={(event) => setResearchNotes(event.target.value)} placeholder="Paste verified facts, source notes, dates, quotations, and constraints." /></label>
          <button className="primary-button" disabled={Boolean(busy)} onClick={() => void generateScript()}>{busy === "generate" ? "Writing…" : script ? "Regenerate draft" : "Generate draft"}</button>
        </div>
        <div className="studio-status-card"><p className="eyebrow">PRODUCTION STATUS</p><strong>{script?.status ?? "No script"}</strong><span>Revision {script?.revision ?? 0}</span><span>{script?.word_count ?? 0} words</span><span>{Math.round((script?.estimated_runtime_seconds ?? 0) / 60)} min estimated</span><span>{narration ? `${completeCount}/${narration.segment_count} audio segments` : "Narration not planned"}</span></div>
      </section>

      {script && <>
        <section className="panel">
          <div className="section-heading"><div><p className="eyebrow">02 · EDITOR</p><h3>Review the story scene by scene</h3></div><div className="studio-actions"><button className="ghost-button" disabled={Boolean(busy)} onClick={() => void saveDraft()}>{busy === "save" ? "Saving…" : "Save draft"}</button><button className="primary-button" disabled={Boolean(busy)} onClick={() => void approveAndApply()}>{busy === "approve" ? "Approving…" : "Approve + apply scenes"}</button></div></div>
          <div className="script-segment-list">{segments.map((segment, index) => <article className="script-segment-card" key={segment.segment_id || index}><div className="segment-heading"><span>Scene {index + 1}</span><input value={segment.act} onChange={(event) => updateSegment(index, { act: event.target.value })} /><small>{segment.estimated_duration_seconds.toFixed(1)} sec</small></div><label>Narration<textarea rows={5} value={segment.narration} onChange={(event) => updateSegment(index, { narration: event.target.value })} /></label><label>Visual intent<textarea rows={3} value={segment.visual_intent} onChange={(event) => updateSegment(index, { visual_intent: event.target.value })} /></label></article>)}</div>
        </section>
        <section className="panel studio-grid">
          <div><p className="eyebrow">03 · NARRATION</p><h3>Choose the voice and synthesize</h3><div className="voice-controls"><label>Voice<select value={voice} onChange={(event) => setVoice(event.target.value)}>{voices.map((item) => <option value={item} key={item}>{item}</option>)}</select></label><label>Speaking rate<input type="number" min={0.5} max={2} step={0.05} value={rate} onChange={(event) => setRate(Number(event.target.value))} /></label></div><div className="studio-actions"><button className="ghost-button" disabled={script.status !== "approved" || Boolean(busy)} onClick={() => void planNarration()}>{busy === "plan" ? "Planning…" : "Plan narration"}</button><button className="primary-button" disabled={!narration || script.status !== "approved" || Boolean(busy)} onClick={() => void synthesize(false)}>{busy === "synthesize" ? "Synthesizing…" : "Synthesize pending"}</button><button className="ghost-button" disabled={!narration || script.status !== "approved" || Boolean(busy)} onClick={() => void synthesize(true)}>Regenerate all</button></div></div>
          <div className="narration-progress"><strong>{narration?.status ?? "Not planned"}</strong>{(narration?.segments ?? []).map((item) => <div className={`audio-row ${item.status}`} key={item.segment_id}><span>Scene {item.scene_number}</span><span>{item.status}</span><span>{item.actual_duration_seconds ? `${item.actual_duration_seconds.toFixed(1)}s` : "—"}</span></div>)}</div>
        </section>
      </>}
    </main>
  );
}
