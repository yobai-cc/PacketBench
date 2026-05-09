from __future__ import annotations

import asyncio
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.system_log import SystemLog


class SystemLogService:
    """Handles file logging, database logging, and in-memory event fanout."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("packetbench.app")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not self.logger.handlers:
            handler = RotatingFileHandler(self.settings.app_log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self._subscribers: set[Any] = set()
        self._pending_events: deque[dict[str, str]] = deque(maxlen=100)

    async def broadcast(self, event: dict[str, str]) -> None:
        subscribers = list(self._subscribers)
        if not subscribers:
            return
        results = await asyncio.gather(*(subscriber.send_json(event) for subscriber in subscribers), return_exceptions=True)
        for subscriber, result in zip(subscribers, results):
            if isinstance(result, Exception):
                self._subscribers.discard(subscriber)

    def subscribe(self, websocket: Any) -> None:
        self._subscribers.add(websocket)

    async def flush_pending(self) -> None:
        while self._pending_events:
            await self.broadcast(self._pending_events.popleft())

    def unsubscribe(self, websocket: Any) -> None:
        self._subscribers.discard(websocket)

    def _schedule_broadcast(self, event: dict[str, str]) -> None:
        if not self._subscribers:
            self._pending_events.append(event)
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._pending_events.append(event)
            return
        loop.create_task(self.broadcast(event))

    def log_to_db(self, level: str, category: str, message: str, detail: str = "", db: Session | None = None) -> None:
        normalized_level = level.upper()
        self.logger.log(getattr(logging, normalized_level, logging.INFO), "%s | %s", category, message)
        if db is not None:
            db.add(SystemLog(level=normalized_level, category=category, message=message, detail=detail))
            db.commit()
        self._schedule_broadcast({"level": normalized_level, "category": category, "message": message, "detail": detail})


system_log_service = SystemLogService()
