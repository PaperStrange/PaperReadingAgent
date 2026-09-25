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

## 交付与实测补证（2026-09-25，`TG-6` 四件套形态）

**为什么补（挑选理由）**：本卡是 **Bug 卡**（预算闸门 fail-open），原 §证据 只有**手抄的断言数与退出码**——没有命令原文、没有关键输出行、没有可复跑的反向对照记录，且数字**已漂**（原写"24 断言"，现为 **46**）。Bug 卡尤其需要四件套：`TG-6` ⑤ 要求"修好了"必须能被别人**倒过来试一次**。

| 证据件 | 内容（2026-09-25 UTC+8 实测） |
|---|---|
| ① 命令原文 | `.venv\Scripts\python.exe verify\verify_runner.py` |
| ② 关键输出行 | `PASS: ⑩a 状态文件损坏 → 拒绝执行（退出 2，无 due 判定、无 RUN）`；`PASS: ⑩a 损坏文件另存 .corrupt 副本（供人工检查）`；`PASS: ⑩b 带 BOM 的合法状态仍被读取（退出 4 REFUSED，且不判损坏）`；`PASS: ⑩c 顶层非 JSON 对象 → 拒绝执行（退出 2）`；`ALL PASS (46 assertions)` |
| ③ 退出码 | **rc=0**（46 断言；旧实现下的失效形态见 ④） |
| ④ 反向对照 | 两类记录。(a) **真实未修复实现上的 FAIL（2026-09-20 走查实证 = 本卡成因事故）**：BOM 状态文件让 `load_state()` 吞掉异常并返回默认空状态 → `last_run` 与成本三态被**静默重置** → `nightly-suite` 被放行并**真实启动**（估算损失约 ¥1.0）。(b) **可复跑变异样本（判据取子进程真实 rc）**：⑩a 截断状态文件 → 退 2 + `.corrupt` 副本留存（旧实现：静默重置 = 放行）；⑩c 顶层非对象 → 退 2；⑩b 带 BOM 的**合法**状态 → 照常读到并退 4 `REFUSED`（**防假红**：不因 fail-closed 把合法 BOM 文件也判死） |

**边界（诚实标注）**：(a) 是当时的事故记录，**不可复跑**（现场已过）；(b) 是脚本内置变异样本，可随时复跑——本卡"修好了"的可核部分由 (b) 承担，(a) 只作为"该失效模式真实发生过"的旁证。
