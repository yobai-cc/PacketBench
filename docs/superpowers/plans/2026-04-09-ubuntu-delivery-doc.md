# Ubuntu Delivery Doc Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tester-friendly Ubuntu first-deployment handoff document and a minimal README entry point so delivery staff can deploy `PacketBench v0.1.0` on Ubuntu 22.04/24.04 without needing product internals.

**Architecture:** Keep deployment behavior unchanged and document the existing Ubuntu path already present in the repository: `bootstrap_ubuntu.sh`, `.env`, `systemd/app.service`, and `Caddyfile.example`. Reuse the existing adaptation notes where accurate, but convert the final handoff into an ordered operations manual with commands, expected results, and failure checks.

**Tech Stack:** Markdown docs, Ubuntu 22.04/24.04, Python virtualenv, systemd, Caddy, UFW.

---

## File Map

**Existing files to modify**
- `docs/2026-04-09-ubuntu-deployment-adaptation.md`
  Purpose: either replace its structure with a formal first-deployment handoff or reuse the file as the final delivery document if that is the smallest correct edit.
- `README.md`
  Purpose: add a minimal link to the Ubuntu delivery document from the existing Linux deployment section.

**Reference files to read before editing**
- `systemd/app.service`
- `scripts/bootstrap_ubuntu.sh`
- `Caddyfile.example`
- `docs/2026-04-09-delivery-test-guide.md`

---

### Task 1: Reshape The Ubuntu Deployment Doc Into A Delivery Manual

**Files:**
- Modify: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Reference: `systemd/app.service`, `scripts/bootstrap_ubuntu.sh`, `Caddyfile.example`
- Review: `docs/2026-04-09-ubuntu-deployment-adaptation.md`

- [ ] **Step 1: Read the current deployment doc against the actual repo assets**

Confirm the document still matches these repository facts:

```text
systemd/app.service
- WorkingDirectory=/opt/packetbench
- EnvironmentFile=/opt/packetbench/.env
- ExecStart=/opt/packetbench/.venv/bin/python scripts/run.py
- User=www-data

scripts/bootstrap_ubuntu.sh
- creates data and logs directories
- creates .venv if missing
- installs requirements
- copies .env.example to .env when absent
- runs scripts/init_db.py and scripts/preflight.py

Caddyfile.example
- reverse_proxy 127.0.0.1:8080
```

- [ ] **Step 2: Rewrite the title and opening summary for delivery staff**

Replace the opening with a handoff-oriented introduction like:

```md
# 2026-04-09 Ubuntu First Deployment Handoff

本文用于 `PacketBench v0.1.0` 在 Ubuntu 22.04/24.04 上的首次部署交付，面向按步骤执行的运维/交付人员。

本文目标：

- 在一台干净的 Ubuntu 服务器上完成首次部署
- 让 Web、UDP Server、TCP Server 具备可验收的基础运行能力
- 统一端口、反向代理、防火墙和页面监听配置，避免现场联调不一致
```

- [ ] **Step 3: Replace the middle sections with ordered deployment steps**

Rewrite the body into this exact high-level structure, filled with real commands and expected outcomes:

```md
## 1. 前置条件
## 2. 服务器目录与项目文件准备
## 3. 安装系统依赖
## 4. 初始化 Python 环境与依赖
## 5. 配置 `.env`
## 6. 初始化数据库与预检查
## 7. 安装并启动 systemd 服务
## 8. 配置 Caddy 反向代理
## 9. 放行防火墙与云安全组端口
## 10. 首次部署验收
## 11. 常见故障排查
```

The rewritten sections must include these concrete command blocks:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip caddy
sudo mkdir -p /opt/packetbench
sudo chown -R $USER:$USER /opt/packetbench
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/init_db.py
.venv/bin/python scripts/preflight.py
sudo cp systemd/app.service /etc/systemd/system/packetbench.service
sudo systemctl daemon-reload
sudo systemctl enable --now packetbench.service
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 9000/udp
sudo ufw allow 9100/tcp
```

- [ ] **Step 4: Add explicit expected-result notes after critical commands**

After the install, bootstrap, service, and reverse-proxy steps, add short operator-facing checks such as:

```md
预期结果：

- `scripts/preflight.py` 输出成功并退出码为 0
- `systemctl status packetbench.service` 显示 `active (running)`
- `http://<公网IP>/login` 或 `https://<域名>/login` 可以打开登录页
```

- [ ] **Step 5: Add a first-deployment acceptance checklist**

Include a numbered checklist with these items:

```md
1. 登录页可访问
2. 使用管理员账号成功登录
3. `/udp-server` 页面绑定为 `0.0.0.0:9000`
4. `/tcp-server` 页面绑定为 `0.0.0.0:9100`
5. UDP 外部发包后可收到自动回复
6. TCP 外部连接后页面可见连接和收发
7. `/packets` 与 `/logs` 能看到对应记录
```

- [ ] **Step 6: Add a focused troubleshooting section**

The troubleshooting section must include these checks and what they are for:

```md
- `journalctl -u packetbench.service -n 100 --no-pager`: 查看服务启动失败原因
- `sudo systemctl status caddy`: 查看反代是否生效
- `sudo ufw status`: 核对端口是否已放行
- `curl -I http://127.0.0.1:8080/login`: 验证应用是否在本机监听
- 检查页面中的 UDP/TCP 绑定端口是否与防火墙和云安全组一致
```

- [ ] **Step 7: Review the rewritten doc for order and readability**

Read the final document top to bottom and verify:
- the steps are in execution order
- no section assumes deep development knowledge
- all commands reference files that actually exist in the repository
- the document does not introduce any deployment mechanism that the repo does not already support

- [ ] **Step 8: Commit**

```bash
git add docs/2026-04-09-ubuntu-deployment-adaptation.md
git commit -m "docs: add ubuntu deployment handoff guide"
```

---

### Task 2: Add The README Entry Point

**Files:**
- Modify: `README.md`
- Reference: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Review: `README.md`

- [ ] **Step 1: Locate the existing Linux deployment section in README**

Confirm the current insertion point is around:

```md
## Linux 部署
```

and that the Ubuntu doc link will be visible before the long command sequence.

- [ ] **Step 2: Add a minimal delivery-doc link near the top of the Linux section**

Insert text like:

```md
- Ubuntu 首次部署交付文档：`docs/2026-04-09-ubuntu-deployment-adaptation.md`
```

Keep the change minimal and avoid duplicating the handoff content inside README.

- [ ] **Step 3: Review README for duplication and wording**

Check that:
- README still reads as a project overview
- the new line clearly signals that the separate doc is for delivery use
- there is no conflicting Ubuntu instruction next to the new link

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: link ubuntu delivery guide"
```

---

### Task 3: Verify The Final Documentation Set

**Files:**
- Review: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Review: `README.md`

- [ ] **Step 1: Read both final documents together**

Check the pair as a delivery flow:

```text
README.md -> points operators to the Ubuntu handoff doc
Ubuntu handoff doc -> contains the real ordered execution steps
```

- [ ] **Step 2: Run a focused diff review**

Run:

```bash
git diff -- README.md docs/2026-04-09-ubuntu-deployment-adaptation.md
```

Expected:
- only documentation changes
- no accidental code or config edits
- wording matches Ubuntu first deployment, not local Windows development

- [ ] **Step 3: Commit the final documentation set if tasks were batched**

If the work was not committed per task, use:

```bash
git add README.md docs/2026-04-09-ubuntu-deployment-adaptation.md
git commit -m "docs: finalize ubuntu deployment handoff"
```
