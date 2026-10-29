# Milestone F — Evaluation, Performance, Documentation

**Date:** 2026-10-29  
**Status:** Complete

## Deliverables

1. **Offline evaluation package** (`eval/`)
   - Synthetic deterministic sessions with known BPM
   - Baseline (gating off) vs improved (gating on) comparison
   - Prerecorded video runner (`eval.runner`) with optional reference CSV
   - JSON + Markdown reports
2. **Docs:** architecture, limitations, attribution, MIT `LICENSE`
3. **Tests** for metric aggregation and synthetic comparison

## Run synthetic evaluation

```powershell
cd C:\Project\CARDIA\rPPG-SDK
.\venv\Scripts\Activate.ps1
python -m eval --synthetic --bpm 72 --duration 8 --out eval/reports
```

Reports: `eval/reports/synthetic_compare.json` and `.md`.

## Run recorded video (optional)

Place videos under `data/eval/` (gitignored). Optional reference CSV columns: `timestamp_s,bpm`.

```powershell
python -m eval --video data/eval/my_clip.mp4 --reference data/eval/my_clip_ref.csv
```

Without `--reference`, the report includes quality/performance metrics only (no invented MAE).

## Report fields

- duration, face-track fraction, quality fractions
- valid-estimate coverage, rejection rate + reason counts
- processing FPS, mean latency
- HR MAE / RMSE / bias **only** when reference pairs exist

## Dataset policy

- Development threshold tuning and final evaluation should use **separate** recordings when available
- Synthetic fixture is labeled `split: evaluation` for CI reproducibility, with explicit limitation text that it is not clinical data

## Definition of done mapping

| Requirement | Status |
|-------------|--------|
| Quality gating prevents bad accepts | Prior milestones + eval reject metrics |
| Web dashboard streams real results | Milestone E |
| Charts from measured data | Milestone E |
| Tests pass | pytest suite |
| Recorded/synthetic reproducible reports | `python -m eval` |
| No false accuracy claims | MAE null without reference |
| Install/usage/limitations/attribution | README + docs/* + LICENSE |
