# 6. 决策登记册（clarification questions 与用户裁决的唯一登记处）

> **定位**：本文件是**用户裁决**（含"裁决式答复"、口径裁定、原话要求）的**唯一登记处**。任何其它文档（计划书、Sprint 文档、卡片、复盘）**引用裁决时只引条目号**，不复制原文；原文只存在这里。
> **读法**：主代理在向用户提问前**必须先查本表**（见 §2 提问纪律）；用户核对时看 `原文（逐字）` 与 `生效状态` 两栏即可。
> **原文与归纳的分离规则（用户 2026-09-25 要求，逐字见 §0）**：`原文（逐字）` 区块**只放逐字引用**（保留错别字、标点、空格原样）；主代理的一切归类、影响判断、状态判定一律写在**独立的** `主代理归纳` 行。**同一段落里不得混排**。
> **状态词表（受控）**：`生效` / `已被取代` / `失效` / `待裁定` / `进行中`。被取代的条目**必须就地标注** `[已被 <条目号> 取代（日期）]`，且取代方条目必须存在。
> **证据纪律**：`证据` 必须是**可复跑或可定位**的东西（`path:line` / 提交 sha / run id / 命令 + 现跑输出）；`验证时间戳` 记**最后一次按证据核对**的网络时间（UTC+8）；**拿不出证据就写 `未验证（待补）`，不得留空、不得编造**。

## 0. 本文件的由来（用户要求，原文逐字）

> 原文（逐字）："我们之间的对话中把所有clarification questions找时间收集整理下，原记录放在D:\All-Downloads\PaperReading\PaperReading-Windows\docs\6-DECISIONS.md中，除了原记录和违背抉择的事故引用外（引用事故记录文档），还要标记生效状态和证据，验证时间戳。把这个新增一张卡吗，每次你问我问题不带上下文的时候我就得翻我们的对话记录，还得提醒你是不是之前做过类似确认/是不是缺少啥内容，我已经厌倦了这么做"
> 原文（逐字）："注意还原事实，原文必须保留，原文和你自己总结/归类的内容做清晰区分"

- 主代理归纳：新增卡片 [`TG-20`](iteration/phases/testing-governance/cards/TG-20.md)（用户插入卡，兑现 G2 插入预留 2 点）；本文件为该卡交付物 ①；提问纪律为交付物 ②（条文入 `1-WORKFLOW.MD` §6 第 9 条）。
- **进展（2026-09-25 D1）**：交付物 ① 已完成到「**全量分层并入**」——§3 本会话裁决 **11 条**（逐字；**D1 时点数**——D6 新增 `D-250925-12` 后现为 **12 条**，现值以 §3 的小节数/闸门读数为准）＋ §4.0 首批已核 8 条（含证据与时间戳）＋ **§4.1 逐字原话 103 条（全收）** ＋ **§4.3 附录索引 282 条**（未判定效力）；交付物 ② 已落条文；**③ 机检判据 / ④ 反向对照 / ⑤ 实战复算 待 D6**；§4.2（二手转述中判定为「仍生效」者）按批次回填（用户裁定 R1）。
- **进展（2026-09-25 D6）**：交付物 **③④⑤ 已交付**——新闸门 `verify/verify_decision_register.py` 按 `TG-20` 卡 ③ 的五条判据实现（(i) 字段齐全／(ii) 受控状态词／(iii) 被取代须指向存在的条目／(iv) 出处必须是 `path:line` 或显式"会话"形态／(v) 原文块不得混排归纳标记词），另加全文 `path:line` 指针可核与 **§4.1 引文↔出处逐条核对**；**④ 反向对照 9 条**（少字段／表外状态词／悬空取代／指针指向不存在的文件／引文与出处不符／出处不可核形态／原文混排归纳／干净 fixture 防假红／"引文真的核过"防空转）；**⑤ 实战复算**见 `sprint-18.md` §7（只读本文件即回答"D-250925-06 为何要求先跑 tech-research、还差什么"）。**现跑读数**：条目 115（§3 12 / §4.1 103）、指针 691 处**全部可核**、§4.1 引文**逐条核对 97 条、0 条不符**、待回填 105 条（WARN 逐条可见）。**本次机检当场抓出 2 处真实漂移**（V-096/V-097 的 `1-WORKFLOW.MD:432/434` 因我在 §6 插入新规则而下移）⇒ 已改指针（432→**439**、434→**441**），并给闸门加了"找不到时报出**现在**在哪一行"的漂移提示。
- 生效状态：进行中（③④⑤ 已交付；§4.1 各条的 `生效状态` / `证据` / `验证时间戳` 仍有 **105 条待回填** ⇒ **回填前不得引用为已核生效裁决**）。
- 证据：本文件；`iteration/phases/testing-governance/cards/TG-20.md`。
- 验证时间戳：2026-09-25（本文件 §4 分层并入当日，网络时间 UTC+8）。

## 1. 字段定义（每条目必填）

| 字段 | 含义 | 判据 |
|---|---|---|
| `原文（逐字）` | 用户的原话，逐字 | 引号包裹；保留错别字/标点；选项式答复须标"选项原文" |
| `出处` | 原文的可核位置 | `path:line`；会话内的写"会话（本会话，无仓内出处）" |
| `时点` | 裁决发生的时间 | 网络时间 UTC+8；未知写 `未标注` |
| `主代理归纳` | 我的归类/影响判断（**非原文**） | 必须显式标注"主代理归纳" |
| `生效状态` | 受控状态词 | 见文件头状态词表 |
| `证据` | 可复跑/可定位的凭据 | `path:line` / sha / run id / 命令 |
| `验证时间戳` | 最后一次按证据核对的时间 | 网络时间 UTC+8；无则 `未验证（待补）` |
| `违背事故` | 违反该裁决的事故档引用 | 事故档 `path:line`；无则 `无` |

## 2. 提问纪律（对主代理的硬要求；条文待并入 `1-WORKFLOW.MD` §6）

1. **提问前必查本表**（以及被本表引用的计划书/Sprint 文档），确认该问题是否已裁决。
2. 每个 clarification question **必须自带三件事**：**(a) 已裁决项**（条目号 + 原文摘引）、**(b) 本次未被覆盖的原因**（为什么旧裁决不能直接套用）、**(c) 证据**（支持该问题成立的 `path:line`/命令/读数）。
3. **禁止**"裸提问"（只给选项、不给上下文与既往裁决）——按 `1-WORKFLOW.MD` §6 第 8 条作为流程事故留档。
4. 发现**两条裁决互相冲突**时：登记冲突（两条条目号 + 原文）、标 `待裁定`，**不得自行选一条**。

## 3. 本会话（2026-09-25：G1 关闭 → G2 开工）用户裁决

> 本节条目全部来自**本会话**，无仓内出处；其中的引号内容为逐字引用。选项式答复（用户点选选项而非自由文本）已标注。

### D-250925-01 关闭签核与四条判断（A1/A2/A3 + B1①/B2①/B3①/B4②）

- 原文（逐字）："签核通过 + 开 PR，四个判断按你的方案来"
- 出处：会话（本会话，无仓内出处）；同一句话被逐字记入 [`2026-09-21-sprint-17.md` §9 签核块](iteration/sprint/2026-09-21-sprint-17.md)
- 时点：2026-09-25 15:52（UTC+8，网络时间核验）
- 主代理归纳：授权 ①关闭冻结（A1）②开 `windows → main` 同步 PR（A2）③维持独立复核强度（A3）；并确认 B1①（G2 照原计划做治理、"关闭税"升为头号复测指标）、B2①（审阅期内修掉的发现不计 ⇒ 本轮扣 0）、B3①（G2 上限 ≤14 点 ＋ 每张卡说得出哪一天 ＋ `F-AC13/14` 继续冻结）、B4②（`TG-18` ＋ 复核给的机制缺口排进 G2；`TG-16` 等 G2 关闭后定稿）
- 生效状态：生效
- 证据：[`2026-09-21-governance-batch-plan.MD` §6](iteration/sprint/2026-09-21-governance-batch-plan.MD)；PR #53 合并提交 `bc3121992a723f57abc5a3cd4b53090b97cbcafb`；rollback ref（合并前 main）`8e9b5eebc1d7bd34aa551d3937d75af831b982b4`
- 验证时间戳：2026-09-25（合并后 main CI run #220 success）
- 违背事故：无

### D-250925-02 合并授权 ＋ 冲突 Plan B

- 原文（逐字）："合并，同时做好合并冲突的Plan B准备"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：授权合并同步 PR；要求**预备冲突回滚路径**（已记录合并前 main 的 sha 作为 rollback ref）
- 生效状态：生效（已执行完毕）
- 证据：[`2026-09-21-sprint-17.md` §9.3](iteration/sprint/2026-09-21-sprint-17.md) 的 ③同步 PR / ④合并 记录；合并提交与 rollback ref 见 D-250925-01
- 验证时间戳：2026-09-25（main CI #220 success）
- 违背事故：无

### D-250925-03 G2 规划启动 ＋ Sprint-17 关闸读数恢复时点

- 原文（逐字）："让我们开始 G2 的规划"；"多久后才能重新启动sprint17"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：要求产出 G2 计划；并询问 Sprint-17 关闭闸门读数何时能再被采信（答复：M-A 落地即可重跑，且通过标准是"恢复后的项数 = 该 Sprint 的真实缺口"）
- 生效状态：生效
- 证据：[`2026-09-25-governance-batch-plan-G2.MD`](iteration/sprint/2026-09-25-governance-batch-plan-G2.MD)；[`2026-09-21-sprint-17.md` §9.4/§9.5](iteration/sprint/2026-09-21-sprint-17.md)；[`TG-19`](iteration/phases/testing-governance/cards/TG-19.md) M-A
- 验证时间戳：2026-09-25（计划书提交 + CI 绿；关闸恢复待 M-A 落地后复核）
- 违背事故：无

### D-250925-04 G2 卡集与点数

- 原文（逐字，选项式）："12 点：含 A-M11（推荐）"
- 出处：会话（选项点选）
- 时点：未标注（同一日）
- 主代理归纳：G2 = `TG-19` 2 ＋ `A-M13` 1 ＋ `TG-18` 1 ＋ `TG-17` 剩余 1 ＋ `A-M12` 2 ＋ `A-M11` 3 = 10 规划点，另留插入预留 2（上限 14）
- 生效状态：**已被取代** [已被 D-250925-11 取代（2026-09-25）：新增插入卡 `TG-20`（2 点）兑现了插入预留 ⇒ 规划内 12 点、距上限 14 余 2 点]
- 证据：[`2026-09-25-governance-batch-plan-G2.MD` §3/§8.1](iteration/sprint/2026-09-25-governance-batch-plan-G2.MD)
- 验证时间戳：2026-09-25（card_index / md_tables / derived_numbers 全绿 + CI 绿）
- 违背事故：无

### D-250925-05 D1 起点与休息日

- 原文（逐字）："25-27都是休息日，你搞错了，从今天开始开工"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：**D1 = 2026-09-25（当天）**；09-26、09-27 为休息日；10-01~10-07（国庆）不计入有效工作日 ⇒ 六个有效工作日 = `09-25 / 09-28 / 09-29 / 09-30 / 10-08 / 10-09`，**D6 = 10-09**
- 生效状态：生效
- 证据：[`2026-09-25-sprint-18.md` §1](iteration/sprint/2026-09-25-sprint-18.md)（时间盒）；计划书 §4（日程表）
- 验证时间戳：2026-09-25（Sprint 文档与看板建立后闸门全绿 + CI 绿）
- 违背事故：无

### D-250925-06 `A-M11` 必须先做前置调研

- 原文（逐字，选项式）："先跑一次 tech-research（推荐）"
- 出处：会话（选项点选）
- 时点：未标注（同一日）
- 主代理归纳：开 `A-M11` 前先跑一次 `tech-research`（不得以卡内旧笔记替代）
- 生效状态：生效（2026-09-25 D6 **已执行完毕**——见证据里的 run id；本条此前写"待 D6 执行"，现按同一条目的回填条件就地更新）
- 证据：计划书 §8.1 D3 行；[`A-M11`](iteration/phases/agents-infra/cards/A-M11.md)；**执行 run** = `run-2026-09-25-tech-research-084`（expert 档；归档 `agents/runs/run-2026-09-25-tech-research-084/`，含 report + context + reasoning + `evidence/` 29 份；`verify/verify_archive.py --depth expert` ⇒ `ALL PASS: 70 passed / 0 failed`，rc=0）
- 验证时间戳：2026-09-26（UTC+8，全量回填批次 4 核对时点）
- 违背事故：无

### D-250925-07 D4 范围冲突（`§3` vs `§6`）

- 原文（逐字）："我需要更多背景来判断"；"为什么会发生冲突 我没理解"；"我只是觉得很悲哀，每一次做项目管理每一次又亲手推翻，"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：用户**未在选项上裁决**；主代理按"最新裁定优先 + 更小更安全"落地为 **§6 优先**（`TG-12` / 多语言 lint → G3 候选；`MM-1/2/3` → 独立并行线），并新增**取代规则**（旧行就地标注取代关系）。**可翻**：用户一句话即可改判
- 生效状态：生效（主代理代行裁定，已标注可翻性）
- 证据：[`2026-09-25-governance-batch-plan-G2.MD` §0/§8.2](iteration/sprint/2026-09-25-governance-batch-plan-G2.MD)；G1 计划书 §3 G2 行与 §2.3 落地批次的就地标注；`TG-12` / `MM-1..3` 的 `## Sprint` 与索引行同步
- 验证时间戳：2026-09-25（md_tables / card_index / derived_numbers 全绿 + CI 绿）
- 违背事故：无

### D-250925-08 `TG-10` ③ 排期

- 原文（逐字）："暂不用管也不需要现在就排G3"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：不并入 G2、也不现在排 G3；维持 backlog "待排期"，**不改其 Sprint 列**
- 生效状态：生效
- 证据：计划书 §8.1 D5 行；[`TG-10`](iteration/phases/testing-governance/cards/TG-10.md)
- 验证时间戳：2026-09-25（同批闸门绿）
- 违背事故：无

### D-250925-09 D6 提问（是否提前开工 M-A）

- 原文（逐字）："一样没有更多背景信息支持决策"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：该问题**已被 D-250925-05 吸收**（D1 = 当天 ⇒ M-A/M-B 即当日交付物），不再单列
- 生效状态：已被取代 [已被 D-250925-05 取代（2026-09-25）]
- 证据：计划书 §8.1 D6 行
- 验证时间戳：2026-09-25
- 违背事故：无

### D-250925-10 开工理由（赶进度）＋ 项目终局目标 ＋ 机制缺口留档

- 原文（逐字）："补充说明今天开工的原因：我们需要赶上因治理耽误的进度，按照我的目标这个项目最终应能对外包装为一个agent供使用/调用，现在来看远远不达标；另外，机制缺口同样记录为agent infra的反例"
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳（拆两条）：① **约束**：治理不得挤占功能开发额度，G2 受 ≤14 点硬约束；项目终局目标 = 本仓对外包装为**可被使用/调用的 agent**，当前远不达标 ⇒ 治理只做能提高"检查可信度"的机制；② **留档规则**：闸门/机制类缺陷一律作为 `agents-infra` 反例留档（与"派单类留档"并列）
- 生效状态：生效
- 证据：计划书 §1 开工理由块；[`1-WORKFLOW.MD` §6](1-WORKFLOW.MD)；[`2026-09-25-gate-mechanism-failure-modes-case.MD`](iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD)
- 验证时间戳：2026-09-25（提交 + CI 绿）
- 违背事故：无

### D-250925-11 决策登记册 ＋ 提问纪律（本文件由来）

- 原文（逐字）：见 §0 两段
- 出处：会话
- 时点：未标注（同一日）
- 主代理归纳：新建 `TG-20`（用户插入卡，**兑现** G2 的插入预留 2 点 ⇒ 规划内 `TG-19` 2 ＋ `A-M13` 1 ＋ `TG-18` 1 ＋ `TG-17` 剩余 1 ＋ `A-M12` 2 ＋ `A-M11` 3 ＋ 本卡 2 = **12 点**，距上限 14 余 2 点；再插入须用该余量或走三选一）；交付 ①本文件 ②提问纪律条文 ③机检判据 ④反向对照 ⑤实战复算
- 生效状态：进行中
- 证据：[`TG-20`](iteration/phases/testing-governance/cards/TG-20.md)；本文件；计划书 §3/§4 的插入记录
- 验证时间戳：2026-09-26（UTC+8，全量回填批次 4 核对时点）
- 违背事故：无

### D-250925-12 D4 之前**中途插入**一次独立复核

- 原文（逐字，本会话消息片段）："先插一次'中途独立复核'"
- 出处：会话（对主代理"是否先把 D1~D3 收口、再进 D4"的选项点选）
- 时点：2026-09-25（UTC+8，D3 收尾后、D4 开工前）
- 主代理归纳：**独立复核不再只在 Sprint 关闭时做**——D4 之前先插一次，对象 = D1~D3 已落地的代码＋文档＋闸门；产出按既有 `code-review` 口径逐条分级（critical/major/minor/nit ＋ `file:line`），"Fix this round: yes" 的**当场整改**，"Fix this round: no" 的转 backlog 并记理由
- 生效状态：生效（**已执行**：`run-2026-09-25-code-review-083`；critical 0 / major 5 / minor 4 / nit 1，5 条 major 全部本轮整改）
- 证据：`agents/runs/run-2026-09-25-code-review-083/code-review.report.md`（18058 字符；账本 `result_files` 为**受控回填**，留痕 `result_files_backfills`）；整改逐条见 [`TG-19`](iteration/phases/testing-governance/cards/TG-19.md) 与 [`sprint-18` §5/§7](iteration/sprint/2026-09-25-sprint-18.md)
- 验证时间戳：2026-09-25（复核 run 已登记收尾；整改后 `verify_lint` 的 E501 由 2521 → **2493**/上限 2494、`verify_gate_integrity` 19 断言、`verify_agentops` 120 断言全绿）
- 违背事故：无

### D-250926-01 每批工作必须主动给出**可见的文字进度**（不得只留工具调用）

- 原文（逐字，本会话消息片段）："三查结果如何 我记得从下午开始你的工作中全变成了执行动作，没有任何我能看到的文字输出吗 看起来都需要我来主动和你问问题才行"；追加（逐字）："现在结果如何，别总是让我来问你要进度"
- 出处：会话（G2 关闭三查进行中，用户两次主动追问进度后当场提出）
- 时点：2026-09-26（UTC+8，关闭期；第一次提出于 2026-09-25 下午之后）
- 主代理归纳：**每完成一个批次或一个可报告的节点，必须主动给出可见的文字汇报**——"做了什么 / 读数是什么（带命令）/ 未决项与下一步 / 有无事故"四段式；**不得让用户靠追问才知道进度**。工具调用不算汇报（用户看不到过程），"我一直在干活"不构成进度可见性
- 生效状态：生效（**本轮起执行**；条文并入 `docs/1-WORKFLOW.MD` §6）
- 证据：`docs/1-WORKFLOW.MD` §6 新增条"进度可见性"；**反例（即刻可核）** = 本条登记之前的连续多轮只发工具调用、无文字汇报，由用户当场指出；本条落盘所在的这一轮即为首次执行样本
- 验证时间戳：2026-09-26（本条落盘时；后续以用户是否仍需追问为验收读数）
- 违背事故：无（自本条生效起）

### D-250926-02 经验文档每次更新 ⇒ 主代理必须增量提取候选思维模型（`MM-4` 的**触发义务**）

- 原文（逐字，会话日志第 20538 行；省略处用 `……` 标注，未加任何标记）: "另新增一个知识沉淀的卡，思维模型管理，在工程开发中总结的经验文档如何转化成 更抽象的模型架构，模型是否成功的判断标准是是否能应用模型架构直接生成可执行的agent workflow，如果判断单卡无法容纳，可以按一个/多个sprint的规模判断（……）思维模型来源：我的输入，我们的探讨交流，由你主管每次经验文档更新时。初始思维模型：名称：思维实验，模型描述：对一个问题生成不少于三种的解决方案，并对每个方案的解决过程进行遵循客观规律事实的模拟，输出方案预期效果并生成比对文档，模型使用时机：初始边界为检测到用户输入讨论时启用该模型，当用户给与认可情绪的反馈后尝试覆盖到其他决策场景，模型边界：xxx，输入：xxx，输出：xxx，模型创始人：爱因斯坦，等等字段信息"
- 出处：会话（用户 2026-09-07 原始要求）；**逐字定位 = 会话日志（仓外备份）`session-d6abecbf-…-readable.txt` 第 20538 行**——本仓 `docs/**` 里此前只有 `MM-4` 的一句话摘要，**原文不在版本控制内**
- 时点：2026-09-07（UTC+8）提出；2026-09-26（UTC+8）用户指出我未执行
- 主代理归纳：**义务 = 每次 `docs/3-LEARNED.MD` 更新（追加或修改条目）时，主代理必须增量提取候选思维模型**，产出须带**来源条目号**；字段口径取用户原话自列的字段（名称/描述/使用时机/边界/输入/输出/创始人 等）。它是本仓**第一条被明文登记的"数据源文档 → 下游产物"触发义务**——不是"有空再做"
- 生效状态：生效（**已执行**：`docs/iteration/phases/mental-models/models/2026-09-26-from-learned-1.67-1.69.MD`，本轮提取 4 个候选模型 `CM-1`~`CM-4`，来源分别标 `1.67` / `1.68` / `1.69` / `1.31` 再版注记）
- 证据：上述模型文件（含"预 schema、`MM-1` 交付后重裁"的状态口径，防越权）；`docs/3-LEARNED.MD` 头部新增的"改本文件之前必读"义务块；机制反例档案例 24
- 验证时间戳：2026-09-26（UTC+8，本轮执行时）
- 违背事故：**有**——2026-09-25/26 我追加 `1.67`~`1.69` 与 `1.31` 再版注记时**未执行**该义务，由用户 2026-09-26 指出（整改与根因见机制反例档案例 24）

### D-250926-03 备案必须**独立且显式存在**；doc-audit 必须对照"执行任务前记录的全部文档管理规则"

- 原文（逐字）: "这些备案和事故记录一样需要独立且显式存在 -> doc aduit规则也需要包括执行任务前的所有卡片/对话/文档中对文档管理的规则记录"
- 出处: 会话（2026-09-26，主代理把 R-001 写进 G2 复盘 §7 之后；含用户原拼写 `aduit`）
- 时点: 2026-09-26（UTC+8）
- 主代理归纳: 两层要求——① **备案/风险登记必须与事故记录同等地独立成文**，不得寄生在复盘或卡片正文里（"埋在别的文档里的一段落"不算满足）；② **doc-audit 的判据必须包含"执行任务前记录在卡片/对话/文档里的文档管理规则"**：先采集规则源，再逐条对照被审对象
- 生效状态: 生效（**已执行**）
- 证据: 独立备案档 `docs/iteration/phases/agents-infra/2026-09-26-residual-risk-register.MD`（R-001，7 要素）；`agents/functions/doc-audit.md` **v1.4.0** 第 10 维 `rule-conformance`（三来源采集 ＋ 逐条判定 ＋ `unverifiable` 本身算 finding ＋ 独立存在类规则按独立产物判定 ＋ 输出模板必需对照表 ＋ Forbidden 禁止无源声称合规）
- 验证时间戳: 2026-09-26（UTC+8；`validate-spec` PASS：`name=doc-audit v1.4.0`）
- 违背事故: 无（自本条生效起）

### D-250926-04 决策登记册的 105 条 `待回填` **全量回填**

- 原文（逐字）: "登记册 105 条 待回填 是全量回填"
- 出处: 会话（2026-09-26，回答主代理"全量回填 vs 先做高频被引用者"的二选一提问）
- 时点: 2026-09-26（UTC+8）
- 主代理归纳: **不留"先做高频"的折中**——103 条 §4.1 逐字原话条目各补 5 个字段（主代理归纳/生效状态/证据/验证时间戳/违背事故），另 2 条 §3 条目（`D-250925-06`/`D-250925-11`）补验证时间戳；回填完成后闸门的 WARN（"回填前不得引用为已核生效裁决"）应消失
- 生效状态: 进行中（侦察已完成：117 条 = §3 14 ＋ §4.1 103；待回填 105）
- 证据: 侦察口径见本条执行记录；判据 = `verify/verify_decision_register.py`（断言数与 `待回填 N 条` 均以该闸门现跑输出为准，本行不写死）
- 验证时间戳: 2026-09-26（UTC+8，本条全量回填完成时点）
- 违背事故: 无

## 4. 历史裁决（征集稿全量分层：逐字原话全收／二手转述入附录）

> **用户裁定（R1，2026-09-25）**：分层并入——**逐字原话全收**；二手转述里只有主代理判定「仍生效」的进 §4.2，其余进 §4.3 附录（**未判定效力，不得引用为裁决**）。
> **编号体系**：`V-xxx` = 逐字原话（本文件正文）；`A-xxx` = 附录索引；合并稿编号 `H-xxx` 仅作追溯（全量稿是只读征集产物，不入本文件）。
> **状态纪律**：`主代理归纳` / `生效状态` / `证据` / `验证时间戳` / `违背事故` 一律**待回填**；回填完成前任何人不得把 §4.1 的条目当作「已核生效裁决」引用（依据 D-250925-11）。

### 4.0 首批已核条目（主代理手工登记，含生效状态与证据）

> 本节 8 条是主代理**已核**的首批条目（含 `生效状态` / `证据` / `验证时间戳`）；与 §4.1 / §4.3 **可能有同一句原话的重复**（同一裁决在卡与 Sprint 文档各出现一次）——**重复不等于冲突**，两处编号可交叉引用。

> **本节状态**：三路子代理正在按"逐字 + `path:line`"征集（范围：`iteration/sprint/**`、`iteration/phases/**`（卡/索引/复盘/事故档）、`docs/1..5-*.MD` 与预研档）。**并入前不得把征集稿当原文使用**。本版只登记**已可核**的两类：
> ① **有仓内逐字记录**的（见下表）；② **只有二手转述**的（必须标 `原文缺失（二手转述）`）。

| 条目 | 原文（逐字）或缺失标注 | 出处 | 生效状态 |
|---|---|---|---|
| D-250921-H1 `TG-15` 不减点、改扣分条件 | 原文缺失（二手转述）："用户 2026-09-25 拍板：**不减点、改扣分条件**" | [`2026-09-21-sprint-17.md` §4](iteration/sprint/2026-09-21-sprint-17.md) | 生效 |
| D-250921-H2 `TG-12` 开卡 | 原文（逐字）："我想从 sprint17 和以前的开发过程发现的文档内容漂移问题也足够开个卡做复盘了，把类似问题一并加到 backlog 中吧" | [`TG-12` 卡 `## 来源`](iteration/phases/testing-governance/cards/TG-12.md) | 生效（已按 D-250925-07 改期 G3） |
| D-250921-H3 `TG-16` 开卡 | 原文（逐字）："先这样做吧，我想需要对现有审查流程和具体策略内容找时间整体过一遍 记张卡把这些内容规则流程梳理作为一个backlog，输出图文并茂容易理解的html汇报文件" | [`TG-16` 卡 `## 来源`](iteration/phases/testing-governance/cards/TG-16.md) | 生效（等 G2 关闭后定稿） |
| D-250921-H4 `TG-17` 立项 | 原文（逐字）："1+2 合成一张新卡（比如 TG-17「闸门可信化收尾」）排进 G：可以，开进backlog吧" | [`TG-17` 卡 `## 来源`](iteration/phases/testing-governance/cards/TG-17.md) | 生效（已前移为 G1 关闭阻塞项，B1~B4 交付） |
| D-250923-H5 `A-M12` 开卡 | 原文缺失（二手转述）："用户 2026-09-23 要求成卡" | [`A-M12` 卡 `## 来源`](iteration/phases/agents-infra/cards/A-M12.md)；[`2026-09-21-sprint-17.md` §10](iteration/sprint/2026-09-21-sprint-17.md) | 生效 |
| D-250921-H6 `A-M11` 只记卡不实现 | 原文（逐字）："这两个方案需要继续调研后再确认怎么做，先记张卡吧" | [`A-M11` 卡 `## 状态`](iteration/phases/agents-infra/cards/A-M11.md) | 已被取代 [已被 D-250925-04 取代（2026-09-25）：本轮实现，且 D-250925-06 要求先跑调研）] |
| D-250921-H7 Sprint-16 两处口径 ＋ "现在修" | 原文缺失（二手转述）："用户确认 Sprint-16 两处口径（F-AC8 = 14 天 due ＋ 任务计划可选不自动注册；TG-5 = 周频 ＋ ¥10 上限 ＋ fail-closed ＋ 不进 CI）并选择「现在修」" | [`2026-09-12-sprint-16.md` §5](iteration/sprint/2026-09-12-sprint-16.md) | 生效 |
| D-250921-H8 派单类事故一律入 agents-infra 反例档 | 原文（逐字）："和子代理派单相关的漏洞/问题/事故今后一律作为 agent infra 的反例留档" | [`1-WORKFLOW.MD` §6](1-WORKFLOW.MD)；[`2026-09-25-subagent-dispatch-failure-modes-case.MD`](iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD) | 生效（已扩展至机制缺口，见 D-250925-10） |

## 4.1 逐字原话（用户原话，逐字）

### V-001 Sprint5 用户所见「与 query 无关」
- 原文（逐字）: "与 query 无关"
- 出处: docs/iteration/sprint/2026-08-30-sprint-5.md:12
- 时点: 未标注
- 主代理归纳: 本条要求检索结果不得把"与 query 无关"的兜底结果当正常命中呈现：BM25 零命中回退取索引前 N 个文件时必须在输出显式标记 `result=fallback_first_n`（选择逻辑对用户可见），并补多语检索降零命中。
- 生效状态: 生效
- 证据: docs/4-ALGORITHM.MD:377；docs/3-LEARNED.MD:143；paper-qa-script/app/orchestration.py:686；verify/eval_retrieve.py:92
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-002 用户指示继续阶段 B
- 原文（逐字）: "继续阶段 B"
- 出处: docs/iteration/sprint/2026-08-31-sprint-12.md:3
- 时点: 2026-08-31
- 主代理归纳: 本条指示在 F2 阶段 A 之后启动阶段 B（SchemaForm 全字段交互表单取代三个手写面板）为独立 Sprint（Sprint-12）并交付。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-08-31-f2-acceptance-guide.MD:11；docs/iteration/phases/refactor-analysis/roadmap.MD:31
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-003 用户指示继续阶段 C 并全盘验收
- 原文（逐字）: "继续阶段 C，完成后全盘验收"
- 出处: docs/iteration/sprint/2026-08-31-sprint-13.md:3
- 时点: 2026-08-31
- 主代理归纳: 本条指示阶段 B 之后启动阶段 C（手写字面量退役 + Settings 升级同步护栏），且完成后必须做全盘验收（F2 整体验收清单），不得只验收本 Sprint 交付物。
- 生效状态: 生效
- 证据: docs/iteration/phases/refactor-analysis/roadmap.MD:32；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:44
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-004 用户拍板底座批次优先
- 原文（逐字）: "底座批次优先"
- 原文缺失（二手转述）: "**Q3**：**底座批次优先**（底座批次开工后，验收修复批次紧随）｜｜**验收修复批次（拆 2~3 个插队 sprint，约 24~26 点，Sprint-15 起）**：交互信息类（F-AC1/2/3/4/7/9）→ 数据准确性+成本韧性（F-AC8/10）+ 响应式/复制报错（F-AC5/6）；开工时按依赖与产能定拆分｜｜**底座式更新应提前完成**（如领域治理备忘这类直接影响架构的机制），避免积累技术债——盘点见 §6"
- 出处: docs/iteration/sprint/2026-08-31-sprint-14.md:3；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:29；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:35；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:36；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:44；docs/iteration/pre-research/2026-08-31-domain-governance.MD:44
- 时点: F2 验收 Q3，2026-08-31；未标注（节标题 2026-08-31 已答复）；2026-08-31
- 主代理归纳: 本条裁定排期顺序：底座批次（Sprint-14，13 点，即刻开工）优先，F2 验收修复批次（约 24~26 点，拆 2~3 个插队 sprint）紧随其后；直接影响架构的底座式更新应提前完成以避免技术债。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-08-31-sprint-14.md:8；docs/iteration/ROADMAP.MD:13
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/pre-research/2026-08-31-domain-governance.MD:44 承载的是本条第二段逐字（"底座式更新应提前完成"），不含"底座批次优先"字样。

### V-005 N1 output 完整查看诉求原话不好用
- 原文（逐字）: "不好用"
- 出处: docs/iteration/sprint/2026-09-07-sprint-15.md:143
- 时点: 未标注（节标题 2026-09-10；行内记"四轮"）
- 主代理归纳: 本条判定 N1「output 完整查看」的 tooltip 形态不可用，要求移除 tooltip，改以 output 复制全文 + answer 全文块 + 复制答案定稿交付。
- 生效状态: 生效
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC11.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:32
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-006 指示"继续做 Sprint-16"
- 原文（逐字）: "继续做 Sprint-16"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:3
- 时点: 2026-09-12
- 主代理归纳: 本条指示按既定排期开工 Sprint-16（数据准确性 + 成本韧性 + 调研工作流深化），前置条件为 Sprint-15 已于 2026-09-10 用户验收通过并关闭。
- 生效状态: 生效
- 证据: docs/iteration/ROADMAP.MD:13；docs/iteration/sprint/2026-09-12-sprint-16.md:3
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 同一 Sprint 后于 2026-09-21 被用户裁定 HOLD（原三查结论需在后续改动落地后重跑），见 docs/iteration/sprint/2026-09-12-sprint-16.md:291；本条系"开工指示"、已履行，未被取代。

### V-007 选择"现在修"
- 原文（逐字）: "现在修｜｜现在修再关闭 Sprint-16"（`｜｜` 为分段符）
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:70；docs/iteration/sprint/2026-09-12-sprint-16.md:287
- 时点: 2026-09-20
- 主代理归纳: 本条拍板 Sprint-16 两处口径并选择当场修复：F-AC8 定期刷新 = 14 天 due 判定、系统任务计划可选不自动注册；TG-5 夜间套件 = 周频 + 单次 ¥10 上限（可配）+ fail-closed + 不进 CI（CI 只跑 offline 档）。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:36；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:37；scripts/scheduled-tasks.py:58；.github/workflows/ci.yml:66
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-008 "没验收前不要提PR"
- 原文（逐字）: "**没验收前不要提PR**"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:279；docs/iteration/sprint/2026-09-12-sprint-16.md:67；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:67；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:25
- 时点: 2026-09-12
- 主代理归纳: 本条禁止在用户走查验收通过之前创建任何 PR（含以"提前验证 CI"为由）；CI 校验改走 windows 分支 push 触发，或经用户同意后再建 PR。注：本规则仓内自认无机器闸门，现有执行点仅为 §3.4 规范条文，属"仅文字、无可执行执行点"。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:52
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——2026-09-12 主代理以"提前验证 CI"为由创建 PR #50（仓内记为"违反'验收前不提 PR'"的越界先例），处理 = PR 关闭、远端/本地 sync/sprint-16 删除、规则事后加固入 §3.4：docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:67；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:25
- 备注: 仓内自认该规则"同样没有执行点"（docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:67，属 TG-11 复盘输入）：现有执行点仅为 §3.4 规范条文，另有 sprint-16 关闭记录的逐字（docs/iteration/sprint/2026-09-12-sprint-16.md:279），无机器闸门。

### V-009 付费项"先计量后执行"口径
- 原文（逐字）: "先计量后执行｜｜先计量再跑｜｜先打通计量再跑付费项"（`｜｜` 为分段符）
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:82；docs/iteration/sprint/2026-09-12-sprint-16.md:284；docs/iteration/sprint/2026-09-12-sprint-16.md:286；docs/iteration/sprint/2026-09-12-sprint-16.md:288
- 时点: 2026-09-20
- 主代理归纳: 本条要求付费（联网/LLM）项在计量打通之前不得开跑：先落地 token 实测采集 → 价表换算 → 闸门自动回填，再执行付费项并留实测数据。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16.md:288；paper-qa-script/app/usage.py:5；verify/verify_usage.py:18
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）

### V-010 决策④ F-AC17 仅记录
- 原文（逐字）: "允许运行中点击"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:111
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条给定运行中点击口径：允许用户在运行中点击（运行按钮不加 disabled、不早退）；因重复点击语义未定义，本轮只立卡记录 `F-AC17`、不实现。
- 生效状态: 生效
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC17.md:1；docs/iteration/phases/refactor-analysis/backlog.MD:63
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: ① 出处所列 docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:111 只有转述（"运行中重复点击语义"），逐字见同批 docs/iteration/sprint/2026-09-12-sprint-16.md:291；② 本条与 §4.1 `V-090` 为同一句原话的重复登记（两处编号，非冲突）。

### V-011 决策⑤ F-AC16/M18 暂不动
- 原文（逐字）: "待真实数据"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16.md:144；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:111
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条裁定 F-AC16 / M18 的"增量"部分暂不动，等真实用户数据再排期；v1 范围已完成，不因增量未做而返工或催办。
- 生效状态: 生效
- 证据: docs/iteration/phases/refactor-analysis/backlog.MD:37；docs/iteration/phases/refactor-analysis/backlog.MD:62
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字"待真实数据"只见于出处所列 docs/iteration/sprint/2026-09-12-sprint-16.md:144；另两处出处（同文件 :291、status-report.MD:111）写作"待用户数据/增量暂不动"，属同义转述。

### V-012 批准"账本多轮次记录做掉"
- 原文（逐字）: "账本多轮次记录做掉"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:211
- 时点: 2026-09-21
- 主代理归纳: 本条批准把账本的多轮次记录做掉：`agent-ops.py` 增 `round`（终态 run 亦可追加、保留首轮快照、产出累加、ended_at 前移）与 `interrupt`（中断/接管留痕），并配离线回归。
- 生效状态: 生效
- 证据: scripts/agent-ops.py:1181；verify/verify_ledger_rounds.py:1；docs/iteration/sprint/2026-09-12-sprint-16.md:211
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-013 要求"单独开卡复盘"
- 原文（逐字）: "单独开卡复盘"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:212
- 时点: 2026-09-21
- 主代理归纳: 本条要求规则绕过事件单独开一张卡做复盘（卡 = `TG-11`），并把证据固化进独立台账文件，不得只散记在卡单元格里。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-11.md:18；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:1
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-014 明确"开卡以后复盘，不是现在就做"
- 原文（逐字）: "**开卡以后复盘，不是现在就做**"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:212；docs/iteration/sprint/2026-09-12-sprint-16.md:98；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:66
- 时点: 2026-09-21
- 主代理归纳: 本条界定时点：开卡即触发，但正式复盘在卡执行时进行；Sprint-16 期间不做任何代码改动（已起草的 `--scope-source` 闸门与相关断言全部回退），台账不得当作复盘结论引用。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-11.md:27；docs/iteration/sprint/2026-09-12-sprint-16.md:212
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-12-sprint-16.md:98 与 docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:66 只有"方案 M1~M4 保留、S16 不删代码"的转述，逐字见 docs/iteration/sprint/2026-09-12-sprint-16.md:212。

### V-015 质疑窄范围定点复核依据
- 原文（逐字）: "窄范围定点复核的判断依据是啥"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:200；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:24
- 时点: 2026-09-21
- 主代理归纳: 本条要求"修复验证复核"的 scope 必须有可执行来源：必须来自〇查 impact-assessment（`never a self-chosen narrow scope`），自选 scope 须显式声明来源与偏离理由，且与关闭三查分节记录。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:109；docs/1-WORKFLOW.MD:121
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）——本条生效后未发现新的违背；
- 备注: 促成本条裁决的既成事实（5 轮"修复验证复核"scope 全为自选、无来源声明，且三查跑过后另有 26 个提交落地致覆盖实质失效）见 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:24；docs/iteration/sprint/2026-09-12-sprint-16.md:212。

### V-016 要求按紧急度排序卡片
- 原文（逐字）: "按你的紧急度标准排序给卡片排个序"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:127
- 时点: 2026-09-21（快照）
- 主代理归纳: 本条要求用显式、可反驳的紧急度标准给全部开放卡排序（P0~P3 分档 + 加权理由），不得只列部分卡或以隐含标准排序。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16.md:127；docs/iteration/sprint/2026-09-12-sprint-16.md:150
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）——本条生效后未发现新的违背；
- 备注: 促成本条裁决的既成事实（紧急度排序初版遗漏 `TG-6`，主代理自认"属我的错"，2026-09-21 补录为 P1 / 14.5）见 docs/iteration/sprint/2026-09-12-sprint-16.md:150。

### V-017 指出架构卡未进排序
- 原文（逐字）: "一张卡对应一个独立文档的架构卡没在排序里"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:149
- 时点: 2026-09-21
- 主代理归纳: 本条要求紧急度排序必须覆盖"一张卡对应一个独立文档"的架构类卡片；遗漏项须补录入表并留修订记录。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16.md:149；docs/iteration/sprint/2026-09-12-sprint-16.md:151
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）——本条生效后未发现新的违背；
- 备注: 促成本条裁决的既成事实（排序初版未收录"一张卡对应一个独立文档"的架构卡，本条原话即用户当场指出该遗漏，修订时补记 `TG-14` 等）见 docs/iteration/sprint/2026-09-12-sprint-16.md:149。

### V-018 叫停跨卡接口"写死"
- 原文（逐字）: "任何涉及写死的操作都需要注意下，**这个需要再研究才能决定**｜｜**任何涉及写死的操作都需要注意下，这个需要再研究才能决定**"（`｜｜` 为分段符）
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:153；docs/iteration/phases/agents-infra/cards/A-M11.md:123
- 时点: 2026-09-21
- 主代理归纳: 本条禁止把跨卡分工/接口按"写死"方式定稿：涉及写死的操作须先再研究才能决定；该接口表只能标为「提案·待研究」，不得当作既定事实引用，执行前须重新论证。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/cards/A-M11.md:123；docs/iteration/phases/agents-infra/cards/A-M11.md:7
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-019 明确全局视角缺失
- 原文（逐字）: "没有项目的全局视角我无法给出有效建议"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16.md:125
- 时点: 2026-09-21
- 主代理归纳: 本条要求主代理先给出项目全局视角（可核数据）再请用户做方向性裁决；缺全局视角时不得要求用户回答"功能优先/治理优先"这类定位问题。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16.md:125；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:7
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 执行面为"Sprint-17 定位待全局状态后再定"的挂起处置，及随后以治理批计划 §1 的数据表（结论见 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:20）供用户裁定 D1~D8；该要求属常设纪律，未设独立闸门。

### V-020 用户要求检查所有按钮行为
- 原文（逐字）: "检查所有按钮行为"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369
- 时点: 2026-09-20，UTC+8
- 主代理归纳: 本条要求对全部按钮行为做全量审计（不止出问题的那一个），结论须逐类给出并落到卡：审计确认仅"复制答案/output/复制报错"三按钮共用 `copied` state 有问题，其余按钮正常，并据此立 `F-AC14`。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369；docs/iteration/phases/refactor-analysis/cards/F-AC14.md:13
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-021 用户选择：先打通 token 计量再跑
- 原文（逐字）: "**先打通 token 计量再跑**"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:384
- 时点: 2026-09-20
- 主代理归纳: 本条在"先执行付费项"与"先打通计量"之间选择后者：先把 token 实测计量链路打通（采集 → 价表换算 → 闸门回填），再跑付费项。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-12-sprint-16.md:288；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:384
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-022 用户选择：TG-7 现在修
- 原文（逐字）: "现在修"
- 出处: docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:442
- 时点: 2026-09-20
- 主代理归纳: 本条选择"现在修"并据此收口 Sprint-16 的 `TG-7`：`load_state()` 改 fail-closed（状态文件解析失败/结构非法 → 退出码 2 拒绝执行 + 损坏文件另存 `.corrupt`），读取容忍 BOM。
- 生效状态: 生效
- 证据: scripts/scheduled-tasks.py:104；verify/verify_runner.py:14；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:442
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-023 规模上限"先跑跑看"
- 原文（逐字）: "先跑跑看"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:25
- 时点: 2026-09-21
- 主代理归纳: 本条要求本轮不预设结论：18 点规模上限是否合理必须用实测数据回答（插入卡点数 / 关闭税 / 有效工作日），并在关闭时写入 §8.1。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-sprint-17.md:25；docs/iteration/sprint/2026-09-21-sprint-17.md:161
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 该"先跑跑看"已由实测收口（18 点不成立、实测 22.5 点），G2 起规模上限按用户裁定改为 ≤14 点（B3①，docs/iteration/sprint/2026-09-21-sprint-17.md:182）；本条作为"本轮用数据回答"的指示已履行完毕。

### V-024 依赖工具口径 L1~L6 裁定
- 原文（逐字）: "L1=a L2=b L3=a L4=c L5=a L6=b"
- 原文缺失（二手转述）: "**工具口径已由用户 2026-09-21 裁定**（`L1=a L2=b L3=a L4=c L5=a L6=b`，执行清单见报告 §6.2）：**G1 只需 ruff**（Python 112 文件），按｜｜**先查后装**｜｜顺序（`npm install --package-lock-only --ignore-scripts` → `npm audit`；`pip download <pin> --no-deps`）留证后引入"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:98；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:111；docs/iteration/pre-research/README.md:15
- 时点: 2026-09-21；2026-09-21（UTC+8）
- 主代理归纳: 本条规定工具口径 L1~L6 的执行后果：G1 只需 `ruff`（Python）、`prettier` 只查新增/改动文件、`tsc --noEmit` 与 `@typescript-eslint` 都上、`yamllint` 引入、不引 `eslint-plugin-react`、`PSScriptAnalyzer` 延后 G2；所有新依赖按"先查后装"留原始输出。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:110；verify/verify_lint.py:41；.github/workflows/ci.yml:124
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）

### V-025 TG-17 开卡原话
- 原文（逐字）: "1+2 合成一张新卡（比如 TG-17「闸门可信化收尾」）排进 G：可以，开进backlog吧"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:135；docs/iteration/phases/testing-governance/cards/TG-17.md:13；docs/iteration/phases/testing-governance/cards/TG-17.md:1；docs/iteration/phases/testing-governance/backlog.MD:31
- 时点: 2026-09-23（UTC+8 `22:47` 网络核验）；2026-09-23（UTC+8 22:47）
- 主代理归纳: 本条批准把 `TG-15` 独立复核批的两条 finding 合成一张新卡 `TG-17`「闸门可信化收尾」并开进 backlog 排进治理批。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-17.md:13；docs/iteration/phases/testing-governance/backlog.MD:31
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/backlog.MD:31 为 `TG-17` 索引行（状态/排期），不含逐字串；逐字见 docs/iteration/phases/testing-governance/cards/TG-17.md:13 与 docs/iteration/sprint/2026-09-21-sprint-17.md:135。

### V-026 关闭签核原话
- 原文（逐字）: "**签核通过 + 开 PR，四个判断按你的方案来**｜｜签核通过 + 开 PR，四个判断按你的方案来"（`｜｜` 为分段符）
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:181；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:193；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:195
- 时点: 2026-09-25（UTC+8 `15:52`，网络时间核验）；2026-09-25
- 主代理归纳: 本条为 Sprint-17（G1）关闭签核：接受关闭结论、授权开 windows→main 同步 PR（排除 `docs/iteration/**`、挡住 4 个 mac `.sh` 删除）、维持本轮复核强度、四个判断按方案执行。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-sprint-17.md:188；docs/iteration/sprint/2026-09-21-sprint-17.md:296
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-sprint-17.md:181 为 B1① 裁定行、不含逐字串（行号偏差 7 行）；逐字在同文件 :188，另 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:195 命中。

### V-027 不减点、改扣分条件
- 原文（逐字）: "**不减点、改扣分条件**"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:87；docs/iteration/sprint/2026-09-21-sprint-17.md:89；docs/iteration/sprint/2026-09-21-sprint-17.md:146；docs/iteration/sprint/2026-09-21-sprint-17.md:155
- 时点: 2026-09-25
- 主代理归纳: 本条裁定 `TG-15` 的 2.5 点不减：点数留在账上，改为按扣分条件结算（未闭环 critical/major 按级别比例扣，口径落为政策数据 `deduction_rates`）。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-15.md:7；agents/policy.json:322；verify/verify_deduction_rates.py:1
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-sprint-17.md:146 为"按用户裁定不减"的转述、:155 为空行，逐字只见于同文件 :87/:89。

### V-028 P-a 暂存分支方案批准
- 原文（逐字）: "按优化方案执行｜｜；｜｜按照你的优化方案来执行"（`｜｜` 为分段符）
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:259；docs/iteration/sprint/2026-09-21-sprint-17.md:261
- 时点: 2026-09-25
- 主代理归纳: 本条批准未推提交暂存分支方案（P-a）按优化方案执行：建 `park/` 分支承载未推提交、不对 `windows` 做 reset、治理模式退出后 fast-forward 推回并删除 park 分支。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-sprint-17.md:259；docs/iteration/sprint/2026-09-21-sprint-17.md:272
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）

### V-029 前两点要落实到位
- 原文（逐字）: "前两点要落实到位"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:274
- 时点: 2026-09-25
- 主代理归纳: 本条要求把方案前两点落实到位：① CI 盲点必须当真实关口（红即修，不得以本机全绿替代）；② 暂存分支的命名与回收留痕写死为可判条件。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-sprint-17.md:274；docs/iteration/sprint/2026-09-21-sprint-17.md:308
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: ①以"CI #207 红 → 修 → #208 绿"兑现（docs/iteration/sprint/2026-09-21-sprint-17.md:276-277）。

### V-030 合并并备 Plan B
- 原文（逐字）: "合并，同时做好合并冲突的 Plan B 准备"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:293
- 时点: 2026-09-25
- 主代理归纳: 本条授权合并 windows→main，同时要求备好合并冲突的 Plan B；合并前须逐条机检前置断言（PR open / mergeable / 必需检查同 head sha 绿），冲突路径不得在主树上手改。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-sprint-17.md:293；docs/iteration/sprint/2026-09-21-sprint-17.md:300
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: Plan B 四条分支已备好但本次未触发（docs/iteration/sprint/2026-09-21-sprint-17.md:300-304）；合并结果 = PR #53 merge sha `bc312199…`（同文件 :296）。

### V-031 sha 纪律要求
- 原文（逐字）: "不想再看到 sha 传参/使用出问题"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:305
- 时点: 2026-09-25
- 主代理归纳: 本条禁止在任何 prompt 或命令里手抄 sha：sha 一律由执行者 `git rev-parse` 或 API 取得并落文件，工具侧必须解析、规范化、失败即 fail-closed；用某个标识符去查结论时，须显式传入或连同来源（仓库、分支、事件）一起打印供逐字比对。
- 生效状态: 生效
- 证据: scripts/agent-ops.py:167；docs/1-WORKFLOW.MD:425；docs/iteration/sprint/2026-09-21-sprint-17.md:296
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条裁决的既成事实（派单 prompt 里手抄 8 位短 sha 致 3 个 run 的覆盖窗口静默作废；主代理两次给 CI 查询脚本传短 sha）见 docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:13；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:18。
- 备注: 同族后发实例（2026-09-25 验证 CI 时轮询脚本在另一个 cwd 的仓库里解析 HEAD，把别人的 run 当成自己提交的证据）见 docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:202；该形态在 §6 的归属判据是第 1 条对偶「不猜标识符」，与本条禁止的手抄、传参不同格，故未据此判违背。

### V-032 日期口径漂移当场指出
- 原文（逐字）: "今天网络时间是 9.23 了"
- 出处: docs/iteration/sprint/2026-09-21-sprint-17.md:150；docs/iteration/sprint/2026-09-21-sprint-17.md:365；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:24
- 时点: 2026-09-23
- 主代理归纳: 本条要求文档日期一律取当次网络时间核验值（UTC+8），不得沿用会话起始日期；可核判据为文档内日期与该文件最近一次提交的 committer 日期相差超过 1 天即记 R2 告警并当日更正，更正方式为加注记、不重命名文件。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:403；docs/iteration/sprint/2026-09-21-sprint-17.md:372；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:24
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后，关闭〇查的启动时刻把账本里的 UTC 值与 UTC+8 写成同一个数（记 `2026-09-25 16:51`，按 UTC+8 应为 `2026-09-26 00:51`），2026-09-26 由一查 must-fix 指出后就地更正为 UTC+8 值（docs/iteration/sprint/2026-09-25-sprint-18.md:228）。
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-sprint-17.md:150（§8.1 的 R2 读数行）与 :365（§10 的过程事故行）均不含逐字串，逐字在同文件 :372；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:24 命中。
- 备注: 促成本条裁决的既成事实（新写文档日期标为 09-21、实际落库已是 09-23，而 §6 早有网络时间规则却未被检索）见 docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:25。

### V-033 未闭环扣率按级别比例
- 原文（逐字）: "未闭环 critical/major 的扣率：**按级别比例**，然后给个具体口径方案和例子我看看"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:34；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:36
- 时点: 2026-09-25，UTC+8
- 主代理归纳: 本条裁定未闭环 critical/major 的扣率取比例制：以被判级的卡为对象，扣分 = 卡点数 × Σ(未闭环发现的比例)，比例只按级别取、同根因合并取最高级别、封顶为该卡点数；比例表、开关、封顶、取整步长与「未闭环」判据全部落为政策数据，文档与脚本只引用该键、不复制数值。
- 生效状态: 生效
- 证据: agents/policy.json:322；verify/verify_deduction_rates.py:31；docs/iteration/sprint/2026-09-21-sprint-17.md:178
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列两处均在 ±2 行内命中：docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:34 为小节标题行（含「按级别比例」字样）、:36 为逐字裁定行。
- 备注: 本条口径已实际结算过一次：`TG-15` 因审阅期内无未闭环 major/critical 而扣 0、结算全额 2.5 点（docs/iteration/sprint/2026-09-21-sprint-17.md:179）。

### V-034 红线触碰即死机制
- 原文（逐字）: "额外增加红线触碰即死机制（硬核红线举例：**文件丢失、卡片内容飘移、测试结果假绿**）"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:66
- 时点: 2026-09-21
- 主代理归纳: 本条要求新增红线触碰即死机制，硬核红线三条为文件丢失、卡片内容漂移、测试结果假绿，每条必须配可检测判据；触发后的动作是立即停止功能推进、冻结、定位修复并做反向对照，经用户二次确认才恢复。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:70；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:74；scripts/structure-guard.py:899；.github/workflows/ci.yml:170
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后 R1（文件丢失或内容被吞）反复被触碰：Sprint-17 内记 6 次同型（治理模式于第 5 次触发后仍复现），Sprint-18/G2 内又记 2 次（2026-09-25 D4），关闭期再记第 3 至第 6 次，两轮「红线事件 = 0」的目标均记为不达标（docs/iteration/sprint/2026-09-25-sprint-18.md:122；docs/iteration/sprint/2026-09-21-sprint-17.md:150）。
- 备注: R1 的处置档位按 V-035 分阶段（G1 为 S0 告警加当日闭环，G2 为 S1 立即硬停）；Sprint-18 记录的闭环方式是当日修复加全闸门复跑，未见 S1 档要求的硬停与用户二次确认（docs/iteration/sprint/2026-09-25-sprint-18.md:327）。
- 备注: 触发计数的登记与复算入口（Sprint-18 §10 带 `R1` 与 `编辑边界` 标记的事故行）见 docs/iteration/phases/agents-infra/cards/A-M12.md:91；同型事故的逐条描述见 docs/iteration/sprint/2026-09-25-sprint-18.md:330。

### V-035 红线分阶段执行
- 原文（逐字）: "分阶段执行"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:76；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:164
- 时点: 2026-09-21
- 主代理归纳: 本条批准红线三段式分阶段生效：G1 为 S0 观测加告警，G2 为 S1 部分即死（文件丢失即硬停），G3 起为 S2 全量即死；并配灰区规则、升级条款（同一红线单 Sprint 内触发两次即转入治理模式）与恢复判据。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:80；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:122
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——升级条款要求同一红线单 Sprint 内触发两次即「立即」转入治理模式，而 R1 在 Sprint-17 内第 3 次触发时（2026-09-23 D3）的记录是「待 §8.2 决定是否转治理模式」，治理模式实际到第 5 次才触发，未按立即执行（docs/iteration/sprint/2026-09-21-sprint-17.md:371；docs/iteration/sprint/2026-09-21-sprint-17.md:367）。
- 备注: 出处所列两处均在 ±2 行内命中逐字「分阶段执行」（小节标题行与 D2 裁定行）；三段式档位表与配套三条见 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:82；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86。
- 备注: G2 处于 S1 档，R1 触发 2 次的处置记为当日闭环，未见硬停记录（docs/iteration/sprint/2026-09-25-sprint-18.md:122）。

### V-036 不接受只写机械规则
- 原文（逐字）: "只写机械规则"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86
- 时点: 2026-09-25
- 主代理归纳: 本条要求治理模式与机制类提案必须满足六项合格标准（证据、根因、机制、反向对照、在原始事故上验证、复用面），缺项即退回；只写机械规则而不落执行点的提案不予接受。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86；docs/iteration/sprint/2026-09-21-sprint-17.md:164；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:92
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条裁决的既成事实（另一会话的治理建议只写机械规则，用户 2026-09-25 判为 U3 治理建议浅层）见 docs/iteration/sprint/2026-09-21-sprint-17.md:368。

### V-037 人类读得懂硬标准
- 原文（逐字）: "写的代码必须人类读得懂"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:90；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:92
- 时点: 2026-09-21
- 主代理归纳: 本条把「写的代码必须人类读得懂」升为 `code major` 的硬性判定标准，落地形式取 spec 判据加工具闸门；评审在 strict 档下须逐条给出读不懂的原因与改法，工具能自动抓的交给工具。
- 生效状态: 生效
- 证据: agents/policy.json:220；verify/verify_lint.py:143；.github/workflows/ci.yml:124
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:90 为小节标题行、:92 为口径引用行，两处均在 ±2 行内命中逐字。
- 备注: 落地现状为 Python 侧由 C 级可读性棘轮守住（docstring 与行宽四类规则，上限即实测值），非 Python 语言侧按 D4 裁定顺延 G3（docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:39）；顺延期间这些语言的可读性只由评审人工判。
- 备注: 执行期内确有越限并被闸门拦下的实例（折行前超长行越上限）见 docs/iteration/sprint/2026-09-21-sprint-17.md:365。

### V-038 D3 覆盖所有编程语言
- 原文（逐字）: "C 可以，但是**不仅仅是 python 语言，需要覆盖该项目所用到的所有编程语言**"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:93；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:165
- 时点: 2026-09-21
- 主代理归纳: 本条要求可读性闸门覆盖项目用到的全部语言而非仅 Python：G1 只落 Python 侧 `ruff`，JS/JSX、TS/TSX、JSON/YAML、PowerShell、Batch 与 Markdown style 各自的工具闸门按批次顺延，每个新增闸门须带反向对照，工具缺失时 fail-closed 或显式 skipped。
- 生效状态: 生效（非 Python 侧顺延 G3）
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:95；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:108；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:142
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:165 为 D3 裁定的落地摘要行（同义转述「须覆盖项目用到的所有语言（非仅 Python）」），逐字只在同文件 :93。
- 备注: 批次变更不是未执行：多语言 lint 由 G2 改记 G3 候选，依据为用户 2026-09-25 的 B3① 与 §3 对 §6 的范围冲突裁定（docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:12；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:144）。

### V-039 观察期记插入卡额外点/时间
- 原文（逐字）: "同时观察期间**插入卡造成的额外故事点/开发时间**的情况"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:128；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:130
- 时点: 2026-09-21
- 主代理归纳: 本条要求在观察期逐 Sprint 记录插入卡造成的额外故事点与开发时间占用（半日粒度）及触发原因，关闭时成表；插入卡占比越阈值或预计延期时，执行方必须交三选一方案（降范围、延时间、换批次）并附点数与风险对比，由用户裁定。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:132；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:145；docs/iteration/sprint/2026-09-21-sprint-17.md:147；docs/iteration/sprint/2026-09-25-sprint-18.md:123
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:128 为小节标题行、:130 为逐字行，两处均在 ±2 行内命中。

### V-040 D6 先跑跑看
- 原文（逐字）: "先跑跑看，对数字我也没有具体感受"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:170
- 时点: 2026-09-21
- 主代理归纳: 本条要求 G1 的 18 点规模上限不预设结论、先按该点数执行，关闭时用实测数据（插入卡点数、关闭税、有效工作日）回头校准规模上限。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:170；docs/iteration/sprint/2026-09-21-sprint-17.md:161；docs/iteration/sprint/2026-09-21-sprint-17.md:182
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条已由实测收口：18 点的上限不成立，G2 起改为不超过 14 点且每张卡须说得出一日（docs/iteration/sprint/2026-09-21-sprint-17.md:162；docs/iteration/sprint/2026-09-21-sprint-17.md:182）。

### V-041 D7 引入依赖附加前提
- 原文（逐字）: "**引入前提要查清楚依赖有无已暴露的安全风险、数据隐患**"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:171；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:174
- 时点: 2026-09-21
- 主代理归纳: 本条批准为闸门引入新依赖，但附加前提：引入前必须逐条完成六项核查（已知漏洞、安装脚本与构建期执行、数据外发与遥测、许可证、维护活跃度与来源、最小化），任一项不通过即拒绝引入或换等价替代，结果连同核查命令与原始输出记入 Sprint。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:176；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:189；verify/verify_lint.py:41
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:174 为 §2.4 小节标题行（同义转述「用户 2026-09-21 D7 附加前提」），逐字只在同文件 :171；六项核查表见 :178。
- 备注: 前置核查先于引入完成、结论为条件通过与直接拒绝的分档（含无一包六项全绿的事实）见 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:189。

### V-042 查清楚不接受看起来没问题
- 原文（逐字）: "查清楚"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:187
- 时点: 2026-09-21
- 主代理归纳: 本条要求六项核查逐条执行并留证，判断以一手证据为准、不接受「看起来没问题」式结论；核查对象包含官方来源的工具，结论须给出核查命令与原始输出。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:187；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:189；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:1
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字为两字串「查清楚」，篇幅不足以参与引文自动比对，此处由人工核过：该串在出处行内出现，同行并写明不接受「看起来没问题」式的判断。

### V-043 B3① 规模上限与每卡一天
- 原文（逐字）: "哪一天在做它"
- 出处: docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:199；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:12；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:53；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:76；docs/iteration/sprint/2026-09-25-sprint-18.md:6
- 时点: 2026-09-25
- 主代理归纳: 本条把 G2 的规模上限定为不超过 14 点（不含关闭税），并要求每张卡都能说出「哪一天在做它」、同日最多两张卡且合计不超过 2 点；同时维持 `F-AC13/14` 冻结不挪期。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:76；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:55；docs/iteration/sprint/2026-09-25-sprint-18.md:121
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:12、:53 与 docs/iteration/sprint/2026-09-25-sprint-18.md:6 均不含逐字串（分别为取代关系行、`TG-20` 卡行、上限行），逐字在 docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:76 与 docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:199。
- 备注: 兑现情况为规划 12 点加用户插入 `TG-20` 2 点、余量 0（docs/iteration/sprint/2026-09-25-sprint-18.md:121）；六个交付批次落在同一日历日 2026-09-25，按计划书 §4 的口径澄清，D1 至 D6 是批次标签而非日历日（docs/iteration/sprint/2026-09-25-sprint-18.md:55）。

### V-044 开工理由逐字口径
- 原文（逐字）: "**我们需要赶上因治理耽误的进度**，按照我的目标这个项目最终应能**对外包装为一个 agent 供使用/调用**，现在来看**远远不达标**。"
- 出处: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:19；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:122
- 时点: 2026-09-25
- 主代理归纳: 本条确立 G2 的两条纪律：治理只做能提高检查可信度的机制、不做规则堆积；规模受不超过 14 点的硬约束、不得挤占后续功能开发的额度，恢复功能开发的时点由 M1 至 M3 的组合门槛决定。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:19；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:22；docs/iteration/sprint/2026-09-25-sprint-18.md:17
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:122 为 D2 裁定行，只含同义转述「需要赶上因治理耽误的进度」，逐字在同文件 :19。

### V-045 D2 休息日与从今天开工
- 原文（逐字）: "**25-27 都是休息日**……**从今天开始开工**"
- 出处: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:63；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:74；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:122
- 时点: 2026-09-25
- 主代理归纳: 本条裁定 D1 为 2026-09-25（当天开工）、09-26 与 09-27 为休息日、国庆 10-01 至 10-07 不计入有效工作日，六个有效工作日为 09-25、09-28、09-29、09-30、10-08、10-09，D6 为 2026-10-09。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:63；docs/iteration/sprint/2026-09-25-sprint-18.md:19；docs/iteration/sprint/2026-09-25-sprint-18.md:120
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:63 与 :74 均为同义转述（写作「09-26 / 09-27 是休息日」），带省略号的逐字写法只在同文件 :122。
- 备注: G2 关闭期自 2026-09-26 00:51 起算、落在休息日；该次关闭由用户指令「启动G2关闭三查」触发，Sprint-18 §8.1 记为加班，未按违背处理（docs/iteration/sprint/2026-09-25-sprint-18.md:120）。

### V-046 回答关闸读数恢复时点
- 原文（逐字）: "多久后才能重启 sprint17 的关闭判定"
- 出处: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:113
- 时点: 未标注
- 主代理归纳: 本条登记一问一答的口径：Sprint-17 的关闸读数在 `TG-19` M-A 落地后即可重跑，通过标准是恢复后的项数等于该 Sprint 的真实缺口而非项数变少；域的左端取该 Sprint 的作用域 run、右端取该 Sprint 关闭期的最后一条覆盖 run。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:113；docs/iteration/sprint/2026-09-25-sprint-18.md:69；docs/iteration/sprint/2026-09-25-sprint-18.md:94
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条 `原文` 是用户的提问、`时点` 未标注，效力来自答复行给出的口径（docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:113）。

### V-047 D5 TG-10③ 不排期
- 原文（逐字）: "暂不用管也不需要现在就排G3"
- 出处: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:124
- 时点: 2026-09-25
- 主代理归纳: 本条裁定 `TG-10` ③ 不并入 G2、也不现在排 G3：维持 backlog 的「待排期」，不改其 Sprint 列，也不给它分配点数。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:124；docs/iteration/phases/testing-governance/cards/TG-10.md:7；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:38
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 卡侧状态词仍为「待排期」，Sprint 列保留原「③ 看板 UI → Sprint-18（G2）」字样（docs/iteration/phases/testing-governance/cards/TG-10.md:7；docs/iteration/phases/testing-governance/backlog.MD:24）；G2 的卡集与 out-of-scope 两处都不含 `TG-10` ③（docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:38；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:39）。

### V-048 用户追问冲突原因
- 原文（逐字）: "为什么会有冲突"
- 出处: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:130
- 时点: 2026-09-25
- 主代理归纳: 本条登记的是一次追问及其裁定后果：G1 计划书 §3 的 G2 行与最新裁定 §6 冲突时以 §6 为准，G2 收为纯治理 12 点；任何改变「某 Sprint 包含什么」的裁定必须在旧行就地标注取代并写明原因，不得只在文末追加校准节而让旧行留活。
- 生效状态: 生效
- 证据: docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:131；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:15；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:119
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处行 docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:130 为小节标题行，逐字「为什么会有冲突」在 :131 行内（±2 行内命中）；取代关系与各项去向见同文件 :12。

### V-049 A-M11 只记卡不实现
- 原文（逐字）: "这两个方案需要继续调研后再确认怎么做，先记张卡吧"
- 出处: docs/iteration/phases/agents-infra/cards/A-M11.md:7；docs/iteration/phases/agents-infra/backlog.MD:44
- 时点: 2026-09-21
- 主代理归纳: 本条原裁定「只记卡、本轮不实现」，已被 D-250925-04 与 D-250925-06 取代：`A-M11` 计入 G2 卡集 3 点、本轮实现，且执行前必须先跑一次 `tech-research` 前置调研。
- 生效状态: 已被取代 [已被 D-250925-04 取代（2026-09-25）：G2 卡集含 A-M11 3 点、本轮实现；D-250925-06 追加要求先跑 tech-research]
- 证据: docs/iteration/phases/agents-infra/cards/A-M11.md:8；docs/iteration/phases/agents-infra/backlog.MD:44；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:52
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/agents-infra/backlog.MD:44 为索引行的取代标注（同义转述，不含逐字串），逐字只在 docs/iteration/phases/agents-infra/cards/A-M11.md:8，且该行落在出处 :7 的 ±2 行内。
- 备注: 同一句原话在 §4.0 另有已核登记（`D-250921-H6`），其状态与本条一致。

### V-050 A-M11 追加：过程事故与内容丢失防线
- 原文（逐字）: "过程事故也是 A-M11 卡需要解决的问题之一，防范提前避免，尤其是这种可能会造成内容丢失的情况，和之前遇到的多次文件莫名被删除的情况等等"
- 出处: docs/iteration/phases/agents-infra/cards/A-M11.md:123
- 时点: 2026-09-21
- 主代理归纳: 本条把过程事故与「内容丢失、误删」防线并入 `A-M11` 的卡内待产出并要求防患于未然，覆盖「以为提交了其实没有」、强切分支静默丢弃、编辑锚点行被吞、分支操作致目录消失、远端丢件等已发生形态。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/cards/A-M11.md:123；docs/1-WORKFLOW.MD:415；scripts/structure-guard.py:899
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 交付现状：该条仍在 `A-M11` 的「卡内待产出」内、卡状态为进行中（docs/iteration/phases/agents-infra/cards/A-M11.md:7；docs/iteration/phases/agents-infra/cards/A-M11.md:123）。
- 备注: 已落地的执行面是结构守卫的 git 基线档与提交层、CI 层接线，其边界（钩子属便利层、不可跳过层只由 CI 成立）见 docs/iteration/phases/agents-infra/cards/A-M12.md:137；条文见 docs/1-WORKFLOW.MD:417。

### V-051 A-M11 追加：LEARNED…
- 原文（逐字）: "等当前任务完全结束后，把 LEARNED 文档内容完整过一遍，分门别类地补充下目标，除了我说的目标外肯定还有别的。其他文档内容也可以自主阅读查找类似事件的记录，比如 report agent runtime 下的文档什么的。"
- 出处: docs/iteration/phases/agents-infra/cards/A-M11.md:123
- 时点: 2026-09-21
- 主代理归纳: 本条要求在 `A-M11` 卡内增加一条动作：等当前任务完全结束后把 LEARNED 文档内容完整过一遍并分门别类补充目标，同时自主阅读其它文档（如 report agent runtime 下的记录）查找类似事件。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/cards/A-M11.md:123；docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:45；docs/iteration/phases/agents-infra/cards/A-M11.md:7
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 执行面为逐条穷举 3-LEARNED 补全卡目标的独立产物（docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:1），其自述覆盖范围为 `1.1` 至 `1.63`（docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:45）。
- 备注: `1.64` 至 `1.69` 未被该盘点覆盖（docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:230）。

### V-052 子代理派单事故一律入 agent infra…
- 原文（逐字）: "**和子代理派单相关的漏洞/问题/事故今后一律作为 agent infra 的反例留档**"
- 出处: docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:3；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:1；docs/iteration/phases/agents-infra/cards/A-M11.md:23；docs/iteration/phases/agents-infra/cards/A-M11.md:26
- 时点: 2026-09-25
- 主代理归纳: 本条定规：与子代理派单相关的一切漏洞、问题、事故今后一律作为 `agents-infra` 的反例留档，一案一节且六要素齐备（现象、证据、根因、机制、反向对照、复用面），并同步把派生规则写进 `1-WORKFLOW.MD` §6。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:424；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:3；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:89
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/agents-infra/cards/A-M11.md:23 与 :26 不含逐字串（分别为盘点口径行与可核性说明行），规则表述在同文件 :117；逐字命中处为反例档 :3 与 :1。
- 备注: 裁决生效后新增的派单类事故已按本条留档为案例 7 与案例 8（docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:70；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:93），并派生出文件占用表加单文件 `git add`、同一切片只许一个写入者两条规则（docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:88；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:89）。

### V-053 机制缺口同样记为 agent infra 反例
- 原文（逐字）: "**机制缺口同样记录为 agent infra 的反例**"
- 出处: docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:3；docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:1；docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:7
- 时点: 2026-09-25
- 主代理归纳: 本条把留档义务从派单类扩展到闸门与机制类缺陷（自指断言、空转与没查也说查过了、静默放宽、判定域错、读数手抄、上限自证等），落点单列一份反例档，同样一案一节且六要素齐备，并在 §6 登记规则。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:432；docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:3；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:20
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 该档建立时为 10 例，中途独立复核及其后续修复后继续追加，现例数以该文件的小节数为准，末例见 docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:227。
- 备注: 关闭期新增的形态含读数无源、编辑边界类事故无闸门覆盖、同一系统两套评审类定义、改了数据源未跑下游义务（docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:209；docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:218）。

### V-054 A-M12 编辑边界事故族是否成卡
- 原文（逐字）: "对于这一类事故问题的治理是否有卡，如果没有同样作为反例加入 agent infra，历史卡片也是做类似移动分类操作"
- 出处: docs/iteration/phases/agents-infra/cards/A-M12.md:17；docs/iteration/phases/agents-infra/cards/A-M12.md:1；docs/iteration/phases/agents-infra/cards/A-M12.md:7；docs/iteration/phases/agents-infra/backlog.MD:45
- 时点: 2026-09-23（UTC+8）
- 主代理归纳: 本条要求先查清这类编辑边界事故是否已有治理卡；没有卡就把它作为反例加入 `agents-infra` 留档，并对历史卡片做同类的移动与分类操作。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/cards/A-M12.md:17；docs/iteration/phases/agents-infra/cards/A-M12.md:41；docs/iteration/phases/agents-infra/2026-09-23-edit-boundary-incidents-case.MD:1
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/agents-infra/cards/A-M12.md:1 与 :7 不含逐字串（为标题行与状态行），逐字只在同文件 :17；docs/iteration/phases/agents-infra/backlog.MD:45 为索引行（同义转述「用户 2026-09-23 要求成卡」）。
- 备注: 执行结果为成卡 `A-M12`（状态进行中，结构守卫的不可跳过层已交付）并同日建立编辑边界反例档（docs/iteration/phases/agents-infra/cards/A-M12.md:7；docs/iteration/phases/agents-infra/cards/A-M12.md:108）。

### V-055 TG-6 用户要求先做 backlog 卡记录
- 原文（逐字）: "做个 backlog 卡记录先"
- 出处: docs/iteration/phases/testing-governance/cards/TG-6.md:13；docs/iteration/phases/testing-governance/cards/TG-6.md:19
- 时点: 2026-09-20（UTC+8）
- 主代理归纳: 本条要求先把该诉求做成 backlog 卡记录（开卡并进索引）再谈实现，卡内须落用户走查来源、来源类型前缀与网络时间口径。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-6.md:13；docs/iteration/phases/testing-governance/backlog.MD:20；docs/1-WORKFLOW.MD:387
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-6.md:19 为卡正文行（反向对照规则所在段），不含逐字串「做个 backlog 卡记录先」，逐字只在同文件 :13。

### V-056 TG-6 反向对照规则（用户称倒过来试试）
- 原文（逐字）: "倒过来试试"
- 出处: docs/iteration/phases/testing-governance/cards/TG-6.md:19；docs/iteration/phases/testing-governance/cards/TG-6.md:13；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13
- 时点: 2026-09-21
- 主代理归纳: 本条拍板交互与 GUI 类检查的反向对照规则（用户称倒过来试试）：新增检查必须先在未修复或旧实现上跑出 FAIL、证明它能触发目标失效模式，再在修复后转 PASS，并把该反例写进脚本注释与验收指南。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:442；docs/iteration/phases/testing-governance/cards/TG-6.md:19；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-6.md:13 不含逐字串（该行只写「追加反向对照规则」），逐字在同文件 :19 与 docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13。
- 备注: 促成本条裁决的既成事实（`gui_check_s5/s7` 用程序化点击结构上无法触发 F-AC13，该缺陷存活 4 个 sprint）见 docs/1-WORKFLOW.MD:442；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:21。

### V-057 TG-10 账本记录失真立案原话
- 原文（逐字）: "每个 agent 运行时间相比之前怎么短了很多？而且有的是直接中途被停掉了，这些信息让我不太安心"
- 出处: docs/iteration/phases/testing-governance/cards/TG-10.md:13；docs/iteration/phases/testing-governance/backlog.MD:38
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条立案多轮次 agent 的账本记录失真：同一 run 被追加多轮复核时账本不得只留首轮，须支持轮次追加、累计时长与中断事件，使看板能反映真实时长与产出。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-10.md:13；docs/iteration/phases/testing-governance/cards/TG-10.md:22；verify/verify_ledger_rounds.py:9
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/backlog.MD:38 为「启动条件」节的前置闸门条目，不含逐字串也不指向本诉求，逐字只在 docs/iteration/phases/testing-governance/cards/TG-10.md:13（出处首指针命中）。

### V-058 TG-10 同日批准做掉
- 原文（逐字）: "做掉"
- 出处: docs/iteration/phases/testing-governance/cards/TG-10.md:13
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条为同日批准把该诉求做掉：v1 交付 `round`（轮次追加、首轮快照、产出与时长累计）与 `interrupt`（中断原因与影响）两个账本能力，并对历史 run 回填。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-10.md:13；docs/iteration/phases/testing-governance/cards/TG-10.md:7；verify/verify_ledger_rounds.py:9
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字为两字串「做掉」，篇幅不足以参与引文自动比对，此处由人工核过：该串在出处行内出现，同行并写明同日批准。

### V-059 TG-11 规则绕过立案原话（定性很严重）
- 原文（逐字）: "这是一个很严重的问题，规则直接被绕过，在 workflow 记再多也没用，需要单独开卡复盘下｜｜**这是一个很严重的问题，规则直接被绕过，在 workflow 记再多也没用，需要单独开卡复盘下**"（`｜｜` 为分段符）
- 出处: docs/iteration/phases/testing-governance/cards/TG-11.md:18；docs/iteration/phases/testing-governance/cards/TG-11.md:1；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:4；docs/iteration/phases/testing-governance/backlog.MD:25
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条把 2026-09-20/21 的「规则直接被绕过」定性为严重问题并立案 `TG-11`：复盘须区分未读到规则与判断越界、给出可检测性分析、交付可执行闸门而非再写条文，并带反向对照。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-11.md:18；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:4；scripts/agent-ops.py:465；verify/verify_close_readiness.py:859
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后同族形态复发：2026-09-25 的两次 R1 编辑边界事故中均跳过了已交付的结构守卫，记录自述为「规则写了没执行」的第 6、7 个实例（docs/iteration/sprint/2026-09-21-sprint-17.md:366；docs/iteration/sprint/2026-09-21-sprint-17.md:364）。
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-11.md:1 与 docs/iteration/phases/testing-governance/backlog.MD:25 不含逐字串（分别为标题行与索引行，索引行只写「定性为『很严重』」的同义转述），逐字在 docs/iteration/phases/testing-governance/cards/TG-11.md:18 与 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:4。
- 备注: 促成本条立案的既成事实（2026-09-20/21 以修复验证复核名义自选窄范围跑了多轮子代理复核、scope 未来自〇查，用户追问才发现）见 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:23。

### V-060 TG-11 用户明确开卡以后复盘不是现在就做
- 原文（逐字）: "**我说的是开卡以后复盘，不是现在就做**——我担心你现在总结半天，后面出现新情况这个方案又得改。"
- 出处: docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:7；docs/iteration/phases/testing-governance/cards/TG-11.md:27
- 时点: 2026-09-21
- 主代理归纳: 本条划定 TG-11 复盘的时点：复盘在开卡之后的卡执行阶段进行、不在立案当场做，理由是方案可能随新情况变化而需要改写；立案当场只固化可核事实。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:7；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:8；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:3
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-11.md:27 不含逐字串（该行只有同义转述「用户明确『开卡以后复盘，不是现在就做』」），逐字在 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:7。
- 备注: 时点纪律的兑现：立案当日只产出证据台账并把根因与对策标为初稿假设，复盘定稿在卡执行时（2026-09-23）成文（docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:8；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:3）。

### V-061 TG-11 D1 先答"是"
- 原文（逐字）: "**是**"
- 出处: docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:98；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:96
- 时点: 2026-09-21
- 主代理归纳: 本条是用户对 `TG-11` 证据台账 D1 的第一答：同意 M1+M2+M3 在 Sprint-16 关闭前落地；该答当日即被用户自己修订为"只留方案、不动代码"，因此本条不再约束任何实现时点，实现时点改由 `V-062` 与 `TG-11` 复盘定稿决定。
- 生效状态: 已被取代 [已被 V-062 取代（2026-09-21）：用户先答"是"、随即修订为"方案保留、不做任何代码改动"，M1~M4 仅作方案留存、实现推迟到正式复盘之后]
- 证据: docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:98（"用户先答"**是**"，**随即修订**"）；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:96（"用户先答两项，随后**修订 D1**"）；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:3（定稿日期 2026-09-23，实现改在此后）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字为单字串「是」，篇幅不足以参与引文自动比对，此处由人工核过：该串在 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:98 行内出现（`用户先答"**是**"`）；出处另一指针同文件 :96 只有同义转述「用户先答两项」、不含逐字，真实逐字在 :98。

### V-062 TG-11 D1 修订：方案保留、不做代码改动
- 原文（逐字）: "**刚刚你建议的方案可以保留，但是不要做任何代码改动**"
- 出处: docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:98；docs/iteration/phases/testing-governance/cards/TG-11.md:27
- 时点: 2026-09-21
- 主代理归纳: 本条把 D1 的方案处置定为"只留方案、不动代码"：M1~M4（scope 来源入账本、关闭前置闸门、§9 结构化 run 表、接入 CI）作为方案参数留在卡内，Sprint-16 期间不得改任何代码，实现等 `TG-11` 正式复盘定稿后另开；复盘前已起草的闸门与断言全部回退。
- 生效状态: 生效（S16 期内禁令已按本条履行完毕；实现按本条"待复盘后"于 Sprint-17 落地）
- 证据: docs/iteration/phases/testing-governance/cards/TG-11.md:27（"**本轮代码零改动**（曾起草 `scripts/agent-ops.py` 的 `--scope-source` 闸门与 `verify_agentops.py` 断言，**已全部回退**，仅保留本卡与证据台账）"）；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:44（M1 已落地：register 新增 --scope-source / --deviation，评审类 role 二者必居其一否则 CLI 拒绝）；scripts/agent-ops.py:479（CLI 侧实现点）；verify/verify_agentops.py:444（UC-14 评审 run 无 scope 来源即拒绝）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条裁决的既成事实（裁决前）：我按方案起草了 `scripts/agent-ops.py` 的 `--scope-source` 闸门与 `verify_agentops.py` 断言，用户随即要求"不要做任何代码改动"，草案已全部回退（docs/iteration/phases/testing-governance/cards/TG-11.md:27 末句"已全部回退，仅保留本卡与证据台账"）。
- 备注: 复盘对 D2 口径的落地说明：取等价形态"无理由即拒绝、带 --deviation 即放行并留痕"，未引入 --force，理由是多一条绕过面（docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:49）。

### V-063 TG-12 文档内容漂移开卡原话
- 原文（逐字）: "我想从 sprint17 和以前的开发过程发现的文档内容漂移问题也足够开个卡做复盘了，把类似问题一并加到 backlog 中吧"
- 出处: docs/iteration/phases/testing-governance/cards/TG-12.md:13；docs/iteration/phases/testing-governance/cards/TG-12.md:1；docs/iteration/phases/testing-governance/cards/TG-12.md:19；docs/iteration/phases/testing-governance/backlog.MD:26
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条要求把"文档内容漂移"（同一事实抄进多处、源头变更后无重生成机制）立成一张复盘卡，并把同类问题一并收进 backlog；执行面 = 卡 `TG-12` 立案 + backlog 索引行，复盘本体仍是候选、Sprint 排期已由 G2 改为 G3 候选。
- 生效状态: 生效（开卡与入索引已交付；复盘本体未开始）
- 证据: docs/iteration/phases/testing-governance/cards/TG-12.md:13（来源行=用户原话）；docs/iteration/phases/testing-governance/cards/TG-12.md:7（状态=候选（用户 2026-09-21 要求开卡复盘；同类问题已足够成卡））；docs/iteration/phases/testing-governance/backlog.MD:26（索引行，Sprint 列=G3 候选）；verify/verify_derived_numbers.py:1（同类"手抄派生数字"的已落地闸门）；docs/iteration/phases/testing-governance/cards/TG-12.md:16（G3 候选取代原 Sprint-18 写法）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后同族形态复发：2026-09-25 关闭期实测"同一批闸门在同一天的 4 份文档里并存 3~4 个读数、无一与工具一致"，根因记为一查 `run-2026-09-25-doc-audit-070` finding 1/2（verify/verify_derived_numbers.py:2；verify/verify_derived_numbers.py:9）；同批 finding 4 另抓出卡状态行与 Sprint 看板直接冲突（docs/iteration/phases/testing-governance/cards/TG-15.md:7）。
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-12.md:1 与 :19 只含节引（标题行在"文档内容漂"处截断；:19 的引文止于"复盘了"、缺后半句），docs/iteration/phases/testing-governance/backlog.MD:26 为瘦索引行（同义截断），逐字全串只在 docs/iteration/phases/testing-governance/cards/TG-12.md:13。
- 备注: 促成本条立案的既成事实（裁决前）：同类"数字/状态/结论副本过期"已反复发生多波（Sprint-7 起例行勘误、doc-audit 026、Sprint-15 日期整体漂移、Sprint-16 内修三轮），逐波清单在 docs/iteration/phases/testing-governance/cards/TG-12.md:19。

### V-064 TG-12 N7 一卡一文档原话
- 原文（逐字）: "`phases` 下的所有文件夹，单个卡片应该对应且唯一对应一个独立文档。现在卡片内容全都记录在 backlog 中，有的卡片内容散落在 sprint 文档中到处都是。一旦卡片内容更新了其他几处万一有的地方漏了就直接造成文档内容漂移｜｜单个卡片应该对应且唯一对应一个独立文档｜｜`phases` 下的所有文件夹，**单个卡片应该对应且唯一对应一个独立文档**。现在卡片内容全都记录在 backlog 中，有的卡片内容散落在 sprint 文档中到处都是。一旦卡片内容更新了其他几处万一有的地方漏了就直接造成文档内容漂移"（`｜｜` 为分段符）
- 原文缺失（二手转述）: "**✅ 用户 2026-09-21 决定：N7 归入本卡（TG-12）正式执行时一并做**（不在 Sprint-17 之前单独立项）；**术语约定已即时生效**——`台账` 仅指独立文件、单元格内清单一律称"卡内实例清单"，并连同引用纪律写入 `1-WORKFLOW.MD` §3（2026-09-21）。｜｜**⤴ 2026-09-21 用户决定：机制候选 `N7`（一卡一文档 + backlog 瘦索引 + 索引 lint）已提升为独立卡 `TG-14`**——本卡机制清单收窄为 **N1~N6**（派生事实/漂移闸门/生成式状态报告/doc-audit 增补/写作规范/TG-11 合流），N7 的 4 类证据与迁移方案随卡移交 `TG-14`，避免两卡重复拥有同一机制。"
- 出处: docs/iteration/phases/testing-governance/cards/TG-12.md:22；docs/iteration/phases/testing-governance/cards/TG-14.md:21；docs/iteration/phases/testing-governance/cards/TG-14.md:8；docs/1-WORKFLOW.MD:407；docs/1-WORKFLOW.MD:405
- 时点: 2026-09-21
- 主代理归纳: 本条把"卡片 ↔ 文档"的拓扑定死：`phases` 下每张卡对应且唯一对应一个独立文档，卡片正文独立成文、`backlog.MD` 退化为瘦索引、Sprint 文档只按卡号引用，并要求该拓扑有可执行 lint 兜住；执行结果 = `TG-12` 的机制候选 N7 提升为独立卡 `TG-14` 并完成迁移与索引化。
- 生效状态: 生效（已交付）
- 证据: docs/iteration/phases/testing-governance/cards/TG-14.md:7（✅ 完成（2026-09-23，D3）…verify_card_index.py 默认档 PASS）；docs/1-WORKFLOW.MD:407（用户原话条文）；docs/iteration/phases/testing-governance/backlog.MD:11（本表仅作瘦索引，判据 verify/verify_card_index.py）；verify/verify_card_index.py:11（判据①一一对应：索引行 ↔ cards/<卡号>.md 双向一致）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-14.md:8 只有同义转述（"（原状态：**候选**——用户 2026-09-21 拍板"提升为独立卡"。**状态由本文件承载，瘦索引行同步**。）"），不含逐字；逐字在 docs/iteration/phases/testing-governance/cards/TG-12.md:22、docs/iteration/phases/testing-governance/cards/TG-14.md:21 与 docs/1-WORKFLOW.MD:407（后者落在出处 :405 的 ±2 行内）。
- 备注: 同批立规的术语面（`台账` 只指独立文件）见 docs/1-WORKFLOW.MD:409。
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）

### V-065 用户追问实例台账是啥文档
- 原文（逐字）: "你经常说实例台账我咋没找到是啥文档"
- 出处: docs/iteration/phases/testing-governance/cards/TG-12.md:22；docs/iteration/phases/testing-governance/cards/TG-14.md:21
- 时点: 2026-09-21
- 主代理归纳: 本条是一次术语澄清追问：用户问"实例台账"到底指哪份文档；答复把术语定死为 `台账` 只指独立文件、写在卡片单元格里的清单一律叫"卡内实例清单"，并写明 `TG-12` 没有独立台账文件。
- 生效状态: 生效（术语口径已落条文）
- 证据: docs/1-WORKFLOW.MD:409（术语（强制）：`台账` 只指独立文件…2026-09-21 用户指出）；docs/iteration/phases/testing-governance/cards/TG-12.md:22（"术语见 `1-WORKFLOW.MD` §6 文档规范：`台账` 仅指独立文件；**本卡无独立台账文件**"）；docs/iteration/phases/testing-governance/cards/TG-14.md:21（"另追问"你经常说实例台账我咋没找到是啥文档""）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条属提问类条目（用户只追问文档归属、未下达新裁决）：其效力内容是"答复必须落成可核的术语条文"，现由 docs/1-WORKFLOW.MD:409 承载；§4.3 另有同题索引 A-213。
- 备注: 出处两指针行内均含逐字（docs/iteration/phases/testing-governance/cards/TG-12.md:22；docs/iteration/phases/testing-governance/cards/TG-14.md:21）。

### V-066 TG-13 账本测量化做成新卡
- 原文（逐字）: "账本测量化……做成新卡 TG-13"
- 出处: docs/iteration/phases/testing-governance/cards/TG-13.md:13；docs/iteration/phases/testing-governance/cards/TG-13.md:1；docs/iteration/phases/testing-governance/cards/TG-13.md:19；docs/iteration/phases/testing-governance/backlog.MD:27
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条把"账本测量化"（时长/轮次/账本↔产物双向一致）判为单开一张卡 `TG-13`、不并入 `TG-10`；交付面 = 新闸门 `verify/verify_ledger_measurement.py` 与口径唯一真源 `agents/policy.json` 的 `ledger_measurement` 键，缺值必须显式 `unknown`、禁止用 0.00 或整十分钟退化值冒充。
- 生效状态: 生效（卡已完成）
- 证据: docs/iteration/phases/testing-governance/cards/TG-13.md:7（已完成（2026-09-25，Sprint-17 D3）…口径真源为 agents/policy.json::ledger_measurement）；docs/iteration/phases/testing-governance/backlog.MD:27（索引行 ✅ 完成）；verify/verify_ledger_measurement.py:12（口径唯一真源）；agents/policy.json:21（键 ledger_measurement）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-13.md:1 与 :19 只有同义转述（"用户 2026-09-21 拍板"开新卡"，而非并入 TG-10"），docs/iteration/phases/testing-governance/backlog.MD:27 为瘦索引行（同义转述"拍板『开新卡』"），逐字只在 docs/iteration/phases/testing-governance/cards/TG-13.md:13。
- 备注: 交付边界（卡内自述）：中文 `task_id` 乱码未处理，与看板的合流只做了"数字可信"一半（docs/iteration/phases/testing-governance/cards/TG-13.md:52）。

### V-067 TG-13 拍板"开新卡"
- 原文（逐字）: "开新卡"
- 出处: docs/iteration/phases/testing-governance/cards/TG-13.md:1；docs/iteration/phases/testing-governance/cards/TG-13.md:19；docs/iteration/phases/testing-governance/backlog.MD:38
- 时点: 2026-09-21
- 主代理归纳: 本条是用户对"账本测量化并入 `TG-10` 还是单开卡"的拍板：开新卡（`TG-13`）、不并入 `TG-10`；卡已开并已完成。
- 生效状态: 生效（已交付）
- 证据: docs/iteration/phases/testing-governance/cards/TG-13.md:1（标题即"（用户 2026-09-21 拍板"开新卡"，而非并入 TG-10）"）；docs/iteration/phases/testing-governance/cards/TG-13.md:7（已完成（2026-09-25，Sprint-17 D3））；docs/iteration/phases/testing-governance/backlog.MD:27（索引行 ✅ 完成）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字为三字串「开新卡」，篇幅不足以参与引文自动比对，此处由人工核过：该串在出处 docs/iteration/phases/testing-governance/cards/TG-13.md:1 与同文件 :19 行内均出现；出处第三个指针 docs/iteration/phases/testing-governance/backlog.MD:38 是「启动条件」节的前置闸门行（F2 验收），与本案无关且不含逐字，其邻行 :39 只写"2026-09-21 用户拍板开卡"的同义转述。

### V-068 TG-14 N7 是否提升为独立卡
- 原文（逐字）: "N7 是否提升为独立卡：可以"
- 出处: docs/iteration/phases/testing-governance/cards/TG-14.md:15；docs/iteration/phases/testing-governance/cards/TG-14.md:8
- 时点: 2026-09-21（UTC+8）
- 主代理归纳: 本条是用户对 `TG-12` 机制候选 N7 的处置拍板"可以"：N7 提升为独立卡；执行结果 = 独立卡 `TG-14`（一卡一文档 + backlog 瘦索引 + 索引 lint），2026-09-23 D3 完成，索引 lint 已在默认档生效。
- 生效状态: 生效（已交付）
- 证据: docs/iteration/phases/testing-governance/cards/TG-14.md:15（来源行=用户原话）；docs/iteration/phases/testing-governance/cards/TG-14.md:7（✅ 完成（2026-09-23，D3））；docs/iteration/phases/testing-governance/backlog.MD:28（索引行 ✅ 完成（2026-09-23，D3））；verify/verify_card_index.py:1（TG-14④ 卡索引 lint）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-14.md:8 只有同义转述（"用户 2026-09-21 拍板"提升为独立卡""），逐字只在同文件 :15；§4.3 另有同题索引 A-088。

### V-069 TG-14 追加交付：报告之间的关系链
- 原文（逐字）: "注意报告之间的因果关系/相关笔记关系链的梳理，如果有文档结构治理的卡将这一要求补充进去"
- 出处: docs/iteration/phases/testing-governance/cards/TG-14.md:28；docs/iteration/phases/testing-governance/cards/TG-14.md:26
- 时点: 2026-09-25
- 主代理归纳: 本条要求给报告/分析类文档补"关系链"治理：梳理报告之间的因果关系与取代关系，有文档结构治理卡就并进去；落点 = `TG-14` 的追加交付判据（头部一行机器可读的关系声明、关系成对闭环、无孤儿无环、被取代稿双向声明、反向对照），呈现并入 `TG-16` 由声明自动生成关系图、不手绘。
- 生效状态: 生效（要求在位、尚未整体交付）
- 证据: docs/iteration/phases/testing-governance/cards/TG-14.md:28（用户原话）；docs/iteration/phases/testing-governance/cards/TG-14.md:32（追加判据（与 ④ 同族，纳入 `verify_card_index.py` 或同批 lint））；docs/iteration/phases/testing-governance/cards/TG-14.md:41（本条并入本卡、完成时同步更新 §证据与 `verify/README.md`）；docs/iteration/phases/testing-governance/cards/TG-14.md:39（呈现并入 TG-16，由关系声明自动生成关系图）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 交付现状（本次核对时点）：`verify/verify_card_index.py` 内检索 `supersedes`/`derived-from`/`input-to` 零命中，追加判据 ①~⑤ 尚无执行点；仓内只有一行 `> 关系：` 声明（docs/iteration/phases/agents-infra/cards/A-M11.md:115），`TG-16` 的自动关系图随该卡（候选、待排期）未产出。

### V-070 TG-15 P1 批准
- 原文（逐字）: "P1：可以，建议复查下类似场景的硬编码问题"
- 出处: docs/iteration/phases/testing-governance/cards/TG-15.md:13；docs/iteration/phases/testing-governance/cards/TG-15.md:1；docs/iteration/phases/testing-governance/cards/TG-15.md:19；docs/iteration/phases/testing-governance/backlog.MD:29
- 时点: 2026-09-23（UTC+8）
- 主代理归纳: 本条批准 `TG-15` 方案 P1（三条不变式 C1/C2/C3 替换逐场景判据，需求只来自 `agents/fanout.json` 与 spec frontmatter 两个数据源），并追加要求"复查类似场景的硬编码问题"；落点 = 硬编码政策闸门 `verify/verify_no_policy_hardcode.py` 与"政策必须落数据文件"的条文，存量硬编码逐处改造。
- 生效状态: 生效（已落地）
- 证据: docs/iteration/phases/testing-governance/cards/TG-15.md:13（来源行=用户原话）；docs/iteration/phases/testing-governance/cards/TG-15.md:7（✅ 实质完成…判据 ①~⑤ + ⑦⑧ 已落地）；verify/verify_no_policy_hardcode.py:1（TG-15⑦ 硬编码政策探测器）；verify/verify_no_policy_hardcode.py:9（政策统一落在三处数据）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-15.md:1（标题行，在"批准 P1="可以"处截断）、同文件 :19（正文行）与 docs/iteration/phases/testing-governance/backlog.MD:29（瘦索引行）只含节引或同义转述，逐字只在同卡 :13。
- 备注: 卡内自陈的未交付项：⑥（覆盖检查接入 CI push 级）状态为"已裁定顺延"，既非完成也非待办（docs/iteration/phases/testing-governance/cards/TG-15.md:7）。

### V-071 TG-15 P2 选型与担心
- 原文（逐字）: "P2：C3-T，但是有个担心，**是否归属表未及时更新同样导致 C3 闸门失效**"
- 出处: docs/iteration/phases/testing-governance/cards/TG-15.md:13
- 时点: 2026-09-23（UTC+8）
- 主代理归纳: 本条是用户对 P2 的选型与担心：选 C3-T，并要求把"归属表未及时更新"本身当作 C3 闸门失效的形态来防；落点 = `verify/verify_close_readiness.py` 的 C3-T 例外表三件套（覆盖默认由 run 数据计算、例外 sha 钉死不许通配、表落后默认 FAIL 并逐条点名未归属 sha，失效方向反转），并接入 CI。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-15.md:13（来源行=用户原话）；verify/verify_close_readiness.py:27（C3-T 例外表（用户 2026-09-23 选型 + 对"表过期"的担心）…）；verify/verify_close_readiness.py:16（C3 覆盖闭环：git rev-list <锚点>..<HEAD> 的每个提交必须有归属）；docs/iteration/phases/testing-governance/cards/TG-15.md:22（④ … (c) 表落后 = 默认 FAIL 并逐条点名未归属 sha）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处只有单一指针 docs/iteration/phases/testing-governance/cards/TG-15.md:13，逐字在该行内命中；用户担心的那张"归属表"的机器可读落点由政策数据承载，具体键与当前值一律以现跑 `verify/verify_close_readiness.py` 的输出为准。

### V-072 TG-15 点数不减、改扣分条件
- 原文（逐字）: "不减点、改扣分条件"
- 出处: docs/iteration/phases/testing-governance/cards/TG-15.md:7；docs/iteration/phases/testing-governance/cards/TG-15.md:23；docs/iteration/phases/testing-governance/backlog.MD:29；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:37；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:70；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:179
- 时点: 2026-09-25
- 主代理归纳: 本条裁定 `TG-15` 的 2.5 点不减、改为扣分条件（未闭环的 critical/major 按级别继续扣）；口径落成政策数据 `agents/policy.json` 的 `deduction_rates` 键，由 `verify/verify_deduction_rates.py` 守门，比例数值不得写进文档或脚本。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/cards/TG-15.md:7（**点数 2.5 不减**（用户 2026-09-25 拍板：不减点、改扣分条件；见 §4 D3 行））；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:37（…遵用户 2026-09-25"不减点、改扣分条件"…）；agents/policy.json:322（键 deduction_rates）；verify/verify_deduction_rates.py:4（真源 = agents/policy.json::deduction_rates）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条与 §3 `V-027` 为同一句原话的重复登记（两处编号，非冲突）。
- 备注: 出处其余四个指针只有同义转述：docs/iteration/phases/testing-governance/cards/TG-15.md:23、docs/iteration/phases/testing-governance/backlog.MD:29、docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:70、docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:179 都写作"不减"＋"改为扣分条件"的改写；逐字「不减点、改扣分条件」在出处首指针 docs/iteration/phases/testing-governance/cards/TG-15.md:7 与 docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:37 行内命中。

### V-073 TG-16 审查流程过一遍 → HTML 汇报
- 原文（逐字）: "先这样做吧，我想需要对现有审查流程和具体策略内容找时间整体过一遍 记张卡把这些内容规则流程梳理作为一个backlog，输出图文并茂容易理解的html汇报文件｜｜我想需要对现有审查流程和具体策略内容找时间整体过一遍，记张卡把这些内容规则流程梳理作为一个 backlog，**输出图文并茂容易理解的 html 汇报文件**"（`｜｜` 为分段符）
- 出处: docs/iteration/phases/testing-governance/cards/TG-16.md:13；docs/iteration/phases/testing-governance/cards/TG-16.md:1；docs/iteration/phases/testing-governance/cards/TG-16.md:19；docs/iteration/phases/testing-governance/backlog.MD:30
- 时点: 2026-09-23（UTC+8）
- 主代理归纳: 本条要求把"现有审查流程与具体策略内容整体过一遍"开成 backlog 卡，交付物是图文并茂、容易理解的 HTML 汇报（单文件、离线可开、零外链），并让每条规则标出执行点；卡 `TG-16` 已开。
- 生效状态: 生效（开卡已交付；HTML 交付物与卡本体未产出）
- 证据: docs/iteration/phases/testing-governance/cards/TG-16.md:13（来源行=用户原话）；docs/iteration/phases/testing-governance/cards/TG-16.md:7（状态=候选（用户 2026-09-23 要求开卡））；docs/iteration/phases/testing-governance/cards/TG-16.md:16（Sprint 列=待排期，HTML 定稿放 G1 关闭后）；docs/iteration/phases/testing-governance/cards/TG-16.md:22（每条规则必须标注 执行点=）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-16.md:1 与 docs/iteration/phases/testing-governance/backlog.MD:30 只含节引（标题行与瘦索引行都在"我想需要对现有审查"处截断）；逐字第一段落在同卡 :13、第二段落在同卡 :19，两段不同行。§4.3 另有同题索引 A-093 与 A-231。
- 备注: 关联：`TG-14` 追加交付的"报告关系图由声明自动生成、不手工画"并入本卡呈现（docs/iteration/phases/testing-governance/cards/TG-14.md:39）。

### V-074 TG-20 登记册与提问纪律当场要求（三段）
- 原文（逐字）: "我们之间的对话中把所有 clarification questions 找时间收集整理下，原记录放在 `docs/6-DECISIONS.md` 中……还要标记生效状态和证据，验证时间戳｜｜；｜｜每次你问我问题不带上下文的时候我就得翻我们的对话记录，还得提醒你是不是之前做过类似确认/是不是缺少啥内容，我已经厌倦了这么做｜｜注意还原事实，原文必须保留，原文和你自己总结/归类的内容做清晰区分"（`｜｜` 为分段符）
- 出处: docs/iteration/phases/testing-governance/cards/TG-20.md:13；docs/iteration/phases/testing-governance/cards/TG-20.md:1；docs/iteration/phases/testing-governance/cards/TG-20.md:7；docs/iteration/phases/testing-governance/cards/TG-20.md:20
- 时点: 2026-09-25（UTC+8）
- 主代理归纳: 本条是登记册与提问纪律的立卡裁决：把主代理与用户之间的全部 clarification questions 逐字收进 `docs/6-DECISIONS.md` 并逐条标生效状态、证据、验证时间戳；原文区只放逐字引用、归纳另立一行；据此派生提问纪律（提问前先查登记册，提问自带已裁决项、未被覆盖的原因、证据）。
- 生效状态: 生效（机制已交付；§4.1 逐条回填仍在进行）
- 证据: verify/verify_decision_register.py:2（决策登记册机检（TG-20 ③④⑤，2026-09-25 D6））；docs/1-WORKFLOW.MD:433（§6 第 9 条 提问纪律：提问前必须先查登记册、必须自带三件事）；docs/iteration/phases/testing-governance/cards/TG-20.md:33（③ 机检判据：新闸门 verify/verify_decision_register.py 已进 gate_integrity.guard_required 与 CI）；docs/6-DECISIONS.md:5（原文与归纳的分离规则）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/testing-governance/cards/TG-20.md:1（标题行）、:7（卡状态行，只写剩余项是 §4.1 的条目回填）与 :20（问题描述行）都只含节引或同义转述；逐字三段全部落在同卡 :13 一行内。
- 备注: 交付现状：卡状态为进行中，剩余项即 §4.1 逐条回填（docs/iteration/phases/testing-governance/cards/TG-20.md:7）；本批（V-061~V-090）即该回填的一批。§4.3 另有同题索引 A-169。
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）

### V-075 用户指出另一会话误开 D2/D3 并要求接手
- 原文（逐字）: "另一个对话（**部署Codex Harness并查最佳实践**）误开启了 Sprint-17 的 D2/D3 任务，交付质量不尽如人意"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:4
- 时点: 2026-09-25
- 主代理归纳: 本条确认另一会话越权开启了 Sprint-17 的 D2/D3 且交付质量不达标，并要求本会话接手该对话下的全部工作（含已完成结果、待办、待用户确认项）；接手后的第一件事是先做 D2/D3 的独立审核，再与用户一起规划下一步。
- 生效状态: 生效（接手与独立审核均已执行）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:4（触发：用户 2026-09-25 指出…并要求本会话**接手全部工作**）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:20（用户分工决定（同日））；docs/iteration/sprint/2026-09-21-sprint-17.md:8（执行会话（2026-09-25 起，用户裁定）：本 Sprint 由本会话单一负责）；docs/iteration/sprint/2026-09-21-sprint-17.md:368（非红线（流程/协作事故：并行写入 + 越权开工）：另一会话误开启并执行了本 Sprint 的 D2/D3）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列的这条原话在 docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:4 行内逐字命中（该行同时记"并要求本会话接手全部工作"）；该行是主代理在文档内对用户话的转写，同文件 :5 自陈本会话读不到那个对话的记录。§4.3 另有同题索引 A-113 与 A-114。
- 备注: 遗留债（非违背）："执行会话"须成为一等字段并并入所有权/覆盖闸门（docs/iteration/sprint/2026-09-21-sprint-17.md:8）。

### V-076 用户判定 U1：重复出现的低级错误
- 原文（逐字）: "**重复出现在我看来不应该犯的低级错误**"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:15
- 时点: 2026-09-25
- 主代理归纳: 本条是用户对另一会话事故形态的第一条判定：同类低级错误重复出现即视为事故复发，处置不得停在"记录 + 写规则"，必须升级为工具约束，并能在原始事故输入上复现拦截。
- 生效状态: 生效（工具约束已交付；判定本身在位）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:15（U1 行=用户原话）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:73（U1 低级错误重复…① 复发即**升级为工具改造**…② 必须在原始事故上复现拦截）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:238（U1…**成立**（且已由 §2.2.1 自动触发治理模式））；docs/iteration/phases/agents-infra/cards/A-M12.md:45（已交付（2026-09-25，工具约束，非"规则 + 反例文档"））；docs/iteration/phases/agents-infra/cards/A-M12.md:96（① 用 R1 的真实输入复跑**必须被拦下** → `--replay` 全绿（**已达成**））
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后同型形态复发：`A-M12` 已交付"结构性编辑前后各跑一次 `structure-guard.py`"之后，R1 编辑边界事故仍连续发生（关闭期第 6 次、关闭后第 7 次，均由主代理所犯），关闭期一轮自述为"同型 4 次、全部靠 `read` 复核发现、闸门一条都抓不到"（docs/iteration/sprint/2026-09-21-sprint-17.md:366；docs/iteration/sprint/2026-09-21-sprint-17.md:364；docs/iteration/sprint/2026-09-25-sprint-18.md:330；docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD:20）。
- 备注: 促成本条判定的既成事实（裁决前）：R1（编辑边界吃内容）在本 Sprint 内的多次实例、`card_index` 套件默认模式恒真、`md_tables` 判据②分支不可达、自写核对器连错多版，逐条见 docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:238。
- 备注: 同族形态另有独立登记：规则绕过族的同两次 R1 实例已记在 §4.1 `V-059` 的违背事故行（docs/6-DECISIONS.md:901），本条按"同型复发"口径另记，两处指向同一事故行的不同判据面。

### V-077 用户判定 U2：延期请求
- 原文（逐字）: "开发开发着跑出来新增需要修复问题的卡，**按现有工作量判断项目要延期**，**找我要权限证明可以延期**"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:16
- 时点: 2026-09-25
- 主代理归纳: 本条是用户对第二类问题的判定：新增修复卡导致需要延期时，执行者不得把决策推回用户，必须按变更协议给出三选一方案（降范围／延时间／换批次）并附点数与风险，决定权在用户；插入卡占比越过计划口径即自动触发再基线提案。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:16（U2 行=用户原话）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:74（U2…③ 变更卡必须提**三选一方案**（降范围／延时间／换批次）+ 点数与风险，**决定权在用户**）；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:145（变更／延期协议（2026-09-25 补，用户 U2 判定）…**决定权始终在用户**）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:239（U2…**成立且更严重**：不是"请示延期"，而是**用不成立的事实把账做平**）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条判定的既成事实（裁决前）：D3 燃尽以"`TG-15`⑥ 已由 CI #206 闭环"为由减 2.5 点，而该依据经复核为假（docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:239）；复核结论与更正见 docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:37。
- 备注: 同义务另有独立登记：§4.1 `V-039` 记同一三选一要求且违背事故同为"无（未发现）"（docs/6-DECISIONS.md:671）；本条按 U2 判定面登记，两处互指、不判取代。

### V-078 用户判定 U3：治理建议浅层
- 原文（逐字）: "问题超过五次按规则要治理，**给的建议方案是写机械规则就行**"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:17
- 时点: 2026-09-25
- 主代理归纳: 本条是用户对第三类问题的判定：问题触发治理后，治理产出不得只写机械规则；合格产出必须给出证据、根因、机制、反向对照、在原始事故上验证、复用面，缺项即退回。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:17（U3 行=用户原话）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:75（U3…⑤ 见 §3.5 的**治理产出合格标准**…"只写规则"一律判不合格）；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86（升级条款…**治理模式的提案必须满足 6 项合格标准**…**缺项即退回；不接受"只写机械规则"**（用户 2026-09-25 U3 判定））；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:240（U3…**成立**：机制数量够、**强度不够**）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条判定的既成事实（裁决前）：治理相关闸门"三条可被一次数据编辑静音"（棘轮注入仍 PASS、豁免一条静音、套件档恒真），且 `A-M12` 当时只有规则与反例文档（docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:240）。
- 备注: 同一裁决在 §4.1 另有条目 `V-036`（不接受只写机械规则，违背事故同为"无（未发现）"，docs/6-DECISIONS.md:635）：两处互指、不判取代。

### V-079 用户判定 U4：态度敷衍
- 原文（逐字）: "**态度敷衍**"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:18
- 时点: 2026-09-25
- 主代理归纳: 本条是用户对第四类问题的判定：把不可核的"态度敷衍"操作化为可核的产出缺项——缺证据、缺反例、缺选项、缺取舍、缺失败判据，并要求每份治理提案自证能拦住原事故，不满足即退回重做。
- 生效状态: 生效
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:18（U4 行=用户原话）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:76（U4 态度敷衍…操作化为**产出缺项**…⑥ 每份治理提案**必须自证"能拦住原事故"**）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:86（5. **原始事故验证**：把本次事故的输入**原样喂给新机制**，必须被拦下）；docs/1-WORKFLOW.MD:440（读数必须有来源：手抄禁止，编造更禁止（2026-09-26 立规，我自己的事故））
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后产出缺项复发：2026-09-26 关闭期把仍在跑的复核 run 的分级结论先写成成品数字（"那组数字没有任何来源"），同型第二次被判"过度声称"，并直接导致用户对严重性判断失去信任（docs/iteration/sprint/2026-09-25-sprint-18.md:332；docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD:53；docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD:86）。
- 备注: 促成本条判定的既成事实（裁决前）：产出中存在当天就存在的真缺陷被闸门放行、死旋钮、文档引用了不存在的政策键与不存在的自检开关（docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:241）。
- 备注: 本条判定的后续可核化落点："读数必须有来源"入 docs/1-WORKFLOW.MD:440；用户因本形态撤回自定"债"口径（docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD:86）。

### V-080 用户分工决定：接手该对话下所有工作
- 原文（逐字）: "全全由你接受这个对话下的所有工作，包括已完成结果、你自己的待办、待我确认的条例等等，**先做 D2、D3 的独立审核**，再和我一起规划下一步。"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:20
- 时点: 2026-09-25
- 主代理归纳: 本条把工作收归定死：该对话下的全部工作（已完成结果、主代理自己的待办、待用户确认的条例等）由本会话接手，次序是先做 D2/D3 的独立审核、再与用户一起规划下一步。
- 生效状态: 生效（接手与独立审核均已完成）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:20（用户分工决定（同日））；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:1（D2/D3 独立审核报告（合成）——事实、分级发现、行动链）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:77（4. 行动链（依赖排序；每步都要"反向对照 + 更新 §3/§7/§10/燃尽 + 显式路径提交"））；docs/iteration/sprint/2026-09-21-sprint-17.md:8（本 Sprint 由本会话单一负责；此前 D2/D3 由另一会话执行，其提交已收归、待独立审核）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:186（已完成结果（接收）：该会话的提交**已独立审核完成**）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 逐字的"全全由你接受"保留了用户原口语重复，未做更正；出处行内逐字可核（docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:20）。

### V-081 需用户转达给另一会话的停止指令
- 原文（逐字）: "D2/D3 已由主会话收归，请停止对 `windows` 分支的写入"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:96；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:190
- 时点: 2026-09-25
- 主代理归纳: 本条是需由用户转达给另一会话的停止指令：D2/D3 已由主会话收归，另一会话须停止对 `windows` 分支的写入；配套常驻规则是不再使用 `git add -A`、一律显式列路径，并建议一会话一 worktree 物理隔离。
- 生效状态: 生效（已由用户转达；对方声明不再执行任何操作）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:96（建议物理隔离…需用户转达："D2/D3 已由主会话收归，请停止对 `windows` 分支的写入"）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:121（对方已声明"**不再执行任何操作**"→ 并发写入风险解除）；docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:93（不再使用 `git add -A`：一律显式列路径）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处第二个指针 docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:190 只有同义转述（"| 需用户转达 | 通知那个会话停止对 `windows` 的写入（本会话无法跨会话通信） |"），逐字只在同文件 :96。
- 备注: 裁决后同族新实例（本条明文禁令未被违反，如实登记）：2026-09-26 关闭期主代理用 `git add <单文件>` 把子代理在飞的工作区改动一并暂存提交，违反的是其后才立的"同一文件不得双写/同一切片只许一个写入者"规则，不是本条"显式列路径"的字面要求（docs/iteration/sprint/2026-09-25-sprint-18.md:331）。
- 备注: 证据局限如实标注：另一会话与本会话的提交作者同为同一 git 身份，无法用 git 元数据区分，"对方未再写入"只由文档记载支撑（docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:121）。

### V-082 用户退出确认
- 原文（逐字）: "退出确认，注意还没实现的目标 比如 CI 未实跑的影响，继续吧"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:114；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:112；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:117；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:3
- 时点: 2026-09-25（UTC+8）
- 主代理归纳: 本条是用户的退出确认：认可退出判据达成并令治理模式退出（Sprint-17 解除"停功能推进"冻结、剩余治理卡照常推进、`F-AC13/14` 仍按 P-d=4 冻结），同时点名"还没实现的目标"必须继续跟到底、不得淡出。
- 生效状态: 生效（治理模式已退出；CI 关口已按本条实跑过一次红绿）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:114（用户原话）；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:116（**据此生效**：治理模式**退出**…）；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:118（CI 从未实跑…E 步推送时 CI **必须当真实关口**：红即修、**不得以"本机绿"替代**）；docs/iteration/sprint/2026-09-21-sprint-17.md:276（CI #207（首次推送）= **failure**）；docs/iteration/sprint/2026-09-21-sprint-17.md:277（CI #208（修复后）= **success，11 步全绿**）；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:1（退出后"未实现目标"逐条核查（验证型批次，2026-09-25 UTC+8））
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处四个指针里只有 docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:114 含逐字：同文件 :112 是小节标题（`## ✅ 用户退出确认（2026-09-25，UTC+8）`）、:117 是主代理写的小标题（只含"未实现目标"四字）、docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:3 是来源清单行（同义转述）；机检窗口内任一指针命中即可，故不改指针。
- 备注: 促成本条提醒的既成事实（裁决前）：本条登记之前该批提交全部未推、"断言在 CI 同款环境跑过"这半条未满足（docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:118）。
- 备注: 仍开项（非违背）：`TG-15`⑥ 状态为"已裁定顺延"、关闭期未闭环清单仍列 major 项（docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:137）。

### V-083 用户点名未实现目标必须带到 E 步
- 原文（逐字，更正后）: "还没实现的目标"
- 出处: docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:114；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:117
- 时点: 2026-09-25
- 主代理归纳: 本条把"未实现目标"立成必须逐项核查并一直带到 E 步的清单：CI 从未实跑（推送时 CI 必须当真实关口、不得以本机绿替代）、关闭闸门真数据模式、度量项、实现类子代理无账本 role、点数结算，均不得淡出。
- 生效状态: 生效（核查已执行；其中 CI 项仍未闭环）
- 证据: docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:117（用户同时点名的"未实现目标"（必须一直带到 E 步，不得淡出））；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:119（2. `close_readiness` **真数据模式**仍 FAIL…）；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:1（退出后"未实现目标"逐条核查（验证型批次，2026-09-25 UTC+8））；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:17（一句结论：O1 的"CI 从未实跑"**依然成立**…）；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:137（1. **[major] CI 从未在本批提交上实跑**…）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: **原文级更正（2026-09-26，父代理授权）**：本条原写 `"未实现目标"` 系主代理小标题用语（出处 docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:117），用户原话为 `"还没实现的目标"`（同文件 :114，完整原话含"退出确认，注意还没实现的目标 比如 CI 未实跑的影响，继续吧"）；按登记册"原文必须逐字"的口径更正，原串已在本备注中保留可核。
- 备注: 出处行 docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:117 的「未实现目标」是主代理自己写的小标题用语，用户原话写作"还没实现的目标"（同文件 :114）；逐字串在本条出处行内可核，故按规则 7 照常判定并在此点名该处措辞来源。
- 备注: 同主题在 §6 另有 `D-250925-P5`（摘要形式"未实现目标都需要check下"，属"待逐字核对"档，逐字性存疑、不得当作原文引用，docs/6-DECISIONS.md:1663）：本条与它是**两个来源**，不是同一条的重复登记。
- 备注: 未闭环状态如实登记：本次核查里 CI 项仍是 [major] 未闭环（docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:137），该文件自身声明为时点快照、现值以命令现跑为准（同文件 :14）。

### V-084 F-AC13 用户要求影响范围评估
- 原文（逐字）: "影响范围评估下再交给我看看"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13；docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:4
- 时点: 2026-09-21
- 主代理归纳: 本条要求先出影响范围评估再交用户过目：F-AC13/F-AC14 的改动面、风险、受影响检查与验收证据设计先成文待用户拍板，评估不等于实现；评估交付后用户据此拍板 Sprint-17 插入。
- 生效状态: 生效（评估已交付；所指实现未交付）
- 证据: docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:5（状态：**待用户决策**（做/不做、本轮做/下 sprint 做）；本文只评估，不含实现）；docs/iteration/sprint/2026-09-12-sprint-16.md:291（用户 10 项决策落地…② F-AC13/F-AC14 进 **Sprint-17 插队**（评估见 2026-09-21-fac13-14-impact.MD…））；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13（**2026-09-21** 用户要求"影响范围评估下再交给我看看"→ 评估已出）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条要求的既成事实（裁决前）：现有 GUI 检查全用程序化 `.click()`、结构上无法触发 F-AC13 的失效路径（关键发现行见 docs/iteration/phases/refactor-analysis/cards/F-AC13.md:22），以及用户 2026-09-20 反馈"验收方式偏代码执行层、未覆盖人机交互面"（docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:107）。
- 备注: 同一条来源行还记着另一条独立要求"新检查须先在未修复代码上跑出 FAIL（反向对照）"，该规则另在 §3 `V-056` 与 §4.1 `V-096` 登记，不属本条内容，本条不重复登记它。
- 备注: 交付现状：评估文档已交付（docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD）；两卡实现按 P-d=4 冻结未交付（docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:202）。

### V-085 F-AC13 拍板插入 S17 + 接受拖动限制
- 原文（逐字）: "不能从按钮行拖动节点"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:34
- 时点: 2026-09-21
- 主代理归纳: 本条是用户拍板的一半：接受 F-AC13 的修法代价——修复后不能再从按钮行拖动节点（两处 `.node-actions` 加 `nodrag nopan`），并把该卡作为搭车项插入 Sprint-17。
- 生效状态: 生效（拖动限制的接受无后续撤销；该卡仍为计划中、未交付）
- 证据: docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:99（`F-AC13` 修复后"不能从按钮行拖动节点"是否可接受？ | (a) 可接受（推荐，与既有 textarea/output 一致））；docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:44（拖拽手感 | 修复后**无法再从按钮行拖动节点**（这正是目的） | 需你确认可接受）；docs/iteration/sprint/2026-09-21-sprint-17.md:41（F-AC13 | 运行按钮（要点 2~3 次） | 复现用例先 FAIL（修复前）→ 修复后一次成功 | 2）；paper-qa-script/reactflow-paperqa-prototype/frontend/src/FlowNode.jsx:133（`<div className="node-actions">`，两处按钮行均未加 `nodrag nopan`，即限制尚未兑现）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处所列 docs/iteration/phases/refactor-analysis/cards/F-AC13.md:7（**计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）**）与 docs/iteration/phases/refactor-analysis/backlog.MD:34（瘦索引行）只支持标题里"拍板插入 S17"那半句，均不含逐字「不能从按钮行拖动节点」；逐字只在同卡 :13。
- 备注: "插入 S17"那半句已被 2026-09-25 的 P-d=4 冻结取代：搭车项继续冻结、不承诺挪期（docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:202；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:116）。
- 备注: 交付现状：卡状态为计划中（docs/iteration/phases/refactor-analysis/cards/F-AC13.md:7）；Sprint-17 关闭证据行按冻结口径留空（docs/iteration/sprint/2026-09-21-sprint-17.md:133）。

### V-086 F-AC14 用户要求检查所有按钮行为
- 原文（逐字）: "检查所有按钮行为"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC14.md:13
- 时点: 2026-09-20（UTC+8）
- 主代理归纳: 本条要求不做单点修复：对全部按钮行为做一次全量审计、逐类给出结论并落到卡；审计结论 = 只有 FlowNode 的复制答案/output/复制报错三个按钮共用同一 `copied` state 有问题、其余按钮正常，据此立 `F-AC14`。
- 生效状态: 生效（审计已交付；所指修复未交付）
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC14.md:13（用户要求"检查所有按钮行为"→ 审计已完成）；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369（**全量审计结论**：…**问题只在这三个按钮**…用户要求"检查所有按钮行为"→ 已完成）；docs/iteration/phases/refactor-analysis/cards/F-AC14.md:19（**全量按钮审计结论（2026-09-20）**…）；paper-qa-script/reactflow-paperqa-prototype/frontend/src/FlowNode.jsx:42（`const [copied, setCopied] = useState(false);`，审计结论所指缺陷的执行点现状）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条与 §3 `V-020` 为同一句原话的重复登记（两处编号，非冲突）；`V-020` 的出处是 docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369。
- 备注: 促成本条要求的既成事实（裁决前）：2026-09-20 走查发现的复制按钮状态串台本身（docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369）。
- 备注: 交付现状：审计结论已落卡与验收指南，两处所指修复按 P-d=4 冻结未交付（docs/iteration/sprint/2026-09-21-sprint-17.md:134）。

### V-087 F-AC15 要求列出 9 个 env +…
- 原文（逐字）: "9 个 env + spec 阈值具体有哪些"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC15.md:13；docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:4
- 时点: 2026-09-21
- 主代理归纳: 本条要求把前端不可见的运行/运维/研究参数列成可核清单：`PAPERQA_*` env 的默认值/读取点/作用 + spec 阈值与档表 + state 键 + CLI 开关 + 硬编码常量，作为运行参数配置面的范围输入交用户勾选。
- 生效状态: 生效（清单已交付；下游 F-AC15 未交付）
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC15.md:13（**2026-09-21** 用户要求"9 个 env + spec 阈值具体有哪些"→ 清单已出）；docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:9（前端**只**暴露"引擎配置"…运行/运维/研究类参数…全部前端不可见）；docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:90（**A. 研究设置区（可改）**…）；docs/iteration/phases/refactor-analysis/cards/F-AC15.md:7（**计划中（Sprint-17，用户 2026-09-21 拍板）**）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条要求的既成事实（裁决前）：清单第 6 节记录的"连 env 都没有"的硬编码常量漏网（docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:76）。
- 备注: 交付现状：清单文档已交付（docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD）；`F-AC15` 仍为计划中且未列入 Sprint-17 看板（docs/iteration/phases/refactor-analysis/cards/F-AC15.md:7）。

### V-088 存疑 B-15：深度阈值为何是命令传参
- 原文（逐字）: "深度阈值怎么是命令传参？不应该是前端显式配置吗？类似的还有哪些"
- 出处: docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:4
- 时点: 2026-09-20
- 主代理归纳: 本条是存疑 B-15 的提问：要求解释深度阈值为何只能靠命令传参或在 spec 里改、而不是前端显式配置，并举一反三列出同类参数；答复把现状拆成"前端可见可改／spec 配置节／CLI+env+state"三类入口并立卡 `F-AC15`。
- 生效状态: 生效（已答复；随之立的 `F-AC15` 仍未交付）
- 证据: docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:4（来源：用户 2026-09-20 走查存疑 B-15…）；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:380（现状三类入口…**②③ 目前前端不可见**…立卡 `F-AC15`）；docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:56（**路由**：`agents/fanout.json` 的 `planning_pipeline.depth`（档位由任务难度建议、**用户可覆盖**））；docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:43（来源：`agents/functions/tech-research.md` 的 **Configurable Parameters 节**…+ `agents/fanout.json` 的 `depth` 路由）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条属提问类条目（用户只存疑并追问同类项）：其效力内容是"必须给出可核的三类入口答复并列出同类参数清单"，现由 docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:380 与 docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD 承载。
- 备注: 促成本条提问的既成事实（裁决前）：深度阈值当时落在 spec 的可配置参数节 + `fanout.json` 的 depth 路由（docs/iteration/phases/refactor-analysis/2026-09-21-config-surface-inventory.MD:43）。

### V-089 F-AC16 要求 v1 达原型验证可靠程度
- 原文（逐字）: "第一版实现达到 Sprint-17 可做原型验证的可靠程度"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC16.md:13
- 时点: 2026-09-21
- 主代理归纳: 本条给 checkpoint 可见性定了 v1 的质量门槛：第一版必须达到可用于原型验证的可靠程度（能被真人按路径定位、复现、核幻觉），不是半成品；v1 已按此交付。
- 生效状态: 生效（v1 已交付；剩余增量由 `V-011` 另行封存）
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC16.md:7（**v1 ✅ 完成（2026-09-21）**；剩余增量待排期）；docs/iteration/phases/refactor-analysis/cards/F-AC16.md:13（**2026-09-21** 要求"第一版实现达到 Sprint-17 可做原型验证的可靠程度"）；verify/verify_checkpoint_index.py:1（F-AC16 v1：checkpoint 只读索引（`app/checkpoint_index.py`）的离线回归）；verify/gui_check_fac16_checkpoint.mjs:1（VERIFY_META：F-AC16 v1：Checkpoints 只读面板（开关/命名空间/逐篇载荷路径/复制按钮）+/api/checkpoints 形状）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 促成本条要求的既成事实（裁决前/同期）：`docs/4-ALGORITHM.MD` 的断言数与验收指南的 CK-1 答复行在 v1 交付前已过期，由 2026-09-20 的二查 finding 抓出并归 `TG-12`（docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:103），不记为违反。
- 备注: 本条同句在 `M18` 卡有缩短版（docs/iteration/phases/refactor-analysis/cards/M18.md:13），属同义转述、以长版为准；§4.3 另有同题索引 A-179 与 A-181。
- 备注: 本条证据行不抄任何断言数：现值一律以 `verify/verify_checkpoint_index.py` 现跑末行为准。

### V-090 F-AC17 用户口径：允许用户在运行中点击
- 原文（逐字）: "**允许用户在运行中点击**"
- 出处: docs/iteration/phases/refactor-analysis/cards/F-AC17.md:19；docs/iteration/phases/refactor-analysis/cards/F-AC17.md:1；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:22；docs/iteration/phases/refactor-analysis/backlog.MD:63
- 时点: 2026-09-21
- 主代理归纳: 本条给运行中重复点击定口径：允许用户在节点运行中继续点击（不加 `disabled`、不加运行中早退），重复点击的语义（忽略/排队/并行/取消重跑）未定义，因此只立卡记录 `F-AC17`、不纳入任何 Sprint 实现范围。
- 生效状态: 生效（按本条"不实现"即合规；卡为候选仅记录）
- 证据: docs/iteration/phases/refactor-analysis/cards/F-AC17.md:19（用户 2026-09-21 口径——"**允许用户在运行中点击**"…**不纳入任何 Sprint 实现范围**）；docs/iteration/phases/refactor-analysis/cards/F-AC17.md:7（候选（**仅记录，待用户数据**））；docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:100（是否同时加 `disabled`（运行中禁用）？ | 按你 2026-09-21 指示：**不加**，另开 `F-AC17` 调研后设计）；docs/iteration/phases/refactor-analysis/backlog.MD:63（瘦索引行同词）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条与 §3 `V-010` 为同一句原话的重复登记（两处编号，非冲突）；`V-010` 的出处是 docs/iteration/sprint/2026-09-12-sprint-16.md:291 与 docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:111。
- 备注: 促成本条口径的既成事实（裁决前）：运行按钮当时无 `disabled`、`runSingleNode` 无运行中早退，重复点击语义未定义（docs/iteration/phases/refactor-analysis/cards/F-AC13.md:22）。
- 备注: 出处第三个指针 docs/iteration/phases/refactor-analysis/cards/F-AC13.md:22 亦含逐字（跨卡同句）；四个指针本次逐处核过，均在各自 ±2 行内命中。

### V-091 MM-6 用户走查提出思维模型阶段尝试
- 原文（逐字）: "这也是思维模型阶段我们要做的尝试"
- 出处: docs/iteration/phases/mental-models/cards/MM-6.md:13
- 时点: 2026-09-20（UTC+8）
- 主代理归纳: 本条把走查中提出的"把各阶段思考（开发/设计/复盘/验收）固化为思维实验并用于真实作业环境"归入思维模型阶段：该诉求由 `MM-6` 承接（不止开发的工程环境），与 `TG-6` 联动排期；本条只立项归类，不授权现在实现。
- 生效状态: 生效（归类生效；`MM-6` 状态仍为候选、Sprint 列为 `—`）
- 证据: docs/iteration/phases/mental-models/cards/MM-6.md:13（来源行=用户走查 2026-09-20（UTC+8）原话）；docs/iteration/phases/mental-models/cards/MM-6.md:19（正文：不止开发的工程环境，而是**真实作业环境**（含验收、讨论、决策、汇报）…与 TG-6 联动）；docs/iteration/phases/mental-models/backlog.MD:20（瘦索引行：状态=候选、Sprint=—）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 同阶段另一条触发义务（`MM-4`：每次 `3-LEARNED` 更新时提取候选模型）曾一次未被触发，该事故行已由 §3 `D-250926-02` 记录并指向机制反例档案例 24（docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:227）；按一事一记，本条不重复判 `有`。

### V-092 MM-1 Q1 独立阶段；Q2 补全草案接受
- 原文（逐字）: "可当成另一个工程项目"
- 原文缺失（二手转述）: "用户 2026-09-07（Q1 独立阶段；Q2 补全草案接受）｜｜用户（2026-09-07）：新增知识沉淀卡「**思维模型管理**」——把工程开发中总结的经验文档（3-LEARNED 等）转化成**更抽象的模型架构**。｜｜**已拍板：独立阶段（工程项目）**｜｜**已拍板：接受**｜｜**已拍板（Q1 独立阶段/Q2 种子接受/Q3 半自动+robust+flexible），阶段已建**……经验文档→思维模型架构；成功判据=生成可执行 agent workflow；种子=思维实验"
- 出处: docs/iteration/phases/mental-models/cards/MM-1.md:13；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:8；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:38；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:56；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:65；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:57；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:66；docs/iteration/pre-research/README.md:14
- 时点: 2026-09-07；未标注
- 主代理归纳: 本条拍板两件事：① 思维模型管理不塞进单卡，成立独立阶段 `phases/mental-models/`（按工程项目做，`M17` 迁出）；② 种子模型「思维实验」的边界/输入/输出补全草案接受（v0.1）。要求按"独立阶段 ＋ 半自动生成器（robust 与 flexibility 为硬约束）"基线排期与启动。
- 生效状态: 生效（阶段已建成：阶段 backlog 与 `MM-1`~`MM-6` 卡在位；Sprint 归属后由 §3 `D-250925-07` 改为独立并行线，不改本条"独立阶段"口径）
- 证据: docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:56（Q1 → **已拍板：独立阶段（工程项目）**）；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:57（Q2 → **已拍板：接受**）；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:65（决策记录：**Q1 = 独立阶段（工程项目）** → 成立 `phases/mental-models/`（MM-1~MM-5，9 点）；M17 迁出）；docs/iteration/pre-research/README.md:14（预研索引：**已拍板（Q1 独立阶段/Q2 种子接受/Q3 半自动+robust+flexible），阶段已建**）；docs/iteration/phases/mental-models/backlog.MD:6（阶段性质（用户 2026-09-07）：独立工程项目）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处第一个指针 docs/iteration/phases/mental-models/cards/MM-1.md:13 是摘要行（只写"用户 2026-09-07（Q1 独立阶段；Q2 补全草案接受）"），不含逐字串；逐字"可当成另一个工程项目"在 docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:38 与同文件 :10（后者加粗符夹在串中，规范化后命中）；:56/:57/:65/:66 是拍板行与决策记录行、docs/iteration/pre-research/README.md:14 是索引行，均不含该逐字串。

### V-093 TG-11 用户定性的复述（工作流记规则无用）
- 原文（逐字）: "规则直接被绕过，在 workflow 记再多也没用"
- 出处: docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:379；docs/iteration/phases/testing-governance/cards/TG-11.md:24
- 时点: 未标注
- 主代理归纳: 本条复述用户对规则绕过的定性：在 workflow 里继续写条文的边际效用为零——治理产出必须落在可执行闸门（执行点）上，不得以"再补一条规则"结案；`TG-11` 的交付口径即为该定性的落地面。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:379（这正是 TG-11 的用户定性——"规则直接被绕过，在 workflow 记再多也没用"）；docs/iteration/phases/testing-governance/cards/TG-11.md:18（用户 2026-09-21 原话全串）；docs/iteration/phases/testing-governance/cards/TG-11.md:24（本卡交付必须含"可执行闸门"，不是文档）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）——同族复发（裁决生效后"规则写了没执行"再犯）已由同句登记 `V-059` 判 `有` 并记录在案，本条按一事一记不重复判。
- 备注: 本条与 `V-059` 是同一句原话的重复登记：本条取该句前半段，`V-059` 收录全串（含"需要单独开卡复盘下"）；两条互指、非冲突。
- 备注: 出处第二个指针 docs/iteration/phases/testing-governance/cards/TG-11.md:24 是主代理的同义转述行（写作"再往 workflow 写规则没用"），不含该逐字串；逐字在 docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:379 与 docs/iteration/phases/testing-governance/cards/TG-11.md:18。

### V-094 A-M11 运行时间变短立案 TG-10（复述）
- 原文（逐字）: "运行时间怎么短了很多"
- 出处: docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:373
- 时点: 未标注
- 主代理归纳: 本条记用户对运行时长变短的追问，效果是立案 `TG-10`（账本多轮次与时长记录失真）：要求账本反映真实时长与中断事件，看板上的汇总数字不得用于判断 agent 是否偷懒或卡住。
- 生效状态: 生效
- 证据: docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:373（用户已经因为"运行时间怎么短了很多"而立案 TG-10）；docs/iteration/phases/testing-governance/cards/TG-10.md:13（用户 2026-09-21（UTC+8）全串原话；同日批准"做掉"）；docs/1-WORKFLOW.MD:446（关联 `TG-10`：多轮次记录失真）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）——本条与 `V-057` 为同一声诉的重复登记，`V-057` 已判 `无（未发现）`，本条不另判。
- 备注: 本条是同一句原话的截取复述：`V-057` 收录全串"每个 agent 运行时间相比之前怎么短了很多？而且有的是直接中途被停掉了，这些信息让我不太安心"（docs/iteration/phases/testing-governance/cards/TG-10.md:13）；两条互指、非冲突；本条只含时长半句，"中途被停"半句的规则落点在 `V-097`。

### V-095 窄范围复核判断依据质疑
- 原文（逐字）: "窄范围复核的判断依据是啥"
- 出处: docs/1-WORKFLOW.MD:109
- 时点: 2026-09-21
- 主代理归纳: 本条要求"修复验证复核"的 scope 必须有可执行来源：必须来自〇查 impact-assessment（`never a self-chosen narrow scope`），自选 scope 须显式声明来源与偏离理由，并与"关闭三查"分节定义。
- 生效状态: 生效（该质疑促成的补定义已落在 `docs/1-WORKFLOW.MD` §4.2）
- 证据: docs/1-WORKFLOW.MD:109（2026-09-21 用户质疑"窄范围复核的判断依据是啥"即由此而来）；docs/1-WORKFLOW.MD:107（修复验证复核（fix-verification review）——与"关闭三查"是两件事（2026-09-21 补定义））；docs/iteration/phases/testing-governance/cards/TG-11.md:24（`agents/functions/code-review.md:26/:34` 明文 `scope` 必须来自〇查 impact-assessment）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条与 `V-015` 是同一提问的两处登记，措辞差一字（`V-015` 写作"窄范围定点复核的判断依据是啥"，出处为 docs/iteration/sprint/2026-09-12-sprint-16.md:200 与 docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:24）；原文照录不改，两条互指、非冲突。
- 备注: 促成本条补定义的既成事实（裁决前）：2026-09-20/21 以"修复验证复核"名义自选窄范围跑了 5 轮子代理复核（run-053 R1~R5）、scope 未来自〇查（docs/iteration/phases/testing-governance/cards/TG-11.md:24；docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:24）。

### V-096 交互类检查反向对照（倒过来试试）
- 原文（逐字）: "倒过来试试"
- 出处: docs/1-WORKFLOW.MD:442
- 时点: 2026-09-21
- 主代理归纳: 本条拍板交互/GUI 类检查的反向对照规则：新增（或改动）的交互类检查必须先在未修复、或旧实现的代码上跑出 FAIL，证明它能触发目标失效模式，再在修复后转 PASS，并把该反例写进检查脚本注释与验收指南。
- 生效状态: 生效
- 证据: docs/1-WORKFLOW.MD:443（交互类检查的反向对照规则（2026-09-21 用户拍板，称"倒过来试试"）…必须先在"未修复（或旧实现）"的代码上跑出 FAIL）；docs/iteration/phases/testing-governance/cards/TG-6.md:19（⑤ 反向对照规则…反例：`gui_check_s5/s7` 用程序化 `.click()` 结构上无法触发 F-AC13）；docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处指针 docs/1-WORKFLOW.MD:442 现为空行，逐字落在紧邻的 :443（漂移一格，本次按 ±2 行命中；同句登记 `V-056` 的出处亦指向 :442）。
- 备注: 本条与 `V-056` 是同一句原话的重复登记（`V-056` 出处为 docs/iteration/phases/testing-governance/cards/TG-6.md:19 等），两条互指、非冲突；`V-084` 的备注亦指向本条。
- 备注: 同族近例（非本格）：2026-09-25 复核的对照走假路径（注入中间变量绕过被判据驱动的真实入口）见 docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:32，其对象是 B5 对照而非交互/GUI 检查，本条不据此判 `有`。

### V-097 子代理中断/接管必须留痕
- 原文（逐字）: "运行时间变短/中途被停"
- 出处: docs/1-WORKFLOW.MD:444
- 时点: 2026-09-21
- 主代理归纳: 本条立规：主代理中断（`interrupt_agent`）、杀掉子代理派生的进程、或按 §4.2 接管时，必须记三件事——何时、为什么、影响范围（哪一轮评审或验证因此缺失、后来如何补做），写入 Sprint 文档 §5/§9；机检执行点 = `scripts/agent-ops.py interrupt` 强制 `--reason` 与 `--impact`，`verify/verify_agentops.py` 的 UC-21 核查项要求账本 `interruptions[]` 的 `reason`/`impact` 均非空、`interruptions_count` 与数组长度一致。
- 生效状态: 生效（机检部分已落；"影响范围是否如实"为 prose-only、无机检——引用时须知边界）
- 证据: docs/1-WORKFLOW.MD:445（规则全文与执行点声明：① 机检部分…② prose-only 部分…该条只做了一半机械化）；docs/1-WORKFLOW.MD:446（依据：2026-09-20 误杀复核子代理派生的套件进程树 3 次、主动 `interrupt` 1 次，若没留痕账本只会看到"首轮 53 秒 succeeded"）；scripts/agent-ops.py:1244（`cmd_interrupt` 实现入口）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 有——裁决生效后同族形态复发：2026-09-25 关闭期三个修复类子代理在同一分钟内因余额耗尽中途退出、均未回执，且修复类子代理当时未登记 run（无 run 目录、无状态文件）⇒ 仓库里看不出哪部分是半成品；反例档直接命名为"子代理**中断不留痕**"（docs/iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD:21；同文件 :23；同文件 :25）。
- 备注: 本条判 `有` 的口径：事故的行为主体是子代理自身资源耗尽退出（非主代理发起的 `interrupt`），但形态与本条所治的"中途被停而账本与仓库看不出"同族，按父代理已定的"同族形态在生效后复发"先例判 `有`；该事故行此前未被任何条目引用，本条按一事一记在此认领。
- 备注: 促成本条的既成事实（裁决前，按规则不计入本条违背）：2026-09-20 误杀复核子代理派生的套件进程树 3 次并主动 `interrupt` 它 1 次、其 round-3 因此顺延，见 docs/1-WORKFLOW.MD:446。
- 备注: 出处指针 docs/1-WORKFLOW.MD:444 现为空行，逐字落在紧邻的 :445（漂移一格，本次按 ±2 行命中）。

### V-098 检索质量先立评测基线
- 原文（逐字）: "top5 与 query 无关"
- 出处: docs/3-LEARNED.MD:143
- 时点: 未标注（标题含 Sprint-6）
- 主代理归纳: 本条要求检索/排序类改动先有评测再动手：先建可复现的小样本评测基线（双语料 ＋ 策略断言 ＋ 负对照），再实现检索改进，使"变好变坏"可量化对比，而不是靠感觉。
- 生效状态: 生效
- 证据: docs/3-LEARNED.MD:143（用户反馈"top5 与 query 无关"后，先建 `verify/eval_retrieve.py` 小样本基线…再实现多语检索 v1）；docs/3-LEARNED.MD:145（教训：**检索/排序类改动先有评测再动手**）；verify/eval_retrieve.py:1（F4 轻量评测基准（Sprint-6 US-6.3，可复现）：retrieve 命中质量小样本对比）；verify/eval_retrieve.py:92（负对照断言：`query_strategy`/`result` 均为 `fallback_first_n`）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 同句原话另在 `V-001` 登记（出处 docs/iteration/sprint/2026-08-30-sprint-5.md:12，原文只取"与 query 无关"）；两条互指、非冲突——`V-001` 管"兜底结果必须对用户可见"，本条管"先立评测基线再动检索"。

### V-099 清账要求：清完无遗漏
- 原文（逐字）: "清完无遗漏"
- 出处: docs/3-LEARNED.MD:159
- 时点: 未标注（标题含 Sprint-7）
- 主代理归纳: 本条要求技术账一次清完、不得遗漏：历次 Retro 与三查的"建议修/后续"先独立登记为维护卡（`M1`~`M6`），用户批准后打包成插队 Sprint 清零；DoD = 卡清零 ＋ verify 证据入库 ＋ 关闭前全量 review 无遗漏，而非"看起来都改了"。
- 生效状态: 生效（Sprint-7 已按此交付；`M3` 按用户指示保留未完成并在卡上注明）
- 证据: docs/3-LEARNED.MD:159（用户要求"清完无遗漏"）；docs/3-LEARNED.MD:160（backlog 维护卡 M1~M6 独立登记…用户批准后打包成插队 Sprint-7 一次性清零（M3 按用户指示保留未完成，卡上注明））；docs/iteration/phases/refactor-analysis/cards/M3.md:7（候选（用户指示未处理））；docs/iteration/phases/refactor-analysis/backlog.MD:45（M1 瘦索引行：Sprint-7 ✅ 完成）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 与本条同族的"逐项核查、不得淡出"要求另在 `V-083` 登记（未实现目标清单），属另条内容，本条不重复登记。

### V-100 评审代理按职能而非按分支
- 原文（逐字）: "按分支划分"
- 出处: docs/3-LEARNED.MD:169
- 时点: 未标注（标题含 Sprint-8）
- 主代理归纳: 本条要求 agent（尤其评审类）按职能与能力划分，目标对象（分支/PR/文件集）一律作为任务参数——同一 spec 换 task 参数即可复用；配套要求调研结论必须转成可测用例（出处 ＋ 可测断言 ＋ 验证方式），否则调研与实现脱节。
- 生效状态: 生效（职能化 spec 已按一职能一份落地，如 `agents/functions/code-review.md`）
- 证据: docs/3-LEARNED.MD:169（① 用户指出评审代理"按分支划分"不合理——应**按职能划分**（分支只是任务参数）…② 把每条调研结论写成"出处+可测断言+验证方式"）；docs/3-LEARNED.MD:170（**agent 按职能/能力划分，目标对象（分支/PR/文件集）一律参数化**）；agents/functions/code-review.md:3（`description`：reviews a branch/PR/working tree…——职能固定、对象参数化）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 出处是主代理的转述行：被引作原文的"按分支划分"是用户指出的做法字串（用户原话未在任何仓内文档里逐字留存），按规则 7 原文照录不改并在此点名。
- 备注: 同族近例（非本格）：2026-09-26"同一系统里两套'评审类'定义 ⇒ 非评审 role 的空窗口两头堵"（角色分类口径在两处各自定义）见 docs/iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD:218；该形态已被 `V-053` 的备注索引，本条不据此判 `有`。

### V-101 走查追问 CK-1 与 M16-5
- 原文（逐字）: "前端能看到载入的 checkpoint 文件吗｜｜；｜｜模型信息更新后会影响更新前的报告吗"（`｜｜` 为分段符）
- 出处: docs/4-ALGORITHM.MD:653
- 时点: 2026-09-20
- 主代理归纳: 本条要求对两个走查追问给出 v1 答复：① 前端必须能看到载入的 checkpoint 文件（F-AC16 只读可见性）；② 模型信息更新后对更新前报告的影响必须有明确口径（M18 报告时效）。两项按 `docs/4-ALGORITHM.MD` §14 的 v1 口径与验证证据交付。
- 生效状态: 生效（两项 v1 均已交付并登记在 §14）
- 证据: docs/4-ALGORITHM.MD:653（用户 2026-09-20 走查的 CK-1（"前端能看到载入的 checkpoint 文件吗"）与 M16-5（"模型信息更新后会影响更新前的报告吗"））；docs/4-ALGORITHM.MD:651（§14 走查追问的两项 v1（2026-09-21）：checkpoint 可见性（F-AC16）与报告时效（M18））；docs/iteration/phases/refactor-analysis/cards/F-AC16.md:13（用户走查 2026-09-20（UTC+8）：CK-1 存疑）；docs/iteration/phases/refactor-analysis/cards/M18.md:13（用户走查 2026-09-20（UTC+8）：M16-5 存疑）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 原文里的 `｜｜` 与夹在其间的分号是征集稿单元格的分段符，源文件把两问写在同一行并以"与"连接（docs/4-ALGORITHM.MD:653），两段逐字片段均已在该行核过；按规则 3 不改 `原文`，在此点名分隔符来源。
- 异文（待核）: 见上方 `原文（逐字）` 的另一段（同一征集稿单元格内的第二种写法，已逐字保留，未另立条目）

### V-102 v1 须达原型验证可靠程度
- 原文（逐字）: "第一版实现能够达到在 Sprint-17 做原型验证的可靠程度"
- 出处: docs/4-ALGORITHM.MD:654
- 时点: 2026-09-21
- 主代理归纳: 本条给走查追问两问的 v1 定质量门槛：第一版实现必须达到"可用于 Sprint-17 原型验证"的可靠程度（真人可按路径定位、复现、核幻觉），不得交半成品；口径覆盖 F-AC16 与 M18 两项。
- 生效状态: 生效（v1 已交付；剩余增量另行封存）
- 证据: docs/4-ALGORITHM.MD:654（用户 2026-09-21 要求"第一版实现能够达到在 Sprint-17 做原型验证的可靠程度"）；docs/4-ALGORITHM.MD:656（### 14.1 F-AC16 v1：本地 checkpoint 可见性（只读））；docs/iteration/phases/refactor-analysis/cards/M18.md:13（**2026-09-21** 要求 v1 可靠到可做 Sprint-17 原型验证）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 本条与 `V-089` 是同一要求的两处登记（`V-089` 出处 docs/iteration/phases/refactor-analysis/cards/F-AC16.md:13，原文写作"第一版实现达到 Sprint-17 可做原型验证的可靠程度"——少"能够"且语序不同；`M18` 卡另有缩短版 docs/iteration/phases/refactor-analysis/cards/M18.md:13），三条互指、非冲突，以本条（docs/4-ALGORITHM.MD:654）为长版。

### V-103 暂不创建 product/marketing…
- 原文（逐字）: "现在不需要立即创建这些 subagent"
- 出处: docs/iteration/pre-research/2026-08-31-domain-governance.MD:3
- 时点: 2026-08-31
- 主代理归纳: 本条指示暂不创建 product-research 与 marketing-research 这两个 subagent：领域治理只留设计备忘（未实施），两领域 agent 的创建时机绑在"用户启动该领域第一轮方案讨论"上，不得提前建 spec。
- 生效状态: 生效
- 证据: docs/iteration/pre-research/2026-08-31-domain-governance.MD:3（用户指示"现在不需要立即创建这些 subagent"）；docs/iteration/pre-research/README.md:17（一领域=一 agent=一 role=一目录；product/marketing 待讨论启动时创建…待建：product-research、marketing-research）；docs/iteration/pre-research/product/README.md:4（启用时机：用户启动产品设计领域的第一轮方案讨论时——按…上线判据创建 `product-research` agent）；docs/iteration/pre-research/marketing/README.md:4（同构的营销域启用时机）
- 验证时间戳: 2026-09-26（UTC+8，本次逐条核对时点）
- 违背事故: 无（未发现）
- 备注: 合规现状=两个域只有声明"启用时机"的 README 壳、无 agent spec（以 `agents/functions/` 目录现跑列表现为准）；领域壳本身由用户启动时机条款约束，不构成提前创建。

## 4.2 二手转述中判定为"仍生效"者（待主代理逐条判定后移入）

> 本节由主代理按批次回填：从 §4.3 附录里挑出"仍生效"的条目，补齐 生效状态/证据/验证时间戳 后移入本节。**回填前本节的条目数为 0**。

## 4.3 附录：其余二手转述（仅索引；**未判定效力，不得引用为裁决**）

| 编号 | 主题（≤40 字，取合并稿短标题） | 出处 | 时点 |
|---|---|---|---|
| A-001 | Sprint2 范围：同步 main、跳过 MAC | docs/iteration/sprint/2026-08-29-sprint-2.md:4 | 未标注 |
| A-002 | Sprint3 范围：双分支评审 | docs/iteration/sprint/2026-08-29-sprint-3.md:4 | 未标注 |
| A-003 | Sprint3 之后 Sprint 全部 hold | docs/iteration/sprint/2026-08-29-sprint-3.md:16 | 2026-08-29 |
| A-004 | Sprint3 需求方要求代码评审 | docs/iteration/sprint/2026-08-29-sprint-3.md:113 | 未标注 |
| A-005 | Sprint4 输入：用户实测反馈 5 项 | docs/iteration/sprint/2026-08-30-sprint-4.md:3 | 未标注 |
| A-006 | Sprint4 原规划顺延保持 hold | docs/iteration/sprint/2026-08-30-sprint-4.md:4 | 未标注 |
| A-007 | Sprint4 范围与 MAC 验证跳过 | docs/iteration/sprint/2026-08-30-sprint-4.md:5 | 未标注 |
| A-008 | Sprint5 输入：用户实战截图与 5 项问题 | docs/iteration/sprint/2026-08-30-sprint-5.md:3 | 未标注 |
| A-009 | Sprint5 roadmap C/E3 继续 hold | docs/iteration/sprint/2026-08-30-sprint-5.md:3 | 未标注 |
| A-010 | 用户选定 F1 方向 | docs/iteration/sprint/2026-08-30-sprint-6.md:3 | 未标注 |
| A-011 | 用户批准 M1~M6 维护批 | docs/iteration/sprint/2026-08-30-sprint-7.md:3；docs/iteration/sprint/2026-08-30-sprint-7.md:55 | 2026-08-30 |
| A-012 | 用户指示 M3 保持未完成 | docs/iteration/sprint/2026-08-30-sprint-7.md:5；docs/iteration/sprint/2026-08-30-sprint-7.md:23；docs/iteration/sprint/2026-08-30-sprint-7.md:55；docs/iteration/sprint/2026-08-30-sprint-7.md:107 | 2026-08-30 |
| A-013 | 用户指示关闭前追加全量 code review | docs/iteration/sprint/2026-08-30-sprint-7.md:5 | 2026-08-30 |
| A-014 | AgentOps 三阶段批准并按 Sprint 管理 | docs/iteration/sprint/2026-08-30-sprint-8.md:3 | 未标注 |
| A-015 | 用户三条修改意见修订阶段 1 | docs/iteration/sprint/2026-08-30-sprint-8.md:8；docs/iteration/sprint/2026-08-30-sprint-8.md:82 | 未标注 |
| A-016 | A-PM1~A-PM4 按用户指示留 backlog | docs/iteration/sprint/2026-08-30-sprint-8.md:23 | 未标注 |
| A-017 | 问题①增 impact-assessment 职能 | docs/iteration/sprint/2026-08-30-sprint-8.md:59；docs/iteration/sprint/2026-08-30-sprint-8.md:65；docs/iteration/sprint/2026-08-30-sprint-8.md:83；docs/iteration/sprint/2026-08-30-sprint-8.md:86；docs/iteration/sprint/2026-08-30-sprint-8.md:107；docs/iteration/sprint/2026-08-30-sprint-8.md:121 | 2026-08-30 |
| A-018 | 用户问题② 留证文件出库 | docs/iteration/sprint/2026-08-30-sprint-8.md:65；docs/iteration/sprint/2026-08-30-sprint-8.md:86；docs/iteration/sprint/2026-08-30-sprint-8.md:119；docs/iteration/sprint/2026-08-30-sprint-8.md:121 | 2026-08-30 |
| A-019 | 复合指标细化 A+B 8:2 / X=50 | docs/iteration/sprint/2026-08-30-sprint-8.md:65；docs/iteration/sprint/2026-08-30-sprint-8.md:121 | 2026-08-30 |
| A-020 | 用户确认进入阶段 3 | docs/iteration/sprint/2026-08-30-sprint-9.md:3 | 未标注 |
| A-021 | 超时砍范围需与用户确认 | docs/iteration/sprint/2026-08-30-sprint-9.md:10 | 未标注 |
| A-022 | 用户样式决策 UI 切 Ant Design | docs/iteration/sprint/2026-08-30-sprint-9.md:23；docs/iteration/sprint/2026-08-30-sprint-9.md:51；docs/iteration/sprint/2026-08-30-sprint-9.md:93；docs/iteration/sprint/2026-08-30-sprint-9.md:98 | 未标注 |
| A-023 | 用户校准 2026-08-30 | docs/iteration/sprint/2026-08-30-sprint-9.md:126 | 2026-08-30 |
| A-024 | 确认 Sprint-9 结束并进入下阶段 | docs/iteration/sprint/2026-08-31-sprint-10.md:3 | 2026-08-31 选择确认 |
| A-025 | 拍板方向＝收口+跨平台债+FANOUT | docs/iteration/sprint/2026-08-31-sprint-10.md:3；docs/iteration/sprint/2026-08-31-sprint-10.md:64 | 2026-08-31 选择确认；2026-08-31 06:47（网络时间 UTC+8） |
| A-026 | 拍板下一阶段方向＝F2 | docs/iteration/sprint/2026-08-31-sprint-11.md:3 | 2026-08-31 |
| A-027 | 要求分阶段分 Sprint 执行 | docs/iteration/sprint/2026-08-31-sprint-11.md:3 | 2026-08-31 |
| A-028 | 用户决策：统一 PR 节奏 | docs/iteration/sprint/2026-08-31-sprint-14.md:48 | 2026-08-31 |
| A-029 | 拍板排期选选项 1 | docs/iteration/sprint/2026-09-07-sprint-15.md:3；docs/iteration/sprint/2026-09-07-sprint-15.md:65 | 2026-09-07 |
| A-030 | 走查第1项字体统一 PASS | docs/iteration/sprint/2026-09-07-sprint-15.md:134 | 未标注（节标题 2026-09-10） |
| A-031 | 走查第2项标题聚合+hints 返工后修复 | docs/iteration/sprint/2026-09-07-sprint-15.md:135 | 未标注（节标题 2026-09-10） |
| A-032 | 走查第3项 local 路径+条件隐藏 PASS | docs/iteration/sprint/2026-09-07-sprint-15.md:136 | 未标注（节标题 2026-09-10） |
| A-033 | 走查第4项完成后收起 PASS | docs/iteration/sprint/2026-09-07-sprint-15.md:137 | 未标注（节标题 2026-09-10） |
| A-034 | 走查第5项响应式 PASS | docs/iteration/sprint/2026-09-07-sprint-15.md:138 | 未标注（节标题 2026-09-10） |
| A-035 | 走查第6项复制+报错详情追加需求 | docs/iteration/sprint/2026-09-07-sprint-15.md:139 | 未标注（节标题 2026-09-10） |
| A-036 | 走查第7项状态作用域语义修正 | docs/iteration/sprint/2026-09-07-sprint-15.md:140；docs/iteration/sprint/2026-09-07-sprint-15.md:41；docs/iteration/sprint/2026-09-07-sprint-15.md:96 | 2026-09-10 |
| A-037 | 走查第8项反向联动返工后修复 | docs/iteration/sprint/2026-09-07-sprint-15.md:141；docs/iteration/sprint/2026-09-07-sprint-15.md:98 | 未标注（节标题 2026-09-10） |
| A-038 | 走查第9项 ATDD case 先行补充已落盘 | docs/iteration/sprint/2026-09-07-sprint-15.md:142；docs/iteration/sprint/2026-09-07-sprint-15.md:31 | 2026-09-10 |
| A-039 | N2 论文截图清晰度新需求 | docs/iteration/sprint/2026-09-07-sprint-15.md:144 | 未标注（节标题 2026-09-10） |
| A-040 | 三轮新逻辑与新问题全部已做 | docs/iteration/sprint/2026-09-07-sprint-15.md:145 | 2026-09-10 |
| A-041 | 四轮反馈全部已做 | docs/iteration/sprint/2026-09-07-sprint-15.md:146 | 2026-09-10 |
| A-042 | 五轮反馈多报错卡定位返工 | docs/iteration/sprint/2026-09-07-sprint-15.md:147；docs/iteration/sprint/2026-09-07-sprint-15.md:99 | 2026-09-10 |
| A-043 | 六轮反馈文档时间记录准确性返工 | docs/iteration/sprint/2026-09-07-sprint-15.md:148；docs/iteration/sprint/2026-09-07-sprint-15.md:74 | 2026-09-10 |
| A-044 | 七轮反馈报错卡重叠定位返工 | docs/iteration/sprint/2026-09-07-sprint-15.md:149；docs/iteration/sprint/2026-09-07-sprint-15.md:75；docs/iteration/sprint/2026-09-07-sprint-15.md:99 | 2026-09-10 |
| A-045 | 八轮反馈定位下一处报错未居中返工 | docs/iteration/sprint/2026-09-07-sprint-15.md:150；docs/iteration/sprint/2026-09-07-sprint-15.md:76；docs/iteration/sprint/2026-09-07-sprint-15.md:99 | 2026-09-10 |
| A-046 | 九轮用户宣布 Sprint-15 验收通过 | docs/iteration/sprint/2026-09-07-sprint-15.md:151 | 2026-09-10 |
| A-047 | 用户口径 09-10 开始走查 | docs/iteration/sprint/2026-09-07-sprint-15.md:130 | 2026-09-10 |
| A-048 | 用户复验一次通过（五~九轮） | docs/iteration/sprint/2026-09-07-sprint-15.md:104 | 未标注 |
| A-049 | Q1 一 provider 一文件 + 每两周更新 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:27；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:19；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:37 | 未标注（节标题 2026-08-31 已答复） |
| A-050 | Q2 文献级 checkpoint | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:28；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:21 | 未标注（节标题 2026-08-31 已答复） |
| A-051 | Q4 完成后全部收起仅留 output_snapshot | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:30；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:16；docs/iteration/sprint/2026-09-07-sprint-15.md:20 | 未标注（节标题 2026-08-31 已答复） |
| A-052 | Q5 主画布报错摘要加可展开堆栈 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:31；docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:18；docs/iteration/sprint/2026-09-07-sprint-15.md:22；docs/iteration/sprint/2026-09-07-sprint-15.md:73 | 未标注（节标题 2026-08-31 已答复） |
| A-053 | 用户完成 F2 验收提交 8 项问题 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:43 | 2026-08-31 |
| A-054 | Q1~Q5 答复与排期登记 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:44 | 2026-08-31 |
| A-055 | 验收反馈问题 1.1 标题字号偏大 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:10 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-056 | 验收 1.3b local 未隐藏无关参数 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:11 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-057 | 验收反馈问题 1.3a local 无路径入口 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:12 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-058 | 验收问题 3 subcanvas 卡片显示不全 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:13 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-059 | 验收反馈问题 1.2a 提示行过多卡片被拉长 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:14 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-060 | 验收反馈问题 1.2b 影响内容未上浮到标题 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:15 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-061 | 验收问题 2 完成后仅留 output_snapshot | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:16 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-062 | 验收反馈问题 5 状态信息残留 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:17 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-063 | 验收反馈问题 4 失败无法复制报错 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:18 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-064 | 验收问题 6 provider 数据非官网最新 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:19 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-065 | 验收反馈问题 7 主画布不联动 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:20 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-066 | 验收 8 embedding 额度失败断点续跑 | docs/iteration/sprint/2026-08-31-f2-acceptance-findings.MD:21 | 未标注（文档标题 2026-08-31 用户验收反馈） |
| A-067 | mental-models 阶段暂缓指示 | docs/iteration/sprint/2026-09-12-sprint-16.md:3；docs/iteration/sprint/2026-09-12-sprint-16.md:58 | 2026-09-12 |
| A-068 | 2026-09-07 排期拍板 | docs/iteration/sprint/2026-09-12-sprint-16.md:3 | 2026-09-07 |
| A-069 | Sprint-15 验收通过并关闭 | docs/iteration/sprint/2026-09-12-sprint-16.md:3 | 2026-09-10 |
| A-070 | 拍板 dashscope 默认模型 | docs/iteration/sprint/2026-09-12-sprint-16.md:69；docs/iteration/sprint/2026-09-12-sprint-16.md:91；docs/iteration/sprint/2026-09-12-sprint-16.md:162 | 2026-09-12 |
| A-071 | 确认 Sprint-16 两处口径 | docs/iteration/sprint/2026-09-12-sprint-16.md:70；docs/iteration/sprint/2026-09-12-sprint-16.md:292 | 2026-09-20（UTC+8，网络时间校准） |
| A-072 | 走查完成未通过 0 项 | docs/iteration/sprint/2026-09-12-sprint-16.md:80；docs/iteration/sprint/2026-09-12-sprint-16.md:284；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:11；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:41 | 2026-09-20（UTC+8） |
| A-073 | 走查提出新增问题 2 项 | docs/iteration/sprint/2026-09-12-sprint-16.md:284；docs/iteration/sprint/2026-09-12-sprint-16.md:80 | 2026-09-20（UTC+8） |
| A-074 | 走查存疑 6 项 | docs/iteration/sprint/2026-09-12-sprint-16.md:284 | 2026-09-20（UTC+8） |
| A-075 | Sprint-16 HOLD 决定 | docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16.md:275；docs/iteration/sprint/2026-09-12-sprint-16.md:196；docs/iteration/sprint/2026-09-12-sprint-16.md:210；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:43；docs/iteration/ROADMAP.MD:13 | 2026-09-21（UTC+8）；2026-09-21 |
| A-076 | HOLD 解除 | docs/iteration/sprint/2026-09-12-sprint-16.md:83 | 2026-09-21 |
| A-077 | 批准执行关闭手续 | docs/iteration/sprint/2026-09-12-sprint-16.md:249；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:90 | 2026-09-21 |
| A-078 | 批准关闭 Sprint-16 | docs/iteration/sprint/2026-09-12-sprint-16.md:274；docs/iteration/sprint/2026-09-12-sprint-16.md:84；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:11 | 2026-09-21 |
| A-079 | 决策② F-AC13/14 进 S17 | docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:106 | 2026-09-21（UTC+8） |
| A-080 | 决策③ F-AC15 进 Sprint-17 | docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:106 | 2026-09-21（UTC+8） |
| A-081 | 决策⑥ Retro②④进 Sprint-17 | docs/iteration/sprint/2026-09-12-sprint-16.md:291；docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:106 | 2026-09-21（UTC+8） |
| A-082 | 决策⑦ est 安全系数可配置 | docs/iteration/sprint/2026-09-12-sprint-16.md:291 | 2026-09-21（UTC+8） |
| A-083 | 决策⑧ 反向对照规则固化 | docs/iteration/sprint/2026-09-12-sprint-16.md:291 | 2026-09-21（UTC+8） |
| A-084 | 决策⑨ 自查修复路径穿越口 | docs/iteration/sprint/2026-09-12-sprint-16.md:291 | 2026-09-21（UTC+8） |
| A-085 | 提出子代理中断疑虑 | docs/iteration/sprint/2026-09-12-sprint-16.md:199 | 2026-09-21 |
| A-086 | 插入 A-M11 记卡 | docs/iteration/sprint/2026-09-12-sprint-16.md:259 | 2026-09-21 |
| A-087 | 已定 A-M11 目标穷举先做 | docs/iteration/sprint/2026-09-12-sprint-16.md:133 | 2026-09-21（快照） |
| A-088 | 拍板 TG-14 提升独立卡 | docs/iteration/sprint/2026-09-12-sprint-16.md:140；docs/iteration/sprint/2026-09-12-sprint-16.md:151 | 2026-09-21 |
| A-089 | 拍板开新卡 TG-13 | docs/iteration/sprint/2026-09-12-sprint-16.md:141；docs/iteration/sprint/2026-09-12-sprint-16.md:152 | 2026-09-21 |
| A-090 | "待立卡项"处置拍板 | docs/iteration/sprint/2026-09-12-sprint-16.md:152 | 2026-09-21 |
| A-091 | 要求记全收尾补充 | docs/iteration/sprint/2026-09-12-sprint-16.md:97 | 2026-09-21 |
| A-092 | 采纳四条度量约束 | docs/iteration/sprint/2026-09-12-sprint-16.md:123 | 2026-09-21 |
| A-093 | 插卡 TG-12 文档漂移复盘 | docs/iteration/sprint/2026-09-12-sprint-16-status-report.MD:106 | 2026-09-21 |
| A-094 | 待你拍板：hint 文案去向（仍未决策） | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:17；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:301 | 未标注 |
| A-095 | 拍板口径①：定期刷新=14 天 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:32；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:36 | 未标注 |
| A-096 | 拍板口径②：夜间套件周频¥10上限 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:32；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:37 | 未标注 |
| A-097 | 拍板 dashscope 模型 qwen3.5-omni-plus | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:202；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:268 | 未标注 |
| A-098 | 暂缓 mental-models（MM-1~5） | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:305 | 未标注 |
| A-099 | 用户走查结论：未通过 = 暂未发现 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:328；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:362 | 2026-09-20，UTC+8 |
| A-100 | 新增问题 1：节点按钮需点 2~3 次 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:368 | 2026-09-20，UTC+8 |
| A-101 | 新增问题 2：复制答案与复制 output 联动 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:369 | 2026-09-20，UTC+8 |
| A-102 | 存疑 M16-5：旧报告是否受模型更新影响 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:375 | 2026-09-20，UTC+8 |
| A-103 | 存疑 CK-1 前端能否看 checkpoint | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:376 | 2026-09-20，UTC+8 |
| A-104 | 存疑 TG-1~TG-5：脚本校验项跳过 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:377 | 2026-09-20，UTC+8 |
| A-105 | 存疑 B-9：预算超限场景跳过 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:378 | 2026-09-20，UTC+8 |
| A-106 | 存疑 B-10：到期指代不明 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:379 | 2026-09-20，UTC+8 |
| A-107 | 存疑 B-15：深度阈值为何是命令传参 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:380 | 2026-09-20，UTC+8 |
| A-108 | 付费项口径：先执行须先报花费并获批 | docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:382；docs/iteration/sprint/2026-09-12-sprint-16-acceptance-guide.MD:384 | 2026-09-20 |
| A-109 | 审定治理批计划 D1~D8 | docs/iteration/sprint/2026-09-21-sprint-17.md:4 | 2026-09-21 |
| A-110 | 批准插入 TG-15（2.5 点） | docs/iteration/sprint/2026-09-21-sprint-17.md:24；docs/iteration/sprint/2026-09-21-sprint-17.md:85；docs/iteration/sprint/2026-09-21-sprint-17.md:147 | 2026-09-23 |
| A-111 | 批准开卡 TG-17 | docs/iteration/sprint/2026-09-21-sprint-17.md:5；docs/iteration/sprint/2026-09-21-sprint-17.md:105 | 2026-09-23 |
| A-112 | TG-15⑥ 顺延（用户授权处置） | docs/iteration/sprint/2026-09-21-sprint-17.md:73；docs/iteration/sprint/2026-09-21-sprint-17.md:103；docs/iteration/sprint/2026-09-21-sprint-17.md:128 | 2026-09-23 |
| A-113 | 执行会话单一负责 / 工作收归本会话 | docs/iteration/sprint/2026-09-21-sprint-17.md:8；docs/iteration/sprint/2026-09-21-sprint-17.md:361 | 2026-09-25 |
| A-114 | 并行会话交付质量判定（U1~U4） | docs/iteration/sprint/2026-09-21-sprint-17.md:361 | 2026-09-25 |
| A-115 | 15 个提交先不推待独立审核 | docs/iteration/sprint/2026-09-21-sprint-17.md:361；docs/iteration/sprint/2026-09-21-sprint-17.md:8 | 2026-09-25 |
| A-116 | A1 关闭冻结与勘误许可 | docs/iteration/sprint/2026-09-21-sprint-17.md:182；docs/iteration/sprint/2026-09-21-sprint-17.md:331 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验）） |
| A-117 | A2 同步 PR 授权 | docs/iteration/sprint/2026-09-21-sprint-17.md:183；docs/iteration/sprint/2026-09-21-sprint-17.md:275 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验）） |
| A-118 | A3 复核强度维持 | docs/iteration/sprint/2026-09-21-sprint-17.md:184；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:203 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验））；2026-09-25 |
| A-119 | B1① 关闭税升为 G2 头号指标 | docs/iteration/sprint/2026-09-21-sprint-17.md:174；docs/iteration/sprint/2026-09-21-sprint-17.md:185 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验）） |
| A-120 | B2① 扣分口径确认 | docs/iteration/sprint/2026-09-21-sprint-17.md:173；docs/iteration/sprint/2026-09-21-sprint-17.md:186；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:205 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验））；2026-09-25 |
| A-121 | B3① G2 上限 ≤14 点 | docs/iteration/sprint/2026-09-21-sprint-17.md:175；docs/iteration/sprint/2026-09-21-sprint-17.md:187 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验）） |
| A-122 | B4② TG-18 与机制缺口排进 G2 | docs/iteration/sprint/2026-09-21-sprint-17.md:176；docs/iteration/sprint/2026-09-21-sprint-17.md:188 | 未标注（所在签核节首行标 2026-09-25（UTC+8 `15:52`，网络时间核验）） |
| A-123 | P-d=4 冻结搭车项 | docs/iteration/sprint/2026-09-21-sprint-17.md:71；docs/iteration/sprint/2026-09-21-sprint-17.md:72；docs/iteration/sprint/2026-09-21-sprint-17.md:89；docs/iteration/sprint/2026-09-21-sprint-17.md:133；docs/iteration/sprint/2026-09-21-sprint-17.md:134 | 2026-09-25 |
| A-124 | TG-17 前移为关闭阻塞项 | docs/iteration/sprint/2026-09-21-sprint-17.md:74；docs/iteration/sprint/2026-09-21-sprint-17.md:89；docs/iteration/sprint/2026-09-21-sprint-17.md:147；docs/iteration/sprint/2026-09-21-sprint-17.md:323 | 2026-09-25 |
| A-125 | 双盲抽查用户裁定 | docs/iteration/sprint/2026-09-21-sprint-17.md:212 | 未标注 |
| A-126 | 三查锚点必填（用户可否决） | docs/iteration/sprint/2026-09-21-sprint-17.md:121 | 未标注 |
| A-127 | B4② 立项依据（TG-19） | docs/iteration/sprint/2026-09-25-sprint-18.md:26；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:204；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:47 | 2026-09-25 |
| A-128 | TG-17 前移裁定 | docs/iteration/sprint/2026-09-25-sprint-18.md:29；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:50 | 2026-09-25 |
| A-129 | A-M12 成卡（编辑边界） | docs/iteration/sprint/2026-09-25-sprint-18.md:30；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:51 | 2026-09-23 |
| A-130 | A-M11 成卡（工作流治理） | docs/iteration/sprint/2026-09-25-sprint-18.md:31；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:52 | 2026-09-21 |
| A-131 | 用户插入 TG-20 | docs/iteration/sprint/2026-09-25-sprint-18.md:32；docs/iteration/sprint/2026-09-25-sprint-18.md:50；docs/iteration/sprint/2026-09-25-sprint-18.md:61；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:53；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:54；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:72 | 2026-09-25 |
| A-132 | 用户审定 D1~D8 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:3 | 2026-09-21 |
| A-133 | 三指标＋红线即死拍板 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:22 | 2026-09-21 |
| A-134 | 观察期长度待用户确认 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:32 | 2026-09-21 |
| A-135 | 已采纳 v0（数值不写死） | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:61 | 2026-09-25 |
| A-136 | 恢复须用户二次确认 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:74；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:86 | 2026-09-21 |
| A-137 | §2.3 工具口径裁定 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:110 | 2026-09-21 |
| A-138 | G1 搭车项批准（D4） | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:118；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:166 | 2026-09-21 |
| A-139 | D5 MM 与 G2 并行 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:120；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:167 | 2026-09-21 |
| A-140 | 产品侧插入项待权衡 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:126 | 未标注 |
| A-141 | U2 变更/延期协议 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:145 | 2026-09-25 |
| A-142 | 抽查按双盲 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:147 | 2026-09-21 |
| A-143 | D1 接受三指标阈值 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:163 | 2026-09-21 |
| A-144 | D8 时间盒 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:172 | 2026-09-21 |
| A-145 | B1① M1 升为头号复测指标 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:200；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:22 | 2026-09-25 |
| A-146 | M1+M2+M3 组合不变 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:201 | 2026-09-25 |
| A-147 | F-AC13/14 继续冻结 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:202；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:13；docs/iteration/sprint/2026-09-25-sprint-18.md:37 | 2026-09-25 |
| A-148 | 派单纪律一律留档 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:206 | 2026-09-25 |
| A-149 | 五项待用户裁定 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:208；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:6 | 2026-09-25 |
| A-150 | §3 G2 行仍待裁定 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:209 | 2026-09-25 |
| A-151 | D4 裁定 §6 优先 | docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:100；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:101；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:102；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:103；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:104；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:105；docs/iteration/sprint/2026-09-21-governance-batch-plan.MD:119；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:39；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:128；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:130；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:131；docs/iteration/sprint/2026-09-25-sprint-18.md:11 | 2026-09-25 |
| A-152 | 口径真源 B1①~A3 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:4 | 2026-09-25 |
| A-153 | 机制缺口同样留档定规 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:20；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:126 | 2026-09-25 |
| A-154 | D3 先跑 tech-research | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:52；docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:123；docs/iteration/sprint/2026-09-25-sprint-18.md:31 | 2026-09-25 |
| A-155 | 点数口径已裁定 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:57 | 2026-09-25 |
| A-156 | D1 裁定 12 点含 A-M11 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:121 | 2026-09-25 |
| A-157 | D6 已被 D2 吸收 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:125 | 2026-09-25 |
| A-158 | MM 是否启动由用户另定 | docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD:13 | 2026-09-25 |
| A-159 | 用户要求卡片来源前缀 + UTC+8 口径 | docs/iteration/phases/testing-governance/backlog.MD:7；docs/iteration/phases/refactor-analysis/backlog.MD:6；docs/iteration/phases/mental-models/backlog.MD:7；docs/iteration/phases/testing-governance/2026-09-25-governance-exit-evidence.MD:16 | 2026-09-20 |
| A-160 | TG-7 走查演示发现（BOM 事故立案） | docs/iteration/phases/testing-governance/cards/TG-7.md:13 | 2026-09-20（UTC+8） |
| A-161 | 用户确认 TG-8 进 Sprint-17 | docs/iteration/phases/testing-governance/cards/TG-8.md:13；docs/iteration/phases/testing-governance/cards/TG-8.md:8；docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:103；docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:160 | 2026-09-21 |
| A-162 | 用户确认 TG-9 进 Sprint-17 | docs/iteration/phases/testing-governance/cards/TG-9.md:13 | 2026-09-21 |
| A-163 | TG-11 D2 用户答：两者结合 | docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:99；docs/iteration/phases/testing-governance/2026-09-23-tg11-retro.MD:49 | 2026-09-21 |
| A-164 | TG-11 D3 定稿：三查锚点写入 DoD 必填 | docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD:100 | 2026-09-23 |
| A-165 | TG-17 前移为 Sprint-17 关闭阻塞 | docs/iteration/phases/testing-governance/cards/TG-17.md:7；docs/iteration/phases/testing-governance/cards/TG-17.md:26；docs/iteration/phases/testing-governance/backlog.MD:31 | 2026-09-25 |
| A-166 | TG-17 G2 追加条目（B4②） | docs/iteration/phases/testing-governance/cards/TG-17.md:71 | 2026-09-25 |
| A-167 | TG-18 棘轮破例须交用户裁决 | docs/iteration/phases/testing-governance/cards/TG-18.md:25 | 未标注 |
| A-168 | TG-19 用户 09-25 裁定 B4② | docs/iteration/phases/testing-governance/cards/TG-19.md:13；docs/iteration/phases/testing-governance/cards/TG-19.md:7；docs/iteration/phases/testing-governance/backlog.MD:33；docs/iteration/phases/agents-infra/cards/A-M13.md:7；docs/iteration/phases/agents-infra/backlog.MD:46 | 2026-09-25 |
| A-169 | TG-20 登记册条目字段要求（判定单位写死） | docs/iteration/phases/testing-governance/cards/TG-20.md:22 | 未标注 |
| A-170 | TG-20 验收判据②：原文缺失必须标二手转述 | docs/iteration/phases/testing-governance/cards/TG-20.md:32 | 未标注 |
| A-171 | 用户 2026-09-25 三项决定 | docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:179 | 2026-09-25 |
| A-172 | 用户裁定决策包 A9（P-a~P-d） | docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD:189；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:89；docs/iteration/phases/testing-governance/2026-09-25-d2d3-independent-review.MD:87 | 2026-09-25 |
| A-173 | 用户约束：不跑 run_suite | docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:34；docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:149 | 2026-09-25 |
| A-174 | TG-15⑥ 状态口径需用户裁定 | docs/iteration/phases/testing-governance/2026-09-25-open-items-check.MD:131 | 2026-09-25 |
| A-175 | F-AC14 拍板 Sprint-17 插入 | docs/iteration/phases/refactor-analysis/cards/F-AC14.md:13；docs/iteration/phases/refactor-analysis/cards/F-AC14.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:35 | 2026-09-21 |
| A-176 | F-AC15 拍板 v1 范围分区 + 备 use-case | docs/iteration/phases/refactor-analysis/cards/F-AC15.md:13；docs/iteration/phases/refactor-analysis/cards/F-AC15.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:36 | 2026-09-21 |
| A-177 | F-AC16 用户 2026-09-21 暂不动 | docs/iteration/phases/refactor-analysis/cards/F-AC16.md:22 | 2026-09-21 |
| A-178 | F-AC17 用户插入时间戳 | docs/iteration/phases/refactor-analysis/cards/F-AC17.md:13 | 2026-09-21（UTC+8） |
| A-179 | M18 用户要求 v1 可靠到可做原型验证 | docs/iteration/phases/refactor-analysis/cards/M18.md:13 | 2026-09-21 |
| A-180 | M18 用户 2026-09-21 暂不动 | docs/iteration/phases/refactor-analysis/cards/M18.md:22 | 2026-09-21 |
| A-181 | 走查 CK-1 存疑（F-AC16） | docs/iteration/phases/refactor-analysis/cards/F-AC16.md:13 | 2026-09-20（UTC+8） |
| A-182 | 走查 B-15 存疑（F-AC15） | docs/iteration/phases/refactor-analysis/cards/F-AC15.md:13 | 2026-09-20（UTC+8） |
| A-183 | F-AC13 走查新增问题① | docs/iteration/phases/refactor-analysis/cards/F-AC13.md:13 | 2026-09-20（UTC+8） |
| A-184 | F-AC14 走查新增问题② | docs/iteration/phases/refactor-analysis/cards/F-AC14.md:13 | 2026-09-20（UTC+8） |
| A-185 | F-AC8 终态：dashscope model 用户拍板 | docs/iteration/phases/refactor-analysis/cards/F-AC8.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:29；docs/iteration/pre-research/2026-08-31-domain-governance.MD:72 | 未标注；2026-08-31 |
| A-186 | F-AC11 tooltip 按用户要求移除 | docs/iteration/phases/refactor-analysis/cards/F-AC11.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:32 | 未标注 |
| A-187 | F-AC6 用户复验通过 | docs/iteration/phases/refactor-analysis/cards/F-AC6.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:27 | 未标注 |
| A-188 | R-C / E3 v1 需用户 review（Q3 闸门） | docs/iteration/phases/refactor-analysis/refactor-analysis.MD:53；docs/iteration/phases/refactor-analysis/roadmap.MD:19；docs/iteration/phases/refactor-analysis/roadmap.MD:36；docs/iteration/phases/refactor-analysis/cards/R-C.md:13；docs/iteration/phases/refactor-analysis/cards/R-E3.md:13；docs/iteration/phases/refactor-analysis/backlog.MD:67；docs/5-VERSIONS.MD:41；docs/iteration/ROADMAP.MD:26 | 未标注 |
| A-189 | M3 用户指示未处理 | docs/iteration/phases/refactor-analysis/cards/M3.md:7；docs/iteration/phases/refactor-analysis/backlog.MD:47；docs/iteration/phases/refactor-analysis/roadmap.MD:28；docs/iteration/ROADMAP.MD:17 | 未标注 |
| A-190 | MM-2 Q3：robust & flexibility 硬约束 | docs/iteration/phases/mental-models/cards/MM-2.md:13；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:58；docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:67 | 2026-09-07 |
| A-191 | MM-3 用户 2026-09-07（来源） | docs/iteration/phases/mental-models/cards/MM-3.md:13 | 2026-09-07 |
| A-192 | MM-4 用户 2026-09-07（来源③） | docs/iteration/phases/mental-models/cards/MM-4.md:13 | 2026-09-07 |
| A-193 | MM-5 种子模型使用时机（2026-09-07） | docs/iteration/phases/mental-models/cards/MM-5.md:13；docs/iteration/phases/mental-models/backlog.MD:19 | 2026-09-07 |
| A-194 | 走查结论：未通过 = 暂未发现 | docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:141 | 2026-09-20（UTC+8） |
| A-195 | 走查反馈：验收偏代码层、未覆盖交互面 | docs/iteration/phases/refactor-analysis/2026-09-21-fac13-14-impact.MD:107 | 2026-09-20 |
| A-196 | 用户中途追加硬约束：禁跑自举/真实 API | docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:95 | 2026-09-20 |
| A-197 | 用户禁止调用真实 API（成本敏感） | docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-runs.MD:100 | 2026-09-20 |
| A-198 | TG-11 关键判断：交付必须含可执行闸门 | docs/iteration/phases/testing-governance/cards/TG-11.md:24 | 2026-09-21 |
| A-199 | A-M11 口径：按持久化修复动作类型划域 | docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:13 | 未标注 |
| A-200 | 用户决定 1.24 归 TG-12 执行 | docs/iteration/phases/agents-infra/2026-09-21-a-m11-from-learned.MD:152 | 2026-09-21 |
| A-201 | agents-infra 阶段 2 陈旧注记被指出 | docs/iteration/phases/agents-infra/backlog.MD:48 | 2026-09-21 |
| A-202 | 子代理越界改写历史 Sprint 文档的处置 | docs/iteration/phases/agents-infra/2026-09-23-subagent-scope-breach-case.MD:3 | 未标注 |
| A-203 | 同步节奏定稿（push/PR 两层） | docs/1-WORKFLOW.MD:48 | 2026-08-31 |
| A-204 | 走查验收通过前不得建 PR | docs/1-WORKFLOW.MD:52 | 2026-09-12 |
| A-205 | 调研前置：先跑深度调研 | docs/1-WORKFLOW.MD:63 | 2026-08-30 |
| A-206 | 时间盒与过程监管制度化 | docs/1-WORKFLOW.MD:65 | 2026-08-30 |
| A-207 | 自主开卡制 | docs/1-WORKFLOW.MD:68 | 2026-08-30 |
| A-208 | Sprint 度量与规模约束四条 | docs/1-WORKFLOW.MD:73 | 2026-09-21 |
| A-209 | 经验教训总结关闭前置 | docs/1-WORKFLOW.MD:83 | 2026-08-30 |
| A-210 | fan-out 顺序与条件可调 | docs/1-WORKFLOW.MD:85 | 未标注 |
| A-211 | 卡片来源类型前缀与时间口径 | docs/1-WORKFLOW.MD:391；docs/1-WORKFLOW.MD:401 | 2026-09-20 |
| A-212 | 日期必须每轮核验 | docs/1-WORKFLOW.MD:403 | 2026-09-23 |
| A-213 | 术语：台账只指独立文件 | docs/1-WORKFLOW.MD:409 | 2026-09-21 |
| A-214 | 子代理派单纪律留档 | docs/1-WORKFLOW.MD:417 | 2026-09-25 |
| A-215 | 机制缺口同样留档 | docs/1-WORKFLOW.MD:425 | 2026-09-25 |
| A-216 | 执行点声明：中断留痕半机制化 | docs/1-WORKFLOW.MD:429 | 2026-09-25 |
| A-217 | 执行点声明：structure-guard prose-only | docs/1-WORKFLOW.MD:415 | 2026-09-25 |
| A-218 | 预研上下文传递制度化 | docs/1-WORKFLOW.MD:442；docs/1-WORKFLOW.MD:444 | 2026-08-31 |
| A-219 | 调研分级 P1~P3 拍板 | docs/1-WORKFLOW.MD:442 | 2026-09-07 |
| A-220 | 用户批准打包插队 Sprint-7 | docs/3-LEARNED.MD:145 | 未标注（标题含 Sprint-7） |
| A-221 | 审查范围不得默认收窄 | docs/3-LEARNED.MD:157；docs/3-LEARNED.MD:158；docs/3-LEARNED.MD:160 | 未标注（标题含 Sprint-8 收尾） |
| A-222 | 中间态文件不入库 | docs/3-LEARNED.MD:158；docs/3-LEARNED.MD:160 | 未标注（标题含 Sprint-8 收尾） |
| A-223 | 双 key 共存走通 openai 全流程 | docs/3-LEARNED.MD:148；docs/3-LEARNED.MD:149 | 未标注（标题含 Sprint-7） |
| A-224 | M3 按用户指示留待后续 | docs/5-VERSIONS.MD:35 | 未标注 |
| A-225 | Sprint-15 用户验收通过 | docs/5-VERSIONS.MD:39 | 2026-09-10 |
| A-226 | Sprint-16 用户确认关闭与走查 | docs/5-VERSIONS.MD:40 | 2026-09-21 |
| A-227 | A-M11 用户插入 | docs/iteration/ROADMAP.MD:14 | 2026-09-21 |
| A-228 | 治理批用户四项口径后成稿 | docs/iteration/ROADMAP.MD:18 | 2026-09-21 |
| A-229 | MM-6 用户插入 | docs/iteration/ROADMAP.MD:27 | 2026-09-20 |
| A-230 | 走查修复批次待用户确认排期 | docs/iteration/ROADMAP.MD:28 | 2026-09-20 |
| A-231 | TG-6/7/11/12 用户插入 | docs/iteration/ROADMAP.MD:29 | 2026-09-20；2026-09-21 |
| A-232 | agents-infra 原规划用户批准冻结 | docs/iteration/phases/agents-infra/roadmap.MD:6 | 2026-08-30 |
| A-233 | 用户意见①按职能划分评审 | docs/iteration/phases/agents-infra/roadmap.MD:11 | 2026-08-30 |
| A-234 | 用户意见②用例表 ③Sprint 化 | docs/iteration/phases/agents-infra/roadmap.MD:11；docs/iteration/phases/agents-infra/roadmap.MD:14 | 2026-08-30 |
| A-235 | SQLite 替代 MongoDB 用户确认 | docs/iteration/phases/agents-infra/roadmap.MD:12；docs/iteration/phases/agents-infra/roadmap.MD:20 | 2026-08-30 |
| A-236 | 用户评审三条修改意见 | docs/iteration/phases/agents-infra/roadmap.MD:20 | 2026-08-30 |
| A-237 | 用户转达 main 未保护提示 | docs/iteration/phases/agents-infra/roadmap.MD:26 | 2026-08-30 |
| A-238 | Sprint-9 验收整改用户发现 2 问题 | docs/iteration/phases/agents-infra/roadmap.MD:27 | 2026-08-30 |
| A-239 | 要求 tech-research 与 spec 英文化 | docs/iteration/phases/agents-infra/roadmap.MD:28 | 2026-08-30 |
| A-240 | M3 按用户指示保持未完成 | docs/iteration/phases/refactor-analysis/roadmap.MD:28 | 2026-08-30 |
| A-241 | 用户建议 e2e 测试同步更新 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:8 | 2026-08-31 |
| A-242 | P3 需用户拍板 API 成本预算 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:35 | 2026-08-31 |
| A-243 | 测试治理 D1 范围=A | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:54；docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:78 | 2026-08-31 |
| A-244 | 测试治理 D2 去漂移另立卡 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:55 | 2026-08-31 |
| A-245 | 测试治理 D3 参数预决 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:56 | 2026-08-31 |
| A-246 | 测试治理 D4 现在开卡 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:57 | 2026-08-31 |
| A-247 | 测试治理采纳范围：继续探讨 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:52 | 2026-08-31 |
| A-248 | 预研结果必须作规划上下文 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:53 | 2026-08-31 |
| A-249 | 测试治理决策已拍板汇总 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:78 | 2026-08-31 |
| A-250 | 矛盾以翻案建议交用户裁决 | docs/iteration/pre-research/tech/2026-08-31-testing-governance.MD:62 | 未标注 |
| A-251 | 模型扩展须用户确认 | docs/iteration/pre-research/tech/2026-09-07-mental-models.MD:46 | 2026-09-07 |
| A-252 | 发版排期与参考案例 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:8；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:9 | 2026-09-07 |
| A-253 | 发版 D1 版本号保留现状 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:32；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-254 | 发版 D2 源码包+免安装包 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:36；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-255 | 发版 D3 中文五组 notes | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:39；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-256 | 发版 D4 rc 起步 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:42；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-257 | 发版 D5 tag 与自动化 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:45；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-258 | 发版决策记录三行 | docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:52；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:53；docs/iteration/pre-research/tech/2026-09-07-release-practice.MD:54 | 2026-09-07 |
| A-259 | 调研工作流三目标提出 | docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:8；docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:9；docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:10；docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:11 | 2026-09-07 |
| A-260 | 调研级别用户可覆盖 | docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:23 | 2026-09-07 |
| A-261 | 调研工作流 P1 放 Sprint-16 | docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:58 | 2026-09-07 |
| A-262 | 调研工作流 P2 主代理直执行 | docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:59 | 2026-09-07 |
| A-263 | 调研工作流 P3 阈值可调 | docs/iteration/pre-research/tech/2026-09-07-research-workflow.MD:60 | 2026-09-07 |
| A-264 | lint 依赖须用户裁定取舍 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:3 | 2026-09-23（UTC+8）（第 4 行逐字：收集于 **2026-09-23（UTC+8）**） |
| A-265 | 裁定后执行清单六项 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:140；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:115；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:116；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:117；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:118；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:119；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:120 | 2026-09-21 |
| A-266 | L6 许可证口径由用户接受 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:149 | 2026-09-21 |
| A-267 | lint 各包处置需用户确认 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:86；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:63；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.MD:105 | 未标注 |
| A-268 | 草案中用户 D7 附加前提 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:5 | 2026-09-21 |
| A-269 | 草案最终解释权归用户 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:142 | 未标注 |
| A-270 | 草案列六项需用户决策 | docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:178；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:179；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:180；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:181；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:182；docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:183 | 未标注 |
| A-271 | 多领域方案讨论线提出 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:8 | 2026-08-31 |
| A-272 | 要求①各领域同流程 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:9；docs/iteration/pre-research/2026-08-31-domain-governance.MD:41 | 2026-08-31 |
| A-273 | 要求②各域独立 subagent | docs/iteration/pre-research/2026-08-31-domain-governance.MD:10；docs/iteration/pre-research/2026-08-31-domain-governance.MD:42 | 2026-08-31 |
| A-274 | 要求③主动完善协作方式 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:11；docs/iteration/pre-research/2026-08-31-domain-governance.MD:43 | 2026-08-31 |
| A-275 | 领域路由须用户批准实施 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:24；docs/iteration/pre-research/2026-08-31-domain-governance.MD:30 | 未标注 |
| A-276 | 领域归属争议由用户裁决 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:25 | 未标注 |
| A-277 | 协作改进提案交用户裁决 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:46；docs/iteration/pre-research/2026-08-31-domain-governance.MD:49 | 2026-08-31 |
| A-278 | 用户拍板底座提前批次 | docs/iteration/pre-research/2026-08-31-domain-governance.MD:70 | 2026-08-31 |
| A-279 | 预研索引：测试治理已拍板 | docs/iteration/pre-research/README.md:11 | 未标注 |
| A-280 | 预研索引：发版实践已拍板 | docs/iteration/pre-research/README.md:12 | 未标注 |
| A-281 | 预研索引：调研工作流 P1~P3 | docs/iteration/pre-research/README.md:13 | 未标注 |
| A-282 | 领域壳启用时机由用户启动 | docs/iteration/pre-research/product/README.md:4；docs/iteration/pre-research/marketing/README.md:4 | 未标注 |

## 5. 违反裁决的事故索引（引用事故档，不在此复制事实）

| 裁决条目 | 事故档 | 形态（一句话） |
|---|---|---|
| D-250925-01（B4②/机制缺口） | [`2026-09-25-gate-mechanism-failure-modes-case.MD`](iteration/phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD) | 闸门自身失效却仍打印成功（自指断言 / `-O` 空转 / 空扫描 PASS / 横幅 / 上限自证 / 判定域 / 手抄读数…） |
| D-250921-H8（派单留档） | [`2026-09-25-subagent-dispatch-failure-modes-case.MD`](iteration/phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD) | 手抄 sha / 中断不留痕 / 对照走假路径 / 报告≠提交 / 环境等价造假 / 前提未验 |
| D-250925-10（机制缺口留档） | 同上两档 | 主代理自身两次给 CI 脚本传短 sha（修法＝把解析做进工具） |
| 编辑边界纪律（`A-M12`） | [`2026-09-23-edit-boundary-incidents-case.MD`](iteration/phases/agents-infra/2026-09-23-edit-boundary-incidents-case.MD)；[`2026-09-21-sprint-17.md` §10](iteration/sprint/2026-09-21-sprint-17.md) | `edit` 的 `old_string` 取边界内容 ⇒ 标题/表格单元格被吞（R1 同型多次） |

## 6. 待逐字核对（原文取自会话压缩摘要，**逐字性存疑**，不得当作原文引用）

> 以下条目来自本会话**更早时段**，我目前只有压缩摘要里的转述形式 ⇒ 依"还原事实"要求，**先登记、标注存疑**，待与会话原文核对后再升级为 `原文（逐字）`。**在此之前任何人引用它们都必须带上本条警告。**

| 条目 | 摘要形式（**非逐字**） | 主题 | 生效状态 |
|---|---|---|---|
| D-250925-P1 | "不要动不动就grep" | 工具使用纪律（少用 grep，优先读文件） | 生效（存疑原文） |
| D-250925-P2 | "push 之后…你可以通过api接口拿到BI结果 不需要我代为转述" | CI 结论自行取证，不转述 | 生效（存疑原文） |
| D-250925-P3 | "这一次我不想再看到在sha的传参.使用上发生任何问题了" | 禁止手抄 sha（后成为 `1-WORKFLOW.MD` §6 第 1 条） | 生效（存疑原文） |
| D-250925-P4 | "同样的数值别写死" | 派生数字不得手抄（后成 `verify_derived_numbers.py`） | 生效（存疑原文） |
| D-250925-P5 | "未实现目标都需要check下" | 未实现目标要逐项核查 | 生效（存疑原文） |
| D-250925-P6 | "其他按流程要求需要派子代理的任务正常派单即可" | 授权按流程派单 | 生效（存疑原文） |
| D-250925-P7 | "继续执行直到需要我判断的地方为止" | 自主推进边界 | 生效（存疑原文） |
| D-250925-P8 | "为什么这次余额消耗的这么快？不是节假日也是off-peak吗" | 成本口径询问（当日答复：中秋节全时段 off-peak，消耗主因是工作量） | 已答复（存疑原文） |
