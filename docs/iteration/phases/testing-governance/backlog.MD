# 阶段 backlog：testing-governance（测试治理）

> 归属：`docs/iteration/phases/testing-governance/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 预研与决策基线：`docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD`（规划时强制注入，见 `1-WORKFLOW.MD` §4.4）。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| TG-1 | P1 成文规则：DoD+三查增补"用户可见功能必须同 PR 交付 verify case + 矩阵登记"；反例演练留证据 | 1 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D1=A + 底座批次） |
| TG-2 | P2 覆盖矩阵 SSOT：脚本头部元数据 + `verify_matrix.py` 生成/校验 + `verify/TEST-MATRIX.MD` + CI 离线断言 + 全量脚本登记 | 4 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D1=A + 底座批次） |
| TG-3 | P4 ATDD case-first：功能卡模板增"验收 case"节（实现前先写步骤+断言），下一张新功能卡实测 | 1 | 候选 | — | 用户 2026-08-31（D1=A） |
| TG-4 | provider e2e 三脚本去漂移：参数化共享基座，修复 verify_e2e_openai 潜在 1.46 bug（D2：本次不做，单独成卡） | 2 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（D2 + 底座批次） |
| TG-5 | P3 分层 runner + cron 夜间全量联网套件（fail-closed）。**参数已预决（D3）**：每周一次、单轮预算上限 ¥10、**上限必须可配置（config/env 驱动，不得写死文件）** | 3 | 候选 | — | 用户 2026-08-31（D3 预决，设计约束入卡） |

## 2. 启动条件

- **前置闸门**：F2 用户全盘验收通过（验收发现 8 项已另立 F-AC 批次，见 `2026-08-31-f2-acceptance-findings.MD`）。
- 底座批次（TG-1/TG-2/TG-4）已完成于 Sprint-14；剩余候选 TG-3（case-first）与 TG-5（cron 回归）待排期。
- 开 sprint 时：planning_pipeline 注入预研笔记（`tech/2026-08-31-testing-governance.MD`），既定决策（D1–D4）为基线，不得重议（翻案建议除外）。
