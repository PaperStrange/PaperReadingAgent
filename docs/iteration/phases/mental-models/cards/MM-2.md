# MM-2 **半自动生成器**：模型 JSON → spec 骨架（schema 字段 → 五段式映射；**robust**=字段

- `card`: MM-2
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
3

## 来源
用户 2026-09-07（Q3：robust & flexibility 为硬约束）

## Sprint
**独立并行线（G2 不含、不占其点数；2026-09-25 D4 裁定）**——原写 `Sprint-18（与治理批 G2 并行）`；G2 的口径是"≤14 点纯治理"（见 [`2026-09-25-governance-batch-plan-G2.MD` §0/§8.2](../../../sprint/2026-09-25-governance-batch-plan-G2.MD)），本卡若要启动需用户另行指定批次。

## 正文
**半自动生成器**：模型 JSON → spec 骨架（schema 字段 → 五段式映射；**robust**=字段缺失降级+validate 前置+失败可解释，**flexible**=字段可扩展+人工可改+schema 演进兼容）

## 交付

2026-11-15；网络时间由 `python scripts/now-network.py` 取得：
`2026-11-15 23:01 UTC+8（来源 https://www.baidu.com/ 的 HTTP Date 头）`。
执行 run：`run-2026-11-15-implementation-148`，分支 `windows`，零提交。

交付文件：

- [`scripts/mental-model-spec.py`](../../../../../scripts/mental-model-spec.py)：
  Python 3.13 标准库生成器，模型/schema 只读，默认 stdout。
- [`thought-experiment.spec.md`](../library/examples/thought-experiment.spec.md)：
  由脚本实际生成、未经手工改写的草稿（行数以脚本输出为准）。

### 用法

在仓库根目录运行（PowerShell）：

```powershell
$model = 'docs/iteration/phases/mental-models/library/thought-experiment.v0.1.json'
$out = 'docs/iteration/phases/mental-models/library/examples/thought-experiment.spec.md'
python scripts/mental-model-spec.py --model $model
python scripts/mental-model-spec.py --model $model --check
python scripts/mental-model-spec.py --model $model --out $out
```

`--schema <path>` 可指定 schema；默认本阶段 `library/schema.json`。
样例现已存在，第三条会拒绝覆盖；明确要重新生成时加 `--force`。
`--check` 与 `--out` 互斥，只校验、不渲染、不写文件。
仓库内输出仅允许位于本阶段目录，文件后缀必须为 `.md`；测试输出可放 `%TEMP%`。

### 字段映射

按 `schema.json::fields[*].maps_to` 分组，不另写字段必填/取值域清单。
仓库 `_template-agent.md` 的五段式名称下实际列有更多标题；本骨架归并为
五个 `##` 主段，保留所需子段，方便人审后实例化。

| schema 字段 | spec 段 / 处理 |
|---|---|
| `name` | Markdown 标题 |
| `description` | Role：用途 |
| `id` | provenance 头；Role / Provenance 中建议文件名 |
| `version`、`founder`、`source` | Role / Provenance；版本另入 provenance 头 |
| `schema_version` | provenance 头；前置主版本兼容检查 |
| `when_to_use` | Trigger (When to use)：初始触发与扩展条件 |
| `input` | Inputs & Outputs / Task Input |
| `output` | Inputs & Outputs / Output Template |
| `success_criteria` | Inputs & Outputs / Done criteria（目标，不声称已达成） |
| `simulation_steps` | Steps；缺省时按输入/输出/验收契约推导通用步骤并标 `derived` |
| `thresholds` | Steps / Configurable Parameters；缺省省略子段并标 `omitted` |
| `boundary` | Forbidden (When not to use / Boundaries) |
| `status`、`tags`、`examples`、`related_models` | 按 `maps_to=—` 不渲染；可选字段缺失仍留降级记录 |
| `x_*` 显式扩展 | 校验放行，不渲染，原 JSON 保留 |
| 同主版本新增可选字段 | 按 `maps_to` 渲染；新目标保留为 Schema addition 子段，缺省留标记 |

五个主段为 `Role`、`Trigger (When to use)`、`Inputs & Outputs`、`Steps`、
`Forbidden (When not to use / Boundaries)`。

### robust / flexible 的落实

**必填缺失选拒绝生成，不选 `<MISSING:字段>` 骨架**：schema 的
`robust.missing_required.action=refuse` 与 `partial_render=false` 已明确裁决；
若把必填缺失渲染为草稿，会让不完整契约被误用。诊断中的 `<MISSING>` 仅表示实际缺值，
不属于生成物。类型错误同样返回非零；所有错误写 stderr，stdout 无半份骨架。

- R1/R2：先收集校验错误再退出；点名文件、字段路径、期望与实际，不只报首错。
- R3：递归标记可选字段缺失，种子存在若干 `DEGRADED` 标记（条数与位置以现跑输出为准）。
- R4：真实调用未修改的 `mental-model-check.py`；仅接受 rc=0、精确成功输出且 stderr 为空。
  warning/SKIP 不算通过；JSON 重复键、非法常量和空必填另行拒绝。
- R5：完整渲染后写同目录临时文件，刷新后原子发布；失败清理临时文件。
  Windows 使用不覆盖的 rename，`--force` 使用 replace；POSIX 使用原子 hard-link 防覆盖。
- F1/F4：复用校验器拒绝未知键、非法枚举与类型，不自动纠正；`x_` 值不进入 spec。
- F2/F5：校验器消费传入 schema，渲染遍历字段；同主版本新增可选字段不使旧模型失效。
  生成器支持主版本 0，主版本变化拒载；字段改名/删除及别名迁移仍按 schema 规则由人工处理。
- F3：provenance 头和人审填充项明确草稿性质；重跑默认保护已有文件，显式 `--force` 才替换。
  模型和 schema 不回写；R1–R5/F1–F5 原规则同步渲染在 Generation contract 中。

### 反向对照（真实入口）

用 Python `TemporaryDirectory(prefix='mm2-148-')` 在 `%TEMP%` 建两份种子副本，
保留合法文件名 `thought-experiment.v0.1.json`。第一份删除 `description`，第二份设
`description=7`；均实际调用 `mental-model-spec.py --model <副本> --out <临时输出.md>`。
以下为现跑输出；临时目录由测试结束时清理。

```text
CONTROL missing:
C:/Users/NemoH/AppData/Local/Temp/mm2-148-dt9dxs9k/missing/thought-experiment.v0.1.json: description: 期望 {"type": "string", "required": true, "min_chars": 8, "max_chars": 200}，实际 "<MISSING>"；description: 缺必填字段（期望 字符串(8..200 字)）
FAIL: 1 项；未生成 spec
rc=1; stdout_chars=0; output_exists=False
CONTROL wrong-type:
C:/Users/NemoH/AppData/Local/Temp/mm2-148-dt9dxs9k/type/thought-experiment.v0.1.json: description: 期望 {"type": "string", "required": true, "min_chars": 8, "max_chars": 200}，实际 7；description: 期望 字符串(8..200 字)，实际 int 7
FAIL: 1 项；未生成 spec
rc=1; stdout_chars=0; output_exists=False
CONTROL normal:
rc=0；行数与段数以现跑输出为准；产物与随卡样例逐字节一致
## Role
## Trigger (When to use)
## Inputs & Outputs
## Steps
## Forbidden (When not to use / Boundaries)
```

正常种子落盘命令为用法中的第三条，rc=0，真实输出：

```text
OK: generated docs/iteration/phases/mental-models/library/examples/thought-experiment.spec.md
```

其后再次以默认 stdout 生成，断言与磁盘样例逐字相同。
扩展验证真实入口 `ALL PASS`（条数以现跑末行为准）：包括一次报出全部错误、可选缺失降级、
`x_` 保留而不渲染、schema 新增可选字段兼容旧模型且能渲染新值、非法日期/枚举/主版本/
空值/未知键/重复键拒绝、已有草稿默认保护、坏输入即使 `--force` 也不破坏旧稿、
正确 `--force` 完整替换、拒写 `agents/`、无临时残留、schema 与种子 SHA-256 不变。
另以标准库 mock 注入两类失败：校验器 rc=0 但返回 warning/SKIP 时仍拒绝；
原子替换抛出 OSError 时，原稿字节不变且临时文件已清理，两项均 PASS。

门槛：`python -m py_compile scripts/mental-model-spec.py` rc=0（末行为准）；
`.venv\Scripts\python.exe verify\verify_lint.py` rc=0，末行以现跑为准（此处不抄机器证据行）。

```text
```

E501 未新增（读数以 `verify_lint.py` 现跑末行为准）；Python 行显示宽度均 ≤88（CJK=2），无超宽行。
本卡脚本、生成物与卡片均使用 LF。

收尾后运行 `.venv\Scripts\python.exe verify\verify_close_readiness.py --sprint docs\iteration\sprint\2026-09-25-sprint-18.md`，rc=0：

```text
`CLOSE-READINESS PASS`（判据数、run 表行数与覆盖提交数以现跑输出为准）
```

登记 HEAD 为 `443fe4f7a6f043b9bed3db66382803f7dd61c2ac`；收尾时共享工作区已出现
另一笔提交 `b24c8c7f284f09cf7fdf523e11a3b8725404be5b`，只涉及同步记录，
不是本 run 产出。本 run 未执行提交，三个交付文件仍未提交；按用户要求以现读 HEAD
执行 `set-anchor --covers-through`，CLI 报同值、无变化，不冒称新增回填记录。

### 为什么不写入 agents/

Q3 已拍板先做「骨架 + 人审填充」。本卡只证明模型 JSON 能生成完整、可编辑的草稿；
正式 agent 实例化、`validate-spec` 和首跑演示属于 MM-3，本轮不执行。
MM-4 的经验提取、MM-5 的自适应扩展机制也未实现；模型中的扩展条件只按原文展示。
生成器拒绝把 `--out` 写到仓库 `agents/`，样例落在本阶段 `library/examples/`。
按用户第 0 步所需的 register/finish 台账与报告归档由 `agent-ops.py` 处理，
不属于正式 agent spec 发布。不改门禁、政策、schema、种子或其他卡，不暂存、提交或推送。
