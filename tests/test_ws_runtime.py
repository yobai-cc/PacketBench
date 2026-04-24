import pytest

from anyio import WouldBlock

from app.services.logging_service import system_log_service


def test_runtime_ws_does_not_send_snapshot_without_events(client):
    with client.websocket_connect("/ws/runtime") as websocket:
        with pytest.raises(WouldBlock):
            websocket._send_rx.receive_nowait()



def test_runtime_ws_unsubscribes_on_disconnect(client):
    before = len(system_log_service._subscribers)

    with client.websocket_connect("/ws/runtime") as websocket:
        during = len(system_log_service._subscribers)
        assert during == before + 1

    after = len(system_log_service._subscribers)
    assert after == before
