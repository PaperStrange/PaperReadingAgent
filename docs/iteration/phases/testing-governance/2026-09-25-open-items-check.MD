# 退出后"未实现目标"逐条核查（验证型批次，2026-09-25 UTC+8）

> 来源清单：本目录 `2026-09-25-governance-exit-evidence.MD`「✅ 用户退出确认」1~5 + 「限制与未闭环」1~5。
> 采集口径：仓库 `D:\All-Downloads\PaperReading\PaperReading-Windows`（branch `windows`），解释器 `.venv\Scripts\python.exe`（Python 3.13.2）。
> **本批次不跑 `verify/run_suite.py`**（另一批可能并发跑闸门，避免端口冲突），只跑**单条**闸门。
> HEAD 在核查期间被并发批推进：起点 `107a7ab`（未推 **40**）→ 终点 `c632274`（未推 **41**，`git rev-list --count origin/windows..HEAD`）。
> **重要前提**：核查时工作树**脏**——`agents/policy.json`、`verify/agent_policy.py` 有未提交改动（并发批 TG-6，mtime 12:35:32/12:35:38，sha256 前缀 `C48CBF0046DC7096` / `B6BE4BDDDC68A1EA`），收尾时 `verify/verify_lint.py` 亦被同一并发批改动。故本报告的本机结论 = **工作树等价**，不等于 HEAD `c632274` 等价；CI 检的是提交态。

> ⚠️ **本文是时点快照，且部分结论已被同窗口后续提交取代——引用前先读本节**（2026-09-25 一查 `run-2026-09-25-doc-audit-070` finding 6 要求补此标注）。
> - **快照时点**：2026-09-25（UTC+8），工作树等价于 HEAD `c632274`（本文末节第 9 条自陈"工作树脏"）。
> - **已被取代**：下方 O2 的结论"真数据 **rc=1 / 46 项**（C1 34 + linkage 11 + C3 1）…**34 项 C1 历史域清不掉**"**已不成立**——同日晚些的 close-blocker 批（`TG-17` B1~B4）把 C1 的判定域收窄为**账本推导的关闭窗口**，历史域不再计入。**现值请现跑**（本文不写现值）：
>   `.venv\Scripts\python.exe verify\verify_close_readiness.py --sprint docs\iteration\sprint\2026-09-21-sprint-17.md`
> - **仍成立**：O1（CI 未在本批提交上实跑；锚点未声明前关闭前置块选择器命中 0 份 ⇒ 该步空跑）、O3（`A-M12` 判据④无度量口径）、O4（实现类子代理无账本 role）、O5（`TG-15` 2.5 点、open majors = 0）。
> - **本文所有数字都只是"时点读数"**，仅在上述时点成立；**现值一律以文中给出的命令现跑输出为准**。本 Sprint 最实的教训正是"手抄派生数字即制造漂移"（同一批闸门在同日文档里并存 3~4 个读数，见 `run-2026-09-25-doc-audit-070` finding 1/2）。
> - 取代标注的写法参照本仓既有正例：`docs/iteration/pre-research/tech/2026-09-21-lint-deps-security-check.search-only-draft.MD:3`。

**一句结论**：O1 的"CI 从未实跑"**依然成立**（且比记录更严重：关闭前置块当前命中 **0** 份 Sprint 文档，推上去也不执行该闸门）；O2 真数据 **rc=1 / 46 项**（C1 34 + linkage 11 + C3 1），填 §9 只能清 **12** 项、**34 项 C1 历史域清不掉**；O3 判据④**已写但无度量方法**；O4 "实现类子代理无账本 role" **成立且 TG-17 卡内并未收录该输入**；O5 审计 7 条 major **逐条可核为已闭环（open majors = 0）**，但 `N9` 两个子项仍开。

---

## O1 CI 从未实跑的影响面

**claim**：本批 40+ 提交从未推过 ⇒ `.github/workflows/ci.yml` 的 `verify` 作业**全部步骤**都没在本批提交上跑过；本机绿不能替代。（ci.yml 只对 `push: [main, windows]` / PR 触发；本地无任何 CI 记录。）

**measurement**（`.github/workflows/ci.yml` `verify` 作业逐步，按文件顺序）：

| # | CI 步骤（原样） | 本批跑过 | 本机等价实测 |
|---|---|---|---|
| 1 | `actions/checkout@v4` | 否 | —（未设 `fetch-depth`，默认 depth=1 浅克隆） |
| 2 | `setup-python` python-version 3.13 | 否 | `.venv` = Python **3.13.2**（次版本一致） |
| 3 | pip install fhlmi/litellm + 3 个 `-e` + `requirements-windows.txt` | 否 | 未跑（本批禁止安装）；`requirements-windows.txt` 含 `ruff==0.14.4` |
| 4 | `choco install graphviz -y` | 否 | `Get-Command dot` **无输出** ⇒ 本机无 dot |
| 5 | `actions/setup-node@v4` node 22 | 否 | node **v26.8.2** / npm **12.0.2**（大版本不同） |
| 6 | `python verify/run_suite.py --tier offline` | 否 | **按用户约束未跑**；以第 9 行 6 条独立闸门替代 |
| 7 | `python verify/verify_matrix.py check` | 否 | rc=0 → `CHECK OK: <N> 脚本与 TEST-MATRIX.MD 一致`（**N 是时点读数，现值现跑该命令**） |
| 8 | 关闭前置块（只对声明真锚点的 Sprint 文档） | 否 | 选择器实跑：**`checked 0 sprint doc(s) declaring a real anchor`**（`Get-ChildItem docs/iteration/sprint/*sprint-*.md` + 同一正则） |
| 9 | 显式档四闸门 + `structure-guard.py --replay` | 否 | 5 条全 rc=0，见下表 |
| 10 | `npm ci` + `npm run build`（reactflow frontend） | 否 | `npm ci` rc=**0**；`npm run build` rc=**0**；产物 `dist` **3 文件 / 356,981 B**（index.html 412 + css 21,293 + js 335,276） |
| 11 | `npm ci --ignore-scripts` + `npm run build`（agents-dashboard） | 否 | `npm ci` rc=**0**（`added 98 packages ... in 20s`，registry 可联网）；`npm run build` rc=**0**；`.next` **711 文件 / 324,732,975 B**（含构建缓存） |

第 9 步逐条实测（末行即断言数，均 rc=0）：

| 命令 | 实测末行 |
|---|---|
| `verify_card_index.py --check --strict` | `ALL PASS (9 assertions)` |
| `verify_md_tables.py` | `MD-TABLE PASS（162 个文件解析通过；其中 4 个历史文件走棘轮基线）`；`应扫 162 / 实扫 162 → 一致`（本报告落盘后复跑同命令为 **163**——集合是政策驱动的动态枚举，新增文档自动纳入） |
| `verify_no_policy_hardcode.py` | `ALL PASS (22 assertions)` |
| `verify_lint.py` | 末行 `ALL PASS (N assertions)` + `EVIDENCE:` 行（**N 与时点 C 级计数只是时点读数，现值现跑**）；`[tool] ruff 0.14.4`；A/B 级全仓 0 条，C 级只报基线 |
| `scripts/structure-guard.py --replay` | `ALL PASS (64 assertions)`；`真文件零改动…162 份文档 sha256=f05d4d37a69e4638…` |

**verdict**：**CI 面仍未闭环，且有两个新发现的收紧点**：① 第 8 步在本 Sprint 填锚点前**恒为空跑**（命中 0 份）——"CI 已接关闭闸门"目前是**未生效接线**；② `actions/checkout@v4` 默认 `fetch-depth: 1`，而关闭闸门 C3 依赖 `git rev-list <锚点>..HEAD`（`verify/agent_policy.py:679` 起，"anchor 非法时抛错，不静默当空"）⇒ 填了真锚点后 CI 首次实跑该分支时，浅克隆下**可能直接报错**（本机无浅克隆，未能实测）。

**what would close it**：推 `windows` 后读 CI 该次 run 的逐步日志，把 head sha + 结论回填 §9/§9.2；并对第 8 步做一次**带真锚点的预演**（建议先 `actions/checkout` 加 `fetch-depth: 0`，否则浅克隆风险始终存在）。

## O2 `verify_close_readiness.py` 真数据模式

**claim**：真数据模式今日 FAIL（三查锚点属关闭期动作）。

**measurement**：`\.venv\Scripts\python.exe verify\verify_close_readiness.py --sprint docs/iteration/sprint/2026-09-21-sprint-17.md` → rc=**1**，首行 `CLOSE-READINESS FAIL（46 项）：`。

| 类别 | 条数 | 样例 | 填 §9 后 |
|---|---|---|---|
| `[C1]` 评审类 run 无 scope 声明 | **34** | `run-2026-08-30-code-review-001` … 最新 `run-2026-09-21-code-review-060` | **清不掉** |
| `[linkage]` 账本有 run 但 §9 run 表未登记 | **11** | 058 / 060 / 061 / 062 / 063 / 064 / 065(impact) / 065(code-review) / 066 / 067 / **068** | **清得掉** |
| `[C3]` 未声明三查锚点 | **1** | `[C3] 未声明三查锚点（三查锚点: <sha>）→ 无法判定三查是否失效` | **清得掉** |

（分类由同一次输出的行分组计数得出；`N9` 记的 `98 项 = 63 linkage + 34 C1 + 1 C3` 现已降为 **46 = 11 + 34 + 1**——linkage 减少是 N6 修复的副作用：窗口起点改由账本推导 `ledger_close_window()`，不再取自 §9 自身。）

**verdict**：**真数据仍 FAIL**，且**不是一个 §9 能关掉的门**：填结构化 run 表（11 行）+ `三查锚点: <sha>` 只清 **12** 项，**34 项 C1 原样留下**（`check_c1()` 遍历全部 68 条 run，无窗口过滤 ⇒ 与 `TG-17` ② "C1 判定域＝全账本"完全一致，TG-17 卡内自述的"永久 FAIL 34 条"与本次实测数字**逐条吻合**）。
补注：锚点若填成 `HEAD` 会触发另一条自检断言"空区间 ≠ 通过"（锚点==HEAD 视为未验证）；锚点应指向二查实际覆盖到的最后提交，且其后每个提交都要有归属。

**what would close it**：D 步回填 §9.1 run 表 + 真锚点（清 12 项）；`TG-17` ② 收窄 C1 判定域到本次关闭窗口并在反向对照下证明"窗口内缺声明仍 FAIL"（清剩余 34 项）。

## O3 `A-M12` 判据④（下 Sprint 度量项）

**claim**：判据④（下 Sprint 同族事故 ≤1、目标 0）只能 Sprint-18 测。

**measurement**：`docs/iteration/phases/agents-infra/cards/A-M12.md`：判据**写在第 66~68 行**——"④ 下一 Sprint 同型事故 ≤1（目标 0）且有数据（**待度量**——本卡唯一非工具项）"，第 63~64 行"验收判据 ④ …属**度量项**，需 Sprint-18 结束时统计——本卡交付时点无法自证"。全卡（69 行）**没有任何**度量口径：未指定数据源（如 Sprint-18 §10 事故行）、未定义"同型"（R1 类的分类键/触发动作特征）、未定计数窗口（Sprint-18 起止日期）、未定登记义务（structure-guard 每次 `[FAIL]` 是否必须落一行事故）、未给可复算命令。第 17 行只在**来源**里引 Sprint-17 §10 的 R1-1~R1-5（历史 5 次），不是 Sprint-18 的测量源。

**verdict**：**判据存在，但不可度量**——Sprint-18 结束时任何人都无法独立复算这个 ≤1，判据退化为叙事。

**what would close it**：在 A-M12 §证据 第 5 条补一行度量口径，至少含四要素：数据源（Sprint-18 §10 中带 R1 族标记的事故行）+ 计数命令/选择器 + 窗口（Sprint-18 首末日期）+ 登记义务（每次被拦下的近似事故都要落行，否则"没记录"会被当成 0）。本报告不代改该卡。

## O4 实现类子代理无账本 role

**claim**：账本没有"实现类"role，强行登记会污染 C1 判定域；归 `TG-17` 输入。

**measurement**：`agents/policy.json` 无 role 白名单键；role 集合由 spec frontmatter 的 `scope_required` 派生（`scripts/agent-ops.py:100-102`）。`agents/functions/` 共 8 个 spec：

| role | `scope_required` | 是否评审类（C1 管辖） |
|---|---|---|
| code-review / doc-audit / agent-onboarding-review | **true** | **是**（3 个） |
| impact-assessment / lessons-learned / tech-research / workspace-check / _template-agent | false | 否 |

`register --role` 无 `choices`（`agent-ops.py:1001` 仅 `required=True`）；`_validate_scope()` 对**非** review role 直接放行（`:438`），且 role 没有 spec 时也只在被引用时由 C2 点名。评审类的 scope 来源**只有一条合法前缀**`impact-assessment:`（`policy.json::scope_ref_sources`），否则必须 `--deviation` ≥ **10** 字符（`scope_min_deviation_chars`）。**结论：没有任何 role 能合法承载"子代理的实现工作"**——3 个评审 role 的 spec 正文都写明 "Never modify any file"（正落在 C1 域内），其余 5 个是评审/研究/主代理手册，用它们登记实现工作属于冒名。
`run-2026-09-25-code-review-068` 实测（`agent-ops.py list`）：`code-review@1.2.2 / succeeded / rounds=2 / msrc=wall-clock / scope=self-chosen(!) / cov=08dbea94..08dbea94`（窗口为空）。它在 `verify_close_readiness.py --sprint sprint-17` 里的报告类别是 **`[linkage]`**——原文 `[linkage] 账本有 run 但 §9 run 表未登记：run-2026-09-25-code-review-068`（**不是** `[C1]`：`self-chosen` + deviation 已满足 C1 的"声明完备"）。
`TG-17.md` 全文（22 行）**没有**这条输入：其 §证据只有 ①覆盖窗口语义 ②C1 判定域 ③反向对照 ④与 TG-15⑥ 合排；"归 TG-17"目前只写在审核文档 `2026-09-25-d2d3-independent-review.MD:139`。

**verdict**：**claim 成立**（无 role 可用是结构缺口）；但"归 TG-17 输入"**尚未落到卡上**，属账实不符。

**what would close it**：在 `TG-17.md` §证据 增一条 ⑤，写明：`register --role` 无白名单而 5 个非评审 role 全是 review-only ⇒ 实现类子代理要么冒用评审 role（把非评审 run 拖进 C1/C2 域），要么无 run id；需定"新增 `implementation` spec（`scope_required: false` + `coverage_window` 取值）"或"显式例外口径"。**缺的就是这一行**（本报告不代改卡）。

## O5 `TG-15` 2.5 点结算依据

**claim**（Sprint-17 §87 / 审核 §4）：2.5 点不减，改扣分条件——棘轮上限制+到期未闭环扣 0.5；审核判 critical/major 且未闭环 → 按级别继续扣。

**measurement**（逐条：commit 由 `git log --oneline -3 -- <文件>` 取，闸门为本次实跑）：

| 项 | 判级 | 状态 | 闭环依据（实测） |
|---|---|---|---|
| N1 扫描集漏 29/160 + 7 处真缺陷 | major | **closed** | `a651e86`；`verify_md_tables.py` 实跑 `应扫 162 / 实扫 162 → 一致`（落盘本报告后为 163，集合动态），点名的 4 个文件（a-m11-from-runs / architecture / tg11-retro / search-only-draft）现均为 `问题 0` |
| N2 棘轮按文件豁免（注入 200 处仍绿） | major | **closed** | `9554a8c`；闸门实跑打印 `棘轮基线：4 个文件（按文件设缺陷上限）；review_by=2026-10-31，今日=2026-09-25 → 未到期`、`15 处`在各自上限内（注入型反向对照本次未复跑，仅核对代码路径） |
| N3 target 子串匹配 | major | **closed** | `a651e86`；自检实跑含 3 条 `N3 反向对照 … 精确匹配，子串不算 → FAIL`（windows-backup / mainline / OLD-working-tree-JUNK），`ALL PASS (30 assertions)` |
| N4 豁免台账可无校验静音 | major | **closed** | `a651e86`；实跑 5 条 N4 反向对照（整文件豁免 / `categories:["policy"]` / 自造 category / 理由过短 / 缺 file）全部 `被拒（rc≠0）且点名原因` + 1 条正向放行 |
| N5 `--coverage-anchor` 无 sha 规范化 | major | **closed** | A1；`registry.json` 实读：066/067 锚点 = `092a2f784c9749126dc0f7483fe78ba721f424d0`（**40 位**），`_resolve_sha` 失败即 `COVERAGE-ANCHOR-ERROR` fail-closed |
| N6 §9 自证窗口 + role/target 不比 | major | **closed** | `a651e86`；`ledger_close_window()` 取代 §9 取值，自检 `N6 反向对照 b：§9 第 3 行 target 写错 → FAIL`；linkage 项实测 63 → **11** |
| N7 `card_index` 默认档只 WARN | major | **closed** | `9554a8c`；无参实跑 rc=**0** 且自述"默认档 = strict"，自检含"缺必备节 → FAIL（strict 档）"与 `D3 ≥61 字符填充规避 → FAIL` |
| N8 "空集/缺失 = PASS"族 | minor | **closed** | `verify_md_tables.py` 含"空集 ≠ PASS"（:218/:276）；`--no-coverage` 死旋钮已删（两文件命中 **0**）；`verify_card_index.py:117` 缺 `backlog.MD` → 判问题 |
| N9 无"§9 未填"诊断 / `parse_sprint` 不容忍缩进 / C1 不执行 deviation 阈值 | minor | **部分开** | ① 已修：实跑输出 `[C3] 未声明三查锚点…`；② **仍开**：`parse_sprint` 仍是 `if not line.startswith("\|")`（:95，缩进行丢弃）；③ **仍开**：`check_c1()`（:195-209）只判"有无"，`scope_min_deviation_chars` 仅出现在 FIXTURE（:346） |
| N10 `finish --result-file` LF→CRLF | minor | **closed** | `a651e86`（"finish keeps original EOL"）；`agent-ops.py:624-628` 改为按字节复制、保留 LF/CRLF/BOM |
| R1 覆盖枚举（§6.3） | — | **closed** | 同 N1 |
| R2 迁移数字口径（453 不可复现 / 6962→7155） | — | **部分开（记录类）** | 现役 Sprint-17 已按要求改"以工具输出为准"并给出复现命令（`25268→7155`）；但冻结的 `…parallel-session-quality-analysis.MD:127/:149` 仍写"453 单元格守恒"，同文件 `:245` 又自述不可复现 ⇒ 历史文档自相矛盾（按 D4 不追溯，属已知残留） |
| R3 棘轮 | major | **closed** | 同 N2 |
| R4 账本↔产物无机器可验链接 | — | **部分开（棘轮）** | `finish` 现写 `result_files`（:615-631），`verify_ledger_measurement.py` 实跑 `ALL PASS (30 assertions)` 并打印 `missing_result_files_review=9/9`（9 条历史债在棘轮内，`review_by 2026-10-31`）；窗口语义问题（068 空区间）归 TG-17 ① |
| R5 断言可信度（判据②恒真式 / 套件默认档 / 豁免台账 / 外围不严） | — | **closed 除一项** | 恒真式判据已删（`29adbe7` + VERIFY_META 自述）；套件默认档→N7；豁免台账→N4；外围 target→N3、§9 互联→N6；**deviation 阈值仍开**（=N9③） |
| 说服二查的三个变异 | — | **closed** | 三条各自对应 N2 / N7 / N4，均见上 |

**verdict**：**open majors = 0**（N1~N7 全部可核闭环；R3 同 N2）。残余为 **2 个 minor**（N9②③）+ 2 条记录/棘轮残留（R2 历史文档矛盾、R4 的 9 条历史债）+ 1 条结构缺口（TG-17 ① 的 068 空窗口，已开卡）。
**算式（按已定规则）**：`2.5 − 0.5 × (棘轮未闭环=0) − (未闭环 critical/major 计分 = 0)` = **2.5 点，不扣**。
**必须点明的一处规则空洞**：规则只写了棘轮那 **0.5** 是唯一成文数值，"**按级别继续扣**"**没有扣率**（全仓 grep `按级别继续扣|扣 0.5` 只命中决定本身，无 per-level 数值）。本次因 open majors = 0 恰好用不到；一旦将来判某 major 未闭环，这条算式**无法计算**，需先定率。
另一处判断口径需用户裁定：`TG-15`⑥（覆盖检查进 CI）状态是"**已裁定顺延**"（Sprint-17:101、:87）。若按"⑥ 未交付＝TG-15 未闭环"计，则上面的"0 分"不成立——但那样也缺扣率。

---

## 仍未闭环清单（按严重度）

1. **[major] CI 从未在本批提交上实跑**（40→41 条未推）；且关闭前置块选择器实测命中 **0** 份 Sprint 文档 ⇒ 推上去该闸门仍是空跑；叠加 `fetch-depth: 1` 浅克隆 vs C3 `git rev-list` 的未实测风险（O1）。
2. **[major] `close_readiness` 真数据 rc=1 / 46 项**：34 C1（历史域）+ 11 linkage + 1 C3；填 §9 只清 12 项，34 项须靠 `TG-17` ②（O2）。
3. **[major] `A-M12` 判据④无度量方法**（数据源/口径/窗口/登记义务四缺），Sprint-18 不可复算（O3）。
4. **[major] 实现类子代理无账本 role**（结构缺口），且"归 `TG-17` 输入"**未落卡**——TG-17 §证据缺该条（O4）。
5. **[minor] `close_readiness` 与政策口径不一致**：C1 不执行 `scope_min_deviation_chars=10`；`parse_sprint` 丢弃缩进行（N9②③）。
6. **[minor/棘轮] `verify_ledger_measurement` 历史债** `missing_result_files_review=9/9`（`review_by 2026-10-31`，到期须重评）。
7. **[minor/棘轮] `md_tables` 4 个历史文件 15 处缺陷**在棘轮内（`TG-18` 已开卡）。
8. **[记录类] R2 数字口径**：冻结的历史分析文档仍写"453 单元格守恒"，同文件自述不可复现（按 D4 不追溯）。
9. **[过程] 工作树脏**：`agents/policy.json` / `verify/agent_policy.py` 未提交（并发批 TG-6 进行中）⇒ 本报告的本机绿 ≠ HEAD 绿，且并发写盘期间单条闸门的结果随时可能变。

## 本报告的核查手段与局限

- **手段**：单条闸门实跑（`verify_card_index.py --check --strict`、`verify_md_tables.py`、`verify_no_policy_hardcode.py`、`verify_lint.py`、`verify_matrix.py check`、`scripts/structure-guard.py --replay`、`verify_close_readiness.py` 自检 + `--sprint`、`verify_ledger_measurement.py`）、CI 选择器分支原地复跑、两个前端按 CI 原样 `npm ci` + build、`agent-ops.py list`、`registry.json` 直读、`git log --oneline -3 -- <文件>`、`git rev-list --count`、代码行定位。**未跑 `verify/run_suite.py`**（用户约束）。
- **未验证**：① 第 6 步 offline 全档（21 脚本）——只跑了我点名的 8 条，`verify_smoke`/`verify_agentops`/`verify_local_dir` 等**未在本批重跑**；② pip 安装步骤与新鲜 venv；③ Graphviz（本机无 `dot`，该代码路径**只会在 CI 被执行**）；④ node 22 下的构建（本机 node 26）；⑤ 浅克隆下的 C3 行为（本地无法造浅克隆）；⑥ 注入型反向对照（N2 的 +1 新缺陷、A2 的 200 处注入）——需新建临时文件，按本批"只允许创建一个文件"的约束未做，改为核对代码路径 + 闸门自报输出；⑦ CI 运行日志本身（无 GitHub 访问）。
- **红线遵守**：未 `git add/commit/push`；未改 `agents/runtime/registry.json`（实跑后仍 68 条、无 fixture 残留）；未安装任何依赖；除本文件外未创建/修改任何仓库文件（`npm`/闸门产生的 `dist`、`.next`、`node_modules` 为 .gitignore 内的构建产物，`git status --porcelain` 对这两个目录为空）。
