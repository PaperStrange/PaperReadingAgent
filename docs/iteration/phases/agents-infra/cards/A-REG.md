# A-REG 派单登记可验证性：规则 14 现为荣誉制（账本分不清谁按的键）

- `card`: A-REG
- 索引: [../backlog.MD](../backlog.MD)

## 状态
完成

## 规模
3

## 来源
2026-09-29 doc-audit-104 判规则 14 为 unverifiable；同日 C3 抓出 9 个提交无归属

## Sprint
—

## 正文
规则 14 要求「派单方在派单时登记 run」，但账本记录只有一条 run 行，无法区分是派单方还是执行方写入；`doc-audit-104` 的规则一致性表因此判 `unverifiable`。

实证缺口：关闭期 **9 个提交无归属**（`958c739878..18f2274eab`，非 doc-only 9 笔），只能靠关闭流水线 C3 事后抓出，并用**补登记 run**（归属，非评审）收口。

**方向**：① 提交 ↔ run 绑定（提交信息带 run_id 或 pre-commit 校验）；或 ② 承认它是口径，并把 C3 事后抓出作为**唯一**兜底，则须写明归属 ≠ 评审。

**验收**：任选一条路径，给出「未登记 run 的提交」能被**在提交时**拦下、或能被**明确列为兜底**的判据。

## 落地（2026-11-12）

按 Lead 2026-11-12 裁定走 **①＋②** 组合；**不做**阻断式钩子（第 0 步之外的提交不受影响）。

### ① 写入者身份（谁按的键）

**取证**（现查本机本会话，不猜）：`[Environment]::GetEnvironmentVariables()` 与
`Get-ChildItem env:` 的实测可用识别源 =
`DSH_SESSION_ID`、`DSH_PROFILE`、`USERNAME`、`COMPUTERNAME`；
`DSH_AGENT_*` 在本环境**不存在**（故不采信、不写进 `src`）。

**字段形态**（只增字段，既有字段语义一个不动）：

```
writer = {"by": "dsh_session_id=…|username=…|computername=…",
          "how": "env" | "flag" | "unknown", "src": [采信的 env 键], "at": ISO8601}
writer_trail = [ {…writer, "cmd": "register|update|finish", "status": …}, … ]
```

`how` 三档：`flag` = 调用者显式 `--by`；`env` = 现查环境变量取证；`unknown` = 两路都
拿不到——此时 `by="unknown"` 且**回执上屏说明**（不伪造身份）。`--by` 也可显式覆盖 env。

**落点**：`register` / `update`（queued→running 也算状态变更）/ `finish`，
以及 `set-anchor`、`set-scope`、`set-sprint`、`set-result-files`、`set-output-chars`、
`set-started-at`、`mark-produced`、`retract` 的回填留痕（每条留痕多一个 `writer`）。
顺带把 `--by` 的默认值从 `main-agent` 改成空串、写入时回落 `args.by or "main-agent"`
——**账本里落的值逐字不变**，但 `how` 从此能区分"显式声明"与"默认值"（否则 `how`
只能是谎报的 `flag`）。

**旧行兼容证据**：读侧 `writer_of()` 对无该键的行返回 `how="legacy"`，`list` 对旧行
输出**逐字不变**（不多出 `by=`）。两条反向对照：UC-28 ⑦ 把 `writer`/`writer_trail`
从整本夹具账本剥掉、按 CLI 同一口径重算 `integrity` 后 `list` 仍 rc=0 且输出无 `by=`；
UC-28 ⑧ 真账本（存量行全部无 `writer`）照常读出。复现：`python verify/verify_agentops.py`。

**写入者侧反向对照读数**（同一条命令现跑）：env／flag／unknown 三档各一条；
`writer_trail` 在 finish 后为两条（register＋finish）、queued→running 后为两条
（register＋update）；回填口 `anchor_backfills[-1]` 同时有 `writer` 与既有 `by`，
且**未给 `--by` 时 `by` 仍是 `main-agent`**（字段语义未改）。

### ② 提交 ↔ run 绑定（咨询式，不阻断）

**约定**：提交信息里可带 `run: run-YYYY-MM-DD-<role>-<n>`（`run:` 前须词边界，
`rerun:` 不算；重复标记去重）。

**口径**（纯函数 `parse_run_markers` / `binding_report`，判定与阈值不在两处各写一份）：

- 带标记 ⇒ 该 run **必须**在账本里存在且 `status=succeeded`，否则 FAIL 并点名
  `sha + run_id`；「登记缺失」与「状态不符」**分开报**（修法不同）。
- **不带标记不 FAIL**：大量提交是主代理直改，规则 14 只约束"派单"类工作；把"无标记"
  判红等于逼人补假标记（假留痕比无留痕更坏）。
- 但仍要能**列出**区间内的「无 run 绑定提交」（`--list-unbound`），供关闭期人工判。

**落点**：`scripts/agent-ops.py check-bindings`（只读子命令；纯函数
`parse_run_markers` / `binding_report` 是判据唯一实现），断言在
`verify/verify_agentops.py` 的 UC-29 里**真驱动**（子进程跑 CLI）。
**为什么没有新建独立闸门脚本**：`verify/verify_artifact_paths.py` 的「未跟踪路径为空」
判据会把**未提交的新文件**判红，而本批禁止 `git add/commit` ⇒ 独立脚本在本批拿不到绿色
套件读数。故落在既有 CLI（判据仍是纯函数、仍可被独立调用），下限同批抬到新实测值。
区间默认最近 50 个提交，`--range` 可指定；不做 pre-commit 钩子（咨询式）。

**三条假提交反向对照（真驱动）**：在 `%TEMP%` 造五个**真** git 仓库、用子进程跑 CLI
真入口（真仓零污染、不产生任何提交）：

1. 带 `run:` 指向**不存在**的 id ⇒ **rc=1**，输出点名 `sha` 与 `run_id`（「登记缺失」）；
2. 带 `run:` 指向**存在且 succeeded** 的 id ⇒ **rc=0**（无违例）；
3. **不带** `run:` ⇒ **rc=0**（不 FAIL），且该提交出现在「无绑定提交」清单里。

另有：`rerun: <id>` 不算标记（词边界，防假命中）；`status=running` ⇒ rc=1 且点名状态；
账本缺失而区间内有标记 ⇒ **第三态 rc=3** 且写「本档不是通过」（不冒充通过）；
区间非法 ⇒ **rc=2**（与"有违例/无违例"都分开）。
复现：`python scripts/agent-ops.py check-bindings --list-unbound`
（真数据档同时上屏 提交/带标记/无绑定 三个计数）。

### 兜底（明示）

**兜底**：C3 事后抓出仍是归属的唯一兜底，且**归属 ≠ 评审**（归属只回答"这笔提交属于哪次
派单"，不回答"它有没有被评审过"；补登记 run 是归属动作，**不是**评审结论）。
本卡交付的是"归属可核 ＋ 声明式绑定可核"，**没有**改变 C3 在关闭流水线里的兜底地位。

### 未决（如实记，不硬说完成的地方）

- `writer` 的识别粒度是**会话／用户／主机**，不是**角色**：同一会话里"派单"与"执行"
  会得到同一个 `by`。要区分派单方／执行方仍须 `--by` 显式声明（或未来把 role 并入
  `writer`）。本卡只保证"每次按键都留下可核的写入者痕迹"，不保证自动判角色。
- `check-bindings` **只对带标记的提交**有强制力：不带标记的提交永远 rc=0、只进清单。
  这是本卡有意的**咨询式**口径（判据②），代价是"该带标记却没带"这件事机检不出来——
  仍要靠 C3 事后抓出（见上「兜底」）。

