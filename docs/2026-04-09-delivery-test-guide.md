# 2026-04-09 Delivery Test Guide

## Scope In This Build

- 登录与 Session
- Dashboard
- UDP Server
- TCP Server
- TCP/UDP Client
- Users 页面
- Packets / Logs 最小筛选

## Recommended Accounts

- `admin`: full access
- `operator`: runtime operations only
- `viewer`: read-only

## Environment Preparation

1. Create venv and install requirements.
2. Run `.venv\Scripts\python scripts/init_db.py`.
3. Run `.venv\Scripts\python scripts/preflight.py`.
4. Run `.venv\Scripts\python scripts/run.py`.

默认管理员账号来自 `.env` 或 `.env.example` 中的 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`。
如需覆盖 `operator` 和 `viewer` 行为，请先用 admin 登录后在 `/users` 创建测试账号。

## Suggested Test Flow

1. Verify login success, failed login, and logout.
2. Verify unauthenticated access to `/dashboard`, `/client`, `/tcp-server`, and `/users` redirects to `/login`.
3. Verify `/users` is admin-only.
4. Verify viewer cannot mutate `/client` and `/tcp-server`.
5. Verify TCP server start, manual send, and disconnect.
6. Verify client connect, manual send, and disconnect in TCP mode.
7. Verify UDP server start, manual send, and stop.
8. Verify failed runtime actions show inline error and appear in `/logs`.
9. Verify `/packets` and `/logs` filters return expected rows.

## Known Limits

- Client is single-profile only.
- Pages are SSR refresh-based, not SPA.
- Runtime audit is intentionally minimal.
- No advanced scheduling, auto-reconnect, or profile management.
