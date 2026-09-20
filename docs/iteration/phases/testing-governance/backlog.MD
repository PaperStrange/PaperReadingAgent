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
| TG-6 | `[用户插入]` **验收方式改进（DoD 补"人机交互验收面" + 过程可见证据 + 规范执行可核查）**：① DoD 现偏代码执行层，需增补"用户可感行为"验收面（交互/呈现/感知）；② 验收指南每条须给**过程可见**的操作与留证（可回放命令 + 原始输出/截图/日志路径，不接受只给结论或"读文档确认"）；③ 机器回归项与人工可感项**分栏标注**（避免把纯脚本断言当人工用例）；④ 建立"Sprint 内规范条目 ↔ 执行记录"抽查机制，治理"规范写了但未执行"的先例；⑤ **反向对照规则（用户 2026-09-21 拍板，称"倒过来试试"）**：新增的交互/GUI 检查**必须先在未修复/旧实现上跑出 FAIL**（证明该检查确实能触发目标失效模式），再在修复后转 PASS——反例：`gui_check_s5/s7` 用程序化 `.click()` 结构上无法触发 F-AC13 | 3 | 候选 | — | **用户走查 2026-09-20（UTC+8）**：用户明确要求"做个 backlog 卡记录先"；**2026-09-21** 追加反向对照规则；与 `phases/mental-models/` 的 MM-6 联动 |
| TG-7 | `[Bug]` **预算闸门 fail-open**：`scripts/scheduled-tasks.py` 的 `load_state()` 吞掉所有异常并返回默认空状态（line 76–82）→ 状态文件损坏/带 UTF-8 BOM/手工编辑出错时，`last_run` 与成本三态被**静默重置**，预算闸门不再拦截，带预算的任务被放行（与 3-LEARNED 1.54 的 fail-closed 口径直接冲突）。修法：解析失败即 **fail-closed**（非零退出 + 明确文案 + 保留损坏文件副本），并给 `verify_runner.py` 增"损坏 state → 拒绝"断言；顺带标注"本机 PowerShell 5.1 的 `Set-Content -Encoding utf8` 会写 BOM"这一操作陷阱 | 2 | ✅ 完成（2026-09-20 当日闭环） | Sprint-16（走查修复） | **走查演示发现 2026-09-20（UTC+8）**（事故实证：BOM 状态文件使 `nightly-suite` 被放行并真实启动，估算损失约 ¥1.0） | **证据**：`load_state` fail-closed（`utf-8-sig` 容忍 BOM + `.corrupt` 副本 + 退出 2）；`verify_runner.py` **24 断言全 PASS**（⑩a 截断→拒 2 + 留副本 / ⑩b 带 BOM 合法状态照常读到并 REFUSED / ⑩c 顶层非对象→拒 2）；BOM 反证由 RUN 转 REFUSED(4)；教训入 `3-LEARNED` 1.58 |
| TG-8 | `[用户插入]` **自举后端前端口自检 + 离线开关统一注入**（Retro 行动项 ② 升级为必修）：`verify/e2e_common.py` 的 `wait_healthy` **只探测端口、不校验"服务是不是自己启的"** → dev 后端在跑时脚本会**静默复用**它并施加 parse/embed 负载；反之套件也会抢占/顶掉 dev 后端（2026-09-20 走查实证：后端两次消失）。修法：① 自举前探测端口占用 → 占用即 **fail-fast** 并提示"请先停 dev 服务或改用其他端口"（**不复用**）；② 退出时只回收自己拉起的进程；③ 统一注入 `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1`（避免 HEAD 重试阻塞）；④ 回归：占用端口下脚本必须明确失败而非静默复用 | 2 | **计划中（Sprint-17，用户 2026-09-21 确认）** | Sprint-17 | **Retro 行动项 ②（Sprint-16）+ 用户 2026-09-21 确认进 S17** | 事故记录见 Sprint-16 §10 与验收指南 §13.5；教训 `3-LEARNED` 1.55 / 1.60 |
| TG-9 | `[用户插入]` **新脚本产物目录约定**（Retro 行动项 ④）：新脚本产物默认写**已忽略目录**（运行态 JSON → `agents/runtime/`、日志/截图 → 已 gitignore 的 `verify/*.log|png`、临时结果 → `%TEMP%`），并在 `verify/README.md` 与 `1-WORKFLOW.MD` 写明"新增脚本前先确认产物路径已忽略"；配套：`.gitignore` 增补运行态文件清单 | 1 | **计划中（Sprint-17，用户 2026-09-21 确认）** | Sprint-17 | **Retro 行动项 ④（Sprint-16）+ 用户 2026-09-21 确认进 S17** | 本轮两次误入库（`verify_checkpoint_run.log`、`ci_fail_log.txt`）已被清理并 gitignore |

## 2. 启动条件

- **前置闸门**：F2 用户全盘验收通过（验收发现 8 项已另立 F-AC 批次，见 `2026-08-31-f2-acceptance-findings.MD`）。
- 底座批次（TG-1/TG-2/TG-4）已完成于 Sprint-14；剩余候选 TG-3（case-first）与 TG-5（cron 回归）待排期。
- 开 sprint 时：planning_pipeline 注入预研笔记（`tech/2026-08-31-testing-governance.MD`），既定决策（D1–D4）为基线，不得重议（翻案建议除外）。
