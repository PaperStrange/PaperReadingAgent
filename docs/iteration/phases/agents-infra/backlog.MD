# 阶段 backlog：agents-infra（卡独立管理）

> 归属：`docs/iteration/phases/agents-infra/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| A-FN | **职能化 agent 划分**：按职能（非分支）定义评审代理，任务参数化（分支=任务输入）；补充调研业界职能划分最佳实践 | 2 | ✅ 完成 | Sprint-8 | 用户修改意见①（2026-08-30） |
| A-UC | **调研结论→用例表**：把四条调研线结论转成可测 use cases（验收断言），Sprint 开发时逐条验证实现遵循调研 | 2 | ✅ 完成 | Sprint-8 | 用户修改意见②（2026-08-30） |
| A-SPEC | 三职能 spec 文件（code-review/doc-audit/workspace-check 主代理手册，按 A-FN 定稿格式） | 3 | ✅ 完成 | Sprint-8 | 阶段 2 交付物 |
| A-LEDGER | `scripts/agent-ops.py` 账本 CLI（8 子命令）+ `registry.json` + `runs/` 报告 + `prices.json` | 3 | ✅ 完成 | Sprint-8 | 阶段 2 交付物（§3.2 字段） |
| A-IDE | 跨 IDE 迁移说明（`docs/agents/README.md`）+ 1-WORKFLOW §4.2 三查引用更新 | 1 | ✅ 完成 | Sprint-8 | 阶段 2 交付物 |
| A-DASH | 本地看板应用（Next.js+SQLite+shadcn/ui，六页面，端口 8600） | 8 | 候选 | Sprint-9（规划） | 阶段 3 交付物（§6） |

## 2. 维护卡 / PM 固化备选（用户意见③：可 agent 固化的项目管理过程）

| 卡号 | 主题 | 规模(点) | 状态 | 来源 |
|---|---|---|---|---|
| A-PM1 | 三查执行器 agent 固化：按 spec 自动 fan-out 评审代理 + 账本登记 + 分诊报告 | 3 | 候选（备选） | 用户 2026-08-30 |
| A-PM2 | Sprint 文档模板生成 agent：planning→燃尽→Retro 自动起草（人审后入库） | 2 | 候选（备选） | 用户 2026-08-30 |
| A-PM3 | 调研结论→用例生成 agent 固化（A-UC 的方法论沉淀） | 2 | 候选（备选） | 用户 2026-08-30 |
| A-PM4 | 新 agent 上线评审 agent（职能粒度/权限/spec 合规检查） | 2 | 候选（备选） | 用户 2026-08-30 |
| A-M1 | 价表人工覆盖段填充（deepseek/qwen/openrouter 单价，来自服务商页面） | 1 | 候选 | 阶段 1 预研 |

## 3. 已完成归档（示例与速查）

| 卡号 | 主题 | 完成 Sprint |
|---|---|---|
| — | 阶段 1 调研 + 架构地基设计（`architecture.MD`） | 阶段 1（非 Sprint，用户已确认 SQLite 方案） |
