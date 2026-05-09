from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.db import SessionLocal, get_db
from app.models.user import User
from app.services.logging_service import system_log_service


router = APIRouter(tags=["ws"])


def _is_authenticated_websocket(websocket: WebSocket) -> bool:
    user_id = websocket.session.get("user_id")
    if not user_id:
        return False

    get_db_override = websocket.app.dependency_overrides.get(get_db)
    if get_db_override is not None:
        db_generator = get_db_override()
        db = next(db_generator)
        try:
            user = db.get(User, user_id)
            return bool(user and user.is_active)
        finally:
            db.close()

    with SessionLocal() as db:
        user = db.get(User, user_id)
        return bool(user and user.is_active)


@router.websocket("/ws/runtime")
async def runtime_ws(websocket: WebSocket) -> None:
    if not _is_authenticated_websocket(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    system_log_service.subscribe(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(system_log_service.flush_pending(), timeout=0.5)
                await asyncio.wait_for(websocket.receive_text(), timeout=2)
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        raise
    finally:
        system_log_service.unsubscribe(websocket)
