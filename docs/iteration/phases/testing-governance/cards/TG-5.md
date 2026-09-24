# TG-5 P3 分层 runner + cron 夜间全量联网套件（fail-closed）。**参数已预决（D3）**：每周一次

- `card`: TG-5
- 索引: [../backlog.MD](../backlog.MD)

## 状态
✅ **完成（Sprint-16）**

## 规模
3

## 来源
用户 2026-08-31（D3 预决，设计约束入卡）；调研结论 run-047（三态预算闸门）｜**终态证据**：`verify/verify_runner.py` **42 断言**、`run_suite.py` 三档（offline **14** / gui 21 / network 10）、离线套件 **SUITE PASSED（14 脚本）**、`scheduled-tasks.py` 三态预算闸门（超限拒跑 3 / 成本 unknown 拒放行 4 / 自动回填解除）+ `register-scheduled-tasks.ps1`

## Sprint
Sprint-16

## 正文
P3 分层 runner + cron 夜间全量联网套件（fail-closed）。**参数已预决（D3）**：每周一次、单轮预算上限 ¥10、**上限必须可配置（config/env 驱动，不得写死文件）**
