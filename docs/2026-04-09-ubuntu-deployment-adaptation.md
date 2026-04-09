# 2026-04-09 Ubuntu Deployment Adaptation

本文用于 `PacketBench v0.1.0` 在 Ubuntu 22.04/24.04 上的落地部署，重点解决以下问题：

- 明确服务器当前公网 IP 的获取方式
- 固定 Web / TCP / UDP 监听端口，避免页面配置、应用监听、防火墙放行不一致
- 提供可直接套用的 Caddy 配置示例

## 1. 获取服务器当前公网 IP

在 Ubuntu 服务器上执行以下任一命令：

```bash
curl -4 ifconfig.me
```

或：

```bash
curl -4 https://api.ipify.org
```

如果服务器安装了 `ip` 工具，也可以先看本机网卡地址：

```bash
ip addr
```

说明：

- `curl -4 ifconfig.me` / `curl -4 https://api.ipify.org` 返回的是服务器对外可见的公网 IP
- `ip addr` 返回的是服务器本机网卡地址，云服务器场景下可能是内网地址，不一定等于公网 IP

建议将查到的公网 IP 记录下来，用于：

- DNS 解析核对
- 临时 IP 访问验收
- 云安全组和外部设备联调说明

## 2. 固定本次部署的监听端口

建议在本次部署中先固定以下端口，不要一边修改 Web 页面配置，一边忘记同步防火墙：

- Web 应用监听：`127.0.0.1:8080`
- Caddy 对外监听：`80/tcp` 和 `443/tcp`
- UDP Server 业务端口：`9000/udp`
- TCP Server 业务端口：`9100/tcp`

建议原则：

- `8080` 只给本机 Caddy 反代使用，不对公网直接放开
- `9000/udp` 和 `9100/tcp` 如果要给外部设备使用，就保持页面配置与防火墙放行一致
- 在没有明确变更单前，不要临时改成别的端口

## 3. 推荐环境变量

`.env` 建议至少设置为：

```env
APP_ENV=production
WEB_HOST=127.0.0.1
WEB_PORT=8080
SESSION_SECURE=true
```

如果当前还未启用 HTTPS，只能临时改为：

```env
SESSION_SECURE=false
```

## 4. 业务端口与页面配置对齐要求

部署后首次登录时，请立即核对页面中的实际监听配置：

### UDP Server

- 页面：`/udp-server`
- 建议绑定：`0.0.0.0:9000`

### TCP Server

- 页面：`/tcp-server`
- 建议绑定：`0.0.0.0:9100`

说明：

- 如果设备需要从外部访问服务器，`bind_ip` 推荐保持 `0.0.0.0`
- 如果页面里把端口改成了别的值，必须同步修改：
  - Ubuntu 防火墙
  - 云安全组
  - 现场联调说明

## 5. 防火墙放行清单

如果本次部署使用推荐端口，Ubuntu `ufw` 可直接执行：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 9000/udp
sudo ufw allow 9100/tcp
sudo ufw enable
sudo ufw status
```

云服务器场景下，还需要在云安全组中同步放行：

- `80/tcp`
- `443/tcp`
- `9000/udp`
- `9100/tcp`

## 6. 部署后端口一致性检查

上线后请按顺序检查：

1. `.env` 中 Web 监听是否为 `127.0.0.1:8080`
2. `/udp-server` 页面是否为 `0.0.0.0:9000`
3. `/tcp-server` 页面是否为 `0.0.0.0:9100`
4. `ufw status` 是否已放行 `9000/udp` 和 `9100/tcp`
5. 云安全组是否同步放行相同端口

只要以上任一项不一致，就很容易出现：

- 页面显示已启动，但外部设备打不通
- 本机联调正常，公网联调失败
- TCP 通，UDP 不通，或反之

## 7. Caddy 配置示例

### 域名 + HTTPS

将域名解析到服务器公网 IP 后，`/etc/caddy/Caddyfile` 可使用：

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

生效命令：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy
```

### 只有公网 IP 的临时访问

如果当前没有域名，只做临时验收，可使用：

```caddy
:80 {
    encode gzip zstd

    reverse_proxy 127.0.0.1:8080
}
```

说明：

- 这种方式通常只有 HTTP，没有自动 HTTPS 证书
- 适合先验收页面、登录和运行态功能，不适合作为长期正式生产方案

## 8. systemd 与运行检查

```bash
sudo cp systemd/app.service /etc/systemd/system/packetbench.service
sudo systemctl daemon-reload
sudo systemctl enable --now packetbench.service
sudo systemctl status packetbench.service
```

查看服务日志：

```bash
journalctl -u packetbench.service -n 100 --no-pager
```

查看应用日志：

```bash
tail -f /opt/packetbench/logs/app.log
```

## 9. 最终验收建议

1. 访问 `http://<公网IP>/login` 或 `https://<域名>/login`
2. 登录后确认 `/udp-server` 和 `/tcp-server` 页面绑定端口与部署清单一致
3. 外部设备向 `9000/udp` 发包，确认 UDP 自动回复正常
4. 外部客户端连接 `9100/tcp`，确认 TCP Server 可见连接和收发
5. 在 `/packets` 和 `/logs` 中确认日志落库

## 10. 一条部署原则

生产现场不要先改页面端口再去猜防火墙，也不要先放行防火墙再忘记页面绑定。

推荐做法是始终维护一份固定端口表：

- Web: `127.0.0.1:8080`
- UDP Server: `0.0.0.0:9000`
- TCP Server: `0.0.0.0:9100`

页面配置、`ufw`、云安全组、联调说明四处必须一致。
