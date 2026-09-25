# F-AC15 **运行参数显式配置面**：把目前只存在于 CLI/env/spec 的参数在**前端显式可见/可配置**。**现状清单

- `card`: F-AC15
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**计划中（Sprint-17，用户 2026-09-21 拍板）**

## 规模
3

## 来源
**用户走查 2026-09-20（UTC+8）**：B-15 存疑；**2026-09-21** 用户要求"9 个 env + spec 阈值具体有哪些"→ 清单已出；同日拍板：**v1 范围按建议（A 研究设置可改 / B 成本与用量只读 / C 数据源与决策只读+可选动作 / D 保持 CLI）**，且 **Sprint-17 需准备不同 use-case 组合供用户人工体验测试**

## Sprint
Sprint-17

## 正文
`[用户插入]` **运行参数显式配置面**：把目前只存在于 CLI/env/spec 的参数在**前端显式可见/可配置**。**现状清单（2026-09-20 审计）**——前端只暴露引擎配置（`/api/config_schema`，7 分组 23 字段）；以下**全部前端不可见**：① `PAPERQA_PROVIDER`（默认服务商）、`PAPERQA_PROVIDERS_JSON`（自定义注册覆盖）；② `PAPERQA_PROVIDER_INTERVAL_DAYS`（provider 刷新周期 14 天）；③ `PAPERQA_NIGHTLY_BUDGET_CNY`（套件预算 10）+ `PAPERQA_SCHEDULE_<TASK>_DAYS`（prices 7 / nightly-suite 7 / providers 14）；④ `PAPERQA_SCHEDULE_STATE`（状态文件路径）；⑤ `PAPERQA_LITELLM_CALLBACK_LIMIT`（回调上限 20，钳制 ≤30）；⑥ `PAPERQA_EMBED_RECOMMEND_LIVE`（embedding 联网实测开关）；⑦ 调研**深度阈值**（`agents/functions/tech-research.md` 可配置参数节 + `fanout.json` depth 路由，CLI `--depth` 仅供校验覆盖）；⑧ 一批纯 CLI 开关（`run_suite --tier/--scripts/--dry-run/--json`、`scheduled-tasks --list/--check-due/--force/--record-cost`、`fetch-prices --apply`、`register-scheduled-tasks.ps1`、`verify_archive --depth`）

## 证据
**详细清单（2026-09-21）**：见 [`2026-09-21-config-surface-inventory.MD`](../2026-09-21-config-surface-inventory.MD)——每个 env 的默认值/读取点/作用、spec 6 项阈值 + 三档档表、state 2 键、CLI 开关 6 组、**7 类硬编码常量（连 env 都没有）**、建议 v1 分区 A/B/C/D
