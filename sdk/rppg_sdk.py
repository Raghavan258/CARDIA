"""Main rPPG SDK with quality gating and explicit measurement states."""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from collections import deque

from sdk.camera import Camera
from sdk.config import QualityConfig
from sdk.diagnostics import build_diagnostics
from sdk.face_detector import FaceDetector
from sdk.heart_rate import HeartRate
from sdk.logging_utils import get_logger, log_estimate
from sdk.measurement_state import REACQUIRE_REASONS, MeasurementState
from sdk.quality_types import QualityResult
from sdk.roi_extractor import ROIExtractor
from sdk.rppg_algorithm import RPPGAlgorithm
from sdk.signal_extractor import SignalExtractor
from sdk.signal_quality import SignalQualityAssessor
from sdk.vitals import BloodPressureEstimator, RespirationEstimator, SpO2Estimator


def _empty_vitals() -> dict[str, Any]:
    return {
        "bpm": None,
        "spo2": None,
        "bp_sys": None,
        "bp_dia": None,
        "resp_rate": None,
        "bpm_raw": None,
        "bpm_accepted": False,
        "last_accepted_bpm": None,
        "last_accepted_bpm_age_s": None,
        "state": MeasurementState.IDLE.value,
        "algorithm": "pos",
        "effective_fps": None,
        "quality": QualityResult().to_dict(),
        "diagnostics": None,
        "session_elapsed_s": None,
        "experimental": {
            "spo2": True,
            "bp_sys": True,
            "bp_dia": True,
            "resp_rate": True,
        },
    }


class RPPGSDK:
    """Main rPPG SDK orchestrating the full heart-rate estimation pipeline."""

    MIN_FRAMES = 64
    MIN_FRAMES_RESP = 128

    def __init__(
        self,
        source=0,
        buffer_size=256,
        window_size=32,
        quality_config: Optional[QualityConfig] = None,
        enable_quality_gating: bool = True,
        algorithm: str = "pos",
        open_camera: bool = True,
        include_diagnostics: bool = True,
    ):
        """Initialize pipeline modules.

        Args:
            source: Camera index or video path (ignored if ``open_camera=False``).
            buffer_size: RGB ring-buffer length.
            window_size: POS/CHROM window length in frames.
            quality_config: Optional quality thresholds.
            enable_quality_gating: Block new accepted HR on hard rejects.
            algorithm: ``"pos"`` (default) or ``"chrom"``.
            open_camera: Set False for frame-injection / unit tests.
            include_diagnostics: Attach RGB/pulse/spectrum traces for dashboards.
        """
        self.source = source
        self.camera: Optional[Camera] = Camera(source) if open_camera else None
        self.fps = self.camera.fps if self.camera else 30.0
        self.face_detector = FaceDetector()
        self.roi_extractor = ROIExtractor()
        self.signal_extractor = SignalExtractor(buffer_size=buffer_size)
        self.rppg_algorithm = RPPGAlgorithm(algorithm=algorithm, window_size=window_size)
        self.heart_rate = HeartRate(smooth_window=7)
        self.spo2_estimator = SpO2Estimator()
        self.resp_estimator = RespirationEstimator()
        self.bp_estimator = BloodPressureEstimator()
        self.quality_assessor = SignalQualityAssessor(quality_config)
        self.enable_quality_gating = enable_quality_gating
        self.include_diagnostics = include_diagnostics
        self._no_face_count = 0
        self.last_landmarks = None
        self.last_quality: Optional[QualityResult] = None
        self.last_accepted_bpm: Optional[float] = None
        self._last_accepted_ts: Optional[float] = None
        self._start_mono = time.monotonic()
        self.state = MeasurementState.IDLE
        self._logger = get_logger("cardia.sdk")
        self._session_active = False
        self._last_pulse = None
        self._last_frame_shape: Optional[tuple[int, int]] = None
        self._accepted_hr_log: deque = deque(maxlen=120)
        self._motion_log: deque = deque(maxlen=120)
        self._session_start_mono: Optional[float] = None

    def start(self) -> None:
        """Mark the monitoring session as active (initializing)."""
        if self.state == MeasurementState.STOPPED:
            self._start_mono = time.monotonic()
        self._session_active = True
        self._session_start_mono = time.monotonic()
        self.state = MeasurementState.INITIALIZING
        self._logger.info('{"event":"session_start","state":"initializing"}')

    def stop(self) -> None:
        """Stop accepting frames; keep resources until ``release``."""
        self._session_active = False
        self.state = MeasurementState.STOPPED
        self._logger.info('{"event":"session_stop","state":"stopped"}')

    def run(self):
        """Read one camera frame and process it."""
        if self.camera is None:
            raise RuntimeError("No camera opened; use process_frame() instead.")
        if not self._session_active:
            self.start()
        frame = self.camera.read()
        if frame is None:
            self.state = MeasurementState.ERROR
            vitals = _empty_vitals()
            vitals["state"] = self.state.value
            return None, vitals
        return self.process_frame(frame)

    def process_frame(self, frame: np.ndarray, timestamp_s: Optional[float] = None):
        """Process an externally supplied BGR frame (tests / web backend)."""
        if not self._session_active and self.state != MeasurementState.STOPPED:
            self.start()
        if self.state == MeasurementState.STOPPED:
            vitals = _empty_vitals()
            vitals["state"] = self.state.value
            return frame, vitals

        vitals = _empty_vitals()
        vitals["algorithm"] = self.rppg_algorithm.algorithm
        now = time.monotonic()
        ts = timestamp_s if timestamp_s is not None else (now - self._start_mono)

        self._last_frame_shape = (frame.shape[0], frame.shape[1])
        landmarks = self.face_detector.detect(frame)
        self.last_landmarks = landmarks
        rgb_mean = None
        pulse = None
        candidate_hr = None
        effective_fps = self._effective_fps()

        if landmarks is None:
            return self._handle_no_face(frame, vitals, ts, now, effective_fps)

        self._no_face_count = 0
        rgb_mean = self.roi_extractor.extract(frame, landmarks)
        if rgb_mean is not None:
            self.signal_extractor.update(rgb_mean, timestamp_s=ts)

        effective_fps = self._effective_fps()
        vitals["effective_fps"] = effective_fps
        initializing = self.signal_extractor.length < self.MIN_FRAMES

        if not initializing and rgb_mean is not None:
            signal = self.signal_extractor.get_signal()
            pulse = self.rppg_algorithm.process(signal, effective_fps)
            self._last_pulse = pulse
            # Quality gates before treating spectral HR as publishable.
            candidate_hr = self.heart_rate.compute(pulse, effective_fps)
            self._fill_experimental_vitals(vitals, signal, pulse, candidate_hr, effective_fps)

        timestamps = self.signal_extractor.get_timestamps()
        quality = self.quality_assessor.assess_frame(
            frame_bgr=frame,
            landmarks=landmarks,
            rgb_mean=rgb_mean,
            timestamp_s=ts,
            pulse=pulse,
            timestamps_s=timestamps,
            buffer_frames=self.signal_extractor.length,
            fps_fallback=effective_fps,
            candidate_hr=candidate_hr,
            initializing=initializing,
        )
        if quality.motion_score is not None:
            self._motion_log.append(
                {"t": ts, "score": float(quality.motion_score)}
            )

        if self._should_reacquire(quality):
            self._enter_reacquisition("quality_trigger")
            self._last_pulse = None
            quality = self.quality_assessor.assess_frame(
                frame_bgr=frame,
                landmarks=landmarks,
                rgb_mean=rgb_mean,
                timestamp_s=ts,
                pulse=None,
                timestamps_s=None,
                buffer_frames=0,
                fps_fallback=effective_fps,
                candidate_hr=None,
                initializing=True,
            )
            candidate_hr = None
            vitals["bpm_raw"] = None

        self._update_state(quality, initializing)
        self._apply_hr_acceptance(vitals, quality, candidate_hr, now, ts, effective_fps)
        return frame, self._finalize_vitals(vitals, quality, now)

    def _handle_no_face(self, frame, vitals, ts, now, effective_fps):
        self._no_face_count += 1
        max_lost = self.quality_assessor.config.face.max_no_face_seconds
        if self._no_face_count > max(1, int(effective_fps * max_lost)):
            self._enter_reacquisition("face_lost")
        quality = self.quality_assessor.assess_frame(
            frame_bgr=frame,
            landmarks=None,
            rgb_mean=None,
            timestamp_s=ts,
            buffer_frames=self.signal_extractor.length,
            fps_fallback=effective_fps,
            initializing=True,
        )
        self._update_state(quality, initializing=True)
        vitals["bpm"] = None
        vitals["bpm_accepted"] = False
        return frame, self._finalize_vitals(vitals, quality, now)

    def _fill_experimental_vitals(self, vitals, signal, pulse, candidate_hr, fps):
        spo2 = self.spo2_estimator.compute(signal, fps)
        bp_sys, bp_dia = self.bp_estimator.compute(pulse, fps, candidate_hr)
        resp_rate = None
        if self.signal_extractor.length >= self.MIN_FRAMES_RESP:
            resp_rate = self.resp_estimator.compute(pulse, fps)
        vitals.update(
            {
                "bpm_raw": candidate_hr,
                "spo2": spo2,
                "bp_sys": bp_sys,
                "bp_dia": bp_dia,
                "resp_rate": resp_rate,
            }
        )

    def _should_reacquire(self, quality: QualityResult) -> bool:
        reasons = set(quality.rejection_reasons)
        return bool(reasons & REACQUIRE_REASONS) and self.signal_extractor.length > 0

    def _enter_reacquisition(self, reason: str) -> None:
        self._reset_estimators(keep_quality_motion=False)
        self.state = MeasurementState.REACQUIRING
        self._logger.info(
            '{"event":"reacquire","reason":"%s","state":"reacquiring"}' % reason
        )

    def _update_state(self, quality: QualityResult, initializing: bool) -> None:
        if self.state == MeasurementState.STOPPED:
            return
        if initializing or self.state == MeasurementState.REACQUIRING:
            if initializing:
                self.state = (
                    MeasurementState.REACQUIRING
                    if self.state == MeasurementState.REACQUIRING
                    else MeasurementState.INITIALIZING
                )
            elif quality.allow_new_hr_estimate:
                self.state = MeasurementState.MEASURING
            else:
                self.state = MeasurementState.LOW_QUALITY
            return
        if quality.allow_new_hr_estimate:
            self.state = MeasurementState.MEASURING
        else:
            self.state = MeasurementState.LOW_QUALITY

    def _apply_hr_acceptance(
        self,
        vitals: dict[str, Any],
        quality: QualityResult,
        candidate_hr: Optional[float],
        now: float,
        ts: float,
        effective_fps: float,
    ) -> None:
        # Never treat a quality-failed spectral peak as an accepted reading.
        accept = (
            (not self.enable_quality_gating) or quality.allow_new_hr_estimate
        ) and candidate_hr is not None

        vitals["bpm_raw"] = candidate_hr
        if accept:
            vitals["bpm"] = candidate_hr
            vitals["bpm_accepted"] = True
            self.last_accepted_bpm = candidate_hr
            self._last_accepted_ts = now
            self.quality_assessor.note_accepted_hr(candidate_hr)
            self._accepted_hr_log.append({"t": ts, "bpm": float(candidate_hr)})
        else:
            # Stale last_accepted is exposed separately — not as fresh bpm.
            vitals["bpm"] = None
            vitals["bpm_accepted"] = False

        log_estimate(
            self._logger,
            state=self.state.value,
            algorithm=self.rppg_algorithm.algorithm,
            bpm_raw=candidate_hr,
            bpm_accepted=bool(vitals["bpm_accepted"]),
            effective_fps=effective_fps,
            quality_category=quality.category.value,
            rejection_reasons=list(quality.rejection_reasons),
            buffer_frames=self.signal_extractor.length,
            timestamp_s=ts,
        )

    def _effective_fps(self) -> float:
        ts = self.signal_extractor.get_timestamps()
        if ts is not None and len(ts) >= 2:
            dts = np.diff(ts)
            dts = dts[dts > 1e-6]
            if len(dts):
                return float(1.0 / np.median(dts))
        return float(self.fps if self.fps and self.fps > 0 else 30.0)

    def _finalize_vitals(
        self,
        vitals: dict[str, Any],
        quality: QualityResult,
        now: float,
    ) -> dict[str, Any]:
        self.last_quality = quality
        vitals["quality"] = quality.to_dict()
        vitals["state"] = self.state.value
        vitals["algorithm"] = self.rppg_algorithm.algorithm
        vitals["last_accepted_bpm"] = self.last_accepted_bpm
        if self._last_accepted_ts is not None:
            vitals["last_accepted_bpm_age_s"] = now - self._last_accepted_ts
        else:
            vitals["last_accepted_bpm_age_s"] = None
        if vitals.get("effective_fps") is None:
            vitals["effective_fps"] = self._effective_fps()
        if self._session_start_mono is not None:
            vitals["session_elapsed_s"] = now - self._session_start_mono
        if self.include_diagnostics:
            vitals["diagnostics"] = build_diagnostics(
                rgb_signal=self.signal_extractor.get_signal(),
                pulse=self._last_pulse,
                timestamps_s=self.signal_extractor.get_timestamps(),
                effective_fps=float(vitals["effective_fps"] or 30.0),
                hr_history=[h["bpm"] for h in self._accepted_hr_log],
                landmarks=self.last_landmarks,
                frame_shape=self._last_frame_shape,
            )
            vitals["diagnostics"]["motion_history"] = list(self._motion_log)
            vitals["diagnostics"]["hr_series"] = list(self._accepted_hr_log)
        return vitals

    def _reset_estimators(self, keep_quality_motion: bool = False) -> None:
        self.signal_extractor.reset()
        self.heart_rate.reset()
        self.spo2_estimator.reset()
        self.resp_estimator.reset()
        self.bp_estimator.reset()
        if keep_quality_motion:
            self.quality_assessor.pulse.reset()
        else:
            self.quality_assessor.reset()

    def release(self):
        """Release all resources."""
        self.stop()
        if self.camera is not None:
            self.camera.release()
        self.face_detector.close()
        self.state = MeasurementState.STOPPED
