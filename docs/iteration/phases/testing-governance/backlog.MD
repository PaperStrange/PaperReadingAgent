# 阶段 backlog：testing-governance（测试治理）

> 归属：`docs/iteration/phases/testing-governance/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 预研与决策基线：`docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD`（规划时强制注入，见 `1-WORKFLOW.MD` §4.4）。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。
> **卡片来源与时间口径（2026-09-20 用户要求）**：来源带类型前缀 `[规划]`/`[用户插入]`/`[Bug]`/`[走查]`/`[三查]`/`[评审]`；时间字段一律用**网络时间 UTC+8**（`YYYY-MM-DD（UTC+8）`），不得用本机时区（本机 UTC+9）。细则见 `1-WORKFLOW.MD` §6（流程纪律）。

## 1. 功能卡

> 卡正文自 2026-09-23（`TG-14` P1 试点）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| TG-1 | P1 成文规则：DoD+三查增补"用户可见功能必须同 PR 交付 verify case + 矩阵登记"；反例演练留证据 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/TG-1.md](cards/TG-1.md) |
| TG-2 | P2 覆盖矩阵 SSOT：脚本头部元数据 + `verify_matrix.py` 生成/校验 + `verify/TE | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/TG-2.md](cards/TG-2.md) |
| TG-3 | P4 ATDD case-first：功能卡模板增"验收 case"节（实现前先写步骤+断言），下一张新功能卡实测；** | ✅ 完成（Sprint-15：§2.1 九卡 case 先行实测 + 边界覆盖规则落盘） | Sprint-15 | [cards/TG-3.md](cards/TG-3.md) |
| TG-4 | provider e2e 三脚本去漂移：参数化共享基座，修复 verify_e2e_openai 潜在 1.46 bug | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/TG-4.md](cards/TG-4.md) |
| TG-5 | P3 分层 runner + cron 夜间全量联网套件（fail-closed）。**参数已预决（D3）**：每周一次 | ✅ **完成（Sprint-16）** | Sprint-16 | [cards/TG-5.md](cards/TG-5.md) |
| TG-6 | **验收方式改进（DoD 补"人机交互验收面" + 过程可见证据 + 规范执行可核查）**：① DoD 现偏代码执行层， | ✅ 已交付（2026-09-25：C 级棘轮 + 四件套证据规范 + `TG-14`/`TG-7` 补证） | Sprint-17（治理批 G1 = 规则落地） | [cards/TG-6.md](cards/TG-6.md) |
| TG-7 | **预算闸门 fail-open**：`scripts/scheduled-tasks.py` 的 `load_stat | ✅ 完成（2026-09-20 当日闭环） | Sprint-16（走查修复） | [cards/TG-7.md](cards/TG-7.md) |
| TG-8 | **自举后端前端口自检 + 离线开关统一注入**（Retro 行动项 ② 升级为必修）：`verify/e2e_comm | **✅ 完成（2026-09-25，Sprint-17）**：端口自检 + 离线开关（发请求前拒绝）+ 套件 flaky 根因修复；状态与 `cards/TG-8.md` 同步 | Sprint-17（治理批 G1） | [cards/TG-8.md](cards/TG-8.md) |
| TG-9 | **新脚本产物目录约定**（Retro 行动项 ④）：新脚本产物默认写**已忽略目录**（运行态 JSON → `age | **✅ 完成（2026-09-25，Sprint-17 D2）**：`verify/verify_artifact_paths.py` + `policy.json::artifact_paths`；状态与 `cards/TG-9.md` 同步 | Sprint-17（治理批 G1） | [cards/TG-9.md](cards/TG-9.md) |
| TG-10 | **多轮次 agent 的账本记录失真（可观测性缺口）**：同一 run 被追加多轮复核（run-053 共 5 轮）时 | **v1 ✅ 完成（2026-09-21）**；③ 看板 UI 展示待排期 | Sprint-16（v1 已交付）／③ 看板 UI → Sprint-18（G2） | [cards/TG-10.md](cards/TG-10.md) |
| TG-11 | **规则绕过复盘 + 可执行闸门（用户 2026-09-21 定性为"很严重"）**：2026-09-20/21 我以" | **✅ 完成（Sprint-17；状态与 Sprint 看板及 `cards/TG-11.md` 同步，2026-09-25）**：③a/③b/③c 全交付 + 复盘定稿 | Sprint-17（治理批 G1） | [cards/TG-11.md](cards/TG-11.md) |
| TG-12 | **文档内容漂移复盘 + 派生事实机制（用户 2026-09-21："sprint17 和以前的开发过程发现的文档内容漂 | **候选（用户 2026-09-21 要求开卡复盘；同类问题已足够成卡）** | **G3 候选（2026-09-25 D4 裁定从 G2 移出；需先与 `TG-19` M-E 去重再估点）** | [cards/TG-12.md](cards/TG-12.md) |
| TG-13 | **账本"测量化"：时长/轮次/账本↔产物一致性**（用户 2026-09-21 拍板"开新卡"，而非并入 TG-10） | **✅ 完成（2026-09-25，Sprint-17 D3）**：`verify/verify_ledger_measurement.py` + `policy.json::ledger_measurement`；状态与 `cards/TG-13.md` 同步 | Sprint-17（治理批 G1） | [cards/TG-13.md](cards/TG-13.md) |
| TG-14 | **一卡一文档：卡片正文独立成文 + backlog 瘦索引 + 索引 lint**（**由 `TG-12` 机制候选  | **✅ 完成（2026-09-23，D3）** | Sprint-17（治理批 G1） | [cards/TG-14.md](cards/TG-14.md) |
| TG-15 | **闸门泛化：三不变式 + 数据驱动（替换"逐场景加条件"式硬编码）**（用户 2026-09-23 批准 P1="可以 | **✅ 实质完成（Sprint-17 D2；状态与 Sprint 看板及 `cards/TG-15.md` 同步，2026-09-25）**：①~⑤+⑦⑧ 落地；**⑥ 已裁定顺延**（非完成、非待办）；**2.5 点不减**（改扣分条件） | Sprint-17（治理批 G1） | [cards/TG-15.md](cards/TG-15.md) |
| TG-16 | **审查流程与策略内容"整体过一遍" → 图文并茂 HTML 汇报**（用户 2026-09-23："我想需要对现有审查 | **候选（用户 2026-09-23 要求开卡）** | 待排期（建议：素材可在 G1 期间并行收集，**HTML 定稿放 G1 关闭后**——届时的流程图/闸门矩阵才包含 G1 全部落地物；若用户要先看"现状版"，可提前单独出一版并在文件头标注快照日期） | [cards/TG-16.md](cards/TG-16.md) |
| TG-17 | **闸门可信化收尾：覆盖窗口语义 + C1 判定域**（来源＝`TG-15` 独立复核批的两条 finding，用户 2 | **进行中（关闭阻塞项 B1~B4 已修，2026-09-25；用户裁定由 Sprint-18 前移为 Sprint-17 关闭阻塞）** | Sprint-17（治理批 G1，**前移**；原排期 Sprint-18 治理批 G2） | [cards/TG-17.md](cards/TG-17.md) |
| TG-18 | **闸门债：15 处历史表格缺陷逐处清理**（棘轮基线 4 个文件／15 处；review_by=2026-10-31） | **候选** | 待排期（**Sprint-18 候选**） | [cards/TG-18.md](cards/TG-18.md) |
| TG-19 | **关闭税机制化：判定域绑定 / 反空转不变式 / 棘轮完整性 / 关闭税读数派生**（G2 头号机制卡；来源＝关闭期复核的机制缺口 ＋ 〇查 `081` 的四条提案 ＋ 本日实测的"跨 Sprint 窗口翻转"事故） | **进行中（2026-09-25 D1 起交付 M-A/M-B；用户 B4② 排进 G2，本卡为 G2 头号机制卡）** | Sprint-18（治理批 G2）——硬次序：M-A/M-B 必须早于 G2 的任何评审 run | [cards/TG-19.md](cards/TG-19.md) |
| TG-20 | **决策登记册与提问纪律（`docs/6-DECISIONS.md`）**：裁决的单一登记处（原文逐字 ＋ 生效状态 ＋ 证据 ＋ 验证时间戳 ＋ 违背事故引用），并要求主代理提问前先查登记册、提问自带"已裁决项/未覆盖原因/证据" | **进行中（2026-09-25 D1 起交付；用户插入卡，兑现 G2 的插入预留 2 点 ⇒ G2 规划内 12 点、距上限 14 余 2 点）** | Sprint-18（治理批 G2，插入卡） | [cards/TG-20.md](cards/TG-20.md) |

## 2. 启动条件

- **前置闸门**：F2 用户全盘验收通过（验收发现 8 项已另立 F-AC 批次，见 `2026-08-31-f2-acceptance-findings.MD`）。
- 底座批次（TG-1/TG-2/TG-4）已完成于 Sprint-14；TG-3（case-first）完成于 Sprint-15；TG-5（cron 回归/分层 runner）完成于 Sprint-16；走查期新增 TG-6（验收方式改进，候选）、TG-7（预算闸门 fail-closed，✅）、TG-8/TG-9（Sprint-17 计划中）、TG-10（账本多轮次，v1 ✅）、TG-11（规则绕过复盘+闸门，候选）、TG-12（文档内容漂移复盘+派生事实机制，候选，**其机制候选 N7 已于 2026-09-21 提升为独立卡 TG-14**）、TG-13（账本测量化，候选，2026-09-21 用户拍板开卡）、TG-14（一卡一文档结构，候选，2026-09-21 用户拍板）。
- 开 sprint 时：planning_pipeline 注入预研笔记（`tech/2026-08-31-testing-governance.MD`），既定决策（D1–D4）为基线，不得重议（翻案建议除外）。
