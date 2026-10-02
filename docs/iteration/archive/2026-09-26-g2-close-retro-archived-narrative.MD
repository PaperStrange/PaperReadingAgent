# G2（治理批）关闭复盘 · 归档叙述（逐字保留）

> **归档口径**：本档收 `2026-09-26-g2-close-retro.MD` 在 2026-10-03 收敛批
> （`run-2026-10-03-implementation-120`）中移出的**全部叙述**。口径细则见同目录 `README.MD`。
> **每个片段都是从归档时刻的源文件里「逐字搬过来」的**——不重排、不改写、不删句；
> 每段给出源文件行区间，搬出前后的 `sha256` 见文末《逐字保留证明》。
> **活文档只留「当前状态 ＋ 未闭环项」**；机读判据（§5 表 `状态码` 列 ＋ 机读 `状态计数:` 行 ＋ §5.0 逐行对钉）
> **留在活文档原位未动**，本档**不含判据、不承担机检职责**。

---

<a id="s5表的口径与机制说明"></a>

> **本表扩容与取值口径（2026-09-29 现跑，本批）**：本表共 **51 行**（原 25 行 ＋ 本批新增 26 行：行 26–34 ＝ `code-review-104` 的 4 major ＋ 4 minor ＋ 1 nit，行 35–44 ＝ `code-review-105` 的 2 critical ＋ 2 major ＋ 4 minor ＋ 2 nit，行 45–51 ＝ `doc-audit-104` 的 2 critical ＋ 2 major ＋ 2 minor ＋ 1 nit）。**2026-09-30 处置批 2（`run-2026-09-30-implementation-109`）**：行 31／34／39／40／41／42／44 状态翻**已修**、行 45／46 按父代理裁定翻**只报**；**2026-09-30 用户单次豁免批（`D-250930-01`）**：行 43／45／46／51 由 `只报` 翻**用户豁免**（行 14 原已为 `用户豁免`）⇒ 现读 `用户豁免=5`；本表**行数与列数一字未变**（全部就地改单元格 ⇒ 登记册 `path:line` 指针零漂移）。
> **行 45／46 即 `impact-assessment-103` 报告自身的两条 critical**——它们与一查 `doc-audit-104` 的 critical 1／2 是**同一发现的两个视角**（发现者＝一查，对象＝〇查报告），故合并为**两行而不是四行**（同一事实不得两处各写一份）。**2026-09-29 父代理裁定：两行状态＝「只报」**（理由与署名见行 45／46）；**2026-09-30 用户单次豁免把两行的 `状态码` 改为 `用户豁免`**（`D-250930-01`）——**性质仍是「只报」**，两行的「只报」定性在 `状态说明` 列逐字保留。
> **状态词表与判据口径（2026-09-30 本轮现跑；**唯一机读真源 ＝ 本表 `状态码` 列**）**：词表**收敛为五元**——`已修`／`未修`／`部分`／`只报`／`用户豁免`；`状态码` 列**只允许这五个词之一**（逐行核对由 `verify/verify_close_tax_reading.py::status_count_problems` 执行：词表合法性 ＋ 声明计数＝逐行实数 ＋ 与 §5.0 逐行一致 ＋ `已修` 行必须指得到落地提交）。**每行的判据来源按三档取**：① 该行 `状态说明` 单元格里写的落地提交；② 该提交的**文件清单与代码内容现读**核对——**提交信息只是线索、不是证据**（本批实测：`1344102` 的提交信息自称"关闭阻塞行 2＋行 3"，其文件清单确实含两个判据文件；而 `1ed6f93` 的提交信息自称"行 15 已修"，文件清单确实含 `scripts/fetch-prices.py`）；③ ①与②冲突时**以代码现读为准**并写改判理由。
> **状态计数（机读，2026-09-30 本轮现跑；供闸门逐行复算）**：状态计数: 已修=46 未修=0 部分=0 只报=0 用户豁免=5 合计=51
> **本批**（`run-2026-09-30-implementation-110`）**改判 7 行**——此前记为 `未修`／`部分`，实测已由落地提交闭环，逐行判据见 **§5.0**：行 2（`1344102`）、行 3（`1344102` ＋ `28bc182`）、行 4／5／6（`61494c9`，同一批）、行 11（`b271606` ＋ `43a65e2`）、行 13（`df5fd73`）。另**更正 1 处签发**：行 15 由 `1344102` 改为 `1ed6f93`（前者文件清单不含 `scripts/fetch-prices.py`）。
> **为什么上一批会数出另一套结果（机制，如实记）**：本档有**三张各自独立编号的表**——§3 A 表（行 1–6，`Finding 编号`）、§4 会话纪要表（行 1–13）、**§5 本表（行 1–51）**。`3e4b649`／`43a65e2` 的提交信息写"close rows 4/5/6"／"row 11"，实际落地的是 **§3 A 表与 §4** 的行；而 `61494c9`／`b271606`／`df5fd73` 又确实把 **§5** 的行 4／5／6／11／13 的缺口修掉了。**同一批行号在三张表里指向不同 finding**，于是"读 §3/§4"与"读 §5"的两个 agent 必然数出两套结果。**本批的处置**：状态一律以本表 `状态码` 列为唯一真源，§5.0 给出逐行"行号｜状态｜落地提交/run｜依据"，两者由闸门逐行对钉（改一处不改另一处即 FAIL）。
> **`只报`／`未修`／`部分` 都不是豁免**：按 `D-250926-06` 的"零未闭环项"口径**仍计入**关闭判定。本次行 43／45／46／51 经用户 **2026-09-30 单次豁免**出列，**非永久生效、不构成先例**（`D-250930-01`；四行的**性质仍是"只报"**——缺陷本体未被修，改变的是关闭判定，不是缺陷状态）。现读（2026-09-30）**未出列行 0 行**（行 43／45／46／51 本次出列、行 14 为**用户单次豁免**〔记为豁免，**不是已修**〕）；机读计数见上一段的 `状态计数:` 行（**唯一真源仍是本表 `状态码` 列**）。`P1`–`P8` 的裁定与执行：`P1`／`P2`／`P3`／`P4`／`P6`＝**2026-09-29 由父代理逐条裁定、本批（`run-2026-09-30-implementation-109`／`-110`）执行**（逐行见 §5.1 与 §5.0）；`P5`＝**父代理亲自执行**（行 42，举证方署名见该行）；`P7`（行 45／46）＝裁定**只报**（署名见该两行，**非本批自评豁免**）；`P8`（行 51）**不在本轮派单范围**，未动 —— **该行的出列已另由用户 2026-09-30 单次豁免裁定**（`D-250930-01`；`P8` 的"改 ID 还是维持现状"这一子问题**仍待裁定**，本次只处置行 51 的关闭判定，未改任何条目 ID）。
> **行 48 的残留义务已具名转移**：R2 日期口径**仍属未验证口径**（父代理 2026-09-29 裁定选②＝就地降级、不实现新闸门）⇒ 强制力恢复的义务落在 **G3 第 6 条**（见下），本表行按"已按裁定执行"记为已修。

> 源行区间 `158-165`（共 8 行）｜搬出前后 `sha256 = 6e1050fc781340dd6d2a702ade67ad58de86ee753402f076f075be06956b7725`。

---

<a id="对话纪要逐字原话13条"></a>

## 4. 与用户的对话纪要（**逐字保留原话**）

| # | 用户原话（逐字） | 处置 |
|---|---|---|
| 1 | "三查结果如何 我记得从下午开始你的工作中全变成了执行动作，没有任何我能看到的文字输出吗 看起来都需要我来主动和你问问题才行" | 登记 `D-250926-01`；条文入 `1-WORKFLOW.MD` §6 第 11 条 |
| 2 | "现在结果如何，别总是让我来问你要进度" | 同上（追加原话） |
| 3 | "是为了减少成本的操作吗，有测算过我们建立的agent loop的ROI吗，我的直观感受是今天我连续做了两次50RMB的billing后才能让这个对话继续下去，结果一直做一直在修major我说的对吗" | 实测 token（cacheRead 3.44B）＋ 官网价目复算：主代理全会话 ≈ ¥103（全 Flash·空闲）~ ¥373（五五开·空闲）；承认"无法测算"是错的 |
| 4 | "本地模型档位是可以根据官网报价页面得到，这件事我提醒过你，本地会话使用的模型类型你也可以拿到" | 认。本机抓取官网价目（`web_fetch` 打不开该域，改本机 HTTP）；价表改**多档** |
| 5 | "不能迭代报价表吗 没人规定报价表只能维护一种价格，这是设计上的偷懒" | 认。撤销"高峰/空闲二选一"的提问 ⇒ 多档 ＋ 按时段计价（用 run 自身时间戳选档） |
| 6 | "G2的交付质量让我不能相信你的严重性判断，我需要真实" | **撤回**"债"分类；第 3 节即为此写的复盘 |
| 7 | "债口径这也是你自己定的对吧 理由依据是什么" | 是自定的，依据薄且违反 `1-WORKFLOW.MD:161` ⇒ 已撤回 |
| 8 | "我觉得越修越多的关键原因在于这几个finding互相耦合……原本我是希望通过impact assessment得到全局视角观察后对三查中对问题提供解耦帮助和处理顺序建议，那么你的观察是？" | 第 3 节给出 6:4 真实比例；**并更正第一版回答**（曾把主因归给耦合 = 把质量问题讲成结构问题）。另记：`impact-assessment` 的判据是 A/B 覆盖率 → 它是"范围尺"，**不消费 finding、无依赖表示** ⇒ 用它解耦是工具定位错误 |
| 9 | "你和另一个对话一样 思考太快太快了 快到我不相信你认真评价反问思考过" | 认。上一轮在**一轮内**拼出"5 类耦合＋工具定位＋4 条顺序"的完整框架，无一处先自我怀疑 ⇒ 改为先反问 |
| 10 | "finding 依赖图，义务索引都可以做成独立的spec，我认可" | 排 G3：两个**独立 spec** |
| 11 | "不要以我能拦得住为前提设计我们的沟通方式，我希望你能完全可靠地自我运行判断" | **已修**（`b271606` ＋ 本次）：`VERIFY_META.features` 里写死的「含 N 条反向对照自检」改成指向现跑末行（3 文件 4 处：`verify_card_index` 8→17、`verify_derived_numbers` 6→19、`verify_decision_register` 9→25 两处）＋重新 `derive`；顺带修 `verify_agentops.py` 的「UC-1~UC-19」（现跑已到 UC-25）与 `docs/1-WORKFLOW.MD` 的同类。**重要更正**：本行原先的字面引用（`sprint-18.md:304` 指 `refresh-providers.py:8/:198`、`verify_config_schema.py:7`）**早已由 `c671b0f` 闭环**，与「陈旧计数」不符——真正闭环的是按现跑证据重新定位的三处。**同形第 4 处**（`verify_gate_integrity.py` 的「7 条」）已由行 21/22 那批一并修掉 |
| 12 | "闭环台账给我看说实话我无法给你有效建议，你的运行过程太长了我基本没参与" | 台账改为 **A 表（finding）＋ B 表（耦合边）**；B 表才是需要用户看的（"哪些必须一起修、按什么顺序"） |
| 13 | "不能迭代报价表吗…" 之后："你的步骤中我没看到复盘文档" | **已修**（`df5fd73`）：未起跑 run 的 `started_at=None` 被 `_before` 字典序回退判成「数据被改过」；改为显式 SKIP 点名＋从次序比较剔除。真入口修前 rc=4 → 修后 rc=0（自检 99→101 断言） |

> 源行区间 `77-94`（共 18 行）｜搬出前后 `sha256 = fd2d30702c3f9a66fd86c397e0d58a05dde9613946ab7d42c9f405a1e0dd5602`。

---

<a id="s51"></a>

### 5.1 行 26–51 逐行处置表（2026-09-29 批 ＋ 2026-09-30 处置批 2；行 24／25／42 为父代理举证项）

> **本小节是 §5 行 26–51 的逐行处置记录**（**状态仍以 §5 表为唯一真源**，本小节只记“做了什么、依据是什么、剩什么要人裁定”）。**2026-09-30 处置批 2 起**：以下行 31／34／39／40／41／42／43／44／45／46 的“本批动作／依据”两列已就地更新（行数不变）。
> **执行 run**：2026-09-29 批＝`run-2026-09-29-implementation-108`；**2026-09-30 处置批 2（本批）＝`run-2026-09-30-implementation-109`**（role `implementation`；覆盖锚点与覆盖上界均由派单方 brief 给定，两者同为 `18f2274e`，与该 role 的 `coverage_window: none` 声明一致）。
> **授权写入集**：2026-09-29 批＝`docs/**`、`verify/**`、`scripts/**`；**2026-09-30 处置批 2（本批）一次性放开**＝`paper-qa-script/**`、`verify/**`、`scripts/**`、`agents/spend-budget.json`、仓根依赖清单、`docs/**`（**仍未碰** `agents/` 下其它文件与 `agents/runs/**`）；两批**均未做** `git add`／`commit`／`push`／`fetch`／改分支；探针全部落 `%TEMP%`（本批另用一个 `%TEMP%` 克隆镜像，用于 absent 分支的实测读数）。
> **已定裁定（派单方，照做）**：① 行 24／25 由**父代理（派单方）**举证、状态翻已修（**反证不是本批跑的**，署名见 §5 对应行）；② `docs/1-WORKFLOW.MD` 的日期口径 R2 规则**就地降级声明**（选②），**不实现新闸门**；③ **2026-09-29 父代理逐条裁定**：行 31／34／39／40／41／44＝**修**（并授权 `paper-qa-script/**`）、行 43＝**接受为具名技术债／不新增判据**、行 45／46＝**只报**（署名＝父代理）、行 42＝**父代理亲自完成**；`P8`（行 51）**不在本批范围**。

| 行 | 修前状态 | 本批动作 | 依据（可复跑） |
|---|---|---|---|
| 24 | 未修 | 状态翻**已修**（举证方＝父代理，逐字写入 §5） | `14603c2`（生产侧端口读 env）＋ `86625c7`（夹具侧 run 级端口）；父代理亲跑：3 轮 × 两实例并发、rc 全 0、`ALL PASS (7 assertions)`、**8787 全程无人监听**（2026-09-29 派单方读数，本批未复跑） |
| 25 | 未修 | 状态翻**已修**（举证方＝父代理，逐字写入 §5） | `86625c7`（`mkdtemp` 回收）；父代理亲量：连跑两轮 `g2l20-before-*`／`verify_runner_*` **净增 0**、两脚本 `ALL PASS (61/46)`（2026-09-29 派单方读数，本批未复跑） |
| 26 | 已修 | **未动**（前批 `a3a3f25` 已修，本批只按 §5 核对状态） | §5 原文；`a3a3f25` |
| 27 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 28 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 29 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 30 | 未修 | **修**：`verify/verify_gate_integrity.py` 的 `PY_WORD_RE` 收词边界（裸词只认 `python*`／`py`，变量形态必须带 `$`）＋ 3 条反向对照 | 修前 `copy`／`happy` 判「有调用」→ 修后判无调用；`copy`／`happy`／`empty`／`apply` 四词读数一律 False；6 种真解释器形态不回归；`--selftest` 断言 56 → 59、`ALL PASS (59 assertions)`（2026-09-29 现跑） |
| 31 | 未修 | **修**（`P1` 裁定）：`scripts/agent-ops.py` 与 `paper-qa-script/app/usage.py` **两侧同改**为**按该模型所属 provider 取窗口**（新增 `provider_of_model`／`provider_of`，`peak_windows_from_prices(prices, model)`／`peak_windows_for(prices, model)` 纯函数 ＋ 便捷入口）；口径＝**窗口随价走** | 真入口反证（`%TEMP%\pr-p1-probe.py`：修前＝`HEAD` 版／修后＝工作区版）：`_estimate_cost(b-1)` 修前 `peak`（借窗口）→ 修后 `flat`；`_tier_plan(b-1)` 修前 `peak` → 修后 `flat`；`a-1` 两侧同判、窗口外 `off_peak`、未入册模型 `flat`、别名归一并具名；`verify_usage.py` ⑪14a–f（断言 61 → 66）；两处调用点普查见回执 |
| 32 | 未修 | **修**：`scripts/fetch-prices.py` 的 `--apply` 档把判据编进退出码（写盘仍 fail-safe）＋ `verify/verify_agentops.py` 3 条永久判据 | 真子进程跑真 `main()`、只替换网络边界 `_fetch`、`AGENT_OPS_DIR` 隔离到 `%TEMP%`：**修前 rc=0 → 修后 rc=1**（2026-09-29 现跑）；`verify_agentops.py --selftest` 断言 156 → 159、`ALL PASS (174 assertions)`（2026-09-29 现跑） |
| 33 | 未修 | **修**：`verify/verify_close_readiness.py` 的 `empty_ops` 夹具增 `atexit` 兜底 | 该夹具命中数 3 → 4；机制反证（真子进程：注册后抛异常 ⇒ 残留 0；不注册 ⇒ 残留 1，2026-09-29 现跑）；**局限**见 §5.3 |
| 34 | 只报 | **修**（`P2` 裁定，口径＝**条数**＋**分支感知**）：`verify/run_suite.py` 新增判决句／条数棘轮（`verdict_problems`／`verdict_scope_problems` 两个纯函数 ＋ 两张按分支实测表）；反向对照 8 条落 `verify/verify_gate_integrity.py` | 套件末段逐脚本打印“判决句｜本分支下限”；反向对照全绿（`verify_gate_integrity.py` 断言 59 → 68）；下限两侧实测值见 §5 行 34；**新发现**：absent 侧 `verify_agentops.py` 打 SKIP 横幅却退 0 ⇒ 本判据判红（真缺陷，如实记） |
| 35 | 已修 | **未动**（前批 `a3a3f25`，本批只核对） | §5 原文；`a3a3f25`（173.1s → 2.8–2.9s） |
| 36 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 37 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 38 | 已修 | **未动**（同上） | §5 原文；`a3a3f25` |
| 39 | 部分 | **修**（`P2` 裁定）：`verify/verify_decision_register.py` 新增 `absent_ratchet_problems()`＋`BRANCH_ABSENT_CAPS`（**只减不增**，键＝`path_in_head(ROOT, "docs/iteration")`）；PASS 行同时打印读数与上限 | 两侧实测：present **0**／absent **1106**（denominator＝登记册 1248 处指针；复算脚本见回执）；反向对照 7 条（`c1″` 端到端**分支感知** ＋ `u`–`z`）；断言 25 → 32；**镜像端到端**：absent 侧真跑打印“1106 处未核，上限 1106 条〔在树里=False〕”并 PASS |
| 40 | 未修 | **修**（`P3` 裁定＝实现，**不改** `verified_by` 措辞）：`scripts/spend-report.py` 新增 `baseline_note()`，逐项上屏高于／低于／等于基线 ＋ 倍率；`baseline` 缺该指标字段 ⇒ **SKIP ＋ rc=3**；附带修 `_comment` 的自述失真 | 真入口反证（`%TEMP%\pr-p3-probe.py` 驱动真 `check()`）：修前对照**零命中**、缺字段照判 `OK` 退 0 → 修后对照上屏、缺字段 rc=3、整段缺 rc=3；不回归：超预算 rc=1、主会话不匹配 rc=3；真 `--check` 现跑末行 `SPEND-BUDGET PASS（全部在预算内；每项基线对照见上）` |
| 41 | 未修 | **修**（`P4` 裁定）：两份仓根依赖清单各补 `zstandard`（`requirements-windows.txt` pin `==0.25.0`，与 `.venv` 实装一致）；`ImportError` 文案改为可执行的安装路径 | 清单现读含 `zstandard`／`zstandard==0.25.0`；`.venv` 现跑 `zstandard.__version__` ＝ `0.25.0`；屏蔽依赖后真入口退 2，且旧误导串从**输出**里消失 |
| 42 | 未修 | **状态翻已修**（`P5`；**举证方＝父代理**）：父代理 2026-09-29 亲自 `git fetch` ＋ 快进本地 `main`；本批**未碰分支**、只登记 | 现跑：`main` ＝ `origin/main` ＝ `bc3121992a723f57abc5a3cd4b53090b97cbcafb`，`git rev-list --count main..origin/main` ＝ **0**（双向 0） |
| 43 | 只报 | **只报**（`P6` 裁定＝**接受为具名技术债**，**不新增判据**）：在 §5 行 43 把债写清（是什么／为什么现在不判／将来要判需先定义什么） | §5 行 43 现含三段具名内容；本批新增的值域兜底＝`verify_usage.py` ⑪14a–f（逐 (provider, 模型) ＋ 合成表反证 ＋ 窗口随价走不变式）；**结构面仍无判据**（如实记）；**该行的关闭判定已由用户 2026-09-30 单次豁免处置**（`D-250930-01`，性质仍为只报） |
| 44 | 只报 | **修**（`P1` 裁定）：`backend/main.py` 端口读取提到**模块级**（`resolve_port()` ＋ `PORT` ＋ `serve()`），import 式启动也生效 | 真入口反证（`import main`，不走 `__main__`）：修前 `has_PORT=false`、非法值静默 rc=0 → 修后 `PORT=9123`／`has_serve=true`；非法 rc=1、越界 rc=1、缺省 8787；4 反证 ＋ 1 对照全过（`%TEMP%\pr-p1-probe.py`） |
| 45 | 未修 | **状态翻只报**（**父代理 2026-09-29 裁定**，理由逐字见 §5 行 45）：缺陷在运行态产物 `agents/runs/**`（被 gitignore）里；纠偏已落在持久层本行与“下游范围一律用 `git diff --name-status` 现跑”这条 | §5 行 45 现署名**父代理裁定**；本批**未代改**他人报告（该目录在忽略域、且不在授权写入集）。**该行的关闭判定已由用户 2026-09-30 单次豁免处置**（`D-250930-01`，**性质仍为只报**） |
| 46 | 未修 | **状态翻只报**（同上，**父代理裁定**；署名见 §5 行 46）：下游按 `doc-audit-104` 的现跑读数纠偏，**不按该清单** | §5 行 46 现署名**父代理裁定**；本批未代改他人报告；`git cat-file -e 18f2274:<path>` 的 5 处命中读数由该行承载。**该行的关闭判定已由用户 2026-09-30 单次豁免处置**（`D-250930-01`，**性质仍为只报**） |
| 47 | 已修 | **未动**（本批工作区改动已由前序批次落盘，本批只核对） | §5 原文；`verify/README.md` 的 `## 故障排查` |
| 48 | 未修 | **修**：`docs/1-WORKFLOW.MD` 的 R2 日期口径处**就地降级声明**（父代理裁定选②，**不实现新闸门**）＋ §6 第 6 条指针同步 | 声明写在规则**同一条内**（就地追加、**不新增行** ⇒ 登记册指针零漂移）；该文件行数与 `HEAD` 版逐字相同（2026-09-29 现跑，Δ=0），规则原文一个字未改 |
| 49 | 已修 | **未动**（本批工作区改动，前序批次已落盘） | §5 原文；10 处改仓内相对路径 |
| 50 | 已修 | **未动**（同上） | §5 原文；`docs/1-WORKFLOW.MD` §6 编号空缺行 |
| 51 | 只报 | **不修**（报告自判"按现体例可接受"）⇒ 待裁定 `P8`；**关闭判定另由用户 2026-09-30 单次豁免处置**（`D-250930-01`，性质仍为只报）；`P8` 的"改 ID／维持现状"子问题仍待裁定 | §5 行 51；`docs/6-DECISIONS.md` 两条的 `时点` 字段各自写明 `2026-09-27（UTC+8）`（2026-09-29 现读） |

> 源行区间 `233-270`（共 38 行）｜搬出前后 `sha256 = a6851b64d513260d7953eb8e00d53b6207e03bbf9b59fb5299986f697d900f9a`。

---

<a id="待裁定清单p1p8"></a>

### 5.2 待裁定清单（`P1`–`P8`；建议处置 ＋ 代价）

> **这些是建议，不是处置**：按 `D-250926-06`，行出列只认**用户逐条裁定**（含单次豁免）。**不允许**把"已给出建议"读成"已闭环"。

| 编号 | 行 | 建议处置 | 代价 |
|---|---|---|---|
| `P1` | 31、44 | 放行 `paper-qa-script/**` 两处：① 选档窗口改**按 provider 取**（`app/usage.py` 的 `peak_windows()` 与 `scripts/agent-ops.py` 的 `peak_windows_from_prices()` 同步改）；② `PAPERQA_VERIFY_PORT` 覆盖对 import 式启动也生效 | 破一次"不得碰 `paper-qa-script/**`"的写入集约束；须重估 `verify_usage.py` ⑪14 与 `verify_provider_switch.py` 的自检；②另需重估应用侧启动路径；**父代理裁定（2026-09-29）：选①＝修**，并**一次性放开** `paper-qa-script/**`；已执行（§5.1 行 31／44）。 |
| `P2` | 34、39 | 先裁**口径**再实现：是限**条数**（只减不增）还是限**成本面**（秒／前缀探测次数）。若限条数，必须**分支感知**（windows ≈ 0、main ≈ 1106），否则"新增指向 `docs/iteration/**` 的合法指针"会被判红 | 新增判据 ＋ 基线数据文件；每次改断言数／新增指针要同批更新基线；口径错则整条判据在某一分支恒红；**父代理裁定（2026-09-29）：口径＝按「条数」且必须分支感知**，先定口径再实现；已执行（§5.1 行 34／39）。 |
| `P3` | 40 | 二选一：① 让 `scripts/spend-report.py --check` 真比对 `baseline`；② 把 `targets.verified_by` 改成与实现相符的措辞 | ①＝改 `agents/spend-budget.json`（集外）＋ 改脚本判据，且"次日读数"要有真值来源才不落成假绿；②＝承认该声明不具备机检；**父代理裁定（2026-09-29）：实现（选①）**——`--check` 真比对 `baseline`，超／低于基线都上屏，缺 `baseline` 字段 ⇒ SKIP 而不是 OK；**不改措辞**；已执行（§5.1 行 40）。 |
| `P4` | 41 | 在 `requirements.txt` 与 `requirements-windows.txt` 各补 `zstandard`（并核对版本与 `.venv` 实装一致） | 改两个仓根文件（集外）；`scripts/spend-report.py` 的报错文案"仓库 `.venv` 已装"要同批改，否则仍误导；**父代理裁定（2026-09-29）：两份清单各补 `zstandard`（含版本核对）＋同批改误导文案**；已执行（§5.1 行 41）。 |
| `P5` | 42 | `git fetch` 后把本地 `main` 快进到 `origin/main`（现跑落后 3 个提交） | 属分支状态动作（本批授权不允许）；快进前须确认无本地未推提交，且 fetch 会刷新 `origin/*` 引用；**父代理裁定（2026-09-29）：由父代理亲自执行**（分支状态动作）——**已完成**；本批只登记（§5.1 行 42）。 |
| `P6` | 43 | 二选一：① 接受为具名技术债（⑪14 已值域兜底，报告原判）；② 新增"两侧同消费面"判据（键消费面一致／新增档位键时两侧同改） | ①＝零成本但结构面仍无判据；②＝约一页夹具 ＋ 需先定义"消费面"的可机检形态（`agent-ops` 与 `usage.py` 的键处理结构不同：前者是白名单常量，后者是 dict 取用）；**父代理裁定（2026-09-29）：接受为具名技术债**（在 §5 行 43 写清“是什么／为什么现在不判／将来要判需先定义什么”），**不新增判据**；已执行（§5.1 行 43）。 |
| `P7` | 45、46 | 二选一：① 让 `impact-assessment-103` 按现跑读数**重跑**并覆盖原报告；② 由用户授权代改该报告（`agents/runs/**` 为忽略域，改动不入版本库） | ①＝再跑一次〇查（成本＋新的覆盖窗口）；②＝"代改他人报告"先例 ＋ 报告不在版本控制里，改动无法被闸门追溯；**父代理裁定（2026-09-29）：行 45／46 状态改为「只报」**（理由逐字见 §5 行 45／46，**署名＝父代理**，非子代理自评豁免）；本批只登记（§5.1 行 45／46）。 |
| `P8` | 51 | 二选一：① 维持现状（ID 内嵌**登记日**，生效时点看 `时点` 字段——两条现已各自写明 `2026-09-27（UTC+8）`）；② 改 ID 为 `D-250927-*` | ①＝零成本，但"体例"只由数据体现、无条文；②＝全仓按条目号引用处（含本档 §5 表头）逐处改写，且与"历史不改号"口径相悖；**本次派单未含 `P8`** ⇒ 本批未动 `P8` 那条体例子问题；**行 51 的关闭判定已由用户 2026-09-30 单次豁免处置**（`D-250930-01`，性质仍为只报），"改 ID／维持现状"仍待父代理／用户裁定。 |

> 源行区间 `271-285`（共 15 行）｜搬出前后 `sha256 = e9a15d153d5f894c9cdf2a06c390c052abd673bd0491fe08d4967899c96deef5`。

---

<a id="未做项与局限"></a>

### 5.3 未做项与局限（如实记）

1. **行 33 的端到端复现未构造**：只做了“机制探针（`atexit` 注册 vs 不注册，异常退出后目录残留 0 vs 1）＋ 该夹具命中数 3 → 4”两件证据，没有构造“真 `--selftest` 中途判红”的复现（要命中创建 `empty_ops` 之后、显式回收之前的那段断言，需向真账本注入坏数据，风险大于收益）。**该行的“异常路径不残留”结论因此是机制级、不是端到端级。**（2026-09-30 处置批 2 复核：仍未构造，结论级别不变。）
2. **行 24／25 的反证不是本批跑的**：并发与净增读数由**父代理（派单方）**提供，本批只把它逐字写进 §5 并署名，**未复跑**。（行 42 的 `fetch` ＋ 快进同型：由父代理执行，本批只做只读复核——`main` ＝ `origin/main` ＝ `bc31219`、落后计数 0；**未**在本批跑 `git fetch`。）
3. **`P1`–`P8` 的处置边界（如实记）**：本批只执行 `P1`／`P2`／`P3`／`P4`／`P6` ＋ 登记行 45／46（父代理裁定）；`P5` 由父代理执行；`P7` 的裁定是**只报**，本批**未代改** `agents/runs/**` 里的他人报告；`P8` 不在派单内、未动。**本批未自标任何豁免**：行 43／45／46／51 的「只报」分别来自 `P6`／`P7`（父代理裁定）与既有状态；**四行的出列来自用户 2026-09-30 的单次豁免**（`D-250930-01`）——**不是本批自评**，且明确**非永久、不构成先例**。
4. **本批不新增闸门脚本、不新增文件**（`git diff --name-status` 现跑全为 `M` ⇒ `verify/verify_artifact_paths.py` 判据⑥ 的 `??` 行为 **0**）：行 34 的判决句／条数棘轮落在既有 `verify/run_suite.py` 内，行 39 的棘轮落在既有 `verify/verify_decision_register.py` 内，行 31／44 的功能改动与行 40／41 的文案/清单改动也都落在既有文件内。**新增判据 ≠ 新增闸门**：本批新增的是既有闸门内的判据（行 34／39 各一族）与既有判据的加固（⑪14a–f）。
5. **单文件处置原则**：本小节的正文**并入复盘本体**而不是另开新档——`verify/verify_artifact_paths.py` 判据⑥（`git status --porcelain -uall` 不得有 `??` 行）会在“新增未跟踪文件”时 FAIL，而本批**不得** `git add`／`commit`；并入既有文件是唯一能同时满足“内容可核”与“套件全绿”的形态。（2026-09-30 处置批 2 沿用同法：§5 表、§5.1 表、§5.2 表全部**就地改单元格**，行数一字未变 ⇒ 登记册 `path:line` 指针零漂移；新增内容只加在既有行**行内**。）
6. **本批（批 3）破了"行数一字未变"这条自述，理由与代价如实记**：状态计数要**可机读**就必须有独立列与逐行举证，本批因此 ① 给 §5 表加了 `状态码` 列（**行数未变**）、② 新增 **§5.0 逐行状态清单**（53 行新行）。**净漂移仍为 0**，因为新增内容全部落在**所有 `path:line` 指针所指行号之后**（本档被指针指到的最大行号是原 `:119`，本批新增内容从原 `:167` 之后起；§5 表的列改动是**就地**的、行号不动）。复扫证据：全仓 `g2-close-retro.MD:<行号>` 的指针集合改动前后**逐条相同**（**22 处**，含 `6-DECISIONS.md` 四处与 `agents/runs/**` 一处；其中 14 处在 `g1-vs-g2-close-comparison.MD`、3 处在 `087-minor-5-9-disposition-spec.MD`）；`verify_decision_register.py` 现跑 `pointers=1248`、`quotes_drift=10` 均与改动前**同数**。**代价**：本档不再是"零新增行"，后续批次若在本档**中间**插行会打断这条不变式——指针一律改用"章节 ＋ 行文本"锚定才是根治（属 G3）。
7. **行 34 的"新发现"在本批被修掉（原文已就地更新）**：`verify_agentops.py` 的 SKIP 档原为"判决行说不是通过、退出码说成功"两通道矛盾。本批新增 `verdict_exit()` ⇒ SKIP 档退 `3`（与判决行同口径），断言 174 → 177、`run_suite.BRANCH_ASSERTION_FLOORS` 的 present 下限同步 177（**下限只随实测上调，未动任何上限／cap／timeout**）。**同时更正一处上一批的表述失真**：`run_suite.py` 原注释称 absent 侧"套件把它算成 PASS"——实测 `verdict_problems` 在"rc=0 ＋ 末行具名 SKIP 横幅"上**本来就报红**（判据②），该注释已改为如实表述。`verify_close_tax_reading.py` 新增"状态计数可解析"一族判据（夹具正向 ＋ **八条**反向对照，断言 → **23**），并同步改了它的 `VERIFY_META` ⇒ **同批 `derive`**（遵行 23 的立规），`verify_matrix.py check` 末行 `CHECK OK: 57 脚本与 TEST-MATRIX.MD 一致`〔2026-09-30 批 3 现跑〕。**如实记一处"收尾后追加"**：判据⑤（"`状态说明` 以状态词开头时必须与 `状态码` 相同"）是**收尾之后**才补的——它抓到的正是本批自己第一版的形态：行 4／5／6／11／13 的说明格仍写裸 `未修`，而机读列已改判 `已修`（同一行两个状态）。该追加使断言 21 → 23，但**未回写 run 交付报告**（`agents/runs/**` 是已封存的测量产物，改写它会让 `output_chars` 与实际文件不符）；差额以 `round` 追加记录在账本里。

> 源行区间 `286-295`（共 10 行）｜搬出前后 `sha256 = cb4c7d555d6325d9243df5a5eb43c70b21beea8721ba0a9ab352d836b27033ea`。

---

<a id="本批门槛读数"></a>

### 5.4 本批门槛读数（2026-09-29 批 ＋ 2026-09-30 处置批 2 现跑；逐条命令见 run 回执）

| 门槛 | 末行读数（**2026-09-30 处置批 2 现跑**；方括号内为 2026-09-29 批的原读数） |
|---|---|
| `verify/verify_md_tables.py` | `MD-TABLE PASS`（186 个文件解析通过；其中 4 个历史文件走棘轮基线、均在各自的 defect 上限内）〔09-29 批为 187〕 |
| `verify/verify_derived_numbers.py` | `DERIVED-NUMBERS PASS`：183 个文档扫描通过（32 个历史文件走棘轮上限、均在各自上限内；生成物 1 个豁免）〔09-29 批为 184〕；断言 19 |
| `verify/verify_decision_register.py` | `DECISION-REGISTER PASS`：122 条条目（§3 19 / §4.1 103）；指针 1248 处（其中本分支不存在 **0** 处未核，行 39 棘轮上限 **0** 条〔分支判据 `docs/iteration` 在树里=True〕）；§4.1 引文-出处核对 97 条、0 条不符（±2 内漂移 **10** 条 —— 与本批改动前**同数** ⇒ **漂移净新增 0**，指针零漂移）；待回填 0 条；断言 25 → **32** |
| `verify/verify_close_readiness.py --sprint docs/iteration/sprint/2026-09-25-sprint-18.md` | `CLOSE-READINESS PASS`：2026-09-25-sprint-18.md（run 表 18 行，锚点 9f8d690f，覆盖提交 72，产出型标注 0）；自检断言 6〔2026-09-30 现跑〕 |
| `verify/verify_ledger_measurement.py` | `ALL PASS (41 assertions)`；`EVIDENCE: … assertions=41 rc=0 ledger=present`〔2026-09-30 现跑〕 |
| `verify/run_suite.py --tier offline` | `SUITE PASSED (26 scripts)`〔2026-09-30 现跑〕；末段新增**行 34 判决句／条数棘轮**读数行（5 个自陈脚本逐条打印“判决句｜本分支下限”；本轮另有 **16** 个脚本打印了判决句但未自陈 ⇒ 逐轮 WARN 点名，本批不判红）。**首轮曾红 2 个**：`verify_lint.py`（C 级 E501 2526 > 2494）与 `verify_runner.py`（fixture 档被“自陈脚本数棘轮”误判）⇒ 均已修（本批新增长行全部折到 ≤88 列；该棘轮改为**只对仓库 `verify/` 目录**判） |
| `verify/verify_lint.py` | `ALL PASS (11 assertions)`；C 级棘轮 `E501=2466/2494`（**未上调任何 cap**；本批新增超长行 **0** 条 —— 初版实测 2526（超限 32 条），已把本批新增的 63 处长行全部折到 ≤88 列，最终 2466 **低于**改动前的 2468）〔2026-09-30 现跑〕 |

**2026-09-30 批 3（`run-2026-09-30-implementation-110`）门槛读数（windows 工作树现跑；命令逐条见 run 回执）**：

| 门槛 | 末行读数（2026-09-30 批 3 现跑） |
|---|---|
| `verify/verify_md_tables.py` | `MD-TABLE PASS`（186 个文件解析通过；其中 4 个历史文件走棘轮基线、均在各自的 defect 上限内）——§5 表加 `状态码` 列＋新增 §5.0 后本档表格块 9 → 10、问题仍 **0** 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_derived_numbers.py` | `ALL PASS (19 assertions)`；`EVIDENCE: … assertions=19 rc=0 review_by=2026-10-31` 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_decision_register.py` | `ALL PASS (32 assertions)`；`EVIDENCE: … assertions=32 rc=0 entries=122 quotes_checked=97 quotes_drift=10 pointers=1248`——**指针 1248 处与引文漂移 10 条均与改动前同数 ⇒ 漂移净新增 0**（全仓指向本档的 `path:line` 指针 **22 处**改动前后逐条复扫相同） 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_close_readiness.py --sprint docs/iteration/sprint/2026-09-25-sprint-18.md` | `CLOSE-READINESS PASS`：2026-09-25-sprint-18.md（run 表 18 行，锚点 9f8d690f，覆盖提交 72，产出型标注 0）；`EVIDENCE: … assertions=6 rc=0 mode=real-data criteria=6` 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_ledger_measurement.py` | `ALL PASS (41 assertions)`；`EVIDENCE: … assertions=41 rc=0 ledger=present` 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_agentops.py --selftest`（windows） | `ALL PASS (177 assertions)`（**174 → 177**：新增"判决行与退出码同口径"3 条；present 下限同步 **177**，**未上调任何上限**） 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_close_tax_reading.py` | `ALL PASS (23 assertions)`；`EVIDENCE: … assertions=23 rc=0 mode=selfcheck`（新增"状态计数可解析"一族：夹具正向 ＋ 八条反向对照）；`--sprint …` 真数据档另打印 `CLOSE-TAX PASS（状态计数档）` 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_gate_integrity.py --selftest` | `ALL PASS (68 assertions)`；`guard_required=10 ratchets=5`（下限 68 **未变**；行 34 反向对照①/② 的样本条数改为**从下限表派生**，不再写死 174） 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_matrix.py check` | `CHECK OK: 57 脚本与 TEST-MATRIX.MD 一致`（改 `verify_close_tax_reading.py` 的 `VERIFY_META` 后**同批 `derive`**，遵行 23 的立规） 〔2026-09-30 批 3 现跑〕 |
| `verify/verify_lint.py` | `ALL PASS (11 assertions)`；C 级棘轮 `E501=2466/2494`（与批 2 读数**同值** ⇒ 本批净新增超长行 **0**；**未上调任何 cap**。**方法更正如实记**：本批第一版新增了 5 条超宽行（ruff 的 E501 按**显示宽度**计，中日韩字符算 2 列——我先用"字符数 > 88"的探针误判为 0 增量），已逐行折到 ≤88 列） 〔2026-09-30 批 3 现跑〕 |
| `verify/run_suite.py --tier offline`（windows） | `SUITE PASSED (26 scripts)`；行 34 逐脚本读数含 `verify_agentops.py：ALL PASS (177 assertions)｜本分支下限 177`，`VERDICT-FAIL` **0** 条；**零 skipped ⇒ 第三态不改动末行形态**（仍逐字为 `SUITE PASSED (26 scripts)`） 〔2026-09-30 批 4 现跑；批 3 原读数同值〕 |
| `verify/run_suite.py --tier offline`（**absent 镜像**） | `SUITE PASSED (25 scripts, 1 skipped): verify_agentops.py[spec-absent-on-branch]`，套件 **rc=3**（第三态：skipped **不混进** PASSED 的脚本数、末行显式写"本档不是通过"）；`VERDICT-FAIL` **0** 条。**批 3 原读数**为 `SUITE FAILED (1/26): verify_agentops.py`、rc=1——那是两态套件把 rc=3 撞成假红（**没有一条真判据失败**）。镜像＝`%TEMP%` 克隆（`-b windows`）后 `git rm -r docs/iteration` 并本地提交一次（`git -c core.autocrlf=false`；**不动真仓的分支／引用**） 〔2026-09-30 批 4 现跑〕 |
| **第三态（SKIP）口径**（`run_suite.py`） | 具名 SKIP ＝ **rc=3 且末行是 `SKIP[…]…本档不是通过` 横幅**（两通道，缺一不可）⇒ 归 `skipped` 档、套件 rc=**3**（不取 0：取 0 就是"SKIP 冒充通过"；与 `verify_agentops.py::SKIP_EXIT`／`spend-report` 同码）。假 SKIP 两种形态各有处置：**rc=3 无横幅** ⇒ 照旧判失败（否则任何脚本退 3 就能溜出记账）；**有横幅却 rc≠3** ⇒ 不归 skipped、上屏 WARN。判据本体＝纯函数 `skip_verdict()`／末行单一真源＝`suite_verdict_line()`。**2026-09-30 批 5 就地更新**：本条原称"既有实例＝`verify_close_readiness.py` 的 rc=0 档，改判要动它的退出码，属另一批，**本批不擅自改判**"——**该实例已由批 5 改判**（`run-2026-09-30-implementation-112`）：其 SKIP 档按 `verify_agentops.py` 的同一真源做法对齐到 rc=3（`verdict_line`／`verdict_exit` 判决行与退出码同源），故"判决行说不是通过、退出码说成功"这一形态在本仓**不再有任何在册实例**；该 WARN 分支**保留**，盯的是将来新出现的同形态脚本 〔2026-09-30 批 5 现跑〕 |
| **第三态反向对照**（`verify_runner.py` ⑮a–c） | **真入口驱动**（起真子进程跑 `run_suite.py`，不是只调纯函数）三条：① 真失败仍判 FAIL（`SUITE FAILED (2/4, 1 skipped)`、rc=1，不被第三态吞掉）；② 假 SKIP 不归 skipped（rc=3 无横幅 ⇒ 判失败；横幅＋rc=0 ⇒ 只 WARN、`skipped_scripts` 为空）；③ skipped 与 failed 并存 ⇒ **failed 优先**（rc=1）。另有一条**夹具环境教训**：子进程 stdout 默认跟控制台代码页（cp936），而套件以 UTF-8 解码 ⇒ 夹具必须 `reconfigure(encoding="utf-8")`，否则中文横幅到父进程成乱码、"末行命中横幅"判据恒假（实测首版 ⑮a 得 `exit=1 status=failed`） 〔2026-09-30 批 4 现跑〕 |
| **CI 是否接受第三态**（`run_suite.py` 那一步） | 父代理 2026-09-30 裁定＝**口径①（接受）＋ 一条硬约束**。事实依据：无账本的全新 checkout 里 `agents/runtime/registry.json` 不存在（`.gitignore` 忽略）⇒ 账本类判据永远走具名 SKIP ⇒ 套件在 CI 上**必然** rc=3，而 `$ErrorActionPreference="Stop"` ＋ `$PSNativeCommandUseErrorActionPreference=$true` 会把它判红（**假红**：没有一条真判据失败）。落点＝`ci.yml` 的 `Offline verify suite` 步骤内 `# === CI-SKIP-GATE-BEGIN/END ===` 段（**门标记即在位证据**）。**硬约束**：绝不允许只看 rc=3——`run_suite.py::REFUSE_EXIT` **也是 3**（预算超限／非有限预估＝**拒绝启动**），裸接受 3 会吞掉真拒绝。放行条件＝**三通道对齐**：① 末行命中 `^SUITE PASSED \(\d+ scripts, \d+ skipped\): \S+\[[^\]]+\](, \S+\[[^\]]+\])*`（零失败 ＋ 具名 SKIP 徽章）；② `rc = 3`；③ 放行分支**显式打印**「零失败 ＋ 有具名 SKIP ⇒ 本步放行」「**账本类判据未执行、本档不是通过**」后再置 rc=0（不静默）。**`$` 锚点故意不用**（套件末行以 CJK 全角 `）` 收尾，ASCII `$` 会让它恒不命中——批 5 实测踩到，首版门就地恒红）〔2026-09-30 批 5 现跑〕 |
| **CI 放行逻辑反向对照**（批 5，**真驱动**：把 `ci.yml` 标记之间的字节逐字取出、在真 `pwsh` 里跑；A 系列走真 `run_suite.py` ＋ `%TEMP%` 夹具，B 系列为注入桩） | 九条各自单跑、逐条看门自身的 rc：**A1** 零 skipped 全绿（`SUITE PASSED (1 scripts)`／rc=0）⇒ 放行但**不走**放行分支（末行不是 skipped 形态）；**A2** 真失败 ⇒ **判红**（`rc=1`）；**A3** 全具名 SKIP（`SUITE PASSED (0 scripts, 2 skipped): verify_skip_a.py[ledger-absent], verify_skip_b.py[spec-absent-on-branch]`／rc=3）⇒ **放行**（rc=0，且打印"本档不是通过"说明）；**A4** 具名 SKIP ＋ 真失败（`SUITE FAILED (1/2, 1 skipped)`）⇒ **判红**（failed 优先）；**B1** 裸 `REFUSE_EXIT` 形态（rc=3 ＋ 末行 `REFUSED: …`）⇒ **判红**（硬约束的实证）；**B2** 假 SKIP 横幅（rc=3 ＋ 末行是 `SKIP[…]` 横幅但**不是**套件形态）⇒ **判红**；**B3** 同形态但 rc=2 ⇒ **判红**；**B4** 同形态但 rc=0 ⇒ **判红**（放行只认 rc=3）；**B5** `SUITE PASSED (3 skipped)`（无具名徽章）＋ rc=3 ⇒ **判红**。**首版门本身被这三条抓出两个缺陷**（如实记）：放行条件原写 `rc=0` ⇒ 放行分支**永不可能命中**（A3 实测 `acc=False` 而 `match/sw` 均 True）；原顺序把 `rc≠0 ⇒ 抛` 放在放行分支**之前** ⇒ 即便命中也会被后一条无条件抛掉。两处均已修，改后九条全绿〔2026-09-30 批 5 现跑〕 |
| **无账本克隆的 CI 等价实跑**（批 5） | `git -c core.autocrlf=false clone --branch windows <本仓> %TEMP%\pr-ci-clone-…`（rc=0）⇒ `agents/runtime/registry.json` **不存在**（该目录只有 `prices.json` ＋ `tg14-baseline.json` 两个入库文件）。把本批改过的三份文件拷进克隆后：① 套件末行 `SUITE PASSED (25 scripts, 1 skipped): verify_agentops.py[ledger-absent] —— 无失败，但 1 个脚本的判据未执行（SKIP≠PASS）⇒ 本档不是通过（rc=3）`、**rc=3**（逐脚本读数：仅 `verify_agentops.py exit=3`，其余 25 个 rc=0；`verify_close_readiness.py` 在套件里走**自检档**、不读账本 ⇒ rc=0，在 `--sprint` 真数据档才走 SKIP 档）；② **照跑 `ci.yml` 那段字节**（只把行首 `python ` 换成显式解释器路径，逻辑一字不改）⇒ **该步 rc=0（放行）**，输出含「**账本类判据未执行、本档不是通过**」与「未执行项见上屏 `skipped` 档点名：…」；③ 克隆内 `--sprint docs/iteration/sprint/2026-09-25-sprint-18.md` ⇒ **rc=3** ＋ 末行 `CLOSE-READINESS SKIP[ledger-absent]（1 条判据未执行：…）——其余 18 条已验，**本档不是通过**`（批 5 改判后的形态；改前同档 rc=0）〔2026-09-30 批 5 现跑〕 |

**2026-09-30 批 5（`run-2026-09-30-implementation-112`）门槛读数（windows 工作树现跑；
下表每行末的〔〕内即为本行的时点标记，命令逐条见 run 回执）**：

| 门槛 | 末行读数（2026-09-30 批 5 现跑） |
|---|---|
| `verify/run_suite.py --tier offline`（windows） | `SUITE PASSED (26 scripts)`、**rc=0**（逐脚本读数 26/26 rc=0；**零 skipped ⇒ 第三态不改动末行形态**）。批 5 改了 `verify/close_readiness`／`run_suite`／`ci.yml` 三处，本读数即"windows 侧未回归"的证据 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_close_readiness.py --selftest` | `ALL PASS (105 assertions)`；`EVIDENCE: … assertions=105 rc=0 mode=selfcheck`（**103 → 105**：新增"两通道同口径（rc=3 ＋ 末行具名横幅）"与"`verdict_line`／`verdict_exit` 同源"两条；**未放松任何既有断言**） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_close_readiness.py --sprint docs/iteration/sprint/2026-09-25-sprint-18.md` | `CLOSE-READINESS PASS`：2026-09-25-sprint-18.md（run 表 18 行，锚点 9f8d690f，覆盖提交 72，产出型标注 0）；`EVIDENCE: … assertions=6 rc=0 mode=real-data criteria=6`——**账本在位时照旧 rc=0 ＋ 机读证据行**（收紧只作用于 SKIP 档） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_close_readiness.py`（**账本缺失档**，`AGENT_OPS_DIR` 指向空目录 ＋ `%TEMP%` 最小 Sprint 文档） | **rc=0 → rc=3**（本批改判）；末行 `CLOSE-READINESS SKIP[ledger-absent]（1 条判据未执行：…）——其余 0 条已验，**本档不是通过**`（判决行落在**末行**，套件两通道判据认的就是这一形态）；**不打印** `EVIDENCE:`／`CLOSE-READINESS PASS` 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_agentops.py --selftest`（windows） | `ALL PASS (177 assertions)`（**读数未变**——本批只改它的 docstring 里"为什么是 3"那段陈述，判据一条未动） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_lint.py` | `ALL PASS (11 assertions)`；C 级棘轮 `E501=**2466**/2494`（**与改动前逐字同值 ⇒ 本批净新增超长行 0**；**未上调任何 cap**）。**如实记**：本批首轮实测 **2471**（+5：`verify_close_readiness.py` ＋3、`verify_agentops.py` ＋2，逐行定位后折行至 ≤88 显示宽度），折行后回到 2466；A/B 硬级别 0 条 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_matrix.py derive` ＋ `check` | `DERIVE OK: 57 脚本 → verify/TEST-MATRIX.MD`；`CHECK OK: 57 脚本与 TEST-MATRIX.MD 一致`（改了两个脚本的注释/文档串 ⇒ **同批 derive**，遵行 23 的立规；派生结果与入库文件逐字节一致 ⇒ 本文件未被改动） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_decision_register.py` | `ALL PASS (32 assertions)`；`EVIDENCE: … assertions=32 rc=0 entries=122 quotes_checked=97 quotes_drift=10 pointers=1248`——**指针 1248 处与引文漂移 10 条均与改动前同数 ⇒ 漂移净新增 0**（本批对 §5.4 表的改动：**就地改写 1 行 ＋ 追加 3 行**，未改动任何被 §4.1 逐字引用的引文段） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_md_tables.py` | `MD-TABLE PASS`（186 个文件解析通过；其中 4 个历史文件走棘轮基线、均在各自的 defect 上限内）——§5.4 新增 3 行表格行后本档表格块与解析均无问题 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_artifact_paths.py` | `ALL PASS (13 assertions)｜动态目标 105 处（34 个文件全在棘轮表内且未超上限）`；`EVIDENCE: … assertions=13 rc=0`——本批**未新增文件**（`git status --porcelain -uall` 只有 3 个 `M`、零 `??`），探针全部落 `%TEMP%` 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_close_tax_reading.py`（自检档） | `ALL PASS (23 assertions)`；`EVIDENCE: … assertions=23 rc=0 mode=selfcheck`（**读数未变**） 〔2026-09-30 批 5 现跑〕 |
| `verify/verify_gate_integrity.py`（真数据档） | `ALL PASS (75 assertions)`；`EVIDENCE: … assertions=75 rc=0 guard_required=10 ratchets=5`（**68 → 75**：批 4 新增的"判决句/条数棘轮"接线判据一族；本批**未改**该文件，读数如实记为批 4 之后、批 5 之前已存在的 75） 〔2026-09-30 批 5 现跑〕 |


> **注（2026-09-30 现读）**：上表各行里的 `run 表 18 行` 是**当时（批 2／3／5／6）的读数**，按"标明时点的历史读数"口径**不回改**。
> 现读（2026-09-30）为 **20 行**——本批按派单要求在 §9.1 补入 `run-2026-09-30-code-review-114` 与
> `run-2026-09-30-lessons-learned-115` 两行（**修前闸门报两条 `INFO[linkage-in-flight]`、超 120 分钟即 FAIL**；
> 补登记后该 INFO 现读为 **0 条**，见文末门槛读数表）。行 446 的 `sprint-18 18 行` 同属**无账本克隆里的历史读数**，同理不回改。

> 源行区间 `296-353`（共 58 行）｜搬出前后 `sha256 = 52ee800c8cba7fc93c232fba0e346c007a041094004c9147ec754a052c7cf0d3`。

---

<a id="g3输入"></a>

## 6. G3 输入（用户已认可方向）

1. **finding 依赖图（独立 spec）**：输入 = finding 列表 ＋ 变更集 ＋"数据源→消费者"登记；
   输出 = 边（同文件/同函数/同数据源/同控制流层）、拓扑序（共享实现的 finding 必须同批修）、
   风险标注（修 A 会让 B 变红）、解耦动作（拆共享实现／换稳定标识／义务声明进数据源）。
2. **义务索引（独立 spec）**：`数据源 → 义务 → 检查器 → 状态` 机器可读；凡声明的数据源出现在
   提交范围里，其义务必须"已履行（带证据）"或"显式豁免（带理由）"，否则 FAIL。首个实例 =
   `3-LEARNED.MD` → `MM-4`（思维模型提取）。
3. **报价表多档 ＋ 时段计价 ＋ 用量记录**：官网高峰/空闲两档；用 run 自身时间戳选档；
   时间戳缺失按**高峰**计并打 `tier_assumed`；`prices-derive` 的键白名单同步（否则派生即丢档）。
4. **稳定标识**：登记册的 `path:line` 指针换成条目号/文本锚点（今日漂移两轮，全是白工）。
5. **登记册回填**：105 条 `待回填` 的处置（全量回填 vs 先做高频被引用者）——**待用户裁定**。
6. **日期口径 R2 规则的机检缺口（2026-09-29 登记；来源＝一查 `run-2026-09-29-doc-audit-104` major 4，落点＝复盘 §5 行 48）**：`docs/1-WORKFLOW.MD:403` 要求"文档内日期与该文件最近一次 `git log -1 --format=%cI` 的 committer 日期相差 >1 天 ⇒ 记 `R2` 并当日更正"，而 2026-09-29 现跑 `verify/` 与 `scripts/` **没有任何实现判这条**（唯一同名命中 `verify_ledger_measurement.py` 的"时间/日期口径"判的是**账本 run 的日期**）⇒ 该规则 `unverifiable`。后果是可观测的：2026-09-29 逐文件比对，本批变更的 13 个 `.MD` 里 **7 个**的头部日期与 `%cI` 相差 >1 天（其中 `verify/TEST-MATRIX.MD` 差 8 天、`docs/6-DECISIONS.md` 差 3 天），**无闸门会报出来**。两条候选：① 落地机检（按变更集逐 `.MD` 取头部日期与 `%cI` 比对，>1 天 FAIL 并点名）——代价＝新增一条闸门并重估套件超时预算；② 在 `:403` 就地标注"本规则 prose-only、无机检"并把执行点降级声明（口径同 `:421`／`:461` 已有的"执行点声明"写法）——代价＝该规则永久失去强制力。**处置（2026-09-29 更新）**：✓ 父代理裁定**选②**并已落地——`1-WORKFLOW.MD` 的 `:403` **同一条内**已明写"本条口径当前无任何机检实现、属**未验证口径**、已登记为 G3 未闭环项（本档 §6）"＋代价（强制力只剩人的执行义务）；写法＝就地追加（**不新增行**，避免顶偏登记册 `path:line` 指针）；**本批不实现新闸门**；规则原文一个字未改。**G3 的残留义务 ＝ 候选①**（恢复强制力的唯一路径），其判据与代价仍按上段原文，**不得**把"已声明"读成"已解决"。**不维持现状**：`agents/functions/doc-audit.md` 第 10 步明定"无执行点的规则 ＝ 机制缺口，须作为一类缺陷报出"——本条即按该步报出并显式降级，而不是让它继续以"看起来有规则"的形态存在。

> 源行区间 `354-367`（共 14 行）｜搬出前后 `sha256 = ac664c0a29e74c9186493eec30a21dd40da0cb69ddea0b72e33bc927b4dd301b`。

---

<a id="账本时间戳退化"></a>

## 7. 账本时间戳退化：修复方案的**覆盖边界与备案**（用户 2026-09-26 追问后补）

> **本节的正式落点已迁至独立备案档**：[`R-001`](../agents-infra/2026-09-26-residual-risk-register.MD)
> （用户 2026-09-26 定规："这些备案和事故记录一样需要独立且显式存在"）。
> **冲突时以备案档为准**；此处保留的是登记当时的原文，后续维护只改 `R-001`。

**起因**：`run-2026-09-26-code-review-092` 的 `started_at == ended_at` 触发
`verify_ledger_measurement` 的 `zero_duration`（棘轮 3/3 已满）⇒ 套件与 CI 红。
根因是主代理的操作序列：`register` 漏 `--start` ⇒ `started_at` 空 ⇒
`update --status running` 把它置为"此刻" ⇒ `finish` 在同一秒写 `ended_at`。
（`finish` 当时已警告 `⚠退化=zero_duration`，**我没有处理**——这条本身是过程事故。）

**用户追问**：方案 (a)（给 CLI 加 `set-started-at` 受控回填）**能不能覆盖这个问题的所有报错场景**？
**答案：不能。** (a) 是**修复工具**，不是**预防机制**；且它自带一类新风险。逐场景判定：

| # | 场景 | 症状（闸门判据） | (a) 能否解决 |
|---|---|---|---|
| 1 | `register` 漏 `--start`，`update` 与 `finish` 同秒 | `zero_duration` | ✅ 能（有真值可回填） |
| 2 | run 从未真正起跑（`queued` 直接收尾 / 中断） | `missing_timestamp`、`terminal_not_written_back` | ❌ 不能——**真值是"未知"**，回填只能编一个像样的数 |
| 3 | 注册 `--start` 但久后才 `finish` | 正常 | —（无需） |
| 4 | 时钟/时区来源不一致 | `negative_duration` 或荒谬时长 | ❌ 不能——根因在时钟，不在账本字段 |
| 5 | **回填本身写错**（把"子代理起跑"记成"主代理发现它跑完"） | **无判据** | ❌ **反而引入**：闸门只能判"合理"，判不了"真实" |
| 6 | 并行派单：多个子代理同时跑，主代理登记时刻与子 run 实际起点不一致 | 时长偏短 | ⚠️ 部分——取决于证据可及性 |
| 7 | 历史存量（存量 `zero_duration` 与 `missing_result_files`，**条数以闸门现跑为准**） | 棘轮 WARN/FAIL | ⚠️ 能修但**改的是历史**，须逐条留痕 |
| 8 | 判据本身只覆盖"写坏了"，不覆盖"没写" | 见 2 | ❌ 不能 |

**结论（备案）**：
1. **(a) 的定位写清**：受控**回填**（repair），口径同 `set-output-chars`（必带理由、写
   `started_at_backfills` 留痕、同值无操作）；**不得**被当作"时间戳问题的解决方案"引用。
2. **(a) 的自身风险必须备案**：它能写出**可信但为假**的测量，而现有闸门**无法区分**——
   这与本 Sprint 刚立的两条规则直接相关：`1-WORKFLOW.MD` §6 第 12 条（**读数必须有来源：
   手抄禁止，编造更禁止**）与机制反例档案例 24（**文档/数据都是主张**）。
   ⇒ **回填规则**：`--reason` 必须写明**证据**（`agents/runs/<id>/` 产物的 mtime / 作业日志），
   拿不出证据的**拒绝回填**；"不知道就写不知道"，不得用估值冒充测量。
3. **真正的预防不在 (a)**，在**写入口 fail-closed**：`finish` 在 `ended - started < 1s`
   时应当**拒绝**（而非只警告），除非显式 `--allow-zero-duration --reason <理由>`；
   同时 `update --status running` 在 `started_at` 为空时应**拒绝**并提示先 `register --start`。
   ——即"把今天这条人工纪律，换成不允许写坏的入口"。
4. **备案去向**：本条进机制反例档（**机制缺口**：判据只覆盖形态、不覆盖真实性；写入口无守卫），
   与报价表多档、稳定标识同列为 G3 首批。


> **已处置裁定（父代理 2026-09-27，不另立行）**：`verify/suite_result.json` 是**仓库内**固定名、两个 `run_suite.py` 并发会互相覆盖 ⇒ 裁定「**并发跑同一套件不是受支持场景**，套件须串行运行」；这不是缺陷而是使用约束（行 8 批如实报出、未擅自改）。

> 源行区间 `368-411`（共 44 行）｜搬出前后 `sha256 = 5025390c7ff1d4a67f7bc2931a744c819caa77bedbf73750846f58a501b5780d`。

---

<a id="ci放行的第二处落点"></a>

## 8. CI 放行的**第二处落点**：关闭前置闸门步骤（2026-09-30 批 6）

**起因（批 5 的遗留）**：批 5 把 `verify/verify_close_readiness.py` 的 SKIP 档退出码由 0 改判成 3
（判决行与退出码同一真源）之后，`ci.yml` 里**另一个步骤**——`Close-readiness gate for sprints that
claim closure (TG-11)`——在无账本的全新 checkout 上必然 rc=3，而该步骤的
`$ErrorActionPreference="Stop"` ＋ `$PSNativeCommandUseErrorActionPreference=$true` 会把它判红：
**套件那一步放行了，红只是换到了这一步**（仍没有一条真判据失败）。父代理 2026-09-30 裁定：
按**与套件门同一条护栏语义**给该步骤加门（放行只认"rc=3 ＋ 具名 SKIP 横幅"两通道，裸 rc=3 仍判红），
并在放行分支**先显式打印**"**账本类判据未执行、本档不是通过**"**再**置 rc=0。

落点＝`ci.yml` 该步骤内 `# === CI-CLOSE-SKIP-GATE-BEGIN/END ===` 段（**门标记即在位证据**）。
与套件门的**唯一有意差异**：标记把**整条步骤体**（含 `$ErrorActionPreference`）纳入，故"逐字取出
标记之间的字节"即得**可直接真跑**的整段（反向对照不需要预置任何变量 ⇒ 不存在推演）。

| 事实 | 读数（2026-09-30 批 6 现跑；命令逐条见 run 回执） |
|---|---|
| 退出码五态（判据来源＝脚本 docstring，门内**不重写**） | 0=通过（末行必是 `EVIDENCE: … rc=0 mode=real-data`）；1=检出违规；2=fail-closed 无法判定；**3=SKIP（唯一可放行档）**；4=domain-unavailable（**不产出结论**） |
| 门的放行条件 | **两通道同时**：① 末行＝具名 SKIP 横幅（`CLOSE-READINESS SKIP[<分类>]（N 条判据未执行：…）——其余 M 条已验，**本档不是通过**`，单一真源＝`verify_close_readiness.py::verdict_line`）；② rc=3。**任缺其一判红**；rc=1/2/4 一律判红；rc=0 但末行不是机读证据行也判红（两通道矛盾 ⇒ fail-closed） |
| 形态判据的**两档**（批 6 实测发现的新假红路径） | pwsh 解码子进程输出用 `[Console]::OutputEncoding`（与控制台代码页耦合）：步骤 `env:` 有 `PYTHONUTF8=1`（python 侧 UTF-8），但**解码侧**若不是 UTF-8，横幅 CJK 段变替换字符 ⇒ 形态判据恒不命中。故：① 全形态（CJK 逐字在位）；② 编码降级档（非 ASCII 投影后前缀仍 `CLOSE-READINESS SKIP[分类]` 且行尾仍 `**`）。**②不比①宽**：real-data 模式下该前缀**只有** `verdict_line()` 的 SKIP 分支会产出（失败档 `CLOSE-READINESS FAIL`／无法判定 `CLOSE-READINESS-ERROR`／域不可派生 `DOMAIN-UNAVAILABLE`／成功档 `EVIDENCE:`＋`CLOSE-READINESS PASS`），而它同一条 f-string 必然带 `**本档不是通过**` ⇒ 两档在**可达状态上等价**（去掉的只是对终端编码的依赖）。**两种编码下九条反向对照结论逐条相同** |

**四条反向对照（真驱动：门字节从 `ci.yml` 标记之间逐字取出、真 `pwsh` 跑；A/B 系列为 `%TEMP%` 注入桩）**：

| 用例 | 期望 | 实测（`rc` 为**门自身**的退出码） |
|---|---|---|
| A1 真失败 rc=1 | 判红 | rc=**1**，末行 `verify_close_readiness.py --sprint rc=1` |
| A2 fail-closed rc=2 | 判红 | rc=**1** |
| A3 **裸 rc=3 无横幅** | 判红 | rc=**1**，末行 `…rc=3 但不是具名 SKIP 的放行形态 ⇒ 本步失败` |
| A4 rc=3 准横幅（有 `SKIP[分类]`、缺 `（N 条判据未执行：` 段） | 判红 | rc=**1**（**两种编码下都判红**） |
| A5 rc=4 domain-unavailable | 判红 | rc=**1**（不被当成 SKIP 吞掉） |
| B1 **具名横幅 ＋ rc=3** | 放行 | rc=**0**，上屏 `**账本类判据未执行、本档不是通过**`；形态档 ①（utf8）／②（legacy 编码失配） |
| B2 具名横幅 ＋ rc=0 | 判红 | rc=**1**，末行 `rc=0 但末行形态不可核` |
| B3 具名横幅 ＋ rc=2 | 判红 | rc=**1** |
| B4 rc=0 ＋ 真机读证据行 | 通过（正向对照） | rc=**0**，`checked 1 sprint doc(s) declaring a real anchor` |

**两环境实测（同一门字节；`OLD` ＝`git show HEAD:.github/workflows/ci.yml` 的该步骤体逐字取出）**：

| 门 | 环境 | 步骤 rc | 判读 |
|---|---|---|---|
| OLD（HEAD，无门） | 无账本克隆 | **1** | 复现批 5 的遗留红：`Program "python.exe" ended with non-zero exit code: 3` ⇒ 该步中止（假红） |
| NEW | 无账本克隆 | **0** | 两份 Sprint 文档（sprint-17 run 表 12 行／sprint-18 18 行）各 rc=3 ＋ 具名横幅 ⇒ 放行；`checked 2 sprint doc(s)` |
| OLD | windows 工作树（有账本） | **1** | sprint-17 真数据档 **FAIL 9 项**（`[C1/需求]` 1 ＋ `[linkage]` 7 ＋ `[C3]` 1 项点名 27 个提交无归属）⇒ **改动前就红**，与本门无关（此前该循环遇 rc=1 同样中止） |
| NEW | windows 工作树 | **1** | 同上（门把 rc=1 原样判红，不做任何吞并）——**行为未回归** |

**无账本克隆里两个步骤的护栏各跑一遍**（命令＝`pwsh` 里 `Set-Location <克隆>` 后跑 `ci.yml` 该步骤的
**逐字字节**；解释器＝把 `<真仓>\.venv\Scripts` 前置到 `PATH`（克隆无 `.venv`；裸 `python` 会
`SUITE FAILED (8/26)`）；环境＝步骤自己声明的 `PYTHONUTF8=1`）：

| 步骤 | 末行／关键输出 | 步骤 rc |
|---|---|---|
| `Offline verify suite` | `SUITE PASSED (25 scripts, 1 skipped): verify_agentops.py[ledger-absent] —— 无失败，但 1 个脚本的判据未执行（SKIP≠PASS）⇒ 本档不是通过（rc=3）`＋放行分支上屏"账本类判据未执行、本档不是通过"；随后 `CHECK OK: 57 脚本与 TEST-MATRIX.MD 一致` 〔2026-09-30 批 6 现跑〕 | **0** |
| `Close-readiness gate…` | sprint-17／sprint-18 各 `CLOSE-READINESS SKIP[ledger-absent]（1 条判据未执行：…）——其余 12／18 条已验，**本档不是通过**`；两次放行分支均上屏"账本类判据未执行、本档不是通过"；`close-tax` 两次 `CLOSE-TAX SKIP（…**不是通过**）` rc=0 | **0** |

⇒ **克隆里 `verify` 作业的三个 Python 步骤全绿**（第三个＝`Explicit gate tiers`，rc=0：`CARD-INDEX PASS`／
`MD-TABLE PASS（186 文件）`／`verify_no_policy_hardcode.py ALL PASS (22)`／`verify_lint.py ALL PASS (11)`／
`DECISION-REGISTER PASS`＋`ALL PASS (32)`／`structure-guard.py --replay ALL PASS (68)`／
`structure-guard.py verify --from-git HEAD~1`）。该步骤含 GitHub Actions 表达式
`${{ github.event.before }}`，探针里替换为空串以走 `HEAD~1` 回退（**这是探针侧唯一的替换**；
两处门字节不含任何 `${{ }}` ⇒ "逐字取出"的前提成立）。**未跑**：两个 `npm ci && npm run build`
（需联网安装，与本批无关——**不声称其结果**）。

**"第三处"同族问题的全量盘点（`ci.yml` 里每一处依赖脚本 rc 的调用）**：

| 位置 | 命令 | 脚本非零退出码语义 | 会被同族问题影响？ |
|---|---|---|---|
| 套件步骤 | `run_suite.py --tier offline` | 1=有失败；3=有具名 SKIP **或** `REFUSE_EXIT`（拒绝启动） | **是**（批 5 已加门） |
| 套件步骤末 | `verify_matrix.py check` | 0/1（无第三态） | 否 |
| 关闭前置步骤 | `verify_close_readiness.py --sprint` | 1/2/**3=SKIP**/4 | **是**（**本批加门**） |
| 关闭前置步骤（**同一循环体**） | `verify_close_tax_reading.py --sprint` | 1=FAIL；2=文档不可解析；**SKIP 三处均退 0** | **否**（不会红）；但**方向相反**：它的 SKIP 横幅写着"**不是通过**"却退 0（与 `run_suite.py::skip_mismatch` 同类；且缺 `[分类]` 方括号形态 ⇒ 套件也不认它为具名横幅）。**本批不改**（改成 3 会在同一循环体里**新增**一处 CI 红灯，需另配门）——列为下一批候选 |
| 显式档位步骤 | `verify_card_index.py --check --strict` | 0/1；SKIP 时打 `CARD-INDEX SKIP` 但 rc=0 | 同上（反向；本批不改） |
| 同上 | `verify_md_tables.py` | 0/1 | 否 |
| 同上 | `verify_no_policy_hardcode.py` | 0/1（`SystemExit(str)`＝1） | 否 |
| 同上 | `verify_lint.py` | 1=C 级棘轮；2=ruff 缺席 fail-closed | 否（无第三态） |
| 同上 | `verify_decision_register.py` | 1=FAIL；缺登记册 ⇒ SKIP rc=**0** | 同上（反向；本批不改） |
| 同上 | `structure-guard.py --replay` | 0/1/2 都是真判定 | 否 |
| 同上 | `structure-guard.py verify --from-git` | 0/1/2 | 否 |
| `e2e-optional`（仅手动） | `verify_e2e.py` | 2=缺 key；**3=后端未就绪**（真失败，非 SKIP） | 否 |

**批 6 门槛读数（windows 工作树现跑；本批只改 `ci.yml` ＋ 本档）**：

| 门槛 | 末行读数 |
|---|---|
| `verify/run_suite.py --tier offline` | `SUITE PASSED (26 scripts)`、**rc=0**（零 skipped ⇒ 第三态仍不改动末行形态） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_close_readiness.py --selftest` | `ALL PASS (105 assertions)`；`EVIDENCE: … assertions=105 rc=0 mode=selfcheck` 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_close_readiness.py --sprint docs/iteration/sprint/2026-09-25-sprint-18.md` | `CLOSE-READINESS PASS`：2026-09-25-sprint-18.md（run 表 18 行，锚点 9f8d690f，覆盖提交 72，产出型标注 0）；`EVIDENCE: … assertions=6 rc=0 mode=real-data criteria=6`；rc=0 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_matrix.py check` | `CHECK OK: 57 脚本与 TEST-MATRIX.MD 一致`（**与改动前同值**） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_lint.py` | `ALL PASS (11 assertions)`；C 级棘轮 `D101=12/12 D102=46/46 D103=203/205 E501=**2466**/2494`（与改动前**逐字同值** ⇒ 净新增超长行 0；**未上调任何 cap**） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_artifact_paths.py` | `ALL PASS (13 assertions)｜动态目标 105 处（34 个文件全在棘轮表内且未超上限）`；本批**零新增文件**（`git status --porcelain -uall` 只有 2 个 `M`、零 `??`） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_gate_integrity.py` | `ALL PASS (75 assertions)`；`guard_required=10 ratchets=5`（读数未变——本批**未改**该文件） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_decision_register.py` | `ALL PASS (32 assertions)`；`entries=122 quotes_checked=97 quotes_drift=10 pointers=1248`——**与改动前同数 ⇒ 漂移净新增 0**（本档改动＝**文件末尾追加**，不动任何既有行号） 〔2026-09-30 批 6 现跑〕 |
| `verify/verify_md_tables.py` | `MD-TABLE PASS（186 个文件解析通过；其中 4 个历史文件走棘轮基线、均在各自的 defect 上限内）` 〔2026-09-30 批 6 现跑〕 |

**本批没做的事（如实记）**：① 未改任何 `verify/**` 脚本、未改 `VERIFY_META`（故 `verify_matrix.py check`
读数与改动前同值；`derive` 无需重跑，已现跑 `check` 复核）；② **未给 CI 门加机检钉**——
`verify_gate_integrity.py` 不检查 `ci.yml` 里门标记是否存在，故**删掉整段门不会让任何闸门变红**
（这与批 5 的套件门同属**未闭环项**，列为下一批候选；本批只交付"门在位 ＋ 反向对照真驱动"）；
③ 未把"SKIP 退 0"的脚本（`verify_close_tax_reading.py` 等）改判（见上表处置）；
④ 未放宽任何判据、未上调任何 cap／timeout、未对 skipped 取 0 换绿。〔2026-09-30 批 6 现跑〕

> 源行区间 `412-508`（共 97 行）｜搬出前后 `sha256 = 8058e687b635916836424f29fbf540d517dfb29930a8e0a7555cb74f019b3c5d`。

---

<a id="修复不合格6条"></a>

### A. 修复不合格（6 条，与"耦合"无关）

| # | 事实 | 当时哪条命令就能发现 | 当时没跑它的原因 |
|---|---|---|---|
| 1 | 批 3 的 `087-major-3` 修法**在真入口完全没生效**（091 判 critical） | 最小真 git 仓库里跑一次真 `git commit` | 只跑了 `--replay-git` 的**单元自检**，把"自检绿"当成"入口通" |
| 2 | `1d(b)`（登记册自身被删）只修了一半 | 用同一条判据对**文件本身**跑一次 | 只按 089 给的 `1d(a)` 字面修 |
| 3 | `commit-msg` 成功路径不打印 `[署名删除]` | 直调钩子看 stdout | 只关心 rc，没看输出是否兑现文案 |
| 4 | `_invokes_guard` 黑名单残留原样留着 | 用 `Write-Output` 形态探针跑一次 | **已修**（`61494c9`）：`_invokes_guard` 由黑名单改**词元级结构判定**；行尾注释／变量赋值／`Write-Output` 三种冒充**修前 0 项假绿 → 修后逐条点名**；真调用与 `Write-Host` 标签不回归 |
| 5 | 批 3 提交信息称"四条 major 全部收口" | 对着 089 的残留清单**逐条数** | **已修**（`61494c9`）：`_installs_hooks` 改 `ast` 解析 `HOOKS` 结构；注释假冒修前假绿→修后点名，**并消除一个既有假红**（合法 `HOOKS = [...]` 原先被误判） |
| 6 | 091 再次判"过度声称" | 同上 | **已修**（`61494c9`）：新增「本地层终判必须由退出码承载」判据（逐调用判 ＋ 终判层单列）。三层全 `--report-only` 修前**无任何判据在判**→修后点名；仓库现状（批 7 的单层 report-only）不误报。**口径偏离已由父代理认可**：A 表原文「数层数」会落进 E3 自己写的反证（只看层数不看退出码⇒又变回 fail-open） |

> 源行区间 `44-54`（共 11 行）｜搬出前后 `sha256 = 04324a5413827c853902ede407d56b18a8415414560c9b66be172c0083e8e964`。

---

## 逐字保留证明（搬出前后的逐段 sha256）

| 段 | 源行区间 | 行数 | sha256（搬出前后同值 ⇒ 逐字未改） |
|---|---|---|---|
| `s5表的口径与机制说明` | 158-165 | 8 | `6e1050fc781340dd6d2a702ade67ad58de86ee753402f076f075be06956b7725` |
| `对话纪要逐字原话13条` | 77-94 | 18 | `fd2d30702c3f9a66fd86c397e0d58a05dde9613946ab7d42c9f405a1e0dd5602` |
| `s51` | 233-270 | 38 | `a6851b64d513260d7953eb8e00d53b6207e03bbf9b59fb5299986f697d900f9a` |
| `待裁定清单p1p8` | 271-285 | 15 | `e9a15d153d5f894c9cdf2a06c390c052abd673bd0491fe08d4967899c96deef5` |
| `未做项与局限` | 286-295 | 10 | `cb4c7d555d6325d9243df5a5eb43c70b21beea8721ba0a9ab352d836b27033ea` |
| `本批门槛读数` | 296-353 | 58 | `52ee800c8cba7fc93c232fba0e346c007a041094004c9147ec754a052c7cf0d3` |
| `g3输入` | 354-367 | 14 | `ac664c0a29e74c9186493eec30a21dd40da0cb69ddea0b72e33bc927b4dd301b` |
| `账本时间戳退化` | 368-411 | 44 | `5025390c7ff1d4a67f7bc2931a744c819caa77bedbf73750846f58a501b5780d` |
| `ci放行的第二处落点` | 412-508 | 97 | `8058e687b635916836424f29fbf540d517dfb29930a8e0a7555cb74f019b3c5d` |
| `修复不合格6条` | 44-54 | 11 | `04324a5413827c853902ede407d56b18a8415414560c9b66be172c0083e8e964` |

**核验方式（任一人可复跑）**：用收敛批**之前**的版本取出上表行区间，逐段算 `sha256`，应与本表逐字相同：

```
git show <收敛批之前的 rev>:docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD
```

同时，活文档里每一处移走都留了**一行指针**（`叙述已移入 <本档>#<锚点>`），反向可查。
