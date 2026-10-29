# Milestone E — React Web Dashboard

**Date:** 2026-10-29  
**Status:** Complete (frontend production build OK; pytest green)

## What shipped

A Vite + React + TypeScript + Tailwind dashboard that:

- Requests camera access via `getUserMedia`
- Creates a backend session and streams JPEG frames over WebSocket (~12 FPS, ≤640px)
- Applies client-side backpressure (`MAX_IN_FLIGHT = 2`)
- Shows live preview with landmark overlay from backend diagnostics
- Displays measurement **state**, quality category, rejection reasons (text, not color-only)
- Distinguishes **accepted HR** vs **last accepted (stale)** with age
- Marks SpO2 / BP / respiration as **experimental**
- Plots **measured** RGB, pulse, spectrum, HR history, motion, and lighting stats

## Run

Terminal 1 — API:

```powershell
cd C:\Project\CARDIA\rPPG-SDK
.\venv\Scripts\Activate.ps1
python -m backend
```

Terminal 2 — UI:

```powershell
cd C:\Project\CARDIA\rPPG-SDK\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` (Vite proxies `/api` and `/ws` to port 8000).

## Files

| Path | Role |
|------|------|
| `frontend/` | Vite React app |
| `frontend/src/hooks/useCamera.ts` | getUserMedia lifecycle |
| `frontend/src/hooks/useMonitorSession.ts` | Session + WS + frame loop |
| `frontend/src/components/*` | Camera, vitals, quality, charts, status |
| `sdk/diagnostics.py` | Compact measured traces for WS |
| `sdk/rppg_sdk.py` | Attaches `diagnostics` + session elapsed |

## Design notes

- Brand-forward header (**CARDIA**) with Sora + IBM Plex Sans
- Teal / slate palette (not purple / cream / broadsheet defaults)
- Dashboard layout intentionally multi-panel (monitoring surface)
- Charts use Recharts with `isAnimationActive={false}` for live updates
- No fabricated series — empty charts show “Waiting for measured data…”

## Remaining limitations

- Landmark overlay is a sparse subset (bandwidth), not full 468 mesh
- Base64 JPEG over JSON is simple but heavy; binary WS frames would be better
- No auth; local-dev CORS only
- Recorded-video evaluation UI not built (Milestone F)
- StrictMode remount in dev can briefly double-connect; production build is fine

## Next

**Milestone F** — Recorded-video evaluation, performance reporting, final documentation.
