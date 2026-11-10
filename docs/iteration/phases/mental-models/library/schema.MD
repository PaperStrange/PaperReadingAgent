# 思维模型库 schema（v0.1）

> 归属：`docs/iteration/phases/mental-models/library/`（windows-only 迭代区；成熟模型可提升共享层）。
> 交付卡：[`MM-1`](../cards/MM-1.md)；预研基线：[`2026-09-07-mental-models.MD`](../../../pre-research/tech/2026-09-07-mental-models.MD)。
> **本文件是人读说明；机读真源是 [`schema.json`](schema.json)**——字段清单、必填性、取值域、
> robust/flexible 规则以它为准。两者不一致时按 `schema.json` 修本文件，不反向改 schema 迁就文字。

## 1. 这个目录是什么

`library/` = **已过 schema 校验的正式模型库**。它与同阶段 `models/` 的分工必须一眼分清，
否则"候选草稿"会被误读成"模型已入库"：

| 目录 | 内容 | 谁写 | 状态口径 |
|---|---|---|---|
| `library/` | `schema.json` + `schema.MD` + 正式模型（`<id>.<version>.json`） | 本卡建立；后续入库须过校验器 | 文件内 `status` 字段：草案 / 验证中 / 已固化 |
| `models/` | MM-4 从 `docs/3-LEARNED.MD` 提取的候选草稿（`CM-*`） | 主代理主管（每次 3-LEARNED 更新时执行） | 候选；**未经重新裁决不算入库**，也不得据以改 `agents/functions/**` |

## 2. 文件结构

| 文件 | 作用 |
|---|---|
| [`schema.json`](schema.json) | 机读 schema：字段规格、跨文件规则、robust/flexible 规则、校验器契约 |
| [`schema.MD`](schema.MD) | 本文件：人读说明与操作步骤 |
| `<id>.<version>.json` | 一个模型一个文件；文件名**严格等于** `id` + `.` + `version` + `.json` |
| [`thought-experiment.v0.1.json`](thought-experiment.v0.1.json) | 种子模型「思维实验」v0.1（内容依据预研 §2.4 草案） |

## 3. 字段

字段清单以 `schema.json::fields` 为准（本节是它的可读投影）。类型列里的长度均为**去空白后**的字符数。
`maps_to` 列给出 MM-2 生成器到 agent spec 五段式的映射目标（预研 §2.2）。

### 3.1 语义字段（必填，与预研 §2.1 的字段表逐项对应）

| 字段 | JSON key | 类型 | 必填 | 取值域 | 映射五段式 | 示例 |
|---|---|---|---|---|---|---|
| 名称 | `name` | string | 是 | 2..40 字；库内唯一 | spec 标题 | 思维实验 |
| 版本 | `version` | string | 是 | 匹配 `^v\d+\.\d+(\.\d+)?$` | 溯源头 | v0.1 |
| 描述 | `description` | string | 是 | 8..200 字 | Role | 对一个问题生成不少于三种解决方案，模拟每个方案的解决过程并输出比对文档 |
| 使用时机 | `when_to_use` | object | 是 | `initial_trigger`（4..120 字）+ `expansion_conditions`（1..6 条，每条 4..200 字） | Trigger | initial_trigger：检测到用户输入讨论时启用 |
| 边界 | `boundary` | string[] | 是 | 1..9 条，每条 4..200 字 | Forbidden | 不适用于纯事实查证（走 M16 调研分级机制） |
| 输入 | `input` | object | 是 | `materials`（1..9 条）+ 可选 `format`（≤120 字） | Task Input | materials：一个问题/决策主题；上下文 |
| 输出 | `output` | object | 是 | `artifacts`（1..9 条，每条 4..240 字）+ 可选 `format` | Output Template | 比对文档：≥3 个方案 ×（推演、预期效果、风险、适用条件） |
| 创始人 | `founder` | string | 是 | 2..120 字 | 溯源头 | 爱因斯坦（思想实验方法论的代表性实践者） |
| 来源 | `source` | object | 是 | `type` 三选一 + `detail`（4..300 字）+ 可选 `ref`（≤120 字）+ `date`（YYYY-MM-DD） | 溯源头 | type：用户输入；date：2026-09-07 |
| 成功判据 | `success_criteria` | string[] | 是 | 1..6 条，每条 4..200 字 | 验收 | 通过 validate-spec；首跑演示产出三方案比对文档 |
| 状态 | `status` | enum | 是 | 草案 / 验证中 / 已固化 | — | 草案 |

### 3.2 元字段（必填，供机器定位与演进）

| 字段 | JSON key | 类型 | 必填 | 取值域 | 映射五段式 | 示例 |
|---|---|---|---|---|---|---|
| schema 版本 | `schema_version` | string | 是 | 匹配 `^0\.\d+$`；主版本须与 `schema.json` 相同 | — | 0.1 |
| 机器标识 | `id` | string | 是 | 匹配 `^[a-z][a-z0-9-]{1,38}$`；库内唯一 | spec 文件名 | thought-experiment |

### 3.3 可选扩展字段（可省略；出现即须合法）

| 字段 | JSON key | 类型 | 必填 | 取值域 | 映射五段式 | 示例 |
|---|---|---|---|---|---|---|
| 模拟推演步骤 | `simulation_steps` | string[] | 否 | 1..9 条，每条 4..200 字 | Steps | 生成不少于 3 个候选方案，逐方案写清核心假设 |
| 可调阈值 | `thresholds` | string[] | 否 | 1..9 条，每条 4..200 字 | Configurable Parameters | 候选方案数下限 = 3 |
| 标签 | `tags` | string[] | 否 | 1..8 条，每条 1..20 字；不渲染 | — | 决策；方案比较 |
| 实例 | `examples` | string[] | 否 | 1..5 条，每条 4..400 字；只写真实发生过的实例 | — | （可选）首跑比对文档路径 |
| 相关模型 | `related_models` | string[] | 否 | 1..8 条，每条 1..40 字（模型 id） | — | scope-enumeration |

> 为什么有 `simulation_steps` 与 `thresholds`：预研 §2.2 的五段式映射需要 Steps 与
> Configurable Parameters 两个来源，但 §2.1 的字段表未单列它们。本 schema 以**可选字段**补位，
> 既让映射完备，又不把 11 个必填字段的基线改掉（详见 §9）。

## 4. 取值域细则

- **`status` 生命周期**：`草案 → 验证中 → 已固化`（预研 §2.1）。状态只由人工改；
  `验证中` 表示已被实例化并在跑，`已固化` 表示首跑与 `validate-spec` 均通过（MM-3 的判据）。
- **`version` 口径**：schema 接受 `vMAJOR.MINOR` 与 `vMAJOR.MINOR.PATCH` 两/三段。
  预研 §2.4 的种子写作 `v0.1`（两段），故种子照抄两段；**新模型推荐三段**。
- **`source.type` 三值**：用户输入 / 探讨交流 / 经验文档提取（预研 §2.1）；
  经验文档提取须在 `source.ref` 写条目号（如 `3-LEARNED 1.70`），不写条目号 = 来源不可核。
- **`source.date`**：来源发生日期，网络时间 UTC+8（`scripts/now-network.py`），不得用本机时钟。
- **`id`**：小写连字符 slug，决定文件名与 MM-2 生成物路径；改名 = 新 id + 主版本升级。
- **空值**：必填字符串去空白后为空一律按**缺失**处理（不允许空格/换行占位），见 robust R1。

## 5. robust（Q3 硬约束：缺字段不许半渲染）

机读规则在 `schema.json::robust`；本节是它的可读投影。

| 编号 | 规则 | 机读落点 | 现在由谁执行 |
|---|---|---|---|
| R1 | 任一必填字段缺失/为空/类型不符 ⇒ 拒绝生成，仓库里不得出现半成品 spec | `robust.missing_required`、`robust.blank_value` | 校验器：rc=1 并点名；生成器：MM-2 落地"拒绝产出" |
| R2 | 一次报全，不 fail-fast；每条含 文件 + 字段路径 + 期望 + 实际 | `robust.missing_required.report=all`、`robust.invalid_value` | 校验器（已实现，反向对照见 §7） |
| R3 | 可选字段缺失只允许"按规则推导"或"省略对应小节"，两种都打 `DEGRADED:<field>:<derived 或 omitted>` | `robust.optional_missing` | 生成器：MM-2；校验器只保证可选字段出现时合法 |
| R4 | 生成前先跑校验器且必须 rc=0；warning/SKIP 不算 pass | `robust.generator_precheck` | 生成器：MM-2 |
| R5 | 失败可定位（文件/字段/期望/实际）；产物先写临时文件、成功后改名 | `robust.atomic_publish` | 生成器：MM-2；校验器本身只读，无产物 |

**能力边界（诚实标注）**：本卡只交付**校验器**。"拒绝产出、DEGRADED 行、原子发布"是生成器行为，
本卡**没有实现**，只把契约写进 `schema.json` 供 MM-2 直接消费。校验器现在可证的是：
必填缺失/空值/类型/取值域/未知键/文件名/唯一性都会 rc=1，且一次列全（不 fail-fast）。

## 6. flexible（Q3 硬约束：字段可扩展 / 人工可改 / schema 演进兼容）

| 编号 | 规则 | 机读落点 | 具体机制 |
|---|---|---|---|
| F1 | 字段可扩展 | `flexible.extension_prefix`、`prefixed_key`、`unknown_key` | 扩展键以 `x_` 开头：校验放行、不渲染；非前缀未知键（含拼错的 `descripton`）一律 FAIL |
| F2 | schema 可演进 | `flexible.schema_version_compat`、`evolution` | 同主版本只做加法（新增可选字段）；改名/删除 = 主版本升级 + 旧名保留 1 个小版本别名 |
| F3 | 人工可改 | `flexible.human_edit` | 生成物是草稿、带 provenance 头；重跑默认不覆盖，`--force` 才覆盖；`library/` 文件只许人改 |
| F4 | 不猜意图 | `flexible.rules[F4]` | 取值域外的值不模糊匹配/不自动纠正，一律拒绝并点名（如 `status` 拼错不猜） |
| F5 | 向后兼容 | `flexible.rules[F5]` | 新模型只填必填 + 需要的可选字段即可入库；schema 新增可选字段不得让旧模型失效 |

**主版本不兼容 = 拒载**：模型文件 `schema_version` 的主版本与 `schema.json` 不同时，校验器直接 FAIL，
不尝试迁移或猜测——迁移是人的决定，不是校验器的。

## 7. 校验（复现命令，以命令输出为准）

```text
python scripts/mental-model-check.py
```

- 成功：倒数第二行给 `checked <N> model(s) against schema <版本>`，**末行 `OK`**，rc=0；
- 失败：逐条 `文件: 字段路径: 期望 …，实际 …`，末行 `FAIL: <N> 项`，rc=1；
- 只读：不写任何文件；**不接入 `verify/` 门禁体系**（本批明确不做，接入是后续卡的决定）；
- 零依赖：Python 3.13 标准库，无第三方包。

反向对照（故意造错必须被点名，rc=1）：

```text
python scripts/mental-model-check.py --model <坏模型路径>
```

坏模型的构造口径：至少覆盖"缺必填字段 / 拼错字段名 / 枚举越界 / 嵌套缺键 / 非法日期 / 文件名不符"
六类之一；输出应逐条点名，而不是只报第一条。

## 8. 新增一个模型的步骤

1. 在 `library/` 新建 `<id>.<version>.json`（可从最近模型复制，删掉不适用字段）；
2. 填 `id`、`version`、`name`、`schema_version`，并保证**文件名与 `id.version` 一致**；
3. 填全部必填字段；可选字段按需，不需要就整段省略（不要填空字符串占位）；
4. 跑 §7 的命令直到 rc=0；**失败时按点名逐条改**，不要靠改 schema 放宽判据；
5. `status` 从 `草案` 起步；实例化/首跑（MM-3）通过后才由人工改 `验证中` / `已固化`；
6. **不要**把 `models/` 的候选草稿直接复制进 `library/` 就算入库——候选须先按本 schema 重裁字段。

## 9. 与预研基线的一致点与口径说明

| 基线项 | 本交付如何落实 | 口径说明（差异/待决） |
|---|---|---|
| Q1 = 独立阶段，库结构在 `phases/mental-models/` | `library/` 落在本阶段目录内；`schema.MD` + `schema.json` + 种子模型三件套 | 与预研 §2.3 草案一致；成熟模型提升共享层留待后续卡 |
| Q2 = 种子模型补全草案接受 | [`thought-experiment.v0.1.json`](thought-experiment.v0.1.json) 逐字段照 §2.4 入库；**未新增任何模型** | 只把 §2.4 的描述拆成 `simulation_steps`/`thresholds` 两个可选字段承载，不新增语义 |
| Q3 = 半自动 + robust + flexible 为硬约束 | `schema.json::robust`（R1–R5）与 `::flexible`（F1–F5）给出**具体规则与机读落点** | 生成器本卡不做；规则已按"MM-2 直接消费"的形态写 |
| §2.1 的 11 个字段 | 11 个语义字段逐项对应，必填；名称/版本承担"唯一标识 + 语义化版本" | 名称与 id 拆开：`name` 供人读、`id` 供机器定位（文件名/生成物路径） |
| §2.1 的 status 三态 | `草案 / 验证中 / 已固化` 照抄为枚举 | 无差异 |
| §2.2 的五段式映射 | 每个字段带 `maps_to`；`simulation_steps → Steps`、`thresholds → Configurable Parameters` | **补位说明**：§2.1 字段表未单列这两项来源，schema 以可选字段补位（不破坏 11 必填基线） |
| §2.4 的 `v0.1` | 版本正则接受两段与三段 | **口径微调**：§2.1 说"语义化版本"、§2.4 写两段 `v0.1`；两段合法、新模型推荐三段 |

## 10. 版本与演进

- 本 schema 版本 `0.1.0`；模型文件声明 `schema_version: "0.1"`（主版本相同即兼容）。
- **加法演进**（新增可选字段）= 小版本；**改名/删除字段** = 主版本 + 别名窗口（见 §6 F2）。
- 改字段/取值域时**同一提交内**同步改 `schema.json` 与本文件；不一致即视为 schema 缺陷。
- 校验器不加新判据来"补 schema 的漏"：判据只有两类——schema 声明的、以及文件级/跨文件的结构约束。
