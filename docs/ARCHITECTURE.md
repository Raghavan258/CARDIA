# CARDIA Architecture

## Overview

CARDIA is a quality-aware vital-signs monitor with:

1. OpenCV desktop demos (legacy)
2. Python SDK with POS/CHROM + signal-quality gating
3. FastAPI session/WebSocket backend
4. React dashboard (browser camera → backend processing)
5. Offline evaluation (`python -m eval`)

```
┌──────────────┐     JPEG/WS      ┌─────────────────┐
│ React UI     │ ───────────────► │ FastAPI backend │
│ getUserMedia │ ◄─── vitals ──── │ SessionManager  │
└──────────────┘                  └────────┬────────┘
                                           │ thread pool
                                           ▼
                                  ┌─────────────────┐
                                  │ RPPGSDK         │
                                  │ face → ROI →    │
                                  │ buffer → POS/   │
                                  │ CHROM → HR +    │
                                  │ quality gate    │
                                  └─────────────────┘
```

## Data flow (live session)

1. Browser captures frames (`getUserMedia`), resizes ≤640px, JPEG-encodes @ ~12 FPS
2. Client sends `{type:frame, timestamp_s, data_base64}` on `/ws/sessions/{id}`
3. Backend decodes JPEG, enqueues into a **bounded queue** (drop oldest)
4. Worker runs `RPPGSDK.process_frame` off the event loop
5. Server emits `{type:vitals, latency_ms, payload}` including quality + diagnostics
6. UI charts plot measured RGB/pulse/spectrum/HR/motion only

## Processing pipeline (SDK)

```
Frame
  → FaceLandmarker (MediaPipe)
  → ROI means (forehead + cheeks)
  → Timestamped RGB buffer (EMA)
  → POS or CHROM pulse extraction
  → Heart-rate fusion (spectral / peaks / ACF)
  → SignalQualityAssessor (face, motion, lighting, pulse)
  → Accept HR only if allow_new_hr_estimate
  → SpO2 / BP / RR computed but marked experimental
```

## Module map

| Concern | Location |
|---------|----------|
| Config thresholds | `sdk/config.py` |
| Quality contract | `sdk/quality_types.py`, `sdk/signal_quality.py` |
| Algorithms | `algorithms/pos.py`, `algorithms/chrom.py` |
| Measurement states | `sdk/measurement_state.py` |
| API / WS | `backend/` |
| Dashboard | `frontend/` |
| Evaluation | `eval/` |

## Input adapters

- **Live:** browser frames (preferred for web)
- **Recorded:** `backend/adapters.iter_video_frames` or `eval.runner.evaluate_video`
- **Synthetic (eval only):** `eval.synthetic` — no personal video required
