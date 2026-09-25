# TG-6 **验收方式改进（DoD 补"人机交互验收面" + 过程可见证据 + 规范执行可核查）**：① DoD 现偏代码执行层，

- `card`: TG-6
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**已交付（2026-09-25，Sprint-17 治理批 G1 尾批）**：A 可读性棘轮（C 级从"只报数"变"咬得住的棘轮"，caps 实测 `12/46/207/2631`）+ B 四件套证据规范入 `1-WORKFLOW.MD` §6 与 `verify/README.md`（示范脚本 `verify_lint.py`，机读证据行 `EVIDENCE:`）+ C 两张旧卡按新形态补证（`TG-14` / `TG-7`）+ D 卡片与索引收口。交付与实测见下节；未做/边界同节末尾。

## 规模
3

## 来源
**用户走查 2026-09-20（UTC+8）**：用户明确要求"做个 backlog 卡记录先"；**2026-09-21** 追加反向对照规则；与 `phases/mental-models/` 的 MM-6 联动

## Sprint
Sprint-17（治理批 G1 = 规则落地）

## 正文
`[用户插入]` **验收方式改进（DoD 补"人机交互验收面" + 过程可见证据 + 规范执行可核查）**：① DoD 现偏代码执行层，需增补"用户可感行为"验收面（交互/呈现/感知）；② 验收指南每条须给**过程可见**的操作与留证（可回放命令 + 原始输出/截图/日志路径，不接受只给结论或"读文档确认"）；③ 机器回归项与人工可感项**分栏标注**（避免把纯脚本断言当人工用例）；④ 建立"Sprint 内规范条目 ↔ 执行记录"抽查机制，治理"规范写了但未执行"的先例；⑤ **反向对照规则（用户 2026-09-21 拍板，称"倒过来试试"）**：新增的交互/GUI 检查**必须先在未修复/旧实现上跑出 FAIL**（证明该检查确实能触发目标失效模式），再在修复后转 PASS——反例：`gui_check_s5/s7` 用程序化 `.click()` 结构上无法触发 F-AC13

## 交付与实测（2026-09-25，UTC+8｜本卡自证）

### A 可读性棘轮：C 级从"只报告"变成"咬得住的棘轮"

- **政策落点**：`agents/policy.json::lint_readability_ratchet`（`agents/policy.json:157`）——`caps`（逐规则计数上限）+ `measured_at` + `review_by`，与 `lint_rules` 同级；读取器 = `verify/agent_policy.py::Policy.lint_readability_ratchet`（`lint_readability_caps()` / `lint_readability_review_by()`），键已登记进 `closure_problems()` 的 `consumed` 集（无死键）。
- **闸门落点**：`verify/verify_lint.py::ratchet_problems()`（纯函数判据）+ `main()` 实数据判定 + `ratchet_selfcheck()`。判据三条：**计数 > cap → FAIL 并点名**（规则号 + 实测 + 上限 + 超出条数）；**caps 键集 ↔ `lint_rules.report_only` 逐键相等**（少一条 = 该类无限放行；多一条 = 死数据）；**`review_by` 过期 → FAIL**。
- **实测 caps（2026-09-25 全仓 `lint_paths` 四路径）**：**D101=12 / D102=46 / D103=207 / E501=2631（合计 2896）**。⚠️ **spec 给的读数已漂**：卡里写的 `11 / 42 / 191~192 / 1774~1804` 与实测不符；本卡落地**前**同口径实测为 `12 / 46 / 210 / 2642（2910）`，落地后 D103 `210→207`、E501 `2642→2631`（本卡给 `run_ruff`/`codes_of`/`summarize` 补了 docstring、把新代码全部控制在行宽内）——**cap 只许下调**，故取落地后实测值。数字随改动漂移这件事已写进 policy 的 `_comment` 与脚本 docstring。
- **三类反向对照（实测，非推断）**：① **注入 → FAIL 点名**：临时副本内注入"缺 docstring 的公开函数 + 一行超长行"→ 同一上限下 `[棘轮/D103] 实测 1 > 上限 0`、`[棘轮/E501] 实测 1 > 上限 0`（脚本内置，真实 ruff 调用）；仓库尺度同型对照 = 临时政策把 E501 cap 降 1（2630）→ 真实仓库 rc=1 且点名 `[棘轮/E501] 实测 2631 > 上限 2630（超出 1 条）`。② **干净树 → rc=0**：`ALL PASS (11 assertions)` + `EVIDENCE: verify_lint.py assertions=11 rc=0 c_ratchet=D101=12/12 D102=46/46 D103=207/207 E501=2631/2631`。③ **过期 → FAIL**：临时政策 `review_by=2026-01-01` → rc=1 且点名 `review_by=2026-01-01 已过期（今天 2026-09-25）`。另有两条守基线自身：caps 缺一类 → FAIL；caps 多出拼错键 → FAIL。
- **样本落点**：全部写 `%TEMP%`（反向对照副本 / 变体政策），仓库内零残留（`git status --porcelain` 只含本卡改动的受控文件）。

### B 验收 case 与"证据形态"落规范

- **条文**：`docs/1-WORKFLOW.MD` §6「验收 case 与"证据形态"四件套」（单段，紧跟 §6「新脚本产物目录约定」）——新验收 case / 新闸门必须给 **① 命令原文（含解释器路径）② 关键输出行（点名失败项原文）③ 退出码（实测 rc）④ 反向对照（未修复/旧实现或注入样本上的 FAIL 记录）**；新增 `verify/*.py` 须在**成功路径**打印 `EVIDENCE: <脚本名> assertions=N rc=0`（失败/SKIP 不打印）。
- **摘要行**：`verify/README.md` 头部新增同要求的 `> **验收证据四件套（TG-6，2026-09-25 立规）**` 区块；`verify_lint.py` 表格行同步改为"棘轮"描述。
- **示范脚本（只做 1 个，按 spec 允许的最小面）**：`verify/verify_lint.py` 已实现机读证据行（上引实测输出）。**未给存量 20+ 脚本做回溯改造**——规范只约束新增脚本。

### C 两张旧卡按新形态补证（挑选理由）

| 卡 | 为何挑它（证据形态最弱） | 补了什么 |
|---|---|---|
| `TG-14` | 状态 ✅ 完成，但 §证据 **通篇是"卡内待产出"**（计划口径）——没有一条可复跑的命令/输出/rc/反向对照；本批同族卡里最弱 | 新增「交付与实测补证」节：① 命令 `.venv\Scripts\python.exe verify\verify_card_index.py`（含 `--check --strict`）② 输出 `CARD-INDEX PASS… / ALL PASS (9 assertions)` ③ rc=0 ④ 7 条内置变异样本逐条 FAIL 点名（孤儿行 / 卡号不符 / 缺必备节 / 正文复制 / ≥61 字符填充规避 / 孤儿文件 + 防假红对照） |
| `TG-7` | **Bug 卡**且只有手抄断言数（"24 断言"，现已 46，数字已漂）；无命令、无输出行、无反向对照 | 新增同节：① 命令 `verify_runner.py` ② ⑩a/⑩b/⑩c 三条关键输出行 + `ALL PASS (46 assertions)` ③ rc=0 ④ 两类反向对照：**真实未修复实现上的 FAIL（2026-09-20 BOM 事故，约 ¥1.0）** + 可复跑变异样本（截断→退 2 留 `.corrupt`、顶层非对象→退 2、带 BOM 合法文件→读到并退 4 REFUSED 防假红） |

两张卡的补证都**诚实标注边界**：内置 fixture 变异 ≠ "回到旧实现复跑"（旧形态已不可回滚），真实事故记录不可复跑。

### 终态证据与套件

- `verify/run_suite.py --tier offline` → `status=ok`、零失败（脚本数见 `verify/TEST-MATRIX.MD`，不在此手抄）；闸门全绿：`verify_lint.py`（11 断言，本卡改的棘轮）/ `verify_md_tables.py` / `verify_card_index.py`（默认 + `--strict`）/ `verify_close_readiness.py` / `verify_no_policy_hardcode.py` / `verify_ledger_measurement.py` / `verify_artifact_paths.py` / `verify_agentops.py`；`verify_matrix.py check` 一致（52 脚本）；`scripts/structure-guard.py --replay` ALL PASS。
- `verify_matrix.py derive` 已随 `verify_lint.py` 的 `VERIFY_META` 变更重生成（矩阵是派生事实，唯一真源仍是脚本头）。

### 未做 / 边界（诚实标注）

- **DoD 与人机交互验收面（正文 ①③④）本卡未做**：本卡按 spec 只交付"验收方式"里可机检的部分（棘轮 + 证据形态 + 补证 + 收口）；① 用户可感行为验收面、③ 机器项/人工项分栏、④ 规范↔执行抽查机制仍待排期（④ 的半成品已在 §6 有雏形：卡片/闸门证据形态要求）。
- **C 级棘轮只覆盖 `lint_paths` 四棵树**（政策数据），未扩到 `paper-qa/`(vendored) 与前端 `.mjs`/`.jsx`；前端可读性不在本卡范围。
- **cap 的"漂移"只能靠 review_by 到期重评**（2026-10-31）：日常改动使计数下降不会自动收紧 cap（棘轮只保证"不放松"），这是刻意的取舍。
