from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

from app.db import Base
from app.models.user import User


def test_users_page_replaces_placeholder_for_admin(tmp_path) -> None:
    from app.routers.pages import users_page

    db_path = tmp_path / "users-page.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    request = Request({"type": "http", "method": "GET", "path": "/users", "headers": [], "query_string": b""})
    admin = User(username="admin-user", password_hash="x", role="admin", is_active=True)

    with Session(engine) as db:
        db.add_all(
            [
                User(username="admin-user", password_hash="x", role="admin", is_active=True),
                User(username="operator-user", password_hash="x", role="operator", is_active=True),
            ]
        )
        db.commit()

    with testing_session_local() as db:
        response = users_page(request, user=admin, db=db)

    body = response.body.decode("utf-8")
    assert "用户管理" in body
    assert "第二阶段实现" not in body
    assert "admin-user" in body
    assert "operator-user" in body


def test_users_page_non_admin_is_forbidden() -> None:
    from app.auth.deps import require_role

    operator = User(username="operator-user", password_hash="x", role="operator", is_active=True)
    dependency = require_role("admin")

    try:
        dependency(user=operator)
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Insufficient permissions"
    else:
        raise AssertionError("Expected non-admin access to be rejected")


def test_create_user_persists_hashed_password_and_renders_message(tmp_path) -> None:
    from app.auth.security import verify_password
    from app.routers.pages import create_user

    db_path = tmp_path / "create-user.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    request = Request({"type": "http", "method": "POST", "path": "/users/create", "headers": [], "query_string": b""})
    admin = User(username="admin-user", password_hash="x", role="admin", is_active=True)

    with testing_session_local() as db:
        response = create_user(request, username="new-user", password="secret123", role="viewer", user=admin, db=db)

    body = response.body.decode("utf-8")
    assert "用户已创建" in body
    assert "new-user" in body

    with Session(engine) as db:
        row = db.query(User).filter(User.username == "new-user").one()
        assert row.role == "viewer"
        assert row.is_active is True
        assert row.password_hash != "secret123"
        assert verify_password("secret123", row.password_hash) is True


def test_create_user_rejects_duplicate_username(tmp_path) -> None:
    from app.routers.pages import create_user

    db_path = tmp_path / "duplicate-user.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        db.add(User(username="dup-user", password_hash="x", role="viewer", is_active=True))
        db.commit()

    request = Request({"type": "http", "method": "POST", "path": "/users/create", "headers": [], "query_string": b""})
    admin = User(username="admin-user", password_hash="x", role="admin", is_active=True)

    with testing_session_local() as db:
        response = create_user(request, username="dup-user", password="secret123", role="viewer", user=admin, db=db)

    body = response.body.decode("utf-8")
    assert "用户名已存在" in body

    with Session(engine) as db:
        assert db.query(User).filter(User.username == "dup-user").count() == 1


def test_toggle_user_disables_and_enables_regular_user(tmp_path) -> None:
    from app.routers.pages import toggle_user

    db_path = tmp_path / "toggle-user.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        target = User(username="viewer-user", password_hash="x", role="viewer", is_active=True)
        db.add(target)
        db.commit()
        target_id = target.id

    request = Request({"type": "http", "method": "POST", "path": "/users/toggle", "headers": [], "query_string": b""})
    admin = User(id=999, username="admin-user", password_hash="x", role="admin", is_active=True)

    with testing_session_local() as db:
        disable_response = toggle_user(request, user_id=target_id, user=admin, db=db)
        assert "用户已禁用" in disable_response.body.decode("utf-8")

    with Session(engine) as db:
        assert db.get(User, target_id).is_active is False

    with testing_session_local() as db:
        enable_response = toggle_user(request, user_id=target_id, user=admin, db=db)
        assert "用户已启用" in enable_response.body.decode("utf-8")

    with Session(engine) as db:
        assert db.get(User, target_id).is_active is True


def test_toggle_user_blocks_disabling_last_active_admin(tmp_path) -> None:
    from app.routers.pages import toggle_user

    db_path = tmp_path / "last-admin.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        target = User(username="sole-admin", password_hash="x", role="admin", is_active=True)
        db.add(target)
        db.commit()
        target_id = target.id

    request = Request({"type": "http", "method": "POST", "path": "/users/toggle", "headers": [], "query_string": b""})
    acting_admin = User(id=999, username="other-admin", password_hash="x", role="admin", is_active=True)

    with testing_session_local() as db:
        response = toggle_user(request, user_id=target_id, user=acting_admin, db=db)

    body = response.body.decode("utf-8")
    assert "至少保留一个启用中的 admin" in body

    with Session(engine) as db:
        assert db.get(User, target_id).is_active is True


def test_toggle_user_blocks_admin_from_disabling_self(tmp_path) -> None:
    from app.routers.pages import toggle_user

    db_path = tmp_path / "self-disable.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        admin = User(username="self-admin", password_hash="x", role="admin", is_active=True)
        db.add(admin)
        db.commit()
        admin_id = admin.id

    request = Request({"type": "http", "method": "POST", "path": "/users/toggle", "headers": [], "query_string": b""})
    acting_admin = User(id=admin_id, username="self-admin", password_hash="x", role="admin", is_active=True)

    with testing_session_local() as db:
        response = toggle_user(request, user_id=admin_id, user=acting_admin, db=db)

    body = response.body.decode("utf-8")
    assert "不能禁用当前登录账号" in body

    with Session(engine) as db:
        assert db.get(User, admin_id).is_active is True
