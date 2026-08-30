# 阶段 1：refactor-analysis（代码重构）—— 阶段卡

> 归属：`docs/iteration/phases/refactor-analysis/`（全局视图见 `docs/iteration/ROADMAP.MD`）。

| 项 | 内容 |
|---|---|
| **阶段目标** | 项目级解耦+重构：行为不变的地基（分层/SSOT/事件/适配器），并完成数据源抽象与体验/Provider 扩展 |
| **边界** | 只动 `windows` + `main` 的 windows 部分；MAC 验证跳过；`docs/iteration/` 仅 windows 分支 |
| **状态** | 🟢 进行中（Sprint-2/3 完成；插队 Sprint-4/5 完成；Sprint-6 F1 完成；插队 Sprint-7 维护批完成） |
| **阶段内文档** | 见下 |

## 文档入口

| 文档 | 内容 |
|---|---|
| [`roadmap.MD`](roadmap.MD) | 阶段 roadmap：**原规划（冻结）** + **实际实录**（含插队登记） |
| [`backlog.MD`](backlog.MD) | 阶段 backlog 卡独立管理（卡号/类型/规模/状态/来源/Sprint 归属） |
| [`refactor-analysis.MD`](refactor-analysis.MD) | 分析文档（问题归类/已确认决策/方法论）——**代码注释与历史文档中的 "refactor-analysis.MD §N" 均指本文件**（2026-08-30 由 `docs/iteration/` 根迁入，内容保持分析定位，规划部分已拆至 roadmap/backlog） |
| `../sprint/` | Sprint 文档（Sprint-2~7；`_template-sprint.md` 为模板） |
| `../embed-optimization.MD` | 性能分析（parse_chunk_embed 提速） |

## 阶段完成与归档约定

- 阶段完成标准：阶段 backlog 全部 DONE/取消，且 `5-VERSIONS.MD` 首次发版登记；
- 完成后本目录**归档封存**（不再新增内容），全局 `ROADMAP.MD` 的 Now 档切至下一阶段，新阶段新建 `docs/iteration/phases/<阶段名>/`。
