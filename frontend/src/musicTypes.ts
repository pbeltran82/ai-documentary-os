export interface BackgroundMusicAsset {
  original_filename: string;
  relative_path: string;
  public_url: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  duration_seconds: number;
  uploaded_at: string;
  rights_notice: string;
}

export interface BackgroundMusicSettings {
  music_enabled: boolean;
  music_gain_db: number;
  music_ducking_db: number;
  music_fade_seconds: number;
}

export interface BackgroundMusicState {
  background_music: BackgroundMusicAsset | null;
  settings: BackgroundMusicSettings;
}

export type BackgroundMusicSettingsUpdate = Partial<BackgroundMusicSettings>;
