# 阶段 backlog：mental-models（思维模型库）

> 归属：`docs/iteration/phases/mental-models/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 预研与决策基线：`docs/iteration/pre-research/tech/2026-09-07-mental-models.MD`（规划时强制注入，见 `1-WORKFLOW.MD` §4.4）。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。**阶段性质（用户 2026-09-07）**：独立工程项目——经验文档（3-LEARNED）→ 抽象思维模型架构；成功判据 = 模型能直接生成可执行 agent workflow。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| MM-1 | 模型 schema 与库结构：统一字段（名称/版本/描述/使用时机/边界/输入/输出/创始人/来源/成功判据/状态）+ `library/` 目录 + 种子模型「思维实验」v0.1 入库 | 2 | 候选 | — | 用户 2026-09-07（Q1 独立阶段；Q2 补全草案接受） |
| MM-2 | **半自动生成器**：模型 JSON → spec 骨架（schema 字段 → 五段式映射；**robust**=字段缺失降级+validate 前置+失败可解释，**flexible**=字段可扩展+人工可改+schema 演进兼容） | 3 | 候选 | — | 用户 2026-09-07（Q3：robust & flexibility 为硬约束） |
| MM-3 | 种子模型实例化首跑：思维实验 → `agents/functions/thought-experiment.md` + validate-spec + 首跑演示（三方案比对文档） | 2 | 候选 | — | 用户 2026-09-07 |
| MM-4 | 经验文档→候选模型提取 SOP：主代理主管，每次 3-LEARNED 更新时执行，产出候选模型卡（来源标注条目号） | 1 | 候选 | — | 用户 2026-09-07（来源③） |
| MM-5 | 自适应触发扩展机制：初始边界（讨论输入）→ 认可反馈后扩展至其他决策场景；每次扩展记录 + 用户确认 | 1 | 候选 | — | 用户 2026-09-07（种子模型使用时机） |

合计 **9 点**（建议首段 = MM-1+MM-2+MM-3，7 点；MM-4/MM-5 随第二阶段）。

## 2. 启动条件

- 排期意向：refactor-analysis 的 Sprint-15/16 之后启动本阶段（独立 sprint 序列，不与 refactor-analysis 并行——保持 Now 档单 active 阶段约定）。
- 启动时按 §4.4 判定 + planning_pipeline 注入预研笔记（既定决策：Q1 独立阶段 / Q2 种子补全 / Q3 半自动+robust+flexible 为基线）。
