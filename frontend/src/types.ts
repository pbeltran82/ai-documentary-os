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
