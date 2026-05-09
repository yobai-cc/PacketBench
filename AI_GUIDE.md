# PacketBench AI 维护说明

本文档是给 AI 智能体的“接手说明”。如果你要在 PacketBench 仓库里改代码、查 bug、补测试或改文档，先读这里，再读 `AI_PROJECT_INDEX.md` 和 `docs/ai-maintenance-guide.md`。

## 1. 当前仓库状态

- 仓库：`https://github.com/yobai-cc/PacketBench`
- 本地路径：`/home/yobai/PacketBench`
- 主线分支：`master`
- 产品版本：`v0.1.0`
- 技术栈：FastAPI + Jinja2 + SQLAlchemy + SQLite + asyncio TCP/UDP runtime

## 2. 最重要的维护原则

1. 先看分支，再动手。

   ```bash
   git status --short --branch
   ```

2. 通用功能和通用 bugfix 进 `master`。
3. Ubuntu 或具体交付现场特化内容不要直接写进 `master`，优先考虑 `release/ubuntu-v0.1.0`。
4. 不要把旧 UDP relay / cloud 双模式语义带回当前主线。当前 UDP 是固定自动回复单模式。
5. 不要未经明确要求修改项目名、版本号、session cookie 名、systemd 服务名、部署路径、远端地址、tag、release 策略。
6. 如果工作区已有他人改动，不要回退，不要覆盖，先确认 diff 来源。
7. 每次改动后运行与范围匹配的测试或预检查。

## 3. AI 快速上手流程

```bash
cd /home/yobai/PacketBench
git status --short --branch
```

优先阅读：

```text
README.md
docs/ai-maintenance-guide.md
AI_PROJECT_INDEX.md
```

如果要理解代码流，再按顺序看：

```text
app/main.py
app/config.py
app/db.py
app/routers/pages.py
app/services/runtime_manager.py
app/services/udp_server.py
app/services/tcp_server.py
app/services/client_runtime.py
tests/conftest.py
```

## 4. 运行和验证

首次本地运行：

```bash
cd /home/yobai/PacketBench
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
python scripts/preflight.py
python scripts/run.py
```

预检查：

```bash
python scripts/preflight.py
```

测试：

```bash
pytest
```

按范围测试示例：

```bash
pytest tests/test_auth_integration.py tests/test_security_hardening.py
pytest tests/test_udp_server_page.py tests/test_udp_relay.py
pytest tests/test_tcp_server.py
pytest tests/test_client_runtime.py tests/test_client_page.py
pytest tests/test_filters_pages.py
```

## 5. 代码修改定位表

| 需求/问题 | 优先查看 |
|---|---|
| 登录、登出、Session、CSRF | `app/routers/auth.py`, `app/auth/deps.py`, `app/auth/security.py`, `app/auth/csrf.py` |
| 权限控制 | `app/auth/deps.py`, `app/routers/pages.py` 中的 `require_role(...)` |
| Dashboard | `app/routers/pages.py`, `app/templates/dashboard.html` |
| UDP Server | `app/services/udp_server.py`, `app/templates/udp_server.html`, `/udp-server*` 路由 |
| TCP Server | `app/services/tcp_server.py`, `app/templates/tcp_server.html`, `/tcp-server*` 路由 |
| TCP/UDP Client | `app/services/client_runtime.py`, `app/templates/client.html`, `/client*` 路由 |
| 协议包日志 | `app/models/packet_log.py`, `app/services/packet_logger.py`, `/packets` 路由 |
| 系统日志 | `app/models/system_log.py`, `app/services/logging_service.py`, `/logs` 路由 |
| 用户管理 | `app/models/user.py`, `app/templates/users.html`, `/users*` 路由 |
| 配置项 | `.env.example`, `app/config.py` |
| 数据库初始化 | `app/db.py`, `scripts/init_db.py` |
| WebSocket | `app/routers/ws.py`, `app/services/logging_service.py`, `tests/test_ws_runtime.py`, `tests/test_security_hardening.py` |
| systemd/Caddy 部署 | `systemd/app.service`, `Caddyfile.example`, `README.md` |

## 6. 运行态架构要点

`app/services/runtime_manager.py` 创建全局 `runtime_manager`，里面有三个进程内服务：

```text
runtime_manager
├── udp_server: UDPServerService
├── tcp_server: TCPServerService
└── client_runtime: ClientRuntimeService
```

这意味着：

- 运行态状态是内存状态。
- Web 进程重启会丢失当前连接、peer 列表、计数器等内存状态。
- 配置和日志会写 SQLite。
- 不适合简单开多个 Uvicorn/Gunicorn worker，否则不同 worker 的 runtime 状态不共享。

## 7. 数据流速记

### 登录与 CSRF

```text
/login form
  -> app/routers/auth.py:login()
  -> verify_password()
  -> request.session["user_id"] = user.id
  -> ensure_csrf_token(request)
  -> /dashboard
```

状态变更 POST 由 `app/auth/csrf.py:CSRFMiddleware` 校验 CSRF。除 `/login` 外，POST/PUT/PATCH/DELETE 等非安全方法需要表单字段 `csrf_token` 或请求头 `X-CSRF-Token`。新增 Jinja 表单时必须加：

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

### UDP Server 收包

```text
UDP datagram
  -> UDPServerProtocol.datagram_received()
  -> UDPServerService.handle_datagram()
  -> record peer / update counters
  -> packet_logger.log_packet(... service_type="udp_server", protocol="UDP")
  -> if custom_reply_data: parse_payload() and sendto()
  -> system_log_service.log_to_db(...)
```

### TCP Server 收包

```text
TCP client connects
  -> TCPServerService._handle_client()
  -> read loop
  -> packet_logger.log_packet(... service_type="tcp_server", protocol="TCP")
  -> page snapshot via runtime_manager.tcp_snapshot()
```

### WebSocket runtime event

```text
已登录浏览器
  -> WS /ws/runtime
  -> app/routers/ws.py 校验 session["user_id"]
  -> system_log_service.subscribe(websocket)
  -> system_log_service.log_to_db(...)
  -> broadcast runtime event
```

匿名 WebSocket 或已禁用用户的旧 session 会以 1008 policy violation 关闭。

### Client 发送

```text
/client form
  -> pages.py /client/send
  -> runtime_manager.client_runtime.send_manual()
  -> TCP writer or UDP transport
  -> packet_logger.log_packet(... service_type="client")
```

## 8. 测试编写习惯

现有测试使用 pytest 和 FastAPI TestClient。

`tests/conftest.py` 会：

- 创建临时 SQLite 数据库。
- `Base.metadata.create_all()`。
- 创建 app。
- 覆盖 `get_db`。

所以新增页面/路由测试时，优先复用 `client` fixture，不要直接打真实 `data/app.db`。

如果测试 runtime 服务，优先让服务可注入临时 db_factory，避免污染真实数据库和全局状态。若必须用全局 `runtime_manager`，测试结束要清理运行态，避免影响后续测试。

## 9. 安全加固状态

- `APP_ENV=production` 或 `APP_ENV=prod` 时，默认 `SECRET_KEY=change-this-secret-key` 会阻止启动。
- `APP_ENV=production` 或 `APP_ENV=prod` 时，默认 `ADMIN_PASSWORD=admin123456` 会阻止启动。该默认值在代码中作为拒绝上线的 sentinel 使用，静态扫描命中时需按上下文判断。
- 表单状态变更需要 CSRF token。
- `/ws/runtime` 需要登录 session，且用户必须仍存在并保持 active。
- `system_log_service.log_to_db()` 会广播 runtime event 给当前 WebSocket 订阅者。
- 当前验证：`python scripts/preflight.py` -> `preflight ok`；`pytest -q` -> `90 passed`。

## 10. 常见坑

1. UDP 语义坑

   当前 UDP 是固定自动回复单模式，不是 relay/cloud 双模式。历史文档或测试名里可能出现 relay 字样，不能据此恢复旧产品语义。

2. 多 worker 坑

   runtime 是进程内单例。多 worker 会让 TCP/UDP listener、连接列表、计数器分裂。部署文档不要建议直接开多 worker。

3. SQLite 迁移坑

   当前没有 Alembic。改 model 字段不等于自动迁移已有生产库。涉及表结构变更时必须单独设计迁移策略。

4. Session secure 坑

   `SESSION_SECURE=true` 需要 HTTPS，否则浏览器不会在 HTTP 下发送 secure cookie。生产建议 HTTPS + true，本地开发默认 false。

5. 表单 context 坑

   页面模板高度依赖 `pages.py` 构造的 context。改模板字段时要同步改 context 和测试断言。

6. 日志展示坑

   页面展示依赖数据库日志；文件日志存在但不是页面数据源。排查页面没日志时先查 `system_logs` / `packet_logs`。

7. CSRF 表单坑

   所有状态变更表单都要带 `csrf_token` hidden input。只改模板不改 context，或只加 POST 路由不加 token，真实页面会 403。

8. WebSocket 鉴权坑

   `/ws/runtime` 必须先登录，且用户仍需存在并保持 active；测试里使用 `client.websocket_connect()` 前要先创建用户并 `POST /login`。如果测试禁用/删除用户后的旧 session，预期应收到 1008 policy violation。

## 11. 文档职责

- `README.md`：产品总览、本地运行、通用部署入口。不要膨胀成现场操作手册。
- `docs/ai-maintenance-guide.md`：仓库维护规则和 AI 工作约束。
- `AI_PROJECT_INDEX.md`：面向 AI 的源码级索引和阅读地图。
- `AI_GUIDE.md`：面向 AI 的操作手册，即本文档。
- `docs/2026-04-09-development-status.md`：开发快照。
- `docs/2026-04-09-delivery-test-guide.md`：交付测试说明。
- `docs/superpowers/`：历史设计和计划文档，不代表当前最新状态。

## 12. 交付前自检模板

完成改动后，至少检查：

```bash
git status --short --branch
git diff --stat
```

按改动范围运行：

```bash
python scripts/preflight.py
pytest
```

如果只改文档，可以不跑全量测试，但仍应检查：

```bash
git diff -- README.md docs/ AI_PROJECT_INDEX.md AI_GUIDE.md
```

不要提交或交付以下本地生成物：

```text
.env
.venv/
data/
logs/
__pycache__/
.pytest_cache/
```

## 13. 对后续 AI 的建议

- 先理解运行态，再改页面按钮和表单。
- 先找对应测试，再改行为。
- 对网络服务相关改动，优先写小范围异步测试验证真实 TCP/UDP 行为。
- 对部署文档改动，先判断是通用产品文档还是 Ubuntu/现场特化文档。
- 对安全相关改动，保持简单务实，但不要削弱 server-side 权限控制。
