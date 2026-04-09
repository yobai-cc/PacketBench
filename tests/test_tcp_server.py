import asyncio
import warnings

import pytest
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models.service_config import ServiceConfig
from app.models.user import User
from app.services.tcp_server import TCPServerConfig, TCPServerService
from app.services.runtime_manager import runtime_manager


def test_update_config_changes_snapshot_values() -> None:
    service = TCPServerService()
    service.update_config(TCPServerConfig(bind_ip="0.0.0.0", bind_port=9101, hex_mode=True))

    snapshot = service.snapshot()

    assert snapshot["bind_ip"] == "0.0.0.0"
    assert snapshot["bind_port"] == 9101
    assert snapshot["hex_mode"] is True
    assert snapshot["running"] is False
    assert snapshot["clients"] == []


def test_make_client_id_uses_ip_and_port() -> None:
    service = TCPServerService()

    assert service.make_client_id(("127.0.0.1", 6000)) == "127.0.0.1:6000"


@pytest.mark.anyio
async def test_disconnect_unknown_client_is_safe() -> None:
    service = TCPServerService()

    await service.disconnect_client("127.0.0.1:6000")

    assert service.snapshot()["clients"] == []


@pytest.mark.anyio
async def test_start_tracks_client_receives_payload_and_disconnects(monkeypatch: pytest.MonkeyPatch) -> None:
    packets: list[dict[str, object]] = []
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "app.services.tcp_server.packet_logger.log_packet",
        lambda **kwargs: packets.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.tcp_server.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    service = TCPServerService()
    service.update_config(TCPServerConfig(bind_ip="127.0.0.1", bind_port=0, hex_mode=False))

    await service.start()
    assert service.running is True

    sockname = service.server.sockets[0].getsockname()
    reader, writer = await asyncio.open_connection(sockname[0], sockname[1])

    for _ in range(20):
        if service.snapshot()["client_count"] == 1:
            break
        await asyncio.sleep(0.01)

    snapshot = service.snapshot()
    assert snapshot["client_count"] == 1
    client_id = snapshot["clients"][0]["client_id"]

    writer.write(b"hello tcp")
    await writer.drain()

    for _ in range(20):
        if service.rx_count == len(b"hello tcp"):
            break
        await asyncio.sleep(0.01)

    assert service.rx_count == len(b"hello tcp")
    assert packets[-1]["direction"] == "client -> server"
    assert packets[-1]["payload"] == b"hello tcp"

    send_task = asyncio.create_task(reader.readexactly(5))
    await service.send_manual(client_id, "reply")
    assert await send_task == b"reply"

    assert service.tx_count == len(b"reply")
    assert any("TCP client connected" in message for _, _, message, _ in logs)

    await service.disconnect_client(client_id)

    for _ in range(20):
        if service.snapshot()["client_count"] == 0:
            break
        await asyncio.sleep(0.01)

    assert service.snapshot()["client_count"] == 0
    writer.close()
    await writer.wait_closed()
    await service.stop()


def test_tcp_server_page_renders_runtime_snapshot_and_persists_config(tmp_path) -> None:
    from app.routers.pages import tcp_server_page, update_tcp_config

    db_path = tmp_path / "tcp-page.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        user = User(username="tcp-admin", password_hash="x", role="admin", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    request = Request({"type": "http", "method": "GET", "path": "/tcp-server", "headers": [], "query_string": b""})

    try:
        response = tcp_server_page(request, user)
        body = response.body.decode("utf-8")
        assert "TCP Server" in body
        assert "第二阶段实现" not in body

        with TestingSessionLocal() as db:
            post_response = update_tcp_config(request, bind_ip="127.0.0.1", bind_port=9102, hex_mode="on", user=user, db=db)
            post_body = post_response.body.decode("utf-8")
            assert "127.0.0.1" in post_body
            assert "9102" in post_body

        with Session(engine) as db:
            row = db.query(ServiceConfig).filter(ServiceConfig.name == "tcp_server").one()
            assert row.service_type == "tcp_server"
            assert row.bind_ip == "127.0.0.1"
            assert row.bind_port == 9102
            assert row.enabled is False
            assert row.config_json["hex_mode"] is True
    finally:
        runtime_manager.tcp_server.update_config(TCPServerConfig())


def test_tcp_server_page_hides_mutations_for_viewer() -> None:
    from app.routers.pages import tcp_server_page

    request = Request({"type": "http", "method": "GET", "path": "/tcp-server", "headers": [], "query_string": b""})
    viewer = User(username="viewer-user", password_hash="x", role="viewer", is_active=True)

    response = tcp_server_page(request, viewer)
    body = response.body.decode("utf-8")

    assert "Viewer 角色仅可查看 TCP 运行状态。" in body
    assert "/tcp-server/start" not in body
    assert "/tcp-server/stop" not in body
    assert "/tcp-server/send" not in body
    assert "/tcp-server/disconnect" not in body


def test_tcp_server_routes_do_not_emit_template_deprecation_warning(tmp_path) -> None:
    from app.routers.pages import tcp_server_page, update_tcp_config

    db_path = tmp_path / "tcp-template-warning.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    user = User(username="admin-user", password_hash="x", role="admin", is_active=True)
    request = Request({"type": "http", "method": "GET", "path": "/tcp-server", "headers": [], "query_string": b""})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = tcp_server_page(request, user)
        _ = response.body.decode("utf-8")
        with TestingSessionLocal() as db:
            response = update_tcp_config(request, bind_ip="127.0.0.1", bind_port=9103, hex_mode="on", user=user, db=db)
            _ = response.body.decode("utf-8")

    messages = [str(item.message) for item in caught]
    assert not any("The `name` is not the first parameter anymore" in message for message in messages)


@pytest.mark.anyio
async def test_tcp_send_and_disconnect_routes_update_persisted_snapshot(tmp_path) -> None:
    from app.routers.pages import disconnect_tcp_client, send_tcp_manual

    db_path = tmp_path / "tcp-routes.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/tcp-server/send", "headers": [], "query_string": b""})
    service = runtime_manager.tcp_server
    service.update_config(TCPServerConfig(bind_ip="127.0.0.1", bind_port=0, hex_mode=False))
    await service.start()
    sockname = service.server.sockets[0].getsockname()
    reader, writer = await asyncio.open_connection(sockname[0], sockname[1])

    for _ in range(20):
        if service.snapshot()["client_count"] == 1:
            break
        await asyncio.sleep(0.01)

    client_id = service.snapshot()["clients"][0]["client_id"]

    try:
        with TestingSessionLocal() as db:
            send_response = await send_tcp_manual(request, client_id=client_id, payload="pong", user=user, db=db)
            send_body = send_response.body.decode("utf-8")
            assert "TCP 手动发送已触发" in send_body

        assert await reader.readexactly(4) == b"pong"

        with TestingSessionLocal() as db:
            row = db.query(ServiceConfig).filter(ServiceConfig.name == "tcp_server").one()
            assert row.config_json["tx_count"] == 4

        with TestingSessionLocal() as db:
            disconnect_response = await disconnect_tcp_client(request, client_id=client_id, user=user, db=db)
            disconnect_body = disconnect_response.body.decode("utf-8")
            assert "TCP 客户端已断开" in disconnect_body

        with TestingSessionLocal() as db:
            row = db.query(ServiceConfig).filter(ServiceConfig.name == "tcp_server").one()
            assert row.enabled is True
            assert row.config_json["tx_count"] == 4
    finally:
        writer.close()
        await writer.wait_closed()
        await service.stop()
        runtime_manager.tcp_server.update_config(TCPServerConfig())


@pytest.mark.anyio
async def test_tcp_route_failures_render_error_and_write_system_log(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import disconnect_tcp_client, send_tcp_manual

    db_path = tmp_path / "tcp-route-failures.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/tcp-server/send", "headers": [], "query_string": b""})
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "app.routers.pages.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    async def boom_send(client_id: str, payload: str) -> None:
        raise RuntimeError("socket broken")

    async def boom_disconnect(client_id: str) -> None:
        raise RuntimeError("close failed")

    monkeypatch.setattr(runtime_manager.tcp_server, "send_manual", boom_send)
    monkeypatch.setattr(runtime_manager.tcp_server, "disconnect_client", boom_disconnect)

    try:
        runtime_manager.tcp_server.update_config(TCPServerConfig(bind_ip="127.0.0.1", bind_port=9100, hex_mode=False))

        with TestingSessionLocal() as db:
            send_response = await send_tcp_manual(request, client_id="127.0.0.1:9200", payload="pong", user=user, db=db)
            send_body = send_response.body.decode("utf-8")
            assert "alert error" in send_body
            assert "TCP 发送失败：socket broken" in send_body

        assert logs[-1] == (
            "error",
            "network",
            "Manual TCP payload send failed by operator-user to 127.0.0.1:9200",
            "socket broken",
        )

        with TestingSessionLocal() as db:
            disconnect_response = await disconnect_tcp_client(
                request, client_id="127.0.0.1:9200", user=user, db=db
            )
            disconnect_body = disconnect_response.body.decode("utf-8")
            assert "alert error" in disconnect_body
            assert "TCP 客户端断开失败：close failed" in disconnect_body

        assert logs[-1] == (
            "error",
            "service",
            "TCP client disconnect failed 127.0.0.1:9200 by operator-user",
            "close failed",
        )
    finally:
        runtime_manager.tcp_server.update_config(TCPServerConfig())


@pytest.mark.anyio
async def test_tcp_start_stop_route_failures_render_error_and_write_system_log(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers.pages import start_tcp_server, stop_tcp_server

    db_path = tmp_path / "tcp-start-stop-route-failures.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/tcp-server/start", "headers": [], "query_string": b""})
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "app.routers.pages.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    async def boom_start() -> None:
        raise RuntimeError("bind failed")

    async def boom_stop() -> None:
        raise RuntimeError("close failed")

    monkeypatch.setattr(runtime_manager.tcp_server, "start", boom_start)
    monkeypatch.setattr(runtime_manager.tcp_server, "stop", boom_stop)

    try:
        runtime_manager.tcp_server.update_config(TCPServerConfig(bind_ip="127.0.0.1", bind_port=9100, hex_mode=False))

        with TestingSessionLocal() as db:
            start_response = await start_tcp_server(request, user=user, db=db)
            start_body = start_response.body.decode("utf-8")
            assert "alert error" in start_body
            assert "TCP 服务启动失败：bind failed" in start_body

        assert logs[-1] == ("error", "service", "TCP server start failed by operator-user", "bind failed")

        with TestingSessionLocal() as db:
            stop_response = await stop_tcp_server(request, user=user, db=db)
            stop_body = stop_response.body.decode("utf-8")
            assert "alert error" in stop_body
            assert "TCP 服务停止失败：close failed" in stop_body

        assert logs[-1] == ("error", "service", "TCP server stop failed by operator-user", "close failed")
    finally:
        runtime_manager.tcp_server.update_config(TCPServerConfig())
