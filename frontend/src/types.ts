export type ProjectStatus =
  | "planning"
  | "research"
  | "script"
  | "storyboard"
  | "assets"
  | "timeline"
  | "complete";

export type AssetType =
  | "stock_video"
  | "stock_image"
  | "ai_image"
  | "ai_video"
  | "chart"
  | "text_animation";

export type AssetStatus = "missing" | "searching" | "selected" | "ready";
export type MediaType = "video" | "photo";
export type ProviderName = "pixabay" | "unsplash" | "wikimedia" | "nasa" | "pexels";
export type NarrationAlignmentStatus = "missing" | "aligned" | "shorter" | "longer";
export type VisualFeedbackReason =
  | "wrong_concept"
  | "too_generic"
  | "repetitive"
  | "poor_quality"
  | "bad_style";

export interface SelectedAsset {
  id: number;
  scene_id: number;
  provider: ProviderName;
  provider_asset_id: string;
  media_type: MediaType;
  source_url: string;
  preview_url: string;
  download_url: string;
  remote_download_url: string;
  creator: string;
  creator_url: string;
  width: number;
  height: number;
  duration_seconds: number | null;
  license_name: string;
  license_url: string;
  attribution: string;
  local_path: string;
  local_preview_path: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  downloaded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetCandidate {
  provider: ProviderName;
  provider_asset_id: string;
  media_type: MediaType;
  source_url: string;
  preview_url: string;
  download_url: string;
  creator: string;
  creator_url: string;
  width: number;
  height: number;
  duration_seconds: number | null;
  license_name: string;
  license_url: string;
  attribution: string;
  description: string;
  keywords: string[];
  query_variant: string;
  director_score: number;
  director_reasons: string[];
  director_warnings: string[];
  shortlist_rank: number | null;
}

export interface ProviderStatus {
  provider: ProviderName;
  label: string;
  configured: boolean;
  requires_key: boolean;
  supports_media_types: MediaType[];
  setup_hint: string;
  source_url: string;
}

export interface AssetSearchResponse {
  provider: ProviderName;
  configured: boolean;
  query: string;
  media_type: MediaType;
  source_url: string;
  rate_limit_remaining: number | null;
  candidates: AssetCandidate[];
}

export interface ShotBrief {
  scene_id: number;
  subject: string;
  action: string;
  setting: string;
  framing: string;
  mood: string;
  must_show: string[];
  must_avoid: string[];
  query_variants: string[];
}

export interface VisualDirectorResponse {
  media_type: MediaType;
  shot_brief: ShotBrief;
  search_queries: string[];
  providers_searched: ProviderName[];
  rate_limit_remaining: number | null;
  rejected_count: number;
  candidates: AssetCandidate[];
}

export interface VisualFeedback {
  scene_id: number;
  provider: ProviderName;
  provider_asset_id: string;
  reason: VisualFeedbackReason;
  created_at: string;
}

export interface Scene {
  id: number;
  project_id: number;
  scene_number: number;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  narration: string;
  visual_intent: string;
  search_keywords: string[];
  preferred_asset_type: AssetType;
  asset_status: AssetStatus;
  selected_asset: SelectedAsset | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  title: string;
  topic: string;
  target_minutes: number;
  audience: string;
  tone: string;
  visual_style: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  scenes: Scene[];
}

export interface ProjectCreate {
  title: string;
  topic: string;
  target_minutes: number;
  audience: string;
  tone: string;
  visual_style: string;
}

export interface SceneGeneratePayload {
  narration: string;
  target_scene_seconds: number;
  replace_existing: boolean;
}

export interface SceneGenerateResponse {
  project_id: number;
  scene_count: number;
  total_duration_seconds: number;
  scenes: Scene[];
}

export interface SceneUpdate {
  narration?: string;
  duration_seconds?: number;
  visual_intent?: string;
  search_keywords?: string[];
  preferred_asset_type?: AssetType;
  asset_status?: AssetStatus;
}

export interface TimelineManifestResponse {
  project_id: number;
  relative_path: string;
  public_url: string;
  manifest: Record<string, unknown>;
}

export interface TimelineMissingScene {
  scene_id: number;
  scene_number: number;
  reason: string;
}

export interface TimelineClip {
  scene_id: number;
  scene_number: number;
  input_index: number;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  narration: string;
  visual_intent: string;
  provider: ProviderName;
  provider_asset_id: string;
  media_type: MediaType;
  local_path: string;
  local_url: string;
  preview_url: string;
  source_url: string;
  creator: string;
  license_name: string;
  attribution: string;
  source_file: string;
  assembly_action: string;
}

export interface Voiceover {
  original_filename: string;
  relative_path: string;
  public_url: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  duration_seconds: number;
  uploaded_at: string;
}

export interface TimelinePlan {
  schema_version: string;
  generated_at: string;
  project_id: number;
  project_title: string;
  ready: boolean;
  ffmpeg_available: boolean;
  runtime_seconds: number;
  clip_count: number;
  missing_scenes: TimelineMissingScene[];
  settings: {
    width: number;
    height: number;
    fps: number;
    video_codec: string;
    pixel_format: string;
    audio: string;
    audio_codec: string | null;
    audio_bitrate: string | null;
    audio_sample_rate: number | null;
  };
  voiceover: Voiceover | null;
  alignment_status: NarrationAlignmentStatus;
  duration_delta_seconds: number | null;
  alignment_message: string;
  clips: TimelineClip[];
  command: string[];
  output_relative_path: string;
  output_url: string;
  output_exists: boolean;
  output_size_bytes: number;
  rendered_at: string | null;
  plan_relative_path: string;
  plan_url: string;
  script_relative_path: string;
  script_url: string;
  message: string | null;
}
