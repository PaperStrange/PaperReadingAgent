# TG-9 **新脚本产物目录约定**（Retro 行动项 ④）：新脚本产物默认写**已忽略目录**（运行态 JSON → `age

- `card`: TG-9
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**已完成（2026-09-25，Sprint-17 D2）** —— 交付物与实测证据见下方「交付与实测」，约定真源为 `agents/policy.json::artifact_paths`

## 规模
1

## 来源
**Retro 行动项 ④（Sprint-16）+ 用户 2026-09-21 确认进 S17**

## Sprint
Sprint-17（治理批 G1）

## 正文
`[用户插入]` **新脚本产物目录约定**（Retro 行动项 ④）：新脚本产物默认写**已忽略目录**（运行态 JSON → `agents/runtime/`、日志/截图 → 已 gitignore 的 `verify/*.log\|png`、临时结果 → `%TEMP%`），并在 `verify/README.md` 与 `1-WORKFLOW.MD` 写明"新增脚本前先确认产物路径已忽略"；配套：`.gitignore` 增补运行态文件清单

## 证据
本轮两次误入库（`verify_checkpoint_run.log`、`ci_fail_log.txt`）已被清理并 gitignore

## 交付与实测（2026-09-25，Sprint-17 D2｜commit `bc76083`）

**① 交付物**：守门闸门 `verify/verify_artifact_paths.py`（`tier=offline`，已进离线套件）；约定条文写进 `docs/1-WORKFLOW.MD` §6「新脚本产物目录约定（TG-9…）」；唯一真源 = `agents/policy.json::artifact_paths`（忽略根清单 / 扫描集 / 已入库数据文件例外 / 临时落点写法 / 动态目标棘轮上限）。

**② `.gitignore` 侧写法（目录级 + 白名单）与选择理由**：`agents/runtime/*` + `!agents/runtime/prices.json` + `!agents/runtime/tg14-baseline.json`（`.gitignore:38-40`）。**为什么必须用 `dir/*` 而不是 `dir/`**——父目录被整体排除时 git **无法**用 `!` 重新包含其中的文件（实测：`agents/runtime/` 写法下 `!prices.json` 仍判"已忽略"，白名单形同虚设；`dir/*` 写法下 `prices.json` rc=1=未忽略、新文件 rc=0=被忽略）。这一条是"新产物默认忽略"与"数据文件入库"能同时表达的唯一形态。

**③ 闸门断言（10 条，`ALL PASS`）**：扫描集写盘目标必须落已忽略路径或 `%TEMP%`（逐条点名）／忽略根**双向差集**（政策声明根须真被忽略 + `.gitignore` 确有其行 + 确有代码在用；反向每个已忽略落点须归到某条声明根）／动态目标棘轮按文件设上限（未登记即 FAIL）／反向对照四类（注入写仓库根 → rc=1 点名；写默认落点 `agents/runtime/` → rc=0；实跑产物后 `git status --porcelain` 为空；`--ignored=matching` 下可见，证明上一条不是"路径不存在"造成的假绿）。

**④ 终态证据**：`verify/run_suite.py --tier offline` → `SUITE PASSED`（**套件 20→21** 个脚本，本闸门在内）；`verify/verify_matrix.py derive` → **矩阵 51→52**（`offline 21 / network 10 / gui 21`）并 `check` 一致；`git status --porcelain` 无未跟踪运行态产物。
