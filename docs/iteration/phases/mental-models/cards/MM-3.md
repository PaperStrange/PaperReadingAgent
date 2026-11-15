# MM-3 种子模型实例化首跑：思维实验 → `agents/functions/thought-experiment.md` + 

- `card`: MM-3
- 索引: [../backlog.MD](../backlog.MD)

## 状态
进行中

## 规模
2

## 来源
用户 2026-09-07

## Sprint
**独立并行线（G2 不含、不占其点数；2026-09-25 D4 裁定）**——原写 `Sprint-18（与治理批 G2 并行）`；G2 的口径是"≤14 点纯治理"（见 [`2026-09-25-governance-batch-plan-G2.MD` §0/§8.2](../../../sprint/2026-09-25-governance-batch-plan-G2.MD)），本卡若要启动需用户另行指定批次。

## 正文
种子模型实例化首跑：思维实验 → `agents/functions/thought-experiment.md` + validate-spec + 首跑演示（三方案比对文档）

## 落地（2026-11-15）

**状态为「进行中」而非「完成」**：草案、首跑记录与提审清单已交付，但**把草案提升为 `agents/functions/thought-experiment.md` 属生产面改动，未经用户裁决**，故本卡差最后一步（见下方提审清单）。

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

**为什么不本轮直接做**：`agents/**` 是 agent 的生产面（`verify_agentops` 对其做封闭世界校验），升格会影响 role↔spec 一致性、结构守卫与套件判据；且"是否把思维实验变成常驻 agent"是产品决策，属用户裁决范围。草案与首跑已证明**模型能生成可执行 spec 骨架并被真实使用一次**，这正是本卡的可验证部分。
