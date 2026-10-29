# Milestone D — FastAPI Streaming Backend

**Date:** 2026-10-29  
**Status:** Complete (full pytest suite green)

## What shipped

A functional FastAPI backend that:

- Creates / stops monitoring sessions
- Accepts browser JPEG frames over WebSocket (live mode)
- Plays authorized prerecorded videos (recorded mode)
- Processes frames in a thread pool (event loop stays responsive)
- Uses a **bounded frame queue** (default size 2) and drops the oldest frame under backpressure
- Returns structured vitals + quality + latency stats

OpenCV desktop demos remain available; this backend is additive.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/config` | Backend + quality thresholds + frame protocol |
| `POST` | `/api/sessions` | Create session (`live` or `recorded`) |
| `GET` | `/api/sessions/{id}` | Session state / stats |
| `POST` | `/api/sessions/{id}/stop` | Stop and release |
| `WS` | `/ws/sessions/{id}` | Frames in (live) / vitals out |

### Create session body

```json
{
  "algorithm": "pos",
  "input_mode": "live",
  "video_path": null,
  "max_width": 640,
  "target_fps": 15
}
```

For `recorded`, `video_path` must resolve under `data/eval` or `data/recordings`.

### WebSocket frame protocol (live)

Client → server:

```json
{
  "type": "frame",
  "timestamp_s": 1.234,
  "mime": "image/jpeg",
  "data_base64": "<jpeg-base64>"
}
```

Also: `{"type":"ping"}`, `{"type":"stop"}`.

Server → client:

```json
{
  "type": "vitals",
  "session_id": "...",
  "server_ts": 1710000000.0,
  "latency_ms": 12.3,
  "stats": {"frames_received": 10, "frames_dropped": 1, "frames_processed": 9},
  "payload": { "bpm": 72.0, "bpm_accepted": true, "state": "measuring", "quality": {}, "...": "..." }
}
```

Errors: `{"type":"error","code":"INVALID_FRAME","message":"..."}`.

## Files

| Path | Role |
|------|------|
| `backend/app.py` | FastAPI routes + WebSocket |
| `backend/sessions.py` | Session manager, queue, worker |
| `backend/adapters.py` | JPEG decode + recorded video iterator |
| `backend/schemas.py` | Request models + protocol docs |
| `backend/settings.py` | Limits / CORS / allowed video roots |
| `backend/__main__.py` | `python -m backend` |
| `tests/test_api.py` | HTTP + WS tests (mocked SDK) |
| `tests/test_session_queue.py` | Backpressure drop test |
| `data/eval/` | Allowed folder for evaluation videos |

## Run the backend

```powershell
cd C:\Project\CARDIA\rPPG-SDK
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend
```

Then open `http://127.0.0.1:8000/api/health` and `http://127.0.0.1:8000/docs`.

## Design decisions

1. **Browser owns the camera** in live mode (`getUserMedia` in Milestone E); backend never opens webcam for web sessions (`RPPGSDK(open_camera=False)`).
2. **JPEG @ ≤640px / ~15 FPS guidance** — full-res unbounded streams are rejected by size/resize limits.
3. **ThreadPoolExecutor** for `process_frame` so MediaPipe/OpenCV work does not block asyncio.
4. **Queue size 2** — prefer fresh frames over backlog (drop oldest).
5. **Recorded adapter is separate** from live WS ingest (`iter_video_frames` feeder task).
6. **Disclaimer** in `/api/config`: SpO2/BP/RR remain experimental.

## Tests

```powershell
python -m pytest tests -q
```

API tests mock `RPPGSDK` so no webcam/MediaPipe is required for CI-style runs.

## Remaining limitations

- No authentication (local development only)
- Base64 JPEG over JSON is simple but less efficient than binary WS frames
- Frontend dashboard not built yet (Milestone E)
- No recorded-video accuracy report yet (Milestone F)
- Real MediaPipe latency under load not yet benchmarked in this milestone

## Next

**Milestone E** — React + Vite + Tailwind dashboard with live diagnostics.
