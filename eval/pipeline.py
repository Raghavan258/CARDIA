"""Offline evaluation pipeline mirroring RPPGSDK HR + quality gating.

Face detection / ROI extraction are injected so synthetic and unit tests do not
require MediaPipe. Real videos should use ``eval.runner.evaluate_video``.
"""

from __future__ import annotations

import time
from typing import Iterator, Optional

import numpy as np

from eval.metrics import FrameRecord
from eval.synthetic import SyntheticSample
from sdk.config import QualityConfig
from sdk.heart_rate import HeartRate
from sdk.measurement_state import REACQUIRE_REASONS, MeasurementState
from sdk.rppg_algorithm import RPPGAlgorithm
from sdk.signal_extractor import SignalExtractor
from sdk.signal_quality import SignalQualityAssessor


class OfflineEvalPipeline:
    """Process injected landmarks + RGB means with optional quality gating."""

    MIN_FRAMES = 64

    def __init__(
        self,
        *,
        algorithm: str = "pos",
        enable_quality_gating: bool = True,
        quality_config: Optional[QualityConfig] = None,
        fps_hint: float = 30.0,
    ):
        self.algorithm = algorithm
        self.enable_quality_gating = enable_quality_gating
        self.fps_hint = fps_hint
        self.signal_extractor = SignalExtractor(buffer_size=256)
        self.rppg_algorithm = RPPGAlgorithm(algorithm=algorithm, window_size=32)
        self.heart_rate = HeartRate(smooth_window=7)
        self.quality_assessor = SignalQualityAssessor(quality_config)
        self.state = MeasurementState.INITIALIZING
        self.last_accepted_bpm: Optional[float] = None

    def reset(self) -> None:
        self.signal_extractor.reset()
        self.heart_rate.reset()
        self.quality_assessor.reset()
        self.state = MeasurementState.INITIALIZING
        self.last_accepted_bpm = None

    def process_sample(self, sample: SyntheticSample) -> FrameRecord:
        t0 = time.perf_counter()
        landmarks = sample.landmarks
        rgb_mean = sample.rgb_mean
        face_ok = landmarks is not None and rgb_mean is not None
        pulse = None
        candidate = None

        if face_ok and rgb_mean is not None:
            self.signal_extractor.update(rgb_mean, timestamp_s=sample.timestamp_s)

        initializing = self.signal_extractor.length < self.MIN_FRAMES
        effective_fps = self._effective_fps()

        if face_ok and not initializing:
            signal = self.signal_extractor.get_signal()
            pulse = self.rppg_algorithm.process(signal, effective_fps)
            candidate = self.heart_rate.compute(pulse, effective_fps)

        quality = self.quality_assessor.assess_frame(
            frame_bgr=sample.frame_bgr,
            landmarks=landmarks,
            rgb_mean=rgb_mean,
            timestamp_s=sample.timestamp_s,
            pulse=pulse,
            timestamps_s=self.signal_extractor.get_timestamps(),
            buffer_frames=self.signal_extractor.length,
            fps_fallback=effective_fps,
            candidate_hr=candidate,
            initializing=initializing or not face_ok,
        )

        # Reacquisition (buffer clear) is part of the improved gated pipeline.
        if (
            self.enable_quality_gating
            and set(quality.rejection_reasons) & REACQUIRE_REASONS
            and self.signal_extractor.length
        ):
            self.signal_extractor.reset()
            self.heart_rate.reset()
            self.quality_assessor.reset()
            self.state = MeasurementState.REACQUIRING
            candidate = None

        accept = (
            (not self.enable_quality_gating) or quality.allow_new_hr_estimate
        ) and candidate is not None
        bpm = candidate if accept else None
        if accept and candidate is not None:
            self.last_accepted_bpm = candidate
            self.quality_assessor.note_accepted_hr(candidate)
            self.state = MeasurementState.MEASURING
        elif initializing:
            self.state = MeasurementState.INITIALIZING
        else:
            self.state = MeasurementState.LOW_QUALITY

        latency = (time.perf_counter() - t0) * 1000.0
        return FrameRecord(
            timestamp_s=sample.timestamp_s,
            face_ok=bool(face_ok),
            quality_category=quality.category.value,
            rejection_reasons=list(quality.rejection_reasons),
            bpm_accepted=bool(accept),
            bpm=bpm,
            bpm_raw=candidate,
            reference_bpm=sample.reference_bpm,
            latency_ms=latency,
            state=self.state.value,
        )

    def run(self, samples: Iterator[SyntheticSample]) -> list[FrameRecord]:
        return [self.process_sample(s) for s in samples]

    def _effective_fps(self) -> float:
        ts = self.signal_extractor.get_timestamps()
        if ts is not None and len(ts) >= 2:
            dts = np.diff(ts)
            dts = dts[dts > 1e-6]
            if len(dts):
                return float(1.0 / np.median(dts))
        return float(self.fps_hint)
