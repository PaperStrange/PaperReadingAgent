# 第 7 次同步 · 增量走查清单（2026-11-17）

> 规则：`docs/1-WORKFLOW.MD` §3「用户走查验收通过之前不得创建 PR」。本清单只覆盖 **main `0884ff3` 以来、本次同步将带上 main 的增量**。

## 1. 本次同步面（结构）

| 判据 | 命令 | 期望 |
|---|---|---|
| 非-iteration 增量 | `git diff --name-status origin/main..HEAD -- . ':!docs/iteration'` | 仅 `M agents/functions/thought-experiment.md`（可能另有 `M docs/6-DECISIONS.md` 一条裁决，见 §2） |
| 4 个 mac 脚本 | `git ls-tree -r --name-only origin/main -- scripts/setup-env.sh scripts/start-backend.sh scripts/start-frontend.sh scripts/start-streamlit.sh` | 4 条（同步保留，不变） |
| `docs/iteration/**` | 同步树内计数 | 0 |

## 2. 内容

| 件 | 变化 | 走查要点 |
|---|---|---|
| `agents/functions/thought-experiment.md` | v1.0.0 → **v1.1.0** | ① 搜索 `may enter only as an explicitly labelled assumption` ⇒ **0 处**（② 回退）；② 搜索 `chain_gap` ⇒ **≥1 处**，且语义为"链在缺机制处中断＋补证观测"；③ `# Steps` 第 3/4 步、`# Output Template::断点`、`# Forbidden`、`# References` 四处均已改；④ 新增 `# Initialization constraints`（8 项必填＋拒绝条件）与 `# Scenario strategy`（mermaid 流程图＋四场景表＋抽检四件事）；⑤ `estimated_chars` 已按实际规模修正 |
| `docs/6-DECISIONS.md`（待补） | +1 条裁决条目 | 出处用**锚点**指向 `agents/functions/thought-experiment.md#<锚文本>`（该文件在 main 上也存在 ⇒ 两形态都可核）；原文为 2026-11-17 用户裁决**逐字**；插入后 1 处自指指针（`:1663`）按内容重定位 |

## 3. 闸门（同步树形态）

| 判据 | 期望 |
|---|---|
| `run_suite.py --tier offline` | `SUITE PASSED`（脚本数以现跑为准；第三态为具名 SKIP） |
| `verify_agentops.py` | `ALL PASS`（断言语义条数同步） |
| `verify_decision_register.py` | `ALL PASS`，`pointers`／`quotes_drift` 不劣化（新增 1 条裁决后计数会 +N，以现跑为准） |
| `structure-guard verify --from-git origin/main` | `STRUCTURE PASS` |
| `verify_matrix.py check` | `CHECK OK` |

## 4. 明确"未证明"的项

- `docs/iteration/**` 的 1106 处指针在 main 上仍不可核（设计如此）；
- 新增的 `# Scenario strategy` 流程图是**流程记录与抽检口径**，**不代表已自动派单**：`agents/fanout.json` 未登记该 agent，实际入口仍为「主代理/用户点名」（详见 spec 的 `# Trigger`）；
- ②「未证实机制不得写入」是 spec 规则，**当前没有闸门**逐条检查 TE 记录里是否出现 assumption 字样（文字规则，A-DECL 同类隐患，已登记为后续项）。

## 5. 红旗（任一命中即不通过）

- 同步树出现 `docs/iteration/` 文件；
- mac 启动脚本减少；
- `may enter only as an explicitly labelled assumption` 仍存在于 spec；
- 裁决条目出处指向 `docs/iteration/**`（会抬高 absent 指针棘轮）；
- 手抄派生数字进文档（`verify_derived_numbers` 会抓）。

## 6. 签收

| 项 | 填 |
|---|---|
| 走查日期（网络时间 UTC+8） | **2026-11-17（`python scripts/now-network.py` 现取）** |
| 结论 | **☑ 通过** |
| 哪几项不过（写编号） | 无 |
| 想让我先修哪个 | — |

**记录方式（如实）**：结论由用户在会话中直接给出（"走查通过"）；未逐项列出 §1–§5 读数，本表只记录"用户声明通过"这一事实与日期，不代填逐项结果。
**连带效果**：`1-WORKFLOW.MD` §3「走查验收通过之前不得创建 PR」对本批已满足。
