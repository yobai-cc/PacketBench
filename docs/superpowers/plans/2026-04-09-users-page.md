# Users Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/users` placeholder with a real admin-only SSR page that lists users, creates users, and enables/disables users without changing the existing role model.

**Architecture:** Extend the existing `app/routers/pages.py` route module with a small set of `/users` handlers and add one Jinja2 template that follows the current SSR pattern. Keep all data access in the page routes with SQLAlchemy sessions, use `hash_password()` for new users, and cover behavior with focused route-function tests against a temporary SQLite database.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, SQLAlchemy, SQLite, pytest

---

## File Map

- Modify: `app/routers/pages.py`
  Responsibility: replace `/users` placeholder with real page and add create/toggle handlers.
- Create: `app/templates/users.html`
  Responsibility: render user creation form, status messages, and users table.
- Create: `tests/test_users_page.py`
  Responsibility: focused TDD coverage for `/users` page, creation, duplicate handling, and enable/disable safety rules.

### Task 1: Add failing coverage for `/users` page rendering and admin-only behavior

**Files:**
- Create: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`
- Create: `app/templates/users.html`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_users_page_replaces_placeholder_for_admin tests/test_users_page.py::test_users_page_non_admin_is_forbidden -v`
Expected: FAIL because `users_page` and `users.html` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

In `app/routers/pages.py`, replace the placeholder route with:

```python
@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = db.query(User).order_by(User.id.asc()).all()
    context = _base_context(request, user)
    context["users"] = rows
    return templates.TemplateResponse(request, "users.html", context)
```

Create `app/templates/users.html` with:

```html
{% extends "base.html" %}
{% block title %}用户管理{% endblock %}
{% block content %}
<section class="page-header">
  <h1>用户管理</h1>
  {% if message %}<div class="alert success">{{ message }}</div>{% endif %}
  {% if error %}<div class="alert error">{{ error }}</div>{% endif %}
</section>

<section class="grid two">
  <article class="card">
    <h2>创建用户</h2>
    <form method="post" action="/users/create">
      <label>用户名<input name="username" required></label>
      <label>密码<input name="password" type="password" required></label>
      <label>
        角色
        <select name="role">
          <option value="viewer">viewer</option>
          <option value="operator">operator</option>
          <option value="admin">admin</option>
        </select>
      </label>
      <button type="submit">创建用户</button>
    </form>
  </article>
  <article class="card">
    <h2>访问规则</h2>
    <p>仅 admin 可访问该页面。</p>
    <p>本轮支持列表、创建、启用和禁用用户。</p>
  </article>
</section>

<section class="card">
  <h2>用户列表</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>用户名</th>
          <th>角色</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>最后登录</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {% for item in users %}
        <tr>
          <td>{{ item.username }}</td>
          <td>{{ item.role }}</td>
          <td>{{ '启用' if item.is_active else '禁用' }}</td>
          <td>{{ item.created_at }}</td>
          <td>{{ item.last_login_at or '从未登录' }}</td>
          <td>待实现</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_users_page_replaces_placeholder_for_admin tests/test_users_page.py::test_users_page_non_admin_is_forbidden -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py app/templates/users.html
git commit -m "test: add users page coverage"
```

### Task 2: Add failing coverage for creating users

**Files:**
- Modify: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_create_user_persists_hashed_password_and_renders_message -v`
Expected: FAIL because `create_user` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add helper and route in `app/routers/pages.py`:

```python
from app.auth.security import hash_password


def _users_context(request: Request, user: User, db: Session) -> dict[str, object]:
    context = _base_context(request, user)
    context["users"] = db.query(User).order_by(User.id.asc()).all()
    return context


@router.post("/users/create", response_class=HTMLResponse)
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    username = username.strip()
    allowed_roles = {"admin", "operator", "viewer"}

    context = _users_context(request, user, db)
    if not username or not password:
        context["error"] = "用户名和密码不能为空"
        return templates.TemplateResponse(request, "users.html", context)
    if role not in allowed_roles:
        context["error"] = "角色不合法"
        return templates.TemplateResponse(request, "users.html", context)
    if db.query(User).filter(User.username == username).first() is not None:
        context["error"] = "用户名已存在"
        return templates.TemplateResponse(request, "users.html", context)

    row = User(username=username, password_hash=hash_password(password), role=role, is_active=True)
    db.add(row)
    db.commit()
    system_log_service.log_to_db("info", "auth", f"User {username} created by {user.username}", db=db)

    context = _users_context(request, user, db)
    context["message"] = "用户已创建"
    return templates.TemplateResponse(request, "users.html", context)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_create_user_persists_hashed_password_and_renders_message -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py
git commit -m "feat: add user creation page flow"
```

### Task 3: Add failing coverage for duplicate usernames

**Files:**
- Modify: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_create_user_rejects_duplicate_username -v`
Expected: FAIL until duplicate handling is wired.

- [ ] **Step 3: Write minimal implementation**

Keep the duplicate guard in `create_user()` exactly as:

```python
if db.query(User).filter(User.username == username).first() is not None:
    context["error"] = "用户名已存在"
    return templates.TemplateResponse(request, "users.html", context)
```

If the test was written after the implementation, do not add new behavior here; only confirm the route keeps this guard.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_create_user_rejects_duplicate_username -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py
git commit -m "test: cover duplicate user creation"
```

### Task 4: Add failing coverage for enabling and disabling regular users

**Files:**
- Modify: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`
- Modify: `app/templates/users.html`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_toggle_user_disables_and_enables_regular_user -v`
Expected: FAIL because `toggle_user` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add route in `app/routers/pages.py`:

```python
@router.post("/users/toggle", response_class=HTMLResponse)
def toggle_user(
    request: Request,
    user_id: int = Form(...),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    context = _users_context(request, user, db)
    target = db.get(User, user_id)
    if target is None:
        context["error"] = "用户不存在"
        return templates.TemplateResponse(request, "users.html", context)

    if target.is_active:
        target.is_active = False
        message = "用户已禁用"
        log_message = f"User {target.username} disabled by {user.username}"
    else:
        target.is_active = True
        message = "用户已启用"
        log_message = f"User {target.username} enabled by {user.username}"

    db.add(target)
    db.commit()
    system_log_service.log_to_db("info", "auth", log_message, db=db)

    context = _users_context(request, user, db)
    context["message"] = message
    return templates.TemplateResponse(request, "users.html", context)
```

Update the action column in `app/templates/users.html` to:

```html
<td>
  <form method="post" action="/users/toggle">
    <input type="hidden" name="user_id" value="{{ item.id }}">
    <button type="submit" class="{{ 'danger' if item.is_active else '' }}">
      {{ '禁用' if item.is_active else '启用' }}
    </button>
  </form>
</td>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_toggle_user_disables_and_enables_regular_user -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py app/templates/users.html
git commit -m "feat: add user enable toggle"
```

### Task 5: Add failing coverage for admin safety rules

**Files:**
- Modify: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_toggle_user_blocks_disabling_last_active_admin tests/test_users_page.py::test_toggle_user_blocks_admin_from_disabling_self -v`
Expected: FAIL because safety checks are not implemented yet.

- [ ] **Step 3: Write minimal implementation**

Insert these guards before disabling an active user in `toggle_user()`:

```python
if target.is_active:
    if target.id == user.id:
        context["error"] = "不能禁用当前登录账号"
        return templates.TemplateResponse(request, "users.html", context)

    if target.role == "admin":
        active_admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if active_admin_count <= 1:
            context["error"] = "至少保留一个启用中的 admin"
            return templates.TemplateResponse(request, "users.html", context)

    target.is_active = False
    message = "用户已禁用"
    log_message = f"User {target.username} disabled by {user.username}"
else:
    target.is_active = True
    message = "用户已启用"
    log_message = f"User {target.username} enabled by {user.username}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_users_page.py::test_toggle_user_blocks_disabling_last_active_admin tests/test_users_page.py::test_toggle_user_blocks_admin_from_disabling_self -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py
git commit -m "fix: protect admin user toggles"
```

### Task 6: Final focused verification

**Files:**
- Modify: `tests/test_users_page.py`
- Modify: `app/routers/pages.py`
- Modify: `app/templates/users.html`

- [ ] **Step 1: Run the focused users test suite**

Run: `.venv\Scripts\pytest tests/test_users_page.py -v`
Expected: all users page tests PASS.

- [ ] **Step 2: Run related focused regression tests**

Run: `.venv\Scripts\pytest tests/test_client_page.py -v`
Expected: PASS, confirming the page route module still behaves correctly for existing `/client` work.

- [ ] **Step 3: Run preflight**

Run: `.venv\Scripts\python scripts/preflight.py`
Expected: `preflight ok`

- [ ] **Step 4: Run startup verification**

Run: `.venv\Scripts\python scripts/run.py`
Expected: application starts on the configured local address without import errors. Stop it after confirming startup.

- [ ] **Step 5: Commit**

```bash
git add tests/test_users_page.py app/routers/pages.py app/templates/users.html
git commit -m "feat: add users management page"
```
