# A-EXCL 排除清单复审：被排除项反复被拉回、排除时不查消费者、清单无周期复审

- `card`: A-EXCL
- 索引: [../backlog.MD](../backlog.MD)

## 状态
候选

## 规模
3

## 来源
用户 2026-10-03 原话（本会话）：「6-DECISIONS.md 纳入同步：可以。**但这一件事提醒我们，需要复查为什么之前列入不追踪的文档现在频繁被拉回来，记录 agent infra 的 backlog**」

## Sprint
—

## 正文
### 现象
本仓的「排除／不追踪」声明来自**三处**，2026-10-03 逐条枚举得 40 ＋ 3 ＋ 15 条（来源与现跑命令见下表）。其中已有 **8 条**在事后被**拉回**：要么被要求回到版本库，要么逼着闸门为它的缺席长出分支 —— 分布在 **7 个族**里，不是一次性偏差。

**为什么"拉回"是结构性的**：排除决定是按**卫生**口径下的（生成物／运行态／体积／机密）。但一条目是不是承重件，跟它"看起来像不像产物"无关 —— 判据会读它、文档会引用它、规范内容会长在它身上。一旦它承重，缺席只剩两条出路：① 把它拉回版本库（改排除条，或加 `!` 白名单）；② 给**每一个**消费者加一条缺席分支（SKIP／第三态／分支感知）。本仓两条都走过了；② 的代价随消费者数量线性增长，而且每条缺席分支自己又变成一个新的判据面。

### 证据（命令 ＋ 读数；读数一律以该命令现跑输出为准）

| 排除源 | 2026-10-03 现读条目数 | 分类结果（同批现跑） | 现跑命令 |
|---|---|---|---|
| `.gitignore`（含 2 条 `!` 白名单） | 40 | 承重 24 ／ 可弃 11 ／ 未知 5 | `(Get-Content .gitignore \| Where-Object { $_.Trim() -ne '' -and -not $_.Trim().StartsWith('#') }).Count`；逐条 `git grep -F -c -- "<模式>" -- scripts verify src paper-qa-script agents docs`（末格注：分类判据见下节，全部为现跑） |
| `docs/1-WORKFLOW.MD:52` 同步排除项 | 3 | 3 条全承重 | `git grep -n "排除项三条" -- docs/1-WORKFLOW.MD`（另见 `:160` 的 DoD 勾选项只复述了 ①②，未含 ③） |
| `agents/policy.json` 的四组排除／白名单键 | 15 | 15 条全承重 | `git grep -n "ignored_roots\|tracked_targets\|exclude_dirs\|conditional_roots" -- agents/policy.json`（5 ＋ 2 ＋ 7 ＋ 1，末格注：逐键行号以该命令现跑为准） |

**分类口径**（三选一，逐条必须能给出命令）：*承重* = 有脚本／闸门／政策键在读取或断言它（含"生产者依赖它被忽略"）；*可弃* = 现跑在上述扫描集里零命中；*未知* = 消费者测试对它不适用或判不出（须写明理由）。

**可弃 11 条**（现跑零命中）：`*.pyc`、`.pytest_cache/`、`dist/`、`venv/`、`.DS_Store`、`._*`、`__MACOSX/`、`data/parsed/*.jsonl`、`tmp.log`、`.idea/`、`.vscode/`。反证命令同上一行的逐条 `git grep -F -c`：例如 `git grep -F -c -- "data/parsed" -- scripts verify src paper-qa-script agents` 命中 0（只有 `docs/1-WORKFLOW.MD:39` 与 `docs/2-ARCHITECTURE.MD:177` 自述该路径），`git grep -F -c -- ".pytest_cache/" -- …` 同样命中 0。

**未知 5 条**：① `docs/iteration/sprint/config_schema.json` —— 写盘落点由 `paper-qa-script/app/config_schema.py` 的 `Path(sys.argv[1]).write_text(...)` 决定（现跑 `git grep -n "sys.argv\[1\]" -- paper-qa-script/app/config_schema.py` 命中），静态判不出它今天还写不写这个路径；② `**/.env`、`.env.local`、`*.pem`、`*.key` —— 消费者测试对本类**不适用**：它们拦的是机密，没有下游消费者正是目的，删不删只能由人判。

**已发生的"拉回／承重"实例（7 族 8 条）**

| 条目 | 何时 | 证据（提交 sha / 现跑命令） |
|---|---|---|
| `docs/6-DECISIONS.md`（排除项③） | 2026-10-03 用户批准纳入同步（推翻③） | 本会话用户原话；`docs/iteration/phases/testing-governance/2026-09-30-windows-to-main-sync-plan.MD:438`（D1 行：纳入后闸门 rc=0 且 `quotes_drift=0`，且**消掉 CI-B2**）与 `:165`（CI-B2：main 上登记册缺席 ⇒ 该闸门 rc=0 ＋ 具名 SKIP 横幅 ⇒ `verify/run_suite.py` 行 34 判 `VERDICT-FAIL` ⇒ 套件 rc=1）。**排除理由本身也实测不符**：③ 写「649 处指针与 94 条引文无法核」，而 `2026-10-03` 现跑 `verify/verify_decision_register.py` 得 rc=0、末行 `EVIDENCE:` 证据行（`entries` / `quotes_checked` / `quotes_drift` / `pointers` 四个读数以该命令现跑末行为准），与本分支"无法核"的描述相反 |
| `docs/iteration/**`（排除项①） | 2026-09-25 | 排除一棵树 ⇒ 闸门读数**结构性失真**：`agents/policy.json:284` 自述「实测在没有 `docs/iteration/` 的树里（main 检出）同一份政策打印『应扫 8 / 实扫 8 → PASS』——少审 156 个文件这件事在读数里不可见」，故新增 `conditional_roots`（`:285`）；同族的代价还有 `verify/run_suite.py:60` 记着的指针规模问题与登记册「行 39 棘轮」（现跑 `verify/verify_decision_register.py --selftest` 可见该棘轮的三条反向对照） |
| `agents/runtime/prices.json` | 2026-09-25（`bc76083`） | 该提交把 `agents/runtime/` 从**逐条列名**改成目录级 `agents/runtime/*`（`.gitignore:38`），**同一次提交内**用 `!agents/runtime/prices.json`（`.gitignore:39`）把它拉回。可核：`git log -p -- .gitignore` 在同一条 diff 里同时可见 `+agents/runtime/*` 与 `+!agents/runtime/prices.json`；`git ls-files agents/runtime` 现跑恰两条 |
| `agents/runtime/tg14-baseline.json` | 2026-09-24 落库（`61dd261`）→ 2026-09-25 拉回（`bc76083` / `.gitignore:40`） | 同上；消费者 = `agents/policy.json::card_index.baseline_file`（`:258`）＋ `verify/verify_card_index.py` 判据 ⑦（现跑该闸门末行为准） |
| `agents/runtime/registry.json` | 2026-08-30 排除（`43bf388`）→ 2026-09-28～30 四次改造 | **不在版本库**（现跑 `git ls-files --error-unmatch agents/runtime/registry.json` rc=1）⇒ 全新 clone 无账本 ⇒ `72946ca`（账本缺席改具名 SKIP）、`6a0cfc9`（套件第三态 rc=3）、`de8efc8`（CI 接受第三态：横幅＋rc=3＋显式非通过）、`677338f`（close-readiness 步同款门）。四个提交的日期与主题以 `git log -1 --format="%ad %s" --date=short <sha>` 现跑为准 |
| `verify_checkpoint_run.log`、`ci_fail_log.txt` | 入库 `2575b74` / `511baab` → 清出 `f6dda51` / `7aeb52a` | 排除规则 `.gitignore:53` 是 `verify/*.log`：只覆盖 `verify/` 下、且只覆盖 `*.log` 形状。这两个真产物坐在**仓库根**，其中一个名字是 `.txt` ⇒ 规则**命中不了**。现跑 `git check-ignore --no-index -v -- ci_fail_log.txt` 仍 rc=1（不命中）⇒ 同一形状今天还能再进一次库。`docs/1-WORKFLOW.MD:385` 自述这两次入库是「误入库」 |
| `docs/iteration/sprint/*.png` | 2026-08-30 清出（`43bf388`）→ **至今悬空，未拉回** | `43bf388` 把它出库并加 `.gitignore:69`；但 sprint 文档仍在消费它：现跑 `git ls-files "docs/iteration/sprint/*.png"` 命中 0，而该目录磁盘上有 11 个 png，sprint 文档里 18 处相对图片链接中 16 处靠本机未追踪的字节解析、2 处是模板占位 ⇒ **全新 clone 上 16 处全断**；且**没有任何闸门查 markdown 图片存在性**（现跑 `git grep -ln "!\[" -- verify scripts` 无命中该用途） |

### 根因假设（各给一条支持或反证）
**H1「排除按卫生做的，事后才发现它承重」——支持，但有反证。** 支持：`agents/runs/` 在 `43bf388` 是按「中间态／实时／留证」排除的，其后 **5 个**闸门为它的缺席长出 fresh-clone／分支感知分支（现跑 `git grep -ln "fresh clone\|全新 checkout" -- verify scripts` 的命中集即该清单）。反证：`bc76083`（TG-9）那次**当次就查了消费者**——同提交带两条 `!` 白名单、policy `tracked_targets` 两条理由、闸门 `verify_artifact_paths.py` 的**双向差集**。所以"排除时不查消费者"并非能力缺失，而是**没有成为每次都要做的步骤**（见 H2）。

**H2「排除时没有检查消费者」——支持。** 最干净的证据是形状漏网：`.gitignore:53` 写的是 `verify/*.log`，而两次真正入库的产物叫 `verify_checkpoint_run.log`（在仓库根）与 `ci_fail_log.txt`（`.txt`）—— 规则与产物**同名不同形**，且现跑仍不命中。同类：`docs/iteration/sprint/*.png` 出库时，没有一条判据去看「谁在引用它」。

**H3「排除清单没有复审机制」——支持。** 三处排除源**都没有** `review_by`／到期 FAIL，而 policy 里每一个棘轮（lint 可读性、表格历史债、账本测量、派生数字、动态目标）**都有**。「到期未重评即 FAIL」这条判据在本仓已被证明可行，只是从未应用到排除清单上；各处的理由只以 `_comment` prose 形态存在 —— 按 `docs/1-WORKFLOW.MD` §6.0 的准入口径，prose 不是执行点。

**H4「排除理由本身没被复核过」——支持。** 排除项③的理由「649 处指针与 94 条引文无法核」与后来两次复测都不符（`2026-09-30` 的 D1 行、`2026-10-03` 的现跑读数）。理由写在条文里之后，就没有任何东西再去看它是否还成立。

### 方向（含机制建议）
**① 排除前必须证明无任何判据／文档消费它（机制，可判定）。** 每条排除声明落盘时必须同行附三连判定命令与读数：**(a)** `git grep -F -c -- "<被排除路径或形状>" -- scripts verify src paper-qa-script agents docs`（消费者扫描）；**(b)** `git ls-files <路径>`（是否已在库）；**(c)** `git check-ignore --no-index -v -- <目标形状探针>`（规则是否真的命中**目标形状**，而不只是命中作者当时想到的那个名字）。三连里任一出现消费者 ⇒ 该条必须同时给出开脱路径（`!` 白名单／`tracked_targets` 式理由／缺席分支的归属闸门），否则该排除条不成立。

**② 排除清单的周期性复审（机制建议；本轮**无法**落地机检 ⇒ 按 §6.0 显式标注「仅文字」）。** 给三处排除源加 `review_by` ＋ 到期 FAIL，复用 policy 里已验证的棘轮形态（`review_by` 键 ＋ `verify_gate_integrity.py::ratchets` 指针）。**代价必须写明**：本轮授权写入集**不含** `verify/**` 与 `scripts/**`，因此本卡**只给出机制方案，不落机检** —— 该条现为「仅文字」，强制力只剩人的执行义务；这与本仓 `agents/obligations.json::OBL-001` 的既有写法同构（`checker: none` ＋ `status: text-only` ＋ `not_implemented` 逐字声明缺口）。**不得把"已声明"读成"已解决"**。

**③ 排除规则必须声明它盖住哪种形状（机制）。** 把"规则是否命中目标形状"做成可判定探针（正形状命中／白名单形状以 `!` 命中／漏形状不命中），并把 `verify_checkpoint_run.log`、`ci_fail_log.txt` 这两个**现成漏形状样本**收作回归样本。

### 验收（可判定）
1. 三处排除源**逐条**带「消费者判定命令 ＋ 该命令现跑输出」；无消费者的条目必须带反证命令与零命中读数，否则不予收录。
2. **至少一条机检落地**：对排除源逐条做消费者存在性判定，命中消费者而该条未给出开脱路径 ⇒ FAIL；条数**不写死**，以该闸门 `--selftest` 末行 `ALL PASS (N assertions)` 为准。
3. **复审**：每条排除源带 `review_by`，到期未重评即 FAIL；若本批未落机检，必须在 `docs/1-WORKFLOW.MD` §6.0 索引里**显式登记「仅文字」并写代价**（否则按 §6.0 不予收录）。
4. **反向对照**：删除任一"承重"排除行（例如 `.gitignore:40` 的白名单行、`:53` 的 `verify/*.log`）⇒ 必须有闸门或套件判红，否则该行是死配置；并把两个漏形状样本（`verify_checkpoint_run.log`、`ci_fail_log.txt`）作为方向③的回归输入，要求"注入该形状的新产物"能被现跑判据点名。

## 派单方失误率（基线读）

> **来源**：用户 2026-10-03 原话——「**放进 A-CASE 或 A-EXCL 的正文里，作为『派单方失误率』的基线读：可以。**」
> 本条是**基线读数**（用于对照与后续趋势），**不是判据**：它不进任何闸门的判定域。
> **数据源＝账本现读**（`agents/runtime/registry.json`，逐笔由脚本读出，无手抄）：
> `python -c "import json,io; d=json.load(io.open('agents/runtime/registry.json',encoding='utf-8')); print(len([r for r in d['runs'] if (r.get('started_at') or '')>='2026-09-29']))"`
> ⇒ 现跑 **27**。**本节全部读数以该命令与下节逐笔表在 2026-10-03（UTC+8）的现跑输出为准。**

### 1. 关闭窗口与口径分歧（重要：与用户给的 26 不同）

现跑过滤 `started_at >= 2026-09-29`（G2 关闭期）：**27 个 run**，按角色 impact-assessment 3 ／ doc-audit 3 ／ **code-review 8** ／ implementation 12 ／ lessons-learned 1。
用户给的是 **26 个 run、code-review 7**。**差异定位为精确一户**：`run-2026-10-03-code-review-128`（`started_at=2026-10-02T17:13:28Z` ＝ 2026-10-03 01:13:28 UTC+8）——它**在用户给数之后**才登记（用户口径 7 笔 code-review 即 `-104/-105/-107/-114/-122/-125/-126`），是本批（收口批）自己在飞的产物。
**本节以 27 为分母**（它已是账本现读），并同时给出 26 口径下的换算，两者都标在读数行上：

| 口径 | 分子 | 分母 | 比率 |
|---|---|---|---|
| 用户口径（26，不含在飞的 `-128`） | 7 | 26 | **26.9%**（用户原话「7/26 ≈ 27%」，复算 7÷26=0.2692） |
| 本卡口径（27，账本现读全集） | **8** | **27** | **29.6%**（复算 8÷27=0.2963） |

**为什么本卡口径多一笔**：本卡按「**上级指令修正**」的**可判定定义**（下节 §2）逐笔判，`-128` 的主体工作＝修正**父代理 `finish` 默认落 HEAD 造成的退化空窗口**（受控回填 `-127` 的锚点）⇒ 按定义归入该族。用户举例里 `-128` 写的是"（在飞）模板缺陷"，**与本卡的归类同族，只是当时未计入分母**。

### 2. 本卡自己的分类口径（三分类，逐笔唯一）

判定对象＝**该 run 的主体工作**（不是它顺带碰到的东西），依据一律取该 run 的 `task_id` ＋ `scope_deviation` 账本现读 ＋ 其产物报告的头两节（现读 `agents/runs/<run_id>/`）。

| 类别 | 定义（可判定） | 落笔判据 |
|---|---|---|
| **A 设计内流程** | 主体工作＝关闭契约本身要求的那几步：作用域评估（order1）、三查（一查/二查）、修复验证复核、lessons 蒸馏、workspace-check | `task_id` 形如 `G2 close three-check step1`／`target=branch:*`／`target=working-tree(fix-verification)`；或 `role=lessons-learned` |
| **B 对发现的正规修复** | 主体工作＝修**本批判据自己报出的**缺陷，且缺陷来源不是上级的产出／记录（源码缺陷、判据强度缺口、门语义缺口、结构化收敛） | `task_id` 含 `close the N critical + M major`／`dispose retro S5 rows`／`fix-verification findings`／`convergence-batch`；`role=implementation` |
| **C 上级指令修正** | 主体工作＝**修正上级（父代理）自己的产出或记录**：误读事实的派单前提、范围漏项、报告自陈强于实际且需复核、验证只覆盖本地而产生的 CI 缺口、**派单时未登记 run 导致的归属补偿**、对上级数据的断言未通过／停并上报、上级工具默认值造成的空窗口 | 见 §3 逐笔表；`task_id`／`scope_deviation` 里出现"登记补偿／归属补偿／补登记"或"断言未通过／已停并上报"，或产物报告首节含"先更正派单前提" |

**归属规则（去重）**：一笔 run **只算一次**；按上表**从上到下第一个匹配**归类（A 优先于 B，B 优先于 C），避免"顺带补一句登记"被计成 C。
**反例（本卡刻意不计入 C 的）**：`-108`（处置复盘 §5 行 26–51 的修复项，其中含用户豁免行的翻状态）——其主体是**复盘表报告的缺陷**逐行处置，不是上级指令错；`-116`（同一张表的行 43/45/46/51 豁免落地）**计入 C**，理由是它的第一项任务＝把用户 2026-09-30 的豁免裁定写进复盘表，属**上级记录修正**（两类相邻但不同：改判据 vs 改记录）。

### 3. C 类逐笔（本卡口径 8 笔；字面命令与读数均现读自 `registry.json` 与对应 run 报告）

| # | run | 角色 | 上级失误类型 | 归因依据（现读） | 工时（`dur_minutes` 现读） |
|---|---|---|---|---|---|
| 1 | `-107` | code-review | **派单时未登记 run ⇒ 归属补偿**（上级把"登记 run"当成子代理的作业） | `task_id=close-gap backfill 958c739878..18f2274eab`；`scope_deviation` 逐字「本 run 只补登记关闭期工作窗口 … 的归属（派单反例档案例 11 同族：这些提交派单时未登记 run）；不评审 …」 | 8.867 |
| 2 | `-110` | implementation | **上级读错表**（派单前提不成立：把 §3/§4 表当成 §5 表） | 报告 §A0「**先更正派单前提（如实记，重要）**」逐字：派单书写"§5 表行 1–25 与 26–51 的列结构不一致"，实测「**该前提不成立**」——§5 表自始统一 4 列、51 行每行 4 格；派单举证的 `:51/:52/:53`／`:91`／`:93` 属**同一文档里另外两张表** | 18.550 |
| 3 | `-113` | implementation | **指令范围漏项**（上级第一批只覆盖 CI 的"套件步骤"，漏了同族的"Close-readiness gate"步骤） | 报告首行逐字「CI 放行的**第二处落点**：`Close-readiness gate … (TG-11)` 步骤的第三态护栏」——即 `-112` 的**同族第二处**；`1-WORKFLOW.MD` §6.0 的 M7 行与 `.github/workflows/ci.yml` 的两段护栏（`CI-SKIP-GATE`／`CI-CLOSE-SKIP-GATE`）为证 | 18.267 |
| 4 | `-116` | implementation | **报告与事实不符**（复盘行 29 的 `状态说明` 自陈覆盖面大于判据实际能力，须由复核逼出补第二轮） | 复盘 `§5` 行 29 现读逐字：「**2026-09-30 复核 `run-…-114` major 1 后已补第二轮，`状态说明` 按实际判据能力改写**——原文只声明『两种吞码形态现判 False』，而 `a3a3f25` 的判据只认**行首**是命令位置 … ⇒ **自陈强于实际**」 | 0.333 |
| 5 | `-118` | implementation | **验证只覆盖本地**（上级的判据⑤只在"占用者可归属"这一支被驱动过，CI 上"被占但查不到属主"判红） | 报告逐字「**根因＝判据只在『占用者可归属』这一支被驱动过**：CI（Windows runner）上端口确实被占、却查不到属主（系统保留区间），旧断言要求一个**并不存在**的 PID ⇒ `含占用PID=False` ⇒ 判红」；`task_id` 直接点名 `CI run 36628590106 红因` | 15.683 |
| 6 | `-125` | code-review | **派单时未登记 run ⇒ 归属补偿**（同 #1 同族） | `task_id=close-gap attribution backfill 677338f2..ce0cd180（归属补偿记录，非评审）`；`scope_deviation` 逐字「本 run 是**归属补偿记录**（登记补偿族，同 run-2026-09-29-code-review-107；派单反例档案例 11 同族），**不是** … 独立代码评审」 | 0.383 |
| 7 | `-126` | code-review | **转述未核**（上级转述的 `g1-vs-g2` 指针关系未先核实；断言未通过 ⇒ 停并上报） | `task_id` 逐字含「断言未通过，已停并上报」；`scope_deviation` 逐字「… 对 g1-vs-g2 的 5 处指针做 '+2 且对象同一' 断言；**断言未通过故未改该档，停并上报**」；另 `anchor_backfills[0].reason` 记「finish 时误按任务模板把 coverage_anchor 也设成 f763f82b，窗口成 (f763f82b,f763f82b] 空区间 … C3 报 f763f82b 无归属（CLOSE-READINESS FAIL 1 项）」（同一笔的两个上级侧缺陷，只计一次） | 4.267 |
| 8 | `-128` | code-review | **上级工具默认值缺陷**（`register`／`finish` 默认落当刻 HEAD ⇒ 声称覆盖却贡献 0 覆盖，须回头改 `-127` 的锚） | `-127` 的 `anchor_backfills[0]` 逐字：「finish 默认把 covers_through 落成当刻 HEAD，而本 run 的锚与端点都落在 f763f82b ⇒ 窗口 (f763f82b,f763f82b] 为空区间、声称覆盖却贡献 0 覆盖；按同族先例（-125/-126）把锚回填到上一窗口端点 ce0cd180，使其窗口＝(ce0cd18,f763f82b]，非伪造覆盖」，`by=run-2026-10-03-code-review-128`；`-128` 的 `task_id` 首项即「`-127` 空窗口」 | 0.483 |

**C 类工时读数**（`dur_minutes` 逐笔现读求和）：**66.83 分钟 ≈ 1.11 小时**；同窗口（27 笔）总工时 **359.25 分钟 ≈ 5.99 小时** ⇒ **C 类占窗口墙钟 18.6%**。
**成本读数（缺口如实声明）**：窗口内 27 笔的 `cost_est.total` 现跑**只有 1 笔非空**（`run-2026-09-29-impact-assessment-103`，0.01575926 CNY），其余 26 笔为 `null`（`pending_price=true`）⇒ **本卡无法给出"上级失误花了多少钱"**，只能给墙钟工时。这一缺口本身就是卡 `A-COST`（成本归属：`finish --usage-*` 未用 ⇒ 损失只能从会话日志反推）的实例，不在本卡解决。

### 4. 机制：「源于上级指令修正」的可判定打标规则

**目标**：让 §3 那张表**下一批不用人再判一遍**，且比率可被脚本持续统计。

**规则（v1，可判定；三件同时成立才算 C 类）**：
1. **前缀标记**（新增字段位）：`register` 的 `--task` 以**字面前缀** `[PARENT-FIX]` 开头（英文大写与方括号逐字，不接受 `Parent-Fix`／`【PARENT-FIX】` 等同义变体——变体一律不命中，宁可漏计不得误差）。
2. **类型码标记**：同一次 `register` 的 `--deviation` 必须**逐字包含**且**只包含一个**类型码，取自**封闭词表六项**：`read-fact`（读错表／读错事实）｜`scope-omit`（指令范围漏项）｜`report-unsourced`（报告与事实不符）｜`local-only-verify`（验证只覆盖本地）｜`relay-unchecked`（转述未核）｜`tool-default`（上级工具默认值缺陷）。另**独立第七类** `attribution-backfill`（派单时未登记 run ⇒ 归属补偿），与上面六类并列但不混用（它的成因是**登记纪律漏项**，不是判断错误）。
3. **可复算命令**：比率＝
   `python -c "import json,io,re; d=json.load(io.open('agents/runtime/registry.json',encoding='utf-8')); g=[r for r in d['runs'] if (r.get('started_at') or '')>='2026-09-29']; c=[r for r in g if str(r.get('task_id') or '').startswith('[PARENT-FIX]')]; print(len(c),'/',len(g))"`
   ⇒ 分子＝窗口内 `task_id` 命中前缀的 run 数，分母＝窗口内 run 总数。**无 `--deviation` 类型码的命中行单独列出并计为"打标不完整"**（不静默计入也不静默丢弃）。

**这个规则现在落地了吗——如实说：没有，且按现行授权无法落地。** 三条缺口逐条声明（按 `docs/1-WORKFLOW.MD` §6.0 的准入口径标注「仅文字」并写代价）：

| 缺口 | 事实（现读） | 代价 |
|---|---|---|
| ① **存量 8 笔没有该前缀** | 逐笔 `task_id` 现读（§3 表第四列引文）**一处 `[PARENT-FIX]` 都没有**——它们当时的写法是中文叙述（「先更正派单前提」「断言未通过，已停并上报」） | 比率**当前不可机检**：§3 那 8 笔是人判的，换个人复算可能得 7 或 9（口径分歧已实测：26 vs 27、7 vs 8） |
| ② **账本 schema 无校验口，且 `scripts/**` 本批不许改** | `scripts/agent-ops.py register` 现读**只校验"传进来的参数合法"**，不校验 `--task` 前缀；本批授权写入集**不含** `scripts/**` 与 `verify/**` | 前缀是**约定**不是**执行点**：写错前缀不会红，只会静默少计 ⇒ 与卡 `A-DECL`（规则可以是无实现的声明）同族 |
| ③ **回填还是只向前？未决** | 回填 8 笔＝经 `agent-ops` 写账本（**本批授权范围未明确包含账本写入**，故本批**不做**） | 不做回填 ⇒ 本节比率在下一批**断点**：新旧口径不可直接相加；做回填则需先由父代理裁"账本历史能否受控回填"（同 `set-anchor` 的先例） |

**因此本卡的处置**：规则 v1 **只给机制与词表**，落地形态标为「**仅文字**」；**不得把"已声明"读成"已解决"**。**判据（可判定）**：当 `scripts/agent-ops.py` 的 `register` 能在 `--task` 缺 `[PARENT-FIX]` 前缀而 `--deviation` 含类型码时**报错退出**，本条从「仅文字」升级为「有执行点」——`verify/verify_agentops.py` 的 `--selftest` 应新增一条反向对照断言（缺前缀 ⇒ 非零退出且点名），否则升级不成立。

### 5. 与其它卡的关系

- **`A-REG`（派单登记可验证性：规则 14 现为荣誉制，账本分不清谁按的键）**：本节的**同一根因**——C 类第 1/6 笔（`-107`/`-125`）就是"派单时没人按登记键"的直接成本；本节的打标规则若落地，`A-REG` 的"荣誉制"问题会缩小一格（能证明**哪几笔是补偿**），但不解决"谁按的键"。
- **`A-COST`**：§3 的成本缺口（26/27 笔 `cost_est.total=null`）是 `A-COST` 的实测实例，本卡只引用不解决。
- **`A-CASE`**：用户原话允许本条落在 `A-CASE` 或 `A-EXCL` 之一；本卡落在 `A-EXCL`，理由是**同期同批**（`A-EXCL` 与本节都由 2026-10-03 这一批写入），且本节引用的"派单反例档案例 11"正是 `A-CASE` 语料的一条。
