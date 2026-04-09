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
    response = client.post(
        "/client/config",
        data={"protocol": "UDP", "target_ip": "127.0.0.1", "target_port": "9201", "hex_mode": "on"},
    )

    assert response.status_code == 200
    assert "Client 配置已更新" in response.text
    assert "9201" in response.text
