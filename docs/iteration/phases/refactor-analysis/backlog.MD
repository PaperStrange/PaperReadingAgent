# 阶段 backlog：refactor-analysis（卡独立管理）

> 归属：`docs/iteration/phases/refactor-analysis/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号（如 `F1`），本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4（Sprint/Bug/维护边界）。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| R-C | C Agent 可观测闭环 + E3 v1 只读可视化（原规划 Sprint-4） | 未估 | ⏸ hold | — | **E3 v1 交付需用户 review** |
| R-E | E1/E2 pip 注入 + 版本检查/更新/回滚（原规划 Sprint-5） | 未估 | ⏸ hold | — | 依赖引擎适配层（已就绪） |
| R-D | D 单机多 worker + 会话外置 + 网关分流（原规划 Sprint-6） | 未估 | ⏸ hold | — | 依赖会话外置化 |
| R-E3 | E3 可编辑工作流（原规划 Sprint-7+） | 未估 | ⏸ hold | — | 依赖 R-C 验收 |
| F1 | 检索体验与查询质量：多语检索 | 13 | ✅ 完成(v1) | Sprint-6 | v1=关键词重试+命中理由；后续：query 翻译/双语索引（F4 评测选型） |
| F2 | 配置面板深化 + SSOT 驱动前端（/api/config_schema + 全字段交互 + 单一受控状态） | 16（分阶段：A 5 + B 6 + C 5） | 🟢 进行中（阶段 A = Sprint-11） | — | 评审 m1 欠账 + m10 遗留；M7 并入；阶段拆解见 Sprint-11 §0 |
| F3 | Agent 接入后端 + 事件时间线雏形 | 未估 | 候选 | — | R-C 的前置步骤 |
| F4 | 本地评测基准（检索/证据/答案三环） | 3(起步) | ✅ 起步 | Sprint-6 | `verify/eval_retrieve.py`；后续扩充语料 |

## 2. 维护卡

| 卡号 | 主题 | 规模(点) | 状态 | 来源 |
|---|---|---|---|---|
| M1 | 索引一致性增强：Tantivy 段损坏探测升级（files.zip + meta.json + tantivy open 三重探针） | 3 | ✅ 完成 | Sprint-7 | `verify/verify_index_health.py`（合成六形态 + 真实构建自愈） |
| M2 | `prune_litellm_callbacks` 上限配置化（env `PAPERQA_LITELLM_CALLBACK_LIMIT`） | 1 | ✅ 完成 | Sprint-7 | `verify_prune_callbacks.py` 覆盖默认/覆盖/非法回落 |
| M3 | staging 清理 UI/自动清理；DOI 源真实 `UNPAYWALL_EMAIL` 实测 | 3 | 候选（用户指示未处理） | — | **Sprint-7 保持未完成**：staging 清理 UI + 真实邮箱实测留待后续 |
| M4 | 多节点并发计时显示；`runStartTimesRef` 清理 | 1 | ✅ 完成 | Sprint-7 | App.jsx subcanvas 计时聚合 + 结束清理；npm build 通过 |
| M5 | `verify_provider_switch` 对 openrouter/自定义连通实测；gui 依赖显式化 | 2 | ✅ 完成 | Sprint-7 | 占位 key 端点级拒绝断言（路由实证）；**真实 openrouter key 实测=用户资源门控**；README 前提显式化 |
| M6 | 文档/知识管理例行勘误（随三查进行） | 1 | 持续 | Sprint-7 | 本轮勘误：verify/README 表格列数错位、README/1-WORKFLOW 清单补全、4-ALGORITHM 行号锚点漂移等 |
| M7 | 默认值漂移收敛：chunk/temperature 等默认值在 config_schema/App.jsx/provider_config/engine 重复 4 处（唯一真源原则） | 3 | 计划中（并入 F2 阶段 A = Sprint-11 US-11.2） | Sprint-7 全量 review | 与 F2（SSOT 驱动前端）同源，已并入 F2 |
| M8 | remote_resolver SSRF DNS rebinding TOCTOU 强化（解析后 IP 复检） | 2 | 候选 | Sprint-7 全量 review | 理论性；现状已有逐跳重定向复检 + 内网段拒绝 |
| M9 | 价表人工覆盖段填充（deepseek/qwen/openrouter 单价）——原 agents-infra A-M1 迁入 | 1 | 候选 | 阶段 1 预研 | **需用户提供服务商真实单价**；填后看板成本口径完整 |
| M10 | fetch-spec 成功路径测试（sha256 命中/失配）+ 账本并发锁——原 agents-infra A-M4 迁入 | 2 | 候选 | Sprint-8 二查 nit | |
| M11 | 三查执行器 agent 固化（fan-out 自动派发 + 账本登记 + 分诊）——原 agents-infra A-PM1 迁入（备选） | 3 | 候选（备选） | 用户 2026-08-30 | fanout.json 已为可调配置，固化执行器属演进项 |
| M12 | Sprint 文档模板生成 agent（planning→燃尽→Retro 自动起草）——原 agents-infra A-PM2 迁入（备选） | 2 | 候选（备选） | 用户 2026-08-30 | |
| M13 | 调研结论→用例生成 agent 固化——原 agents-infra A-PM3 迁入（备选） | 2 | 候选（备选） | 用户 2026-08-30 | |
| M14 | 新 agent 上线评审 agent——原 agents-infra A-PM4 迁入（备选） | 2 | 候选（备选） | 用户 2026-08-30 | 与 `_template-agent.md` 模板联动 |

### 2.1 与 hold 状态的关系

- R-C（C+E3 v1）仍 hold；**若用户先做 F2/F3/F1 后续，E3 v1 的可视化验收闸门（用户 review）不变**。
- R-E/R-D/R-E3 的 hold 不阻塞功能卡 F 系列：F3 即 R-C 的解冻前置步骤；R-E 依赖的引擎适配层已就绪、R-D 依赖会话外置化、R-E3 依赖 R-C 验收。
- 插队/新 Sprint 的启动按 `1-WORKFLOW.MD` §4.4 判定；新卡完成后在 `roadmap.MD` §2 实际实录登记。

## 3. 已完成归档（示例与速查）

| 卡号 | 主题 | 完成 Sprint |
|---|---|---|
| R-A | 配置 SSOT + 策展 schema（原规划 Sprint-2 部分） | Sprint-2 |
| R-B | 数据源抽象（原规划 Sprint-3） | Sprint-3 |
| F-EXT1 | 体验修复 + provider 扩展（插队） | Sprint-4 |
| F-EXT2 | 实战问题修复（插队） | Sprint-5 |
