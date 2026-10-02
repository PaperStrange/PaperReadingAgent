# G2（治理批）关闭复盘 · 2026-09-26

> **定位**：G2 = `docs/iteration/sprint/2026-09-25-governance-batch-plan-G2.MD` 的六个批次（D1~D6，12 点规划 ＋ 用户插入卡 `TG-20` 2 点）；Sprint 文档 = `sprint/2026-09-25-sprint-18.md`。
> **本文件是 G2 复盘的唯一真源**；Sprint 文档 §8.3/§8.4 只保留指针与一句话摘要（引用纪律：不得复制正文）。
> **收敛批（2026-10-03，`run-2026-10-03-implementation-120`）**：按用户 2026-10-02 裁定「先收敛、再解决合并面」对本档减量——**活文档只留「当前状态 ＋ 未闭环项」**。
> **未改的东西（本批的边界）**：§5 状态表的**行集合与 `状态码` 逐行语义**、机读 `状态计数:` 行、§5.0 逐行对钉表**一律未动**；被移走的叙述**逐字**进归档档，原位置留指针。
> **关闭状态：未关闭**。用户 2026-09-26（UTC+8）裁定：
> 主代理自定的「债口径（没有闸门覆盖 ⇒ 不挡关闭）」不可信、予以撤回 ⇒ **一查/二查判出的未闭环项**
> 按既有先例（Sprint-17 §9：三查结论 = 关闭阻塞项）**仍属关闭阻塞项**，直到逐条闭环或**由用户逐条豁免**。

## 0. 范围与读数（时点读数，非现值）

| 项 | 目标 | 实测 |
|---|---|---|
| 计划点 / 实际点 | ≤14（不含关闭税） | **14 / 14**（规划 12 ＋ 插入 `TG-20` 2），余量 0 |
| M1 关闭税 | `code major ≤ 2` 且 `文档项 ≤ 3`，三查一次通过 | **code 5 major ＋ 3 critical / 文档项 12** ⇒ **未达标**；三查重跑 0 次（合计判出 一查 12 ＋ 二查 windows 9 ＋ 二查 main 8 项） |
| M2 | 五项违规指标全 0 | 见 Sprint §8.1（未跑〇查即派评审 0／锚点后未评审提交见锚点注／窗口内 `self-chosen` 无 deviation 0／§9↔账本 0／抽查见 §9.5） |
| M3 | 无零提交日 | 达标有保留：六批全落在 **2026-09-25** 一天内，关闭期为 **2026-09-26 00:51（UTC+8）** 起 |
| 红线 | 0 | **R1 编辑边界同型 4 次**（全在关闭期、同一天、**全部靠 `read` 复核发现，闸门一条都抓不到**）⇒ 不达标 |

**变更集**：`1cad0b7..9945d6d` = 46 文件 / **+5565 −147** / **24 提交**（`git diff --shortstat` 现跑；
原记录写 +5585/−148、25 提交，属「手抄/推算」，已按现跑更正）。`paper-qa-script/**` **零改动** 〔2026-09-26 时点记录，以现跑为准〕
⇒ 本期全部风险都关在治理层内。

> **本节的数字一律是「标明时点的历史读数」，不是现值**——现值以各自命令现跑为准（`git diff --shortstat 1cad0b7..9945d6d`、`git rev-list --count 1cad0b7..9945d6d`）。

## 1. 关闭三查与修复验证（2026-09-26 时点记录）

| 环节 | run | 结论 |
|---|---|---|
| 〇查（scope） | `run-2026-09-25-impact-assessment-085` | `tier = full`；composite **69.36**（原记 69.38，按同式复算更正） |
| 一查 | `run-2026-09-25-doc-audit-086` | must-fix 9 / should-fix 3 |
| 二查 · windows | `run-2026-09-25-code-review-087` | 0 critical / 4 major / 5 minor；并明确「没有放宽任何棘轮」 |
| 二查 · main | `run-2026-09-25-code-review-088` | 3 critical / 1 major / 4 minor / 1 nit；三条 critical 同形态（新闸门把 windows-only 的 `docs/iteration/**` 当前提） |
| 修复验证 批 1+2 | `run-2026-09-26-code-review-089` | 0 critical / 4 major / 5 minor / 2 nit；另记「提交信息过度声称」 |
| 修复验证 批 3 | `run-2026-09-26-code-review-091` | **1 critical**（我批 3 的修法在真入口完全没生效）/ 1 major / 4 minor / 1 nit |
| 修复验证 批 7 | `run-2026-09-26-code-review-092` | 0 critical / 1 major / 4 minor / 1 nit；**确认 091 的 critical 真闭环**（真 `git commit` 修前/修后对照），并**新报一条存量 major**（structure-guard 对「整份文件消失」fail-open） |

`run-092` 的覆盖上界显式钉为 `958c739`（不用「收尾时 HEAD」）。

**二查 · main 的三条 critical 是同一个形态**：新交付的闸门/自检把 `docs/iteration/**`（**windows-only**）当成「必然存在」的前提 ⇒ 落到 main 形态树上必红。
**归属用基线对照证明，不靠推测**：干净 `origin/main` ⇒ 套件 `SUITE PASSED`；`origin/main` + 本变更集 ⇒ 套件 `SUITE FAILED`（3/26）⇒ **确认是变更集引入的**。

**三查重跑 0 次** ⇒ 字面「一次通过」成立；但**这一条必须与 §0 的 M1 读数分开读**——一次通过只说明评审本身没崩，不代表被审对象合格。

**修复验证复核与关闭三查是两件事**（`1-WORKFLOW.MD` §4.2）：复核**分节记录、不计入三查覆盖**。

**批 7（091 critical 的修复）**：本地层**判权按信息可得性分层**——`pre-commit` 改 `--report-only`（读不到署名 ⇒ **不许终判**），**终判交给 `commit-msg`** 与 CI。
真入口 e2e（最小真 git 仓库 ＋ 真 `git commit`）：带署名的结构删除 ⇒ **rc=0**（修前 rc=1）、无署名删除 ⇒ **rc=1**（终判没被吞）。
同批两条常设判据：① `verify_gate_integrity.py` 新增「**安装器 `HOOKS` 必须同时装两个钩子**」；② 结构守卫新增 `--report-only` 档（读不到署名时既不 rc=1 卡死合法删除、也不打 PASS 冒充通过，改打 `STRUCTURE REPORT-ONLY` 横幅）。

## 2. 修复质量复盘（主代理自查，用户要求「我需要真实」）

**判准只有一条：每条失误，当时哪一条命令就能发现它。**

**A. 修复本身不合格（6 条，与「耦合」无关）**——逐条明细（事实 / 当时哪条命令就能发现 / 当时没跑它的原因）**已移入** `docs/iteration/archive/2026-09-26-g2-close-retro-archived-narrative.MD`#修复不合格6条。

**B. 真属于耦合的（4 条）**：`1d(a)`（共享 `agent_policy.path_in_head` 被两个闸门消费）／installer 判据缺失（判权从 `pre-commit` 移到 `commit-msg` 后长出的新面）／`acks_from_text` 一函数两档复用／登记册指针漂移（用行号当稳定标识）。

**C. 结论**
**「越修越多」的主因不是耦合——6:4，主因是修复不合格。**

**共同形态**：**用间接证据（自检绿 / 我的记忆 / 字面清单）代替直接证据（真入口 / 来源报告逐条 / 现跑探针）**。
它与 `3-LEARNED` **1.68** 同族——我把那条用在「标识符」上，**没用在自己的修复验收上**；A 组缺直接证据、B 组缺解耦设计。

**自我验收三件套（缺任一条该批不得标记完成）**：① **真入口复现**（命令 ＋ 输出）；② 对着**来源报告**逐条核残留（不凭记忆）；③ 改动对象对应的**最小探针**现跑。

**D. 一条被撤回的自定口径**：主代理曾在 Sprint §9.6 用「没有闸门覆盖 ⇒ 不挡关闭」把 7 项划成「债」。
该判据**是自定的**：本仓没有「关闭阻塞项」的定义，最接近的 `1-WORKFLOW.MD:161` 要求豁免**「经用户确认」**。
⇒ 已撤回；严格口径下这些项**仍挡关闭**。

## 3. 与用户的对话纪要（**逐字保留原话**）

**用户 2026-09-26 要求逐字保留；13 条原文 ＋ 我的处置已移入** `docs/iteration/archive/2026-09-26-g2-close-retro-archived-narrative.MD`#对话纪要逐字原话13条

> **该节是逐字原话的唯一落点之一**；与本档冲突时以归档档的逐字原文为准。
> 摘要：用户在该轮提出 ① 进度可见性（不要让我追问）② 成本/ROI 要能测算（报价表须多档、按时段计价）
> ③ 「G2 的交付质量让我不能相信你的严重性判断，我需要真实」④ 越修越多的主因是不是耦合
> ⑤ 「思考太快，快到我不相信你认真评价反问思考过」⑥ finding 依赖图与义务索引可做成独立 spec
> ⑦ 「不要以我能拦得住为前提设计我们的沟通方式」。

## 4. 未闭环项与归档指针

**§5 状态表（下）＝ 未闭环项的唯一真源**；本节的机读计数行由 `verify/verify_close_tax_reading.py` 逐行复算：

**状态计数（机读，2026-09-30 本轮现跑；供闸门逐行复算）**：状态计数: 已修=46 未修=0 部分=0 只报=0 用户豁免=5 合计=51

> **词表与逐行判据（2026-09-30 时点记录）**：`状态码` 列**只允许五元**（`已修`／`未修`／`部分`／`只报`／`用户豁免`）；
> **每行的判据来源按三档取**：① 该行 `状态说明` 单元格里写的落地提交；② 该提交的**文件清单与代码内容现读**核对——**提交信息只是线索、不是证据**；③ ①与②冲突时**以代码现读为准**并写改判理由。
> **`只报`／`未修`／`部分` 都不是豁免**（按 `D-250926-06` 的「零未闭环项」口径仍计入关闭判定）；
> 行 14／43／45／46／51 为**用户单次豁免**（行 43／45／46／51 = `D-250930-01`，**非永久、不构成先例**；四行的**性质仍是「只报」**）。
> **本表扩容与取值口径、三张独立编号表的机制说明、行 45／46 父代理裁定署名、行 48 残留义务转移**：**叙述已移入** `docs/iteration/archive/2026-09-26-g2-close-retro-archived-narrative.MD`#s5表的口径与机制说明

**§5.1～§5.4 / §6 / §7 / §8 —— 叙述已移入** `docs/iteration/archive/2026-09-26-g2-close-retro-archived-narrative.MD`（锚点：#s51、#待裁定清单p1p8、#未做项与局限、#本批门槛读数、#g3输入、#账本时间戳退化、#ci放行的第二处落点）

**未闭环项（一句话清单；证据与去向见 §5／§5.0 与归档档）**：① `_invokes_guard` 曾是黑名单（行 4，2026-09-30 已改命令位置判定）；② `_norm_sprint` 两份实现（行 7）；③ `%TEMP%` 固定名夹具（行 8）；④ `derived_numbers` 的 WARN 被 `warnings[:20]` 截断（行 9）；⑤ `.github/workflows/ci.yml` 标签写死条数（行 10）；⑥ 三处 `.py` docstring 陈旧计数（行 11）；⑦ `6-DECISIONS.md` §4.1 待回填（行 12）；⑧ **CI 门标记无机检钉**——`verify_gate_integrity.py` 不检查 `ci.yml` 里门标记是否存在，删掉整段门不会让任何闸门变红（**本条未闭环，列为下一批候选**，见归档档#ci放行的第二处落点）。

> **注**：本节只列「现在不做 / 做不了」的项；**已闭环的行逐条证据见 §5.0**，不再在本节复述。

## 5. 未闭环项（**关闭阻塞**；关闭标准＝**零未闭环项**，2026-09-27 00:06 UTC+8 用户裁定 `D-250926-06`）

> **关闭标准（时效）**：G2 与 G3 **均按「零未闭环项」执行**；**不回溯 G1**（Sprint-17 在「按声明关闭」的旧形态下结案）。
> **行号次序是历史次序、不是流水号**：行 17／18 排在 19–25 之后；**本表不重编号**（仓规：历史不改号，且多处按号引用）。
| # | 项 | 来源 | 状态说明（依据） | 状态码 |
|---|---|---|---|---|
| 1 | `structure-guard` 对"整份文件消失"fail-open（164/172 份删掉即隐身，三层全走该路径） | 复核 `092` major | **批 9 已修**（`1d394d8`）：真入口两例 ＋ 自检 12→15 条 | 已修 |
| 2 | `087-minor-5` 围栏剥离／表格单元格／重复字段判据**只做了 1/3** | 089 判定表（部分闭环） | **现读＝已修**（`1344102`）：原文取证**更正为 0/3**（三项一项都没做、`Fix` 段实列**五件事**，行号已漂移，详见 [取证档](2026-09-26-087-minor-5-9-disposition-spec.MD)）；该五件事已由 `1344102` 全部落地（判据 8–12），取证档 §C.1 逐字"五项全部落地"；判据见 §5.0 行 2 | 已修 |
| 3 | `087-minor-9` sprint-18 成片过期计数（部分） | 089 判定表（部分闭环） | **现读＝已修**（`1344102` ＋ `28bc182`）：四类形态已落地；**原记"部分"所依据的两处基准漂移如实保留**——① `ci.yml` 写死条数实际**已闭环**（`28bc182`，晚于 089 覆盖上界），而 `sprint-18` §9 区自述仍写"标签写死 12 条"＝**该自述本身已过期**（**现读已清，grep 0 命中**）；② 089 判定表该行的"已改/未改"清单**不可用**（`75324f9` 对 sprint-18 **只改两行**，判定表所引行号错，且把 `ci.yml` 同时列进"已改"与"未改"）——②是**复核产物**的缺陷，不是本仓判据缺口；判据见 §5.0 行 3 | 已修 |
| 4 | `verify_gate_integrity.py::_invokes_guard` 仍是黑名单 | 089 minor | **现读＝已修**（`61494c9`）：由黑名单改**命令位置 ＋ 词元级结构判定**（`bool(_guard_command_lines(text))`），假绿三种形态逐条点名；判据见 §5.0 行 4 | 已修 |
| 5 | `_installs_hooks` 停在文本子串层（注释可糊弄；`HOOKS = [...]` 假红） | 复核 `092` minor | **现读＝已修**（`61494c9`）：改 `ast` 解析 `HOOKS` 结构（`_hooks_from_ast`），注释假冒判红、合法字面量不再假红；判据见 §5.0 行 5 | 已修 |
| 6 | **没有任何判据守着"不许所有层都加 `--report-only`"** | 复核 `092` minor | **现读＝已修**（`61494c9`）：新增"本地层终判必须由**退出码**承载"判据（逐调用判 ＋ 终判层单列 ＋ 吞码形态判否）；判据见 §5.0 行 6 | 已修 |
| 7 | `_norm_sprint` 两份实现 | 088 minor | **已修**（`8b03c77`）：写入侧唯一实现、读取侧保留**不导入**的独立镜像，同义性由**一致性向量**守；**父代理验了写入侧漂移**（扰动写入正则 ⇒ 向量点名 A07/A15 并 rc=1） | 已修 |
| 8 | 自检夹具 `%TEMP%` 固定名（并发互踩） | 088 minor | **已修**（`31ceb6e`）：5 个脚本的固定名夹具改为 `mkdtemp` run 级唯一目录（含回收：`try/finally`／`atexit`；实测坑：decision_register 的真 git 仓库只读 `.git/objects` 让 `rmtree(ignore_errors=True)` 静默半途而废，改为先清只读位）。**反证（真并发）**：修前 96 个实例运行里 **10 个失败**（互踩实证：见证文件被删/覆盖、`PermissionError`、反向对照假绿），修后同装置 **0 失败**；`run_suite` 连跑 5 轮全绿。断言/条数/cap 一字未动 | 已修 |
| 9 | `derived_numbers` 的 WARN 被 `warnings[:20]` 截断 | 088 minor | **已修**（`28bc182`）：截断改为自曝"另有 N 项未列出" | 已修 |
| 10 | `ci.yml` 写死条数（088 要的是"不写死"） | 088 nit | **已修**（`28bc182`）：标签不再写死条数 | 已修 |
| 11 | 三处 `.py` docstring 陈旧计数 | 批 5 子代理"未做"清单 | **现读＝已修**（`b271606` ＋ `43a65e2`）：写死的"含 N 条反向对照自检"改指现跑末行（3 文件 4 处）；UC 区间与 `1-WORKFLOW` 的同类计数由 `43a65e2` 收口；判据见 §5.0 行 11 | 已修 |
| 12 | `6-DECISIONS.md` **105/117 条 `待回填`**（闸门 WARN：回填前不得引用为已核生效裁决） | 闸门 WARN | **已修**（`1f31475` 等四批）：全量回填完成，剩余条数以闸门现跑为准 | 已修 |
| 13 | `verify_close_readiness.py` 对 `queued` run（`started_at=None`）判"数据被改过" ⇒ 整档 rc=4 | 复核 `092` minor | **现读＝已修**（`df5fd73`）：改显式 `SKIP[窗口/未起跑]` 并上屏点名（"未起跑"≠"数据被改过"）；终态＋坏时间戳仍 fail-closed；判据见 §5.0 行 13 | 已修 |
| 14 | **G2 属 S1 档（R1 = 立即硬停），但 §8.1/§10 只记"当日修复 ＋ 全闸门复跑"，未记录硬停动作与恢复所需的用户二次确认** | 登记册回填批次 3 的 V-035 判定提出 | **用户单次豁免**（2026-09-26 原话："我很想让你体验惩罚，但是这次算了，按我单次豁免记录"，登记为 `D-250926-05`）——本次不执行硬停、不倒填、不裁定条款不适用；**规则原文不改**，再次触发仍按 S1。**记为豁免，不是"已修"** | 用户豁免 |
| 15 | `scripts/fetch-prices.py::parse_deepseek` **已完全失效**：要求"3 模型 ＋ ≥18 个 `$`"，而官方表现已是 **2 模型 / 12 个 `$`** ⇒ 抓取恒返回 `{}`、价表静默停在 `2026-09-20` | 价表多档改造＋父代理独立复现 | **已修**（`1ed6f93`）：解析器重写（按 `<tr>` 顺序、容忍模型数、支持中文页"元"），`--check` 现跑 `2 models`（改前恒 0）；加"抓空/过旧"判据。**本批更正签发**：原记 `1344102`，但该提交的文件清单不含 `scripts/fetch-prices.py`（现读 `git show --name-only 1344102`），重写落在 `1ed6f93`（同一提交的提交信息逐字写"行 15 已修"） | 已修 |
| 16 | 价表**扁平键仍是过渡态**（只镜像 `peak`）；`prices-derive` 白名单只覆盖 `auto` 段、顶层新键会被静默丢弃 | 价表多档改造 | **已修**（`1ed6f93` ＋ `d1204b8`）：`agent-ops` 与 `app/usage` **两条链路都按时刻选档**（前者真入口夜间 `0.01208124 → 0.0060408`、后者 `0.002 → 0.001`，均精确 2.0×）；白名单纳入 `_tiers`＋"派生后档位仍在"判据。扁平键**保留为垫片**（仅对无档位数据的调用生效），不再决定夜间金额 | 已修 |
| 19 | **账本没有合法的撤回/删除路径** ⇒ 任何误登记的 run **永久**留在判定域里 | 价表批的验收 run `097`~`099` **误写入生产账本**（正确形态＝隔离账本 `AGENT_OPS_DIR=%TEMP%`，守卫批就是这么做的）⇒ `verify_ledger_measurement` 报 `zero_duration`，而该闸门现处"严格判定、无上限"域，历史棘轮余量吃不到这一批 | **已修**（`df5fd73`）：新增 `retract`（≥10 字符理由／顶层 `retractions[]` 七字段留痕／只认显式点名 id／`--evidence` 必须存在／产物移入 `runtime/retracted-runs/`／被引用者与重复撤回 fail-closed）。生产账本 `097`~`099` 已按此撤回，`runs` 102→99；账本闸门**凭该机制**由 rc=1 转 PASS。**未用 `set-started-at` 伪造时间戳** | 已修 |
| 20 | **实际用量的成本展示仍按高峰计价**：`paper-qa-script/app/usage.py` 只用扁平键（`:123`/`:124` 读 `input_cost_per_token`/`output_cost_per_token`，**全文无 `_tiers`**） | 价表批具名缺口（**父代理读码复核**） | **已修**（`d1204b8`）：按调用起止时刻选档，跨档墙钟加权且**逐分支镜像** `agent-ops` 的实现；真入口夜间 `0.002 → 0.001`（**精确 2.0×**，前置断言该用例确实落在空闲窗口内）、高峰同值、跨档 `0.0015`。**并更正我原先的因果判断**：我写"该链路**没有选档输入**"是**错的**——litellm `integrations/custom_logger.py:378-389` 的 `log_event` 本来就以 `(kwargs, response_obj, start_time, end_time)` 调回调（父代理读码独立复核），**输入一直在，缺的是消费方没用它** | 已修 |
| 21 | `scripts/hooks/pre-commit` **成功路径的 `exit 0` 是常量**，不是守卫的退出码；文件注释却写「非 0 一律拒绝提交」⇒ 「本地层由退出码承载」目前**不是字面事实** | 行 6 批实测暴露（父代理受理） | **已修**（本批，父代理独立复核）：尾行改为 `exit $rc`——本层 rc **就是**守卫的 rc；**并保留 `--report-only`**（本层只报告不终判，没被改成强制拒绝）。`verify_gate_integrity.py` 断言 43→50 PASS、`verify_matrix.py check` OK。**交付过程如实记录**：该批**中途失败、未交回执**，四条修法由父代理在工作区逐条核实（`exit $rc` 在位、`_check_ok` 已重写、`:53` 的「7 条」已清、编译 rc=0）后才收下 | 已修 |
| 22 | **同族残留两处**：① `_check_ok`（安装器 `--check`／`commit-msg` 的 `--ack-file`）仍是**裸文本出现**判定；② `ECHO_PREFIXES` 仍是**回显动词清单**，未列入者（如 `Out-Host`）仍可冒充接线 | 行 4/5 批自报残留 | **已修**（同批，父代理独立复核）：① `_check_ok` 由裸文本改为**结构判定**（docstring 写明修前形态「注释里写一行字面即可满足」并点名两处假绿）；② 命令位置判定改为**默认判红**，`ECHO_PREFIXES` 只用于识别回显、不再承担接线判定 | 已修 |
| 23 | **改了 SSOT 却漏收尾动作**：`df5fd73` 与行 20 批分别改了 `verify_ledger_measurement.py`／`verify_usage.py` 的 `VERIFY_META` **却没重新 `derive`** ⇒ `TEST-MATRIX.MD` 与脚本元数据漂移、`verify_matrix.py check` **rc=1 而无人发现** | 行 11 批实测发现（并顺带修好） | 已修（`b271606`）＋**立规**：凡改 `VERIFY_META`，**同一批必须 `derive` 并给出 `check` 末行**，否则把红留给下一个人 | 已修 |
| 24 | `verify/verify_local_dir.py` 的共享对象是**固定端口 8787**（`verify/e2e_common.py:24`）＋仓库内 `verify/verify_local_dir_server.log` ⇒ **套件内偶发失败、单跑必过** | 行 8 批实测并**明确判定不归行 8**（该脚本修前就已是 `mkdtemp`；批方没有假装修好一个不存在的洞） | **已修**（`14603c2`：生产侧端口读 env ＋ `86625c7`：夹具侧 run 级端口）。**举证方＝父代理（派单方）**，逐字：亲跑反证＝**3 轮 × 两实例并发、rc 全 0、`ALL PASS (7 assertions)`、8787 全程无人监听**（原记关闭动作＝端口改 run 级分配或先探测空闲端口＋日志落 `%TEMP%`） | 已修 |
| 25 | **夹具目录只建不回收**：`verify/verify_usage.py:96`（`g2l20-before-*`，**由行 20 批引入**）与 `verify/verify_runner.py:113`（`verify_runner_*`）实测**每跑一次各 +1 个 `%TEMP%` 目录**（名字唯一⇒非互踩位点，属资源泄漏） | 行 8 批实测 | **已修**（`86625c7`：`mkdtemp` 回收）。**举证方＝父代理（派单方）**，逐字：亲量连跑两轮 `g2l20-before-*`／`verify_runner_*` **净增 0**，两脚本 `ALL PASS (61/46)`（原记关闭动作＝纳入回收或改 `TemporaryDirectory`） | 已修 |
| 17 | 守卫**拒绝路径会留孤儿产物**：`--result-file` 的按字节复制发生在守卫之前 ⇒ 被拒后 `runs/<id>/` 多一份产物而账本行仍是 `running` | 守卫交付回执 ⑤2（父代理知悉，未擅动） | **已修**（`df5fd73`）：产物复制推迟到守卫之后（新 `_copy_result_file`）；真入口＝拒前/拒后 `runs/<id>/` 清单两侧均空、账本行仍 `running` | 已修 |
| 18 | 具名豁免的**理由文本未落账本**：行内只记 `measurement_flags=['zero_duration']` 与 `measurement_source='declared'`，理由只上屏（**父代理独立探针 v2 实测**） | 同上；回执 ⑤1 的表述须更正（"未落账本"只对**理由文本**成立，豁免事实**有**落库） | **已修**（`df5fd73`）：裁定选项①，CLI 放行时写 `degenerate_reason`（原话）＋闸门两条判据。**现跑抓到的更正**：判据须用**重算 flags** 而非行内存储的 `measurement_flags`，否则会把「受控回填修好起点、行内标记陈旧」的 `092` 追溯判红 | 已修 |
| 26 | major：`verify_close_readiness.py` 的"未起跑 ⇒ 显式 SKIP"只看 `started_at` 可解析性、**不看 `status`** ⇒ "终态 run 的时间戳坏掉"被当成"未起跑"静默剔除（2026-09-29 于 `bf41d200` 现跑探针：`problems=[]`、窗口照常推导、整档不 rc=4），而同一函数对**候选作用域 run** 的坏时间戳是 fail-closed 的 ⇒ 自相矛盾 | 二查 windows `code-review-104` major 1 | **已修**（`a3a3f25`）：新增 `_terminal_statuses()`，终态＋坏时间戳改判具名数据缺陷；防假红＝`queued`＋同一坏时间戳仍 SKIP | 已修 |
| 27 | major：`retract --evidence` 用 `Path(ev).exists()` ⇒ **目录也算凭据**，且留痕七字段**无任何 hash** ⇒ 证据事后可任意改写／删除而留痕看不出来（生产账本已有 3 条真实留痕，其 `evidence` 指向仍在版本库、仍可编辑的复盘档） | 二查 windows `code-review-104` major 2 | **已修**（`a3a3f25`）：改 `is_file()` ＋ 留痕记 `evidence_sha256`；改写证据后 CLI 报"与留痕记录不一致"并拒绝 | 已修 |
| 28 | major：`_retract_cited_by` 只普查 `scope_source` 一个字段，而 `result_files` 同样逐行承载 run 引用（探针：79 行含 `runs\<run_id>\…` 形态）；且"先撤引用者、再撤被引用者"可绕过（探针 `rc=0`）⇒ 引用链保护只是**快照检查**、不是不变式 | 二查 windows `code-review-104` major 3 | **已修**（`a3a3f25`）：引用面改为数据驱动（`result_files` 一并查）；该时序路径现被 CLI 拒绝 | 已修 |
| 29 | major：`_enforces_exit_code` 判的是"存在一次不带 `--report-only` 的调用"，**从未看退出码有没有被传递** ⇒ 捕获后追加 `\|\| true`（吞码）与 `python … ; rc=$?`（丢弃）两种形态**全部**判 True（假绿）；三层当前恰好都没踩中 ⇒ 属**判据强度**缺口而非现行事故 | 二查 windows `code-review-104` major 4 | **已修**（`a3a3f25`；**2026-09-30 复核 `run-…-114` major 1 后已补第二轮，`状态说明` 按实际判据能力改写**——原文只声明"两种吞码形态现判 False"，而 `a3a3f25` 的判据只认**行首**是命令位置：同一种吞码写成**同一行**（`; echo done`／`; rc=$?; echo done`）时仍判 True ⇒ 自陈强于实际）。**现在能判的形态**（每条都有真驱动反向对照 ＋ `--selftest` 断言；`verify_gate_integrity.py` 断言 68 → **88**）：① 捕获后 `\|\| true`／`\|\| :`／`&& true`／`; true`；② 捕获后 `rc=$?` 存进变量却再没用过（**多行与同行两种写法同判 False**）；③ 调用后**同行** `; echo done`、`; exit 0`、`; exit $((1))`、`\|\| exit 0`、`\|\| exit 1`（常量退出码）；④ 调用后台化 `&`；⑤ 捕获变量被**无条件覆盖**（`rc=$?` 后 `rc=0`）后 `exit $rc`；⑥ 调用行之后还有别的命令、末行常量 `exit 0`。**仍判 True（已知余量，本批明确登记，不是"已治"）**：**未被本判据绑定的变量**（`; exit $rc` 而 `$rc` 不出现在调用行/下一行的捕获里）与**条件内的退出**（`\|\| exit 1`）：二者都是**保守方向**（判否/认承载），且 `ci.yml`＝裸调用、`commit-msg`＝条件分支 `exit 1`、`pre-commit`＝`exit $rc` 三层现状**恰好都没踩中** ⇒ 仍是**判据强度**缺口、不是现行事故 | 已修 |
| 30 | minor：`PY_WORD_RE` 第二支 `[\w${}]*py` 匹配**任何以 `py` 结尾的词**（`copy`／`happy` 判 True，`empty`／`apply` 判 False —— 读数取决于词尾字母而不是结构）⇒ `copy scripts/structure-guard.py verify …` 被判成"解释器 ＋ 守卫脚本 ＋ verify" | 二查 windows `code-review-104` minor 5 | **已修**（本批工作区改动，`verify/verify_gate_integrity.py`）：裸词只认 `python*`／`py`，变量形态**必须带 `$`**（`$py`／`${PY}`／`$py.exe`）。**反向对照 3 条**（真 `_invokes_guard`）：`copy`／`happy` 修前判 True → 修后判无调用；`copy`／`happy`／`empty`／`apply` 四词读数一律 False（不再由词尾字母决定）；6 种真解释器形态（含 `"$py"` 与 `.venv/Scripts/python.exe`）**不回归**。`verify_gate_integrity.py --selftest` 断言 **56 → 59**、`ALL PASS (59 assertions)`（2026-09-29 现跑） | 已修 |
| 31 | minor：`peak_windows()` 与 `peak_windows_from_prices()` 按“第一个 `scraped.*` 命中”**全局**取窗口再套到所有模型；今天恰因只有 `deepseek` 带 `_peak_windows` 而等价于正确口径（成本结论正确）⇒ 属**数据巧合**而非结构保证 | 二查 windows `code-review-104` minor 6 | **已修**（`P1` 裁定＝修；授权集一次性放开 `paper-qa-script/**`）：两侧镜像**同改**为**按该模型所属 provider 取窗口**——`scripts/agent-ops.py` 新增 `provider_of_model()` 并把 `peak_windows_from_prices(prices, model)` 改成取模型参数；`paper-qa-script/app/usage.py` 新增 `provider_of(prices, model)`／`peak_windows_for(prices, model)`（纯函数）＋`peak_windows(model)` 便捷入口；口径＝**窗口随价走**（窗口的 provider 必须与 `_prices_for`／`price_for` 实取的那条价目同属一个 provider；`manual` 非 null／`auto` 兜底 ⇒ `None` ⇒ 如实标 `flat`）。**真入口反证**（修前＝`HEAD` 版／修后＝工作区版；合成价表：`alpha` 带窗口、`beta` 不带而其模型 `b-1` 有 `_tiers`；2026-09-30 现跑）：`agent-ops._estimate_cost(b-1)` 修前 `tier=peak`（**借了 alpha 的窗口**）→ 修后无 `tier` 键（＝`flat`）；`usage._tier_plan(b-1)` 修前 `peak` → 修后 `flat`；对照 `a-1` 两侧同判 `peak`／窗口外 `off_peak`（不回归）、未入册模型两侧 `flat`。**永久判据**＝`verify/verify_usage.py` ⑪14a–f（逐 (provider, 模型) 对照 ＋ 合成表反证 ＋ “窗口随价走”不变式；断言 61 → 66）。**顺带发现（如实记，本批未改）**：两侧的**价格键解析口径**本就不同（`price_for` 走 `_model_candidates` 别名归一以认 litellm 报出的名字；`_prices_for` 按精确键，账本里的名字本就是价表键）⇒ openrouter 的 3 个 `deepseek/*` 命名空间键在两侧解析到**不同价目**，窗口读数随之不同；⑪14b/d 已把它钉成“窗口分歧 ⊆ 价目不同的键 ⊆ 带 `/` 的命名空间键”（差异**具名可见**，不是被抹平） | 已修 |
| 32 | minor：`--apply` 下抓空只 `print WARN`、**不编码成退出码**（`judge_scrape` 的 `strict` 只绑 `args.check`）⇒ "价表是否有效"只能靠人读日志，而 CI 只认退出码 | 二查 windows `code-review-104` minor 7 | **已修**（本批工作区改动，`scripts/fetch-prices.py`）：`--apply` 与 `--check` 共用 strict 判据并把 rc 带回（修前写盘后恒 `return 0`）；**反证＝真子进程跑真 `main()`**（只替换网络边界 `_fetch`、数据目录 `AGENT_OPS_DIR` 隔离到 `%TEMP%`）：修前 rc=0 → 修后 rc=1，写盘仍 fail-safe、真价表未被碰；**永久判据**落 `verify/verify_agentops.py`（3 条，断言 156 → 159） | 已修 |
| 33 | minor：`empty_ops` 夹具**无 `atexit` 兜底**（同函数另两个夹具 `tmp`／`close_sprint_root` 都有）⇒ 该处断言失败提前 return 时永久残留 `%TEMP%`——正是行 25"每跑一次多一个目录"的同族落点 | 二查 windows `code-review-104` minor 8 | **已修**（本批工作区改动，`verify/verify_close_readiness.py`）：`empty_ops` 增 `atexit` 兜底（该夹具命中数 3 → 4）。**反证＝异常路径构造**（真子进程：建目录 → 注册 → 抛异常 ⇒ 退出后残留 0；同装置去掉注册 ⇒ 残留 1）。**局限如实记**：未构造"真 selftest 中途判红"的复现（见§5.3 未做项） | 已修 |
| 34 | nit：本批把多处 `VERIFY_META['features']` 里写死的“含 N 条反向对照”改成“见末行”，方向正确，但**无判据要求 `--selftest` 确实跑到末行判决句** ⇒ 删掉一批自检不会让任何闸门变红（只会让 N 变小，而 N 已不被任何地方钉住） | 二查 windows `code-review-104` nit 9 | **已修**（`P2` 裁定：口径＝**按「条数」**且**必须分支感知**）：`verify/run_suite.py` 新增**判决句 ＋ 条数棘轮**四道判据（`verdict_problems`／`verdict_scope_problems` 两个**纯函数** ＋ `BRANCH_ASSERTION_FLOORS`／`BRANCH_VERDICT_SCOPE_MIN` 两张**按分支实测**的表）：①自陈“条数见末行”的脚本必须**真的打印判决句**（接受 `ALL PASS (N assertions)` 与 `EVIDENCE: <本脚本> assertions=N rc=0` 两种已声明形态；**退 0 ≠ 跑到末行**）；②末行是具名 SKIP 横幅 ⇒ 判红（`TG-19` M-B：SKIP 与 PASS 互斥）；③断言数 ≥ 本分支下限（**只增不减**：删一批 `ok()` ⇒ N 下降 ⇒ 红）；④自陈脚本数 ≥ 本分支下限（删掉 features 里的自陈字样＝把该脚本移出棘轮 ⇒ 红）。**实测下限**（present＝windows 工作树／absent＝“windows 树减 `docs/iteration/**`”镜像，两侧现跑）：`verify_agentops.py` **174／absent 侧无下限**（它在那侧跑不到判决句，见下）；`verify_card_index.py` **17／15**（**唯一**两侧读数不同的脚本——正是“下限必须分支感知”的实例）；`verify_decision_register.py` 32／32；`verify_derived_numbers.py` 19／19；`verify_gate_integrity.py` 68／68。**反向对照 8 条**落 `verify/verify_gate_integrity.py`（断言 59 → 68），含“判据**真被套件调用**”的静态钉（删接线即红）。**新发现（`run-2026-09-30-implementation-110` 已修，如实记）**：`verify_agentops.py` 在 absent 分支打 `AGENTOPS SKIP[spec-absent-on-branch]…本档不是通过` 却**退 0** ⇒ 判决行与退出码两个通道互相矛盾（**本批更正**：套件判据②**本来就**会把它判红，并非"套件照旧算 PASS"；真正的缺陷是两通道不一致）。修法＝新增 `verdict_exit()`，SKIP 档退 `3`（与判决行同口径、与 `spend-report`／`spend-budget` 的 SKIP 码一致），断言 174 → 177、下限同步 177。**另记（未变）**：本轮另有 16 个脚本打印了判决句但**未自陈**条数（未纳入棘轮，套件逐轮 WARN 点名） | 已修 |
| 35 | critical：`verify_decision_register.py` 在 main 上**套件必然超时**——登记册 1248 个指针里 1106 个指向 windows-only 的 `docs/iteration/**`（2026-09-29 现跑计数），旧实现对每个指针 spawn 两次 `git ls-tree`；模拟 main 实测约 173s，越过 CI 路径的 80s 上限 ⇒ 精确复现 `TIMEOUT`、`exit=124` | 二查 main `code-review-105` critical 1 | **已修**（`a3a3f25`）：目录前缀短路缓存（**存在方向不缓存**，判据强度未改）；镜像 main 实测 173.1s → 2.8–2.9s | 已修 |
| 36 | critical：`verify_agentops.py` 读 windows-only 的 sprint-id 向量 spec 时抛**未捕获** `FileNotFoundError` ⇒ 脚本直接崩（rc=1）；同族第二处＝`verify_close_readiness.py` 的 E1 向量表判 `FAIL: 0 行` ⇒ **两条独立的 CI 变红路径** | 二查 main `code-review-105` critical 2 | **已修**（`a3a3f25`）：两处改具名 `SKIP[spec-absent-on-branch]`（**不是通过**）；spec 在位时照旧真判 | 已修 |
| 37 | major：`agents/spend-budget.json` 写死**某一台开发机的 DSH 会话 id**，换机器／克隆即不匹配 ⇒ 规则 17 的"主代理 output／日"读数**静默变 0**而 `--check` 照常判 `OK`（假绿）；该文件在 `origin/main` 上不存在 ⇒ 本批把它**新增进 main** | 二查 main `code-review-105` major 3 | **已修**（`a3a3f25`）：id 不存在时改 `[SKIP]` ＋ rc=3 ＋"**不是通过**"上屏，且 SKIP 优先于 OVER | 已修 |
| 38 | major：`VERIFY_META.est_seconds` 是**分支无关常量**，而实测耗时随分支差 110 倍 ⇒ 同一份判据在一个分支绿、另一个分支红（同机同 venv 同树，差别只在 `docs/iteration/**` 是否存在 ⇒ 不是"机器慢"） | 二查 main `code-review-105` major 4 | **已修**（`a3a3f25`）：`run_suite.py` 增 `BRANCH_EST_OVERRIDES`（两侧都是实测值）；**未上调任何 timeout 常量**（那是放宽判据） | 已修 |
| 39 | minor：分支感知口径**语义正确但漏了成本面**——当前 1106 个指针指向 windows-only 子树（2026-09-29 现跑），每新增一个同形态指针都会线性放大 | 二查 main `code-review-105` minor 5 | **已修**（`P2` 裁定：棘轮口径＝**条数**）：`verify/verify_decision_register.py` 新增 `absent_ratchet_problems()`（**纯函数**）＋`BRANCH_ABSENT_CAPS`，把**未核指针数**（`pointers_branch_absent`）纳入**只减不增**的棘轮：超本分支上限即 FAIL，分支键＝`path_in_head(ROOT, "docs/iteration")`（**与 `run_suite.PROBE_KEY` 同一判据**）。实测上限：present（windows）**0**／absent（镜像）**1106**——两侧都是现跑复算（登记册 1248 处指针，absent 侧 1106 处未核、present 侧 0 处；复算口径写在该表上方注释里；`main` ref 上登记册本身缺席 ⇒ 该分支走具名 SKIP，absent 侧是**镜像**读数，如实标注）。**反向对照 7 条**（`c1″` 端到端**分支感知** ＋ `u`–`z`：上限内放行／超一条即红／下调放行／缺分支项 fail-closed；断言 25 → 32）。PASS 行现同时打印**读数与上限**（“其中本分支不存在 N 处未核，行 39 棘轮上限 M 条”） | 已修 |
| 40 | minor：`agents/spend-budget.json` 把**预算值**与**基线读数**放在同一文件，而该文件注释自述“只放预算不放读数”；`targets.verified_by` 声称“次日读数与 baseline 对比”，而 `--check` 实际只做 `got <= cap`、**不比对 baseline** ⇒ 声明了机制而机制不存在 | 二查 main `code-review-105` minor 6 | **已修**（`P3` 裁定＝实现，**不改 `verified_by` 措辞**）：`scripts/spend-report.py::check()` 把比对**真做出来**——新增 `baseline_note()`，逐项上屏“高于／低于／等于基线 ＋ 倍率”，且对照**不参与退出码**（该文件自述 baseline“用于对照，不作为判据”）；`baseline` 缺该指标字段 ⇒ 该行判 **SKIP 且 rc=3**（口径同 `TG-19` M-B：判据没被执行就不算通过）。**真入口反证**（驱动真 `check()`，只把“配置根”换到 %TEMP% 夹具）：修前“低于基线／高于基线”**零命中**、缺字段照判 `[OK ]` 退 0 → 修后低于／高于都上屏、缺字段 rc=3、整段缺 rc=3；不回归：超预算仍 rc=1、主会话匹配不上仍 rc=3（该条修前修后同判）。附带修掉 `_comment` 的自述失真（“只放预算不放读数”与文件里确有 baseline 读数矛盾）——**未动** `targets.verified_by` 的措辞（裁定要求） | 已修 |
| 41 | minor：`zstandard` 是 `scripts/spend-report.py` 的**运行依赖**，而 `requirements.txt` 与 `requirements-windows.txt` **均无它** ⇒ 换机器上该仪器以 `exit 2` 退出，且报错文案写“仓库 .venv 已装”（在这份清单下不成立） | 二查 main `code-review-105` minor 7 | **已修**（`P4` 裁定）：两份仓根依赖清单各补 `zstandard`（`requirements-windows.txt` 按本仓 `.venv` 实装 pin `zstandard==0.25.0`，2026-09-30 现跑核对一致；`requirements.txt` 沿用该文件既有的无 pin 体例）；`scripts/spend-report.py` 的 `ImportError` 文案不再声称“仓库 .venv 已装”，改为可执行的安装路径。**反证**（屏蔽 `zstandard` 后跑真入口）：修前输出含“仓库 .venv 已装” → 修后不含且给出 `pip install` 路径，两侧控制流不变（都退 2） | 已修 |
| 42 | minor：本地 `main` 落后 `origin/main` 三个提交；本次评审判据一律取 `origin/main` 故不受影响，但任何以本地 main 为基准的 diff 会得出**过期结论** | 二查 main `code-review-105` minor 8 | **已修**（`P5`；**举证方＝父代理（派单方）**：2026-09-29 由父代理亲自 `git fetch` ＋ 快进本地 `main`；本批**未碰分支**、只登记状态）：现跑复核 `git rev-parse main` ＝ `bc3121992a723f57abc5a3cd4b53090b97cbcafb` ＝ `origin/main`（commit `sync(sprint-17): windows → main`），`git rev-list --count main..origin/main` ＝ **0**（双向 0） | 已修 |
| 43 | nit：`paper-qa-script/app/usage.py` 与 `scripts/agent-ops.py` **有意镜像两份**选档口径（SSOT 上已具名的技术债；有 `verify_usage.py` 一致性测试兜底） | 二查 main `code-review-105` nit 9 | **豁免前状态＝只报**（已按 `P6` 裁定登记为具名技术债、不新增判据）。**性质＝只报**（四项缺陷本体未被修，仍如实记为只报）；**状态＝用户豁免**：本次行 43／45／46／51 经用户 **2026-09-30 单次豁免**出列（**非永久、不构成先例、后续批次不得引用**，`D-250930-01`）。**债名**：选档口径有意镜像两份。**是什么**：窗口元数据解析、选档函数（`is_peak_at`／`peak_frac`）、跨档加权三条口径在两文件各有一份；`usage.py` 不能 import `agent-ops.py`（后者是**文件名带连字符**的 CLI 脚本、模块级即拉 argparse 与账本路径常量）⇒ 镜像不是疏忽，是运行环境所迫。**为什么现在不判**：结构面判据先要定义“消费面”的**可机检形态**，而两侧键处理结构不同（`agent-ops` 是白名单常量 `_TOP_LEVEL_TIER_KEYS`，`usage.py` 是 dict 取用），定语域成本大于本批收益；且**值域已有现跑兜底**——`verify/verify_usage.py` ⑪14a–f 逐 (provider, 模型) 对照窗口来源，⑪14 的 8 个边界 ＋ 5 个跨档向量 ＋ 缺失／退化逐条同值，本批又加了“窗口随价走”不变式与合成表反证。**将来要判需先定义**：①“消费面”的机检形态（键集合？调用序列？）；②新增档位键时“两侧必须同改”的**检测点**（谁在何时跑）；③失败方向（假红代价 vs 漏判代价）。**本批不新增判据**（父代理裁定） | 用户豁免 |
| 44 | nit：`PAPERQA_VERIFY_PORT` 覆盖**只在 `__main__` 分支生效**，import 式启动（如 `uvicorn main:app`）读不到它；实现本身 fail-fast 合规 | 二查 main `code-review-105` nit 10 | **已修**（`P1` 裁定；与行 31 同一次授权）：`paper-qa-script/reactflow-paperqa-prototype/backend/main.py` 把端口读取从 `__main__` 分支提到**模块级**——新增 `resolve_port()` ＋ `PORT = resolve_port()`（**import 时**求值，非法整数／越界即 `SystemExit`），并新增 `serve()` 作为 `python main.py` 与 import 式启动的**共用入口**。**真入口反证**（`import main`，**不走 `__main__`**；2026-09-30 现跑）：修前**无模块级端口事实**（`has_PORT=false`、非法值静默忽略 rc=0）→ 修后 `PORT=9123`、`has_serve=true`；非法值 `abc` ⇒ import 即 rc=1（`不是合法整数`）、越界 `70000` ⇒ rc=1（`越界`）、**不设 env ⇒ 8787**（向后兼容）。**局限（如实记）**：`uvicorn main:app` 的端口仍由启动器决定 ⇒ 修法是把覆盖暴露成**模块级事实**（`main.PORT`／`main.serve()`），而不是让第三方启动器自动遵守 env | 已修 |
| 45 | critical：`impact-assessment.report.md` 的**模块归并表五处计数全部与 `git diff --numstat` 现跑不符**，且是**混基线复合体**——声称值相加 38 ≠ 33 个文件；`.github` 行逐字等于被弃用的超集基线 `958c739878..bf41d200` 的读数。**此即 `impact-assessment-103` 报告自身的 critical ①** | 一查 `doc-audit-104` critical 1（对象＝〇查 `impact-assessment-103` 报告 `:80-98`） | **性质＝只报**（四项缺陷本体未被修，仍如实记为只报）；**状态＝用户豁免**：本次行 43／45／46／51 经用户 **2026-09-30 单次豁免**出列（**非永久、不构成先例、后续批次不得引用**，`D-250930-01`）。**父代理 2026-09-29 裁定，理由逐字**：“缺陷在运行态产物（`agents/runs/**`，被 gitignore）里；纠偏已落在持久层 §5 行 45/46 与『下游范围一律用 `git diff --name-status` 现跑』这条”）⇒ 状态由「未修」改为「只报」。**署名：这是父代理（派单方）的裁定，不是本批（子代理）自评的豁免**；本批**未代改** `agents/runs/**` 里他人报告（该目录属 `.gitignore` 忽略域、亦不在授权写入集），只登记状态（§5.2 `P7`） | 用户豁免 |
| 46 | critical：同报告 `:198-244` 的“必含：本次变更面（33 文件）”清单含 **5 个基线内既有文件**（`agents/obligations.json`、`agents/runtime/prices.json`、`g1-vs-g2-close-comparison.MD`、`residual-risk-register.MD`、`governance-batch-plan-G2.MD`；`git cat-file -e 18f2274:<path>` 现跑 rc=0 全部命中），且 2 处 `(新增)` 错标。**此即 `impact-assessment-103` 报告自身的 critical ②** | 一查 `doc-audit-104` critical 2（对象＝同报告 `:198-244`） | **性质＝只报**（四项缺陷本体未被修，仍如实记为只报）；**状态＝用户豁免**：本次行 43／45／46／51 经用户 **2026-09-30 单次豁免**出列（**非永久、不构成先例、后续批次不得引用**，`D-250930-01`）。**父代理 2026-09-29 裁定，理由逐字**：同上——“缺陷在运行态产物（`agents/runs/**`，被 gitignore）里；纠偏已落在持久层 §5 行 45/46 与『下游范围一律用 `git diff --name-status` 现跑』这条”）⇒ 状态由「未修」改为「只报」。**署名：父代理裁定，非本批自评豁免**；下游按 `doc-audit-104` 的现跑读数纠偏，**不按该清单**（§5.2 `P7`） | 用户豁免 |
| 47 | major：`verify/README.md` **缺 readme-completeness 第 ④ 类"故障排查"整类**（四类缺一即 must-fix）；2026-09-29 现跑该文件唯一标题在 `:1`、三个关键词（故障／排查／troubleshoot）零命中 | 一查 `doc-audit-104` major 3 | **已修**（本批工作区改动）：新增 `## 故障排查`，覆盖 `PAPERQA_VERIFY_PORT` 覆盖法与"套件内偶发失败／单跑必过"两类真故障 | 已修 |
| 48 | major：`docs/1-WORKFLOW.MD:403` 的**日期口径 R2 规则无机检**（`verify/` 与 `scripts/` 全仓零实现；同名命中判的是**账本 run 的日期**，与文档日期无关）⇒ 该规则 `unverifiable`；2026-09-29 逐文件比对，本批变更的 13 个 `.MD` 里 7 个超阈而无闸门会报 | 一查 `doc-audit-104` major 4 | **已修**（本批工作区改动，父代理裁定选②＝**就地降级声明**）：规则**同一条内**（`docs/1-WORKFLOW.MD:403`，就地追加、**不新增行** ⇒ 登记册 `path:line` 指针零漂移）已明写"本条口径当前无任何机检实现，属**未验证口径**，已登记为 G3 未闭环项（复盘 §6）"并记代价；**未实现新闸门**（父代理裁定）；§6 第 6 条指针已同步。规则原文一个字未改 | 已修 |
| 49 | minor：`2026-09-27-g2-walkthrough-checklist.MD` 有 10 处 Markdown 链接写成本机绝对路径（本机 10/10 可解析 ⇒ "在本机能用、出本机即死"：其它克隆根、GitHub 渲染、WSL 全断） | 一查 `doc-audit-104` minor 5 | **已修**（本批）：10 处改仓内相对路径，逐个 `Test-Path` 现跑解析通过 | 已修 |
| 50 | minor：`docs/1-WORKFLOW.MD` §6 **缺编号 `15.`**（13→16 跳号），全仓无任何说明 | 一查 `doc-audit-104` minor 6 | **已修**（本批）：在 `16.` 前插入具名"编号空缺"行；`git log -S'15. **'` 现跑 0 命中 ⇒ **从未有过第 15 条、非删除** ⇒ `:420` 的 `Structure-Removal:` 具名署名**不适用**；**不重编号**（理由见该行） | 已修 |
| 51 | nit：`docs/6-DECISIONS.md::D-250926-06` 与 `-07` 条目 ID 内嵌日期为 `0926`，而正文生效时点为 `2026-09-27`（仅 ID 与生效日不同日） | 一查 `doc-audit-104` nit 7 | **性质＝只报**（四项缺陷本体未被修，仍如实记为只报）；**状态＝用户豁免**：本次行 43／45／46／51 经用户 **2026-09-30 单次豁免**出列（**非永久、不构成先例、后续批次不得引用**，`D-250930-01`）（原因：报告自判"按现体例可接受，记 nit 供后续命名参考"）⇒ **已给出待裁定建议 `P8`**（§5.2：两条的 `时点` 字段已各自写明 `2026-09-27（UTC+8）`，即生效日**有执行点**；改 ID 的代价＝全仓按条目号引用的改写。建议维持现状并只登记体例） | 用户豁免 |

### 5.0 逐行状态清单（行号｜状态｜落地提交/run｜依据；2026-09-30 本轮现跑）

> **本小节是 §5 表 `状态码` 列的逐行展开与举证**（51 行全覆盖，行号与 §5 表一一对应）。
> **唯一真源仍是 §5 表的 `状态码` 列**；本小节与之由 `verify/verify_close_tax_reading.py::status_count_problems`
> **逐行对钉**（两处任一处改了而另一处没改 ⇒ 闸门 FAIL）。
> **`落地提交` 列的判据**：该 sha 的**文件清单**必须真的含该行提到的改动对象（`git show --name-only <sha>` 现读），
> 提交信息只作线索——本批即据此更正了行 15 的签发。
> **已知局限（如实记）**：`落地提交/run` 是「该 sha 的文件清单含该行改动对象」这一级证据，
> **不等于**「该行缺陷已被端到端复现证明闭环」——后者仍以各行 `状态说明` 里的反证／举证为准
> （行 24／25／42 的举证方是父代理，本批未复跑；行 33 的端到端复现仍未构造，见归档档#未做项与局限）。







| 行 | 状态 | 落地提交/run | 依据（可复跑） |
|---|---|---|---|
| 1 | 已修 | `1d394d8` | `scripts/structure-guard.py` 真入口两例 ＋ 自检扩条；该提交触及守卫与两个钩子（`git show --name-only 1d394d8`） |
| 2 | 已修 | `1344102` | `087-minor-5` 五项全部落地：`verify/verify_decision_register.py` 判据 8–12（围栏剥离／章节行区间／重复契约字段／"会话"形态／表格非字段载体）；取证档 §C.1 逐字"五项全部落地" |
| 3 | 已修 | `1344102` ＋ `28bc182` | `087-minor-9` 四类形态落地（`verify/verify_derived_numbers.py` 的 `guard_required`／棘轮比值／自陈条数／变更集四类）；`ci.yml` 部分由 `28bc182` 闭环；残留自述（`sprint-18` §9"标签写死 12 条"）现读已清 |
| 4 | 已修 | `61494c9` | `_invokes_guard` 改**命令位置 ＋ 词元级结构判定**（`bool(_guard_command_lines(text))`），docstring 自陈"G2 行 4"残留 |
| 5 | 已修 | `61494c9` | `_installs_hooks` 改 `_hooks_from_ast`（`ast` 解析 `HOOKS` 结构），docstring 自陈"行 5（复核 `092` minor）" |
| 6 | 已修 | `61494c9` | `_enforces_exit_code` ＋ `unskippable_wiring_problems`："三处合起来至少一次由退出码终判"＋"终判层不得让出" |
| 7 | 已修 | `8b03c77` | 写入侧唯一实现；读取侧独立镜像 ＋ 一致性向量守同义 |
| 8 | 已修 | `31ceb6e` | 5 个脚本的固定名夹具改 `mkdtemp` run 级唯一目录（含回收） |
| 9 | 已修 | `28bc182` | `derived_numbers` 的截断改为自曝"另有 N 项未列出" |
| 10 | 已修 | `28bc182` | `ci.yml` 标签不再写死条数 |
| 11 | 已修 | `b271606` ＋ `43a65e2` | `VERIFY_META` 写死计数改指末行（3 文件 4 处，`b271606` diff 现读核）；UC 区间与 `1-WORKFLOW` 同类由 `43a65e2` 收口 |
| 12 | 已修 | `1f31475` 等四批 | `docs/6-DECISIONS.md` 全量回填完成；剩余条数以闸门现跑为准 |
| 13 | 已修 | `df5fd73` | `verify/verify_close_readiness.py` 的 `SKIP[窗口/未起跑]`，逐字"（行 13：未起跑 ≠ 数据被改过）" |
| 14 | 用户豁免 | `D-250926-05` | 用户 2026-09-26 单次豁免原话；**是豁免，不是已修**（规则原文不改，再次触发仍按 S1） |
| 15 | 已修 | `1ed6f93` | `parse_deepseek` 重写（该提交触及 `scripts/fetch-prices.py`）；**本批更正签发**：原记 `1344102` 的文件清单不含该脚本 |
| 16 | 已修 | `1ed6f93` ＋ `d1204b8` | `agent-ops` 与 `app/usage` 两条链路按时刻选档；白名单纳入 `_tiers`＋"派生后档位仍在" |
| 17 | 已修 | `df5fd73` | 产物复制推迟到守卫之后（`_copy_result_file`）；拒前/拒后 `runs/<id>/` 两侧均空 |
| 18 | 已修 | `df5fd73` | 放行时写 `degenerate_reason`（原话）＋闸门两条判据 |
| 19 | 已修 | `df5fd73` | 新增 `retract`（理由留痕／只认显式点名 id／被引用者 fail-closed） |
| 20 | 已修 | `d1204b8` | `paper-qa-script/app/usage.py` 按调用起止时刻选档、跨档墙钟加权 |
| 21 | 已修 | `ac92269` | `scripts/hooks/pre-commit` 尾行 `exit $rc`（保留 `--report-only`） |
| 22 | 已修 | `ac92269` | `_check_ok` 改结构判定；命令位置改**默认判红** |
| 23 | 已修 | `b271606` | 改 `VERIFY_META` 后同批 `derive` 并给出 `check` 末行 |
| 24 | 已修 | `14603c2` ＋ `86625c7` | 生产侧端口读 env ＋ 夹具侧 run 级端口（**举证方＝父代理**） |
| 25 | 已修 | `86625c7` | `mkdtemp` 回收（**举证方＝父代理**） |
| 26 | 已修 | `a3a3f25` | `_terminal_statuses()`：终态＋坏时间戳判具名数据缺陷 |
| 27 | 已修 | `a3a3f25` | `is_file()` ＋ 留痕记 `evidence_sha256` |
| 28 | 已修 | `a3a3f25` | 引用面改数据驱动（`result_files` 一并查） |
| 29 | 已修 | `a3a3f25` | 升级为退出码结构判定（吞码两形态判 False） |
| 30 | 已修 | `24cb109` | `PY_WORD_RE` 收词边界（裸词只认 `python*`／`py`） |
| 31 | 已修 | `fa1250a` | 两侧同改为按 provider 取窗口（`provider_of_model`／`provider_of`） |
| 32 | 已修 | `24cb109` | `--apply` 与 `--check` 共用 strict 判据并把 rc 带回 |
| 33 | 已修 | `24cb109` | `empty_ops` 夹具增 `atexit` 兜底 |
| 34 | 已修 | `fa1250a` ＋ 本批 | `run_suite.py` 判决句 ＋ 条数棘轮四道判据；**本批**补 SKIP 退出码判据（`verify_agentops.py::verdict_exit`，下限 177） |
| 35 | 已修 | `a3a3f25` | 目录前缀短路缓存（存在方向不缓存；判据强度未改） |
| 36 | 已修 | `a3a3f25` | 两处改具名 `SKIP[spec-absent-on-branch]`（**不是通过**） |
| 37 | 已修 | `a3a3f25` | `agents/spend-budget.json` id 不存在时 `[SKIP]` ＋ rc=3 |
| 38 | 已修 | `a3a3f25` | `run_suite.py` 增 `BRANCH_EST_OVERRIDES`；**未上调任何 timeout** |
| 39 | 已修 | `fa1250a` | `absent_ratchet_problems()` ＋ `BRANCH_ABSENT_CAPS`（只减不增） |
| 40 | 已修 | `fa1250a` | `scripts/spend-report.py::check()` 真比对 `baseline`（`baseline_note()`） |
| 41 | 已修 | `fa1250a` | 两份仓根依赖清单各补 `zstandard` |
| 42 | 已修 | `main=bc31219`（**父代理执行**） | 父代理 2026-09-29 亲自 `fetch` ＋ 快进；现跑 `git rev-parse main` ＝ `bc3121992a723f57abc5a3cd4b53090b97cbcafb`，`main..origin/main` 计数 0 |
| 43 | 用户豁免 | `D-250930-01`（用户 2026-09-30 裁定） | 具名技术债：选档口径有意镜像两份；**不新增判据**（值域由 `verify_usage.py` ⑪14a–f 兜底）。**性质＝只报**；本次经用户 **2026-09-30 单次豁免**出列（非永久、不构成先例） |
| 44 | 已修 | `fa1250a` | `resolve_port()` ＋ `PORT` 提到模块级 ＋ `serve()`（import 式启动也生效） |
| 45 | 用户豁免 | `D-250930-01`（用户 2026-09-30 裁定） | 缺陷在运行态产物 `agents/runs/**`（`.gitignore` 忽略域、不在授权写入集）。**性质＝只报**；本次经用户 **2026-09-30 单次豁免**出列（非永久、不构成先例） |
| 46 | 用户豁免 | `D-250930-01`（用户 2026-09-30 裁定） | 同上；下游按 `doc-audit-104` 现跑读数纠偏，不按该清单。**性质＝只报**；本次经用户 **2026-09-30 单次豁免**出列（非永久、不构成先例） |
| 47 | 已修 | `a8da964` | `verify/README.md` 新增 `## 故障排查`（四类缺一的那一类） |
| 48 | 已修 | `24cb109` | `docs/1-WORKFLOW.MD` 的 R2 就地降级声明（**不新增行** ⇒ 登记册指针零漂移） |
| 49 | 已修 | `a8da964` | `2026-09-27-g2-walkthrough-checklist.MD` 10 处改仓内相对路径 |
| 50 | 已修 | `a8da964` | `docs/1-WORKFLOW.MD` §6 插入具名"编号空缺"行（不重编号） |
| 51 | 用户豁免 | `D-250930-01`（用户 2026-09-30 裁定） | 条目 ID 内嵌 `0926` 而生效时点为 `2026-09-27`；建议维持现状、只登记体例。**性质＝只报**；本次经用户 **2026-09-30 单次豁免**出列（非永久、不构成先例） |

## 6. 归档与收敛记录（2026-10-03 现跑）

- **归档档**：`docs/iteration/archive/2026-09-26-g2-close-retro-archived-narrative.MD`（口径见 `docs/iteration/archive/README.MD`）。
- **已逐字移出**：§2 A 表、§3 对话纪要、§5 表的口径与机制说明、§5.1～§5.4、§6、§7、§8。
- **未改**：§5 表行集合与 `状态码` 逐行语义、机读 `状态计数:` 行、§5.0 表；**未新增／删除任何 §5 表行，未改任何 `状态码` 值，未上调任何 cap，未碰 `verify/**`**。
- **本档行网格是刻意的**：其他档用 `path:line` 指进本档，`verify_decision_register.py` 只在指针 **±2 行**内核对逐字引文；故 §5 表头、§5.0 表头与各处被引用的句子**钉在原行号上**——这是「指针漂移净新增 0」的构造性保证，代价是本档含少量空行（**不是排版失误**）。
