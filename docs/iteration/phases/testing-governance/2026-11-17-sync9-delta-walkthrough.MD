# 第 9 次同步 · 增量走查清单（2026-11-17）

> **规则**：`docs/1-WORKFLOW.MD` §3「用户走查验收通过之前不得创建 PR」，以及 2026-11-17 新增例外
> （non-production ＋ AC `PASS` 可替代；**production 仍须用户签**）。
> 本批由 `verify/verify_acceptance_record.py` 判定为 **production**（11 文件全部命中 production globs）⇒
> **需要你签本清单**；配套 AC 记录：
> [`acceptance-records/AC-2026-11-17-acceptance-workflow.MD`](acceptance-records/AC-2026-11-17-acceptance-workflow.MD)。

- **验收范围**：`da7f8d09663d5ef0186086c0f747c0bc1bf3bb13..f17267722d1d74d30d34f183d59813e17ebe50c1`
  （同步 #8 的 windows 源 → 当前 HEAD；HEAD 完整 sha 见上行，日期 2026-11-17 UTC+8）

## 1. 本次同步面（结构）

| 判据 | 命令 | 期望 |
|---|---|---|
| 非-iteration 增量 | `git diff --name-status da7f8d0..HEAD -- . ':!docs/iteration'` | **11 文件**（见 §2） |
| `docs/iteration/**` | 同步树内计数 | 0（按设计排除） |
| 4 个 mac 启动脚本 | `git ls-tree -r --name-only origin/main -- scripts/{setup-env,start-backend,start-frontend,start-streamlit}.sh` | 4 条（保留项不变） |
| 同步提交形态 | 构建后 | 单亲（父＝当前 main 顶端），`origin/main..HEAD = 1` |

## 2. 内容（本批带上 main 的东西）

| 文件 | 变化 | 走查要点 |
|---|---|---|
| `agents/functions/acceptance-review.md` | **新增** spec v1.0.0 | 五段式；硬边界：**不改文件、不建 PR、不代替用户签、不给自己 PASS**；`# Steps` 要求逐项实测读数 |
| `agents/policy.json` | **新增 `acceptance_review` 数据块** | 两类 globs（production 优先、未匹配默认 production）、`categories`（含 `added_only_globs`：新增脚本才算 non-production）、`record_dir`、`verdicts` 三态、`walkthrough_glob`、`ignored_deletions`（仅 4 个 mac 保留项）＋"可调整"注释 |
| `verify/verify_acceptance_record.py` | **新增闸门** 519 行 | 五条判据（分类／记录匹配 range／逐项实测读数／verdict 一致性／fail-closed）＋**32 断言自检**＋`-O` 守卫；只读、不写仓库 |
| `docs/1-WORKFLOW.MD` | §3 追加**例外** | non-production＋AC PASS ⇒ 可建 PR；**production（含阶段/Sprint 记录）仍须签**；§6.0 机制索引已同步（M12 行） |
| `docs/6-DECISIONS.md` | **＋`D-251117-02`** | 用户 2026-11-17 裁决原文（会话出处）；插入后自指指针按内容重定位 |
| `docs/3-LEARNED.MD` | **＋1.74** | "第三方依赖是否可用是环境事实，不是判据结果"（今天 main CI 红的教训） |
| `verify/run_suite.py` | 接线 | 新闸门进套件（`--selftest` 档）＋断言下限 32；agentops 下限 244 |
| `verify/TEST-MATRIX.MD` / `verify/README.md` / `verify/agent_policy.py` / `agents/README.md` | 索引与装载 | 矩阵 64 脚本一致；policy 装载器暴露新块；spec 索引一行 |

## 3. 闸门（本地，`.venv` 实测；读数同 AC 记录）

| 判据 | 实测 |
|---|---|
| 套件 | `SUITE PASSED (30 scripts)` |
| `verify_lint` | rc=0；`E501=2492/2493` |
| `verify_decision_register` | rc=0；`entries=126 pointers=1248 quotes_drift=10` |
| `verify_acceptance_record --selftest` | rc=0；**32 断言**（含 6 组对照＋作用域对照＋非规范 root 对照） |
| `validate-spec acceptance-review` | `PASS`（v1.0.0） |
| `verify_matrix check` | `CHECK OK: 64` |
| `verify_gate_integrity` | `88 断言 guard_required=11` |
| `verify_no_policy_hardcode` | `22 断言 scanned=86` |
| `verify_md_tables` | `PASS（206 文件）` |
| `verify_derived_numbers` | `19 断言` |
| `verify_card_index` | `17 断言` |

## 4. 你这次真正在批什么（请重点看这三点）

1. **规则被放宽了一格**：原来"走查通过前不得建 PR"是绝对约束；现在 **non-production delta** 可由 `acceptance-review` 的 AC `PASS` 记录替代。**production 面不减**（反而新增了"阶段/Sprint 记录属 production"）。
2. **谁来判断分类**：`agents/policy.json::acceptance_review` 是唯一真源；闸门不硬编码路径。**改类别/范围只改数据**（你要求的"后续可调整"）。
3. **反形式主义**：AC 记录的每个 checklist 项必须有**实测读数**（"我检查过了"会被判 FAIL）；production 记录必须 `NEEDS-HUMAN` 并引用**你的签收档**；缺依赖只能记"未验证"，不得写成 FAIL。

## 5. 明确"未证明"的项

- **non-production 自动放行尚未被真实使用过一次**（此前所有批次都触到 production）——它目前的证据是自检夹具，不是实战样本；
- CI 侧只跑该闸门的 `--selftest`（默认模式需要 AC 记录，CI 全新 checkout 没有），这是设计取舍；
- `docs/iteration/**` 里的阶段记录按 production 计 ⇒ 只要它们被编辑，批次就不能全自动验收（这是你定的边界，不是缺陷）。

## 6. 红旗（任一命中即不通过）

- 同步树出现 `docs/iteration/` 文件；
- 4 个 mac 启动脚本在 main 上减少；
- AC 记录里任何 checklist 项只有声明没有实测读数；
- production delta 的记录 verdict 不是 `NEEDS-HUMAN` 或未引用签收档；
- 手抄派生数字进文档（`verify_derived_numbers` 会抓）。

## 7. 签收

| 项 | 填 |
|---|---|
| 走查日期（网络时间 UTC+8） | |
| 结论 | ☐ 通过　☐ 不通过 |
| 哪几项不过（写编号） | |
| 想让我先修哪个 | |
