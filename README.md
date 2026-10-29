# CARDIA

### Contactless vital-sign monitoring from a webcam — with signal-quality awareness, a live web dashboard, and reproducible evaluation.

**CARDIA** is a full-stack computer-vision and signal-processing system that estimates heart rate from ordinary camera frames using remote photoplethysmography (rPPG). It emphasizes **engineering honesty**: poor inputs are detected, rejected with explicit reasons, and never silently presented as fresh clinical readings.

> **Not a medical device.** Heart rate is the primary supported output. SpO₂, blood pressure, and respiration are experimental heuristics and are labeled as such in the product UI and API.

---

## Why this project exists

Most webcam “vitals” demos show a number as soon as a face appears. CARDIA is built around a harder question:

**When should the system refuse to publish a heart-rate estimate?**

That question drives the architecture — face tracking, motion, lighting, pulse stability, measurement states, WebSocket session lifecycle, diagnostic charts, and an offline evaluation harness.

---

## Demo

| Surface | Command | URL |
|--------|---------|-----|
| Web dashboard | `python -m backend` + `cd frontend && npm run dev` | http://127.0.0.1:5173 |
| API docs | `python -m backend` | http://127.0.0.1:8000/docs |
| Desktop OpenCV demo | `python examples/webcam_demo.py` | local window |

**Try the dashboard:** allow camera access → **Start monitoring** → hold still while the buffer warms up (~64 frames) → watch HR, quality reasons, and live signal charts.

---

## What recruiters / hiring managers should notice

| Skill area | What CARDIA demonstrates |
|------------|---------------------------|
| **Computer vision** | MediaPipe face landmarks, ROI extraction (forehead/cheeks), landmark overlays |
| **Signal processing** | POS & CHROM rPPG, bandpass/detrend, Welch PSD, peak/ACF heart-rate fusion |
| **Systems design** | Explicit measurement states, quality contracts, accept vs stale readings |
| **Backend** | FastAPI, WebSockets, bounded queues, backpressure, thread-pool offload |
| **Frontend** | React, TypeScript, Vite, Tailwind, Recharts — live diagnostics from real traces |
| **Quality engineering** | pytest suite (no webcam required), synthetic + recorded eval reports |
| **Product judgment** | Experimental outputs labeled; limitations and attribution documented |

---

## Features

### Core monitoring
- Real-time **heart-rate** estimation from webcam or browser frames
- Pluggable pulse extractors: **POS** (default) and **CHROM**
- Triple-method HR fusion (spectral + temporal peaks + autocorrelation)

### Signal-quality gate (first-class)
- Face tracking status and ROI stability
- Landmark-normalized **motion** scoring
- **Lighting** stats (brightness, under/over-exposure, abrupt changes)
- Pulse diagnostics (buffer length, spectral prominence, sampling gaps)
- Structured rejection codes (`FACE_NOT_DETECTED`, `EXCESSIVE_MOTION`, `POOR_LIGHTING`, …)
- **Accepted HR** vs **last accepted (stale)** with age — rejected estimates are never shown as current

### Web application
- Browser `getUserMedia` capture (camera stays on the client)
- JPEG frame streaming over WebSocket with client + server backpressure
- Live dashboard: state, quality, warnings, RGB / pulse / spectrum / HR / motion charts
- Session API: create → stream → stop / cleanup

### Evaluation
- Deterministic synthetic sessions with known BPM
- Baseline (ungated) vs quality-gated comparison reports
- Optional prerecorded video + synchronized reference CSV → MAE / RMSE when references exist
- **No invented accuracy metrics** when ground truth is absent

---

## Architecture (high level)

```
Browser camera  ──JPEG/WS──►  FastAPI SessionManager  ──thread pool──►  CARDIA SDK
     ▲                              │                                      │
     └──────── vitals + diagnostics─┘                                      │
                                                                           ▼
                                                    Face → ROI RGB → buffer
                                                    → POS/CHROM pulse → HR
                                                    → quality gate → accept/reject
```

Deeper walkthrough: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Tech stack

**Python:** OpenCV, MediaPipe, NumPy, SciPy, FastAPI, Uvicorn, Pydantic, pytest  

**Web:** React 19, TypeScript, Vite, Tailwind CSS, Recharts  

**Tooling:** WebSockets, bounded asyncio queues, ThreadPoolExecutor for CV workloads

---

## Quick start

### 1. Backend

```bash
git clone https://github.com/Raghavan258/CARDIA.git
cd CARDIA
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
python -m backend
```

### 2. Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**

### 3. Tests & evaluation

```bash
python -m pytest tests -q
python -m eval --synthetic --bpm 72 --duration 8
```

---

## Repository map

```
CARDIA/
├── sdk/                 # rPPG pipeline, quality gating, diagnostics
├── algorithms/          # POS, CHROM, shared filters
├── backend/             # FastAPI + WebSocket sessions
├── frontend/            # React monitoring dashboard
├── eval/                # Offline evaluation & reports
├── examples/            # OpenCV desktop demos
├── tests/               # Deterministic unit / API tests
├── docs/                # Architecture, limitations, milestones
└── models/              # Face Landmarker asset
```

---

## Measurement philosophy

| Output | Status | Notes |
|--------|--------|-------|
| Heart rate | **Primary** | From rPPG pulse; gated by signal quality |
| SpO₂ | Experimental | Ratio-of-ratios on webcam RGB — **not** pulse-ox validated |
| Blood pressure | Experimental | Pulse-morphology heuristic — **not** cuff validated |
| Respiration | Experimental | Pulse-amplitude envelope estimate |

Details and citations: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md), [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md)

---

## Robustness behavior

| Condition | System response |
|-----------|-----------------|
| Face missing / lost | No new HR; may reacquire and clear buffer |
| Excessive motion | Reject new HR; optional reacquisition |
| Poor / unstable lighting | Warnings + reject new accepts |
| Insufficient buffer / weak pulse | Stay in `initializing` / `low_quality` with explicit reasons |
| After a good reading goes bad | Keep **last accepted** HR separately with age; UI does not treat it as live |

Session states: `idle` → `initializing` → `measuring` / `low_quality` / `reacquiring` → `stopped`

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Data flow & module map |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Honest scope boundaries |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | Algorithms & third-party notices |
| [`docs/MILESTONE_*.md`](docs/) | Incremental build notes |
| [`LICENSE`](LICENSE) | MIT |

---

## Disclaimer

CARDIA is an **engineering research prototype** for portfolio and learning use. It is **not** FDA/CE cleared, not clinically validated, and must **not** be used for diagnosis, monitoring of patients, or treatment decisions.

---

## License

MIT — see [`LICENSE`](LICENSE).
