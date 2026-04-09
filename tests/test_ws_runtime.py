from app.services.logging_service import system_log_service


def test_runtime_ws_sends_initial_snapshot(client):
    with client.websocket_connect("/ws/runtime") as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "snapshot"
    assert "udp" in payload
    assert isinstance(payload["udp"], dict)


def test_runtime_ws_unsubscribes_on_disconnect(client):
    before = len(system_log_service._subscribers)

    with client.websocket_connect("/ws/runtime") as websocket:
        _ = websocket.receive_json()
        during = len(system_log_service._subscribers)
        assert during == before + 1

    after = len(system_log_service._subscribers)
    assert after == before
