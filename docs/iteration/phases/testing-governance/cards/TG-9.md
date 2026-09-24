# TG-9 **新脚本产物目录约定**（Retro 行动项 ④）：新脚本产物默认写**已忽略目录**（运行态 JSON → `age

- `card`: TG-9
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**计划中（Sprint-17，用户 2026-09-21 确认）**

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
