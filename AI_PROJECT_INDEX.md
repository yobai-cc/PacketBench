# PacketBench AI 项目索引

本文档面向后续接手本仓库的 AI 智能体，用于快速建立项目全局认识、定位代码入口，并避免重复踩已有边界。

最后更新：2026-05-09
仓库地址：https://github.com/yobai-cc/PacketBench
本地路径：`/home/yobai/PacketBench`
当前分支：`master`
当前产品版本：`v0.1.0`

## 1. 一句话概览

PacketBench 是一个轻量级 Web 版 TCP/UDP 调试工作台，使用 FastAPI + Jinja2 + HTMX 风格表单交互 + SQLite 构建，提供登录、Dashboard、UDP 固定自动回复服务、TCP Server、TCP/UDP Client、协议包日志、系统日志和用户管理页面。

## 2. 当前已确认的产品边界

这些边界已经写入 `docs/ai-maintenance-guide.md`，AI 不应自行推翻：

- 项目名是 `PacketBench`。
- 当前产品版本是 `v0.1.0`。
- `master` 是通用产品主线，不承载某台服务器或某个交付现场的特化约束。
- `release/ubuntu-v0.1.0` 是 Ubuntu 交付分支，适合放 Ubuntu 部署、固定端口、防火墙、Caddy 现场配置等内容。
- UDP 当前语义是“固定自动回复单模式”。旧的 UDP relay / cloud 双模式只保留在归档分支，不应被 AI 从历史文档或旧分支中带回主线。
- 不要随意改项目名、版本号、cookie 名、部署路径、systemd 服务名、远端地址、tag 或发布分支策略，除非用户明确要求。

## 3. 技术栈与运行模型

### 后端

- Python 3
- FastAPI
- Starlette SessionMiddleware
- SQLAlchemy 2.x
- SQLite，默认数据库：`sqlite:///./data/app.db`
- Uvicorn，入口：`scripts/run.py`

### 前端

- Jinja2 模板：`app/templates/`
- 静态资源：`app/static/app.css`、`app/static/app.js`
- 页面交互主要通过普通 HTML 表单和服务端渲染返回页面完成；状态变更 POST 需要 CSRF token。
- `/ws/runtime` 提供运行态 WebSocket 能力；连接必须带已登录且仍有效的 active 用户 session，事件来源主要是 `system_log_service` 的系统日志广播。

### 网络运行态

运行态服务都是应用进程内对象，由 `app/services/runtime_manager.py` 中的全局 `runtime_manager` 持有：

- `UDPServerService`：UDP 监听、记录来源、固定自动回复、手动向当前目标发送。
- `TCPServerService`：TCP listener、在线客户端管理、服务端向客户端手动发送、断开客户端。
- `ClientRuntimeService`：作为 TCP 或 UDP client 连接远端并手动发送，接收回包。

这些服务不在单独进程中运行；Web 进程重启后运行态内存状态会丢失。配置和日志会写入 SQLite。

## 4. 目录结构速览

```text
PacketBench/
├── app/
│   ├── main.py                 # FastAPI app factory；挂载 session/static/router
│   ├── config.py               # Pydantic Settings；读取 .env
│   ├── db.py                   # SQLAlchemy engine/session/Base/init_db
│   ├── auth/                   # 登录、密码、CSRF、Session 用户依赖和角色校验
│   ├── models/                 # SQLAlchemy 表模型
│   ├── routers/                # Web 页面、登录、WebSocket 路由
│   ├── services/               # TCP/UDP/Client 运行态和日志服务
│   ├── templates/              # Jinja2 页面模板
│   ├── static/                 # CSS/JS
│   └── utils/                  # 编码/解码工具
├── scripts/
│   ├── init_db.py              # 初始化数据库与管理员账号
│   ├── preflight.py            # 启动前预检查
│   ├── run.py                  # Uvicorn 启动入口
│   └── bootstrap_ubuntu.sh     # Ubuntu 快速部署辅助脚本
├── tests/                      # pytest 测试
├── docs/
│   ├── INDEX.md                # 文档索引
│   ├── ai-maintenance-guide.md # AI 维护约束，修改前必读
│   ├── 2026-04-09-development-status.md
│   ├── 2026-04-09-delivery-test-guide.md
│   └── superpowers/            # 历史设计/计划文档
├── systemd/app.service         # systemd 示例
├── Caddyfile.example           # Caddy 反代示例
├── .env.example                # 环境变量模板
├── requirements.txt
└── README.md
```

## 5. 关键入口文件

### `app/main.py`

职责：创建 FastAPI 应用。

核心逻辑：

- `create_app()` 读取 settings。
- 创建 `data_dir` 和 `log_dir`。
- 创建 `FastAPI(title="PacketBench", version="v0.1.0")`。
- 加入 `SessionMiddleware`，cookie 名来自 `SESSION_COOKIE_NAME`，默认 `packetbench_session`。
- 挂载 `/static`。
- include routers：`auth`、`pages`、`ws`。
- `lifespan()` 中调用 `init_db()` 并写入启动日志。

### `scripts/run.py`

职责：开发和部署启动入口。

- 读取 `WEB_HOST`、`WEB_PORT`、`APP_ENV`。
- 运行 `uvicorn.run("app.main:app", host=settings.web_host, port=settings.web_port, reload=settings.app_env == "development")`。

### `scripts/init_db.py`

职责：初始化数据库和管理员。

- 创建 data/log 目录。
- 调用 `init_db()` 创建表。
- 若 `ADMIN_USERNAME` 对应用户不存在，则创建 admin 用户，密码来自 `ADMIN_PASSWORD`。

### `scripts/preflight.py`

职责：启动前基础检查。

- 创建 data/log 目录。
- 调用 `create_app()`。
- 成功时输出 `preflight ok`。

## 6. 路由索引

### 认证路由：`app/routers/auth.py`

- `GET /login`：登录页。
- `POST /login`：校验用户名密码，成功后写入 `request.session["user_id"]` 并跳转 Dashboard。
- `POST /logout`：清理 session 并跳转登录页。

### 页面和操作路由：`app/routers/pages.py`

- `GET /`：303 跳转 `/dashboard`。
- `GET /dashboard`：运行态概览、日志计数。
- `GET /udp-server`：UDP Server 页面。
- `POST /udp-server/config`：保存 UDP 配置。
- `POST /udp-server/start`：启动 UDP listener。
- `POST /udp-server/stop`：停止 UDP listener。
- `POST /udp-server/send`：向当前 UDP 目标手动发送。
- `POST /udp-server/target`：选择 UDP 当前目标来源。
- `POST /udp-server/peer/remove`：删除 UDP 来源记录。
- `GET /packets`：协议包日志列表，支持 protocol/service/direction/q/limit 筛选。
- `GET /logs`：系统日志列表，支持 level/category/q/limit 筛选。
- `GET /tcp-server`：TCP Server 页面。
- `POST /tcp-server/config`：保存 TCP Server 配置。
- `POST /tcp-server/start`：启动 TCP listener。
- `POST /tcp-server/stop`：停止 TCP listener。
- `POST /tcp-server/send`：向指定 TCP client 发送。
- `POST /tcp-server/disconnect`：断开指定 TCP client。
- `GET /client`：TCP/UDP Client 页面。
- `POST /client/config`：保存 Client 配置。
- `POST /client/connect`：连接远端。
- `POST /client/disconnect`：断开 Client。
- `POST /client/send`：Client 向远端发送。
- `GET /users`：用户管理页。
- `POST /users/create`：创建用户。
- `POST /users/toggle`：启用/禁用用户。

### WebSocket 路由：`app/routers/ws.py`

- `WS /ws/runtime`：要求已登录且用户仍存在、未禁用；连接后订阅 `system_log_service`，接收系统日志 runtime event。匿名或已禁用用户连接会以 1008 policy violation 关闭。

## 7. 数据模型索引

定义目录：`app/models/`

### `User`

表：`users`

字段：

- `id`
- `username`：唯一，索引。
- `password_hash`
- `role`：默认 `viewer`，常见角色包括 `admin`、`operator`、`viewer`。
- `is_active`
- `created_at`
- `last_login_at`

### `PacketLog`

表：`packet_logs`

字段：

- `service_type`：例如 `udp_server`、`tcp_server`、`client`。
- `protocol`：`TCP` 或 `UDP`。
- `direction`：例如 `device -> server`、`server -> device`、`client -> server`、`server -> client`、`client -> remote`、`remote -> client`、`manual`。
- `src_ip` / `src_port`
- `dst_ip` / `dst_port`
- `data_hex`
- `data_text`
- `length`
- `created_at`

### `SystemLog`

表：`system_logs`

字段：

- `level`：如 `info`、`warning`、`error`。
- `category`：如 `auth`、`service`、`network`、`rule`、`config`。
- `message`
- `detail`
- `created_at`

### `ServiceConfig`

表：`service_configs`

字段：

- `name`：唯一配置名，如 `udp_server`、`tcp_server`、`client_runtime`。
- `service_type`
- `bind_ip` / `bind_port`
- `target_ip` / `target_port`
- `enabled`
- `config_json`
- `created_at` / `updated_at`

## 8. 核心服务索引

### `app/services/runtime_manager.py`

全局运行态聚合器。

- 持有 `udp_server`、`tcp_server`、`client_runtime` 三个单例服务。
- 提供 `*_snapshot()` 给页面渲染使用。
- 提供 `apply_*_config()` 将页面表单配置转换为对应 dataclass。

### `app/services/udp_server.py`

UDP 固定自动回复服务。

关键点：

- 默认监听 `0.0.0.0:9000`。
- 默认 `custom_reply_data` 为空；收到包但回复内容为空时不回包，写 warning 日志。
- 收到 UDP 包后记录来源、更新 peer 状态、写 packet/system log。
- 若配置了固定回复，则按 `hex_mode` 解析 payload 并回发。
- 手动发送目标优先使用 `current_target_addr`，否则 `last_client_addr`。
- 支持 peer 列表、选择当前目标、删除来源记录。

### `app/services/tcp_server.py`

TCP Server 运行态。

关键点：

- 默认监听 `0.0.0.0:9100`。
- 使用 `asyncio.start_server()`。
- 以 `ip:port` 作为 client_id 管理在线客户端。
- 记录 TCP RX/TX 字节计数。
- 支持向指定 client 手动发送和断开指定 client。
- 流量写入 `packet_logs`，服务事件写入 `system_logs`。

### `app/services/client_runtime.py`

TCP/UDP Client 运行态。

关键点：

- 默认协议 `TCP`，目标 `127.0.0.1:9001`。
- TCP 模式使用 `asyncio.open_connection()`，后台 task 读取回包。
- UDP 模式创建本地 UDP endpoint，然后向目标 `sendto()`。
- 支持手动发送、断开、RX/TX 计数。
- 流量写入 `packet_logs`，运行事件写入 `system_logs`。

### `app/services/packet_logger.py`

统一落库 packet log。

预期职责：

- 将 payload 转成 hex 和文本表达。
- 写入 `PacketLog`。

### `app/services/logging_service.py`

统一系统日志服务。

预期职责：

- 写入应用日志文件和数据库日志。
- 管理 WebSocket 订阅者。
- `log_to_db()` 写入日志后会向订阅者广播 runtime event；无活动订阅者时不缓存普通历史日志，事件历史仍以数据库日志为准。

## 9. 鉴权和权限模型

相关文件：

- `app/auth/security.py`
- `app/auth/deps.py`
- `app/auth/csrf.py`
- `app/routers/auth.py`

当前机制：

- 密码使用 bcrypt 哈希。
- 登录成功后把 `user_id` 放入 Starlette session，并确保 session 中存在 CSRF token。
- `get_current_user()` 从 session 取用户；无 session 或用户禁用时跳转 `/login`。
- `require_role(*allowed_roles)` 用于限制操作权限。
- `CSRFMiddleware` 保护非安全 HTTP 方法；除 `/login` 外，状态变更 POST 需要表单字段 `csrf_token` 或请求头 `X-CSRF-Token`。
- Jinja 页面 context 通过 `_base_context()` 注入 `csrf_token`，新增表单时必须带 hidden input。

常见权限边界：

- `admin` / `operator`：可以启动/停止服务、保存配置、发送数据、断开连接等操作。
- `viewer`：只读查看状态、日志、客户端列表等。

## 10. 配置项索引

环境变量模板：`.env.example`

```text
APP_ENV=development
SECRET_KEY=change-this-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123456
WEB_HOST=127.0.0.1
WEB_PORT=8080
DATABASE_URL=sqlite:///./data/app.db
LOG_DIR=./logs
DATA_DIR=./data
APP_LOG_FILE=app.log
PACKET_LOG_FILE=packets.log
SESSION_COOKIE_NAME=packetbench_session
SESSION_SECURE=false
```

生产环境至少应修改：

- `APP_ENV=production`
- `SECRET_KEY`
- `ADMIN_PASSWORD`
- `SESSION_SECURE=true`，前提是通过 HTTPS 访问。

安全启动约束：当 `APP_ENV=production` 或 `APP_ENV=prod` 时，`app/config.py` 会拒绝默认 `SECRET_KEY=change-this-secret-key` 或默认 `ADMIN_PASSWORD=admin123456`，避免带开发凭据上线。这里的默认值常量是用于“拒绝开发默认值”的哨兵，不是可用生产凭据；静态扫描可能会把它识别为 hardcoded secret，需要结合上下文判断。

## 11. 页面模板索引

目录：`app/templates/`

- `base.html`：全站基础布局。
- `login.html`：登录页。
- `dashboard.html`：概览页。
- `udp_server.html`：UDP Server 页面。
- `tcp_server.html`：TCP Server 页面。
- `client.html`：TCP/UDP Client 页面。
- `packets.html`：协议包日志页。
- `logs.html`：系统日志页。
- `users.html`：用户管理页。
- `placeholder.html`：占位模板。

修改页面时通常要同时检查：

- `app/routers/pages.py` 中对应 context 字段。
- 模板中是否引用了同名字段。
- `tests/test_*_page.py`、`tests/test_pages_integration.py`、`tests/test_auth_integration.py` 中是否有页面断言。

## 12. 测试索引

测试目录：`tests/`

当前验证状态：`pytest -q` 为 90 passed；`python scripts/preflight.py` 输出 `preflight ok`。

当前测试大致覆盖：

- App factory：`test_app_factory.py`
- 登录/Session/权限集成：`test_auth_integration.py`
- 页面集成：`test_pages_integration.py`
- UDP relay/UDP server 行为：`test_udp_relay.py`、`test_udp_server_page.py`
- TCP server 行为：`test_tcp_server.py`
- Client runtime 和页面：`test_client_runtime.py`、`test_client_page.py`
- Packets/Logs 筛选：`test_filters_pages.py`
- Users 页面：`test_users_page.py`
- WebSocket：`test_ws_runtime.py`
- 安全加固回归：`test_security_hardening.py`（CSRF、WS 鉴权、生产默认凭据）
- 编码工具：`test_codec.py`
- 品牌命名：`test_project_branding.py`

测试夹具：`tests/conftest.py`

- 为每个测试创建临时 SQLite DB。
- 调用 `create_app()`。
- 覆盖 `get_db` 依赖，避免污染真实 `data/app.db`。

## 13. 本地开发常用命令

Linux/macOS：

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

Windows PowerShell 风格命令在 `README.md` 中已有记录。

运行测试：

```bash
cd /home/yobai/PacketBench
. .venv/bin/activate
pytest
```

如果当前环境没有虚拟环境，也可用系统 Python 临时验证，但不要把生成的 `data/`、`logs/`、`.venv/` 提交。

## 14. 部署相关文件

- `systemd/app.service`
  - 默认工作目录：`/opt/packetbench`
  - `EnvironmentFile=/opt/packetbench/.env`
  - `ExecStart=/opt/packetbench/.venv/bin/python scripts/run.py`
  - User/Group：`www-data`

- `Caddyfile.example`
  - 反代 Web 到 `127.0.0.1:8080`。
  - TCP/UDP 业务端口不经过 Caddy，由应用自身监听。

- `scripts/bootstrap_ubuntu.sh`
  - Ubuntu 快速部署辅助脚本。
  - 涉及系统依赖、虚拟环境、依赖安装、`.env` 初始化、数据库初始化和预检查。

## 15. 代码规模快照

基于当前工作区粗略统计，排除 `.git`、虚拟环境、缓存和构建目录：

```text
Python         42 files   4519 lines
Markdown       15 files   4370 lines
HTML/Jinja2    10 files    806 lines
CSS             1 file     606 lines
JavaScript      1 file      28 lines
Shell           1 file      29 lines
systemd         1 file      17 lines
其他配置        若干
总计           75 files  10416 lines
```

## 16. AI 修改前检查清单

开始改代码前：

1. 运行 `git status --short --branch`，确认分支和工作区。
2. 阅读 `docs/ai-maintenance-guide.md`。
3. 如果是 Ubuntu/现场部署特化，优先考虑是否应该切到 `release/ubuntu-v0.1.0`。
4. 如果涉及 UDP 行为，确认不是把旧 relay/cloud 双模式带回当前主线。
5. 根据改动范围定位对应测试。

提交或交付前：

1. 至少运行与改动范围匹配的 pytest。
2. 如果改了启动、配置或数据库，运行 `python scripts/preflight.py`。
3. 如果改了路由/页面，检查登录态、权限态、页面模板 context。
4. 如果改了网络运行态，补充或运行 TCP/UDP runtime 测试。
5. 检查 `git diff`，不要包含 `.env`、`data/`、`logs/`、`.venv/` 等本地生成物。

## 17. 推荐阅读顺序

新 AI 接手时建议按以下顺序阅读：

1. `README.md`
2. `docs/ai-maintenance-guide.md`
3. 本文档：`AI_PROJECT_INDEX.md`
4. `app/main.py`
5. `app/config.py`
6. `app/db.py`
7. `app/routers/pages.py`
8. `app/services/runtime_manager.py`
9. `app/services/udp_server.py`
10. `app/services/tcp_server.py`
11. `app/services/client_runtime.py`
12. `tests/conftest.py` 和与目标改动相关的测试文件

## 18. 常见改动定位指南

- 登录、Session 或 CSRF 问题：`app/routers/auth.py`、`app/auth/deps.py`、`app/auth/security.py`、`app/auth/csrf.py`、`tests/test_auth_integration.py`、`tests/test_security_hardening.py`
- UDP Server 问题：`app/services/udp_server.py`、`app/routers/pages.py` 的 `/udp-server*` 路由、`app/templates/udp_server.html`
- TCP Server 问题：`app/services/tcp_server.py`、`app/routers/pages.py` 的 `/tcp-server*` 路由、`app/templates/tcp_server.html`
- TCP/UDP Client 问题：`app/services/client_runtime.py`、`app/routers/pages.py` 的 `/client*` 路由、`app/templates/client.html`
- 日志筛选问题：`app/routers/pages.py` 的 `/packets` 和 `/logs`、`app/templates/packets.html`、`app/templates/logs.html`
- 用户管理问题：`app/routers/pages.py` 的 `/users*`、`app/templates/users.html`
- 数据库模型问题：`app/models/`、`app/db.py`、`scripts/init_db.py`
- 部署问题：`README.md`、`systemd/app.service`、`Caddyfile.example`、`scripts/bootstrap_ubuntu.sh`

## 19. 重要注意事项

- 当前项目没有 Alembic 迁移体系；模型变更需要谨慎处理已有 SQLite 数据。
- `app/db.py` 在模块导入末尾调用了 `init_db()`，因此导入 DB 模块会触发表创建。
- `runtime_manager` 是进程内全局单例；多 worker 部署会导致运行态不共享，不适合直接开多进程 worker。
- TCP/UDP 业务端口由应用自身监听，Web 反代只处理 HTTP 页面。
- 当前日志既有文件日志也有数据库日志；页面展示依赖数据库日志。
- `.env.example` 中的默认密码和 secret 只适合开发；生产环境未修改时应用会拒绝启动。默认值哨兵用于阻止上线，不应删除，除非同步调整 `.env.example` 和生产校验逻辑。
- 新增状态变更表单时必须添加 `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`，否则真实 POST 会 403。
- `/ws/runtime` 已经不是匿名 smoke endpoint；测试或客户端连接前必须先登录。
