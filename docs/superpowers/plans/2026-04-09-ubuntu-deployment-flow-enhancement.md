# Ubuntu Deployment Flow Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add concrete Git and archive-based project acquisition steps plus clearer deployment actions to the Ubuntu handoff guide, and update the docs index to match the guide's new role.

**Architecture:** Keep `docs/2026-04-09-ubuntu-deployment-adaptation.md` as the single operator-facing deployment and handoff manual. Expand its early deployment sections with a Git-first flow, an archive fallback flow, and explicit deployment sequencing. Keep `docs/INDEX.md` as a summary-only document that points to the Ubuntu guide without duplicating the procedure.

**Tech Stack:** Markdown docs, Git, Ubuntu shell commands.

---

## File Map

**Existing files to modify**
- `docs/2026-04-09-ubuntu-deployment-adaptation.md`
  Purpose: add Git clone/pull flow, archive upload flow, code-version verification, and a more explicit deployment sequence.
- `docs/INDEX.md`
  Purpose: describe the Ubuntu guide as a deployment-and-handoff manual.

**Reference files to read before editing**
- `README.md`
- `systemd/app.service`
- `scripts/bootstrap_ubuntu.sh`
- `Caddyfile.example`

---

### Task 1: Expand The Ubuntu Guide With Concrete Code Acquisition Steps

**Files:**
- Modify: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Reference: `README.md`, `scripts/bootstrap_ubuntu.sh`

- [ ] **Step 1: Keep the existing compatibility anchors unchanged**

Preserve these strings in the Ubuntu guide:

```text
## 0. 本分支如何使用
curl -4 ifconfig.me
127.0.0.1:8080
9000/udp
9100/tcp
reverse_proxy 127.0.0.1:8080
```

- [ ] **Step 2: Rewrite the project preparation section to include a Git-first path**

In the early deployment section, add concrete commands shaped like:

```bash
sudo mkdir -p /opt/packetbench
sudo chown -R $USER:$USER /opt/packetbench
cd /opt/packetbench
git clone https://github.com/yobai-cc/PacketBench.git .
git checkout release/ubuntu-v0.1.0
git pull origin release/ubuntu-v0.1.0
git rev-parse --short HEAD
```

Explain that:
- first deployment uses `git clone`
- later updates use `git pull origin release/ubuntu-v0.1.0`
- `git rev-parse --short HEAD` is used to record the deployed commit

- [ ] **Step 3: Add an archive fallback path for environments without Git access**

Add a separate subsection with commands shaped like:

```bash
sudo mkdir -p /opt/packetbench
sudo chown -R $USER:$USER /opt/packetbench
cd /opt/packetbench
unzip packetbench-release-ubuntu-v0.1.0.zip -d /opt/packetbench
ls
```

If you use a different extraction example, it must stay realistic for Ubuntu and explain:
- where the archive should be uploaded
- how to extract it into `/opt/packetbench`
- how to replace an old directory carefully
- how to confirm required files exist after extraction

- [ ] **Step 4: Add a code-version confirmation subsection**

Add operator-facing checks such as:

```md
代码准备完成后，建议至少记录以下信息：

- 当前分支：`git branch --show-current`
- 当前提交：`git rev-parse --short HEAD`
- 关键文件是否存在：`requirements.txt`、`.env.example`、`scripts/run.py`、`systemd/app.service`
```

---

### Task 2: Make The Deployment Actions More Explicit

**Files:**
- Modify: `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- Reference: `systemd/app.service`, `Caddyfile.example`

- [ ] **Step 1: Convert the early deployment flow into a more explicit action sequence**

Adjust the section ordering and wording so the operator can follow this sequence clearly:

```text
1. 准备服务器目录
2. 获取项目代码（Git 或压缩包）
3. 确认代码版本和关键文件
4. 安装系统依赖
5. 创建虚拟环境并安装依赖
6. 配置 `.env`
7. 初始化数据库并执行预检查
8. 安装或重启 systemd 服务
9. 写入并校验 Caddy 配置
10. 放行端口
11. 验收
```

- [ ] **Step 2: Add explicit post-update deployment actions for Git-based maintenance**

Add a short subsection for later updates with commands like:

```bash
cd /opt/packetbench
git fetch origin
git checkout release/ubuntu-v0.1.0
git pull origin release/ubuntu-v0.1.0
. .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python scripts/preflight.py
sudo systemctl restart packetbench.service
```

Explain that this is for a server already deployed once.

- [ ] **Step 3: Ensure the archive path also includes the same post-extract deployment actions**

Make sure the archive section clearly reconnects to the shared flow after extraction:
- configure `.env`
- create or reuse `.venv`
- install requirements
- run `scripts/init_db.py`
- run `scripts/preflight.py`
- restart service

- [ ] **Step 4: Review the final guide for duplication and operator clarity**

Confirm:
- Git remains the recommended path
- archive remains a fallback path
- the operator never needs to guess the next step after code is present
- the new sections do not contradict the existing rollback and acceptance sections

---

### Task 3: Update The Docs Index And Verify The Result

**Files:**
- Modify: `docs/INDEX.md`
- Review: `docs/2026-04-09-ubuntu-deployment-adaptation.md`

- [ ] **Step 1: Update the docs index description for the Ubuntu guide**

Replace the current description with wording shaped like:

```md
- `2026-04-09-ubuntu-deployment-adaptation.md`
  - Ubuntu 部署与交付准备手册，覆盖代码获取、部署动作、验收与回滚。
```

- [ ] **Step 2: Re-read the modified docs to confirm Chinese content and new sections are visible**

Read:
- `docs/2026-04-09-ubuntu-deployment-adaptation.md`
- `docs/INDEX.md`

Confirm the new Git and archive sections are present and the Chinese text displays normally.

- [ ] **Step 3: Run the focused documentation test**

Run:

```bash
pytest tests/test_project_branding.py -v
```

Expected:
- PASS

- [ ] **Step 4: Review the final diff**

Run:

```bash
git diff -- docs/2026-04-09-ubuntu-deployment-adaptation.md docs/INDEX.md
```

Expected:
- only documentation changes
- Ubuntu guide includes both Git and archive code acquisition paths
- docs index description matches the guide's new role
