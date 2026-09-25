# D2/D3 独立审核报告（合成）——事实、分级发现、行动链

> 生成：**2026-09-25（UTC+8）**｜主代理（本会话）｜依据：〇查 `run-2026-09-25-impact-assessment-065`、一查 `run-2026-09-24-doc-audit-066`（✅ 终报）、二查 `run-2026-09-25-code-review-067`（🔄 中期已给 F1/F2）、主代理独立复算 M1~M6。
> **结论绑定 sha**：被审对象 = `092a2f78..9ffc108d`（30 提交 / 137 文件 / +6231−325）。审计期间 HEAD 漂移（`7e188eb`→`9bf2db1`→`639decf`→`ac42f7b`→`08a0bd1`，均为本会话 docs(pm) 提交，**在被审范围之外**）→ 各条发现以**取得证据时的 sha** 为准。
> **本文件不复制 run 报告全文**：细节在 `agents/runs/<run_id>/*.report.md`；本文件只做**合成、定性、点数更正与行动链**。
> ⚠️ **时点记录（2026-09-25 一查 `run-2026-09-25-doc-audit-070` finding 1/2 后补标注）**：本文所有"实测"数字（卡数 `96`、字节、断言数、脚本数、C 级条数）都是**取证时点的读数**，会随仓库推进漂移（同窗口内卡数即由 96 → 97）。引用时**一律现跑对应命令**（`scripts/card-inventory.py` / `verify_lint.py` 的 `[report-only C 级]`、`EVIDENCE:` 行 / 套件末行），**不得把本文数字当现值**——本文自己的 M-c 就是这条教训的实例。

---

## 0. 一句话结论

被审的 D2/D3 **工程产物基本达标**（迁移守恒经独立复算成立、三不变量闸门真实落地且反向对照有效、套件 19/19 本机全绿、卡-文档拓扑干净），但**过程与账目存在 1 条 critical + 8 条 major**：其中最严重的是"**用一条不成立的事实（CI #206 闭环 ⑥）去支撑减点**"，它直接改变了 Sprint 的剩余点数口径。

---

## 1. 现状快照（可复现命令）

| 项 | 值 | 命令 |
|---|---|---|
| 分支 / HEAD | `windows` / `08a0bd1`（被审范围止于 `9ffc108`） | `git log --oneline -1` |
| 未推提交 | **21**（对方 15 + 本会话审计相关 6） | `git rev-list --count origin/windows..HEAD` |
| 工作树 | 干净（审计全程未污染） | `git status --porcelain` |
| 离线套件 | **SUITE PASSED（19 scripts）**，187.6s，¥0 | `.venv\Scripts\python.exe verify\run_suite.py --tier offline` |
| 矩阵 | **50 脚本 CHECK OK**（offline 19 / gui 21 / network 10） | `verify/verify_matrix.py check` |
| 卡库存 | 时点读数 **96 卡 / 4 阶段**，与 `agents/runtime/tg14-baseline.json` 一致（**现值现跑**；同窗口内已漂到 97，见本文顶部时点标注） | `scripts/card-inventory.py` |
| 账本 | **67** 条 run；`closure_problems()` 为空 | `agent_policy.closure_problems()` |
| CI | 上一批已推批次的 CI #206 = success（head `f2d37ab`）；**21 个未推提交从未跑过 CI** | GitHub Actions |

---

## 2. 分级发现（合并一查 / 二查 / 主代理）

### 2.1 critical（必修，1 条）

| # | 发现 | 证据 | 处置 |
|---|---|---|---|
| **C1** | **减点依据为假**：Sprint-17 §4 的 D3 行称 `TG-15`⑥"已于 D3 由 CI #206 success 闭环"，据此减 2.5 点（燃尽 D3→12）；而 §5 第 6 条自己写着 ⑥"**已裁定顺延（不是完成）**" | 一查实测：`grep close-sync\|fail-on-unowned .github/workflows/ci.yml` **零命中**；唯一覆盖检查块以**真实锚点**为门（`ci.yml:73` 正则），而 Sprint 锚点仍为 `待填`（§9.1:166）→ **该步骤被跳过**。主代理复核同上 | ✅ **已改**：§4 D3 行更正为 **14.5 点**（`TG-15` 2.5 点**不再减**，遵用户 2026-09-25"不减点、改扣分条件"），并留更正说明与扣分条件 |

### 2.2 major（必修，8 条）

| # | 发现 | 证据（sha 绑定） | 最小修法 |
|---|---|---|---|
| **M-a** | `verify_md_tables.py` 棘轮**对新增缺陷失明**（不只"缺到期日"）：只做路径比较，基线文件内**任何数量**的缺陷全被吸收 | 一查临时副本：12 处 → rc=0；**+1 处全新缺陷 → 13 处仍 rc=0 "MD-TABLE PASS"**；二查独立注入 **200 处**仍 PASS；对照：向非基线文件注入 → rc=1。与 `policy.json:56`"新改动一律判失败"矛盾 | `md_table_legacy_files.files` 由路径列表改 **`{路径: 缺陷上限}`**（实测 15 = sprint-15 12 + sprint-16 1 + acceptance 1 + sprint-6 1，可复现）→ `len(found) > cap` 即 FAIL；加 `review_by` 过期即 FAIL（约 13 行） |
| **M-b** | **短 sha 锚点被静默丢弃**：`CoverageWindow.covers()` 要求 40 位完整 sha；短 sha → `covers()` 恒 False → 该 run **贡献 0 覆盖** | 二查实测：真账本 `window_problems()` 点名 `run-2026-09-24-code-review-065 的 coverage_anchor='092a2f78' 不是完整 40 位 sha → 静默丢弃`；本次两个审计 run（066/067）都因此 `cov` 无效；收尾后 C3 需为 `092a2f78..HEAD`（33 提交）找归属，实测现 `unowned` **15** 条（含迁移提交 `8d759512`）→ C3 必红。**归因：主代理在 prompt 里给了短 sha** | `register` 侧 `git rev-parse --verify <anchor>^{commit}` **规范化** + 解析失败 **fail-closed**；为 `finish`/新子命令开**受控回填口**（`update`/`finish` 现均无 `--coverage-anchor`，账本有完整性哈希禁手改）；反向对照＝短 sha / 不存在 sha 必须被拒。完整 sha：`092a2f784c9749126dc0f7483fe78ba721f424d0` |
| **M-c** | **手抄派生事实已漂移**：卡数 `95`（§3/§7/§8 三处）vs 实测 **96 卡 / 105580 B**；lint C 级"现行实测 **1858**" vs 实测 **1998**（D103 181→191、E501 1624→1754；**两个数都是本审核时点读数**，现值以 `verify_lint.py` 报告行现跑为准）；"SUITE PASSED（**17** scripts）" vs 实测 **19** | 一查：`card-inventory.py` → 96/4/1 == `tg14-baseline.json` = 96；同处政策还写着"文档不写死数字" | 三处数字改为**引用工具输出**（`card-inventory.py` / `verify_lint.py` 报告行 / 套件输出），不再手抄；并入 TG-12（派生事实 SSOT） |
| **M-d** | `verify_card_index.py --body-threshold` 是**死旋钮**（贯穿 run/check_phase 但从未被读取；实际用 policy 的 `BODY_PREFIX_CHARS`/`MIN_FINGERPRINT_CHARS`） | 一查代码核对 | 删除参数与文档行，或真正接线（二选一，且加"每个参数都有消费点"的断言，防再犯） |
| **M-e** | **strict 判据从未在 CI 执行**：`verify_card_index.py` 默认宽松档（只跑 ①②⑤），`--strict` 才跑 ③④；offline 套件以**无参**调用 | 主代理实测 M3 + 一查 D 项（`--check --strict` 在真实数据上 **PASS**） | 迁移已宣称完成 → 默认档翻 strict（或 CI 显式 `--strict`）；并把 `md_tables`/`no_policy_hardcode`/`card_index`/`lint` 在 CI 中**显式**调用（现仅 `close_readiness` 显式） |
| **M-f** | **CI 只显式接了一个闸门**：`ci.yml` 仅调用 `verify_close_readiness.py`；其余四个新闸门只经套件**默认参数**间接运行 | 主代理 M4 | 同上；并在 CI 里打印各闸门**实际参数**（可核"跑的是哪一档"） |
| **M-g** | **账本 id ↔ 目录名不一致（新类型）**：`register` 自动 run-id 用 **UTC** 日期，目录/文档用 **UTC+8** → 实测 `run-2026-09-24-doc-audit-066`（账本）↔ `run-2026-09-25-doc-audit-066`（目录）；另有 1 条 `cancelled` 孤儿 `run-2026-09-24-code-review-065`（无目录） | 主代理 M2/M5（`dirs_without_record=4`、`records_without_dir=3`） | run-id 生成改**网络时间口径**或强制显式；加"账本 id ↔ 目录名一致"断言（linkage），并入 TG-13/TG-17 |
| **M-h** | **账本测量缺陷量化**（一查未测、主代理测）：`succeeded` 但 `output_chars=0` → **12** 条；评审类 run 无 `result_files` → **13** 条；`started_at == ended_at` → **3** 条 | 主代理 M1（`registry_audit.py`，67 条全量） | 并入 `TG-13` 卡内证据（其卡文已有同类描述，这里是刷新后的量化） |

### 2.3 minor / nit（不阻断，入排队）

一查给出 5 条：`tg14-baseline.json` 的 `_note` 日期错 2 天；`1-WORKFLOW.MD` 的 `## 3.1` 位置/层级错（跑到 §4.4 之后且吞并 :248/:250-254/:266/:274）；两份 09-23 命名的事件文档实际 09-25 落盘且无落盘日期（与 §3 日期判据冲突，需豁免或补行）；`:73` 引用了不存在的政策键 `md_table_targets`（真实为 `md_table_docs`+`md_table_globs`）；`verify_card_index.py` 文档写了不存在的 `--selftest`。

### 2.4 经独立复核**成立**的正面项（同样重要）

1. **迁移守恒**：主代理独立复算（不碰对方核对器）96 行卡 / **453 单元格**归一化子串守恒，唯一命中是非卡 `—` 行；一查另行复核"迁移时点字节与卡数"（`git ls-tree -r -l 7eead16` → 95 卡 / 99700 B；backlog 6878/3039/7155/11720）**在声称时点成立**（漂移发生在之后）。
2. **闸门真实且反向对照有效**：`verify_close_readiness.py`（含 7 条**从 `fanout.json` 自动生成**的变异）、`verify_card_index.py`（A~E 变异全 FAIL、合法计划表行 PASS）、`verify_no_policy_hardcode.py` 三者**各自现跑末行 `ALL PASS (<N> assertions)`**（**本文不写断言数**：此处原有 23 / 8 / 13 三个读数，2026-09-25 一查 finding 2 实测均已过期）；**卡-文档拓扑干净**（卡文件 ↔ 索引行一一对应，文件数现跑为准）。
3. **TG-15 数据化确实落地**：`UC-15`（新增角色只改 spec 数据即生效）、`UC-16`（缺 `scope_required` → CLI fail-closed）、C3-T 例外表三条规则（短 sha/通配/缺理由 → FAIL）。
4. **本机全序列套件 19/19**、矩阵 50 一致、`closure_problems()` 为空。
5. **064 的 critical 确实已修**（二查确认）。

---

## 3. 更正后的账（用户决策依赖此表）

| 项 | 原记 | **更正后** | 依据 |
|---|---|---|---|
| `TG-15` 2.5 点 | D3 减 2.5（因"⑥ 由 CI #206 闭环"） | **不减**（改为**扣分条件**：棘轮上限制+到期未闭环扣 0.5；审核 critical/major 未闭环按级别继续扣） | C1（减点依据为假）+ 用户 2026-09-25 决定 |
| Sprint-17 剩余 | 12 点 | **14.5 点**（`TG-6`3+`TG-13`2+`TG-8`2+`TG-9`1+`F-AC13`2+`F-AC14`2 = 12 ＋`TG-15` 2.5） | 同上 |
| 治理模式 | 待定 | **已由 §2.2.1 自动触发**（R1 本 Sprint **5 次** ≥2） | 分析文档 §7 |
| 未推提交 | 15 | **21**（含审计期间 6 条 docs(pm)） | 现状快照 §1 |

---

## 4. 行动链（依赖排序；每步都要"反向对照 + 更新 §3/§7/§10/燃尽 + 显式路径提交"）

| 步 | 动作 | 依赖 | 完成判据 |
|---|---|---|---|
| **A1** | 修 **M-b/N5**（锚点规范化 + fail-closed + 受控回填口） | 无 | ✅ **已完成（2026-09-25）**：`register --coverage-anchor` 与 `finish --covers-through` 走 `_resolve_sha()`（`git rev-parse --verify <v>^{commit}` → 必须 40 位十六进制），解析失败 **`COVERAGE-ANCHOR-ERROR` fail-closed**；新增受控回填子命令 `set-anchor <run_id> --anchor <sha> --reason <≥10 字符>`，每次回填追写 `anchor_backfills`（可审计）。**反向对照**：`verify_agentops.py` **UC-17 四条**（短 sha **被规范化**为 40 位 / 无法解析的 sha **被拒** / 回填缺理由**被拒** / 回填成功且留痕）→ **ALL PASS（61 断言）**。**回填实测**：`doc-audit-066`、`code-review-067`、`code-review-065(cancelled)` 三条锚点由 `092a2f78` → `092a2f784c9749126dc0f7483fe78ba721f424d0`（各 `backfills=1`）；回填后 `verify_close_readiness --sprint sprint-17` **不再输出"静默丢弃/不是完整 sha"** → 窗口恢复有效 |
| **A2** | 修 **M-a**（棘轮上限制 + `review_by`） | 无 | 基线文件注入 1 处新缺陷 → FAIL；正常 → PASS |
| **A3** | 修 **M-e/M-f**（`card_index` 默认 strict；CI 显式调用四个闸门并打印实际参数） | 无 | CI 日志可见各闸门档位；strict 判据在 CI 运行 |
| **A4** | 收口 **M-c**（三处数字改引用工具输出） | 无 | `grep` 无手抄的 95/1858/17 |
| **A5** | 收口 **M-d / M-g / M-h** 与 §2.3 minors | A1（M-g 同族） | 死旋钮删除或接线；账本 id ↔ 目录一致断言；minor 全清或显式延期并说明 |
| **A6** | 二查终报并入本文件（分节 + sha 绑定） | 二查完成 | 本文件出现二查终报分节 |
| **A7** | 治理模式**必修 + 退出判据**成文（`A-M12` 工具约束必须拦住 5 次 R1 的输入；棘轮闭环；用户二次确认） | A2 | 清单交用户二次确认 |
| **A8** | 回填 TG-13 卡内证据（M1/M5/M-h 量化）与 TG-17（覆盖窗口语义：短 sha、UTC vs UTC+8、〇查不认领内容覆盖） | A1 | 两张卡内证据刷新 |
| **A9** | **决策包**交用户：P-a 推 21 提交 / P-b 15 处历史缺陷 / P-c A-M12 点数 / P-d 剩余 **14.5** 点排期（三选一方案） | A1~A4（拿到 CI 与闸门事实后再问） | 用户裁定 |

---

## 5. 未核实（如实登记）

① CI #206 的**步骤日志**（无 GitHub 访问；一查以"接线缺失 + 锚点门跳过"两条即可否证 §4 的说法，但未读日志本身）；② 迁移**逐字段**守恒的 102/117/36/231 分项（一查只重算了卡数/字节/backlog 体积；主代理做的是归一化子串守恒，非逐字段）；③ `verify_local_dir.py` 的 flaky 复现（审计期间刻意未跑套件以外的写状态操作）；④ 被审范围外的 6 条 docs(pm) 提交未审。

---

## 6. 二查终报（`run-2026-09-25-code-review-067`，✅ succeeded，`rounds=2`，`covers_through=4f2fcc15`）

> 该 run 首个 `register` 被 CLI 自动编号成 `run-2026-09-24-code-review-065`（**UTC 日期 + 撞号**，与 M-g 同源）→ 已用显式 `--run-id` 重登记，并把误建行置 `cancelled`。

### 6.1 major（7 条；**前 4 条今天就放行真实缺陷，或可被一次数据编辑静音**）

| # | 发现 | 证据 | 必修 |
|---|---|---|---|
| **N1** | **表格闸门扫描集漏 29/160 个相关文档**：阶段级 `.MD` 从不自动纳入（含本轮新增的 2 份"编辑越界"事故反例） | 漏项里**今天就藏着 7 处真实缺陷**（`agents-infra/2026-09-21-a-m11-from-runs.MD:102,:178`、`architecture.MD:251`、`tg11-retro.MD:42,:43`、`lint-deps-security-check.search-only-draft.MD:62,:79`），闸门却打印 `MD-TABLE PASS` | **是**（政策侧扩 glob + 修那 7 处） |
| **N2** | 棘轮**按文件**豁免（同 M-a） | 注入 **200 处**新缺陷仍 rc=0；非基线对照 rc=1 | **是**（`{path: 上限}` + `review_by`，~13 行） |
| **N3** | `verify_close_readiness.py:131-132` target 判据是**子串匹配** → `branch:windows-backup`、`OLD-working-tree-JUNK`、`branch:mainline` **全 PASS** | 真 policy + 合成 run 实测 | **是（1 行）** |
| **N4** | `verify_no_policy_hardcode.py:292` 台账加**一条无校验豁免**（`categories:["policy"]`）即 rc 0 `ALL PASS(13)`，同一屏还打印"无政策硬编码 clean" | 与台账自述"绝不整文件豁免"冲突 | **是**（豁免须校验：类别白名单 + 理由 + 文件级最小化） |
| **N5** | `agent-ops.py:373` `--coverage-anchor` **无 sha 规范化** → **066/067 两个审计 run 的覆盖窗口已被静默作废**（= M-b，主代理造成） | 短 sha → `covers()` 恒 False；登记后无 CLI 可修 | **是**（3 行 + 回填口） |
| **N6** | `verify_close_readiness.py:211-215` §9↔账本 `window_start` **取自 §9 自己** → **删掉最早几条 run 即 PASS**；`:257-261` 只比对 `scope_source`，**role/target 写错也 PASS** | 一查/二查一致 | **是** |
| **N7** | `verify_card_index.py:321-323` 默认（套件）模式真数据只 **WARN** → **"SUITE PASSED" 不能证明卡索引一致**；④ 判据可用 **≥61 字符填充**规避 | 同一坏数据 `--check` rc=1 / 无参数 rc=0+WARN | **是** |

### 6.2 minor（3 条）

`N8` "空集/缺失 = PASS"一族（`verify_md_tables.py:126-128,151`：空扫描集 rc=0，且"N 个文件"数的是**请求数**不是解析数；`--no-coverage` 顺带删掉锚点检查 `:273-277,616`；`card_index:220-221` 无 backlog 阶段静默跳过）；`N9` `close_readiness` 真数据 **FAIL(98 项 = 63 linkage + 34 C1 + 1 C3)** 无"§9 未填"诊断、`parse_sprint` 不容忍缩进、C1 不执行政策 `scope_min_deviation_chars=10`（其中 34 C1 属 `TG-17` 已开卡的顺延项）；`N10` **`agent-ops.py:464` `finish --result-file` 把报告 LF 静默改写成 CRLF**（实测 35721→35913 B / CRLF 192 行；未过 `finish` 的 `context.md` 仍 0 CRLF）——同族修复在 `2206f376` 做过而漏此处。

### 6.3 R1~R5 与闸门可信度（二查的判定）

| 项 | 结论 |
|---|---|
| **R1 覆盖枚举** | `policy.json` glob 展开 vs 文件系统**双向差集 + 逐文件实跑**：**131 = 128 docs + 3**；相关集 **160**，**漏 29**，其中 **7 处真缺陷**；卡覆盖 = **全部卡（卡数按当时读数，现值现跑 `card-inventory.py`）**；`card_index` 阶段动态枚举覆盖 **4/4**；`no_policy_hardcode` 只扫 **39/182** 个 `.py` |
| **R2 迁移守恒** | 二查自建 git 解析器（blob sha1 复核）：**守恒成立** —— **476/476** 非空非卡号单元格**字节级精确命中**、**0 丢失**、**反向 0 自造**、无删/改名、0 BOM/0 CRLF/0 乱码。但 **主代理的 `453` 不可复现**（现测得 454），逐阶段计数口径互不一致；P3 字节 `6962` 实为 **`7155`**（一查亦报此） |
| **R3 棘轮** | 判 **major**：注入 200 处仍 rc=0 → **补到期日也不解决**；最小修法 = `{path: 缺陷上限}` + `review_by` |
| **R4 账本↔产物** | 062/063/064 目录与 `<role>.report.md` 命名一致，但 `result_files=[]`（**无机器可验链接**）；`cov=` 窗口**全不覆盖自称区间**（0/6、0/9、0/9；065 为 0/30 空区间）。正面：064 那条 critical（空区间静默通过）**已修好且真数据会红** |
| **R5 断言可信度** | `md_tables` = **部分可信**（判据①真且锐利——自造 ragged 表 rc=1 带行号；判据②`unescaped=raw-escaped` 后自比是**恒真式、分支不可达**，故"两条判据"实际只有一条）；`card_index` = **`--check` 可信、套件默认模式恒真**；`no_policy_hardcode` = **主判据真**，但**豁免台账必须视为可信输入**；`close_readiness` = **C1/C2/C3 核心真**，外围（§9 互联、target 子串、deviation 阈值）不严 |
| **说服二查的三个变异** | ① 棘轮 **200 处注入仍 PASS**；② **同一坏数据 `--check` rc=1 vs 无参数 rc=0**（card_index）；③ **一条豁免把 rc=1 变 rc=0 且打印 clean**（hardcode） |

### 6.4 对**本 §4 行动链**的增补（据终报重排）

- **A1 扩**：除短 sha 规范化，追加 **N5 回填口**；并明确 066/067 的窗口处置（补窗口 **或** 按 C3-T 逐条 sha 钉死例外）。
- **A2 扩**：棘轮改上限制 + `review_by`（N2/R3），并复核"N 个文件"计数口径（N8）。
- **A3 扩**：`card_index` 套件模式**必须判失败**（N7），不只翻 strict；CI 打印各闸门**实际档位与参数**。
- **新 A10**：**闸门扫描集双向差集检查**（N1）——把"相关文档集合"变成政策驱动的枚举 + 与文件系统做双向差集，并对缺失项 fail-closed；顺带修那 **7 处真缺陷**。
- **新 A11**：**target 判据改精确匹配**（N3）+ **§9 互联自洽**（N6：`window_start` 不得取自被校验文档自身；`role/target` 一并比对）+ **豁免台账校验**（N4）。
- **新 A12**：**`finish --result-file` 的 LF→CRLF 静默改写**（N10）——与 D1 的 EOL 事故同族，必须修 + 加断言。
- **`no_policy_hardcode` 覆盖 39/182 `.py`**（R1）→ 并入 A10 的"扫描集双向差集"一并收口。

> **NOTE（2026-09-25）**：账本**没有"实现类"role** —— 执行治理卡子代理无法在不污染 C1 判定域的前提下登记 run（强行用 code-review role 会让关闭闸门多点名"§9 未登记"）。→ 归 **TG-17**（C1 判定域）输入。

