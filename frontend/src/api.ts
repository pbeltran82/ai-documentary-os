import type {
  AssetCandidate,
  AssetSearchResponse,
  MediaType,
  Project,
  ProjectCreate,
  ProjectDetail,
  ProviderName,
  ProviderStatus,
  Scene,
  SceneGeneratePayload,
  SceneGenerateResponse,
  SceneUpdate,
  SelectedAsset,
  ShotBrief,
  TimelineManifestResponse,
  TimelinePlan,
  TimelineStyle,
  VideoFormat,
  VisualDirectorResponse,
  VisualFeedback,
  VisualFeedbackReason,
} from "./types";
import type { MediaQAReport } from "./mediaQaTypes";
import type { BackgroundMusicSettingsUpdate, BackgroundMusicState } from "./musicTypes";
import "./version.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type TimelinePlanWithQA = TimelinePlan & { qa_report?: MediaQAReport | null };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (typeof options.body === "string" && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { message = ((await response.json()) as { detail?: string }).detail ?? message; } catch { /* keep fallback */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function dispatchQAInvalidated(projectId: number): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("atlas:timeline-qa-invalidated", { detail: { projectId } }));
}

function dispatchRendered(projectId: number, qaReport: MediaQAReport | null): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("atlas:timeline-rendered", { detail: { projectId, qaReport } }));
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: number) => request<ProjectDetail>(`/projects/${id}`),
  createProject: (payload: ProjectCreate) => request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id: number, payload: { video_format: VideoFormat }) => request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (id: number) => request<void>(`/projects/${id}`, { method: "DELETE" }),
  listScenes: (projectId: number) => request<Scene[]>(`/projects/${projectId}/scenes`),
  generateScenes: (projectId: number, payload: SceneGeneratePayload) => request<SceneGenerateResponse>(`/projects/${projectId}/scenes/generate`, { method: "POST", body: JSON.stringify(payload) }),
  planVisualBeats: (projectId: number, targetSeconds: number) => request<{ project_id: number; scene_count: number; visual_beat_count: number; target_beat_seconds: number }>(`/projects/${projectId}/production/visual-beats/plan`, { method: "POST", body: JSON.stringify({ target_seconds: targetSeconds }) }),
  updateScene: (sceneId: number, payload: SceneUpdate) => request<Scene>(`/scenes/${sceneId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteScene: (sceneId: number) => request<void>(`/scenes/${sceneId}`, { method: "DELETE" }),
  getProviderStatuses: () => request<ProviderStatus[]>("/providers/status"),
  getShotBrief: (sceneId: number, mediaType: MediaType) => request<ShotBrief>(`/scenes/${sceneId}/shot-brief?${new URLSearchParams({ media_type: mediaType })}`),
  directVisuals: (sceneId: number, options: { media_type: MediaType; provider?: "auto" | ProviderName; per_page?: number }) => {
    const params = new URLSearchParams({ media_type: options.media_type, per_page: String(options.per_page ?? 6) });
    return request<VisualDirectorResponse>(`/scenes/${sceneId}/adaptive-visual-director?${params}`);
  },
  rejectVisual: (sceneId: number, candidate: AssetCandidate, reason: VisualFeedbackReason) => request<VisualFeedback>(`/scenes/${sceneId}/visual-feedback`, { method: "POST", body: JSON.stringify({ provider: candidate.provider, provider_asset_id: candidate.provider_asset_id, reason }) }),
  resetVisualFeedback: (sceneId: number) => request<{ removed: number }>(`/scenes/${sceneId}/visual-feedback`, { method: "DELETE" }),
  searchAssets: (sceneId: number, options: { provider: ProviderName; query: string; media_type: MediaType; per_page?: number }) => {
    const params = new URLSearchParams({ provider: options.provider, query: options.query, media_type: options.media_type, per_page: String(options.per_page ?? 12) });
    return request<AssetSearchResponse>(`/scenes/${sceneId}/asset-candidates?${params}`);
  },
  selectAsset: (sceneId: number, candidate: AssetCandidate) => request<SelectedAsset>(`/scenes/${sceneId}/selected-asset`, { method: "PUT", body: JSON.stringify(candidate) }),
  removeSelectedAsset: (sceneId: number) => request<void>(`/scenes/${sceneId}/selected-asset`, { method: "DELETE" }),
  generateTimelineManifest: (projectId: number) => request<TimelineManifestResponse>(`/projects/${projectId}/timeline-manifest`, { method: "POST" }),
  buildTimelinePlan: async (projectId: number, style?: TimelineStyle) => {
    const plan = await request<TimelinePlan>(`/projects/${projectId}/timeline/plan`, { method: "POST", body: style ? JSON.stringify(style) : undefined });
    if (style) dispatchQAInvalidated(projectId);
    return plan;
  },
  uploadNarration: async (projectId: number, file: File) => {
    const plan = await request<TimelinePlan>(`/projects/${projectId}/timeline/narration?filename=${encodeURIComponent(file.name)}`, { method: "PUT", body: file, headers: { "Content-Type": file.type || "application/octet-stream" } });
    dispatchQAInvalidated(projectId);
    return plan;
  },
  removeNarration: async (projectId: number) => {
    const plan = await request<TimelinePlan>(`/projects/${projectId}/timeline/narration`, { method: "DELETE" });
    dispatchQAInvalidated(projectId);
    return plan;
  },
  getBackgroundMusic: (projectId: number) => request<BackgroundMusicState>(`/projects/${projectId}/timeline/music`),
  uploadBackgroundMusic: async (projectId: number, file: File) => {
    const state = await request<BackgroundMusicState>(`/projects/${projectId}/timeline/music?filename=${encodeURIComponent(file.name)}`, { method: "PUT", body: file, headers: { "Content-Type": file.type || "application/octet-stream" } });
    dispatchQAInvalidated(projectId);
    return state;
  },
  updateBackgroundMusic: async (projectId: number, payload: BackgroundMusicSettingsUpdate) => {
    const state = await request<BackgroundMusicState>(`/projects/${projectId}/timeline/music`, { method: "PATCH", body: JSON.stringify(payload) });
    dispatchQAInvalidated(projectId);
    return state;
  },
  removeBackgroundMusic: async (projectId: number) => {
    const state = await request<BackgroundMusicState>(`/projects/${projectId}/timeline/music`, { method: "DELETE" });
    dispatchQAInvalidated(projectId);
    return state;
  },
  renderTimeline: async (projectId: number, style?: TimelineStyle) => {
    const plan = await request<TimelinePlanWithQA>(`/projects/${projectId}/timeline/render`, { method: "POST", body: style ? JSON.stringify(style) : undefined });
    dispatchRendered(projectId, plan.qa_report ?? null);
    return plan;
  },
  runTimelineQA: (projectId: number) => request<MediaQAReport>(`/projects/${projectId}/timeline/qa`, { method: "POST" }),
  getTimelineQA: (projectId: number) => request<MediaQAReport>(`/projects/${projectId}/timeline/qa`),
};
