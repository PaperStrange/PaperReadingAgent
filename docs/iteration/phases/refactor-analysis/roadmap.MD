# 阶段 roadmap：refactor-analysis（原规划冻结 + 实际实录）

> 归属：`docs/iteration/phases/refactor-analysis/`。全局三档视图见 `../../ROADMAP.MD`。
> 规则：**原规划一经制定即冻结**（§1 不改写）；执行情况只记入 §2 实际实录（滚动式规划：近期细化、远期主题）。

## 1. 原规划（2026-08-29 制定，冻结）

| Sprint | 目标 |
|---|---|
| **Sprint-2（前置重构）** | 地基：配置 SSOT（策展 schema 生成器+覆盖层）、编排层解耦、事件模型、SessionStore、EngineAdapter 接口；全程行为不变 |
| Sprint-3 | B 数据源抽象（本地目录/URL/manifest/论文ID 多源）+ 前端切换 UI |
| Sprint-4 | C Agent 可观测闭环（结构化事件→时间线）+ 一手证据（原始错误/trace_id）→ 交付 E3 v1 **只读可视化**，验收后再迭代 |
| Sprint-5 | E1/E2 pip 注入 + 版本检查/更新/回滚 |
| Sprint-6 | D 单机多 worker + 会话外置 + 网关分流；之后评估简单多机 |
| Sprint-7+ | E3 可编辑工作流（编排 DSL/配置 + 执行器） |

## 2. 实际实录（随迭代更新）

> 与原始规划的对应关系在此维护；插队 Sprint 一律记录"插队"来源。E3 v1 交付后**需用户 review**（Q3 闸门）保持不变。

| 实际 Sprint | 日期 | 内容（对应原始规划） | 状态 |
|---|---|---|---|
| Sprint-2 | 2026-08-29 | 前置重构（=原 Sprint-2）：分层/SSOT/事件/SessionStore/EngineAdapter，行为不变（证据 `../sprint/2026-08-29-sprint-2.md`） | ✅ 完成 |
| Sprint-3 | 2026-08-29 | B 数据源抽象（=原 Sprint-3）+ 双分支 code review（`../sprint/2026-08-29-sprint-3.md`） | ✅ 完成 |
| Sprint-4（插队） | 2026-08-30 | 体验修复 + provider 扩展（不在原规划，用户实测驱动）：光标草稿态、`\\?\` 长路径/索引自愈、OpenRouter+自定义 provider、`/api/providers`、样式统一、ModelConfigPanel（`../sprint/2026-08-30-sprint-4.md`） | ✅ 完成 |
| Sprint-5（插队） | 2026-08-30 | 实战问题修复（不在原规划）：自动重跑 config、retrieve 去重与来源标记、litellm 回调上限防护、SSE 断连静默、UI 三件套（`../sprint/2026-08-30-sprint-5.md`） | ✅ 完成 |
| Sprint-6（新增候选 F1） | 2026-08-30 | 检索体验：多语检索 v1 + F4 评测基准起步（`../sprint/2026-08-30-sprint-6.md`） | ✅ 完成 |
| Sprint-7（插队·维护批） | 2026-08-30 | 清技术账：M1 索引三重探针 / M2 回调上限 env 配置 / M4 并发计时+清理 / M5 verify 路由实证+gui 依赖显式化 / M6 文档勘误 + 关闭前全量 code review（`../sprint/2026-08-30-sprint-7.md`）；M3 按用户指示保持未完成 | ✅ 完成 |
| Sprint-10（收口+跨平台债） | 2026-08-31 | agents-infra 阶段归档封存（剩余卡迁出 M9~M14）；A-M8 分叉核查（三点差分假象 → 双向差分仅 4 个 mac .sh 有意分叉）；A-M3 悬空引用；A-M9 better-sqlite3 决策（维持 v13）；A-FANOUT 看板 fan-out 配置页（`../sprint/2026-08-31-sprint-10.md`） | ✅ 完成 |
| Sprint-11（F2 阶段 A） | 2026-08-31 | 配置 SSOT 端点（`/api/config_schema` + `/api/config/validate`，路由 8→10、impact spec v1.4.0）；M7 默认值收敛锁（verify_config_schema 104 断言）；前端 schema 只读清单（`../sprint/2026-08-31-sprint-11.md`） | ✅ 完成 |
| Sprint-12（F2 阶段 B） | 2026-08-31 | SchemaForm 全字段交互表单（23 字段类型控件/防抖字段级校验/impacts 切换前可见/provider 联动），取代 ModelConfigPanel/DataSourcePanel/SchemaFieldList；gui_check_s4/remote 选择器更新（`../sprint/2026-08-31-sprint-12.md`） | ✅ 完成 |
| 原 Sprint-4（C + E3 v1 只读可视化） | — | 结构化事件→时间线 + 工作流只读可视化 v1 | ⏸ hold（v1 需用户 review） |
| 原 Sprint-5（E1/E2） | — | pip 注入 + 版本检查/更新/回滚 | ⏸ hold |
| 原 Sprint-6（D） | — | 单机多 worker + 会话外置 + 网关分流 | ⏸ hold |
| 原 Sprint-7+（E3 可编辑） | — | 编排 DSL/配置 + 执行器 | ⏸ hold |

## 3. 落地映射（分层）

`app/config_schema.py`（SSOT）、`app/orchestration.py`（编排）、`app/engine.py`（引擎适配）、`app/events.py`（事件）、`app/session_store.py`（会话）、`app/data_sources.py`+`app/remote_resolver.py`（数据源）、`app/embedding_recommender.py`（embedding 推荐）；`backend/main.py` 纯路由层（10 条 API 路由）；前端 `SchemaForm.jsx`（schema 驱动全字段表单，Sprint-12 起取代 ModelConfigPanel/DataSourcePanel）交互面板。
