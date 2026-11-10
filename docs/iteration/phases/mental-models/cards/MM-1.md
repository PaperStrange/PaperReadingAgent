# MM-1 模型 schema 与库结构：统一字段（名称/版本/描述/使用时机/边界/输入/输出/创始人/来源/成功判据/状态）+ 

- `card`: MM-1
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
2

## 来源
用户 2026-09-07（Q1 独立阶段；Q2 补全草案接受）

## Sprint
**独立并行线（G2 不含、不占其点数；2026-09-25 D4 裁定）**——原写 `Sprint-18（与治理批 G2 并行）`；G2 的口径是"≤14 点纯治理"（见 [`2026-09-25-governance-batch-plan-G2.MD` §0/§8.2](../../../sprint/2026-09-25-governance-batch-plan-G2.MD)），本卡若要启动需用户另行指定批次。

## 正文
模型 schema 与库结构：统一字段（名称/版本/描述/使用时机/边界/输入/输出/创始人/来源/成功判据/状态）+ `library/` 目录 + 种子模型「思维实验」v0.1 入库

## 交付（2026-11-10，UTC+8）

| 交付物 | 路径 | 说明 |
|---|---|---|
| 人读 schema | [`library/schema.MD`](../library/schema.MD) | 字段表（类型/必填/取值域/示例/五段式映射）+ robust/flexible 规则 + 操作步骤 |
| 机读 schema | [`library/schema.json`](../library/schema.json) | 字段规格与取值域的唯一真源；MM-2 直接消费 `fields[].maps_to` 与 `robust`/`flexible` |
| 种子模型 | [`library/thought-experiment.v0.1.json`](../library/thought-experiment.v0.1.json) | 「思维实验」v0.1（依据预研 §2.4 草案，未新增模型） |
| 只读校验器 | [`scripts/mental-model-check.py`](../../../../../scripts/mental-model-check.py) | 零依赖标准库；只读；**不接入 `verify/` 门禁** |

复现命令（成功末行 `OK`、rc=0；以命令输出为准）：

```text
python scripts/mental-model-check.py
```

反向对照（故意造错模型时必须逐条点名、rc=1；以命令输出为准）：

```text
python scripts/mental-model-check.py --model <坏模型路径>
```

口径说明：

- 本卡不手抄模型条数/字段条数：字段清单以 `library/schema.json::fields` 为准，库存以复现命令输出为准；
  不写“实测 N”这类当期主张（`docs/1-WORKFLOW.MD` §6）。
- 与预研的一致点与两处口径微调（v0.1 两段版本、`simulation_steps`/`thresholds` 可选补位）
  见 [`library/schema.MD`](../library/schema.MD) §9。
- 本卡**未生成任何 agent spec**（实例化与首跑属 MM-3，生成器属 MM-2）。
