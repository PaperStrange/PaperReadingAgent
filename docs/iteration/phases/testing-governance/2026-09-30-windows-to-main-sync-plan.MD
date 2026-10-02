# windows → main 同步方案（可评审；本文件不执行任何同步动作）

- **文档类型**：方案（plan）——**不是执行结果**，不含任何已落地的同步动作。
- **时点锚**：全部读数为 `2026-10-02T21:32:40+09:00` 现跑（探针窗口 `21:0x`–`21:3x`）。
- **源树（被同步方）**：`windows` = `6663e6815cbcd131904c4f55d9ecf7f1901e39d9`。
- **目标树（接收方）**：`origin/main` = `bc3121992a723f57abc5a3cd4b53090b97cbcafb`（本地 `main` 已与之一致，`git rev-list --left-right --count main...origin/main` = `0  0`）。
- **合并基**：`80c01d7cf55b8276a91dcdb51ba0ea33b5a949a9`。
- **run**：`run-2026-10-02-impact-assessment-119`（spec `agents/functions/impact-assessment.md`）。
- **本文件只读取证**：所有 git 查询为只读命令；`merge-tree` 用 `--write-tree` **只读输出**，未写入任何索引；镜像探针一律落在 `%TEMP%`，仓库根未留未跟踪文件。
- **范围声明**：本文件**只**给方案、逐条冲突处置表与决策点。**未**建分支、**未**提交、**未**推送、**未**建 PR、**未**改远程引用、**未**动 `git config`。

> **日期口径更正（声明）**：派单方给的 run 日期是 `2026-09-30`，但本机现跑时间为 **2026-10-02**（`Get-Date` = `2026-10-02 21:29:56 +09:00`；`windows` HEAD 的 `%cI` = `2026-10-02T21:03:52+09:00`）。按 `docs/1-WORKFLOW.MD` §6「日期必须每轮核验……不得沿用会话起始日期」（2026-09-23 事故后补规），run_id 采用**实际日期** `run-2026-10-02-impact-assessment-119`（编号接现最大 118）。**此偏离需用户知悉**（见决策点 D8）。

## 0. 一句话结论

同步面共 **47 个文件**（37 改 + 10 增；**不含** `docs/iteration/**` 的 178 个路径、**不含** 4 个 mac 启动脚本的删除）。47 个里有 **25 个是真实冲突**，逐条比对后 **25/25 取 windows 侧**（main 侧一律是旧版或同步分支手工重建的陈旧快照，无一处是 main 独有工作）。但**「取 windows 侧」不等于「合完就绿」**：在 main 侧实测出**三条 CI 必红路径**，其中两条是**本次新发现**（105 报告未列），必须由用户裁定修法后才能落 main。

## 1. 证据基础与复核口径

### 1.1 本方案的两条独立证据链

| 证据链 | 内容 | 性质 |
|---|---|---|
| ① 既有复核报告 | `agents/runs/run-2026-09-29-code-review-105/code-review.report.md`（target=branch:main） | 两日前读数，**本方案逐项复核后部分已被 windows 后续提交修复** |
| ② 本方案现跑 | 25 处冲突逐条比对 + 两个后同步镜像的闸门实跑（`%TEMP%`） | 现跑，带命令与读数 |

**105 报告的失效项（本方案更正）**：105 报告的两条 critical（`verify_decision_register.py` 在 main 上超时 143s；`verify_agentops.py`/`verify_close_readiness.py` 因读 `docs/iteration/**` 的 sprint-id spec 而崩）**均已由 windows 侧 `25c8a8c`／`62393c6`／后续批次修掉**（见 §4.2 实测）。**照抄 105 报告会得出错误结论**，故本方案一律以现跑为准。

### 1.2 复核用命令（只读）

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
git rev-parse windows origin/main main
git merge-base origin/main windows
git rev-list --count origin/main..windows
git rev-list --count windows..origin/main
git merge-base --is-ancestor origin/main windows; $LASTEXITCODE
git diff --shortstat origin/main...windows
git diff --name-status origin/main..windows
git merge-tree --write-tree --name-only origin/main windows
git ls-remote --heads origin
```

### 1.3 现状读数（现跑，时点锚 `2026-10-02T21:32:40+09:00`）

| 读数 | 值 |
|---|---|
| `windows` | `6663e6815cbcd131904c4f55d9ecf7f1901e39d9` |
| `origin/main` | `bc3121992a723f57abc5a3cd4b53090b97cbcafb` |
| `main`（本地） | `bc3121992a723f57abc5a3cd4b53090b97cbcafb` |
| `git merge-base origin/main windows` | `80c01d7cf55b8276a91dcdb51ba0ea33b5a949a9` |
| `git rev-list --count origin/main..windows`（ahead） | `222` |
| `git rev-list --count windows..origin/main`（behind） | `120` |
| `git merge-base --is-ancestor origin/main windows` | 退出码 `1` ⇒ **不是快进，main 不是 windows 的祖先** |
| `git diff --shortstat origin/main...windows` | `232 files changed, 37647 insertions(+), 562 deletions(-)` |
| `git diff --shortstat origin/main..windows` | `229 files changed, 27504 insertions(+), 529 deletions(-)` |
| `git status --porcelain -uall`（开工） | 空 |

> `...`（三点，对合并基）与 `..`（两点，对 main 树）差 3 个文件，成因是 main 有 windows 没有的文件（如 `docs/6-DECISIONS.md` 的反向、以及 mac 脚本侧的分叉），故 `--name-status` 用两点（它才是「树到树」的同步面）。

## 2. 历史同步机制取证（本方案的核心）

### 2.1 三个提交的父提交数（现跑）

| 提交 | `git rev-list --parents -n 1` 父数 | 判定 | 作者/日期 |
|---|---|---|---|
| `f0205e0db15fd7d46ef3f53c2c1378e2413adb8b` | **1**（父 = `8e9b5eebc1d7bd34aa551d3937d75af831b982b4`） | **单亲＝同步提交**（非 merge） | PaperStrange / 2026-09-25 16:54:27 +0900 |
| `c8578b03c6fb504abe3bb5cc78cf15970faf87ef` | **1**（父 = `f0205e0`） | **单亲＝同步提交**（非 merge） | PaperStrange / 2026-09-25 17:17:19 +0900 |
| `bc3121992a723f57abc5a3cd4b53090b97cbcafb` | **2**（父 = `8e9b5ee` + `c8578b0`） | **真 merge**（GitHub 生成，`git log --merges` 命中） | NemoHuang / 2026-09-25 17:59:10 +0900 |

**结论**：`windows → main` **不是** `git merge windows`。做法的真实形态是：**在一个（临时）分支上手工构造单亲同步提交，再以 PR 合入 main 形成双亲 merge 提交**。

### 2.2 是否 =「windows 全树 − `docs/iteration/**` + 分支感知改写」

| 提交 | 与父的 `git diff --name-only` 含 `docs/iteration/**`？ | 该提交的树里有 `docs/iteration/**` 吗 |
|---|---|---|
| `f0205e0` vs `8e9b5ee` | **ABSENT（0 个路径）**；改动文件数 `63` | 树里 0 条（`git ls-tree -r f0205e0` 计数 = `0`） |
| `c8578b0` vs `f0205e0` | **ABSENT（0 个路径）**；4 个文件（`agents/policy.json`、`scripts/structure-guard.py`、`verify/verify_card_index.py`、`verify/verify_derived_numbers.py`） | 树里 0 条 |
| `bc31219`（merge 结果） | — | 树里 0 条 |
| `windows`（当前） | — | 树里 **178** 条 |

**结论**：取证与「windows 全树 − `docs/iteration/**` + 分支感知改写」**一致**。三条独立证据：① 两个同步提交都不含 `docs/iteration/**` 的改动；② 两者的树里该目录条目数为 0；③ `c8578b0` 的提交信息逐字写着「带上分支感知修复（`verify_card_index`/`verify_derived_numbers` 在无 `docs/iteration` 时显式 SKIP）」——**「分支感知改写」在历史上是同步配方的一部分**，不是同步后的补丁。

### 2.3 mac 启动脚本的删除抵挡（现跑）

| 树 | `scripts/{setup-env,start-backend,start-frontend,start-streamlit}.sh` 在位 |
|---|---|
| `origin/main` | **4/4** |
| `windows` | **0/4**（四个都是 `D`） |
| `f0205e0` | **4/4**（删除被挡住） |
| `c8578b0` | **4/4**（删除被挡住） |

`git diff --name-status origin/main..windows` 里这 4 条的状态是 `D` ⇒ **按字面 `git merge windows` 会删掉 mac 侧启动器**；历史同步提交明确把它们保住。本方案延续该排除（见 §3）。

### 2.4 同步分支先例（spec 必查项）

`git log --merges --oneline --all` 命中 **30+ 条** `Merge pull request #NN from PaperStrange/sync/...`（`sync/sprint-9-dashboard`、`sync/acceptance-fixes`、`sync/branch-protection`、`sync/research-agent`、`sync/sprint-10`…`sync/sprint-16`、`sync/sprint-16-close-docs`、`sync/dashscope-e2e`、`sync/domain-governance`、`sync/git-hygiene`、`sync/ci`、`sync/pr-helper-fix`、`sync/lessons-fanout`、`sync/multi-provider`、`sync/impact-v11`、`sync/user-two-issues`、`sync/agents-move` 等）。

**结论**：**sync 分支先例充分且是主流做法**（PR #22 起一路到 #52）。

### 2.5 远程分支卫生与一个易误读的点

- `git ls-remote --heads origin` = `refs/heads/mac`（`50cbab1fffe27b2e3f8af5816688fb3471b0845e`）、`refs/heads/main`（`bc3121992a723f57abc5a3cd4b53090b97cbcafb`）、`refs/heads/windows`（`6663e6815cbcd131904c4f55d9ecf7f1901e39d9`）——**仅此三条，无遗留 `sync/*` 头分支** ⇒ 卫生合格（合并后即删头分支，与 §2.4 的 PR 记录并存）。
- **易误读点**：`sync/*` 分支**在远端已不存在**，但**历史先例存在**。两者不矛盾：「用过 sync 分支」由 merge 提交取证，「当前无遗留 sync 头」由 `ls-remote` 取证。**不要把「远端只有三条分支」误读成「没用过同步分支」**。

### 2.6 一个关键的拓扑事实（决定方案必须显式构造树）

`git merge-base --is-ancestor c8578b0 windows` ⇒ **退出码 1**，即 **`c8578b0` 不是 `windows` 的祖先**（它在 `origin/main` 上是祖先，退出码 0）。

**含义**：历史同步提交住在 main 侧的一条**独立短支**上（`8e9b5ee → f0205e0 → c8578b0`），随后被 merge 进 main，但**从未回灌 windows**。因此 main 与 windows 不存在「同步提交」这个共同点，**每次同步都要重新处理同一批文件**——这正是本轮 25 处冲突的成因，也是 §4 表里 main 侧文件普遍「陈旧」的根因。

## 3. 同步面（本次要带过去的到底有哪些）

`git diff --name-status origin/main..windows` = **229** 条；按既定排除口径（§2.2/§2.3）切分：

| 分类 | 条数 | 处置 |
|---|---|---|
| `docs/iteration/**` | **178** | **排除**（windows-only，main 按设计没有这棵树） |
| 4 个 mac 启动脚本（`D`） | **4** | **挡住删除**（有意分叉保留） |
| **其余（＝同步面）** | **47** | 37 改（`M`）+ 10 增（`A`）；**无 `D`、无 `R`** |
| **合计** | **229** | — |

**47 个同步面的内部结构**：

| 子类 | 条数 | 说明 |
|---|---|---|
| 真实冲突（`git merge-tree` 报冲突） | **25** | 见 §5 逐条处置表 |
| 干净合并（只有 windows 一侧动过） | **22** | 见 §5.3 |

> **新增的 10 个文件**（`A`）是本次同步的实质增量：`agents/functions/implementation.md`、`agents/obligations.json`、`agents/spend-budget.json`、`docs/6-DECISIONS.md`、`scripts/hooks/commit-msg`、`scripts/hooks/pre-commit`、`scripts/install-hooks.py`、`scripts/spend-report.py`、`verify/verify_close_tax_reading.py`、`verify/verify_decision_register.py`。
> 其中 **`docs/6-DECISIONS.md` 是决策点 D1**（`1-WORKFLOW.MD` 现行排除项③），其余 9 个按 §5.3 全带。

## 4. 主侧 CI 现跑实证（本方案的判据来源）

### 4.1 探针方法（可复现；全部在 `%TEMP%`）

1. `git archive -o %TEMP%\pr119-main.tar --format=tar origin/main` → 解开成「main 树」。
2. `git archive -o %TEMP%\pr119-sync47.tar --format=tar windows -- <47 个路径>` → 覆盖上去 ⇒ **「后同步 main 镜像」**（无 `docs/iteration/**`）。
3. 在该目录 `git init` + 单提交，使 `HEAD` 指向该树——因为仓内闸门用 `git ls-tree HEAD -- <path>` 判分支（`verify/agent_policy.py::path_in_head` 默认 `rev="HEAD"`），**没有真 git 仓库就无法触发分支感知**。
4. 用仓库自己的 `.venv` 跑闸门（`%TEMP%` 里的 venv 解析不到 site-packages，须显式 `PYTHONPATH` 或把树放在 venv 的相对路径下）。

### 4.2 两个场景的闸门与套件实测

下表为 `2026-10-02` 时点读数（历史读数，**断言数／闸门计数一律以各命令现跑末行为准，不在此固化**）。

| 闸门/套件 | 场景 A（**带** `docs/6-DECISIONS.md`） | 场景 B（**不带**，＝`1-WORKFLOW` 现行排除③） |
|---|---|---|
| `verify/verify_decision_register.py` | `2026-10-02`：rc=`0`，末行为 `EVIDENCE:` 证据行（`quotes_drift=0`、`pointers` 与 `entries` 见现跑末行），**5.03s** | `2026-10-02`：rc=`0`，末行 `DECISION-REGISTER SKIP（本分支没有 docs/6-DECISIONS.md…不是通过）`，**0.16s** |
| `verify/verify_gate_integrity.py` | `2026-10-02`：rc=`0`，`guard_required=10 ratchets=5`，2.94s | `2026-10-02`：rc=`0`，同读数，2.97s |
| `verify/verify_close_tax_reading.py` | `2026-10-02`：rc=`0`，末行为证据行 `mode=selfcheck`，0.10s | 同 |
| `verify/verify_card_index.py` | `2026-10-02`：rc=`0`，末行为自检判决行（条数以现跑末行为准），0.13s | rc=`0`，同 |
| `verify/verify_md_tables.py` | `2026-10-02`：rc=`0`（`docs/iteration` 条件根缺席 ⇒ 具名 SKIP，**不打印 PASS**） | 同 |
| `verify/verify_no_policy_hardcode.py` | `2026-10-02`：rc=`0`，`scanned` 计数见现跑证据行 | 同 |
| **`verify/run_suite.py --tier offline`** | `2026-10-02`：rc=`1`，**163.2s**，`SUITE FAILED (2/26, 1 skipped)` ⇒ 失败项 `verify_agentops.py`、`verify_usage.py` | `2026-10-02`：rc=`1`，**216.0s**，`SUITE FAILED (2/26, 2 skipped)` ⇒ 失败项 **`verify_decision_register.py（行34）`**、`verify_usage.py` |

**对照（真 windows 树，同一台机、同一 venv，`2026-10-02` 时点）**：`verify_decision_register.py` rc=`0`、2.38s；`verify_agentops.py` rc=`0`（断言数以现跑末行为准）；`verify_gate_integrity.py` rc=`0`；`verify_lint.py` rc=`0`。

### 4.3 三条「main 侧必红」路径（前两条是本方案新发现）

**CI-B1（新发现，硬阻断）`verify/verify_usage.py:65,120` 钉死了一个 main 历史上不存在的 revision。**
该脚本用 `BEFORE_REV = "1ed6f937396eb81e7fc6a9e40d87fbdd139fa926"` 做「改前/改后」对照，`_load_before()` 在 `main()` 里**无条件**调用（`:338`），内部 `git -C ROOT show 1ed6f93…:paper-qa-script/app/usage.py` 失败即 `assert returncode == 0` ⇒ `AssertionError: git show 失败：fatal: …` ⇒ rc=`1`。
**现跑取证**：`git merge-base --is-ancestor 1ed6f93… origin/main` 退出码 **`1`**（不是祖先）；`git branch -a --contains 1ed6f93…` 只列 `windows` / `remotes/origin/windows`；`git rev-list origin/main..windows` 里**有**这条 sha ⇒ 它**只存在于 windows 谱系**。CI 是 `fetch-depth: 0`（`ci.yml:29`）全量历史，所以这不是浅克隆问题——**该 revision 在 main 上永远解析不出**。
**扫描面**：本方案扫过全部 47 个同步 `.py` 里的 sha 字面量，命中 15 处「windows-only revision」，**只有这一处是运行期真调用**，其余 14 处全在注释／断言夹具字符串里（无害）。

**CI-B2（新发现，硬阻断）`verify/verify_decision_register.py` 在 main 上「退 0 ＋ 具名 SKIP 横幅」⇒ 套件行 34 判红。**
场景 B 实测该脚本 rc=`0`、末行是 `DECISION-REGISTER SKIP（…不是通过）`。而 `verify/run_suite.py:595-617` 对**自陈『条数见末行』**的脚本（该脚本在自陈的 5 个之列）执行 `verdict_problems()`：自陈却以具名 SKIP 横幅收尾**且退 0** ⇒ 记 `VERDICT-FAIL`、`failed.append(f"{name}（行34）")` ⇒ 套件 `SUITE FAILED`、rc=`1`。
**这条与 CI-B1 不同**：它**只在场景 B 出现**；场景 A 下该脚本走真数据路径、打印证据行、行 34 正常通过。这与 `run_suite.py` 自己的注释口径一致（「`verify_agentops.py` 的 spec 缺席档已由 rc=0 收紧为 rc=3」）——**同一族形态在登记册这条上还没收紧**。

**CI-B3（105 报告已列，仍未闭环）`docs/1-WORKFLOW.MD` 的「PR 前不得建 PR」用户令。**
该文档逐字写着「**用户明确（2026-09-12）：用户走查验收通过之前不得创建 PR**」。这直接约束机制选择（见 §6）与决策点 D3。

### 4.4 已被 windows 后续提交修掉、**不再构成阻断**的 105 报告项

| 105 报告项 | 现状（现跑） | 依据 |
|---|---|---|
| critical 1：`verify_decision_register.py` 在 main 上 143s > 80s 超时上限 | **已修**。`verify/run_suite.py:71-75` 加了 `PROBE_KEY="docs/iteration"` + `BRANCH_EST_OVERRIDES{("verify_decision_register.py", False): 200.0}`，`:408` 改为 `timeout_s = int(effective_est_seconds(...)*4+60)` ⇒ absent 侧上限 860s。实测该脚本在 main 镜像上 **0.16s**（SKIP 短路）／**5.03s**（真数据） | `verify/run_suite.py` 现跑；§4.2 |
| critical 2：`verify_agentops.py:110` 在 main 上 `FileNotFoundError` 崩 | **已修**。absent 侧现走具名 SKIP 档（`AGENTOPS SKIP[spec-absent-on-branch]`，rc=3），不再崩 | §4.2 场景 B 的 skipped 档 |
| critical 2 同族：`verify_close_readiness.py:267` 的 E1 向量表读取侧 | **已修**（`2026-10-02` 时点）。absent 侧现为 `CLOSE-READINESS SKIP[spec-absent-on-branch]`（rc=3，其余判据已验，条数见现跑横幅） | §4.2 |
| `verify_gate_integrity.py` 因缺 `verify/verify_decision_register.py` 而 fail-closed | **已消**。把两个 windows-only 文件一并同步后，该闸门在 main 镜像上 `2026-10-02` rc=`0`（计数见现跑证据行） | §4.2 |
| major 8：`est_seconds` 分支无关常量 | **已修**（同上 `BRANCH_EST_OVERRIDES`） | §4.2 |

> **尚不能在本机测准的两项（据实声明）**：`verify_agentops.py` 的 E9 档位一致性断言在 `%TEMP%` 镜像里报 `声明=['deepseek-flash','deepseek-v4-pro'] vs 真实=['deepseek-v4-flash','deepseek-v4-flash-vision-exp','deepseek-v4-pro']`——这是**本机 `agents/runtime/` 运行态**造成的，真 windows 树上同脚本 `2026-10-02` rc=`0`（断言数以现跑末行为准）；`verify_lint.py` 在 `%TEMP%` 里报 `LINT-ERROR: 未找到 ruff`（路径解析），真 windows 树上 rc=`0`。⇒ **这两项必须在真 CI 上终判**，本方案不用它们下结论。

## 5. 逐条冲突处置表（25 处；用户走查核心）

### 5.1 判定口径（先说清「为什么 25/25 都取 windows」）

逐文件用 `git diff --numstat "windows:<p>" "origin/main:<p>"` 量「main 独有行数」与「windows 独有行数」，并抽取 **main 独有行的实文** 逐条读。读数（唯一例外只有 2 个文件 `main-only=0`）：

| 形态 | 文件数 | 含义 |
|---|---|---|
| main 独有行 = 0（严格超集） | 2 | 直接取 windows，无需论证 |
| main 独有行 > 0，但**全部是「旧版原文／已被 windows 就地改写」或「windows 侧显式删除的陈旧内容」** | 23 | 取 windows＝**拿新版**；main 侧无一处是「main 独有的新工作」 |

**关键实文证据（main 独有行确实是旧版，而非 main 的独占成果）**：

- `docs/1-WORKFLOW.MD`：main 写「排除项**两条**」，windows 写「排除项**三条**」（多了排除③ `docs/6-DECISIONS.md`）；main 无 D4「不可跳过层」14 行，windows 有。⇒ windows **更新**。
- `docs/3-LEARNED.MD`：main 缺 `MM-4` 义务提示块、缺 `1.67`–`1.72` 索引项；windows 有。⇒ windows **更新**。
- `agents/functions/doc-audit.md`：main `version: "1.3.2"`、`focus` 9 项；windows `version: "1.4.0"`、`focus` 10 项（含 `rule-conformance`）。⇒ windows **更新**。
- `agents/functions/lessons-learned.md`：main `version: "1.1.2"`/`coverage_window: self`；windows `1.1.3`/`none`。⇒ windows **更新**。
- `verify/README.md`：main 写死「`gui_check_s15_*.mjs`（10 个）」「16 个配置键字面量」「77 字段路径」；windows 已按 §6「派生数字不得手抄」改成「以现跑为准／不写死」，并补登 `verify_md_tables/verify_card_index/verify_gate_integrity/verify_derived_numbers/verify_close_tax_reading/verify_decision_register` 六行。⇒ 取 main 会**重新引入违规的写死读数**。
- `verify/verify_card_index.py`：main 的 `FIXTURE_DIR = Path(tempfile.gettempdir()) / "verify_card_index_fixture"`（固定名）；windows 是 `Path(tempfile.mkdtemp(prefix="verify_card_index_fixture-"))` + `atexit` 回收（提交 `31ceb6e`「run-unique mkdtemp fixtures…fixed %TEMP% names caused real concurrent collisions」）。⇒ 取 main＝**回退掉并发碰撞修复**。
- `agents/policy.json`：main 缺 `structure_ack_min_reason_chars`（`structure-guard.py` 的署名理由阈值，`verify/agent_policy.py` 有对应 property）；main 的 `report_round_pattern` 是旧式；main 的 `dynamic_ratchet` 仍是 `measured_total=105`（windows 已按实测重评）。⇒ 取 main＝**回退棘轮口径**。
- `verify/verify_derived_numbers.py`：main 用「父目录是否存在」推断分支差异（旧实现），windows 已改为按 git 树直接证据判定，并多出反向对照（windows `:298` 明写「旧实现按父目录推断，会把它当分支差异放行」）。⇒ windows **是 main 的演进超集**（与 105 报告 §Sync 判断一致）。

**因此：25 条处置一律「取 windows 侧」。** 每条下面的「判定」列给出**可复制的机器判据**；只有 3 处需要人判（已标出）。

### 5.2 冲突处置表（25 处）

| # | 路径 | 冲突形态 | 取哪边 | 怎么改 | 为什么 | 判定命令（自动）／人判 |
|---|---|---|---|---|---|---|
| 1 | `.github/workflows/ci.yml` | 改/改 | **windows** | 整file 取 windows 版（171→410 行） | windows 侧含三道新门（套件第三态放行 `CI-SKIP-GATE`、close-readiness 第三态放行 `CI-CLOSE-SKIP-GATE`、显式闸门档位），main 侧全无；main 的 `Test-Path 'docs/iteration/sprint'` 守卫在 windows 侧**仍在**（行号由 `:86` 变 `:220`） | `git diff "windows:.github/workflows/ci.yml" "origin/main:.github/workflows/ci.yml" \| Select-String '^\+'` ⇒ 全为 windows 侧已含的**旧文**；人判：**否** |
| 2 | `agents/functions/doc-audit.md` | 改/改 | **windows** | 整file（65→76 行） | windows `1.4.0` 含 `rule-conformance`（第 10 维）；main `1.3.2` 无 | `git show windows:agents/functions/doc-audit.md \| Select-String '^version\|rule-conformance'`；人判：否 |
| 3 | `agents/functions/lessons-learned.md` | 改/改 | **windows** | 整file（57→57 行） | windows `1.1.3`/`coverage_window: none`；main `1.1.2`/`self` | `git show windows:agents/functions/lessons-learned.md \| Select-String '^version\|^coverage_window'`；人判：否 |
| 4 | `agents/policy.json` | **add/add** | **windows** | 整file（386→506 行） | main 是同步分支手工重建的快照，缺 `structure_ack_min_reason_chars`、`dynamic_ratchet.measured_total` 旧（105 vs 新）、`report_round_pattern` 旧式；windows 为现行政策 SSOT | `git show windows:agents/policy.json \| Select-String 'structure_ack_min_reason_chars'`（windows 有、main 无）；人判：否 |
| 5 | `agents/runtime/tg14-baseline.json` | **add/add** | **windows** | 整file（723→779 行） | windows 含 main 缺失的卡条目（`A-PTR`/`A-REG`/`A-COST` 等）；该文件是**受 `!` 白名单追踪**的基线（`.gitignore:40`） | `git diff "windows:agents/runtime/tg14-baseline.json" "origin/main:agents/runtime/tg14-baseline.json" \| Select-String '^\-.*card'`；人判：否 |
| 6 | `docs/1-WORKFLOW.MD` | 改/改 | **windows** | 整file（337→380 行） | windows 含排除项③（`docs/6-DECISIONS.md` 不进 main）与 D4「不可跳过层」三层执行 | `git show windows:docs/1-WORKFLOW.MD \| Select-String '排除项三条'`；人判：否 |
| 7 | `docs/3-LEARNED.MD` | 改/改 | **windows** | 整file（351→390 行） | 现最大教训号 **1.72**；main 只到 1.66。取 main＝丢 6 条教训 | `git show windows:docs/3-LEARNED.MD \| Select-String '1\.72'`；人判：否 |
| 8 | `requirements-windows.txt` | 改/改 | **windows** | 整file（29→34 行） | **main 独有行 = 0**（严格超集）；windows 补 `zstandard==0.25.0`（`scripts/spend-report.py` 的运行依赖，105 报告 minor 已点出两份清单都缺） | `git diff --numstat "windows:requirements-windows.txt" "origin/main:requirements-windows.txt"` ⇒ `0  6`；人判：否 |
| 9 | `scripts/agent-ops.py` | 改/改 | **windows** | 整file（1318→2123 行） | windows 是现行 CLI（`register/finish/round/list/close-sync` + `TG-15` 锚点 + `spend-report` 联动）；main 侧缺 953 行 | `git show windows:scripts/agent-ops.py \| Select-String 'covers_through\|coverage_anchor'`；人判：否 |
| 10 | `scripts/fetch-prices.py` | 改/改 | **windows** | 整file（236→480 行） | windows 含 `prices-derive` 干跑默认、UC-26 永久判据 | `git show windows:scripts/fetch-prices.py \| Select-String 'prices-derive'`；人判：否 |
| 11 | `scripts/structure-guard.py` | **add/add** | **windows** | 整file（1398→1855 行） | windows 含 D4 三层执行（`--from-git`/钩子/CI）+「不可跳过层」接线判据；main 侧为旧版 | `git show windows:scripts/structure-guard.py \| Select-String 'Structure-Removal'`；人判：否 |
| 12 | `verify/README.md` | 改/改 | **windows** | 整file（103→144 行） | windows 已按「派生数字不得手抄」去掉写死读数（main 写死「10 个」「16 个」「77 字段」）；并补登 6 行闸门 | `git diff "windows:verify/README.md" "origin/main:verify/README.md" \| Select-String '^\+.*(10 个\|16 个配置键\|77 字段)'` ⇒ 命中的是 main 侧旧写死读数；人判：否 |
| 13 | `verify/TEST-MATRIX.MD` | 改/改 | **windows** | 整file（61→63 行） | 矩阵是各脚本 `VERIFY_META` 的派生 SSOT；windows 侧含新脚本行与「共 55 个脚本」现读数 | `python verify/verify_matrix.py check`（同步后跑，应 `CHECK OK`）；人判：否 |
| 14 | `verify/agent_policy.py` | **add/add** | **windows** | 整file（1233→1301 行） | **main 独有行 = 0**；windows 含 `path_in_head` 的子树短路、`structure_ack_min_reason_chars` property 等分支感知/政策读取件 | `git diff --numstat "windows:verify/agent_policy.py" "origin/main:verify/agent_policy.py"` ⇒ `0  75`；人判：否 |
| 15 | `verify/e2e_common.py` | 改/改 | **windows** | 整file（356→410 行） | windows 含 run 级端口分配与 `PAPERQA_VERIFY_PORT` 覆盖（`14603c2` 落地） | `git show windows:verify/e2e_common.py \| Select-String 'PAPERQA_VERIFY_PORT'`；人判：否 |
| 16 | `verify/run_suite.py` | 改/改 | **windows** | 整file（292→690 行） | **本方案最关键的一个文件**：windows 含 `BRANCH_EST_OVERRIDES`（消掉 105 critical 1 的超时）、第三态 SKIP 两通道判据、行 34 判决句棘轮 | `git show windows:verify/run_suite.py \| Select-String 'BRANCH_EST_OVERRIDES\|SKIP_EXIT'`；人判：否 |
| 17 | `verify/verify_agentops.py` | 改/改 | **windows** | 整file（967→1954 行） | windows 的 spec 缺席档已是 rc=3 具名 SKIP（不再 `FileNotFoundError`）；断言下限见 `run_suite.py::BRANCH_ASSERTION_FLOORS` 与现跑末行 | 同步后 `verify/verify_agentops.py --selftest` 末行应为 `ALL PASS` 判决行，断言数以该末行为准；人判：否 |
| 18 | `verify/verify_card_index.py` | **add/add** | **windows** | 整file（655→687 行） | main 的固定 `%TEMP%` 夹具名有并发碰撞（`31ceb6e` 已修）；windows 另有 `no-iteration-docs` 具名 SKIP 路径 | `git show origin/main:verify/verify_card_index.py \| Select-String 'FIXTURE_DIR = '` ⇒ 命中固定名（旧）；人判：否 |
| 19 | `verify/verify_close_readiness.py` | **add/add** | **windows** | 整file（1372→2267 行） | windows 的 spec 缺席档是 rc=3 具名 SKIP（实测 `CLOSE-READINESS SKIP[spec-absent-on-branch]`），main 侧旧版在 main 上 E1 FAIL | 场景探针：absent 侧 rc=`3` 且末行含 `本档不是通过`；人判：否 |
| 20 | `verify/verify_derived_numbers.py` | **add/add** | **windows** | 整file（256→371 行） | windows 改为按 git 树直接证据判分支差异（含反向对照），main 侧旧版按父目录推断 | `git show windows:verify/verify_derived_numbers.py \| Select-String '旧实现按父目录推断'`；人判：否 |
| 21 | `verify/verify_gate_integrity.py` | **add/add** | **windows** | 整file（277→1676 行） | windows 含「不可跳过层」接线判据与 `-O` 探针；`2026-10-02` 实测在 main 镜像上 rc=`0` | 场景探针：absent 侧 rc=`0` `guard_required=10 ratchets=5`；人判：否 |
| 22 | `verify/verify_ledger_measurement.py` | **add/add** | **windows** | 整file（1036→1265 行） | windows 含 TG-13 账本测量化判据与 CLI 写入侧自检 | 场景探针：absent 侧 rc=`0` `ledger=absent-skip`；人判：否 |
| 23 | `verify/verify_local_dir.py` | 改/改 | **windows** | 整file（221→350 行） | windows 含 run 级端口分配（8787 占用即 fail-fast）与免密链路 | `git show windows:verify/verify_local_dir.py \| Select-String 'run 级分配'`；人判：否 |
| 24 | `verify/verify_md_tables.py` | **add/add** | **windows** | 整file（266→313 行） | windows 含 `conditional_roots` 分支感知（`docs/iteration` 缺席 ⇒ 具名 SKIP，**不打印 PASS**）与双向差集 | 场景探针：absent 侧 rc=`0` 且打印「条件根缺席…不是通过」；人判：否 |
| 25 | `verify/verify_runner.py` | 改/改 | **windows** | 整file（372→495 行） | windows 含 TG-5 分层 runner 三态预算闸门 | `git show windows:verify/verify_runner.py \| Select-String 'SKIP_EXIT'`；人判：否 |

**需人判的项（3 处，从表里单列）**：

| 人判编号 | 项 | 为什么要人判 | 建议 |
|---|---|---|---|
| H1 | 第 1 项 `ci.yml` 取 windows 后，**main 的 `docs/iteration/sprint` 守卫行号从 `:86` 变 `:220`** | 105 报告与 `1-WORKFLOW.MD` 都以 `ci.yml:86` 指代该守卫；同步后**该行号在 main 上失效**，任何按行号引用的文档/卡片需同步改 | 接受行号漂移并在同步提交信息里点名；或把守卫行号引用改为**片段锚**（治理债，建议单开卡） |
| H2 | 第 4 项 `agents/policy.json` 取 windows 后，`dynamic_ratchet` 的 `measured_total` 由 `105` 变 `107` | 该值是**棘轮基线**，改了要带 `rebased_at` + `rebased_reason`（`verify_gate_integrity.py` 会逐项比对） | 取 windows 侧（其 `rebased_reason` 已在位，实测 gate_integrity rc=0）；人只需确认同意基线随同步迁移 |
| H3 | 第 13 项 `verify/TEST-MATRIX.MD` 取 windows 后，矩阵脚本数与 `verify_matrix.py check` 一致 | 矩阵是**派生 SSOT**，与仓内脚本集合强耦合；若同步面漏带某个脚本，矩阵会红 | 同步后必跑 `python verify/verify_matrix.py check`；红则按缺失脚本补带（不要改矩阵） |

### 5.3 干净合并的 22 个文件（不需处置，列出以便走查对齐）

`README.md`、`agents/README.md`、`agents/functions/implementation.md`(A)、`agents/obligations.json`(A)、`agents/runtime/prices.json`、`agents/spend-budget.json`(A)、`docs/2-ARCHITECTURE.MD`、`docs/4-ALGORITHM.MD`、`paper-qa-script/app/usage.py`、`paper-qa-script/reactflow-paperqa-prototype/backend/main.py`、`requirements.txt`、`scripts/hooks/commit-msg`(A)、`scripts/hooks/pre-commit`(A)、`scripts/install-hooks.py`(A)、`scripts/refresh-providers.py`、`scripts/spend-report.py`(A)、`verify/verify_close_tax_reading.py`(A)、`verify/verify_decision_register.py`(A)、`verify/verify_config_schema.py`、`verify/verify_ledger_rounds.py`、`verify/verify_usage.py`，以及 `docs/6-DECISIONS.md`(A)——**最后这个不是「干净合并」，是 D1 决策点**（见 §7）。

> **注意 `paper-qa-script/app/usage.py` 与 `verify/verify_usage.py` 的关系**：前者干净合并（+438/−5 里的 app 侧），后者干净合并但**钉了 main 不存在的 revision** ⇒ **CI-B1 正落在这一对文件上**。

## 6. 机制选择（两条路径 + 推荐）

### 路径 ①：造同步分支 → PR → 合入 main（**推荐**）

与历史先例（§2.4，PR #22→#52）**一致**。

| 维度 | 评价 |
|---|---|
| **与历史先例一致性** | **完全一致**。历史上 `sync/sprint-*`、`sync/*-fixes` 等 30+ 个分支就是这条路径；`bc31219` 的 merge 父提交对（`8e9b5ee` + `c8578b0`）就是这个形态的产物 |
| **可复核性** | **最好**。`ci.yml:6-7` 的 `pull_request: branches: [main]` 触发使得**PR 上就跑完整 CI**，可在合入前看到套件/闸门/前端构建的真实结果——这正是要验的场景 A/B 差异 |
| **可回滚性** | **最好**。合入前：删分支即可（零 main 污染）。合入后：`GitHub` 的 revert PR 或 `git revert -m 1 <merge-sha>` |
| **风险** | ①**需要建分支 + 建 PR** ⇒ 与 `1-WORKFLOW.MD`「用户走查验收通过之前不得创建 PR」的**用户令冲突**（CI-B3）⇒ **决策点 D3**；②分支名若用 `sync/*` 需在合并后删除（卫生，历史已如此）；③推送一次即产生远端引用（可删） |

### 路径 ②：直接在 main 上落单亲同步提交

即「本地 checkout main → 构造同步树 → 直接 commit → push main」。

| 维度 | 评价 |
|---|---|
| **与历史先例一致性** | **部分一致**。历史**确有**「单亲同步提交」这一半（`f0205e0`、`c8578b0` 都是单亲），但历史上的单亲提交**住在同步分支上**，随后经 PR 合入；**没有**「直接推 main」的先例 |
| **可复核性** | **最差**。main 上只有 `push` 触发（`ci.yml:4-5`），一旦推送就已经落在 main；若红，main 处于红态直到修复提交。**没有 PR 前置观察窗** |
| **可回滚性** | 中等。需要 `git revert` + 再次推送；main 的历史会留下一条红态记录（无法像删分支那样「零痕迹」） |
| **风险** | ①**绕过分支保护/评审**（main 是否受保护需确认——**决策点 D5**）；②直接推 main 使「先合门、后 ✅」的口径失去一个前置观察点；③若 CI 红（**本方案预测至少 CI-B2 在场景 B 下必红**），main 立刻红，违反「main 侧 CI 必须绿」的验证要求 |

### 推荐：**路径 ①（同步分支 → PR → 合 main）**

理由三条，按权重排序：

1. **唯一能在「合入 main 之前」拿到 main 侧 CI 真结论的路径。** 本方案已predict 出 **CI-B1/CI-B2 两条必红路径**（§4.3）；路径 ② 会把这两条红直接落到 main 上，而路径 ① 能在 PR 上先看见、先修。
2. **与历史先例完全一致**（§2.4），且 `bc31219` 的父提交结构证明这条路径**产出的是双亲 merge 提交**——回滚语义清晰（`-m 1`）。
3. **回滚成本最低**：合入前删分支＝零残留；这正是历史上「远端只剩 mac/main/windows 三条」的成因（§2.5）。

**但路径 ① 必须先解 D3**（用户令禁止走查前建 PR）。**若用户裁定 D3＝「不允许建 PR」**，则退路是**路径 ② 的变体**：在**本地**构造同步提交并按 §8 的验证计划**在本地复现三道主侧判据**（本方案 §4.1 的镜像探针法即为该复现法的原型），**用户走查通过后再推送**。

## 7. 执行序列（可复制的命令序列；本方案不执行）

> **前置条件（全部步骤共用）**：① 工作区干净（`git status --porcelain -uall` 为空）；② `git fetch origin`；③ 已拿到用户对 D1–D5 的裁定；④ **不得** `git config` 任何项。

### 步骤 S0：同步前留证（dry-run，零写入）

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
git status --porcelain -uall                      # 期望：空
git fetch origin
git rev-parse origin/main windows                 # 期望：bc31219… / 6663e68…
git merge-tree --write-tree --name-only origin/main windows   # 期望：39 条冲突（14 docs/iteration + 25 代码面）
git ls-remote --heads origin                      # 期望：只有 mac/main/windows
```
**失败回退**：若冲突数 ≠ 39 或 `windows` sha 变了 ⇒ **停**，重新取证（本方案的读数以 `6663e68` 为锚）。

### 步骤 S1：造同步分支（**需 D3 通过**）

```powershell
# 分支名遵循历史先例 sync/*
git switch -c sync/sprint-18-main-landing origin/main
```
**前置**：D3 已裁定允许建分支（建分支本身不改远程）。
**失败回退**：`git switch windows` 回原分支；`git branch -D sync/sprint-18-main-landing`。

### 步骤 S2：铺同步面（＝window 全树 − `docs/iteration/**` − 4 个 mac .sh 删除）

```powershell
# 2a) 先把 47 个路径里的「增/改」按 windows 侧铺上（含 25 处冲突 → 取 windows）
git archive -o "$env:TEMP\sync47.tar" --format=tar windows -- (Get-Content "$env:TEMP\pr119-syncset.txt")
tar -x -f "$env:TEMP\sync47.tar" -C .
# 2b) 反向：确保 docs/iteration/** 从未进入本分支的索引
git status --porcelain -uall | Select-String 'docs/iteration'   # 期望：空
# 2c) 反向：4 个 mac 脚本必须保持 main 侧在位（不得出现 D）
git status --porcelain -uall | Select-String 'scripts/(setup-env|start-backend|start-frontend|start-streamlit)\.sh'
# 期望：空
```
**失败回退**：`git checkout -- .` + `git clean -fd`（**注意**：先确认无其他未跟踪产物），或直接删分支重来。
**注意**：`syncset.txt` 是探针产物（落在 `%TEMP%`）；复现时用 §3 的口径现算：`git diff --name-status origin/main..windows` 去掉 `docs/iteration/**` 与 4 个 mac `.sh`。

### 步骤 S3：解 CI-B1/CI-B2（**需 D6 裁定**；本方案不执行）

按用户裁定择一：
- **CI-B1**：(a) 把 `verify/verify_usage.py` 的 `BEFORE_REV` 改锚到 main 可达的 revision（需重新论证「改前」对照仍成立）；或 (b) 让 `_load_before()` 在 revision 不可达时记**具名 SKIP**（与 `verify_agentops.py` 的 spec-absent 档同族），而不是 `assert` 硬崩。
- **CI-B2**：**场景 A**＝把 `docs/6-DECISIONS.md` 纳入同步（**覆盖** `1-WORKFLOW.MD` 的排除项③，需 D1 裁定）；或 **场景 B**＝把 `verify/verify_decision_register.py` 的「登记册缺席」档由 `rc=0` 收紧为 `rc=3` 具名 SKIP（与 `verify_agentops.py::SKIP_EXIT` 同一真源口径）。

### 步骤 S4：本地判据复跑（dry-run 形态，零推送）

```powershell
python verify/run_suite.py --tier offline          # 判据见 §8.1
python verify/verify_matrix.py check               # 期望：CHECK OK
python verify/verify_gate_integrity.py             # 期望：rc=0（计数以现跑末行为准）
python scripts/structure-guard.py --replay         # 期望：ALL PASS (N assertions)
python verify/verify_md_tables.py                  # 期望：rc=0（docs/iteration 条件根 SKIP 上屏）
```
**失败回退**：先修再跑；**不得**用上调 timeout／放宽阈值／删断言的方式「变绿」（＝放宽判据）。

### 步骤 S5：提交 + 推送同步分支（**需 D3 通过**）

```powershell
git add -A
git commit -m "sync(sprint-18): windows -> main（排除 docs/iteration/**；挡住 4 个 mac .sh 删除）"
git push -u origin sync/sprint-18-main-landing
```
**失败回退**：`git push --delete origin sync/sprint-18-main-landing`；本地分支照旧可删。

### 步骤 S6：建 PR（**需 D3 通过**）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 create -Base main -Head sync/sprint-18-main-landing -Title "<标题>" -Body "<正文>"
```
**失败回退**：关闭 PR（不改 main）。
**注**：`1-WORKFLOW.MD` 明确**禁止**直接用 `Invoke-RestMethod` 传中文 Body（PS 5.1 会按 GBK 编码 ⇒ GitHub 乱码，`3-LEARNED.MD` 1.18）。

### 步骤 S7：PR 上 CI 绿 → 合入 → 删同步分支

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 merge -Number <N> -Method merge
git push origin --delete sync/sprint-18-main-landing
git branch -D sync/sprint-18-main-landing
```
**失败回退**：不合入；删分支；回到 §6 重新选路。

## 8. 验证计划（main 侧 CI 必须绿的具体判据）

### 8.1 判据一：`Offline verify suite`（`ci.yml` 套件步骤）

**放行条件＝两通道同时**（`ci.yml:66-105` 的 `CI-SKIP-GATE`；单一真源＝`run_suite.py::suite_verdict_line`）：

| 通道 | 判据 |
|---|---|
| 判决行通道 | 末行形如 `SUITE PASSED (<N> scripts, <M> skipped): <name>[<分类>](, …)*`（末行以 CJK 全角 `）` 收尾，**故意不用 `$` 锚**） |
| 退出码通道 | rc = **3**（`run_suite.py::SKIP_EXIT`，＝「零失败 ＋ 有 skipped」） |

**硬约束**：**绝不接受裸 rc=3**——`run_suite.py::REFUSE_EXIT` 也是 3（预算超限/非有限预估＝拒绝启动，该分支不执行任何脚本）。**裸 rc=3 仍判红**。

**第三态 SKIP 的显式披露**（必须上屏、不得读成 PASS）：本方案预测 main 侧将出现 **2 条具名 SKIP**：
- `verify_close_readiness.py[spec-absent-on-branch]`（`2026-10-02` 实测：`CLOSE-READINESS SKIP[spec-absent-on-branch]（N 条判据未执行…）——其余判据已验，**本档不是通过**`，rc=3；条数以现跑横幅为准）
- `verify_agentops.py[spec-absent-on-branch]`（场景 B 实测出现；场景 A 下该脚本转为真跑）

**必须在 PR 日志里逐条确认这两条 SKIP 的名字与分类**，以及 `run_suite` 的读数段「具名 SKIP（第三态…）」行。

### 8.2 判据二：`Close-readiness gate for sprints that claim closure (TG-11)`

**放行条件＝两通道同时**（`ci.yml:150-200` 的 `CI-CLOSE-SKIP-GATE`）：① 末行是具名 SKIP 横幅 `CLOSE-READINESS SKIP[<分类>]（N 条判据未执行：…**本档不是通过**`（形态判据两档，任一命中即可，第一档逐字、第二档编码降级）；② rc = **3**。
**main 侧路径**：`ci.yml:220` 的 `if (Test-Path 'docs/iteration/sprint')` 为假 ⇒ 走 `:297` 的 else 分支，打印 `close-readiness: no sprint docs on this branch -> step skipped (docs/iteration/ is windows-only; …)` 并 `exit 0` ⇒ **该步骤在 main 上按设计跳过**。
**裸 rc=3（无横幅）、rc=1/2/4 一律判红**。

### 8.3 判据三：`Explicit gate tiers`

五个显式闸门（`ci.yml:301-368`）在 main 侧的预期：

| 闸门 | main 侧预期 |
|---|---|
| `verify/verify_card_index.py --check --strict` | `2026-10-02`：rc=0（末行为自检判决行，条数以现跑末行为准；absent 侧少 2 条依赖 windows-only 卡文件的判据） |
| `verify/verify_md_tables.py` | rc=0（`docs/iteration` 条件根缺席 ⇒ 具名 SKIP 上屏，**不打印 PASS**） |
| `verify/verify_no_policy_hardcode.py` | `2026-10-02`：rc=0（`scanned` 计数见现跑证据行） |
| `verify/verify_lint.py` | rc=0（**必须在真 CI 判**；本机镜像因 ruff 路径解析报 `LINT-ERROR: 未找到 ruff`） |
| `verify/verify_decision_register.py` | **场景 A**：`2026-10-02` rc=0 且末行为 `EVIDENCE:` 证据行；**场景 B**：rc=0 ＋ SKIP 横幅 ⇒ **该步骤本身放行（rc=0），但套件行 34 判红（CI-B2）** |
| `scripts/structure-guard.py --replay` | rc=0（`ALL PASS (N assertions)`） |
| `scripts/structure-guard.py verify --from-git <before>` | **main 侧 push 事件**：`guardBase=${{ github.event.before }}`；首推或 `0{40}` ⇒ 回退 `HEAD~1`。**若本分支只有 1 个提交则两者都不可解析 ⇒ `ci.yml:360` 显式跳过并打印「不是通过」**（对同步 PR 而言分支通常有多个提交，正常路径是**真跑**） |

### 8.4 判据四：`docs/iteration/**` 不得进 main

```powershell
git ls-tree -r --name-only origin/main | Select-String '^docs/iteration/'   # 期望：空
```
并在 PR 的 changed files 里确认无 `docs/iteration/**`。

### 8.5 判据五：4 个 mac 启动脚本不得被删

```powershell
git ls-tree -r --name-only origin/main -- scripts/ | Select-String '\.sh$'
# 期望：setup-env.sh / start-backend.sh / start-frontend.sh / start-streamlit.sh 四个都在
```

### 8.6 判据六：结构守卫与「新文件」

同步提交会新增文件（本方案自身新增的 `docs/iteration/phases/testing-governance/2026-09-30-windows-to-main-sync-plan.MD` 也是 `??`）⇒ **`git status --porcelain -uall` 判据⑥会红，这是预期**，由父代理在提交时消除。
**结构守卫口径**：Markdown 结构编辑须 `scripts/structure-guard.py snapshot`（编辑前）→ 编辑 → `verify`（编辑后）；`verify` 只对**丢失/变形**报错，**新增**标题/表格/文件一律放行。有意删除结构须在提交信息里写 `Structure-Removal: <仓库相对路径> :: <理由≥10 字符>`（阈值 `agents/policy.json::structure_ack_min_reason_chars`）。

### 8.7 判据七：桌面级复跑（同步后必须现跑，不得只信本方案）

```powershell
python verify/verify_matrix.py check
python verify/run_suite.py --tier offline
```

## 9. 决策点清单（逐条必须用户拍板）

| 编号 | 决策点 | 本方案的建议 | 不拍板的后果 |
|---|---|---|---|
| **D1** | `docs/6-DECISIONS.md` 是否纳入本次同步？现行 `1-WORKFLOW.MD` 排除项③**明确不进 main** | **纳入（场景 A）**——实测：纳入后 `verify_decision_register.py` rc=0、`quotes_checked=9`、**`quotes_drift=0`**，且**消掉 CI-B2**；排除项③给出的「649 处指针／94 条引文无法核」与现测**不符**（现测只有 9 处引文指针）。**若维持排除，则必须同时改脚本/CI（见 D6）** | 维持排除 ⇒ main 侧套件**必红**（CI-B2） |
| **D2** | 若 D1＝纳入，是否同批**修订 `1-WORKFLOW.MD` 的排除项③**（它现在与实测相反）？ | **是**，同批改并写明「③ 已按 2026-10-02 现测翻转」 | 文档与实现相反 ⇒ 下一轮同步又会按旧条文排除 |
| **D3** | 是否**允许首次创建 PR / 建 `sync/*` 分支**？（`1-WORKFLOW.MD`：用户走查验收通过之前不得创建 PR） | **允许建同步分支并建 PR**——否则无法在合入前拿到 main 侧 CI 结论，CI-B1/B2 这类必红项会直接落到 main | 不允许 ⇒ 只能走路径②变体（本地复现后待走查通过再推），**主侧 CI 结论在推送前无法由 GitHub 给出** |
| **D4** | 是否**允许推送**（`git push` 到 `origin`）？推 `sync/*` 与推 `main` 是两件事 | 允许推 `sync/*`；**不**直推 `main` | 不允许推 ⇒ 方案只能停在本地提交 |
| **D5** | `main` 是否**受分支保护**（必须走 PR）？ | 需用户/仓库确认——这直接决定路径②是否**技术可行** | 未知 ⇒ 路径② 的可行性未定 |
| **D6** | **CI-B1 / CI-B2 的修法**（本方案不执行任何代码改动，需用户裁定由谁改、怎么改） | CI-B1：让 `verify/verify_usage.py` 的 `_load_before()` 在 revision 不可达时记**具名 SKIP**（不要 `assert` 硬崩）；CI-B2：若 D1＝排除，则把 `verify_decision_register.py` 的登记册缺席档 `rc=0`→`rc=3`（与 `verify_agentops.py::SKIP_EXIT` 同口径） | 不修 ⇒ main 侧 CI 必红（CI-B1 恒红；CI-B2 在场景 B 恒红） |
| **D7** | 冲突表里 **H1/H2/H3** 三个人判项是否接受 | H1 接受行号漂移（`ci.yml:86`→`:220`）并在提交信息点名；H2 确认 `dynamic_ratchet.measured_total` 105→107 随同步迁移；H3 同步后必跑 `verify_matrix.py check` | 不接受 ⇒ 需为 H1 另做片段锚、为 H2 重新 rebase 棘轮 |
| **D8** | 本方案 run 的**日期口径偏离**（派单给 `2026-09-30`，实际 `2026-10-02`） | 采用实际日期 `run-2026-10-02-impact-assessment-119` | 若强行回填 09-30 ⇒ 违反「日期必须每轮核验」并复现 2026-09-23 事故形态 |
| **D9** | 是否需要**同步前的「两日增量复核」**？105 报告基于两天前的树，本批 windows 已再前进（ahead 209→**222**） | 本方案已按现树复核并更正 105 的两条 critical；**建议以此为准**，不必重跑 105 | 直接采信 105 ⇒ 会去修两个**已经修好**的问题（浪费且误导） |

## 10. 本方案的边界与未决

**已做**：§1 现跑读数；§2 三个提交的父提交数／`docs/iteration` 排除／sync 分支先例取证；§3 同步面现算（47）；§4 两个后同步镜像的主侧闸门与套件实跑；§5 25 处冲突逐条比对（含 main 独有行实文）；§6 两条路径；§7 可复制命令序列；§8 七条判据；§9 九个决策点。

**未做（据实声明）**：
1. **未建分支、未提交、未推送、未建 PR、未改远程引用、未动 `git config`**——按要求，本方案只产出文档。
2. **未改任何非授权文件**：`verify/**`、`scripts/**`、`paper-qa-script/**`、`.github/**`、`docs/1-WORKFLOW.MD`、`docs/6-DECISIONS.md`、`docs/3-LEARNED.MD`、`docs/iteration/sprint/**` 一字未改。
3. **未在真 CI 上跑任何东西**——所有主侧结论来自 `%TEMP%` 镜像探针；**两条环境态闸门（`verify_agentops.py` 的 E9 档位一致性、`verify_lint.py` 的 ruff 解析）在本机镜像里结论不可用，必须在真 CI 终判**（§4.4 末注）。
4. **未实跑前端构建**（`ci.yml:370`/`:376` 的 `Build reactflow frontend`／`Build agents-dashboard`）与 online/gui 档——与 main 落地无直接关系，且属 workspace-check 主代理职责。
5. **未复核 `paper-qa-script/app/usage.py` 的计价数值正确性**（只审其与 `agent-ops` 的口径一致性）。
6. **未测 `structure-guard.py verify --from-git` 在 main push 事件下的真跑**（依赖 `github.event.before`，本地无法等价复现）。

**未决（等用户裁定）**：D1–D9 全部；其中 **D1／D3／D6 是本方案能否落地的三条硬前提**。
