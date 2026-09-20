# 阶段 backlog：testing-governance（测试治理）

> 归属：`docs/iteration/phases/testing-governance/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 预研与决策基线：`docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD`（规划时强制注入，见 `1-WORKFLOW.MD` §4.4）。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。
> **卡片来源与时间口径（2026-09-20 用户要求）**：来源带类型前缀 `[规划]`/`[用户插入]`/`[Bug]`/`[走查]`/`[三查]`/`[评审]`；时间字段一律用**网络时间 UTC+8**（`YYYY-MM-DD（UTC+8）`），不得用本机时区（本机 UTC+9）。细则见 `1-WORKFLOW.MD` §3。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| TG-1 | P1 成文规则：DoD+三查增补"用户可见功能必须同 PR 交付 verify case + 矩阵登记"；反例演练留证据 | 1 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D1=A + 底座批次） |
| TG-2 | P2 覆盖矩阵 SSOT：脚本头部元数据 + `verify_matrix.py` 生成/校验 + `verify/TEST-MATRIX.MD` + CI 离线断言 + 全量脚本登记 | 4 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D1=A + 底座批次） |
| TG-3 | P4 ATDD case-first：功能卡模板增"验收 case"节（实现前先写步骤+断言），下一张新功能卡实测；**走查补充（2026-09-10）**：验收 case 须覆盖**完整测试链路 + 边界情况**（≥1 异常/边界输入；不适用须注明理由） | 1 | ✅ 完成（Sprint-15：§2.1 九卡 case 先行实测 + 边界覆盖规则落盘） | Sprint-15 | 用户 2026-08-31（D1=A）+ 走查 2026-09-10 |
| TG-4 | provider e2e 三脚本去漂移：参数化共享基座，修复 verify_e2e_openai 潜在 1.46 bug（D2：本次不做，单独成卡） | 2 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D2 + 底座批次） |
| TG-5 | P3 分层 runner + cron 夜间全量联网套件（fail-closed）。**参数已预决（D3）**：每周一次、单轮预算上限 ¥10、**上限必须可配置（config/env 驱动，不得写死文件）** | 3 | **计划中（Sprint-16）** | 用户 2026-08-31（D3 预决，设计约束入卡）；调研结论 run-047（三态预算闸门） |
| TG-6 | `[用户插入]` **验收方式改进（DoD 补"人机交互验收面" + 过程可见证据 + 规范执行可核查）**：① DoD 现偏代码执行层，需增补"用户可感行为"验收面（交互/呈现/感知）；② 验收指南每条须给**过程可见**的操作与留证（可回放命令 + 原始输出/截图/日志路径，不接受只给结论或"读文档确认"）；③ 机器回归项与人工可感项**分栏标注**（避免把纯脚本断言当人工用例）；④ 建立"Sprint 内规范条目 ↔ 执行记录"抽查机制，治理"规范写了但未执行"的先例 | 3 | 候选 | — | **用户走查 2026-09-20（UTC+8）**：用户明确要求"做个 backlog 卡记录先"；与 `phases/mental-models/` 的 MM-6 联动 |
| TG-7 | `[Bug]` **预算闸门 fail-open**：`scripts/scheduled-tasks.py` 的 `load_state()` 吞掉所有异常并返回默认空状态（line 76–82）→ 状态文件损坏/带 UTF-8 BOM/手工编辑出错时，`last_run` 与成本三态被**静默重置**，预算闸门不再拦截，带预算的任务被放行（与 3-LEARNED 1.54 的 fail-closed 口径直接冲突）。修法：解析失败即 **fail-closed**（非零退出 + 明确文案 + 保留损坏文件副本），并给 `verify_runner.py` 增"损坏 state → 拒绝"断言；顺带标注"本机 PowerShell 5.1 的 `Set-Content -Encoding utf8` 会写 BOM"这一操作陷阱 | 2 | 候选 | — | **走查演示发现 2026-09-20（UTC+8）**（事故实证：BOM 状态文件使 `nightly-suite` 被放行并真实启动，估算损失约 ¥1.0） | `scripts/scheduled-tasks.py:76-82`；`verify/verify_runner.py` |

## 2. 启动条件

- **前置闸门**：F2 用户全盘验收通过（验收发现 8 项已另立 F-AC 批次，见 `2026-08-31-f2-acceptance-findings.MD`）。
- 底座批次（TG-1/TG-2/TG-4）已完成于 Sprint-14；剩余候选 TG-3（case-first）与 TG-5（cron 回归）待排期。
- 开 sprint 时：planning_pipeline 注入预研笔记（`tech/2026-08-31-testing-governance.MD`），既定决策（D1–D4）为基线，不得重议（翻案建议除外）。
