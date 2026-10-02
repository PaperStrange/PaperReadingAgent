# BR-1 现行基线逐条盘点 ＋ 分类法 ＋ 处置判据：棘轮只防恶化不促改善，而每次编辑都要付费

- `card`: BR-1
- 索引: [../backlog.MD](../backlog.MD)

## 状态
候选

## 规模
8

## 来源
用户 2026-10-03（UTC+8）原话（本会话逐字）：「**关于基线这件事需要系统性检查和重构，补一张 agent infra 的阶段。现在的基线只会让我花更多的钱和更多的时间产出一个原地踏步的东西。**」

## Sprint
—

## 正文
### 现象

**棘轮／基线只防恶化、不促改善，而每次编辑都要付费。** 三条机制事实叠在一起就得出用户的结论：

1. **棘轮形态天然是单边的**：本仓现行基线的判据一律是「实测 **≤** 上限 ⇒ 放行；**>** 上限 ⇒ FAIL」，而 cap **只许下调**（上调要 `rebased_at` ＋ `rebased_reason` 署名，见 `agents/policy.json::lint_readability_ratchet._measured_value_why` 现读）。这套形态**只禁止变坏**，对"变好"零要求——**没有一条判据要求实测值必须从 cap 往下走**。
2. **每次编辑都要付费**：C 级 lint 的 cap 是**全仓绝对条数**，不是增量。任何一次正常改动（加一行、改一个 docstring、动一条注释）都会改变全仓计数，于是**每一次编辑都要先付一次"重排/折行/补 docstring"的过路费**才能让闸门变绿——`E501` 现跑的 `2494/2494`（2026-10-03 现读，见下 §1 行①）就是**零余量**：再多一条超宽行，当期就红。
3. **结果是"花更多钱与更多时间，产出原地踏步"**：本批批前现跑的 `scripts/spend-report.py --check`（2026-10-03，UTC+8）读数——派单会话数/日 **19**（预算 6、基线 20）、主代理 output token/日 **55396**（预算 50000、基线 99533）、当日合计 **23.73 CNY**（预算 12.0、基线 19.67）⇒ **三项全 OVER**。而 `agents/spend-budget.json` 自身逐字写着基线读数「**仅用于对照、自述『不作为判据』**」⇒ 花超了**只有一张表红**，它**不阻断派发、也不驱动改善**；产出侧则被上面第 2 条钉在"只能不变坏"。**这就是"原地踏步"的财务形态。**

### 1. 现行基线逐条枚举（一律现跑取证；读数同行带时点锚 2026-10-03 UTC+8）

**取证命令（本表全部读数的产生方式，现读）**：`verify/verify_lint.py`、`verify/run_suite.py`（读源码常量）、`verify/verify_card_index.py`、`scripts/card-inventory.py`、`verify/verify_derived_numbers.py`、`verify/verify_md_tables.py`、`verify/verify_gate_integrity.py`、`scripts/spend-report.py --check`、`verify/verify_decision_register.py`、`verify/verify_close_tax_reading.py`、`verify/verify_ledger_measurement.py`、`verify/verify_artifact_paths.py`（均以该命令当次输出为准）。

| # | 基线 | 消费者（哪个闸门读它） | 当前读数（2026-10-03 现跑） | 最近一次实际挡住的真实缺陷 | 最近一次造成的返工代价 |
|---|---|---|---|---|---|
| ① | **C 级可读性棘轮 caps**（`D101/D102/D103/E501`，含 `measured_at`／`review_by`／只许下调） | `verify/verify_lint.py::ratchet_problems`；完整性由 `verify/verify_gate_integrity.py` 的 `ratchets[0]` 再校验 | caps `D101=12 D102=46 D103=205 E501=2494`；实测 `12/12、46/46、203/205、2494/2494`；`measured_at=2026-09-25`、`review_by=2026-10-31` | **有**：`E501` 零余量当场咬住——改文档行即顶破，逼出按**显示宽度**（CJK 占 2 列）折行 | **重**：`2026-09-25` 关闭期唯一一次重评把 `E501` 由 2631 下调到 2494（折 37 行 → 2492）；复核期又由 2492 **回升到 2494** 并**再次折行** ⇒ 同一件事付了**两次**折行费。另 `D103` 亦曾由 207 下调到 205（补 10 处 public 函数 docstring） |
| ② | **`run_suite.py::BRANCH_ASSERTION_FLOORS`**（断言**条数下限**，9 个键、分支感知） | `verify/run_suite.py`（套件自己；判据①判决句出现、②SKIP 不算通过、③N 不低于下限、④自陈脚本数不低于下限） | 现读：`verify_agentops.py=180`；`verify_card_index.py=17`（present）／`15`（absent）；`verify_decision_register.py=32/32`；`verify_derived_numbers.py=19/19`；`verify_gate_integrity.py=88/88`。**逐值对照现跑末行**：套件这五项现跑断言数均 ≥ 各自下限 | **有**：`verify_gate_integrity.py` 的下限曾写在 **68** 而现跑 **75** ⇒ **删掉 7 条 `ok()` 仍判绿**；同批复核出 `verify_agentops.py` 亦有余量（**177 → 180**）。两处都点名为"下限与实测不一致" | **中**：**同步副作用**——每加一条断言，**所有**引用该数的文档与常量要跟着改：本批现读可见 `verify_gate_integrity.py` 在 `2026-09-30` 一天内被三次抬高（**68 → 75 → 88**，随 `6a0cfc9` 的 7 条与本批 13 条）；`verify_agentops.py` 同步抬（**177 → 180**） |
| ③ | **`run_suite.py::BRANCH_VERDICT_SCOPE_MIN`**（判决句必须落在输出末尾几行内） | `verify/run_suite.py` | 现读 `{True: 5, False: 5}`（两分支同值）；配套 `VERDICT_TAIL_LINES = 6` 现读 | **无留痕案例**（现跑该闸门输出与两端常量里都查不到它咬住过哪条缺陷） | **无留痕案例**。**但有一条同族已结案的强度缺口留档**：`verify/verify_gate_integrity.py` 的 `ratchets` 曾**漏覆盖** `lint_readability_ratchet.caps` 一族——`agents/policy.json` 逐字记「本表此前未被 `gate_integrity.ratchets` 覆盖 ⇒ 声明 Σ=107 而现跑 105，存在 **2 处静默配额**」（`2026-09-25` M-C 收口）。**该缺口的实际影响是"声明不可信"，不是"挡住了假绿"** ⇒ 按本卡 §3 判据**重分类**，不计作它挡住的缺陷 |
| ④ | **`agents/runtime/tg14-baseline.json`**（卡库存"当前真值快照"）＋ **`scripts/card-inventory.py`** | `verify/verify_card_index.py` 判据⑦（`totals` 必须与 `card-inventory` **当次**输出逐值相等；基线缺失/工具输出解析不出 ⇒ FAIL） | 本批**刷新前**：基线 `totals = {cards:106, phases:4, non_card_rows:1}`；工具现跑「合计：106 张卡 / 4 个阶段 / 非卡行 1」（2026-10-03 现读，**另有**本批在飞的 `A-EXCL` 已由上一批计入 33） | **有**：七条判据里唯一"曾被静默放过"的是它自己——基线文件自称"当前真值快照"，**却曾落后 1 卡**（`TG-14` ⑦ 的落地理由，现读 `verify_card_index.py` 判据⑦ docstring 逐字） | **重**：**每次卡数/阶段数变动都要重刷**。本批一条实例：新建阶段 ⇒ `totals` 变 `{cards:107, phases:5, non_card_rows:1}` ⇒ 判据⑦**必然红**，必须先跑 `scripts/card-inventory.py --json <路径>` 才能过 |
| ⑤ | **`derived_numbers.baseline`**（派生数字"当期主张"的历史文件上限，`default_cap=0`） | `verify/verify_derived_numbers.py`；完整性由 `verify_gate_integrity.py` 的 `ratchets[3]` 再校验 | 现读：**32 个历史文件 / 111 处**上限（`measured_at=2026-09-25`、`review_by=2026-10-31`；13 个模式，含 `claim_count`／`all_pass`／`assertions_cn`／`evidence_line`／`gate_required`／`ratchet_pair`／`replay_count`／`diffstat`） | **有**：**本批当场实测**——写本卡时 A-EXCL 新节里一句「C 级 2880 条」形态被 `c_level_total` 命中（闸门 `--selftest` 现跑的反向对照 H 用它当样本）⇒ 改写成"命令 ＋ 以该命令输出为准"才过 | **重**：`2026-09-25` 首次扫出 **111 处**违规，逐一改写或补时点锚；此后**每一篇新文档**都受 `default_cap=0` 约束 ⇒ 写作时必须同时想"这个数字闸门认不认" |
| ⑥ | **`md_table_legacy_files.files`**（4 个历史文件，缺陷上限全 **0**） | `verify/verify_md_tables.py`；完整性由 `verify_gate_integrity.py` 的 `ratchets[1]` 再校验 | 现读「棘轮基线：**4** 个文件（按文件设缺陷上限）；`review_by=2026-10-31`，今日=2026-10-03 → 未到期」；全仓「MD-TABLE PASS（191 个文件解析通过；其中 4 个历史文件走棘轮基线）」（2026-10-03 现读） | **有**：`TG-18` 在 `2026-09-25` 把这 4 个文件的 **15 处**真实表格缺陷（未转义管道／表头与数据行列数不符）逐处清零后把上限由 1/12/1/1 置 **0** | **中**：15 处历史债的**人工逐处修**（每处要人判：补表头列／转义内容管道／合并单元格）；**当时的替代路径更贵**——`2026-09-23` 实测过一次"为了让闸门变绿而改写已关闭 Sprint 的历史记录"，**已 revert**（现读 `md_table_legacy_files._comment` 逐字） |
| ⑦ | **`agents/spend-budget.json`**（成本预算 ＋ 基线读数） | `scripts/spend-report.py --check` | **预算**：派单会话数/日 6、主代理 output/日 50000、当日合计 12.0 CNY；**基线（2026-09-28，自陈"不作为判据"）**：20 ／ 99533 ／ 19.67。**批前现跑**：19 ／ 55396 ／ 23.73 ⇒ 三项全 OVER（会话数 3.2× 预算、token 1.11× 预算、CNY 1.98× 预算） | **有**：`2026-09-30` 修掉两处"基线恒真"缺陷——① `--check` 原来自述比对 baseline 而**实测不真比对**（`fa1250a` 修，逐字：`spend --check really compares baseline`）；② `main_sessions` 写死某台开发机的会话 id，换机器即**静默变 0 而 `--check` 照常判 OK**（复盘 §5 行 37，`a3a3f25` 修：id 不存在改 `[SKIP]` ＋ rc=3 ＋ 上屏"不是通过"） | **无留痕案例**（**这是个发现，不是缺口**）：三项全 OVER 而**没有任何东西因此停下**——它对"花钱更多"零约束，正是本卡现象第 3 条 |
| ⑧ | **`verify_decision_register.py` 的 `quotes_drift` 漂移计数**（被当成"不得增长"的基线而非缺陷信号） | `verify/verify_decision_register.py`（`drift` 只进 `warns`、**不判 FAIL**，见该脚本现读 `L575-L576`"漂移可见、不判 FAIL"）；完整性由 `verify_gate_integrity.py` 的 `guard_required` 再校验 | 现跑 `EVIDENCE` 行现读：`entries=124 quotes_checked=97 quotes_drift=10 pointers=1248`。**漂移在 ±2 窗口内命中而指针行未命中**——它是"指针已漂"的**信号**，却被当作"不得增长"的**基线**使用 | **无留痕案例**（它按设计不判 FAIL） | **重**：本批实测一条——`docs/iteration/sprint/2026-09-25-sprint-18.md:393` 逐字记：在 `:234` 处插行会让其后**整体下移 3 行**、两条逐字引文落到 ±2 窗口外 ⇒ `quotes_drift` **由 10 涨到 12**（**实测**）；为把漂移**净新增压回 0**，补登记表只能放到**文件末尾** ⇒ 代价是该 Sprint 的 run 行**分处两段**、人读须看两处。**同一窗口内已为它反复付过费**：`2026-10-03` 的 `-126`（`+2` 断言未通过 ⇒ 停并上报）、`-127`／`-128`（空窗口与锚点回填）三笔 run 都与"指针/锚点不得漂"直接相关 |
| ⑨ | **`ledger_measurement.legacy_ratchet.caps`**（账本历史缺陷计数上限，8 个键） | `verify/verify_ledger_measurement.py`；完整性由 `verify_gate_integrity.py` 的 `ratchets[2]` 再校验 | 现读 `missing_result_files_review=9/9 missing_timestamp=0/0 negative_duration=0/0 output_chars_zero=12/12 round_duration=3/3 rounds_mismatch=1/1 terminal_not_written_back=0/0 zero_duration=3/3`（`measured_at=2026-09-25`、`review_by=2026-10-31`） | **有**：`output_chars_zero=12` 一类挡的是"把交付当没交付"；`missing_result_files_review=9` 挡的是**评审类 run 已终态却无产物**——该闸门现跑逐条 `WARN` 点名 9 例（例：`run-2026-09-09-doc-audit-043`「评审产物未归档，评审结论不可回溯」） | **中**：上限**只许下调**⇒ 每修一例就要重评一次基线（改 `caps` ＋ `measured_value` ＋ 署名）；未修完的 9 例则**每跑必刷一屏 WARN**（噪音成本） |
| ⑩ | **`artifact_paths.dynamic_ratchet.files`**（"写盘目标无法静态判定"的按文件上限） | `verify/verify_artifact_paths.py`；完整性由 `verify_gate_integrity.py` 的 `ratchets[4]` 再校验 | 现读：扫描集 98 个脚本 / 368 写盘目标；动态 **105**（`measured_total=105`）；`measured_at=2026-09-25`、`review_by=2026-10-31` | **有**：反向对照②现跑逐字——注入"写到仓库根"的新脚本 ⇒ `rc=1` 并点名「`tg9-injected-artifact.json` **未被 `.gitignore` 忽略**…须落 `agents/runtime/` … 或 `%TEMP%`」 | **中**：**未列入上限表的文件出现动态目标即 FAIL** ⇒ 每次新写盘目标都要人判"落点能不能静态判定"，判不了就要先改基线表（改表须署名 + `rebased_reason`） |

**枚举边界（如实记）**：`agents/policy.json` 另有 `deduction_rates`、`hardcode_exemptions`、`md_table_coverage` 三键具备"阈值/词表"形态但**未被本表逐条盘**（M1 部分完成的原因，见 `roadmap.MD` §2）。

### 2. 分类法（四类）与每类的处置

| 类别 | 判据（现读可得） | 处置 | 本表归属 |
|---|---|---|---|
| **承重** | ①有具体消费者；②**能证明**它最近一次挡住的真实缺陷；③该缺陷若放过会造成不可核／不可复现（不是"风格不好看"） | **保留**（但按 §3 增加"成本-收益读数"格，让它自证） | ①（E501 那一支）、④、⑤、⑥、⑨、⑩ |
| **自律性** | **无留痕案例**：现跑查不到它咬住过任何真实缺陷 | **改造为"促改善"**：给它补一条**要求实测值从 cap 往下走**的判据（现在只有"≤"）；给不出促改善形态的**降级为提示**，不得继续以 FAIL 收费 | ③、⑧ |
| **锁住债务** | 有真实缺陷记录，**但**它的存在理由是"历史既存债 → 用上限换时间"，而上限**只许下调**⇒ 它把债务**锁在了原地**（既不清零也不冒头） | **改造为"促改善"**：上限之外再挂一个**速率**判据（例：`review_by` 到期时实测值必须严格小于上一次重评时的 `measured_value`，否则 FAIL）。这是本卡对"棘轮不促改善"的正面修法 | ②（断言下限）、⑦（成本基线）、⑨（9 例 WARN 若长期不动） |
| **可弃** | ①消费者缺席（没有任何闸门读它）；或②它守的东西**已被另一条更强的判据覆盖**（重复计数） | **删除**（连同它的 `review_by`；删前必须给"零消费者"的反证命令） | 本表 10 条**暂无**——**这是个结论，不是遗漏**：十条都有现跑可指的消费者，故本轮**不建议删除任何一条**，只建议改造 |

**可判定口径（本卡要求写进判据的原文）**：
> **棘轮若不能证明它最近挡住过真实缺陷，就不该继续收费。**
逐条落地为三问，答"否"即触发处置：
1. **"最近一次挡住"有没有具名证据？** 证据形态限三种：闸门输出的 FAIL 行、账本 run 的 `task_id`／报告里的修复记录、或提交信息里点名的该类计数。**"应该能挡住"不算证据**。
2. **它挡住的缺陷若放过，会不会造成不可核或不可复现？** 只会造成"不好看"的 ⇒ 不属承重。
3. **它最近一次造成的返工，代价是否已经超过它挡住的缺陷的代价？** 超过 ⇒ 改造（补促改善/速率判据）或降级为提示。

### 3. 验收（可判定）

1. **每类基线给出成本-收益读数**：`承重`／`自律性`／`锁住债务`／`可弃` 四类各至少一条，逐条给「挡住过什么（具名）／造成过什么返工（具名）／两者可比」；给不出具名证据的写「**无留痕案例**」，**不得**推测补齐。
2. **删除／改造／保留各给判据**：每条基线一行裁定；`删除` 必须附**零消费者反证命令**；`改造` 必须附**改造后的可判定形态**（例：速率判据的阈值与比较口径）；`保留` 必须附它第 1 问的具名证据。
3. **至少一条基线的处置落地 ＋ 反向对照**：落地方向二选一——(a) 删除一条零消费者的基线；(b) 给一条基线加"促改善"判据。反向对照：**(a)** 恢复被删基线中的任一条 ⇒ 必须有闸门判红（否则该条本就是死配置）；**(b)** 把实测值**停在 cap 上不动**（模拟"零改善"）⇒ 新判据**必须红**——这是"棘轮变促改善"的核心反向对照。
4. **授权缺口如实标注**：本批授权写入集**不含** `verify/**`、`scripts/**`（只读）⇒ 上述落地**本批做不到**。按 `docs/1-WORKFLOW.MD` §6.0 的准入口径，本卡把"改造为促改善"标为「**仅文字**」并写明代价：**它现在只活在人的执行义务里**——与 `agents/obligations.json::OBL-001`（`checker: none` ＋ `status: text-only`）同构。**不得把"已声明"读成"已解决"**。

### 4. 方向（机制建议，按判据可判定）

- **方向 A（促改善判据的最小形态）**：给每条 `lock-debt` 类上限加**单调性要求**——`review_by` 到期时 `实测值 < 上一次 measured_value`，否则 FAIL。**为什么这能治"原地踏步"**：现行判据只要求"不超标"，新判据要求"必须往下走"；且它复用**已有**的 `measured_value`／`review_by`／`rebased_*` 字段，**不新增数据面**。
- **方向 B（成本基线也进判据）**：`agents/spend-budget.json` 的 `baseline` 现自陈"不作为判据"。若把它升级为判据（例：连续两日 `> budget` ⇒ 阻断新派单），需先由用户裁"成本能否阻断派单"——本卡**不擅自升级**，只登记为候选。
- **方向 C（漂移计数回归"信号"本位）**：`quotes_drift` 是**信号**（指针已漂），现行用法把它当**基线**（不得增长）。建议：漂移**逐条点名**并要求每条给"重锚或豁免"的处置，而不再只报一个总数。代价：**逐条处置会让当前 10 处全部暴露**，本批不动。

### 5. 未决点（需父代理或用户裁）

1. **全局 ROADMAP 未登记本阶段**：`docs/iteration/ROADMAP.MD` 不在本批授权写入集 ⇒ 该档"Now/Next 档阶段索引"尚未含 `baseline-reform`（阶段目录已建，索引滞后）。同族先例：`A-M13` 的卡与索引就曾出现过偏差。
2. **本卡点数 8 是估的**：M1 已交付 10 条盘点；M2（逐条裁定）与 M3（落地＋反向对照）的实际点数**未按 `1-WORKFLOW.MD` §4.4 走 planning 判定**（本批不开 Sprint）。
3. **`tg14-baseline.json` 的刷新是"必然"而非"可选"**：新建阶段使阶段数 4 → 5，判据⑦在没有刷新时**必然红**——本批已刷新；后续任何阶段/卡数变动同样要刷。
4. **`agents/policy.json` 三键未盘**（`deduction_rates`／`hardcode_exemptions`／`md_table_coverage`）⇒ M1 只算部分完成。

### 6. 本批没做的事（如实记）

- **没有改任何 `verify/**`、`scripts/**` 文件**（授权只读）；**没有放宽任何判据、没有上调任何 cap**；**没有 `git add/commit/push`**。
- **没有删除或改造任何一条基线**（M3 未开始）⇒ §3 验收第 3 条**本批不通过**，如实留在此处。
- **没有把 `agents/spend-budget.json` 的基线升级为判据**（方向 B 需用户裁定）。
- **没有回填**本卡引用任何历史读数到 `measured_value`（按当次实测为准，只引用不写回）。

### 7. 落地记录（2026-10-03 批：用户裁定「成本基线倾向 A」＝**超预算即阻断派单**）

> 本节**只追加**。上文 §5 第 2 条、§6 第 3 条记的是**上一批**的状态（"方向 B 需用户裁定／本卡不擅自升级"）——用户 2026-10-03 已裁定，故本批落地；**上面那些行一个字都没删**，以免把"当时的边界"改成"事后看本来就该做"。

**裁定 → 实现口径**（父代理 2026-10-03 转述，本批**照此实现、未另设计**）：

1. **阻断轴＝派单数/日，读数必须取自账本**：`register` 现读 `runtime/registry.json`（本命令在锁内刚 load 的那一份）里当日（UTC+8）已登记的 run 数，`>= 预算` 即**拒绝启动**（`rc=1`，沿用本仓"拒绝启动"语义）。
2. **金额（CNY）/日 轴暂不阻断**，只上屏提示：度量仪 `scripts/spend-report.py --check` 的"派单会话数"把**别的主线的子代理会话**也算进本主线（作用域缺陷，归 `A-COST` 卡）⇒ 拿它当阻断依据＝**用错数停工作**。本批**不改度量仪**，只在拒绝文案里如实标注该缺陷。
3. **具名逃生门**：`register --over-budget "<理由 ≥下限>"` ⇒ 放行，且理由**落账本**（不是只上屏）。
4. **预算值从数据文件读，不许在代码里写死**：`agents/spend-budget.json::budget.dispatched_sessions_per_day`（2026-10-03 时点读数 **6**，**本批未动**，现值以文件为准）；逃生门理由下限新增键 `over_budget_escape.reason_min_chars`。判据＝`verify/verify_no_policy_hardcode.py`（干净与否**以该命令现跑输出为准**）。

**实现点与接线位置**：

| 位置 | 作用 |
|---|---|
| `scripts/agent-ops.py::_spend_budget_path` | 预算文件 = `<账本根>/spend-budget.json`（默认即 `agents/spend-budget.json`）。**跟账本根走**：预算与账本必须同源，否则是拿另一本账的预算判这本账的读数（度量仪作用域缺陷的同一种病） |
| `scripts/agent-ops.py::_dispatch_budget` | 读预算与理由下限。文件**不存在** ⇒ 判据**未执行**（上屏点名"不是通过"，但不阻断隔离账本：verify 夹具与 `%TEMP%` 探针没有预算文件）；文件在但预算键**缺失/布尔/负数** ⇒ **fail-closed 拒绝**（配置坏了必须响亮地坏） |
| `scripts/agent-ops.py::_dispatch_reading` | 当日（UTC+8）读数 = `run_id` 的 `run-<日期>-` 段 **∪** `started_at` 折算 |
| `scripts/agent-ops.py::_dispatch_gate` | `>= 预算` ⇒ 拒绝（点名**读数／预算／逃生门用法**＋金额轴缺陷）；具名 ⇒ 放行并回传留痕；**未超预算却传 `--over-budget`** ⇒ 拒绝（假留痕比无留痕更坏） |
| `scripts/agent-ops.py::cmd_register` | 接线点：**纯输入校验之后、任何写盘之前**——输入错永远报它自己的错，且被拒时账本零字节改动（拒绝启动 ≠ 半写） |

**字段落点**（父代理要求说明"理由落哪个字段"）：具名豁免写该 run 行**两格**——

- `budget_override_reason`：理由**原话**（去空白后 ≥ 下限）；
- `budget_override`：`{axis, reading, budget, day, at}`＝**被豁免掉的那一次读数**（哪个轴、当时读多少、预算是多少、UTC+8 哪天、何时登记）。

先例：`finish --allow-degenerate` 的 `degenerate_reason`（同族"具名豁免"：单行、原话、事后逐字可核）与 `mark-produced` 的 `produced_only` ＋ `produced_only_marks[]`（"这不是默认形态"落库，且**留下判据所依据的数**）。**不用 `task_id`／`scope_deviation` 兼职**：那两格各有自己的语义，塞进去会让读账本的人分不清"任务名"与"豁免理由"；具名豁免必须是**可 grep 的独立字段**。

**读数口径与已知盲区**（不假装覆盖）：两个日期信号取**并集**——只认 `run_id` 日期段 ⇒ 无日期段的显式 id 全漏计；只认 `started_at` ⇒ 漏 `--start` 的 run 全漏计（**不传 `--start` 就能刷单**，闸门形同不存在）。**盲区**：id 无日期段**且**无 `started_at` 的 run 不计入——2026-10-03 时点读数：真账本两个信号都可派生（**以现跑为准**），故当日读数没有落在盲区里的项；UC-27 ⑧ 把这条盲区钉成断言。

**五条反向对照（真驱动 CLI 子进程，非注释）**：

| # | 对照 | 现跑结果 |
|---|---|---|
| ① | 超预算 ⇒ 拒绝且点名 | **真账本**（读数 10 ≥ 预算 6）：`rc=1`、`BUDGET-REFUSED` 点名读数／预算／逃生门用法／金额轴缺陷；拒绝后账本 127 条**零改动**（无新行、无 `-130`） |
| ② | 未超 ⇒ 正常登记 | 夹具账本（预算 2）：`0/2`、`1/2` 两笔均 `rc=0`，账本 1 → 2 条 |
| ③ | 逃生门 ⇒ 放行且账本留痕（现读） | **真账本** `run-2026-10-03-implementation-130`：`rc=0`；`budget_override_reason` **逐字**＝所传理由；`budget_override = {axis: dispatched_sessions_per_day, reading: 10, budget: 6, day: 2026-10-03, at: …}` |
| ④ | 正方向不误伤：当日第一笔必须放行 | 空账本首笔 `0/2 ⇒ rc=0`（不被"空账本/无历史"卡住） |
| ⑤ | 别的 role 也走同一判据 | `implementation` 与评审类 `doc-audit` **两个 role** 都被判 `BUDGET-REFUSED`（不是某一 role 的专属接线） |

**永久断言**：`verify/verify_agentops.py` 新增 **UC-27（18 条）**，断言数与 `verify/run_suite.py::BRANCH_ASSERTION_FLOORS` 的下限同批齐抬（**两处现值一律以现跑末行为准**；2026-10-03 时点读数见下节，**不得当作现值**）。仓规：下限只增不减、且等于现跑值；不抬 ⇒ 删掉这 18 条仍判绿＝本批白做。UC-27 覆盖：空账本第一笔／两个日期信号各自的计数／超预算拒绝＋点名＋**不半写**／别的 role／逃生门放行＋留痕逐字／理由过短拒绝／未超预算乱传逃生门拒绝／读数盲区／**只改数据文件即改判定**（2→4 放行、2 拒绝）／未配置预算判"未执行"／预算键三种坏法 fail-closed／真仓文件契约（只核键与类型，**不核取值**——预算值属用户政策，改它不该让本判据变红）。

**门槛末行**（下列每行都是 **2026-10-03 时点读数**，**不得当作现值**；现值一律由各命令现跑产生）：

- `py_compile scripts/agent-ops.py verify/verify_agentops.py verify/run_suite.py` ⇒ `exit=0`（2026-10-03）
- `verify/verify_agentops.py --selftest` ⇒ 通过档判决句（2026-10-03：`ALL PASS (198 assertions)`；**以现跑末行为准**）
- `verify/run_suite.py --tier offline` ⇒ 全绿（2026-10-03 读数：26 个脚本；**以现跑为准**）。首轮**曾红 1/26**：`verify_artifact_paths.py` 判 `verify/verify_agentops.py` 动态写盘目标超上限——**是本批自己引起的**（新夹具把预算文件写到函数参数上）；改成字面量落点后回到上限内，复跑该项转绿（2026-10-03）。该红**如实记**，不当作"环境问题"
- `verify/verify_lint.py` ⇒ A/B 级零发现、C 级棘轮未顶破（2026-10-03：E501 计数较批前**净 −1**；现值以现跑 EVIDENCE 行为准）
- `verify/verify_matrix.py derive` ＋ `check` ⇒ 派生与入库一致（2026-10-03；脚本数以现跑为准。**改了 `VERIFY_META` 故同批 derive**）
- `verify/verify_no_policy_hardcode.py` ⇒ 无政策硬编码（2026-10-03；扫描文件数以现跑为准）
- `scripts/spend-report.py --check`（venv）⇒ 仍 **3 项 OVER**（2026-10-03 时点读数：派单会话数 20／预算 6、主代理 output 68470／50000、当日 36.64 CNY／12.0；**以现跑为准**）——**这正是"度量仪不是闸门"的现状**：本批新增的阻断轴**不是它**，而是账本读数；金额轴的不阻断与原因已写进拒绝文案。
- **本批自因的两次红（如实记、逐条归因，不笼统归给环境）**：① `verify_artifact_paths.py`（2026-10-03）——新夹具把预算文件写到**函数参数**上 ⇒ 动态写盘目标顶破上限；改成字面量落点后转绿。② `verify_derived_numbers.py`（2026-10-03）——本节第一版把闸门末行读数**原样抄进文档**（"派生数字不得手抄"）⇒ 改成"复现命令 ＋ 时点读数（声明不得当作现值）"后转绿。两处**都是本批引起的**，与缺依赖/网络无关。

**本批未做／未决（如实记）**：

- **没有改度量仪**（`scripts/spend-report.py` 的作用域缺陷归 `A-COST` 卡）；**没有上调任何现值预算**（`budget` 段三值逐字未动）；**没有 `git add/commit/push`**。
- **逃生门的滥用面**：`--over-budget` 只要求"≥下限字符的理由"，闸门**判不了理由真假**——它与 `--allow-degenerate`／`retract --reason` 同族，靠"必留痕 + 事后可核"约束，不靠自动判真。**未决**：是否需要"同一日逃生门次数上限"（本批不做，避免与 `A-COST` 卡抢设计）。
- **未配置预算档的口径**：预算文件缺失时判"未执行"并放行（否则隔离账本被卡死），代价是"删掉文件即可让闸门不生效"。**对冲**＝UC-27 ⑫ 对真仓文件钉了契约（删/改坏键 ⇒ 该断言变红），但这是**仓库级**对冲，不是**机器级**。**未决**：是否要改成"真仓缺失即 fail-closed、仅 `AGENT_OPS_DIR` 重定向档放行"。
