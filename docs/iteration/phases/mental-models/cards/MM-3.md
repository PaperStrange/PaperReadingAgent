# MM-3 种子模型实例化首跑：思维实验 → `agents/functions/thought-experiment.md` + 

- `card`: MM-3
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
2

## 来源
用户 2026-09-07

## Sprint
**独立并行线（G2 不含、不占其点数；2026-09-25 D4 裁定）**——原写 `Sprint-18（与治理批 G2 并行）`；G2 的口径是"≤14 点纯治理"（见 [`2026-09-25-governance-batch-plan-G2.MD` §0/§8.2](../../../sprint/2026-09-25-governance-batch-plan-G2.MD)），本卡若要启动需用户另行指定批次。

## 正文
种子模型实例化首跑：思维实验 → `agents/functions/thought-experiment.md` + validate-spec + 首跑演示（三方案比对文档）

## 落地（2026-11-15）

**2026-11-16 升格后状态为「完成」**（本段保留 2026-11-15 的原始判断供审计）：当时草案、首跑记录与提审清单已交付，但**把草案提升为 `agents/functions/thought-experiment.md` 属生产面改动，未经用户裁决**，故本卡差最后一步。用户已批准本批升格，结果见下方「升格结果」。

### 交付物

| 件 | 路径 | 说明 |
|---|---|---|
| spec 草案 | [`drafts/thought-experiment.spec-draft.md`](../drafts/thought-experiment.spec-draft.md) | 由 MM-2 生成器经 **stdout 重定向**落盘；头部带草案声明（未注册为生产 spec、未进 `agents/functions/`） |
| 首跑记录 | [`experiments/TE-2026-11-15-anchor-scope.md`](../experiments/TE-2026-11-15-anchor-scope.md) | 第 1 份真实思维实验记录：题＝A-PTR 迁移是否扩到 iteration 的 1106 处指针；三条路径（A 全量迁移／B 局部试点／C 维持现状） |
| 提审清单 | 本卡下方 `## 提审清单` | 升格为生产 spec 需要的改动与校验，逐条给闸门/命令 |

### 首跑机检（MM-6 的判据：路径数＝falsifier 数、无裸 falsifier）

- `### 路径` 条数与 `- falsifier:` 条数相等（各 3 条），无裸 falsifier（每条 falsifier 均给出命令或读取动作）；
- 三条路径的 `verdict` 分别是 **FAIL／PASS／未验证**——第三种态是合法的，未折叠成 PASS；
- 记录消费约束满足：`question`／`baseline`／`material`／`freeze` 自带指针与命令（C1）；`判决证据` 为「系统＋标识符＋判决＋rc」（C2）；未验证显式（C3）。

### 执行说明（如实）

本卡原派给 codex 子代理（`run-2026-11-15-implementation-149`）：它完成了草案，**之后长时间无终态**（账本 `status=running` 超过 40 分钟、`experiments/` 未建），lead 据此把它**如实收为 `failed`**（错误说明已记入账本）并以 `run-2026-11-15-implementation-151` **接管补完**。接管期间该执行者又**迟交了一份首跑记录**（14KB、含三组只读探针）——两份同题记录已合并为**唯一主记录**（保留其探针，追加 lead 的 main 形态证据，并按 MM-6 把 verdict 规范化为三态），重复的那份已删除。**既不包装失败，也不丢弃已完成的产出。**

两点补充事实：① 执行者事后尝试 `finish --status succeeded` 被 CLI 拒绝（`非法流转 failed -> succeeded`）⇒ 终态保持 `failed`，其**未完成共享卡合入**的事实与账本一致；② 它那份同题记录的**完整正文与对照**已备份在 `agents/runs/run-2026-11-15-implementation-149/implementation.report.md`（账本 `result_files` 指向），合并后的主记录保留了它的全部路径与探针节，审计可回溯。

### 升格结果（2026-11-16）

用户批准把草案升格为生产 spec，本卡由「进行中」→「完成」。

| 件 | 值 |
|---|---|
| spec | [`agents/functions/thought-experiment.md`](../../../../../agents/functions/thought-experiment.md)（v1.0.0；`scope_required: false`、`coverage_window: none`：分析产出不声明 scope、不承担 C3 内容覆盖） |
| 登记 run | `run-2026-11-16-implementation-152`（implementation；已 `finish --status succeeded`，并用 `set-anchor` 显式设端点） |
| 正文结构 | 五段式：`# Role` / `# Trigger` / `# Task Input` / `# Configurable Parameters` / `# Steps`，另加 Output discipline / Output Template / Forbidden / References；正文英文（[`agents/README.md`](../../../../../agents/README.md) 的 spec 语言约定），TE 记录仍中文 |
| validate-spec | `python scripts/agent-ops.py validate-spec agents/functions/thought-experiment.md` → PASS（末行以现跑为准） |
| 角色枚举闭合 | `load_policy().closure_problems() == []`；role 由 `policy.json::spec_dir`／`spec_glob` 自动枚举，**未新增 `roles` 键** |

**mode 设计（本升格的核心判断）**：外部参考是"单变量受控反事实"，本仓种子是"≥3 方案对比推演"——两条不同的思维实验传统。spec 用**两个显式 mode** 调和，一条记录只用一个 mode，不混用：

| mode | 适用 | 路径下限 | 专属失败判据 |
|---|---|---|---|
| `compare`（默认） | 在冻结基线下选方案 | `min_paths=3`，且必须含"维持现状" | F1（路径不足／假选择／缺现状） |
| `isolate` | 一个因果变量、其余可钉死 | `min_paths=2`（处理＋对照） | I1（多自由变量／条件未钉死）、I2（缺对照臂） |

两种 mode 共用 F2–F6（fact 无指针／falsifier 不可取得／未跑写 PASS／静默重议基线／只在该环境成立却对外）。`mode`、`min_paths`、`max_paths`、`cheapest_action`、`empiricism_override`、`stop_rule`、`record_dir` 全部是 spec `# Configurable Parameters` 里的可调项。

**外部参考采纳表**（来源 `tjboudreaux/cc-thinking-skills`）：

| 来源 | 采用 | 拒绝（理由） |
|---|---|---|
| [仓库](https://github.com/tjboudreaux/cc-thinking-skills) | 何时用／何时不用：真实实验太贵/太罕见/不可逆才做；有廉价真测就先做（empiricism override）；安全红队走红队结构；机制已知只需决断；无受控变量的脑暴不合法 | — |
| [SKILL.md](https://raw.githubusercontent.com/tjboudreaux/cc-thinking-skills/main/skills/thinking-thought-experiment/SKILL.md) | 6 步程序、输出字段、校验（隔离／机制／有界推论／一链即停）；与 MM-6 S1–S6 合成**一套固定顺序**（对应表在 spec `# Steps`） | `disable-model-invocation`（本仓有自己的派单模型：账本 `register` ＋ `fanout.json` ＋ spec，再引入一个调用控制通道＝两个真源）；"只允许单变量"作为唯一合法形态（种子要求 ≥3 方案对比 ⇒ 双 mode） |
| [评估契约](https://raw.githubusercontent.com/tjboudreaux/cc-thinking-skills/main/evals/contracts/thinking-thought-experiment.json) | 判别性检验的"最便宜动作"口径、过度应用守卫（一链＋有界推论＋一个判别检验即停，禁止 scenario sprawl） | 契约 JSON 格式本身（本仓验收面＝`validate-spec` ＋ F1–F6 ＋ 被主代理消费的 TE 记录；第二套契约格式会成为无人读的数据） |

**spec 与种子模型的差异（供用户裁决；`library/thought-experiment.v0.1.json` 未改）**：

| # | 种子口径 | spec 现状 | 性质 |
|---|---|---|---|
| 1 | "不少于三种解决方案"无条件 | ≥3 只在 `compare`；`isolate` 为 2 臂（处理＋对照） | 实质差异：按"两个显式 mode"要求做的调和；若要"任何 mode 都 ≥3"，把 `min_paths` 调成 3 即可 |
| 2 | 未证实的作用机制不得写入 | 未证实机制只能以显式 assumption 进入，并在第 4 步作为断点（"若为假设则该链作废"） | 解释差异：禁止编造 ≠ 禁止显式假设；若要更严，删该条即可 |
| 3 | 输出"不少于 3 个方案 × …"的比对文档 | `compare` 产出多路径记录；`isolate` 产出单变量反事实记录 | 形态差异：同一记录骨架，`isolate` 不产 3 列对比 |
| 4 | 触发＝"检测到用户输入讨论时" | 触发必须是 fanout step／卡号／走查轮次／决策点；"讨论时"不算触发 | 收紧（MM-6 §2.2）；与种子原话不同 |

## 提审清单

把草案提升为 `agents/functions/thought-experiment.md` 之前，至少逐条完成：

| # | 改动/校验 | 命令或判据 |
|---|---|---|
| 1 | 在 `agents/policy.json` 登记该 spec 的 role／能力边界（若 policy 有 role→spec 映射） | 读 `agents/policy.json::roles` 结构后按既有格式增项；`python verify/verify_agentops.py`（UC 里对 role↔spec 的封闭世界判据）须仍 `ALL PASS` |
| 2 | 补全草案里留空的人审项（`## Forbidden` 的边界是否与 §6 规则冲突、`# Steps` 的可执行粒度） | 人工审读；用 `agents/functions/_template-agent.md` 对照段名 |
| 3 | 跑 `validate-spec`（若 agent spec 有该入口） | `python scripts/agent-ops.py validate-spec <spec>`（`agent-ops.py` 现有子命令之一；无此能力则先在卡上登记缺口） |
| 4 | 结构守卫：新增 spec 是否触发结构变更签名要求 | `python verify/structure-guard.py verify --from-git HEAD`（若报签名要求，按 `Structure-Removal:` 口径处理） |
| 5 | 闸门矩阵与断言下限同步（若新增 verify 或改闸门） | `python verify/verify_matrix.py derive && check`；`BRANCH_ASSERTION_FLOORS` 只增不减 |
| 6 | 套件全绿（**提交前必须跑完整套件**，今天的两次漏都出在"只跑了局部闸门"） | `.venv\Scripts\python.exe verify\run_suite.py --tier offline` |
| 7 | 用户裁决：生产面改动是否批准 | 卡与 `backlog` 状态由「进行中」→「完成」**只在用户确认后**执行 |

### 执行记录（2026-11-16，7 条逐条）

| # | 结果 | 证据（命令末行以现跑为准） |
|---|---|---|
| 1 | 已执行；角色枚举自动闭合，未新增 `roles` 键 | `load_policy().closure_problems() == []`；新 spec 被 `spec_dir`／`spec_glob` 枚举为 role `thought-experiment` |
| 2 | 已执行（人审项已补） | `# Steps` 6 步可执行粒度；`# Forbidden` 与 `1-WORKFLOW.MD` §4.4／§6 不冲突；段名对照 `_template-agent.md` |
| 3 | 已执行 | `python scripts/agent-ops.py validate-spec agents/functions/thought-experiment.md` → PASS（末行以现跑为准） |
| 4 | 已执行 | `python scripts/structure-guard.py verify --from-git 439d3bdfb23fcfe85d36e432e7d5e42d198ebaab` → STRUCTURE PASS |
| 5 | 不适用（未新增 verify、未改闸门） | 未动 `VERIFY_META`，按清单**只跑** `python verify/verify_matrix.py check`，未 derive |
| 6 | 已执行 | `.venv\Scripts\python.exe verify\run_suite.py --tier offline` → 末行以现跑为准 |
| 7 | 已批准并已执行 | 用户批准本批升格（派单原文）；卡与 `backlog` 状态→完成，spec 入库 |

### 执行者补充的更精确提审项（2026-11-15，原文要点）

- 补生产 frontmatter，并按 MM-6 补齐输入／步骤／记录骨架／F1–F6；然后跑
  `python scripts/agent-ops.py validate-spec agents/functions/thought-experiment.md`。
- 角色枚举走 `load_policy().closure_problems()`；**当前 role 由 `policy.json::spec_dir`／`spec_glob` 枚举，
  不需要新增 `roles` 名单键**（这一点修正了上表第 1 行的猜测）。
- 跑 `python verify/verify_agentops.py`，重点看 **UC-1／UC-15／UC-16**。
- 跑 `verify_close_readiness.py --sprint …` 核 **C1／C2／C3**；**不能把建议角色当成内容评审**（归属≠评审）。
- 跑 `python scripts/structure-guard.py verify --from-git <提升前完整 HEAD>`、`verify_md_tables.py`、
  `verify_derived_numbers.py`，并检查 LF。
- **未改 `VERIFY_META` 时只跑 `verify_matrix.py check`；新增检查才先 `derive` 再 `check`。**
- 提升获准后，以**生产角色真实首跑**并执行 falsifier 正反对照，再登记采纳与收尾。

**为什么 2026-11-15 没有本轮直接做（历史记录，保留供审计）**：`agents/**` 是 agent 的生产面（`verify_agentops` 对其做封闭世界校验），升格会影响 role↔spec 一致性、结构守卫与套件判据；且"是否把思维实验变成常驻 agent"是产品决策，属用户裁决范围。草案与首跑已证明**模型能生成可执行 spec 骨架并被真实使用一次**，这正是本卡的可验证部分。**2026-11-16 用户批准后本段已不是当前状态**：升格按上表 7 条执行完毕，结果见「升格结果」。

## 裁决（2026-11-17）

上方"4 处差异"表记录的是**升格当时**的状态，这里补上用户 2026-11-17 的逐条裁决；**历史差异表正文不改**。

| # | 裁决 | 落地 |
|---|---|---|
| ① 方案数范围 | **接受 spec**（`compare:3`／`isolate:2`） | 无改动 |
| ② 未证实机制 | **不接受 spec；回退种子的零假设口径** | spec 改 `# Steps` 3/4、`# Output Template`、`# Forbidden`、`# References`；未证实链接改为 `chain_gap` 截断链 |
| ③ 输出形态 | **接受 spec**（TE 记录），另补**历史文档处理方案与留痕** | 新增 [`2026-11-17-seed-spec-divergence.MD`](../2026-11-17-seed-spec-divergence.MD)（冻结档清单＋读法规则＋裁决记录） |
| ④ 触发条件 | **接受 spec**，另补**初始化约束方式、场景策略、登记内容、各场景自动化流程记录（需图示）** | spec 新增 `# Initialization constraints`＋`# Scenario strategy`（含 mermaid 流程图、四场景表、抽检口径） |

- spec 版本：**1.0.0 → 1.1.0**（`validate-spec` PASS）。
- 种子 JSON 与预研档**未改**（历史原文冻结）；差异与裁决只在本文档与卡上留痕。
- 既有首跑记录 `experiments/TE-2026-11-15-anchor-scope.md` 不含 `assumption` 条目，两种口径下均成立，**不需重判**。
