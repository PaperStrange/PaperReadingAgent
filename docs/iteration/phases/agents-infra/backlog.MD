# 阶段 backlog：agents-infra（卡独立管理）

> 归属：`docs/iteration/phases/agents-infra/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| A-CLOSE | 阶段收口：剩余卡处置（迁出/取消）+ 阶段封存归档 + 全局 ROADMAP 切换 | 1 | ✅ 完成 | Sprint-10（US-10.1，2026-08-31） | 用户 2026-08-31 阶段规划 |
| A-FN | **职能化 agent 划分**：按职能（非分支）定义评审代理，任务参数化（分支=任务输入）；补充调研业界职能划分最佳实践 | 2 | ✅ 完成 | Sprint-8 | 用户修改意见①（2026-08-30） |
| A-UC | **调研结论→用例表**：把四条调研线结论转成可测 use cases（验收断言），Sprint 开发时逐条验证实现遵循调研 | 2 | ✅ 完成 | Sprint-8 | 用户修改意见②（2026-08-30） |
| A-SPEC | 四职能 spec 文件（impact-assessment / code-review / doc-audit / workspace-check 主代理手册，按 A-FN 定稿格式） | 3 | ✅ 完成 | Sprint-8 | 阶段 2 交付物（impact-assessment 为用户问题①后增） |
| A-LEDGER | `scripts/agent-ops.py` 账本 CLI（8 子命令）+ `registry.json` + `runs/` 报告 + `prices.json` | 3 | ✅ 完成 | Sprint-8 | 阶段 2 交付物（§3.2 字段） |
| A-IDE | 跨 IDE 迁移说明（`agents/README.md`）+ 1-WORKFLOW §4.2 三查引用更新 | 1 | ✅ 完成 | Sprint-8 | 阶段 2 交付物 |
| A-DASH | 本地看板应用（Next.js 16 + **antd 6.6.2** + better-sqlite3/FTS5 + chokidar；概览/specs/costs/runs 四页面；端口 8600） | 15（12+US-9.7 插卡 3） | ✅ 完成 | Sprint-9（2026-08-30 关闭；PR #31 合并 cbf93ea） | 阶段 3 交付物（§6）；US-9.7 换栈 antd（Tailwind v4 冲突，issue #56015） |

## 2. 维护卡 / PM 固化备选（用户意见③：可 agent 固化的项目管理过程）

| 卡号 | 主题 | 规模(点) | 状态 | 来源 |
|---|---|---|---|---|
| A-PM1 | 三查执行器 agent 固化：按 spec 自动 fan-out 评审代理 + 账本登记 + 分诊报告 | 3 | 迁出 → refactor-analysis M11（备选） | 用户 2026-08-30 |
| A-PM2 | Sprint 文档模板生成 agent：planning→燃尽→Retro 自动起草（人审后入库） | 2 | 迁出 → refactor-analysis M12（备选） | 用户 2026-08-30 |
| A-PM3 | 调研结论→用例生成 agent 固化（A-UC 的方法论沉淀） | 2 | 迁出 → refactor-analysis M13（备选） | 用户 2026-08-30 |
| A-PM4 | 新 agent 上线评审 agent（职能粒度/权限/spec 合规检查） | 2 | 迁出 → refactor-analysis M14（备选） | 用户 2026-08-30 |
| A-PM5 | ~~经验教训总结 agent~~ → **已落地（2026-08-30）**：`agents/functions/lessons-learned.md` 职能，Sprint 关闭前置必做（1-WORKFLOW §4.1）；主代理审核回填 3-LEARNED | ✅ 完成 | 用户 2026-08-30 |
| A-FANOUT | 看板 fan-out 配置页：可视化编辑 `agents/fanout.json`（五步顺序/运行条件/执行者可调），供用户观察 agent 对开发部署进度影响并调整 | 2 | ✅ 完成 | Sprint-10（US-10.5，2026-08-31；/fanout 页 + /api/fanout GET/PUT/POST） | 用户 2026-08-30（随 Sprint-9 后续） |
| A-M1 | 价表人工覆盖段填充（deepseek/qwen/openrouter 单价，来自服务商页面） | 1 | 迁出 → refactor-analysis M9 | — | 阶段 1 预研；**需用户提供服务商真实单价** |
| A-M2 | ~~评审 spec v1.1 timebox~~ → **已由用户问题①方案取代（2026-08-30）**：新增 impact-assessment 职能（`agents/functions/impact-assessment.md`），审查范围 = recommended_scope（**composite=(0.8A+0.2B)×100，X=50 两档**），不得默认收窄到 Sprint 交付物 | ✅ 完成 | Sprint-8 Retro / 用户问题① |
| A-M3 | main 分支 docs/iteration 悬空引用清理（16 处 pre-existing 行内引用，main 评审发现） | 2 | ✅ 完成 | Sprint-10（US-10.3，2026-08-31）：6 处为注记；另经 018 大小写盲区复核补 3 处"仅 windows"注记 | Sprint-8 二查 |
| A-M4 | agent-ops fetch-spec 成功路径测试（sha256 命中/失配）+ 账本并发锁（last-writer-wins 边界） | 2 | 迁出 → refactor-analysis M10 | — | Sprint-8 二查 nit |
| A-M5 | ~~git/pwsh 环境 SOP~~ → **已完成（2026-08-30）**：AMSI 崩溃重试、push/PR 前 fetch origin/main；**远程分支卫生**（PR 合并后删 `sync/*` 头分支）已补进 workspace-check §步骤3 与 code-review main 同步说明——2026-08-30 用户发现 7 条远程 sync 残留后一次性清理并制度化 | ✅ 完成 | Sprint-8 三查过程 / 用户 2026-08-30 |
| A-M6 | ~~仓库留证文件出库（用户问题②）~~ → **已随 PR #24 完成**：registry.json/runs 报告/截图/静态分析产物 gitignore + 远程同步清理（`.gitignore` 现为 `agents/runtime/registry.json`、`agents/runs/`） | ✅ 完成 | 用户 2026-08-30 |
| A-M7 | **agent spec 模板**（用户 2026-08-30）：`agents/functions/_template-agent.md`（英文）——新增 agent 时复制填写；frontmatter 超集 + 五段式 + 可配置参数节 + 输出模板骨架；**spec 规范演进时模板必须同步更新**（与 A-PM4 上线评审联动） | 1 | ✅ 完成 | 用户 2026-08-30（2026-08-30 落地，随 tech-research 一并上线） |
| A-RS | **深度技术调研 agent（用户 2026-08-30）**：`agents/functions/tech-research.md`——任务含调研要求自动启用（关键词触发），多来源深度调研（≥3 来源/论断 + 对比矩阵 + 结论建议），报告注入上下文后再规划；`fanout.json` 增 `planning_pipeline`（条件/顺序可调）；首跑演示 `run-2026-08-30-tech-research-013`（spec 语言与 skill 描述最佳实践调研） | 2 | ✅ 完成 | 用户 2026-08-30 |
| A-M8 | **main 补齐 windows 历史分叉**（Sprint-9 二查 011 发现）：`paper-qa-script/app/*.py`、`provider_config.py`、`verify/verify_remote_e2e.py` 等核心代码在 windows↔main 存在既存分叉（历史工作项同步遗漏，非 Sprint-9 引入），需专项 PR 按工作项补齐（mac 分支以 main 为源） | 3 | ✅ 完成 | Sprint-10（US-10.2，2026-08-31）：双向差分核查（三点差分为合并基假象）→ 真实分叉仅 5 文件 → PR #35 合并 602e855 后仅余 4 个 mac .sh（有意分叉） | Sprint-9 三查（2026-08-30） |
| A-M9 | better-sqlite3 选型（Sprint-10 US-10.4，tech-research 调研定论）：**维持 v13.0.3**——v13 无 install script、N-API 预编译随包分发（ABI 无关，覆盖 win32/darwin/linux），安装零工具链；`--ignore-scripts` 为防御性空操作保留；翻案条件（迁 node:sqlite 需 Node≥22.16/≥24 LTS + Stability 2.0 + FTS5 等价实测三条件齐备；降级 v12 永不） | 1 | ✅ 完成 | Sprint-10（2026-08-31；调研报告 agents/runs/run-2026-08-31-tech-research-014/） |
| A-M10 | **main 分支保护（GitHub 安全提示跟进，2026-08-30）**：调研最佳实践（[GitHub REST branch protection](https://docs.github.com/rest/branches/branch-protection)、[safeguard.sh 配置指南](https://safeguard.sh/resources/blog/how-to-configure-github-branch-protection-rules)）→ **已应用**：必需 PR 合并（0 approvals——单人/agent 流水线不卡人工评审）、必需状态检查「Offline suite + builds (Windows)」（CI 未绿 API 合并被拒，预期行为）、enforce_admins 开启、禁 force push / 禁删除（restrictions=null）。windows/mac 不保护（工作分支允许历史整理）。 | 1 | ✅ 完成 | GitHub 提示 2026-08-30 |
| A-M11 | `[用户插入]` **Agent workflow 与提示词治理迭代（对照 OpenAI/Anthropic 的 `AGENTS.MD` 实践 + 评估 OpenAI codex harness）**：目标 = **让每个 Agent（含主代理自己）减少甚至不再出现"擅自行动 / 违规行为"**。用户给出的两条方向：① **现有 agent 框架结构对照 OpenAI 与 Anthropic 目前使用的 `AGENTS.MD` 提示词管理方式做更新迭代**；② **借用 OpenAI 开源的 codex harness 工具包管理 agent workflow**。 | 3 | **候选（用户 2026-09-21："这两个方案需要继续调研后再确认怎么做，先记张卡吧"——**本轮只记卡、不实现**）** | Sprint-17 或调研后另开 | **用户插入 2026-09-21（UTC+8）** | **卡内待产出**：<br>① **调研（开卡即触发 `planning_pipeline` 的 tech-research，深度按决策影响取 expert 或 scholar）**：≥3 来源/论断 + 对比矩阵 + 结论建议，并按 M16 归档结构落 `context.md`/`evidence/`/`reasoning.md`：OpenAI 侧 `AGENTS.md` 的分层/作用域/优先级与 Codex 用法；Anthropic 侧 `CLAUDE.md` 与 subagent/技能约定的异同；**codex harness 工具包的定位、能力边界与可复用面**（它解决 workflow 编排的哪一层，与本仓 `agents/fanout.json` + `agent-ops` 账本重叠/互补在哪）。<br>② **现状盘点（规则 vs 闸门）**：把本仓 `agents/functions/*.md`（8 个 spec）、`agents/fanout.json`、`1-WORKFLOW.MD` §3/§4 的条目分成"**只有文字**"与"**有可执行检查点**"两类 —— 直接对应 TG-11 的核心结论"有规则 ≠ 有执行点"。<br>③ **方案对比与建议**：A 仅引入 `AGENTS.md` 式**分层提示词治理**（根/子目录/角色三级 + 冲突优先级）；B 引入 **codex harness** 管理 workflow；C 混合；D 维持现状只补闸门。含成本、兼容性（DSH/多 IDE/CI）、迁移风险，以及"不引入"的正当理由。<br>④ **度量与验收**：把"擅自行动/违规"变成**可观测指标**并逐条给反向对照（示例：未跑〇查即派评审 = 0 次；三查锚点之后未评审提交 = 0；self-chosen scope 无 deviation 声明 = 0；§9 与账本交叉不一致 = 0；规范条目↔执行记录抽查不一致 = 0）。<br>⑤ **与既有卡的分工（避免重复建设）**：`TG-11` = scope 越权的**具体闸门**（证据台账已固化，复盘待做）；`TG-12` = 文档口径漂移的**检测机制**；本卡 = **提示词/框架层**的治理与外部实践对标 —— 建议在 TG-11/TG-12 复盘出结论后再定本卡方案，以免三张卡各自造一套。关联 `3-LEARNED` **1.29**（scope 规则）、**1.61**（部分修复比未修复更危险）、**1.62**（同语义定位须复用同一实现）。 |

> **阶段 2 待用户确认（2026-08-30 暂停）**：用户两个问题（① 审查范围影响评估 + 量化指标 ② 中间态/留证文件出库）已分别落地为 §8/impact-assessment 职能与 A-M6，处理后继续阶段 3（Sprint-9 看板）。

## 3. 已完成归档（示例与速查）

| 卡号 | 主题 | 完成 Sprint |
|---|---|---|
| — | 阶段 1 调研 + 架构地基设计（`architecture.MD`） | 阶段 1（非 Sprint，用户已确认 SQLite 方案） |
