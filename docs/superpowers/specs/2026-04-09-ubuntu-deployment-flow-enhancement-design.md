# Ubuntu Deployment Flow Enhancement Design

## Goal

优化 Ubuntu 部署与交付准备手册，补充实际可执行的项目获取与部署动作，覆盖 Git 拉取和压缩包上传两种路径，并让交付人员可以按明确顺序完成代码落盘、环境准备、服务启动与验收。

## Scope

- 继续以 `docs/2026-04-09-ubuntu-deployment-adaptation.md` 作为唯一主手册。
- 在手册前半部分补充 Git 拉取流程和压缩包部署流程。
- 把现有部署步骤整理成更明确的动作顺序，减少交付现场的自行推断。
- 更新 `docs/INDEX.md` 中 Ubuntu 文档描述，使其与手册实际职责一致。
- README 仅保留入口，不重复详细部署动作。

## Approaches

### Option 1: Git 为主，压缩包为备

正文先写 Git 拉取和后续更新，再补充无 Git 环境时的压缩包替代方案。

Pros:
- 最利于后续维护、升级和回滚。
- 兼顾无法直连 GitHub 的现场。

Cons:
- 需要在文档中明确两种路径的适用场景。

### Option 2: 双主流程并列

从代码准备开始就完全并列写两套步骤。

Pros:
- 信息完整。

Cons:
- 正文会变长，读者更容易走错分支。

### Option 3: 压缩包为主，Git 为补充

正文按交付包操作写，Git 作为补充说明。

Pros:
- 贴近纯交付现场。

Cons:
- 不利于后续版本更新和问题追踪。

## Recommendation

采用 Option 1。Git 流程作为主路径最利于持续维护，压缩包流程作为现场备选最符合交付需求。

## Document Changes

主手册新增或强化以下内容：

1. Git 首次拉取流程
2. Git 后续更新流程
3. 压缩包上传与解压流程
4. 如何确认当前部署代码版本
5. 更明确的部署动作顺序

`docs/INDEX.md` 仅做最小调整：

- 将 Ubuntu 文档描述改成“Ubuntu 部署与交付准备手册”

## Validation

- 重新读取目标文档，确认中文内容正常。
- 确认手册同时包含 Git 和压缩包两种获取方式。
- 保持现有文档相关测试通过。
