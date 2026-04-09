# AI Maintenance Guide

本文档用于约束 `PacketBench` 仓库的日常维护方式，目标读者是仓库所有者本人和在本仓库内工作的 AI 智能体。

这不是产品说明，而是维护规则。

## 1. 仓库分工

当前仓库采用以下分工：

- `master`
  - 通用产品主线
  - 保持代码、文档和默认配置尽量通用
  - 不承载现场部署特化约束
- `release/ubuntu-v0.1.0`
  - Ubuntu 交付分支
  - 允许维护 Ubuntu 相关部署说明、固定端口建议、防火墙清单、Caddy 示例等交付内容
- `archive/*`
  - 历史归档分支
  - 只用于保留旧语义和历史实现，不回写当前主线

## 2. 当前已确认的产品边界

维护时默认以下结论已经成立，不应被 AI 随意改回：

- 项目名为 `PacketBench`
- 当前产品版本为 `v0.1.0`
- UDP 当前语义是固定自动回复单模式
- 旧 UDP relay / cloud 双模式语义只保留在归档分支

如果后续要改变这些边界，必须是明确的产品决策，不应由 AI 自行推断。

## 3. 分支使用规则

### 改 `master` 的内容

以下内容优先进入 `master`：

- 通用功能开发
- 通用 bugfix
- 测试修复与覆盖增强
- 不依赖特定部署环境的文档更新
- 不带现场假设的默认配置调整

### 改 `release/ubuntu-v0.1.0` 的内容

以下内容优先进入 Ubuntu 交付分支：

- Ubuntu 专属部署步骤
- 固定端口表
- `ufw` / 云安全组说明
- 公网 IP 获取说明
- Caddy 站点配置示例
- 现场验收清单

### 不要做的事

- 不把 Ubuntu 现场约束直接堆进 `master`
- 不把某一台服务器、某一个客户环境的特化设置写进主线
- 不把归档分支中的旧 UDP 语义带回主线

## 4. 推荐维护流程

### 通用功能或通用修复

1. 从 `master` 开始
2. 修改代码和测试
3. 在 `master` 验证通过后提交
4. 如需发布，再打产品版本 tag

### Ubuntu 交付改动

1. 切到 `release/ubuntu-v0.1.0`
2. 只修改 Ubuntu 交付相关文档或示例配置
3. 不把这些部署特化内容反向污染 `master`
4. 如需对外提供交付基线，可在该分支上打独立 tag

### 主线修复同步到 Ubuntu 分支

如果主线出现通用 bugfix，需要同步到 Ubuntu 分支，推荐：

1. 先在 `master` 完成修复并验证
2. 切到 `release/ubuntu-v0.1.0`
3. 使用 `git cherry-pick <commit>` 同步所需提交
4. 再在 Ubuntu 分支补跑对应验证

## 5. AI 智能体工作约束

AI 在本仓库内工作时，默认必须遵守以下规则：

1. 先检查当前分支，再决定修改落点
2. 如果当前改动是 Ubuntu 交付特化，不应直接提交到 `master`
3. 不恢复旧 UDP relay / cloud 语义
4. 不随意更改项目名、版本号、cookie 名、部署路径、systemd 服务名，除非用户明确要求
5. 不擅自修改远端地址、tag、发布分支策略，除非用户明确要求
6. 提交前必须运行与改动范围相匹配的验证命令
7. 如果发现工作区中有不是自己产生的改动，默认不要回退

## 6. 文档维护规则

默认文档职责如下：

- `README.md`
  - 产品总览
  - 本地运行
  - 通用部署入口
- `docs/2026-04-09-development-status.md`
  - 当前开发快照
- `docs/2026-04-09-delivery-test-guide.md`
  - 当前交付测试说明
- `docs/ai-maintenance-guide.md`
  - 仓库维护规则和 AI 工作约束

规则：

- `README.md` 不应该无限膨胀成现场操作手册
- 细化部署策略优先写到专门文档里
- 历史文档保留即可，不要拿历史文档覆盖当前状态

## 7. 版本与发布规则

- 产品版本使用 `vX.Y.Z`
- 当前版本是 `v0.1.0`
- 产品 tag 以主线版本为准，例如 `v0.1.0`
- 如果 Ubuntu 交付需要独立标记，可以考虑额外使用类似 `ubuntu-v0.1.0` 的 tag

AI 不应在没有明确要求时自行打 tag 或创建 release。

## 8. 常用命令备忘

查看分支：

```bash
git branch --list
```

切到主线：

```bash
git switch master
```

切到 Ubuntu 交付分支：

```bash
git switch release/ubuntu-v0.1.0
```

把主线修复同步到 Ubuntu 分支：

```bash
git switch release/ubuntu-v0.1.0
git cherry-pick <commit>
```

查看当前工作区：

```bash
git status --short --branch
```

推送主线：

```bash
git push origin master
```

推送 Ubuntu 分支：

```bash
git push origin release/ubuntu-v0.1.0
```

推送 tag：

```bash
git push origin v0.1.0
```

## 9. 一条总规则

如果一个改动带有“特定环境、特定机器、特定交付对象”的假设，就优先考虑是否应该放到专门分支，而不是直接进入 `master`。

对本仓库来说，默认答案是：

- 通用能力进 `master`
- Ubuntu 现场适配进 `release/ubuntu-v0.1.0`
