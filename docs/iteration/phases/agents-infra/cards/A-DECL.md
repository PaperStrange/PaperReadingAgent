# A-DECL 规则可机检性：规则可以是无实现的声明

- `card`: A-DECL
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
3

## 来源
2026-09-29 doc-audit-104 判 1-WORKFLOW.MD:403 日期口径全仓零实现（unverifiable）

## Sprint
—

## 正文
§6 的规则是散文；**没有任何判据要求「每条规则必须有机检，或显式声明自己无机检」**。于是存在「看起来已验证、实际全仓零实现」的规则（实证：`:403` 的「文档日期 vs `%cI` 差 >1 天」比对，`verify/`、`scripts/` 零实现；本批 13 个变更 `.MD` 里 7 个超阈而无闸门会报）。

现状处置（2026-09-29）：该条已就地**降级声明**为未验证口径并登记 G3，**未实现**机检。

**方向**：给每条规则一个**机检状态字段**（`mechanized` / `declared-unverifiable` / `manual`），未声明者由闸门报出。

**验收**：规则清单可机读出「哪些规则无机检」，且新规则**不带该字段就判红**。

## 落地（2026-11-13）

**只补"声明面 + 闸门"，不实现任何被声明为无实现的判据**——`:403` 原样保持未验证
（理由见末节）。状态词按派单口径取 `machine`（卡文正文的方向里写作 `mechanized`，
以本节的封闭三词为准：`machine` / `declared-unverifiable` / `manual`）。

### ① 机读真源（`docs/1-WORKFLOW.MD` 文末新增 §6.1）

新增 `## 6.1 规则机检状态（机读真源）`：**19 行**，每条 §6 编号规则一行。
规则域 = §6 内最长从 1 起的连续编号序列（现读 = 行 425–461，编号 1–19），外加 §6 内
任何编号更大的条目（新规则追加在 §6 末尾也逃不掉）。**15 是行内自陈"本行不是规则"的
编号空缺** ⇒ 单列一行 `placeholder`。表头 = `| 规则号 | 状态 | 执行点／判据 | 理由或复核日期 |`。
**§6 与 §6.0 的既有行一个字未改**（追加在文末，指向本档的 `path:line` 指针零漂移）。

**三态计数（2026-11-13 现跑，口径 = `verify/verify_rule_index.py` 的输出，以该命令为准）**：

- `machine` = 5：规则 10／12／14／17／19；
- `declared-unverifiable` = 3：规则 3／11／18；
- `manual` = 10：规则 1／2／4／5／6／7／8／9／13／16；
- `placeholder` = 1：规则 15。

**这 13 条 `declared-unverifiable` ＋ `manual` 就是"哪些规则无机检"的机读答案**——此前只能
靠读散文猜。口径：`machine` = 失败时有现存闸门判红（判据列逐行写明它只覆盖哪一半）；
`declared-unverifiable` = §6/§6.0 已明文"无实现/仅文字"；`manual` = 人工判据、非机器——
**半自动一律不冒称 `machine`**。

### ② 闸门 `verify/verify_rule_index.py`（零依赖、只读）

**六条判据**（FAIL 一律点名规则号与 `文件:行`）：

1. **覆盖**：§6 规则域里每个编号在 6.1 表里**恰一行**（§6 有、表里无 ⇒ FAIL——这就是
   "新规则不声明状态就红"；同一编号重复行同样 FAIL）；
2. **词表**：状态 ∈ 封闭三词；`placeholder` 只允许出现在缺号上；
3. **脚本存在**：`machine` 行必须给出可核的仓库相对脚本路径，且文件**真实存在**
   （不存在 ⇒ FAIL 点名该路径）；
4. **理由与日期**：`declared-unverifiable` / `manual` 行必须有非空理由 ＋ `YYYY-MM-DD`；
5. **死行与占位错位**：表里有、§6 没有的规则号 ⇒ FAIL；实规则标 `placeholder`、
   或缺号不标 `placeholder` ⇒ FAIL；
6. **汇总**：打印三态计数（上面那行即其输出）。

**四条回归判据** = ①覆盖 ②词表 ③脚本存在 ④理由＋日期（任何一条失守即红；⑤⑥是死行与
汇总，补的是"表能自己解释自己"）。

### ③ 反向对照读数（`--selftest`，`%TEMP%` 合成副本上真跑同一 `check()`）

- ① §6 注入假规则 20 ⇒ `[① 覆盖] 规则 20（docs/1-WORKFLOW.MD:493）在 §6.1 表里没有行`；
- ② 把 `machine` 行改到不存在的脚本 ⇒ `[③ 脚本] … verify/verify_rule_index_missing.py 不存在`；
- ③ 状态改成非法词 `auto` ⇒ `[② 词表] 规则 10 … 'auto' 不在三词表`；
- ④ 删掉 `declared-unverifiable` 行的理由/日期 ⇒ `[④ 理由] 规则 3 … 却没有理由`；
- ⑤ 干净副本 ⇒ 0 问题、三态计数非空（防假红）；
- ⑥ 表里追加 §6 没有的规则 99 ⇒ `[⑤ 死行] …`；
- ⑦ 把实规则 14 标成 `placeholder` ⇒ `[⑤ 占位] … 却被标成 placeholder`。

`--selftest` 末行 `ALL PASS (7 assertions)`（2026-11-13 现跑）；整套（真数据 6 ＋ 反向 7）
末行 `ALL PASS (13 assertions)`（2026-11-13 现跑）——复现：`.venv\Scripts\python.exe
verify\verify_rule_index.py`（读数以该命令输出为准）。**`-O` 反证**：`.venv\Scripts\python.exe
-O verify\verify_rule_index.py` ⇒ rc=1，stderr 为"本闸门不得在 -O/PYTHONOPTIMIZE 下运行
（判据会被剥离）"，**不打印 `ALL PASS`**。

### ④ `:403` 日期口径的归态（卡片的原始实证缺口）

行 403 的"文档日期 vs `%cI` 差 >1 天"比对在 `verify/`、`scripts/` **仍全仓零实现**
（2026-11-13 复核：`now-network.py` 只产出网络时间、不做比对；全仓零命中），且它是 §6 的
**非编号散文规则**（不在 1–19 的编号域）⇒ 它的状态是 **`declared-unverifiable`**，
**不是 `machine`**。本批**没有**把它机检化（派单禁止在设计外新增判据），它继续留在
G3 第 6 条；**代价照旧**：超阈不会被任何闸门报出来，只靠人"当日更正"。

### ⑤ 接线与门槛（读数见 run 报告 `implementation.report.md`）

- `verify/TEST-MATRIX.MD` 同批 `derive`（62→63 脚本；生成物，数字以
  `verify_matrix.py check` 输出为准）；
- `verify/run_suite.py`：`BRANCH_ASSERTION_FLOORS[("verify_rule_index.py", …)] = 13`
  （两侧同值：断言只依赖 `docs/1-WORKFLOW.MD`）；自陈脚本数下限 9→10；
- 门槛：`py_compile`／`verify_rule_index.py`（含 `--selftest` 与 `-O` 反证）／
  `run_suite.py --tier offline`／`verify_lint`／`verify_matrix derive`＋`check`／
  `verify_gate_integrity`／`verify_decision_register`／`verify_card_index`／
  `verify_md_tables`／`verify_derived_numbers`／`verify_close_readiness --sprint`
  全部现跑。

### 未决（如实记）

- 闸门只覆盖**编号**规则；§6 的散文规则（含 `:403`、行 474／476 两条）**不设表行、
  也无判据**——这是派单划定的边界，本批没有越界新增。
- `manual` 里有多条其实是"半自动"：机器管住的那一半写在判据列，但**没有**判据检查
  "人那一半真的做了"（如规则 1 的 prompt 文本、规则 13 的将来时）。
- §6.0 机制索引自身仍无机检（该表自陈的缺口），本批未动它。
