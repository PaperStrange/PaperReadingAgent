# SOP-extract：3-LEARNED → 候选思维模型卡（MM-4）

> 归属：`docs/iteration/phases/mental-models/`；交付卡 [`MM-4`](cards/MM-4.md)。
> 机读真源：[`library/schema.json`](library/schema.json)；人读字段说明：[`library/schema.MD`](library/schema.MD)。
> 本文件只写**动作序列与判据**，**不抄字段表**：字段清单、必填性、取值域一律以 `schema.json::fields` 为准
> （schema 改，本文件不改字段表）。
> 形态：**人可执行**（照 §2 的顺序做）＋**可机检**（§5 一条命令判这张候选卡合不合格）。

## 0. 一句话

`docs/3-LEARNED.MD` 每新增（或实质修改）一条 `### 1.x` 条目，就在**同一批**里把其中**可复用的那一条经验**
提炼成**一张候选模型卡 JSON**，来源写死条目号，机检通过；**候选不进正式库**，入库与否由人审 + 首跑（MM-3）决定。

| 产物 | 落点 | 谁写 | 机检形态 |
|---|---|---|---|
| **候选模型卡**（schema 口径的 JSON） | `library/candidates/<id>.<version>.json` | 本 SOP | `mental-model-check.py --model <卡>`（§5） |
| 提取执行档（Markdown，`CM-N` 序列） | `models/<日期>-from-learned-<条目>.MD` | 早期轮次（MM-1 交付前） | **无**：字段口径早于 schema，不过校验器 |
| 正式模型 | `library/<id>.<version>.json` | 人审通过后才写 | `mental-model-check.py` 默认全库 |
| agent spec | `agents/functions/<name>.md` | MM-2 / MM-3 | `validate-spec` + 首跑 |

**`models/` 与 `candidates/` 不是同一物的两个位置**：前者是"提取这件事做过"的**执行档**（含方法自述、
批次范围、当时的口径说明，字段是用户原话口径），后者是**可过 schema 校验的候选卡**。两者并存、互不替代；
`models/` 的历史档**不搬、不改**（§6）。

## 1. 触发点：什么时候必须执行

**三个触发场景**（任一命中即执行）：

| 场景 | 形态 | 判定方式 |
|---|---|---|
| A 新增条目 | `3-LEARNED.MD` §1 出现新的 `### 1.x` | §1.1 检查 ① 有新增行 |
| B 实质修改 | 既有条目的 `phenomenon` / `fix` / `lesson` 段**结论**被改（错别字、排版、纯链接不算） | 人工读 diff（① 无输出时才需要，见判读） |
| C 补课 | 发现历史条目从未被提取（前两轮的漏项就是这么暴露的） | §1.1 检查 ② 对历史条目号无命中 |

**时点（硬约束）**：`3-LEARNED.MD` 头部义务块第 1 条要求——**完成提取前不得提交该文件的条目变更**，
或按 `1-WORKFLOW.MD` §6 显式豁免并把豁免写进提交信息。提取与条目变更在同一批里完成，不留"下次再提"。

### 1.1 可操作检查（复制即用，仓库根，PowerShell）

```powershell
# ① 本批新增了哪些 §1 条目（无输出 = 没有新增条目，仍须看 ③ 判断是否属场景 B）
git diff --unified=0 -- docs/3-LEARNED.MD | Select-String -Pattern '^\+### 1\.'

# ② 这些条目号是否已有候选卡（把 1.73 换成 ① 的结果；无命中 = 还没提取）
Get-ChildItem docs/iteration/phases/mental-models/library/candidates -Filter *.json -ErrorAction SilentlyContinue |
  Select-String -Pattern '3-LEARNED 1\.73'

# ③ 反向检查：3-LEARNED 动过、candidates/ 却没有新增 ⇒ 触发未履行
git status --short -- docs/3-LEARNED.MD docs/iteration/phases/mental-models/library/candidates
```

**判读**：

- ① 有 `+### 1.` 且 ② 对这些条目号无命中 ⇒ **必须提取**，逐条过 §3；
- ① 无输出而 ③ 显示 `3-LEARNED.MD` 已改 ⇒ 按场景 B 人工判断（改动是否动了结论）；
- ① 有新增而 ② 已命中 ⇒ 已提取过；若条目又被实质修改，追加 `examples` 或升版本（§4.2），**不新开同 id 卡**。

### 1.2 执行记录（可核性）

每次执行都留一行可核记录（写在 [`cards/MM-4.md`](cards/MM-4.md) 的 `## 落地`，或该次 run 的报告里）：

```text
条目号 → 候选卡 id/version → 机检末行（OK / FAIL: <N> 项） → 不提取的条目号与命中的 N 编号
```

**"不提取"也要记**：否则下一轮无法区分"判过了"与"漏了"。

## 2. 提取步骤（一条经验 → 一张候选卡，固定顺序）

| 步 | 动作 | 判据 / 产出 |
|---|---|---|
| 1 | 读**整条**条目：`- **phenomenon**`（现象）、`- **fix**`（整改）、`- **lesson**`（教训）；早期条目写作 `- 现象：` / `- 解决：` / `- 教训：`，其后可能还有 `再版注记` / `边界` / `跨引用` 等追加行 | 只读 `lesson` 会把"当次事故细节"当边界；只读 `phenomenon` 会把"事故"当模型 |
| 2 | 过 §3 的五条判据（N1–N5） | 任一命中 ⇒ **停**，按 §1.2 记一行"不提取 + 命中编号" |
| 3 | 抽**机制句**：把 `lesson` 里"可复用规则 = …"压成**一句无主语规则**：触发条件 → 必做动作 → 失效后果 | 这一句就是 `description`；压不出 = 回第 2 步按 N2/N5 判不提取 |
| 4 | 定 `id` / `name` / `version`：`id` 用小写连字符 slug（pattern 见 schema）、`name` 是人读名、`version` 从 `v0.1.0` 起 | 文件名必须是 `<id>.<version>.json`（§4.2） |
| 5 | 按 `schema.json::fields` 逐字段填：**只填 required + 用得上的 optional** | 必填一律给实质内容（空格/空串占位按缺失处理）；用不上的 optional **整段省略**，不填空串 |
| 6 | 写 `source`：`type` = `经验文档提取`、`ref` = `3-LEARNED <条目号>`、`date` = 条目**成文日**、`detail` 写"谁/何时/从哪条提炼 + 源事故日期" | 缺条目号 = 来源不可核（`schema.MD` §4）；成文日现读见下 |
| 7 | 自检：机检（§5）＋ 人工四问（§2.1） | 任一不过 ⇒ 回第 5/6 步改；**不许**改 schema 迁就 |
| 8 | 落盘 `library/candidates/<id>.<version>.json`（UTF-8、无 BOM、LF、末尾换行） | 候选目录**不是**正式库；默认校验器不扫它（§5.1） |
| 9 | 记执行档（§1.2） | 下次触发时 §1.1 的 ② 能查重 |

`source.date` 的取值口径：**条目成文日**（引入该条目的提交的 author date），源事故日期写进 `detail`。
现读命令（把条目号换成本条）：

```powershell
git log -S '### 1.73' --format='%h %ad' --date=short -- docs/3-LEARNED.MD
```

### 2.1 填完后的四个自问（人工闸，任一条答不出就不算完）

1. **换人/换天还成立吗**：去掉"这次""我这台机器""这个文件"之后，`description` 仍是一句完整的规则？
2. **失败长什么样**：能否说出"不照它做会怎样"的具体形态（静默绿 / 假红 / 漏检 / 把没判洗成判过）？
3. **边界在不在**：`boundary` 写的是"它**不治**什么"，而不是再写一遍适用范围？
4. **能不能生成一个可执行 workflow**：`success_criteria` 至少两步、缺一步不成立（MM-2/MM-3 的入口条件）？

## 3. 判据：什么样的经验**不该**被提取成模型

> 目的：**防止把一次性事故包装成模型**。N1–N5 任一条命中即**不提取**，理由按 §1.2 记档。
> 这不是"漏了"：`3-LEARNED` 是踩坑记录，模型只收其中**可复用的机制**。

| 编号 | 标准 | 怎么判（可操作） | 命中后 |
|---|---|---|---|
| **N1** | **一次性 / 不可复用**：搬到"另一个项目、另一天、另一个人"就不成立 | 试写 `when_to_use.initial_trigger`：只能靠**这一次**的具体标识符（某个 run id、某个临时路径、某台机器）触发 ⇒ 命中 | 留在 3-LEARNED，不建卡 |
| **N2** | **无可执行验收**：写不出一条"缺一步就不成立"的 workflow | 试填 `success_criteria`：每条都只能是"注意/小心/加强/多检查"这类不可断言的措辞 ⇒ 命中 | 不建卡；条目补成可断言形态后再提 |
| **N3** | **靠具体工具/项目名才成立**：换掉某个工具版本、某个脚本名、某棵目录树，机制就消失 | 把 `description` 里的专有名替换成"某工具/某脚本"后：句子仍成立 = 模型；句子失效 ⇒ 命中 | 归入条目/操作手册，不建卡 |
| **N4** | **与既有候选同构**：同一机制、只换了事故现场 | 拿新机制句比对 `library/candidates/` 既有卡的 `description`：动作与失效后果同构 ⇒ 命中 | **不新开卡**：追加进既有卡的 `examples` / `boundary`，记"并入 <id>" |
| **N5** | **机制未定性**：只有现象与临时绕法，`fix` 说不出"为什么这样能治" | 读 `fix`：若只是"改成 X 之后就不红了"，且说不出 X 治的是哪个失效 ⇒ 命中 | 不建卡（宁缺勿凑），等机制解释落进条目再提 |

补两则口径：

- **一条条目最多产出一张卡**（宁缺勿凑）；一张卡可以吸收多条同构条目（走 N4 的"并入"）。
- **判据优先于数量**：某一批一条都不该提 ⇒ 合法结论，照 §1.2 记档即可；**不许**为了"每批都有产出"硬提。

## 4. 产物形态

### 4.1 落点与 `status` 取值

- 落点：`docs/iteration/phases/mental-models/library/candidates/`（**专放候选卡**）。
- **候选不进 `library/` 正式目录**，除非人审通过（理由见 §4.4）。
- `status` **一律 `草案`**。schema 的三态语义是 `草案 → 验证中 → 已固化`：`验证中` = 已被实例化并在跑、
  `已固化` = 首跑与 `validate-spec` 均通过（MM-3）。候选卡还没实例化 ⇒ 只能是 `草案`。
  **不要**用 `验证中` 表达"我认真写过了"——那是状态词滥用，会让人审误判进度。

### 4.2 文件名与编号

- 文件名 = `<id>.<version>.json`（例：`executable-form-coverage.v0.1.0.json`）。
- **为什么不是 `<id>.json`**：校验器把"文件名 = `<id>.<version>.json`"当**跨文件判据**（`schema.json::cross_file_rules` X1）。
  写成 `<id>.json` 会被点名 `文件名必须是 …` 并 rc=1——这是**校验器在正确工作**，不是它的 bug（反向对照见 §5.3）。
- **编号**（沿用 `models/` 的 `CM-N` 序列）：schema 没有编号字段，且**不得**为它私加顶层键（未知键 FAIL）。
  把 `CM-N` 放进 `tags`（≤20 字、不渲染进 spec），检索与去重都靠它。

### 4.3 最小字段集（= `schema.json` 的 required；字段清单以它为准）

| 类别 | 字段 | 备注 |
|---|---|---|
| 元字段 | `schema_version`、`id` | `schema_version` 写 `0.1`（主版本须与 `schema.json` 相同，否则拒载） |
| 语义必填 | `name`、`version`、`description`、`when_to_use`、`boundary`、`input`、`output`、`founder`、`source`、`success_criteria`、`status` | 共 11 条；`when_to_use` / `input` / `output` / `source` 是对象，**内层键也有必填** |
| 本 SOP 额外要求 | `source.ref` | schema 里是可选，但**经验文档提取必须写条目号**，否则来源不可核 |
| 常见可选 | `simulation_steps`、`thresholds`、`tags`、`examples` | `examples` 只写**真实发生过**的实例，不编造 |

- **候选卡与正式模型字段同源**：不删字段、不改名、不"先随便写写"。人审通过后只需改 `status` 并搬进
  `library/`（改名保留版本段），**不需要重裁字段**。
- `related_models` 可指向**尚未入库**的候选 id（schema 允许），但不要指向不存在的字符串——那是死指针。

### 4.4 为什么候选不进正式 `library/`

| 理由 | 具体后果 |
|---|---|
| 目录即状态 | `library/` 的口径是"已过校验的正式库"（`schema.MD` §1）；候选进去会让"库里有几个模型"把草稿算进去 |
| 唯一性判据被占用 | X2（`id` 唯一）/ X3（`name` 唯一）是**库内**判据；草稿进库后改名/合并就变成"删库文件"，而不是"改草稿" |
| 人审是必经步骤 | 候选卡是人审的**输入**，不是产物；入库 = 人审 + 首跑（MM-3）之后的动作，不是提取动作的自动结果 |
| 机检口径要分清 | 默认 `mental-model-check.py` 扫 `library/*.json`（不递归）⇒ 候选目录天然不在"正式库是否合规"的判定里 |

## 5. 机检：候选卡必须过 `mental-model-check.py`

### 5.1 命令与判据

```text
python scripts/mental-model-check.py --model docs/iteration/phases/mental-models/library/candidates/<id>.<version>.json
```

- **通过**：倒数第二行 `checked <N> model(s) against schema <版本>`（条数与版本以现跑为准），**末行 `OK`**，rc=0；
- **不通过**：逐条 `文件: 字段路径: 期望 …，实际 …`，末行 `FAIL: <N> 项`，rc=1（一次报全，不 fail-fast）。

两条口径：

- **必须带 `--model`**：默认调用只扫 `library/*.json`（**非递归**）⇒ 候选目录不在默认扫描集里。
  "默认跑"判的是"正式库是否合规"，"`--model` 跑"判的是"这张候选卡是否合规"，两条命令各管一件事，不互相冒充。
- 校验器**只读、零依赖、未接入 `verify/` 门禁**（`schema.json::validator.wired_into_verify=false`）：
  它是**提取动作的验收**，不是仓库门槛。跳过它 = 这张卡不算交付。

### 5.2 失败怎么处置

| 失败形态 | 校验器会点名 | 处置 |
|---|---|---|
| 缺必填字段 / 空值 | `缺必填字段（期望 …）` | 补实质内容；**不许**用空格或空串占位（`robust.missing_required` / `blank_value`） |
| 拼错字段名 | `未知字段（拼错字段名一律 FAIL…）` | 按 schema 的键名改；私有扩展只能用 `x_` 前缀 |
| 枚举越界（`status` / `source.type`） | `期望 取值 草案 / 验证中 / 已固化` 或三值来源 | 改值，**不猜**（F4 不模糊匹配） |
| 嵌套缺键（`when_to_use` / `input` / `output` / `source`） | `… 缺必填键（期望 对象(键：…)）` | 补内层键；`expansion_conditions` / `materials` / `artifacts` 至少 1 条 |
| 非法日期 / 正则不符 | `不是合法日期（YYYY-MM-DD）` / `不匹配 ^…$` | 日期用 `python scripts/now-network.py` 现取，不用本机时钟；`id`/`version` 按 pattern 改 |
| 文件名不符 | `文件名必须是 <id>.<version>.json` | 改文件名，内容不动 |

**一律不许的处置**：改 `schema.json` 放宽判据、删判据、把候选复制进 `library/` 绕过、把 FAIL 说成"校验器太严"。

### 5.3 反向对照（证明机检有牙；改本 SOP 或换校验器版本后重跑一次）

```powershell
$tmp = Join-Path $env:TEMP 'mm4-control'
New-Item -ItemType Directory -Force $tmp | Out-Null
$src = 'docs/iteration/phases/mental-models/library/candidates/executable-form-coverage.v0.1.0.json'
# ① 文件名去掉版本段 ⇒ 必须因 X1 rc=1
Copy-Item $src (Join-Path $tmp 'executable-form-coverage.json')
python scripts/mental-model-check.py --model (Join-Path $tmp 'executable-form-coverage.json')
# ② 删一个必填字段 ⇒ 必须逐条点名 rc=1（放到子目录、文件名保持合法，隔离「文件名」判据）
$sub = Join-Path $tmp 'missing'; New-Item -ItemType Directory -Force $sub | Out-Null
$bad = Get-Content $src -Raw | ConvertFrom-Json
$bad.PSObject.Properties.Remove('success_criteria')
$bad | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $sub 'executable-form-coverage.v0.1.0.json') -Encoding utf8
python scripts/mental-model-check.py --model (Join-Path $sub 'executable-form-coverage.v0.1.0.json')
```

判据：① 必须点名"文件名必须是 `<id>.<version>.json`"；② 必须点名缺的那个字段（文件名合法时只报字段，便于隔离变量）。
**两条都红 = 机检有效**；任一条绿 = 先查命令写法（路径、工作目录、`--model` 拼写），再当缺陷报。

## 6. 边界 / 未做（如实记账）

- 本 SOP 只产出**候选卡**：不生成 agent spec（MM-2）、不做实例化与首跑（MM-3）、**不判"这个模型好不好"**（人审）。
- **只读** `docs/3-LEARNED.MD`：条目怎么改由写条目的那一方决定，提取不反向改它。
- 不改 `schema.json`、不改 `library/schema.MD`、不把候选复制进 `library/`。
- `models/` 的历史提取档（`CM-1`…`CM-7`）**保留原样**：字段是 MM-1 交付前的用户原话口径，**不过**现在的校验器；
  是否回填成 JSON 候选是后续决定，本 SOP **不批量搬**（搬迁会伪造"当时就合规"的假象）。
- **与 `schema.MD` §1 的口径差（如实记）**：那里把 MM-4 的产出落在 `models/`（`CM-*`）。本 SOP 把**可机检的候选卡**
  落在 `library/candidates/`，`models/` 继续承接**提取执行档**。两处表述的合并留给 `schema.MD` 的下一次修订
  ——本卡写作用域不含 `schema.MD`，故只登记、不修改。
