"""Session lifecycle, bounded frame queue, and CPU offload worker."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.adapters import DecodedFrame, iter_video_frames, resolve_video_path
from backend.settings import SETTINGS
from sdk.config import QualityConfig
from sdk.measurement_state import MeasurementState
from sdk.rppg_sdk import RPPGSDK

logger = logging.getLogger("cardia.backend.sessions")


@dataclass
class SessionStats:
    frames_received: int = 0
    frames_dropped: int = 0
    frames_processed: int = 0
    last_latency_ms: Optional[float] = None


@dataclass
class MonitoringSession:
    session_id: str
    algorithm: str
    input_mode: str
    max_width: int
    target_fps: float
    video_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    sdk: Optional[RPPGSDK] = None
    queue: Optional[asyncio.Queue] = None
    outbound: Optional[asyncio.Queue] = None
    stats: SessionStats = field(default_factory=SessionStats)
    worker_task: Optional[asyncio.Task] = None
    recorded_task: Optional[asyncio.Task] = None
    closed: bool = False
    loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def state(self) -> str:
        if self.sdk is None:
            return MeasurementState.IDLE.value
        return self.sdk.state.value


class SessionManager:
    """Create/stop sessions and process frames without blocking the event loop."""

    def __init__(
        self,
        settings=SETTINGS,
        sdk_factory=None,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        self.settings = settings
        self._sessions: dict[str, MonitoringSession] = {}
        self._lock = asyncio.Lock()
        self._sdk_factory = sdk_factory or self._default_sdk_factory
        self._executor = executor or ThreadPoolExecutor(
            max_workers=settings.worker_threads,
            thread_name_prefix="cardia-rppg",
        )

    @staticmethod
    def _default_sdk_factory(algorithm: str) -> RPPGSDK:
        return RPPGSDK(
            open_camera=False,
            algorithm=algorithm,
            enable_quality_gating=True,
            quality_config=QualityConfig(),
            include_diagnostics=True,
        )

    async def create_session(
        self,
        *,
        algorithm: str = "pos",
        input_mode: str = "live",
        video_path: Optional[str] = None,
        max_width: int = 640,
        target_fps: float = 15.0,
    ) -> MonitoringSession:
        if input_mode == "recorded":
            if not video_path:
                raise ValueError("video_path is required for recorded input_mode")
            resolve_video_path(video_path)

        session_id = uuid.uuid4().hex
        session = MonitoringSession(
            session_id=session_id,
            algorithm=algorithm,
            input_mode=input_mode,
            max_width=max_width,
            target_fps=target_fps,
            video_path=video_path,
            queue=asyncio.Queue(maxsize=self.settings.frame_queue_size),
            outbound=asyncio.Queue(maxsize=64),
            loop=asyncio.get_running_loop(),
        )
        session.sdk = self._sdk_factory(algorithm)
        session.sdk.start()

        async with self._lock:
            self._sessions[session_id] = session

        session.worker_task = asyncio.create_task(
            self._worker_loop(session), name=f"worker-{session_id[:8]}"
        )
        if input_mode == "recorded":
            session.recorded_task = asyncio.create_task(
                self._recorded_feeder(session), name=f"recorded-{session_id[:8]}"
            )
        logger.info("session_created id=%s mode=%s alg=%s", session_id, input_mode, algorithm)
        return session

    def get(self, session_id: str) -> Optional[MonitoringSession]:
        return self._sessions.get(session_id)

    async def stop_session(self, session_id: str) -> bool:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        await self._shutdown_session(session)
        return True

    async def _shutdown_session(self, session: MonitoringSession) -> None:
        session.closed = True
        if session.sdk is not None:
            try:
                session.sdk.stop()
            except Exception:
                logger.exception("sdk.stop failed")
            try:
                session.sdk.release()
            except Exception:
                logger.exception("sdk.release failed")
            session.sdk = None
        for task in (session.recorded_task, session.worker_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("session_stopped id=%s", session.session_id)

    async def enqueue_frame(self, session: MonitoringSession, frame: DecodedFrame) -> None:
        """Push a frame with backpressure: drop oldest if the queue is full."""
        if session.closed or session.queue is None:
            raise RuntimeError("Session is closed")
        session.stats.frames_received += 1
        q = session.queue
        if q.full():
            try:
                q.get_nowait()
                session.stats.frames_dropped += 1
            except asyncio.QueueEmpty:
                pass
        await q.put(frame)

    async def _worker_loop(self, session: MonitoringSession) -> None:
        assert session.queue is not None and session.outbound is not None
        try:
            while not session.closed:
                frame = await session.queue.get()
                t0 = time.perf_counter()
                loop = asyncio.get_running_loop()
                vitals = await loop.run_in_executor(
                    self._executor,
                    self._process_sync,
                    session,
                    frame.bgr,
                    frame.timestamp_s,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                session.stats.frames_processed += 1
                session.stats.last_latency_ms = latency_ms
                message = {
                    "type": "vitals",
                    "session_id": session.session_id,
                    "server_ts": time.time(),
                    "latency_ms": round(latency_ms, 2),
                    "stats": {
                        "frames_received": session.stats.frames_received,
                        "frames_dropped": session.stats.frames_dropped,
                        "frames_processed": session.stats.frames_processed,
                    },
                    "payload": vitals,
                }
                await self._emit(session, message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("worker failed session=%s", session.session_id)
            await self._emit(
                session,
                {"type": "error", "code": "WORKER_ERROR", "message": str(exc)},
            )

    @staticmethod
    def _process_sync(session: MonitoringSession, bgr: np.ndarray, timestamp_s: float):
        if session.sdk is None:
            return {"state": MeasurementState.STOPPED.value, "bpm": None}
        _frame, vitals = session.sdk.process_frame(bgr, timestamp_s=timestamp_s)
        return vitals

    async def _recorded_feeder(self, session: MonitoringSession) -> None:
        assert session.video_path is not None
        try:
            path = resolve_video_path(session.video_path)
            await self._emit(
                session,
                {
                    "type": "status",
                    "state": session.state,
                    "message": f"Playing recorded video {path.name}",
                },
            )
            interval = 1.0 / max(session.target_fps, 1.0)
            for decoded in iter_video_frames(path, max_width=session.max_width):
                if session.closed:
                    break
                await self.enqueue_frame(session, decoded)
                await asyncio.sleep(interval)
            await self._emit(
                session,
                {"type": "status", "state": session.state, "message": "recorded_complete"},
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("recorded feeder failed")
            await self._emit(
                session,
                {"type": "error", "code": "RECORDED_ERROR", "message": str(exc)},
            )

    async def _emit(self, session: MonitoringSession, message: dict[str, Any]) -> None:
        if session.outbound is None or session.closed:
            return
        if session.outbound.full():
            try:
                session.outbound.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await session.outbound.put(message)

    async def shutdown(self) -> None:
        ids = list(self._sessions.keys())
        for sid in ids:
            await self.stop_session(sid)
        self._executor.shutdown(wait=False, cancel_futures=True)
