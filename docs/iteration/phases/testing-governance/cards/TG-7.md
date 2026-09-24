# TG-7 **预算闸门 fail-open**：`scripts/scheduled-tasks.py` 的 `load_stat

- `card`: TG-7
- 索引: [../backlog.MD](../backlog.MD)

## 状态
✅ 完成（2026-09-20 当日闭环）

## 规模
2

## 来源
**走查演示发现 2026-09-20（UTC+8）**（事故实证：BOM 状态文件使 `nightly-suite` 被放行并真实启动，估算损失约 ¥1.0）

## Sprint
Sprint-16（走查修复）

## 正文
`[Bug]` **预算闸门 fail-open**：`scripts/scheduled-tasks.py` 的 `load_state()` 吞掉所有异常并返回默认空状态（line 76–82）→ 状态文件损坏/带 UTF-8 BOM/手工编辑出错时，`last_run` 与成本三态被**静默重置**，预算闸门不再拦截，带预算的任务被放行（与 3-LEARNED 1.54 的 fail-closed 口径直接冲突）。修法：解析失败即 **fail-closed**（非零退出 + 明确文案 + 保留损坏文件副本），并给 `verify_runner.py` 增"损坏 state → 拒绝"断言；顺带标注"本机 PowerShell 5.1 的 `Set-Content -Encoding utf8` 会写 BOM"这一操作陷阱

## 证据
**证据**：`load_state` fail-closed（`utf-8-sig` 容忍 BOM + `.corrupt` 副本 + 退出 2）；`verify_runner.py` **24 断言全 PASS**（⑩a 截断→拒 2 + 留副本 / ⑩b 带 BOM 合法状态照常读到并 REFUSED / ⑩c 顶层非对象→拒 2）；BOM 反证由 RUN 转 REFUSED(4)；教训入 `3-LEARNED` 1.58
