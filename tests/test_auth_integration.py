import warnings

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User


def test_auth_routes_do_not_emit_template_deprecation_warning(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        login_page_response = client.get("/login")
        failed_login_response = client.post("/login", data={"username": "admin", "password": "wrong"})

    assert login_page_response.status_code == 200
    assert failed_login_response.status_code == 400
    messages = [str(item.message) for item in caught]
    assert not any("The `name` is not the first parameter anymore" in message for message in messages)


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "登录" in response.text


def test_login_succeeds_and_redirects_to_dashboard(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    response = client.post(
        "/login",
        data={"username": "admin", "password": "secret123"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_login_failure_returns_400_and_error_message(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True))
        db.commit()

    response = client.post("/login", data={"username": "admin", "password": "wrong"})

    assert response.status_code == 400
    assert "用户名或密码错误" in response.text


def test_inactive_user_cannot_log_in(client, db_engine):
    with Session(db_engine) as db:
        db.add(User(username="disabled", password_hash=hash_password("secret123"), role="viewer", is_active=False))
        db.commit()

    response = client.post("/login", data={"username": "disabled", "password": "secret123"})

    assert response.status_code == 400
    assert "用户名或密码错误" in response.text


def test_logout_clears_session_and_redirects(client, db_engine):
    with Session(db_engine) as db:
        user = User(username="admin", password_hash=hash_password("secret123"), role="admin", is_active=True)
        db.add(user)
        db.commit()

    login_response = client.post(
        "/login",
        data={"username": "admin", "password": "secret123"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    logout_response = client.post("/logout", follow_redirects=False)

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"

    redirected = client.get("/dashboard", follow_redirects=False)
    assert redirected.status_code == 303
    assert redirected.headers["location"] == "/login"
