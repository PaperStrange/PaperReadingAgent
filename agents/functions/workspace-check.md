---
name: workspace-check
description: 工作区与功能完整性核验手册（主代理执行，不子代理化）：git 状态零残留、分支/端口卫生、.gitignore 覆盖、回归套件全绿。
version: "1.0.0"
model: ""
tools: []
metadata:
  tags: [review, workspace, manual]
  note: 本职能由主代理执行（D2 决策：涉及起服务/杀进程等高风险操作，不交给子代理）
---

# 角色

你是主代理的**环境核验执行手册**（不是子代理 prompt——本职能保留在主代理，见 §3.3 触发分级 D2）。

# 触发

- Sprint 关闭三查（"三查"）；
- 任何"我改完了，收尾吧"的时刻。

# 可配置参数（编辑点：调整只改本节，不改正文规则）

| 参数 | 当前值 | 说明 |
|---|---|---|
| 端口清单 | 5173（前端）、8787（后端）、8501（Streamlit）、8600（agents 看板，阶段 3） | §步骤 3 检查的端口 |
| 回归脚本（离线） | verify_smoke / verify_prune_callbacks / verify_agentops / verify_index_health | 无 API、无网络 |
| 回归脚本（联网） | verify_provider_switch / verify_e2e / verify_e2e_openai / eval_retrieve | 需真实 key（e2e_openai 需账户余额） |
| 回归脚本（GUI） | gui_check*.mjs | 需前后端已启动 + Playwright |

# 步骤（固定顺序）

1. **工作区零残留**：`git status --short` 逐条核对——每个改动文件都应属于本轮改动清单；意外残留（临时文件、生成物、未登记的截图）逐一处理（入库 or gitignore or 删除）。
2. **分支卫生（本地）**：本地分支只剩 main/windows（+ 当前 sync 分支）；过期 sync 分支删除；`git log --oneline -3` 确认 HEAD 与计划一致。
3. **分支卫生（远程，2026-08-30 用户发现盲区后新增）**：`git ls-remote --heads origin` 应为 `mac/main/windows` 三条——**每个已合并 PR 的 `sync/*` 头分支必须删除**（`git push origin --delete <branch>`）；若启用仓库"合并后自动删头分支"设置则自动满足，仍需复查。
4. **端口卫生**：`Get-NetTCPConnection -LocalPort 5173,8787,8501,8600 -State Listen` 全 FREE；若占用 → 按 SOP 定位 PID + `Get-CimInstance Win32_Process` 核对命令行确认是本项目进程 → **只对确认的 PID** `Stop-Process`（绝不按进程名批量杀，见 3-LEARNED 1.11/1.20）→ 复查 FREE。
5. **.gitignore 覆盖**：`git status --porcelain --ignored` 抽查生成物（__pycache__/.venv/node_modules/.next/agents-dashboard/data/data/remote/verify/*.log/*_result.json）是否被正确忽略。
6. **回归套件**（按改动范围选取）：
   - 离线：`verify_smoke.py`、`verify_prune_callbacks.py`、`verify_index_health.py`、`verify_agentops.py`；
   - 联网：`verify_provider_switch.py`、`verify_e2e.py`、`eval_retrieve.py`、`verify_e2e_openai.py`（需账户余额）；
   - GUI（需前后端已启动）：`gui_check*.mjs`；
   - 前端/看板：`npm run build`（agents-dashboard 同）。
   逐项记录 PASS/FAIL 与输出摘要。
7. **收尾**：停掉本轮启动的 dev server 并复查端口；把结论（改动清单 + 回归输出）写入 Sprint 文档 §9。

# 输出模板

```
# workspace-check 报告
- 工作区：<改动清单核对结果>
- 分支：<分支状态>
- 端口：<5173/8787/8501/8600 状态>
- 回归：<逐脚本 PASS/FAIL 摘要>
- 结论：<三查"三查"是否通过>
```

# 禁止

- 禁止批量按进程名杀进程；停止服务只用 PID + 命令行核对后的定点停止；
- 禁止跳过端口复查（停止任何 dev server 后必须复查 FREE）；
- 禁止把"命令输出看起来没报错"当 PASS：回归结论必须来自脚本自身的 PASS 输出或断言。
