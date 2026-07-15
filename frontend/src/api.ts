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
  TimelineManifestResponse,
  TimelinePlan,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Keep the fallback error message when the response is not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: number) => request<ProjectDetail>(`/projects/${id}`),
  createProject: (payload: ProjectCreate) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: number) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
  listScenes: (projectId: number) =>
    request<Scene[]>(`/projects/${projectId}/scenes`),
  generateScenes: (projectId: number, payload: SceneGeneratePayload) =>
    request<SceneGenerateResponse>(`/projects/${projectId}/scenes/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateScene: (sceneId: number, payload: SceneUpdate) =>
    request<Scene>(`/scenes/${sceneId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteScene: (sceneId: number) =>
    request<void>(`/scenes/${sceneId}`, { method: "DELETE" }),
  getProviderStatuses: () => request<ProviderStatus[]>("/providers/status"),
  searchAssets: (
    sceneId: number,
    options: {
      provider: ProviderName;
      query: string;
      media_type: MediaType;
      per_page?: number;
    },
  ) => {
    const params = new URLSearchParams({
      provider: options.provider,
      query: options.query,
      media_type: options.media_type,
      per_page: String(options.per_page ?? 12),
    });
    return request<AssetSearchResponse>(
      `/scenes/${sceneId}/asset-candidates?${params.toString()}`,
    );
  },
  selectAsset: (sceneId: number, candidate: AssetCandidate) =>
    request<SelectedAsset>(`/scenes/${sceneId}/selected-asset`, {
      method: "PUT",
      body: JSON.stringify(candidate),
    }),
  removeSelectedAsset: (sceneId: number) =>
    request<void>(`/scenes/${sceneId}/selected-asset`, { method: "DELETE" }),
  generateTimelineManifest: (projectId: number) =>
    request<TimelineManifestResponse>(`/projects/${projectId}/timeline-manifest`, {
      method: "POST",
    }),
  buildTimelinePlan: (projectId: number) =>
    request<TimelinePlan>(`/projects/${projectId}/timeline/plan`, {
      method: "POST",
    }),
  uploadNarration: (projectId: number, file: File) =>
    request<TimelinePlan>(
      `/projects/${projectId}/timeline/narration?filename=${encodeURIComponent(file.name)}`,
      {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type || "application/octet-stream",
        },
      },
    ),
  removeNarration: (projectId: number) =>
    request<TimelinePlan>(`/projects/${projectId}/timeline/narration`, {
      method: "DELETE",
    }),
  renderTimeline: (projectId: number) =>
    request<TimelinePlan>(`/projects/${projectId}/timeline/render`, {
      method: "POST",
    }),
};
