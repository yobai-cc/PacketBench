import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

from app.auth.security import hash_password
from app.db import Base
from app.models.packet_log import PacketLog
from app.models.service_config import ServiceConfig
from app.models.system_log import SystemLog
from app.models.user import User
from app.services.runtime_manager import runtime_manager
from app.services.udp_server import UDPServerConfig


def login_as(client, username: str, password: str) -> None:
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.anyio
async def test_udp_route_failures_render_error_and_write_system_log(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import send_udp_manual, start_udp_server, stop_udp_server

    db_path = tmp_path / "udp-route-failures.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/udp-server/start", "headers": [], "query_string": b""})
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "app.routers.pages.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    async def boom_start() -> None:
        raise RuntimeError("bind failed")

    async def boom_stop() -> None:
        raise RuntimeError("close failed")

    async def boom_send(payload: str) -> None:
        raise RuntimeError("UDP server is not running")

    monkeypatch.setattr(runtime_manager.udp_server, "start", boom_start)
    monkeypatch.setattr(runtime_manager.udp_server, "stop", boom_stop)
    monkeypatch.setattr(runtime_manager.udp_server, "send_manual", boom_send)

    try:
        runtime_manager.udp_server.update_config(
            UDPServerConfig(
                bind_ip="127.0.0.1",
                bind_port=9000,
                custom_reply_data="",
                hex_mode=False,
            )
        )

        with testing_session_local() as db:
            start_response = await start_udp_server(request, user=user, db=db)
            start_body = start_response.body.decode("utf-8")
            assert "alert error" in start_body
            assert "UDP 服务启动失败：bind failed" in start_body

        assert logs[-1] == ("error", "service", "UDP server start failed by operator-user", "bind failed")

        with testing_session_local() as db:
            send_response = await send_udp_manual(request, payload="ping", user=user, db=db)
            send_body = send_response.body.decode("utf-8")
            assert "alert error" in send_body
            assert "UDP 手动发送失败：UDP server is not running" in send_body

        assert logs[-1] == (
            "error",
            "network",
            "Manual UDP payload send failed by operator-user",
            "UDP server is not running",
        )

        with testing_session_local() as db:
            stop_response = await stop_udp_server(request, user=user, db=db)
            stop_body = stop_response.body.decode("utf-8")
            assert "alert error" in stop_body
            assert "UDP 服务停止失败：close failed" in stop_body

        assert logs[-1] == ("error", "service", "UDP server stop failed by operator-user", "close failed")
    finally:
        runtime_manager.udp_server.running = False
        runtime_manager.udp_server.transport = None
        runtime_manager.udp_server.protocol = None
        runtime_manager.udp_server.last_client_addr = None
        runtime_manager.udp_server.update_config(UDPServerConfig())


def test_update_udp_config_accepts_bind_and_reply_fields_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import update_udp_config

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/udp-server/config", "headers": [], "query_string": b""})

    captured_payload: list[dict[str, object]] = []
    snapshots: list[dict[str, object]] = [
        {
            "running": False,
            "bind_ip": "127.0.0.1",
            "bind_port": 9000,
            "custom_reply_data": "reply",
            "hex_mode": True,
            "tx_count": 0,
            "rx_count": 0,
            "last_client_addr": None,
        }
    ]
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(runtime_manager, "apply_udp_config", lambda payload: captured_payload.append(payload) or UDPServerConfig(**payload))
    monkeypatch.setattr(runtime_manager, "udp_snapshot", lambda: snapshots[-1])
    monkeypatch.setattr("app.routers.pages._save_udp_config", lambda db, snapshot: None)
    monkeypatch.setattr(
        "app.routers.pages.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    response = update_udp_config(
        request,
        bind_ip="127.0.0.1",
        bind_port=9000,
        custom_reply_data="reply",
        reply_mode="fixed",
        hex_mode="on",
        user=user,
        db=None,
    )

    body = response.body.decode("utf-8")
    assert captured_payload == [
        {
            "bind_ip": "127.0.0.1",
            "bind_port": 9000,
            "custom_reply_data": "reply",
            "hex_mode": True,
        }
    ]
    assert "自动回复" in body
    assert "回复内容" in body
    assert "云端 IP" not in body
    assert "UDP 配置已更新" in body
    assert logs[-1] == ("info", "config", "UDP config updated by operator-user", "")


def test_update_udp_config_can_disable_reply_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import update_udp_config

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/udp-server/config", "headers": [], "query_string": b""})

    captured_payload: list[dict[str, object]] = []
    monkeypatch.setattr(runtime_manager, "apply_udp_config", lambda payload: captured_payload.append(payload) or UDPServerConfig(**payload))
    monkeypatch.setattr(
        runtime_manager,
        "udp_snapshot",
        lambda: {
            "running": False,
            "bind_ip": "127.0.0.1",
            "bind_port": 9000,
            "custom_reply_data": "",
            "hex_mode": False,
            "tx_count": 0,
            "rx_count": 0,
            "last_client_addr": None,
            "current_target_addr": None,
            "peers": [],
        },
    )
    monkeypatch.setattr("app.routers.pages._save_udp_config", lambda db, snapshot: None)
    monkeypatch.setattr("app.routers.pages.system_log_service.log_to_db", lambda *args, **kwargs: None)

    update_udp_config(
        request,
        bind_ip="127.0.0.1",
        bind_port=9000,
        custom_reply_data="reply",
        reply_mode="off",
        hex_mode=None,
        user=user,
        db=None,
    )

    assert captured_payload[-1]["custom_reply_data"] == ""


def test_update_udp_config_preserves_reply_when_basic_form_omits_reply_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import update_udp_config

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/udp-server/config", "headers": [], "query_string": b""})

    runtime_manager.udp_server.update_config(
        UDPServerConfig(bind_ip="127.0.0.1", bind_port=9000, custom_reply_data="keep-reply", hex_mode=True)
    )
    captured_payload: list[dict[str, object]] = []

    def capture_apply(payload: dict[str, object]) -> UDPServerConfig:
        captured_payload.append(payload)
        return UDPServerConfig(**payload)

    monkeypatch.setattr(runtime_manager, "apply_udp_config", capture_apply)
    monkeypatch.setattr("app.routers.pages._save_udp_config", lambda db, snapshot: None)
    monkeypatch.setattr("app.routers.pages.system_log_service.log_to_db", lambda *args, **kwargs: None)

    try:
        update_udp_config(
            request,
            bind_ip="127.0.0.1",
            bind_port=9001,
            custom_reply_data=None,
            reply_mode=None,
            hex_mode="on",
            user=user,
            db=None,
        )
    finally:
        runtime_manager.udp_server.update_config(UDPServerConfig())

    assert captured_payload[-1]["custom_reply_data"] == "keep-reply"
    assert captured_payload[-1]["hex_mode"] is True


def test_update_udp_config_preserves_hex_mode_when_reply_form_omits_hex_field(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import update_udp_config

    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    request = Request({"type": "http", "method": "POST", "path": "/udp-server/config", "headers": [], "query_string": b""})

    runtime_manager.udp_server.update_config(
        UDPServerConfig(bind_ip="127.0.0.1", bind_port=9000, custom_reply_data="old", hex_mode=True)
    )
    captured_payload: list[dict[str, object]] = []

    def capture_apply(payload: dict[str, object]) -> UDPServerConfig:
        captured_payload.append(payload)
        return UDPServerConfig(**payload)

    monkeypatch.setattr(runtime_manager, "apply_udp_config", capture_apply)
    monkeypatch.setattr("app.routers.pages._save_udp_config", lambda db, snapshot: None)
    monkeypatch.setattr("app.routers.pages.system_log_service.log_to_db", lambda *args, **kwargs: None)

    try:
        update_udp_config(
            request,
            bind_ip="127.0.0.1",
            bind_port=9000,
            custom_reply_data="new-reply",
            reply_mode="fixed",
            hex_mode=None,
            user=user,
            db=None,
        )
    finally:
        runtime_manager.udp_server.update_config(UDPServerConfig())

    assert captured_payload[-1]["custom_reply_data"] == "new-reply"
    assert captured_payload[-1]["hex_mode"] is True


def test_save_udp_config_uses_udp_server_service_name(tmp_path) -> None:
    from app.routers.pages import _save_udp_config

    db_path = tmp_path / "udp-config-name.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    snapshot = {
        "running": False,
        "bind_ip": "127.0.0.1",
        "bind_port": 9000,
        "custom_reply_data": "reply",
        "hex_mode": False,
        "tx_count": 1,
        "rx_count": 2,
        "last_client_addr": ("10.0.0.8", 4567),
    }

    with testing_session_local() as db:
        _save_udp_config(db, snapshot)
        row = db.query(ServiceConfig).one()

    assert row.name == "udp_server"
    assert row.service_type == "udp_server"


def test_udp_page_uses_reworked_layout_sections(client, db_engine) -> None:
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    login_as(client, "admin", "secret123")

    response = client.get("/udp-server")

    assert response.status_code == 200
    assert "服务状态" in response.text
    assert "基础设置" in response.text
    assert "来源地址列表" in response.text
    assert "自动回复" in response.text
    assert "日志区" in response.text
    assert 'class="log-scroll"' in response.text
    assert "实时日志" not in response.text
    assert 'class="ghost"' in response.text
    assert '<select name="reply_mode"' in response.text
    assert '<select disabled>' not in response.text
    assert "发送和自动回复均按 HEX 解析" in response.text
    assert "文本 / HEX" not in response.text


def test_udp_page_uses_operations_console_layout(client, db_engine) -> None:
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    login_as(client, "admin", "secret123")
    response = client.get("/udp-server")

    assert response.status_code == 200
    assert 'class="workbench-shell"' in response.text
    assert 'class="status-strip"' in response.text
    assert 'class="workspace-grid"' in response.text
    assert 'class="workspace-main"' in response.text
    assert 'class="workspace-side"' in response.text
    assert 'class="status-pill status-idle"' in response.text


def test_udp_page_renders_peer_table_and_target_summary(client, db_engine) -> None:
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    runtime_manager.udp_server.record_client_addr(("10.0.0.8", 4567))
    try:
        login_as(client, "admin", "secret123")

        response = client.get("/udp-server")

        assert response.status_code == 200
        assert "10.0.0.8:4567" in response.text
        assert "当前目标来源地址" in response.text
        assert "设为当前目标" in response.text
    finally:
        runtime_manager.udp_server.peers.clear()
        runtime_manager.udp_server.current_target_addr = None
        runtime_manager.udp_server.last_client_addr = None


@pytest.mark.anyio
async def test_select_udp_target_updates_page_state(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.pages import select_udp_target

    db_path = tmp_path / "udp-target.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    request = Request({"type": "http", "method": "POST", "path": "/udp-server/target", "headers": [], "query_string": b""})
    user = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    logs: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "app.routers.pages.system_log_service.log_to_db",
        lambda level, category, message, detail="", db=None: logs.append((level, category, message, detail)),
    )

    runtime_manager.udp_server.record_client_addr(("10.1.2.3", 4567))
    try:
        with testing_session_local() as db:
            response = select_udp_target(request, peer_addr="10.1.2.3:4567", user=user, db=db)

        body = response.body.decode("utf-8")
        assert "当前目标来源地址" in body
        assert "10.1.2.3:4567" in body
        assert "已切换当前目标来源" in body
        assert logs[-1] == ("info", "network", "UDP target selected by operator-user", "10.1.2.3:4567")
    finally:
        runtime_manager.udp_server.peers.clear()
        runtime_manager.udp_server.current_target_addr = None
        runtime_manager.udp_server.last_client_addr = None


def test_udp_page_filters_packet_and_system_logs(client, db_engine) -> None:
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.add(
            PacketLog(
                service_type="udp_server",
                protocol="UDP",
                direction="device -> server",
                src_ip="10.1.2.3",
                src_port=4567,
                dst_ip="127.0.0.1",
                dst_port=9000,
                data_hex="70696e67",
                data_text="ping",
                length=4,
                created_at=datetime(2026, 4, 10, 15, 8, 23, tzinfo=timezone.utc),
            )
        )
        db.add(
            SystemLog(
                level="error",
                category="network",
                message="UDP failed",
                detail="timeout",
                created_at=datetime(2026, 4, 10, 16, 0, 0, tzinfo=timezone.utc),
            )
        )
        db.commit()

    login_as(client, "admin", "secret123")

    rx_response = client.get("/udp-server?log_type=rx&q=ping")
    assert rx_response.status_code == 200
    assert "内容摘要" in rx_response.text
    assert "ping" in rx_response.text
    assert "接收" in rx_response.text
    assert "2026-04-10 23:08:23" in rx_response.text

    error_response = client.get("/udp-server?log_type=error")
    assert error_response.status_code == 200
    assert "UDP failed" in error_response.text
    assert "2026-04-11 00:00:00" in error_response.text
