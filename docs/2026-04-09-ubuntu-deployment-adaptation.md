# 2026-04-09 Ubuntu First Deployment Handoff

本文用于 `PacketBench v0.1.0` 在 Ubuntu 22.04/24.04 上的首次部署交付，面向按步骤执行的运维/交付人员。

本文目标：

- 在一台干净的 Ubuntu 服务器上完成首次部署
- 让 Web、UDP Server、TCP Server 具备可验收的基础运行能力
- 统一端口、反向代理、防火墙和页面监听配置，避免现场联调不一致

## 0. 本分支如何使用

当前文档位于 `release/ubuntu-v0.1.0` 交付分支，对应 Ubuntu 现场部署与交付说明。

使用建议：

- Ubuntu 首次部署、现场交付、环境验收优先参考本文
- 通用功能说明仍以 `README.md` 为入口
- 如 `master` 后续修复了通用问题，需要评估是否同步到本分支

## 1. 前置条件

部署前请确认：

- 目标系统为 Ubuntu 22.04 或 24.04
- 当前账号具备 `sudo` 权限
- 已拿到项目代码包，或已能从仓库拉取 `release/ubuntu-v0.1.0` 分支内容
- 已准备好管理员账号口令、目标域名或服务器公网 IP
- 如需外部设备联调，已具备云安全组或网络防火墙配置权限

建议先记录本机公网 IP，便于后续域名解析核对和临时验收：

```bash
curl -4 ifconfig.me
```

或：

```bash
curl -4 https://api.ipify.org
```

预期结果：命令返回一个公网 IP 字符串，例如 `203.0.113.10`。

## 2. 服务器目录与项目代码准备

先创建部署目录：

```bash
sudo mkdir -p /opt/packetbench
sudo chown -R $USER:$USER /opt/packetbench
cd /opt/packetbench
```

推荐优先使用 Git 方式准备代码，便于后续更新、问题追踪和回滚。

### 方案 A：使用 Git 拉取项目代码（推荐）

首次部署可直接执行：

```bash
git clone https://github.com/yobai-cc/PacketBench.git .
git checkout release/ubuntu-v0.1.0
git pull origin release/ubuntu-v0.1.0
git branch --show-current
git rev-parse --short HEAD
```

说明：

- 首次部署使用 `git clone`
- 交付分支固定使用 `release/ubuntu-v0.1.0`
- `git rev-parse --short HEAD` 用于记录当前实际部署提交

如果服务器已经部署过一次，后续更新可执行：

```bash
cd /opt/packetbench
git fetch origin
git checkout release/ubuntu-v0.1.0
git pull origin release/ubuntu-v0.1.0
git rev-parse --short HEAD
```

预期结果：

- 当前分支显示为 `release/ubuntu-v0.1.0`
- 能输出当前短提交号
- 项目目录下能看到代码文件和 `docs/`、`scripts/`、`systemd/` 等目录

### 方案 B：使用压缩包上传项目代码（无 Git 环境时使用）

如果服务器无法直接访问 GitHub，可先在本地准备好交付压缩包，然后上传到服务器，例如上传到 `/opt/packetbench`：

```bash
cd /opt/packetbench
unzip packetbench-release-ubuntu-v0.1.0.zip -d /opt/packetbench
ls
```

如果当前目录中已有旧版本文件，建议先备份旧目录，再解压新包，避免新旧文件混杂。例如：

```bash
cd /opt
mv packetbench packetbench.bak
mkdir -p packetbench
cd packetbench
unzip ../packetbench-release-ubuntu-v0.1.0.zip -d /opt/packetbench
```

预期结果：解压后至少应能看到以下文件和目录：

- `requirements.txt`
- `.env.example`
- `scripts/bootstrap_ubuntu.sh`
- `scripts/init_db.py`
- `scripts/preflight.py`
- `scripts/run.py`
- `systemd/app.service`
- `Caddyfile.example`

### 代码版本确认

代码准备完成后，建议至少记录以下信息：

- 当前分支：`git branch --show-current`（若为压缩包方式，可记为压缩包版本名）
- 当前提交：`git rev-parse --short HEAD`（若为压缩包方式，可记为压缩包文件名）
- 关键文件是否存在：`requirements.txt`、`.env.example`、`scripts/run.py`、`systemd/app.service`

## 3. 安装系统依赖

在 Ubuntu 上安装 Python 和 Caddy：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip caddy
```

预期结果：安装成功，无中断报错。

可选检查：

```bash
python3 --version
caddy version
```

预期结果：`python3` 和 `caddy` 都能输出版本号。

## 4. 部署动作顺序

建议现场按下面顺序执行，不要跳步：

1. 准备服务器目录
2. 获取项目代码（Git 或压缩包）
3. 确认代码版本和关键文件
4. 安装系统依赖
5. 创建虚拟环境并安装依赖
6. 配置 `.env`
7. 初始化数据库并执行预检查
8. 安装或重启 `systemd` 服务
9. 写入并校验 Caddy 配置
10. 放行端口
11. 验收

## 5. 初始化 Python 环境与依赖

如果希望一步完成虚拟环境、依赖安装、`.env` 初始化、数据库初始化和预检查，可直接执行：

```bash
sudo bash scripts/bootstrap_ubuntu.sh
```

如果你希望逐步执行和观察每一步，也可以手动运行：

```bash
cd /opt/packetbench
mkdir -p data logs
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

如果是 Git 方式的后续版本更新，也建议在 `git pull` 之后重复执行：

```bash
cd /opt/packetbench
. .venv/bin/activate
pip install -r requirements.txt
```

预期结果：

- 当前目录下生成 `.venv`、`data`、`logs`
- `pip install -r requirements.txt` 成功完成
- 没有出现缺失系统依赖导致的安装失败

## 6. 配置 `.env`

如果项目目录下还没有 `.env`，先从示例文件复制：

```bash
cp .env.example .env
```

建议至少确认或修改以下配置：

```env
APP_ENV=production
SECRET_KEY=replace-with-a-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
WEB_HOST=127.0.0.1
WEB_PORT=8080
SESSION_SECURE=true
```

说明：

- `WEB_HOST=127.0.0.1` 和 `WEB_PORT=8080` 表示 Web 只监听本机，由 Caddy 反代对外提供访问
- `SECRET_KEY` 不能保留默认值，必须改成新的随机字符串
- `ADMIN_PASSWORD` 应改为交付现场约定的强密码
- 如果当前只使用公网 IP 做临时 HTTP 验收，尚未启用 HTTPS，可暂时设置：

```env
SESSION_SECURE=false
```

待正式域名和 HTTPS 就绪后，再改回 `true`。

预期结果：`.env` 文件已存在，且关键配置项已经根据现场环境修改完成。

## 7. 初始化数据库与预检查

如果前面没有使用 `bootstrap_ubuntu.sh`，请手动执行：

```bash
cd /opt/packetbench
.venv/bin/python scripts/init_db.py
.venv/bin/python scripts/preflight.py
```

预期结果：

- 数据库初始化成功
- `scripts/preflight.py` 输出成功并退出码为 0

如果是 Git 更新或压缩包替换后的再次部署，也建议至少执行：

```bash
cd /opt/packetbench
.venv/bin/python scripts/preflight.py
```

如果初始化完成，可额外确认这些目录文件已经出现：

- `data/app.db`
- `logs/`

## 8. 安装并启动 systemd 服务

仓库内置的服务文件位于 `systemd/app.service`，其关键配置为：

- `WorkingDirectory=/opt/packetbench`
- `EnvironmentFile=/opt/packetbench/.env`
- `ExecStart=/opt/packetbench/.venv/bin/python scripts/run.py`
- 运行用户为 `www-data`

先确保部署目录对 `www-data` 可读写。若当前目录归属还是登录用户，可执行：

```bash
sudo chown -R www-data:www-data /opt/packetbench
```

首次部署安装服务：

```bash
sudo cp systemd/app.service /etc/systemd/system/packetbench.service
sudo systemctl daemon-reload
sudo systemctl enable --now packetbench.service
sudo systemctl status packetbench.service
```

如果是后续更新部署，可执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart packetbench.service
sudo systemctl status packetbench.service
```

预期结果：`systemctl status packetbench.service` 显示 `active (running)`。

如需查看最近服务日志：

```bash
journalctl -u packetbench.service -n 100 --no-pager
```

## 9. 配置 Caddy 反向代理

Web 应用建议固定为本机监听 `127.0.0.1:8080`，由 Caddy 对外暴露 80/443。

如果已有域名，推荐直接使用 HTTPS。将 `Caddyfile.example` 按实际域名写入 `/etc/caddy/Caddyfile`，示例如下：

```caddy
packetbench.example.com {
    encode gzip zstd

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy strict-origin-when-cross-origin
    }

    reverse_proxy 127.0.0.1:8080
}
```

如果当前没有域名，只做首次临时验收，可先使用：

```caddy
:80 {
    encode gzip zstd

    reverse_proxy 127.0.0.1:8080
}
```

写入配置后执行：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy
```

预期结果：

- `caddy validate` 输出校验通过
- `systemctl status caddy` 显示 `active (running)`
- 浏览器可以访问 `http://<公网IP>/login` 或 `https://<域名>/login`

## 10. 放行防火墙与云安全组端口

推荐固定本次部署端口如下：

- Web 应用监听：`127.0.0.1:8080`
- Caddy 对外监听：`80/tcp` 和 `443/tcp`
- UDP Server 业务端口：`9000/udp`
- TCP Server 业务端口：`9100/tcp`

Ubuntu `ufw` 可直接执行：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 9000/udp
sudo ufw allow 9100/tcp
sudo ufw enable
sudo ufw status
```

预期结果：`ufw status` 中能看到 `80/tcp`、`443/tcp`、`9000/udp`、`9100/tcp` 处于允许状态。

如果部署在云服务器，还需要在云安全组中同步放行相同端口：

- `80/tcp`
- `443/tcp`
- `9000/udp`
- `9100/tcp`

说明：`127.0.0.1:8080` 只给本机 Caddy 使用，不需要对公网放开。

## 11. 首次部署验收

完成部署后，按下面顺序验收：

1. 打开 `http://<公网IP>/login` 或 `https://<域名>/login`，确认登录页可访问
2. 使用管理员账号成功登录
3. 打开 `/udp-server` 页面，确认绑定地址为 `0.0.0.0:9000`
4. 打开 `/tcp-server` 页面，确认绑定地址为 `0.0.0.0:9100`
5. 外部设备向 `9000/udp` 发包，确认可以收到自动回复
6. 外部客户端连接 `9100/tcp`，确认页面可看到连接和收发
7. 打开 `/packets` 与 `/logs`，确认可以看到对应记录

重点提醒：页面中的 UDP/TCP 绑定端口、防火墙、云安全组、联调说明必须一致。只要其中一处不一致，就容易出现“页面显示已启动，但外部仍然打不通”的问题。

## 12. 常见故障排查

如果服务无法访问、页面打不开或外部端口不通，按下面顺序排查：

- `journalctl -u packetbench.service -n 100 --no-pager`
  作用：查看应用服务启动失败原因，例如 `.env` 配置错误、依赖未安装、目录权限不足。

- `sudo systemctl status caddy`
  作用：确认反向代理进程是否正常运行。

- `sudo ufw status`
  作用：核对 80/443/9000/9100 是否已经放行。

- `curl -I http://127.0.0.1:8080/login`
  作用：验证应用是否已在本机 `127.0.0.1:8080` 正常监听。

- 检查 `/udp-server` 和 `/tcp-server` 页面中的绑定配置
  作用：确认页面里没有把端口改成和 `ufw`、云安全组不一致的值。

- 检查 `/opt/packetbench` 目录权限
  作用：如果 `packetbench.service` 运行用户是 `www-data`，但目录或 `data`、`logs` 不可写，应用可能启动失败或运行异常。

## 13. 一条现场原则

生产现场不要先改页面端口再去猜防火墙，也不要先放行防火墙再忘记页面绑定。

推荐始终维护一份固定端口表：

- Web: `127.0.0.1:8080`
- UDP Server: `0.0.0.0:9000`
- TCP Server: `0.0.0.0:9100`

页面配置、`ufw`、云安全组、交付清单四处必须一致。

## 14. 交付包清单

交付前至少确认以下内容已准备完毕：

- 当前部署分支名称或代码包版本
- 当前使用的 `.env` 实际部署版本
- `systemd` 服务文件位置与服务名：`/etc/systemd/system/packetbench.service`
- Caddy 配置文件位置与当前生效域名
- 管理员账号交接方式
- 固定端口表
- 验收结果记录
- 回滚时要恢复的上一版代码包或仓库提交信息

建议把以上信息单独截图或整理成一页交付附件，避免现场口头交接后遗漏。

## 15. 部署前信息登记

建议在交付前补齐以下信息，并按现场实际填写：

- 服务器 IP：
- 访问域名：
- 部署目录：`/opt/packetbench`
- Web 监听：`127.0.0.1:8080`
- UDP 端口：`9000/udp`
- TCP 端口：`9100/tcp`
- `systemd` 服务名：`packetbench.service`
- Caddy 配置文件：`/etc/caddy/Caddyfile`
- 管理员账号交接人：
- 云安全组责任人：
- 本次部署代码来源：
- 上一版可回滚版本：

## 16. 现场操作顺序

建议现场按以下顺序操作：

1. 核对服务器 IP、域名、登录方式和 `sudo` 权限
2. 核对代码版本、部署目录和本次目标分支或代码包
3. 核对 `.env`、固定端口表、域名和 Caddy 配置
4. 启动或重启 `packetbench.service`
5. 核对 Caddy 生效状态
6. 核对 `ufw` 与云安全组是否已放行端口
7. 打开登录页并完成最小验收
8. 记录验收结果和交接信息
9. 向接手人明确回滚入口和关键检查命令

## 17. 回滚说明

如果本次部署失败或验收不通过，建议按以下顺序回滚：

1. 记录当前失败现象、时间点和执行到的步骤
2. 停止 `packetbench.service`
3. 恢复上一版代码或上一版部署包
4. 恢复上一版 `.env` 和 Caddy 配置
5. 重新加载 `systemd` 和 Caddy
6. 再次验证登录页和关键端口

可参考命令：

```bash
sudo systemctl stop packetbench.service
sudo systemctl daemon-reload
sudo systemctl restart packetbench.service
sudo systemctl reload caddy
sudo systemctl status packetbench.service
sudo systemctl status caddy
```

说明：当前仓库没有单独的数据库迁移回滚机制，因此不要在现场假设存在额外的自动回滚脚本。回滚应以恢复上一版代码、`.env` 和 Caddy 配置为主。

## 18. 验收记录模板

建议现场直接按下面模板记录：

- 验收时间：
- 验收人员：
- 访问地址：
- 登录结果：通过 / 失败
- UDP 验证结果：通过 / 失败
- TCP 验证结果：通过 / 失败
- 日志检查结果：通过 / 失败
- 服务状态检查结果：通过 / 失败
- 备注：

## 19. 最终交付检查表

- [ ] 文档已更新为现场实际信息
- [ ] `.env` 已按现场配置完成
- [ ] `packetbench.service` 运行正常
- [ ] Caddy 配置已生效
- [ ] 防火墙和云安全组已放行
- [ ] 管理员账号已完成交接
- [ ] 验收记录已填写
- [ ] 回滚入口已向接手人说明
