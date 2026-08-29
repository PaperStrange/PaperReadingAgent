# 重构分析与问题归类（前置动作 · Sprint-2 输入）

> 归属：`docs/iteration/`（迭代增量文档）。本文档固化"项目级解耦+重构"的决策与问题归类，
> 作为 Sprint-2（前置重构）的规划输入。配套 Sprint 文档：`docs/iteration/sprint/2026-08-29-sprint-2.md`。

## 1. 范围与完成标准（已确认）

- **范围**：仅更新 `windows` 与 `main` 分支的 windows 部分；**MAC 版验证跳过**。
- **完成标准**：**结构解耦、行为不变**——重构不掺新功能；以回归证据（全链路/冒烟/API 实测）证明行为一致。
- **原则**：Single source of truth / Type safety / Consistent patterns / Easy maintenance；
  执行中不局限于这四条，可吸收外部重构最佳实践（[Strangler Fig 渐进重构](https://lobehub.com/skills/spacholski1225-cc-config-strangler-fig-pattern#1)、
  [特征化测试：先测后改](https://qaskills.sh/blog/testing-legacy-code-refactoring-guide)、
  [消除全局可变状态](https://github.com/antosubash/simple_module_python/blob/7bd73f61e374941fbea94d67ad15518342cb5274/docs/plans/2026-04-13-eliminate-global-mutable-db-state-design.md#1)、
  [FastAPI 会话依赖注入](https://github.com/fastapi/sqlmodel/blob/ad0766fe3ed40d8880af8fece48616d70d6809ff/docs/tutorial/fastapi/session-with-dependency.md#1)、
  [Clean Architecture 参考](https://github.com/gwynz/fastapi-clean-architecture#2)）。

## 2. 目标分层架构

```
表现层 UI          ReactFlow / Streamlit         只展示与交互，不实现逻辑
API 服务层         FastAPI REST + SSE            薄：协议/路由/校验
应用编排层         Pipeline / Agent 编排         6 节点流程、Agent 流程状态机、事件流
引擎适配层         paperqa EngineAdapter（接口）  屏蔽 vendor/pip 注入、版本、多代理框架
基础设施           会话/缓存/事件总线/任务队列     弹性与可观测底座（先单机多 worker）
```

四条原则的落点：

- **SSOT**：paperqa `Settings`（pydantic）为配置唯一真源 → 派生**策展 schema**（见 §4 Q2），后端校验、前端表单、文档全部从它生成/引用。
- **Type safety**：后端全面 pydantic（请求/响应/事件/配置/schema 元数据）；前端由 schema 驱动表单（JSON 校验）。
- **Consistent patterns**：所有"步骤"统一 `Step`/`Event` 抽象（普通节点、Agent 内部工具、未来的 Summarize 节点复用同一事件模型）；所有注入点走同一 Adapter 接口。
- **Easy maintenance**：vendor 目录与业务代码彻底隔离；DI 替代全局可变状态；契约/特征化测试保行为。

## 3. 问题归类（7 个问题 → 5 个主题域）

| # | 原始问题 | 主题域 | 根因 | 依赖 |
|---|---|---|---|---|
| 前端1 | config 未覆盖全 + 缺分组 + 缺切换提示 | **A 配置模型（SSOT）** | 手写参数子集，无 schema、无"字段→下游影响"元数据 | —（地基） |
| 前端2 | load_index 数据源写死本地绝对路径 | **B 数据源抽象** | `paper_directory` 单一假设；未暴露 `aadd_url`/manifest/搜索源 | A+C 的编排层 |
| 前端3 | Agent 流程不透明、失败无感、无一手证据 | **C 可观测性与证据** | 事件模型缺失；错误未结构化上报 | 事件模型（地基） |
| 后端1 | 支撑上述特性 | 横切 | 编排/API 层能力不足 | 随各主题 |
| 后端2 | 弹性 + LB + 分流 | **D 基础设施弹性** | 单进程 + 内存会话 | 会话外置 + 事件模型 |
| 大模型1 | 多代理框架切换 + pip 注入 | **E1 框架适配层** | 无 Adapter 接口，`pip install -e ./paper-qa` 写死 | —（地基） |
| 大模型2 | 版本检查/手动/自动更新 | **E2 框架生命周期** | 版本 pin 散落注释，无检测/回滚 | E1 |
| 大模型3 | Agent 可视化 + 可编辑工作流 | **E3 工作流编排（最大）** | 工作流硬编码在 paperqa tools；无编排模型 | E1 + C；分多 Sprint |

## 4. 已确认决策（2026-08-29 与需求方对齐）

| 问题 | 决策 |
|---|---|
| Q1 完成标准 | 结构解耦、行为不变；MAC 验证跳过；只更新 windows + main 的 windows 部分 |
| Q2 配置形态 | **方案 B：手工策展 schema 作为唯一真源 + 自动渲染**（维护成本分析见下） |
| Q3 工作流 | 采用**可编辑工作流**方向，多 Sprint 交付；**先交付 v1 只读可视化**，验收通过后再迭代；**v1 交付后需用户 review，未通过不进入下一步** |
| Q4 基础设施 | 先**单机多 worker**，再扩展**简单多机**（低并发，单服务器三位数级并发请求）；分流 = **API 网关路由**，避免多模型抢占同一后端资源 |

### Q2 维护成本展开说明

策展 schema 的"维护成本"主要来自：paperqa `Settings` 升级时，策展字段/分组/提示需人工同步。

- 属**代码复杂度成本 → 可接受，并从技术架构上优化**：不手工维护两份字段——用脚本从 `Settings.model_json_schema()` **自动抽取字段/类型/默认值**，策展层只维护**覆盖项**（分组、中文标签、`impacts` 影响提示、可见性）。升级时跑一次同步脚本 + 一个 diff 检查（CI 校验）即可，把人工同步降到最小。
- 属**用户体验成本 → 不可接受，必须做好**：schema 驱动的表单必须有**友好报错**（字段级错误、配置不合法时的清晰提示、SSOT 缺失/失配时的引导文案），"影响提示"（如切换 embedding → 需重新下载模型/重建索引；切换 reader → 需重建索引）要在用户切换**之前**可见，而不是报错后才解释。

## 5. 方法论（吸收的外部实践）

- **Strangler Fig**：不推倒重写。每次从一个模块（会话、事件、配置）切一小块到新抽象，旧调用原地保留至切完，全程可运行。
- **特征化测试（回归锚点）**：先固化现有行为（`verify_smoke`/`verify_embed_load`/e2e + 关键 API 输入输出快照），每步重构后必跑，作为"行为不变"的证据。
- **DI 替代全局可变状态**：`SESSIONS` 全局字典 → `SessionStore` 接口 + 内存实现，路由经依赖注入取得（为多 worker/多机铺路）。
- **分层契约**：每层边界用 pydantic 类型表达（请求/响应/事件/配置），层间只依赖契约，不依赖实现。

## 6. Sprint 序列（Roadmap）

| Sprint | 目标 |
|---|---|
| **Sprint-2（本前置重构）** ✅ 已完成（2026-08-29） | 地基：配置 SSOT（策展 schema 生成器+覆盖层）、编排层解耦、事件模型、SessionStore、EngineAdapter 接口；全程行为不变（证据见 `sprint/2026-08-29-sprint-2.md` §7） |
| Sprint-3 ✅ 已完成（2026-08-29） | B 数据源抽象（本地目录/URL/manifest/论文ID 多源）+ 前端切换 UI（证据与双分支 code review 见 `sprint/2026-08-29-sprint-3.md` §7/§9） |
| Sprint-4 | C Agent 可观测闭环（结构化事件→时间线）+ 一手证据（原始错误/trace_id）→ 交付 E3 v1 **只读可视化**，验收后再迭代；**v1 需用户 review，通过后方可继续** |
| Sprint-5 | E1/E2 pip 注入 + 版本检查/更新/回滚 |
| Sprint-6 | D 单机多 worker + 会话外置 + 网关分流；之后评估简单多机 |
| Sprint-7+ | E3 可编辑工作流（编排 DSL/配置 + 执行器） |

> Sprint-2 落地结果（分层映射）：`app/config_schema.py`（配置 SSOT）、`app/orchestration.py`（编排）、`app/engine.py`（引擎适配）、`app/events.py`（事件模型）、`app/session_store.py`（SessionStore）；`backend/main.py` 已瘦身为纯路由层（~190 行，7 条 API 路由不变）。
> Sprint-3 落地结果：`app/data_sources.py`（数据源领域模型）+ `app/remote_resolver.py`（arXiv/DOI/URL → `data/remote/<index_name>/` 暂存，复用索引/解析管线）+ 前端 `DataSourcePanel.jsx`（Config 节点切换 UI）；local 默认行为不变（回归为证）。
>
> **当前状态（2026-08-29）**：Sprint-4~7+ 全部 **hold**；E3 工作流可视化 v1 交付后**需用户 review**（Q3 闸门）。双分支 code review 已完成，发现与修复闭环见 `sprint/2026-08-29-sprint-3.md` §9。
