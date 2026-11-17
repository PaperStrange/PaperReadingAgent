# 种子模型 vs 生产 spec 的口径差异 · 裁决与历史文档处理（2026-11-17）

> 归属：`docs/iteration/phases/mental-models/`。真源分工：**当前口径只信** `agents/functions/thought-experiment.md`
> （v1.1.0）与本文的裁决记录；**历史原文不改**（见 §2）。本文是 2026-11-17 用户裁决的留痕，不重写任何历史文档正文。

## 1. 用户裁决原文（2026-11-17，逐条）

| # | 差异 | 裁决 | 落地位置 |
|---|---|---|---|
| ① | 种子"不少于三种方案"（无条件） vs spec `compare:3 / isolate:2` | **接受 spec** | spec `# Configurable Parameters::min_paths`（未改） |
| ② | 种子"未证实的作用机制不得写入" vs spec"允许显式 assumption＋断点" | **不接受 spec；回退到种子的零假设口径** | spec `# Steps` 第 3/4 步、`# Output Template::断点`、`# Forbidden`、`# References`（已改，见 §3） |
| ③ | 种子输出"3 方案比对文档" vs spec 输出 TE 记录 | **接受 spec**；并**补充历史文档处理方案并留痕**（本文） | spec `# Output Template`（未改）；本文 §2／§4 |
| ④ | 种子触发"检测到用户输入讨论时" vs spec"可登记触发" | **接受 spec**；并**补充初始化约束方式、场景策略**（登记内容、各场景自动化流程记录，**需有图示**方便抽检与人工阅读） | spec 新增 `# Initialization constraints`、`# Scenario strategy`（含 mermaid 图与登记/抽检表） |

## 2. 冻结的历史档（**禁止改正文**，只允许在本文/卡里登记差异）

| 历史档 | 冻结理由 | 处置 |
|---|---|---|
| `docs/iteration/phases/mental-models/library/thought-experiment.v0.1.json` | 用户 2026-09-07 **原话**，是种子的唯一原始载体；改它等于改写历史 | **不动**。其 `success_criteria`/`output` 里的"三方案比对文档"按历史原文读，现口径见 spec |
| `docs/iteration/pre-research/tech/2026-09-07-mental-models.MD` §2.4 | 预研结论档，Q2 已拍板；历史决策依据 | **不动** |
| `docs/iteration/phases/mental-models/cards/MM-3.md` 的"4 处差异"表 | 记录的是**升格当时**的状态 | 表正文**不改**；在其后追加 `## 裁决（2026-11-17）` 指向本文 |
| `docs/iteration/phases/mental-models/experiments/TE-2026-11-15-anchor-scope.md` | 首跑记录（已有结论） | **不动**；经核其对 ② 的两种口径都成立（记录里 0 处 `assumption`，只有 `fact:`/`inference:`） |

**读法规则**：历史档 = 冻结原文（可能含已被更新的口径）；当前口径 = `agents/functions/thought-experiment.md`
（版本号 ≥ v1.1.0）＋本文裁决表。**读者遇到"三方案比对文档/讨论时触发/显式假设"这类措辞时，一律以 spec 为准，
并回到本文看裁决。**

## 3. ② 的回退落地（零假设口径）

| 位置 | 改前 | 改后 |
|---|---|---|
| `# Steps` 第 3 步 | 未证实机制**可作为显式 assumption 进入**，第 4 步记为断点 | 未证实机制**不得写入**；链在此**中断**，记 `chain_gap`（缺的机制名＋能补上它的观测），该路径记 `未验证（机制未证实）`，除非缺此步仍能支撑结论 |
| `# Steps` 第 4 步 | `break_points` = 依赖假设的步＋"若假设为假则链作废" | `break_points` = **因机制未证实而中断**的步；缺的机制、补证观测、缺此步仍成立的部分；说不出停止点即 `无效（F2）` |
| `# Output Template` | `断点: <…依赖假设…>` | `断点: <…因机制未证实而中断…>` |
| `# Forbidden` | "不得编造机制；未证实链接是 assumption 与断点" | "**不得写入未证实机制**；未证实链接以 `chain_gap` 截断链，**既不当 assumption 携带、也不升级为事实**" |
| `# References` | 外部"labelled assumption"被采纳 | 标记为**部分拒绝**（2026-11-17 裁决） |
| 版本 | 1.0.0 | **1.1.0** |

**对既有记录的影响**：`TE-2026-11-15-anchor-scope.md` 无 `assumption` 条目（0 处），两种口径下均成立，**不需要重判**。

## 4. ④ 的补充落地

spec 新增两节：

1. `# Initialization constraints`：**初始化约束表**（`stage`／`trigger`／`question`／`baseline`／`freeze`／`material`／
   `mode`＋`isolated_variable`／`run_dir`），逐行给出"必须长什么样"与"什么情况拒绝"；preflight 在任何推理之前
   跑完，失败则**拒绝并返回理由、不创建记录**。
2. `# Scenario strategy`：四场景（design／dev／retro／acceptance）的
   **入口 → mode 规则 → 记录产物 → 账本登记内容 → 人工抽检点**，附 **mermaid 流程图**（每根箭头都对应一个记录产物
   或账本字段）；并写明**每次运行必须留下的四件事**（TE 文件／账本行／判决证据／adoption 留空）作为抽检口径。

图示位置：spec `# Scenario strategy` 节内（`flowchart TD`，含四个 subgraph 与"拒绝/无效/采纳"分支）。
**渲染说明**：GitHub 原生渲染 mermaid；本仓已有 mermaid 先例（`docs/2-ARCHITECTURE.MD` 等 8 处）。

## 5. 为什么本文不写进 `docs/6-DECISIONS.md`

登记册的机检要求每条**出处**可核；本文位于 `docs/iteration/**`，它在 main 上**不存在**，新增一条指向它的 `path:line`
指针会抬高登记册的 **absent 指针计数**（当前棘轮上限＝1106，见 `1-WORKFLOW.MD` §3 排除项③）。因此：
- 本次裁决**留痕在本文＋MM-3 卡＋spec 的 References 指针**（三者皆可被 windows 侧读者检索）；
- 若将来需要进登记册，须**同时**处理带指针棘轮（或改指向 main 上存在的文件，如 `agents/functions/thought-experiment.md`），
  属独立批次，本文只登记该未决点。

## 6. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-17 | 初版：记录 2026-11-17 用户 4 条裁决，登记冻结历史档清单与读法规则，说明未进登记册的原因 |
