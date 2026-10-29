# Third-party attribution

## Algorithms (papers)

- **POS** — Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017). Algorithmic Principles of Remote PPG. *IEEE Transactions on Biomedical Engineering*.
- **CHROM** — de Haan, G., & Jeanne, V. (2013). Robust Pulse Rate From Chrominance-Based rPPG. *IEEE Transactions on Biomedical Engineering*.

## Major dependencies

| Component | Project | Notes |
|-----------|---------|-------|
| Face landmarks | [MediaPipe](https://developers.google.com/mediapipe) | Face Landmarker model (`models/face_landmarker.task`) |
| Vision / I/O | OpenCV | Capture, JPEG, drawing |
| Numerics | NumPy, SciPy | Signal processing |
| API | FastAPI, Uvicorn, Pydantic | Session + WebSocket backend |
| UI | React, Vite, Tailwind CSS, Recharts | Dashboard |

Dependency licenses are governed by their respective upstream distributions; review them before commercial redistribution.

## Models

The MediaPipe Face Landmarker `.task` asset is subject to Google MediaPipe model terms. It may be auto-downloaded on first use if missing.
