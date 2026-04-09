# Users Page Design

## Goal

在现有 FastAPI + Jinja2 SSR 架构下，将 `/users` 从占位页替换为真实的用户管理页面，首轮范围仅包含用户列表、创建用户、启用/禁用用户，并保持 `viewer` 不可访问。

## Current Context

- 认证采用 Session，会话解析在 `app/auth/deps.py`。
- 角色控制通过 `require_role()` 完成，`/users` 入口目前已限制为 `admin`。
- 页面路由集中在 `app/routers/pages.py`，当前模式是 SSR 页面加少量表单 POST 动作。
- 模板基于 Jinja2，页面共用 `app/templates/base.html` 和现有 CSS，不引入 SPA 或前端构建。
- 用户模型位于 `app/models/user.py`，现有字段已满足本轮最小范围：`username`、`password_hash`、`role`、`is_active`、`created_at`、`last_login_at`。

## In Scope

- `GET /users` 渲染真实用户管理页面。
- 仅 `admin` 可访问和操作用户管理。
- 列出所有用户，展示：
  - `username`
  - `role`
  - `is_active`
  - `created_at`
  - `last_login_at`
- 新增用户：输入 `username`、`password`、`role`。
- 启用/禁用用户。
- 阻止禁用最后一个 active admin。
- 阻止当前登录 admin 禁用自己，避免当前会话把自己锁死。
- 使用 TDD，先写失败测试，再做最小实现。

## Out Of Scope

- 密码重置。
- 删除用户。
- 首轮角色编辑。
- 用户搜索、分页、筛选。
- 任何 Client / TCP Server / UDP Server 已完成功能的重构。

## Route Design

### GET `/users`

- 依赖：`require_role("admin")`
- 查询所有用户，按 `created_at` 或 `id` 稳定排序。
- 渲染 `users.html`。
- 若非 admin，通过现有依赖返回 403，不新增特殊跳转逻辑。

### POST `/users/create`

- 依赖：`require_role("admin")`
- 表单字段：`username`、`password`、`role`
- 校验：
  - `username` 去除首尾空白后不能为空
  - `password` 不能为空
  - `role` 必须属于 `admin`、`operator`、`viewer`
  - `username` 必须唯一
- 密码使用 `app.auth.security.hash_password()` 哈希后入库。
- 成功后重新渲染 `users.html` 并显示成功消息。
- 失败时重新渲染 `users.html` 并显示错误消息，不跳转到新页面。

### POST `/users/toggle`

- 依赖：`require_role("admin")`
- 表单字段：`user_id`
- 若目标用户不存在，返回当前页错误消息。
- 若目标用户当前为启用状态，则尝试禁用：
  - 若目标用户是当前登录用户，拒绝禁用
  - 若目标用户角色为 `admin` 且其为最后一个 active admin，拒绝禁用
- 其余情况直接切换 `is_active`。
- 成功后重新渲染 `users.html` 并显示成功消息。

## Template Design

新增 `app/templates/users.html`，延续当前页面结构：

- 页面头部显示标题和消息。
- 使用两栏 `grid two`：
  - 左侧卡片：创建用户表单
  - 右侧卡片：用户管理说明或访问规则提示
- 下方卡片：用户列表表格

表格每行包含：

- 用户名
- 角色
- 状态
- 创建时间
- 最后登录时间
- 操作按钮（启用 / 禁用）

仅使用现有 CSS 类：`card`、`grid two`、`alert`、`table-wrap`、`button-row` 等；如确有必要，只补最小样式。

## Data Handling

- 不新增模型字段。
- 不新增 service 层抽象，避免为本轮最小功能引入不必要结构。
- 用户操作直接在 `pages.py` 中配合 `Session` 完成，保持与现有页面路由一致。
- 创建用户和启停用户成功后提交数据库事务。

## Logging

沿用 `system_log_service.log_to_db()` 记录关键审计事件：

- 用户创建成功
- 用户启用
- 用户禁用
- 用户创建失败或禁用被拒绝不强制单独记审计，首轮以页面提示为主，避免过度扩 scope

## TDD Plan

首轮 focused tests 新增 `tests/test_users_page.py`，风格对齐 `tests/test_client_page.py`：直接调用路由函数，配合临时 SQLite 数据库断言 HTML 和数据库状态。

测试顺序：

1. `/users` 对 admin 渲染真实页面，对非 admin 通过角色依赖拒绝访问。
2. 创建用户成功，页面返回成功消息，数据库新增用户且密码为哈希值。
3. 重复用户名创建失败，不新增记录。
4. 禁用普通用户成功。
5. 禁用最后一个 active admin 失败。
6. admin 禁用自己失败。

## Verification

完成后执行：

- focused tests：`tests/test_users_page.py` 及其依赖的认证/页面相关测试
- `scripts/preflight.py`
- 必要的启动验证，确认应用可正常导入并启动到现有入口

## Risks And Limits

- 当前 `pages.py` 已较长，继续加 `/users` 逻辑会增加文件长度；但本轮遵循仓库现状，不额外拆分。
- 时间显示格式先沿用模板默认输出；若后续需要统一本地化格式，再单独收敛。
- 本轮不做角色编辑，后续若增加此能力，需要重新定义“最后一个 admin”保护边界。

## Confirmed Decisions

- 角色体系保持现状：`admin`、`operator`、`viewer`。
- 本轮不改动现有 `/client`、`/tcp-server`、`/udp-server` 的角色模型与权限逻辑。
- 新建用户表单允许选择现有三种角色，避免引入跨模块角色重构。
