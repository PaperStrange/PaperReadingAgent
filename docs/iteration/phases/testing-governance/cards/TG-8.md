# TG-8 **自举后端前端口自检 + 离线开关统一注入**（Retro 行动项 ② 升级为必修）：`verify/e2e_comm

- `card`: TG-8
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**计划中（Sprint-17，用户 2026-09-21 确认）**

## 规模
2

## 来源
**Retro 行动项 ②（Sprint-16）+ 用户 2026-09-21 确认进 S17**

## Sprint
Sprint-17（治理批 G1）

## 正文
`[用户插入]` **自举后端前端口自检 + 离线开关统一注入**（Retro 行动项 ② 升级为必修）：`verify/e2e_common.py` 的 `wait_healthy` **只探测端口、不校验"服务是不是自己启的"** → dev 后端在跑时脚本会**静默复用**它并施加 parse/embed 负载；反之套件也会抢占/顶掉 dev 后端（2026-09-20 走查实证：后端两次消失）。修法：① 自举前探测端口占用 → 占用即 **fail-fast** 并提示"请先停 dev 服务或改用其他端口"（**不复用**）；② 退出时只回收自己拉起的进程；③ 统一注入 `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1`（避免 HEAD 重试阻塞）；④ 回归：占用端口下脚本必须明确失败而非静默复用

## 证据
事故记录见 Sprint-16 §10 与验收指南 §13.5；教训 `3-LEARNED` 1.55 / 1.60

### 追加证据（2026-09-23，D3 复现：**本卡的另一面** —— 套件偶发假红）

**现象**：`verify/run_suite.py --tier offline` 偶发 `SUITE FAILED`，失败脚本在 `verify_agentops` 与 `verify_local_dir` 之间漂移。
- 另一会话实测（P3 期间）：4 连跑 **18/19**，`verify_agentops` 1 次 / `verify_local_dir` 3 次；
- 主代理实测（D3 收尾）：全序列 1 次 FAIL（`verify_local_dir`）→ 复跑 **2/2 PASS**；单跑 `verify_local_dir.py` **3 次中第 2 次 FAIL**。

**已排除**：两脚本源码**都不读** `docs/iteration/phases/**` ⇒ 与卡文档迁移（TG-14）无关；本轮未改这两个脚本。

**先前口径已更正**：另一会话曾判"只有全序列才失败 ⇒ 自举后端 kill/端口释放竞态"。主代理单跑复现出失败，
故该口径**过窄**——**单跑与全序列都会偶发失败**，至少两条原因并存：
1. **自举后端竞态**（本卡正文已覆盖：`wait_healthy` 只探端口、不校验归属）；
2. **`load_index` 步骤自身偶发异常**：单跑失败输出为
   `F-AC3 load_index 成功 FAIL: unhandled errors in a TaskGroup (1 sub-exception)`
   ——**根因未展开**（TaskGroup 子异常需进一步抓取），本卡落地时须一并查（否则离线开关/端口自检修好了，假红仍在）。

**落地要求（本卡追加）**：⑤ 修完后回归必须包含"**连跑 N 次全序列 + 单跑该脚本各 N 次**"两个口径（N≥5），
以"0 次假红"为验收；⑥ 若 ②（TaskGroup 子异常）确认与端口无关，则另立子项或并入本卡范围，**不得以"端口已修"结案**。

