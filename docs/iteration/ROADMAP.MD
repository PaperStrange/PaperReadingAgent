# ROADMAP.MD —— 全局路线图（Now / Next / Later 三档）

> 归属：`docs/iteration/`（**仅 windows 分支**维护）。
> 方法论：三档承诺度（[Now/Next/Later](https://www.ideaplan.io/templates/now-next-later-template)）+
> 滚动式规划（[GAO 滚动式规划指南](https://guides.gaoinnovations.gov/schedule-guide/rolling-wave-planning.html)）：
> **Now 细化到 Sprint 序列；Next 为主题级候选；Later 为远期方向**。细节一律下沉到阶段文档（`phases/<阶段>/`）。
> 工作边界判定见 `../1-WORKFLOW.MD` §4.4；发版规范见 `../5-VERSIONS.MD`。

## Now（当前阶段，细化）

| 阶段 | 入口 | 状态 | 当前 Sprint 序列 |
|---|---|---|---|
| **refactor-analysis（代码重构）** | [`phases/refactor-analysis/README.MD`](phases/refactor-analysis/README.MD) | 🟢 进行中（**Now 档唯一 active 阶段**） | Sprint-2 ✅ · Sprint-3 ✅ · 插队 Sprint-4 ✅ · 插队 Sprint-5 ✅ · Sprint-6(F1) ✅ · 插队 Sprint-7(维护批) ✅ · Sprint-10（收口+跨平台债）✅ · **Sprint-11（F2 阶段 A，进行中）** |
| **agents-infra（AgentOps 基础设施）** | [`phases/agents-infra/README.MD`](phases/agents-infra/README.MD) | ✅ **已归档封存（2026-08-31，只读）** | 阶段1 ✅ · Sprint-8 ✅（PR #23）· Sprint-9 ✅（PR #31 cbf93ea）；剩余卡迁出至 refactor-analysis M9~M14 |

- 阶段内 roadmap（原规划冻结 + 实际实录）：[`phases/refactor-analysis/roadmap.MD`](phases/refactor-analysis/roadmap.MD)
- 阶段内 backlog 卡：F1✅(v1)/**F2（进行中：阶段 A=Sprint-11）**/F3/F4✅(起步)、R-C/R-E/R-D/R-E3（hold）、M1~M8（M1/M2/M4/M5✅、M3 用户指示未处理、M6 持续、**M7 已并入 F2**、M8 候选）+ **M9~M14（agents-infra 收口迁入）**

## Next（已确定方向的候选，主题级）

| 主题 | 说明 | 依赖 |
|---|---|---|
| F1 后续 | query 翻译/双语索引（用 F4 评测选型） | F4 基准扩充 |
| F2 阶段 B/C（Sprint-12/13） | 全字段交互 + impacts 切换前提示 + 完全 schema 驱动 + 同步脚本 | 阶段 A 完成 |
| F3 Agent 接入 + 时间线雏形 | R-C 前置步骤 | 事件模型（已就绪） |
| R-C（解冻候选） | C 可观测 + E3 v1 只读可视化 | ⏸ hold：用户 review 闸门（backlog 卡 R-C） |

## Later（远期主题）

| 主题 | 说明 |
|---|---|
| R-E（E1/E2） | pip 注入 + 版本检查/更新/回滚 |
| R-D | 单机多 worker + 会话外置 + 网关分流 |
| R-E3 | 可编辑工作流（编排 DSL/配置 + 执行器） |

## 阶段与文档管理规则

1. **两级 roadmap**：全局（本文件，三档+阶段索引）↔ 阶段（`phases/<阶段>/roadmap.MD`，原规划冻结+实际实录）。
2. **Backlog 卡独立管理**：每阶段 `backlog.MD` 独立登记卡（卡号/类型/规模/状态/来源）；Sprint 文档引用卡号。
3. **阶段收口**：阶段 backlog 全 DONE/取消 + 首次发版登记（`5-VERSIONS.MD`）→ 阶段目录归档封存，Now 档切换至下一阶段，新阶段新建目录。
4. **判定与版本**：开不开 Sprint 按 `1-WORKFLOW.MD` §4.4；每 Sprint 关闭前执行三查（同 §4.2）。
