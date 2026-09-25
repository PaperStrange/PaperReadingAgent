# 阶段 backlog：agents-infra（卡独立管理）

> 归属：`docs/iteration/phases/agents-infra/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。

## 1. 功能卡

> 卡正文自 2026-09-24（`TG-14` P3）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| A-CLOSE | 阶段收口：剩余卡处置（迁出/取消）+ 阶段封存归档 + 全局 ROADMAP 切换 | ✅ 完成 | Sprint-10（US-10.1，2026-08-31） | [cards/A-CLOSE.md](cards/A-CLOSE.md) |
| A-FN | **职能化 agent 划分**：按职能（非分支）定义评审代理，任务参数化（分支=任务输入）；补充调研业界职能划分最佳实 | ✅ 完成 | Sprint-8 | [cards/A-FN.md](cards/A-FN.md) |
| A-UC | **调研结论→用例表**：把四条调研线结论转成可测 use cases（验收断言），Sprint 开发时逐条验证实现遵循 | ✅ 完成 | Sprint-8 | [cards/A-UC.md](cards/A-UC.md) |
| A-SPEC | 四职能 spec 文件（impact-assessment / code-review / doc-audit / wo | ✅ 完成 | Sprint-8 | [cards/A-SPEC.md](cards/A-SPEC.md) |
| A-LEDGER | `scripts/agent-ops.py` 账本 CLI（8 子命令）+ `registry.json` + `run | ✅ 完成 | Sprint-8 | [cards/A-LEDGER.md](cards/A-LEDGER.md) |
| A-IDE | 跨 IDE 迁移说明（`agents/README.md`）+ 1-WORKFLOW §4.2 三查引用更新 | ✅ 完成 | Sprint-8 | [cards/A-IDE.md](cards/A-IDE.md) |
| A-DASH | 本地看板应用（Next.js 16 + **antd 6.6.2** + better-sqlite3/FTS5 + c | ✅ 完成 | Sprint-9（2026-08-30 关闭；PR #31 合并 cbf93ea） | [cards/A-DASH.md](cards/A-DASH.md) |

## 2. 维护卡 / PM 固化备选（用户意见③：可 agent 固化的项目管理过程）

> 卡正文自 2026-09-24（`TG-14` P3）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| A-PM1 | 三查执行器 agent 固化：按 spec 自动 fan-out 评审代理 + 账本登记 + 分诊报告 | 迁出 → refactor-analysis M11（备选） | — | [cards/A-PM1.md](cards/A-PM1.md) |
| A-PM2 | Sprint 文档模板生成 agent：planning→燃尽→Retro 自动起草（人审后入库） | 迁出 → refactor-analysis M12（备选） | — | [cards/A-PM2.md](cards/A-PM2.md) |
| A-PM3 | 调研结论→用例生成 agent 固化（A-UC 的方法论沉淀） | 迁出 → refactor-analysis M13（备选） | — | [cards/A-PM3.md](cards/A-PM3.md) |
| A-PM4 | 新 agent 上线评审 agent（职能粒度/权限/spec 合规检查） | 迁出 → refactor-analysis M14（备选） | — | [cards/A-PM4.md](cards/A-PM4.md) |
| A-PM5 | ~~经验教训总结 agent~~ → **已落地（2026-08-30）**：`agents/functions/les | ✅ 完成 | — | [cards/A-PM5.md](cards/A-PM5.md) |
| A-FANOUT | 看板 fan-out 配置页：可视化编辑 `agents/fanout.json`（五步顺序/运行条件/执行者可调），供 | ✅ 完成 | Sprint-10（US-10.5，2026-08-31；/fanout 页 + /api/fanout GET/PUT/POST） | [cards/A-FANOUT.md](cards/A-FANOUT.md) |
| A-M1 | 价表人工覆盖段填充（deepseek/qwen/openrouter 单价，来自服务商页面） | 迁出 → refactor-analysis M9 | — | [cards/A-M1.md](cards/A-M1.md) |
| A-M2 | ~~评审 spec v1.1 timebox~~ → **已由用户问题①方案取代（2026-08-30）**：新增 im | ✅ 完成 | Sprint-8 Retro / 用户问题① | [cards/A-M2.md](cards/A-M2.md) |
| A-M3 | main 分支 docs/iteration 悬空引用清理（16 处 pre-existing 行内引用，main 评审 | ✅ 完成 | Sprint-10（US-10.3，2026-08-31）：6 处为注记；另经 018 大小写盲区复核补 3 处"仅 windows"注记 | [cards/A-M3.md](cards/A-M3.md) |
| A-M4 | agent-ops fetch-spec 成功路径测试（sha256 命中/失配）+ 账本并发锁（last-writer | 迁出 → refactor-analysis M10 | — | [cards/A-M4.md](cards/A-M4.md) |
| A-M5 | ~~git/pwsh 环境 SOP~~ → **已完成（2026-08-30）**：AMSI 崩溃重试、push/PR  | ✅ 完成 | Sprint-8 三查过程 / 用户 2026-08-30 | [cards/A-M5.md](cards/A-M5.md) |
| A-M6 | ~~仓库留证文件出库（用户问题②）~~ → **已随 PR #24 完成**：registry.json/runs 报告 | ✅ 完成 | — | [cards/A-M6.md](cards/A-M6.md) |
| A-M7 | **agent spec 模板**（用户 2026-08-30）：`agents/functions/_template | ✅ 完成 | — | [cards/A-M7.md](cards/A-M7.md) |
| A-RS | **深度技术调研 agent（用户 2026-08-30）**：`agents/functions/tech-resea | ✅ 完成 | — | [cards/A-RS.md](cards/A-RS.md) |
| A-M8 | **main 补齐 windows 历史分叉**（Sprint-9 二查 011 发现）：`paper-qa-scrip | ✅ 完成 | Sprint-10（US-10.2，2026-08-31）：双向差分核查（三点差分为合并基假象）→ 真实分叉仅 5 文件 → PR #35 合并 602e855 后仅余 4 个 mac .sh（有意分叉） | [cards/A-M8.md](cards/A-M8.md) |
| A-M9 | better-sqlite3 选型（Sprint-10 US-10.4，tech-research 调研定论）：**维持 | ✅ 完成 | Sprint-10（2026-08-31；调研报告 agents/runs/run-2026-08-31-tech-research-014/） | [cards/A-M9.md](cards/A-M9.md) |
| A-M10 | **main 分支保护（GitHub 安全提示跟进，2026-08-30）**：调研最佳实践（[GitHub REST  | ✅ 完成 | — | [cards/A-M10.md](cards/A-M10.md) |
| A-M11 | **Agent workflow 与提示词治理迭代（对照 OpenAI/Anthropic 的 `AGENTS.MD`  | **进行中（2026-09-25 D6：① 调研 run `run-2026-09-25-tech-research-084` 完成、② 规则↔执行点盘点与 ④ 指标已交付；③ 已给结论、⑤ 待 G3 复盘）——原"候选（只记卡、不实现）"已被 `D-250925-04`/`D-250925-06` 取代（就地标注，2026-09-25 D6）** | Sprint-18（治理批 G2；含 MM 并行线的交叉用例） | [cards/A-M11.md](cards/A-M11.md) |
| A-M12 | **编辑边界事故族治理：写入前体检 + 标题层检测**（由 Sprint-17 内 5 次真实事故提炼；用户 2026-09-23 要求成卡） | **进行中（2026-09-25 D4 交付判据 ①：结构守卫"不可跳过层"——git 基线档 ＋ pre-commit 钩子 ＋ CI 接线 ＋ 机检接线；判据 ④ 的度量读数仍待 Sprint-18 关闭时统计）** | Sprint-18（治理批 G2，与 `A-M11`/`TG-17` 同批） | [cards/A-M12.md](cards/A-M12.md) |
| A-M13 | **实现类 run 的账本 role（`implementation` spec）＋ 在飞宽限**（来源＝`TG-17` 证据⑤：实现工作挂评审 role 会污染 C1 判定域） | **进行中（2026-09-25 D2 交付 spec ＋ 判据侧 ②③ ＋ 机检；首次真实使用 = `run-2026-09-25-implementation-082`）** | Sprint-18（治理批 G2）——硬次序：先于 `TG-17` 的 C1 判定域定稿 | [cards/A-M13.md](cards/A-M13.md) |

> ✅ **阶段 2 已确认并闭环（2026-09-21 更正陈旧注记，TG-12 实例）**：原注记写"**待用户确认（2026-08-30 暂停）**……处理后继续**阶段 3（Sprint-9 看板）**"，该状态**早已过期**——① 两个问题已分别落地为 §8/impact-assessment 职能与 A-M6；② **阶段 3 看板亦已完成**（`A-DASH` ✅ Sprint-9、`A-FANOUT` ✅ Sprint-10）；③ 本阶段 **2026-08-31 已归档封存**（ROADMAP 行可核）。→ 属"**封存阶段的行动注记未随事实更新**"（用户 2026-09-21 指出），已按 `TG-12` 实例登记；全仓扫描确认这是唯一一处该型陈旧注记。

## 3. 已完成归档（示例与速查）

> 本节是**归档速查表**（非卡索引）：`—` 行是阶段 1 的归档占位，**不是卡、不建卡文件**（`TG-14` 硬约束 ⑥ 的显式处置，迁移时原样保留）。

| 卡号 | 主题 | 完成 Sprint |
|---|---|---|
| — | 阶段 1 调研 + 架构地基设计（`architecture.MD`） | 阶段 1（非 Sprint，用户已确认 SQLite 方案） |
