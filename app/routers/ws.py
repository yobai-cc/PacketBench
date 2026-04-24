from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.logging_service import system_log_service


router = APIRouter(tags=["ws"])


@router.websocket("/ws/runtime")
async def runtime_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    system_log_service.subscribe(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=2)
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        raise
    finally:
        system_log_service.unsubscribe(websocket)
