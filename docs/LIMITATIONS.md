# Limitations

CARDIA is an **engineering research prototype**, not a medical device.

## Clinical / product

- Not FDA/CE cleared or clinically validated
- Heart-rate estimates can err under motion, poor lighting, makeup, facial hair, or camera artifacts
- SpO2, blood pressure, and respiration outputs are **experimental heuristics** and must not be used for diagnosis or treatment
- Webcam rPPG is sensitive to illumination spectrum and automatic exposure/white-balance

## Signal quality

- Quality thresholds are initial defaults; tune on held-out recordings (keep eval split separate)
- Passing quality checks does **not** guarantee physiological correctness
- Landmark motion is a proxy for head movement, not a full optical-flow model

## Evaluation data

- Bundled reproducible eval uses **synthetic** RGB/landmark sequences
- Synthetic MAE is not real-world accuracy
- Personal videos and PHI must not be committed to Git (`data/eval` is gitignored except `.gitkeep`)
- MAE/RMSE appear only when a synchronized reference CSV (`timestamp_s,bpm`) is supplied

## Platform

- Live web mode depends on browser camera permissions and local backend availability
- Base64 JPEG over WebSocket is bandwidth-heavy versus binary frames
- MediaPipe model download may require network on first FaceLandmarker use
