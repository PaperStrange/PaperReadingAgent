# MM-4 经验文档→候选模型提取 SOP：主代理主管，每次 3-LEARNED 更新时执行，产出候选模型卡（来源标注条目号）

- `card`: MM-4
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
1

## 来源
用户 2026-09-07（来源③）

## Sprint
—

## 正文
经验文档→候选模型提取 SOP：主代理主管，每次 3-LEARNED 更新时执行，产出候选模型卡（来源标注条目号）

## 落地（2026-11-15）

网络时间由 `python scripts/now-network.py` 取得：`2026-11-15 23:50 UTC+8（来源 https://www.baidu.com/ 的 HTTP Date 头）`。
执行 run：`run-2026-11-15-implementation-150`，分支 `windows`，零提交。

| 交付物 | 路径 | 说明 |
|---|---|---|
| 提取 SOP（人可执行 + 可机检） | [`SOP-extract.MD`](../SOP-extract.MD) | 触发点（含查重命令）／提取步骤／**不该提取**的五条判据（N1–N5）／产物形态／机检与失败处置／边界 |
| 示例候选卡 | [`executable-form-coverage.v0.1.0.json`](../library/candidates/executable-form-coverage.v0.1.0.json) | 从 `3-LEARNED` **1.73** 实际提取；`id` = `executable-form-coverage`，`version` = `v0.1.0`，`status` = `草案` |

候选卡 `status` 取 `草案` 的理由：schema 的三态是 `草案 → 验证中 → 已固化`，`验证中` 的语义是"已实例化并在跑"、
`已固化` 是"首跑与 `validate-spec` 均通过"（MM-3）。本卡只证明"这条经验能被提取成一张合规的候选卡"，
**没有实例化、没有首跑**，故只能停在 `草案`——用 `验证中` 表达"我认真写过了"会让下游误判进度。

### 机检（候选卡是否合格）

```text
python scripts/mental-model-check.py --model docs/iteration/phases/mental-models/library/candidates/executable-form-coverage.v0.1.0.json
```

现跑：倒数第二行 `checked 1 model(s) against schema 0.1.0`（条数/版本以现跑为准），**末行 `OK`**，rc=0。
另跑 `python scripts/mental-model-spec.py --model <同一路径> --check`，rc=0（`OK: model + schema validated; no spec generated`）
——说明它不是"只有字段形状"的空卡，MM-2 的渲染前置检查也认它。

**反向对照**（证明机检有牙，命令见 SOP §5.3；在 `%TEMP%` 里做，不写仓库）：

| 对照 | 注入 | 期望 | 现跑 |
|---|---|---|---|
| ① 文件名去掉版本段 | 复制为 `<id>.json` | 因 X1 rc=1 | `文件名必须是 executable-form-coverage.v0.1.0.json（<id>.<version>.json）`，`FAIL: 1 项`，rc=1 |
| ② 删必填字段 | 去掉 `success_criteria`，文件名保持合法 | rc=1 并点名该字段 | `success_criteria: 缺必填字段（期望 数组[字符串(4..200 字)]）`，`FAIL: 1 项`，rc=1 |

① 同时是本 SOP 把文件名写成 `<id>.<version>.json` 而**不是** `<id>.json` 的证据：后者被校验器判红，不是它太严。

### 为什么候选卡不进正式 `library/`

- **目录即状态**：`library/` 的口径是"已过校验的正式库"（[`schema.MD`](../library/schema.MD) §1）；候选进去会让
  "库里有几个模型"把草稿算进去。
- **唯一性判据被草稿占用**：`id` / `name` 的唯一性是**库内**判据（X2/X3）；草稿进库后改名或合并就变成"删库文件"，
  而不是"改草稿"。
- **人审是必经步骤**：候选卡是人审的**输入**，入库 = 人审 + 首跑（MM-3）之后的动作，不是提取动作的自动结果。
- **机检口径要分清**：默认 `python scripts/mental-model-check.py` 只扫 `library/*.json`（非递归），
  候选目录天然不在"正式库是否合规"的判定里；候选卡一律用 `--model` 单独判。

### 口径与残留（如实记）

- **`backlog.MD` 索引行尚未同步**：本卡写作用域不含 `docs/iteration/phases/mental-models/backlog.MD`，
  其索引行状态列仍写 `候选`；而 `verify/verify_card_index.py` ⑥ 要求"卡文件 ↔ 索引行 ↔ Sprint 看板"三处同词
  （本卡 `Sprint` 为 `—`，看板一档跳过）。**同步索引行是主代理的写作用域**，本卡不改；在此之前该闸门会因这一处判红。
- **与 `schema.MD` §1 的口径差**：那里把 MM-4 的产出落在 `models/`（`CM-*` Markdown）。本轮把**可机检的候选卡**
  落在 `library/candidates/`，`models/` 继续承接**提取执行档**（`CM-1`…`CM-7` 原样保留、不搬不改，因为它们的字段
  是 MM-1 交付前的用户原话口径，不过现在的校验器）。两处表述的合并留给 `schema.MD` 的下一次修订。
- **未做**：不生成 agent spec（MM-2）、不实例化/首跑（MM-3）、不改 `3-LEARNED`、不改 `schema.json`/`schema.MD`、
  不改 `models/`、不批量回填历史条目；本卡只交付 SOP 与**一张**示例候选卡。
- 复现门槛：`verify_md_tables.py`、`verify_derived_numbers.py`、`verify_close_readiness.py --sprint <Sprint-18>`
  末行与 rc 见 run 报告 `run-2026-11-15-implementation-150`（本卡不抄机器读数，以命令现跑为准）。
