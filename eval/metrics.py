"""Aggregate evaluation metrics from per-frame result records.

Accuracy metrics (MAE/RMSE) are computed only when synchronized reference
BPM values are present. Otherwise they remain null — never invented.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class FrameRecord:
    timestamp_s: float
    face_ok: bool
    quality_category: str
    rejection_reasons: list[str]
    bpm_accepted: bool
    bpm: Optional[float]
    bpm_raw: Optional[float]
    reference_bpm: Optional[float] = None
    latency_ms: Optional[float] = None
    state: Optional[str] = None


@dataclass
class EvalReport:
    name: str
    mode: str
    algorithm: str
    gating_enabled: bool
    duration_s: float
    frame_count: int
    processing_fps: float
    mean_latency_ms: Optional[float]
    face_track_fraction: float
    quality_fractions: dict[str, float]
    valid_estimate_coverage: float
    rejection_rate: float
    rejection_reason_counts: dict[str, int]
    hr_mae: Optional[float] = None
    hr_rmse: Optional[float] = None
    hr_bias: Optional[float] = None
    paired_reference_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize(
    records: list[FrameRecord],
    *,
    name: str,
    mode: str,
    algorithm: str,
    gating_enabled: bool,
    wall_time_s: float,
) -> EvalReport:
    n = len(records)
    duration = records[-1].timestamp_s - records[0].timestamp_s if n >= 2 else 0.0
    face_ok = sum(1 for r in records if r.face_ok)
    cats = Counter(r.quality_category for r in records)
    quality_fractions = {
        k: (cats.get(k, 0) / n if n else 0.0)
        for k in ("initializing", "good", "fair", "poor")
    }
    accepted = [r for r in records if r.bpm_accepted and r.bpm is not None]
    rejected = [r for r in records if r.rejection_reasons]
    reason_counts: Counter[str] = Counter()
    for r in records:
        reason_counts.update(r.rejection_reasons)

    latencies = [r.latency_ms for r in records if r.latency_ms is not None]
    mean_latency = float(sum(latencies) / len(latencies)) if latencies else None

    paired = [
        r for r in accepted
        if r.reference_bpm is not None and r.bpm is not None
    ]
    hr_mae = hr_rmse = hr_bias = None
    notes: list[str] = []
    if paired:
        errs = [float(r.bpm) - float(r.reference_bpm) for r in paired]
        hr_bias = float(sum(errs) / len(errs))
        hr_mae = float(sum(abs(e) for e in errs) / len(errs))
        hr_rmse = float((sum(e * e for e in errs) / len(errs)) ** 0.5)
    else:
        notes.append(
            "No synchronized reference BPM pairs available; "
            "HR MAE/RMSE/bias omitted (not estimated)."
        )

    proc_fps = (n / wall_time_s) if wall_time_s > 0 else 0.0
    return EvalReport(
        name=name,
        mode=mode,
        algorithm=algorithm,
        gating_enabled=gating_enabled,
        duration_s=float(duration),
        frame_count=n,
        processing_fps=float(proc_fps),
        mean_latency_ms=mean_latency,
        face_track_fraction=face_ok / n if n else 0.0,
        quality_fractions=quality_fractions,
        valid_estimate_coverage=len(accepted) / n if n else 0.0,
        rejection_rate=len(rejected) / n if n else 0.0,
        rejection_reason_counts=dict(reason_counts),
        hr_mae=hr_mae,
        hr_rmse=hr_rmse,
        hr_bias=hr_bias,
        paired_reference_count=len(paired),
        notes=notes,
    )
