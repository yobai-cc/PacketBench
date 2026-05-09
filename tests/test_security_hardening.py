from __future__ import annotations

import re
import time

import pytest
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User
from app.services.logging_service import system_log_service


def create_user(
    db_engine,
    username: str = "admin",
    password: str = "secret123",
    role: str = "admin",
    is_active: bool = True,
) -> int:
    with Session(db_engine) as db:
        user = User(username=username, password_hash=hash_password(password), role=role, is_active=is_active)
        db.add(user)
        db.commit()
        return user.id


def login_as(client, username: str = "admin", password: str = "secret123") -> None:
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def csrf_token_from_session(client) -> str:
    response = client.get("/dashboard")
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, response.text
    return match.group(1)


def test_login_sets_csrf_token_for_authenticated_session(client, db_engine):
    create_user(db_engine)

    login_as(client)

    token = csrf_token_from_session(client)
    assert isinstance(token, str)
    assert len(token) >= 32


def test_state_changing_post_without_csrf_token_is_rejected(client, db_engine):
    create_user(db_engine)
    login_as(client)

    response = client.post("/udp-server/config", data={"bind_ip": "127.0.0.1", "bind_port": "9000"})

    assert response.status_code == 403
    assert "CSRF" in response.text


def test_state_changing_post_with_csrf_token_is_allowed(client, db_engine):
    create_user(db_engine)
    login_as(client)
    token = csrf_token_from_session(client)

    response = client.post(
        "/udp-server/config",
        data={
            "bind_ip": "127.0.0.1",
            "bind_port": "9000",
            "custom_reply_data": "",
            "reply_mode": "off",
            "csrf_token": token,
        },
    )

    assert response.status_code == 200
    assert "UDP 配置已更新" in response.text


def test_logout_requires_csrf_token(client, db_engine):
    create_user(db_engine)
    login_as(client)

    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 403


def test_runtime_ws_rejects_anonymous_connection(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/runtime"):
            pass

    assert exc_info.value.code == 1008


def test_runtime_ws_accepts_authenticated_connection(client, db_engine):
    create_user(db_engine)
    login_as(client)

    with client.websocket_connect("/ws/runtime") as websocket:
        assert websocket is not None


def test_runtime_ws_rejects_disabled_authenticated_user(client, db_engine):
    user_id = create_user(db_engine)
    login_as(client)
    with Session(db_engine) as db:
        user = db.get(User, user_id)
        user.is_active = False
        db.commit()

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/runtime"):
            pass

    assert exc_info.value.code == 1008


def test_system_log_broadcasts_runtime_event_to_authenticated_ws(client, db_engine):
    create_user(db_engine)
    login_as(client)
    system_log_service._pending_events.clear()

    with client.websocket_connect("/ws/runtime") as websocket:
        system_log_service.log_to_db("info", "service", "UDP server started by admin", "detail text")
        deadline = time.time() + 2
        event = None
        while time.time() < deadline:
            candidate = websocket.receive_json()
            if candidate["category"] == "service" and candidate["message"] == "UDP server started by admin":
                event = candidate
                break

    assert event == {
        "level": "INFO",
        "category": "service",
        "message": "UDP server started by admin",
        "detail": "detail text",
    }


def test_system_log_queues_events_until_runtime_ws_flushes_them(client, db_engine):
    create_user(db_engine)
    login_as(client)
    system_log_service._pending_events.clear()
    system_log_service.log_to_db("warning", "service", "queued event", "queued detail")

    with client.websocket_connect("/ws/runtime") as websocket:
        event = websocket.receive_json()

    assert event == {
        "level": "WARNING",
        "category": "service",
        "message": "queued event",
        "detail": "queued detail",
    }


def test_production_rejects_default_secret_key(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-this-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-password")

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_default_admin_password(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123456")

    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        Settings()
