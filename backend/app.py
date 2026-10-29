"""FastAPI application: health, config, sessions, and WebSocket streaming."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.adapters import decode_jpeg_base64
from backend.schemas import (
    FRAME_PROTOCOL,
    HealthResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionStopResponse,
)
from backend.sessions import SessionManager
from backend.settings import SETTINGS
from sdk.config import QualityConfig

logger = logging.getLogger("cardia.backend")


def create_app(manager: Optional[SessionManager] = None) -> FastAPI:
    session_manager = manager or SessionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.manager = session_manager
        logging.basicConfig(level=logging.INFO)
        yield
        await session_manager.shutdown()

    app = FastAPI(
        title="CARDIA rPPG API",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(SETTINGS.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="ok", version=__version__)

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        qc = QualityConfig()
        return {
            "backend": SETTINGS.to_public_dict(),
            "quality": {
                "motion": qc.motion.__dict__,
                "lighting": qc.lighting.__dict__,
                "face": qc.face.__dict__,
                "pulse": qc.pulse.__dict__,
                "fair_score_min": qc.fair_score_min,
                "good_score_min": qc.good_score_min,
            },
            "frame_protocol": FRAME_PROTOCOL,
            "disclaimer": (
                "Heart rate is the primary supported output. "
                "SpO2, blood pressure, and respiration are experimental estimates "
                "and are not medical-device readings."
            ),
        }

    @app.post("/api/sessions", response_model=SessionCreateResponse)
    async def create_session(body: SessionCreateRequest):
        try:
            session = await session_manager.create_session(
                algorithm=body.algorithm,
                input_mode=body.input_mode,
                video_path=body.video_path,
                max_width=body.max_width,
                target_fps=body.target_fps,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("create_session failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return SessionCreateResponse(
            session_id=session.session_id,
            input_mode=session.input_mode,
            algorithm=session.algorithm,
            ws_url=f"/ws/sessions/{session.session_id}",
            state=session.state,
            frame_protocol=FRAME_PROTOCOL,
        )

    @app.post("/api/sessions/{session_id}/stop", response_model=SessionStopResponse)
    async def stop_session(session_id: str):
        ok = await session_manager.stop_session(session_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionStopResponse(session_id=session_id, state="stopped", stopped=True)

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str):
        session = session_manager.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": session.session_id,
            "state": session.state,
            "input_mode": session.input_mode,
            "algorithm": session.algorithm,
            "stats": {
                "frames_received": session.stats.frames_received,
                "frames_dropped": session.stats.frames_dropped,
                "frames_processed": session.stats.frames_processed,
                "last_latency_ms": session.stats.last_latency_ms,
            },
        }

    @app.websocket("/ws/sessions/{session_id}")
    async def session_ws(websocket: WebSocket, session_id: str):
        session = session_manager.get(session_id)
        if session is None:
            await websocket.close(code=4404)
            return
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "status",
                "state": session.state,
                "message": "connected",
                "input_mode": session.input_mode,
            }
        )

        async def sender():
            assert session.outbound is not None
            while not session.closed:
                msg = await session.outbound.get()
                await websocket.send_json(msg)

        send_task = None
        try:
            send_task = asyncio.create_task(sender())
            if session.input_mode == "live":
                await _live_receive_loop(websocket, session_manager, session)
            else:
                # Recorded mode: client may ping; server pushes vitals via sender.
                while not session.closed:
                    data = await websocket.receive_json()
                    if data.get("type") == "stop":
                        break
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            logger.info("websocket disconnect session=%s", session_id)
        except Exception as exc:
            logger.exception("websocket error")
            try:
                await websocket.send_json(
                    {"type": "error", "code": "WS_ERROR", "message": str(exc)}
                )
            except Exception:
                pass
        finally:
            if send_task is not None:
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
            try:
                await session_manager.stop_session(session_id)
            except Exception:
                logger.exception("session cleanup failed id=%s", session_id)

    return app


async def _live_receive_loop(websocket: WebSocket, manager: SessionManager, session) -> None:
    while not session.closed:
        data = await websocket.receive_json()
        msg_type = data.get("type")
        if msg_type == "stop":
            await websocket.send_json({"type": "status", "state": "stopped", "message": "client_stop"})
            break
        if msg_type == "ping":
            await websocket.send_json({"type": "pong"})
            continue
        if msg_type != "frame":
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_MESSAGE",
                    "message": f"Unsupported message type: {msg_type}",
                }
            )
            continue
        try:
            _validate_frame_message(data)
            decoded = decode_jpeg_base64(
                data_base64=data["data_base64"],
                timestamp_s=float(data["timestamp_s"]),
                max_width=session.max_width,
            )
            await manager.enqueue_frame(session, decoded)
        except Exception as exc:
            await websocket.send_json(
                {"type": "error", "code": "INVALID_FRAME", "message": str(exc)}
            )


def _validate_frame_message(data: dict) -> None:
    if "timestamp_s" not in data or "data_base64" not in data:
        raise ValueError("frame requires timestamp_s and data_base64")
    mime = data.get("mime", "image/jpeg")
    if mime not in ("image/jpeg", "image/jpg"):
        raise ValueError("Only image/jpeg frames are supported")
    if not isinstance(data["data_base64"], str) or not data["data_base64"]:
        raise ValueError("data_base64 must be a non-empty string")


app = create_app()
