export type MeasurementState =
  | 'idle'
  | 'initializing'
  | 'measuring'
  | 'low_quality'
  | 'reacquiring'
  | 'error'
  | 'stopped'

export interface QualityPayload {
  category: string
  overall_score: number | null
  face_status: string
  motion_score: number | null
  motion_category: string
  lighting: {
    mean_brightness: number | null
    median_brightness: number | null
    underexposed_fraction: number | null
    overexposed_fraction: number | null
    brightness_delta: number | null
    roi_brightness_spread: number | null
    status: string
  }
  pulse: {
    buffer_frames?: number
    buffer_duration_s?: number | null
    effective_fps?: number | null
    [key: string]: unknown
  }
  warnings: string[]
  rejection_reasons: string[]
  allow_new_hr_estimate: boolean
}

export interface Diagnostics {
  rgb: { r: number[]; g: number[]; b: number[]; t: number[] }
  pulse: { y: number[]; t: number[] }
  spectrum: { freq_hz: number[]; psd: number[] }
  hr_history: number[]
  hr_series: { t: number; bpm: number }[]
  motion_history: { t: number; score: number }[]
  landmarks_norm: { x: number; y: number }[] | null
}

export interface VitalsPayload {
  bpm: number | null
  bpm_raw: number | null
  bpm_accepted: boolean
  last_accepted_bpm: number | null
  last_accepted_bpm_age_s: number | null
  spo2: number | null
  bp_sys: number | null
  bp_dia: number | null
  resp_rate: number | null
  state: MeasurementState
  algorithm: string
  effective_fps: number | null
  session_elapsed_s: number | null
  quality: QualityPayload
  diagnostics: Diagnostics | null
  experimental: Record<string, boolean>
}

export interface VitalsMessage {
  type: 'vitals'
  session_id: string
  server_ts: number
  latency_ms: number
  stats: {
    frames_received: number
    frames_dropped: number
    frames_processed: number
  }
  payload: VitalsPayload
}

export type ServerMessage =
  | VitalsMessage
  | { type: 'status'; state?: string; message?: string; input_mode?: string }
  | { type: 'error'; code?: string; message: string }
  | { type: 'pong' }
