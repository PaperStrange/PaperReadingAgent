# G2 走查清单（用户走查验收用）

> 生成 2026-09-27（UTC+8）。**用法**：按 §3 的顺序跑命令，用 §4 的读数对表；§5 是我**主动列出的未达标/未验证项**，
> 走查时请优先看那一节。**本清单不构成关闭主张**——关闭标准见 `D-250926-06`（零未闭环项）。

## 0. 一页事实

| 项 | 值 |
|---|---|
| 分支 / 仓库 | `windows` / `PaperReading-Windows`（remote `PaperStrange/PaperReadingAgent`） |
| 关闭标准 | **零未闭环项**（G2、G3 均按此；`docs/6-DECISIONS.md::D-250926-06`，2026-09-27 你再次确认） |
| 发现项总账 | 复盘 §5，共 **25 行**（行号即权威；本清单不复制描述） |
| 计划内交付 | D1–D6（12 点）＋ 插入 `TG-20`（2 点）＝ 14/14 |
| `windows→main` PR | **未创建**（按你的规矩：走查验收通过前不建） |

## 1. 要打开的文件（按重要性）

| # | 文件 | 为什么看它 |
|---|---|---|
| 1 | [G2 复盘](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\testing-governance\2026-09-26-g2-close-retro.MD) | **§5 未闭环项总账**（25 行，每行有来源与状态）；§4 是与你对话的逐字纪要 |
| 2 | [闭环台账](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\testing-governance\2026-09-26-g2-closure-ledger.MD) | A 表＝每行的**关闭动作**；B 表＝**耦合边**（谁和谁必须同批改） |
| 3 | [残余风险备案](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\agents-infra\2026-09-26-residual-risk-register.MD) | `R-001`~`R-003`：方案覆盖不到的边界 |
| 4 | [派单反例档](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\agents-infra\2026-09-25-subagent-dispatch-failure-modes-case.MD) | 案例 1–11（含**我自己的**事故：混提交、文字承诺、派单未登记 run） |
| 5 | [机制反例档](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\agents-infra\2026-09-25-gate-mechanism-failure-modes-case.MD) | 案例 1–26（含**假绿**、影响面漏普查、口径造出的假结论） |
| 6 | [G1↔G2 对照](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\agents-infra\2026-09-26-g1-vs-g2-close-comparison.MD) | 收口时长的**活跃口径**对照（旧 6.4× 已作废，改判约 1.5×，区间 1.1×~5.0×） |
| 7 | [价表 spec](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\agents-infra\2026-09-26-price-tier-spec.MD) | 两档计价、时段窗口、未决点、`fx` 裁定 |
| 8 | [087 处置取证](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\testing-governance\2026-09-26-087-minor-5-9-disposition-spec.MD) | 行 2/3 的原始 finding 逐字出处 |

## 2. 验收面（你手上要有哪些可核读数）

| 证据 | 位置 |
|---|---|
| 本地全量闸门 | `.venv\Scripts\python.exe verify\run_suite.py --tier offline` → 末行 `SUITE PASSED (26 scripts)` （2026-09-27 时点读数，以现跑末行为准） |
| CI（**只对 HEAD 有效**） | GitHub Actions 上 **HEAD 那一笔**的 conclusion；更早的提交多为 `cancelled`（并发取消），**不代表通过** |
| 关闭税机读读数 | `verify\verify_close_tax_reading.py --sprint docs\iteration\sprint\2026-09-25-sprint-18.md` |
| 账本 | `agents/runtime/registry.json`（**不在版本库**，`.gitignore:38`）＝ 本机运行态 |
| 决策登记册 | `verify\verify_decision_register.py` 现跑末行 |

## 3. 走查步骤（按顺序，约 4 步）

**第 1 步｜跑一遍闸门（约 3–5 分钟）**
```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
.venv\Scripts\python.exe verify\run_suite.py --tier offline
```
看末行是不是 `SUITE PASSED (26 scripts)`。**任何 FAILED 都请记下脚本名**，它对应 §5 的某一行。 （2026-09-27 时点读数，以现跑末行为准）

**第 2 步｜看"钱"那一条（你最该看的）**
夜间成本过去被按高峰价高估约 2 倍。现在两条计价链路都按调用/run 自己的时刻选档：
```powershell
# 账本里某条 run 的档位（tier=off_peak 表示按空闲价计）
.venv\Scripts\python.exe -c "import json,pathlib;d=json.loads(pathlib.Path('agents/runtime/registry.json').read_text(encoding='utf-8'));[print(r['run_id'], (r.get('cost_est') or {}).get('tier'), (r.get('cost_est') or {}).get('tier_assumed')) for r in d['runs'][-6:]]"
```
**判据**：夜间跑的 run 应出现 `off_peak`；**没有时间戳**的 run 应是 `peak` ＋ `tier_assumed=True`（不得静默挑便宜的档）。

**第 3 步｜看关闭账有没有糊（5 分钟）**
- 打开[复盘 §5](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\testing-governance\2026-09-26-g2-close-retro.MD)：**每行的"状态"栏**应只有三种：`已修`（带提交 sha）、`已达成`、`已由用户裁定处置`（含你给的单次豁免）。
- **若有"未修/未闭环"**，那就是还没到零未闭环项。
- 打开[闭环台账 B 表](D:\All-Downloads\PaperReading\PaperReading-Windows\docs\iteration\phases\testing-governance\2026-09-26-g2-closure-ledger.MD)：看有没有"两条发现必须同批、却分批做了"的情况。

**第 4 步｜看我不打算让你发现的东西**
直接跳到 §5。

## 4. 期望读数（以现跑为准，不写死）

| 读数 | 期望 |
|---|---|
| 套件末行 | `SUITE PASSED (26 scripts)` （2026-09-27 时点读数，以现跑末行为准） |
| 关闭税 | 机读行给出 `code_major / code_critical / doc_items` ＋ 来源 run（**M1 上限 ≤2/≤3 未达标，见 §5**） |
| 登记册 | `ALL PASS`，含 `entries=` / `quotes_checked=` / `quotes_drift=` 三项读数 |
| 账本闸门 | `verify_ledger_measurement.py` → 本机 PASS（**前提：账本存在**；CI 上账本不存在，见 §5 第 3 条） |

## 5. 我主动列出的未达标 / 未验证项（**走查请优先看这节**）

1. **M1 从未达标**：DoD §6 第②条要求 `code major ≤2` 且文档项 `≤3`；G2 实际 **5／12**（G1 是 7／11）。按 `D-250926-06` 关闭以**零未闭环项**为准，M1 作**时点读数如实记录**，但"G2 超标"这件事是真的，不是口径问题。
2. **R1（文件丢失/内容被吞）关闭期复现 3–6 次**（同型在 G1 记 7 次、家族累计约 11 次）。这是本仓最老的问题，**G2 没有解决它**，只加了守卫。
3. **CI 曾红而本地绿**：`1e8bae0`／`3e4b649`／`43a65e2` 三笔 CI `failure`，根因是 **`agents/runtime/registry.json` 不在版本库**，而部分判据读真实账本 ⇒ 全新克隆上失败。**当前状态：修复在跑**（要求先在真 `git clone` 里复现、修成"账本不存在 ⇒ 显式 SKIP 且不冒充 PASS"）。**走查时请确认这一条已落地，否则"CI 绿"不能算数。**
4. **`agents/runtime/**` 不在版本库**：账本、价格抓取产物、隔离区都是本机态。⇒ **CI 无法复核与账本相关的任何结论**；这是结构性的，不是本次引入。
5. **行 24／25 未修（正在修）**：固定端口 8787 导致套件内偶发失败；两个脚本每次运行泄漏一个 `%TEMP%` 目录（其中 `verify_usage.py` 那条**是我自己引入的**）。
6. **行 14 是"你单次豁免"，不是"已修"**：S1 档要求的硬停与二次确认在 G2 关闭期确实没执行（`D-250926-05` 里"违背事故"栏如实记为"有"）。
7. **我今天问重复了一个问题**：DoD(M1) 与零未闭环谁优先——`D-250926-06` 里已经写过，我却又问了一遍。走查时若发现类似"已定的事再问一次"，请直接打断我。
8. **走查清单本身没被任何闸门检查**：它是给人看的，如果它与 §5/台账不一致，**以那两处为准**。

## 6. 走查之后的岔路

- 若你在 §5 里认可"零未闭环项"已达成（即 §5 第 3、5 条落地后）⇒ 我可以**按你的指示**准备 `windows→main` 的 PR（**不会自行创建**）。
- 若你认为还有该挡关闭的项 ⇒ 请直接点名行号，我按台账 A 表给关闭动作，不再自定口径。
