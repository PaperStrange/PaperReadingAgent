# 阶段 2：agents-infra（AgentOps 基础设施）—— 阶段卡

> 归属：`docs/iteration/phases/agents-infra/`（全局视图见 `docs/iteration/ROADMAP.MD`）。
> 用户批准的三阶段方案（2026-08-30）：① 调研+架构地基 → ② 四职能 spec（impact-assessment / code-review / doc-audit / workspace-check 主代理手册）+ 账本 + 跨 IDE 说明 → ③ 本地看板应用。

| 项 | 内容 |
|---|---|
| **阶段目标** | 把"多子代理并行评审/开发"制度化为可复用基础设施：agent spec 文件 + runtime 账本 + 本地看板；为未来新增更多 agent、以及 paper-qa workflow 引用 agent 能力打地基 |
| **边界** | 稳定交付物（`agents/` spec、`agents-dashboard/` 应用、`scripts/agent-ops.py` 账本工具）随分支同步 main；本阶段规划/分析/调研文档仅 windows 分支 |
| **状态** | 🟢 进行中（阶段 1 ✅；Sprint-8 = 阶段1修订 + 阶段2，见 `../sprint/2026-08-30-sprint-8.md`） |
| **阶段内文档** | 见下 |

## 文档入口

| 文档 | 内容 |
|:--|:--|
| [`architecture.MD`](architecture.MD) | **阶段 1 产出**：调研结论（业界最佳实践）+ 架构地基设计（agent 定义格式/账本数据模型/fan-out 协议/看板技术栈） |
| `../sprint/` | 本阶段 Sprint 文档（阶段 2/3 各一个 Sprint） |

## 阶段完成与归档约定

- 阶段 2 完成：`agents/functions/` 四职能 spec（impact-assessment 闸门 + code-review/doc-audit + workspace-check 主代理手册）+ `scripts/agent-ops.py` + `1-WORKFLOW.MD` §4.2 三查改为引用固定 spec；
- 阶段 3 完成：看板支持 spec 编辑 / skill URL 配置 / runtime 展示（自报+估算）/ memory 报告浏览，并跑通一次真实 fan-out 演示；
- 完成后本目录归档封存，全局 `ROADMAP.MD` 状态更新。
