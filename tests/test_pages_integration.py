import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User


def login_as(client, username: str, password: str) -> None:
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_unauthenticated_requests_redirect_to_login(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_viewer_can_open_client_page_but_cannot_see_mutation_forms(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="viewer", password_hash=hash_password("secret123"), role="viewer", is_active=True))
        db.commit()

    login_as(client, "viewer", "secret123")
    response = client.get("/client")

    assert response.status_code == 200
    assert "Viewer 角色仅可查看 Client 运行状态。" in response.text
    assert "/client/connect" not in response.text


def test_operator_cannot_open_users_page(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="operator", password_hash=hash_password("secret123"), role="operator", is_active=True))
        db.commit()

    login_as(client, "operator", "secret123")
    response = client.get("/users", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_open_users_page(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    login_as(client, "admin", "secret123")
    response = client.get("/users")

    assert response.status_code == 200
    assert "用户管理" in response.text


def test_operator_can_update_client_config_through_real_post(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="operator", password_hash=hash_password("secret123"), role="operator", is_active=True))
        db.commit()

    login_as(client, "operator", "secret123")
    page = client.get("/client")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = client.post(
        "/client/config",
        data={"protocol": "UDP", "target_ip": "127.0.0.1", "target_port": "9201", "hex_mode": "on", "csrf_token": token},
    )

    assert response.status_code == 200
    assert "Client 配置已更新" in response.text
    assert "9201" in response.text


def test_login_page_uses_packetbench_branding(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "PacketBench 登录" in response.text
    assert "U2T Web 登录" not in response.text


def test_sidebar_logout_button_has_distinct_style(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    login_as(client, "admin", "secret123")
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'class="sidebar-logout"' in response.text
    assert 'class="sidebar"' in response.text


def test_dashboard_does_not_show_nonfunctional_runtime_stream(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    login_as(client, "admin", "secret123")
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="runtime-stream"' in response.text
    assert "Runtime Event Stream" in response.text
    assert "等待运行时事件" in response.text
    assert "PacketBench Control Plane" in response.text
    assert 'class="metric-card"' in response.text
    assert 'class="service-card"' in response.text
    assert "Recent Packet Log" in response.text


def test_static_css_assets_are_consolidated_and_have_balanced_rule_blocks():
    static_dir = Path("app/static")
    assert not (static_dir / "v3.css").exists()
    assert not (static_dir / "v4.css").exists()

    css = (static_dir / "app.css").read_text(encoding="utf-8")
    assert "Consolidated final UI polish" in css

    balance = 0
    for char in css:
        if char == "{":
            balance += 1
        elif char == "}":
            balance -= 1
        assert balance >= 0

    assert balance == 0


def test_consolidated_css_keeps_final_dashboard_and_udp_polish():
    css = Path("app/static/app.css").read_text(encoding="utf-8")

    assert "grid-template-columns: 216px minmax(0, 1fr);" in css
    assert ".listener-config-primary-row" in css
    assert ".listener-config-reply-row" in css
    assert ".payload-config-field" in css
    assert ".dashboard-side .runtime-stream" in css
    assert ".manual-reply-panel" in css
