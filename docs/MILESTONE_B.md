# Milestone B — Signal Quality Module

**Date:** 2026-10-29  
**Status:** Complete (26/26 pytest passing)

## Files added / changed

### Added
| Path | Role |
|------|------|
| `sdk/config.py` | Typed thresholds (motion, lighting, face, pulse) with documented rationale |
| `sdk/quality_types.py` | Enums, reason codes, `QualityResult` contract |
| `sdk/motion.py` | Landmark-normalized, timestamp-aware motion estimator |
| `sdk/lighting.py` | ROI luminance / exposure / abrupt-change assessor |
| `sdk/face_quality.py` | Face presence, completeness, ROI stability |
| `sdk/pulse_quality.py` | Pulse metrics + separate component score weights |
| `sdk/signal_quality.py` | Aggregator; hard rejects vs composite score |
| `tests/` | Deterministic unit tests (no webcam required) |
| `.gitignore` | venv, caches, private data |
| `docs/MILESTONE_B.md` | This note |

### Changed
| Path | Change |
|------|--------|
| `sdk/signal_extractor.py` | Optional per-sample timestamps |
| `sdk/rppg_sdk.py` | Quality gating; richer vitals payload; preserves POS/HR |
| `sdk/roi_extractor.py` | Public `region_map` alias |
| `examples/webcam_demo.py` | Quality category + rejection / last-accepted age text |
| `requirements.txt` | Added `pytest>=7.0` |

## Design decisions

1. **Incremental, not a rewrite** — POS, MediaPipe face, ROI, and HR fusion unchanged in algorithm logic.
2. **Hard rejects ≠ score** — `allow_new_hr_estimate` is False whenever `rejection_reasons` is non-empty (or initializing / face not OK / high motion). Composite `overall_score` is diagnostic only.
3. **Individual metrics retained** — Pulse metrics (`pulse_std`, spectral prominence, gaps, etc.) are always present on `QualityResult.pulse` for debugging.
4. **Backward-compatible vitals** — Legacy keys (`bpm`, `spo2`, …) remain. New keys: `quality`, `bpm_raw`, `bpm_accepted`, `last_accepted_bpm`, `last_accepted_bpm_age_s`, `experimental`.
5. **SpO2/BP/RR** — Still computed for continuity but marked `experimental: true` in the vitals payload; HR is the gated primary output.
6. **Demo** — OpenCV UI shows quality text and stale last-accepted HR age; rejected frames do not put a new value into the HR card as current.

## How to run tests

```powershell
cd C:\Project\CARDIA\rPPG-SDK
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests -q
```

## Remaining limitations

- Quality thresholds are **initial defaults**; not yet tuned on held-out video (Milestone F).
- Motion uses landmark displacement only (not optical flow).
- Lighting checks do not prove physiological validity — they only flag exposure risk.
- OpenCV demo is not yet a full diagnostic dashboard (Milestone E).
- CHROM not added yet (Milestone C scope).
- No FastAPI / WebSocket layer yet (Milestone D).
- Buffer reset on prolonged face loss remains time/FPS heuristic-based.

## Next

**Milestone C** — Motion-aware HR pipeline polish, optional CHROM as a separately testable method, explicit measurement states, safer reacquisition.
