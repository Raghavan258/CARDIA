"""Compare ungated baseline vs quality-gated pipeline on the same inputs."""

from __future__ import annotations

import time
from typing import Any

from eval.metrics import EvalReport, summarize
from eval.pipeline import OfflineEvalPipeline
from eval.synthetic import iter_synthetic_session


def compare_synthetic(
    *,
    reference_bpm: float = 72.0,
    duration_s: float = 8.0,
    algorithm: str = "pos",
    motion_at_s: float | None = 5.0,
) -> dict[str, Any]:
    """Run identical synthetic samples through baseline and gated pipelines."""
    samples = list(
        iter_synthetic_session(
            reference_bpm=reference_bpm,
            duration_s=duration_s,
            motion_at_s=motion_at_s,
        )
    )

    def _run(gating: bool) -> EvalReport:
        pipe = OfflineEvalPipeline(
            algorithm=algorithm,
            enable_quality_gating=gating,
            fps_hint=30.0,
        )
        t0 = time.perf_counter()
        records = pipe.run(iter(samples))
        wall = time.perf_counter() - t0
        return summarize(
            records,
            name=f"synthetic_{int(reference_bpm)}bpm",
            mode="synthetic",
            algorithm=algorithm,
            gating_enabled=gating,
            wall_time_s=wall,
        )

    baseline = _run(False)
    gated = _run(True)
    return {
        "dataset": {
            "type": "synthetic",
            "reference_bpm": reference_bpm,
            "duration_s": duration_s,
            "motion_at_s": motion_at_s,
            "split": "evaluation",
            "limitation": (
                "Synthetic RGB/landmark sequence — not a clinical dataset. "
                "Do not treat MAE on this fixture as real-world accuracy."
            ),
        },
        "baseline_ungated": baseline.to_dict(),
        "improved_gated": gated.to_dict(),
        "delta": {
            "valid_estimate_coverage": (
                gated.valid_estimate_coverage - baseline.valid_estimate_coverage
            ),
            "rejection_rate": gated.rejection_rate - baseline.rejection_rate,
            "processing_fps": gated.processing_fps - baseline.processing_fps,
            "hr_mae": _sub(gated.hr_mae, baseline.hr_mae),
            "hr_rmse": _sub(gated.hr_rmse, baseline.hr_rmse),
        },
    }


def _sub(a, b):
    if a is None or b is None:
        return None
    return float(a) - float(b)
