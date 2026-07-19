import { ChangeEvent, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { BackgroundMusicSettings, BackgroundMusicState } from "../musicTypes";
import type { ProjectDetail } from "../types";
import { TimelineBuilderWithQA } from "./TimelineBuilderWithQA";
import "../background-music.css";

interface TimelineBuilderWithMusicProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenAssets: () => void;
  onOpenScenes: () => void;
  onProjectChanged: () => Promise<void> | void;
}

const defaultSettings: BackgroundMusicSettings = {
  music_enabled: false,
  music_gain_db: -22,
  music_ducking_db: -8,
  music_fade_seconds: 1.5,
};

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TimelineBuilderWithMusic(props: TimelineBuilderWithMusicProps) {
  const { project } = props;
  const [musicState, setMusicState] = useState<BackgroundMusicState>({ background_music: null, settings: defaultSettings });
  const [settings, setSettings] = useState<BackgroundMusicSettings>(defaultSettings);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loadingMusic, setLoadingMusic] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [musicError, setMusicError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function acceptState(next: BackgroundMusicState) {
    setMusicState(next);
    setSettings(next.settings);
    setDirty(false);
  }

  useEffect(() => {
    setLoadingMusic(true);
    setMusicError("");
    void api.getBackgroundMusic(project.id)
      .then(acceptState)
      .catch((err: unknown) => setMusicError(err instanceof Error ? err.message : "Unable to load background music"))
      .finally(() => setLoadingMusic(false));
  }, [project.id]);

  function chooseMusic(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setMusicError("");
  }

  function changeSetting<K extends keyof BackgroundMusicSettings>(key: K, value: BackgroundMusicSettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
    setDirty(true);
  }

  async function uploadMusic() {
    if (!selectedFile) return;
    setUploading(true);
    setMusicError("");
    try {
      acceptState(await api.uploadBackgroundMusic(project.id, selectedFile));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setMusicError(err instanceof Error ? err.message : "Unable to upload background music");
    } finally {
      setUploading(false);
    }
  }

  async function saveSettings() {
    setSaving(true);
    setMusicError("");
    try {
      acceptState(await api.updateBackgroundMusic(project.id, settings));
    } catch (err) {
      setMusicError(err instanceof Error ? err.message : "Unable to save music settings");
    } finally {
      setSaving(false);
    }
  }

  async function removeMusic() {
    if (!window.confirm("Remove the background music from this project?")) return;
    setRemoving(true);
    setMusicError("");
    try {
      acceptState(await api.removeBackgroundMusic(project.id));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setMusicError(err instanceof Error ? err.message : "Unable to remove background music");
    } finally {
      setRemoving(false);
    }
  }

  const track = musicState.background_music;
  const controlsDisabled = !track || loadingMusic || uploading || removing;

  return (
    <div className="timeline-music-shell">
      <TimelineBuilderWithQA {...props} />
      <div className="background-music-dock">
        <section className={`panel background-music-panel ${track && settings.music_enabled ? "active" : "inactive"}`}>
          <div className="section-heading background-music-heading">
            <div>
              <p className="eyebrow">DOCUMENTARY SOUND DESIGN</p>
              <h3>Controlled background music</h3>
              <p className="background-music-intro">
                Music remains separate from narration, loops to the exact runtime, fades cleanly,
                and automatically ducks whenever the voiceover is present.
              </p>
            </div>
            <span className={`asset-status ${track && settings.music_enabled ? "ready" : "missing"}`}>
              {track ? settings.music_enabled ? "Music active" : "Music muted" : "No track"}
            </span>
          </div>

          {musicError && <div className="error-banner">{musicError}</div>}

          <div className="background-music-upload">
            <label className="music-file-picker">
              <span>Instrumental music file</span>
              <input ref={fileInputRef} type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg,.webm" onChange={chooseMusic} />
            </label>
            <button className="secondary-button" disabled={!selectedFile || uploading} onClick={() => void uploadMusic()}>
              {uploading ? "Uploading music…" : track ? "Replace track" : "Upload track"}
            </button>
          </div>

          {selectedFile && <p className="music-selection">Selected: {selectedFile.name}</p>}

          {track ? (
            <>
              <div className="music-track-card">
                <div>
                  <span className="eyebrow">LOCAL MUSIC BED</span>
                  <strong>{track.original_filename}</strong>
                  <small>{formatBytes(track.file_size_bytes)} · {formatTime(track.duration_seconds)}</small>
                </div>
                <audio controls preload="metadata" src={track.public_url} />
              </div>

              <div className="music-enable-row">
                <label className="music-toggle">
                  <input
                    type="checkbox"
                    checked={settings.music_enabled}
                    disabled={controlsDisabled}
                    onChange={(event) => changeSetting("music_enabled", event.target.checked)}
                  />
                  <span>Include music in the next timeline render</span>
                </label>
                <div className="music-presets" aria-label="Music level presets">
                  <button type="button" onClick={() => changeSetting("music_gain_db", -24)}>Subtle</button>
                  <button type="button" onClick={() => changeSetting("music_gain_db", -22)}>Balanced</button>
                  <button type="button" onClick={() => changeSetting("music_gain_db", -18)}>Cinematic</button>
                </div>
              </div>

              <div className="music-control-grid">
                <label>
                  <span>Music bed level <strong>{settings.music_gain_db.toFixed(0)} dB</strong></span>
                  <input
                    type="range"
                    min={-30}
                    max={-14}
                    step={1}
                    value={settings.music_gain_db}
                    disabled={controlsDisabled}
                    onChange={(event) => changeSetting("music_gain_db", Number(event.target.value))}
                  />
                  <small>Start around −22 dB for restrained documentary texture.</small>
                </label>
                <label>
                  <span>Narration ducking <strong>{settings.music_ducking_db.toFixed(0)} dB</strong></span>
                  <input
                    type="range"
                    min={-16}
                    max={0}
                    step={1}
                    value={settings.music_ducking_db}
                    disabled={controlsDisabled}
                    onChange={(event) => changeSetting("music_ducking_db", Number(event.target.value))}
                  />
                  <small>More negative values push music farther behind speech.</small>
                </label>
                <label>
                  <span>Opening and closing fade <strong>{settings.music_fade_seconds.toFixed(1)}s</strong></span>
                  <input
                    type="range"
                    min={0}
                    max={4}
                    step={0.25}
                    value={settings.music_fade_seconds}
                    disabled={controlsDisabled}
                    onChange={(event) => changeSetting("music_fade_seconds", Number(event.target.value))}
                  />
                  <small>The bed is looped first, then faded to the exact export duration.</small>
                </label>
              </div>

              <div className="music-control-footer">
                <p>{track.rights_notice}</p>
                <div>
                  <button className="ghost-button" disabled={removing || saving} onClick={() => void removeMusic()}>
                    {removing ? "Removing…" : "Remove track"}
                  </button>
                  <button className="primary-button" disabled={!dirty || saving || controlsDisabled} onClick={() => void saveSettings()}>
                    {saving ? "Saving sound design…" : "Apply music settings"}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="background-music-empty">
              <strong>Add a licensed instrumental track</strong>
              <p>MP3, WAV, M4A, AAC, FLAC, OGG, and WebM are supported. Uploading a track enables the balanced −22 dB preset automatically.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
