# Milestone C — Motion-Aware HR Pipeline & Measurement States

**Date:** 2026-10-29  
**Status:** Complete (35/35 pytest passing)

## Goals addressed

- Timestamp-aware effective FPS for filtering / HR
- Explicit session states (`idle` → `initializing` → `measuring` / `low_quality` / `reacquiring` / `error` / `stopped`)
- Safe rejection: rejected HR never published as fresh `bpm`; stale value only via `last_accepted_bpm` + age
- Motion / tracking discontinuity triggers buffer clear + reacquisition
- CHROM added as a separately testable method alongside POS
- Structured JSON logging of HR accept/reject decisions
- `process_frame()` for injected frames (tests / future web backend)

## Files added / changed

### Added
| Path | Role |
|------|------|
| `algorithms/filters.py` | Shared bandpass |
| `algorithms/chrom.py` | CHROM (de Haan & Jeanne, 2013) |
| `sdk/measurement_state.py` | State enum + reacquire reason set |
| `sdk/logging_utils.py` | JSON estimate logging |
| `tests/test_chrom.py` | CHROM + POS/CHROM synthetic agreement |
| `tests/test_measurement_state.py` | States, stale HR, reacquire |
| `docs/MILESTONE_C.md` | This note |

### Changed
| Path | Change |
|------|--------|
| `algorithms/pos.py` | Uses shared `bandpass` |
| `sdk/rppg_algorithm.py` | Supports `pos` / `chrom`; `process_both()` |
| `sdk/rppg_sdk.py` | States, gating, reacquisition, `start`/`stop`, `process_frame` |
| `examples/webcam_demo.py` | Shows measurement state in overlay |

## Design decisions

1. **Default algorithm remains POS** — CHROM is opt-in via `RPPGSDK(algorithm="chrom")` until recorded-video evaluation (Milestone F) compares them fairly.
2. **Synthetic comparison only so far** — On clean 72/80 BPM synthetic RGB, both POS and CHROM recover HR within ~6 BPM and agree within ~8 BPM. This is **not** evidence of real-world superiority.
3. **Reacquisition triggers** — `EXCESSIVE_MOTION`, `ABRUPT_LANDMARK_DISPLACEMENT`, `FACE_TRACKING_LOST`, `IRREGULAR_SAMPLING` clear the RGB buffer so corrupted history is not reused.
4. **Spectral peaks after failed quality** — Candidate HR may still be computed into `bpm_raw` for diagnostics, but `bpm` / `bpm_accepted` stay unset when gating fails.
5. **`open_camera=False`** — Enables unit tests and upcoming FastAPI workers without grabbing the webcam at construct time.

## How to compare POS vs CHROM (synthetic)

```python
from sdk.rppg_algorithm import RPPGAlgorithm
alg = RPPGAlgorithm(window_size=32)
pulses = alg.process_both(rgb_signal, fps=30.0)
```

## Remaining limitations

- No recorded-video MAE/RMSE yet (Milestone F)
- CHROM not selected automatically; no online fusion of POS+CHROM
- Face detector still constructed even when `open_camera=False` (mock in tests)
- Logging goes to stderr by default; no rotating file handler yet
- Web dashboard / FastAPI still pending (Milestone D)

## Next

**Milestone D** — FastAPI streaming backend and session management.
