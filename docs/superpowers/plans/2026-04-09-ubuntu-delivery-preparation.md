# Ubuntu Delivery Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Ubuntu handoff guide into a single deployment-and-delivery-preparation manual, keep the README entry point aligned, verify UTF-8 content integrity, and sync the final result to `origin/release/ubuntu-v0.1.0`.

**Architecture:** Keep a single operator-facing Markdown handoff document at `docs/2026-04-09-ubuntu-deployment-adaptation.md`. Add the missing delivery-preparation sections directly into that document instead of splitting templates into separate files, so deployment, rollback, acceptance logging, and final handoff checks stay in one place. Use UTF-8 reads and the existing doc-related tests to verify that content and encoding remain consistent.

**Tech Stack:** Markdown docs, Git, Pytest, UTF-8 text files.

---

## File Map

**Existing files to modify**
- `docs/2026-04-09-ubuntu-deployment-adaptation.md`
  Purpose: remain the single Ubuntu deployment and delivery-preparation handoff manual.
- `README.md`
  Purpose: keep the repository entry point aligned with the expanded Ubuntu handoff doc.

**Reference files to read before editing**
- `tests/test_project_branding.py`
- `docs/INDEX.md`
- `systemd/app.service`
- `scripts/bootstrap_ubuntu.sh`
- `Caddyfile.example`

---

### Task 1: Expand The Ubuntu Handoff Doc With Delivery Preparation

**Files:**
- Modify: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Reference: `systemd/app.service`, `scripts/bootstrap_ubuntu.sh`, `Caddyfile.example`
- Test: `tests/test_project_branding.py`

- [ ] **Step 1: Confirm the existing doc still contains the required compatibility anchors**

Verify the document keeps these strings after the rewrite:

```text
## 0. 本分支如何使用
curl -4 ifconfig.me
127.0.0.1:8080
9000/udp
9100/tcp
reverse_proxy 127.0.0.1:8080
```

These are already enforced or implied by the existing doc test coverage.

- [ ] **Step 2: Add a delivery package checklist section**

Insert a new section after the current deployment steps with content shaped like:

```md
## 13. 交付包清单

交付前至少确认以下内容已准备完毕：

- 当前部署分支或代码包
- `.env` 实际部署版本
- systemd 服务文件位置与名称
- Caddy 配置文件位置与生效域名
- 管理员账号信息交接方式
- 固定端口表
- 验收结果记录
```

The final wording may be improved, but the checklist must stay concrete and operator-facing.

- [ ] **Step 3: Add a deployment information registration section**

Insert a section with a copy-paste-ready registration template such as:

```md
## 14. 部署前信息登记

建议在交付前补齐以下信息：

- 服务器 IP：
- 访问域名：
- 部署目录：`/opt/packetbench`
- Web 监听：`127.0.0.1:8080`
- UDP 端口：`9000/udp`
- TCP 端口：`9100/tcp`
- systemd 服务名：`packetbench.service`
- Caddy 配置文件：`/etc/caddy/Caddyfile`
- 管理员账号交接人：
- 云安全组责任人：
```

- [ ] **Step 4: Add an on-site operation sequence section**

Insert a section describing the operator sequence from arrival to acceptance, with numbered steps like:

```md
## 15. 现场操作顺序

1. 核对服务器信息和访问方式
2. 核对代码版本与部署目录
3. 核对 `.env`、端口、域名
4. 启动或重启 `packetbench.service`
5. 核对 Caddy 生效状态
6. 核对防火墙和云安全组
7. 打开登录页并完成最小验收
8. 记录结果并完成交接
```

- [ ] **Step 5: Add a rollback section**

Insert a minimal rollback section that stays within currently supported deployment behavior:

```md
## 16. 回滚说明

如果本次部署失败或验收不通过，建议按以下顺序回滚：

1. 记录当前失败现象和时间点
2. 停止 `packetbench.service`
3. 恢复上一版代码或上一版部署包
4. 恢复上一版 `.env` 和 Caddy 配置
5. 重新加载 systemd 和 Caddy
6. 再次验证登录页和关键端口
```

Do not invent database migration rollback flows that the repository does not actually provide.

- [ ] **Step 6: Add an acceptance record template and final handoff check section**

Append two sections with concrete templates:

```md
## 17. 验收记录模板

- 验收时间：
- 验收人员：
- 访问地址：
- 登录结果：通过 / 失败
- UDP 验证结果：通过 / 失败
- TCP 验证结果：通过 / 失败
- 日志检查结果：通过 / 失败
- 备注：

## 18. 最终交付检查表

- [ ] 文档已更新为现场实际信息
- [ ] `.env` 已按现场配置完成
- [ ] `packetbench.service` 运行正常
- [ ] Caddy 配置已生效
- [ ] 防火墙和云安全组已放行
- [ ] 管理员账号已完成交接
- [ ] 验收记录已填写
```

- [ ] **Step 7: Review the final doc for UTF-8-safe content and operator readability**

Read the finished document and confirm:
- all Chinese text reads correctly through the file reader
- the document still flows from deployment to delivery preparation
- no new section contradicts the existing deployment instructions
- all examples remain consistent with `/opt/packetbench`, `packetbench.service`, `127.0.0.1:8080`, `9000/udp`, and `9100/tcp`

---

### Task 2: Align README With The Expanded Handoff Doc

**Files:**
- Modify: `README.md`
- Reference: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Test: `tests/test_project_branding.py`

- [ ] **Step 1: Keep the existing Ubuntu doc link intact**

Preserve this path exactly:

```md
`docs/2026-04-09-ubuntu-deployment-adaptation.md`
```

because the existing branding test asserts that the README includes it.

- [ ] **Step 2: Adjust the link label if needed to reflect delivery preparation**

If the wording still says only deployment, update it to something like:

```md
- Ubuntu 部署与交付准备文档：`docs/2026-04-09-ubuntu-deployment-adaptation.md`
```

Keep this as a minimal text-only change.

- [ ] **Step 3: Review the Linux section for duplication**

Confirm:
- the Linux section is still a summary
- the detailed operator workflow remains in the dedicated Ubuntu handoff doc
- no conflicting wording is introduced next to the new label

---

### Task 3: Verify Content, Encoding, And Push The Branch

**Files:**
- Review: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Review: `README.md`

- [ ] **Step 1: Re-read both modified docs through the file reader**

Confirm the Chinese content is displayed correctly when read with UTF-8 and that the sections added in Task 1 appear in the file contents.

- [ ] **Step 2: Run the focused doc test first**

Run:

```bash
pytest tests/test_project_branding.py -v
```

Expected:
- PASS

- [ ] **Step 3: Run the full test suite**

Run:

```bash
pytest
```

Expected:
- PASS

- [ ] **Step 4: Review the final diff before commit**

Run:

```bash
git diff -- README.md docs/2026-04-09-ubuntu-deployment-adaptation.md
```

Expected:
- only documentation changes
- updated Ubuntu handoff content includes delivery-preparation sections
- no accidental edits to code or deployment assets

- [ ] **Step 5: Commit the delivery-preparation docs**

Use:

```bash
git add README.md docs/2026-04-09-ubuntu-deployment-adaptation.md docs/superpowers/specs/2026-04-09-ubuntu-delivery-preparation-design.md docs/superpowers/plans/2026-04-09-ubuntu-delivery-preparation.md
git commit -m "docs: expand ubuntu delivery preparation"
```

- [ ] **Step 6: Push to the remote Ubuntu branch**

Use:

```bash
git push origin release/ubuntu-v0.1.0
```

Expected:
- remote branch `origin/release/ubuntu-v0.1.0` is updated successfully
