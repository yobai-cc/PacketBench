import pytest
from sqlalchemy.orm import Session

from anyio import WouldBlock

from app.auth.security import hash_password
from app.models.user import User
from app.services.logging_service import system_log_service


def login_for_ws(client, db_engine) -> None:
    with Session(db_engine) as db:
        db.add(User(username="ws-admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()
    response = client.post("/login", data={"username": "ws-admin", "password": "secret123"}, follow_redirects=False)
    assert response.status_code == 303


def test_runtime_ws_does_not_send_snapshot_without_events(client, db_engine):
    login_for_ws(client, db_engine)
    system_log_service._pending_events.clear()
    with client.websocket_connect("/ws/runtime") as websocket:
        with pytest.raises(WouldBlock):
            websocket._send_rx.receive_nowait()



def test_runtime_ws_unsubscribes_on_disconnect(client, db_engine):
    login_for_ws(client, db_engine)
    before = len(system_log_service._subscribers)

    with client.websocket_connect("/ws/runtime") as websocket:
        during = len(system_log_service._subscribers)
        assert during == before + 1

    after = len(system_log_service._subscribers)
    assert after == before
