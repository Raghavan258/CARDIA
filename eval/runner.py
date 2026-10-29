"""Evaluate prerecorded videos through the real RPPGSDK (MediaPipe required)."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Optional

import cv2

from eval.metrics import FrameRecord, summarize
from sdk.rppg_sdk import RPPGSDK


def load_reference_csv(path: Path) -> list[tuple[float, float]]:
    """Load synchronized reference as rows of timestamp_s,bpm."""
    rows: list[tuple[float, float]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((float(row["timestamp_s"]), float(row["bpm"])))
    return rows


def _nearest_ref(refs: list[tuple[float, float]], t: float, tol_s: float = 0.5) -> Optional[float]:
    if not refs:
        return None
    best_t, best_bpm = min(refs, key=lambda r: abs(r[0] - t))
    return best_bpm if abs(best_t - t) <= tol_s else None


def evaluate_video(
    video_path: Path,
    *,
    algorithm: str = "pos",
    enable_quality_gating: bool = True,
    reference_csv: Optional[Path] = None,
    max_frames: Optional[int] = None,
) -> tuple[list[FrameRecord], float]:
    """Process a video file frame-by-frame. Returns (records, wall_time_s)."""
    refs = load_reference_csv(reference_csv) if reference_csv else []
    sdk = RPPGSDK(
        open_camera=False,
        algorithm=algorithm,
        enable_quality_gating=enable_quality_gating,
        include_diagnostics=False,
    )
    sdk.start()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        sdk.release()
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    records: list[FrameRecord] = []
    t0 = time.perf_counter()
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            ts = idx / fps
            _frame, vitals = sdk.process_frame(frame, timestamp_s=ts)
            q = vitals.get("quality") or {}
            records.append(
                FrameRecord(
                    timestamp_s=ts,
                    face_ok=q.get("face_status") == "ok",
                    quality_category=q.get("category", "poor"),
                    rejection_reasons=list(q.get("rejection_reasons") or []),
                    bpm_accepted=bool(vitals.get("bpm_accepted")),
                    bpm=vitals.get("bpm"),
                    bpm_raw=vitals.get("bpm_raw"),
                    reference_bpm=_nearest_ref(refs, ts),
                    state=vitals.get("state"),
                )
            )
            idx += 1
            if max_frames is not None and idx >= max_frames:
                break
    finally:
        cap.release()
        sdk.release()
    return records, time.perf_counter() - t0


def report_for_video(
    video_path: Path,
    *,
    algorithm: str = "pos",
    enable_quality_gating: bool = True,
    reference_csv: Optional[Path] = None,
    max_frames: Optional[int] = None,
):
    records, wall = evaluate_video(
        video_path,
        algorithm=algorithm,
        enable_quality_gating=enable_quality_gating,
        reference_csv=reference_csv,
        max_frames=max_frames,
    )
    return summarize(
        records,
        name=video_path.name,
        mode="recorded_video",
        algorithm=algorithm,
        gating_enabled=enable_quality_gating,
        wall_time_s=wall,
    )
