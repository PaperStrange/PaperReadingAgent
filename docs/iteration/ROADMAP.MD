# ROADMAP.MD —— 全局路线图（Now / Next / Later 三档）

> 归属：`docs/iteration/`（**仅 windows 分支**维护）。
> 方法论：三档承诺度（[Now/Next/Later](https://www.ideaplan.io/templates/now-next-later-template)）+
> 滚动式规划（[GAO 滚动式规划指南](https://guides.gaoinnovations.gov/schedule-guide/rolling-wave-planning.html)）：
> **Now 细化到 Sprint 序列；Next 为主题级候选；Later 为远期方向**。细节一律下沉到阶段文档（`phases/<阶段>/`）。
> 工作边界判定见 `../1-WORKFLOW.MD` §4.4；发版规范见 `../5-VERSIONS.MD`。

## Now（当前阶段，细化）

| 阶段 | 入口 | 状态 | 当前 Sprint 序列 |
|---|---|---|---|
| **refactor-analysis（代码重构）** | [`phases/refactor-analysis/README.MD`](phases/refactor-analysis/README.MD) | 🟢 进行中（**Now 档唯一 active 阶段**） | Sprint-2 ✅ · Sprint-3 ✅ · 插队 Sprint-4 ✅ · 插队 Sprint-5 ✅ · Sprint-6(F1) ✅ · 插队 Sprint-7(维护批) ✅ · Sprint-10（收口+跨平台债）✅ · Sprint-11（F2 阶段 A）✅ · Sprint-12（F2 阶段 B）✅ · Sprint-13（F2 阶段 C）✅ · Sprint-14（底座批次）✅ · **Sprint-15（F2 验收修复·交互类）✅（PR #49，2026-09-10 验收通过关闭）** · **Sprint-16（数据准确性+成本韧性+调研工作流深化，2026-09-12 启动，19 点）⏸ HOLD（用户 2026-09-21 决定）：四卡 DONE（19/19）+ 三查闭环 + workspace-check 通过；走查（09-20）未通过 0 项，走查发现全部闭环，Retro③ 成本计量 + F-AC16/M18 v1 落地；因后续改动（F-AC13/14 修复、F-AC15 配置面、est 系数可配置等）将新增测试项与代码变更，**原三查结论需更新** → 待改动落地后重跑三查，再建 PR → 合并 → 关闭；新增卡 F-AC13~F-AC17/M18/TG-6~TG-9/MM-6（其中 F-AC13/14/15、TG-8/9 进 Sprint-17）** |
| **agents-infra（AgentOps 基础设施）** | [`phases/agents-infra/README.MD`](phases/agents-infra/README.MD) | ✅ **已归档封存（2026-08-31，只读）**；**例外：2026-09-21 用户插入 `A-M11`（Agent workflow 与提示词治理迭代：对照 OpenAI/Anthropic 的 `AGENTS.MD` 实践 + 评估 OpenAI codex harness；**只记卡、待调研后再确认方案**）** | 阶段1 ✅ · Sprint-8 ✅（PR #23）· Sprint-9 ✅（PR #31 cbf93ea）；剩余卡迁出至 refactor-analysis M9~M14 |

- 阶段内 roadmap（原规划冻结 + 实际实录）：[`phases/refactor-analysis/roadmap.MD`](phases/refactor-analysis/roadmap.MD)
- 阶段内 backlog 卡：F1✅(v1)/**F2 ✅（阶段 A=Sprint-11、B=Sprint-12、C=Sprint-13 全完成，转用户验收）**/F3/F4✅(起步)、R-C/R-E/R-D/R-E3（hold）、M1~M8（M1/M2/M4/M5✅、M3 用户指示未处理、M6 持续、**M7 已并入 F2**、M8 候选）+ **M9~M14（agents-infra 收口迁入）** + **F-AC13~F-AC16（2026-09-20 走查新增：点击失响应 / 复制状态串台 / 运行参数显式配置面 / checkpoint 可见性与可复现）、M18（报告时效治理）**
- **📋 治理批规划草案（G1/G2/G3，2026-09-21，用户四项口径后成稿，待审定）**：[`sprint/2026-09-21-governance-batch-plan.MD`](sprint/2026-09-21-governance-batch-plan.MD) —— **先立规则**（TG-11 闸门 / TG-6 验收面+反向对照 / TG-13 账本测量化 / TG-14 一卡一文档 / TG-8 / TG-9）→ **载体与验证可信度**（A-M11 ① 分层提示词 / ② 四列映射表 / ⑧ 验证可信度 / ⑨ 接管判据 / ⑩ 报告↔run 绑定 + TG-12 派生事实机制）→ **观察与度量 + MM 启动**（三指标 + 红线即死 + 双盲抽查 + 插入卡成本记录）；**用户已定：拆多 Sprint 实现；达标压缩为三指标 + 红线即死（文件丢失/卡片漂移/测试假绿）；`code major` 须含"人类读得懂"标准（参考 Google Python Style Guide）；抽查由主代理按双盲执行、判断类升级用户二次检查**。

## Next（已确定方向的候选，主题级）

| 主题 | 说明 | 依赖 |
|---|---|---|
| F1 后续 | query 翻译/双语索引（用 F4 评测选型） | F4 基准扩充 |
| F3 Agent 接入 + 时间线雏形 | R-C 前置步骤 | 事件模型（已就绪） |
| R-C（解冻候选） | C 可观测 + E3 v1 只读可视化 | ⏸ hold：用户 review 闸门（backlog 卡 R-C） |
| **mental-models（思维模型库，独立阶段·工程项目）** | 经验文档（3-LEARNED）→ 抽象思维模型架构；成功判据 = 模型可直接生成可执行 agent workflow；种子=思维实验（爱因斯坦）；**MM-6（2026-09-20 用户插入）：把各阶段思考固化为思维实验并用于"生产环境"（含验收/讨论/决策），与本轮走查暴露的"规范未执行/过程不可见"挂钩** | 阶段目录已建（[`phases/mental-models/backlog.MD`](phases/mental-models/backlog.MD)，MM-1~MM-6 共 11 点）；排期意向=refactor-analysis Sprint-15/16 之后启动；预研基线 `pre-research/tech/2026-09-07-mental-models.MD` |
| 走查修复批次（候选插队） | 2026-09-20 走查产出：F-AC13（运行按钮点击 1~2 次无响应）、F-AC14（复制按钮状态串台）、TG-7（预算闸门 fail-open）；按 `1-WORKFLOW.MD` §3 插队判定（≥3 同源问题或 >8 点）决定是否成批 | 用户确认修复取舍与排期 |
| testing-governance（测试治理） | e2e 测试与功能演进同步治理：成文规则(TG-1) + 覆盖矩阵 SSOT(TG-2) + ATDD case-first(TG-3) + provider 去漂移(TG-4) + 定时回归(TG-5) | **底座批次 ✅ 完成（Sprint-14，PR #48）**：TG-1/2/4 + M15 领域治理壳 + M10 账本并发锁 + M14 上线评审 + M9 价表自动抓取；剩余候选 TG-3（case-first）与 TG-5（cron 回归，参数已预决）见 [`phases/testing-governance/backlog.MD`](phases/testing-governance/backlog.MD)；**新增 TG-6（验收方式改进：DoD 补人机交互验收面 + 过程可见证据 + 规范执行可核查，用户插入 2026-09-20）、TG-7（预算闸门 fail-open 修复，走查实证 2026-09-20）、TG-8/TG-9（自举端口自检 / 产物目录约定，Sprint-17）、TG-10（账本多轮次记录失真，v1 ✅）、TG-11（规则绕过复盘 + 可执行闸门，用户插入 2026-09-21）、TG-12（文档内容漂移复盘 + 派生事实机制，用户插入 2026-09-21）** |

## Later（远期主题）

| 主题 | 说明 |
|---|---|
| R-E（E1/E2） | pip 注入 + 版本检查/更新/回滚 |
| R-D | 单机多 worker + 会话外置 + 网关分流 |
| R-E3 | 可编辑工作流（编排 DSL/配置 + 执行器） |

## 阶段与文档管理规则

1. **两级 roadmap**：全局（本文件，三档+阶段索引）↔ 阶段（`phases/<阶段>/roadmap.MD`，原规划冻结+实际实录）。
2. **Backlog 卡独立管理**：每阶段 `backlog.MD` 独立登记卡（卡号/类型/规模/状态/来源）；Sprint 文档引用卡号。
3. **阶段收口**：阶段 backlog 全 DONE/取消 + 首次发版登记（`5-VERSIONS.MD`）→ 阶段目录归档封存，Now 档切换至下一阶段，新阶段新建目录。
4. **判定与版本**：开不开 Sprint 按 `1-WORKFLOW.MD` §4.4；每 Sprint 关闭前执行三查（同 §4.2）。
