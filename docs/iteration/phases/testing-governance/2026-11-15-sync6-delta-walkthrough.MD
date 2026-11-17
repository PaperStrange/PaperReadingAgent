# 第 6 次同步 · 增量走查清单（2026-11-15）

> **为什么有这份清单**：`docs/1-WORKFLOW.MD` §3 规定「**用户走查验收通过之前不得创建 PR**」。
> 上一次走查签收是 **2026-11-11**，其覆盖范围是当时的快照；此后 `windows` 又有新增量。
> 本清单只覆盖**自同步 #5（main `945286a`）以来、本次同步将要带上 main 的增量**，逐项可复制执行。

## 过程缺口记录（如实）

**同步 #5（PR #58，2026-11-15）** 是在 11-11 走查签收之后、**未对新增量重新走查**的情况下创建 PR 的。
这是一个流程缺口：走查签收的语义是"这一批即将进 main 的内容已被用户看过"，而不是"曾经看过一次就长期有效"。
本清单用来补齐第 6 次同步的走查；**缺口本身记在这里，不隐藏。**

## 1. 本次同步面（结构）

| 判据 | 命令 | 期望 |
|---|---|---|
| 同步面只有这些非-iteration 文件 | `git diff --name-status origin/main..HEAD -- . ':!docs/iteration'` | `A scripts/mental-model-spec.py`；另有 4 个 `D scripts/*.sh` **属保留项**（见下） |
| `docs/iteration/**` 不同步 | `git diff --name-only origin/main..HEAD -- docs/iteration \| Measure-Object` | 无论多少，**同步树内必须为 0** |
| **4 个 mac 启动脚本保留** | `git ls-tree -r --name-only origin/main -- scripts/setup-env.sh scripts/start-backend.sh scripts/start-frontend.sh scripts/start-streamlit.sh` | **4 条**（它们在 main/mac 上，windows 本就没有；同步时按 `mac-sh-keep` 跳过删除） |
| `docs/6-DECISIONS.md` 在树 | `git ls-tree -r --name-only origin/main -- docs/6-DECISIONS.md` | 1 条 |

## 2. 内容（这次真正新增到 main 的东西）

| 件 | 它做什么 | 走查要点 |
|---|---|---|
| `scripts/mental-model-spec.py` | 思维模型 JSON → 五段式 agent spec 骨架的**纯 stdout 渲染器**（不写盘） | ① `--model` 渲染出的内容与 `docs/iteration/.../library/examples/thought-experiment.spec.md` **逐字节一致**（样例在 windows-only 目录，可自行跑比对）；② 缺必填字段 ⇒ **rc≠0 且不产出**；③ **无写盘路径**（这正是它通过 `verify_artifact_paths` 的方式） |
| `agents/functions/thought-experiment.md`（**待升格落地后**） | 生产 agent spec：思维实验（比较模式／隔离模式）＋ 判别性检验 | 见该文件 `# References`：外部参考采纳了什么、拒绝了什么 |

## 3. 闸门（在**同步树**形态跑，不是 windows 形态）

| 判据 | 命令 | 期望 |
|---|---|---|
| 离线套件 | `.venv\Scripts\python.exe verify\run_suite.py --tier offline`（在同步树工作目录） | `SUITE PASSED`（脚本数以输出为准）；**第三态**为具名 SKIP（无账本 ⇒ `verify_agentops`/`verify_spend_report` SKIP），rc=3 时末行须带 `SKIP!=PASS` 语义 |
| 决策登记册（真数据） | `python verify/verify_decision_register.py` | `ALL PASS`；main 形态下 `quotes_checked` 显著小于 windows（iteration 文档缺席 ⇒ 引文不可核），`pointers` 仍全量计数 |
| 结构守卫 | `python scripts/structure-guard.py verify --from-git origin/main` | `STRUCTURE PASS`（无"文件消失"误报） |
| 矩阵一致 | `python verify/verify_matrix.py check` | `CHECK OK` |
| 派生数字 | `python verify/verify_derived_numbers.py` | `ALL PASS` |

## 4. 明确"未证明"的项（不要读成已验）

- `docs/iteration/**` 的 **1106 处指针**在 main 上**永远不可核**（文件不在树）——这是设计，不是缺陷，但**不能声称"已核"**；
- 新增的 `scripts/mental-model-spec.py` **没有 CI 回归门**（它是本地开发工具，不进套件）；它"能用"靠的是人工/子代理跑过的证据；
- 走查**不覆盖** `docs/iteration/**` 内的思维模型产物（MM-1/2/3/4/6 的卡与记录），那些按设计留在 windows。

## 5. 红旗（任一条命中即不通过）

- 同步树里出现任何 `docs/iteration/` 文件；
- 4 个 mac 启动脚本在 main 上**减少**；
- 套件把第三态算成失败（或把 `rc=3` 当通过）；
- 新增 spec 缺 `# References` 或声称"已通过内容评审"（归属≠评审）；
- 任何"派生数字手抄"进文档（`verify_derived_numbers` 会抓）。

## 6. 签收

| 项 | 填 |
|---|---|
| 走查日期（网络时间 UTC+8） | **2026-11-17（`python scripts/now-network.py` 现取）** |
| 结论 | **☑ 通过** |
| 哪几项不过（写编号） | 无 |
| 想让我先修哪个 | — |

**记录方式（如实）**：结论由用户在会话中直接给出（"走查通过 继续吧"）；**未逐项列出 §1–§5 的读数**，本表只记录"用户声明通过"这一事实与日期，不代填逐项结果。
**连带效果**：`docs/1-WORKFLOW.MD` §3「走查验收通过之前不得创建 PR」对本批**已满足**，故允许创建第 6 次同步的 PR。

**顺带记录（未裁决项）**：MM-3 升格时 spec 与种子模型的 **4 处差异**（≥3 方案的适用范围、"未证实机制"改为显式假设、输出形态、触发条件）仍待用户逐条裁决；本轮**未改** `library/thought-experiment.v0.1.json`，差异只登记在 MM-3 卡，**不冒充已获新裁决**。

> 签收后我才会：造单亲同步分支 → 草稿 PR → main 侧 CI → 合并 → 复核 main 树 → 追加执行记录。
