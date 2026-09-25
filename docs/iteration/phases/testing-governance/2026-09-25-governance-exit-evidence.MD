# 治理模式退出条件——证据包（2026-09-25）

> 用途：Sprint-17 因 R1 在本 Sprint 触发 **5 次**（≥2）而**自动进入治理模式**（计划 §2.2.1 升级条款）。本文件把**四条退出判据**的**实测证据**集中在一处，供用户**二次确认**（规则要求）。
> 采集时间：**2026-09-25（UTC+8，网络时间核验 `HTTP Date` → 04:17）**｜被验状态：`windows` HEAD = **`d93c989`**（本地领先 `origin/windows` **38** 个提交）
> 判据来源：[`2026-09-25-d2d3-parallel-session-quality-analysis.MD`](2026-09-25-d2d3-parallel-session-quality-analysis.MD) §7「本会话提议的范围与退出判据」

---

## 判据 ① A-M12 工具约束交付 + 用 5 次真实 R1 输入复跑被拦

**机制**：`scripts/structure-guard.py`（`snapshot` → 编辑 → `verify`；只对"丢失/变形"报错）＋ 规则入 `docs/1-WORKFLOW.MD` §6（`snapshot→编辑→verify` 强制流程）＋ CI 步骤跑 `--replay` 自检。

**实测（`python scripts/structure-guard.py --replay`，rc=0）**：
```
R1-1 -> [FAIL] … backlog.MD:34 标题被删：## 2. 启动条件
R1-2 -> [FAIL] … 1-WORKFLOW.MD:348 锚点行被删：**卡片来源与时间口径（2026-09-20 用户要求，全部 backlog 适用）**…
R1-3 -> [FAIL] … sprint-17.md:94 表格列数变化：第 13 行 3 列 → 2 列（现 :106；表头 @:94）
R1-4 -> [FAIL] … sprint-15.md:132 表格块消失：表头 | # | 项 | 结果 |（基线 20 行 × 3 列）
R1-5 -> [FAIL] … 2026-09-25-d2d3-parallel-session-quality-analysis.MD:181 标题被删：## 8. 我接手的工作面
ALL PASS (64 assertions)
```
即：**5 次真实事故的输入逐条被拦下**（R1-1…R1-5 与 §7 记录一一对应）；另含 F2（表格追加/删行/改列/删标题）、H1（行首粗体锚点**就地改写**报 `[修改]` rc=0，删同一行必须 FAIL）、T1（表头/数据行就地改写）等反向对照，共 **64 断言**。

**真仓库无损失自证**（同一命令序列）：
```
SNAPSHOT OK → agents/runtime/doc-structure.json
STRUCTURE PASS（161 文件无丢失/变形；修改 0 项 / 新增 0 项）
```

**判定：达成。**

---

## 判据 ② 棘轮闭环（按文件设缺陷上限 + 到期日）

**机制**：`agents/policy.json::md_table_legacy_files.files` 由**路径列表**改为 **`{路径: 缺陷上限}`**，并加 `review_by`；闸门 `len(found) > cap` → FAIL。

**实测（`python verify/verify_md_tables.py`，rc=0）**：
```
棘轮基线：4 个文件（按文件设缺陷上限）；review_by=2026-10-31，今日=2026-09-25 → 未到期
棘轮基线（历史文件，上限内不判失败）：15 处，涉及 4 个文件
MD-TABLE PASS（161 个文件解析通过；其中 4 个历史文件走棘轮基线、均在各自的 defect 上限内）
```
**反向对照证据**（A2 批实测，`%TEMP%` 副本）：基线文件 +1 处**全新缺陷** → rc=1 点名（此前实现在此场景仍 rc=0，可吞 200 处新缺陷）；`review_by` 设为过去 → rc=1「棘轮基线已过期…必须重评基线」；非基线文件 +1 → rc=1（既有行为不回归）。

**判定：达成。**（15 处历史缺陷的**逐处清理**另开卡 `TG-18`，1 点、待排期——本判据只要求"棘轮咬得住 + 有到期日"。）

---

## 判据 ③ 7 处真缺陷修完（且扩集后先证明"恰在此处报错"）

**实测（`verify_md_tables.py`，rc=0）**：扫描集 **131 → 161**（"应扫=实扫 161 → 一致"），并对缺失项 fail-closed（政策↔文件系统**双向差集**）。

7 处逐条修法：`a-m11-from-runs.MD:102` 单元格裸管道转义｜同文件 `:178` 行内代码首个管道补转义｜`agents-infra/architecture.MD:251` `task=branch:windows\|main`｜`tg11-retro.MD:42/:43` 实为**表头 4 格 vs 数据行 3 格列错位**→拆分 M1~M4 四行｜`search-only-draft.MD:62/:79` 裸管道转义。修前该批在**这 7 行逐条报错**（证据见 A10 批报告），修后全绿。

**判定：达成。**

---

## 判据 ④ 反向对照全绿（含"断言在目标环境为真"）

> **读表约定（2026-09-25 一查 `run-2026-09-25-doc-audit-070` finding 2 后改）**：断言数**不是**本表的证据——它是**必然漂移的派生数字**（同一批闸门在同日 4 份文档里并存 3~4 个读数，无一与工具一致）。本表的证据 = **命令可跑 + 判据存在 + 反向对照有牙**；`<N>` 处一律**现跑该命令、以末行 `ALL PASS (N assertions)` 或 `EVIDENCE:` 行为准**。写成具体数字的地方只是**该时点读数**，不构成现值主张。

| 闸门 | 实测输出（`<N>` = 现跑为准） |
|---|---|
| `verify_close_readiness.py` | `ALL PASS (<N> assertions)`（自检档；该档随判据增加而增，**本表不写现值**） |
| `verify_no_policy_hardcode.py` | `ALL PASS (<N> assertions)`（另打印扫描覆盖的 `.py` 个数；**应扫=实扫**必须一致，否则它就是死配置） |
| `verify_ledger_measurement.py` | `ALL PASS (<N> assertions)`（TG-13 新闸门：双向目录/时间戳退化/rounds 对报告/终态写回 + 4 类反向对照） |
| `verify_artifact_paths.py` | `ALL PASS (<N> assertions)` + 动态目标分布行（按文件设上限，`review_by` 到期重评） |
| `verify_agentops.py` | `ALL PASS (<N> assertions)` |
| `verify_lint.py` | `ALL PASS (<N> assertions)` + `EVIDENCE:` 行（含四类 C 级棘轮现值/上限） |
| `verify_card_index.py --check --strict` | `ALL PASS (<N> assertions)`（含状态三处一致 + 卡库存基线一致两条新判据） |
| **整档套件** | **`SUITE PASSED (<N> scripts)`**（`status=ok`，零失败；脚本数现跑为准） |
| 矩阵 SSOT | `CHECK OK: <N> 脚本与 TEST-MATRIX.MD 一致`（现跑为准） |

**其中"环境无关"这一条有实证**：`verify_local_dir.py` 在**没有** `PYTHONUTF8=1` 的本机 shell 里曾 `SUITE FAILED (1/21)`——根因是子进程经管道以 GBK 写、父进程按 UTF-8 解码 → 中文提示变 mojibake + `U+FFFD` 触发 `UnicodeEncodeError`（**断言只在特定环境为真** = 审计 R3 类）。修法：父进程 stdout 显式 UTF-8+容错、子进程注入 `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`；修后 `verify_local_dir` 7 断言 PASS、套件 21/21 PASSED（本机默认环境）。

**判定：达成。**

---

## 如何自行复核（逐条命令，约 6 分钟）

```powershell
$py = "D:\All-Downloads\PaperReading\PaperReading-Windows\.venv\Scripts\python.exe"
cd D:\All-Downloads\PaperReading\PaperReading-Windows
& $py scripts\structure-guard.py --replay          # 判据①：5 类 R1 逐条 FAIL（断言数以末行为准）
& $py verify\verify_md_tables.py                   # 判据②③：棘轮上限 + 应扫=实扫（文件数现跑为准）
& $py verify\run_suite.py --tier offline           # 判据④：SUITE PASSED (N scripts)
& $py verify\verify_matrix.py check                # N 脚本一致
git -C . log --oneline -1 ; git rev-list --count origin/windows..HEAD
```

---

## 限制与未闭环（不影响判据，但你应当知道）

1. **CI 从未实跑**：本批 38 个提交**全部未推**（按你 P-a 的暂存分支方案）；因此"断言在 CI 同款环境跑过"这半条**仍未满足** → `§9.2` 已写死：退出后推 `windows` 触发的 CI **必须当真实关口**（红即修，不得以"本机绿"替代）。
2. `close_readiness` 的**真数据模式**今日仍 `FAIL`（Sprint-17 的三查锚点尚未声明，属关闭期动作）；其"绿"= 自检档 `ALL PASS (<N>)` + 0 份文档受检。**注（2026-09-25 稍后）**：同日晚些的 B1~B4 + D0 批已把真数据项从 13 降到 1（剩 `[C3]` 未归属提交），本条的"仍 FAIL"结论不变、**条数已变**——现值现跑 `verify\verify_close_readiness.py --sprint docs\iteration\sprint\2026-09-21-sprint-17.md`。
3. `A-M12` 判据④（下 Sprint 同族事故 ≤1 次）是**度量项**，只能 Sprint-18 测。
4. `TG-15` 的 2.5 点**扣分条件**：棘轮已闭环 → 不扣；待 C 批（`TG-6` 可读性棘轮）完成后我给出最终算式。
5. 实现类子代理**没有账本 role**（登记会污染 C1 判定域）→ 归 `TG-17` 输入；这也是本证据包里的机制批**没有 run id** 的原因（不是漏记）。

---

## 请你确认

回复 **`退出确认`** 即视为认可上述四条判据达成；随后我按序执行：**D** 关闭三查 + §9 结构化 run 表与三查锚点 + Retro（含 `run-2026-09-25-code-review-068` 这类补登记行）→ **E** 推 `windows`（CI 当真实关口）并回收 `park/sprint-17-pre-governance-2026-09-25` → **F** `TG-15` 点数结算。若你认为哪条证据不足，指出即可，我不会自行结案。

---

## ✅ 用户退出确认（2026-09-25，UTC+8）

**用户原话**："退出确认，注意还没实现的目标 比如 CI 未实跑的影响，继续吧"

**据此生效**：治理模式**退出**（Sprint-17 解除"停功能推进"冻结，剩余治理卡照常推进；`F-AC13/14` 仍按 P-d=4 冻结、不承诺挪期）。
**用户同时点名的"未实现目标"（必须一直带到 E 步，不得淡出）**：
1. **CI 从未实跑** → 本批 39 个提交的"断言在 CI 同款环境跑过"这半条**仍未满足**；E 步推送时 CI **必须当真实关口**：红即修、**不得以"本机绿"替代**，CI 结论与 head sha 需回填 §9 与 §9.2 回收行。
2. `close_readiness` **真数据模式**仍 FAIL（三查锚点属关闭期动作，D 步填写后才首次真正受检）。
3. `A-M12` 判据④（下 Sprint 同族事故 ≤1 次）只能 Sprint-18 测。
4. **实现类子代理无账本 role** → 机制批无 run id 是结构性缺口（归 `TG-17`），不是漏记。
5. `TG-15` 2.5 点的**扣分条件**结算在 F 步给出算式（棘轮已闭环 → 不扣该项）。

**E 步推送前的预检清单（CI 等价物，全部本机先跑一遍）**：`requirements-windows.txt` 含 `ruff==0.14.4`（CI 自动获得）→ `verify/run_suite.py --tier offline`（21 脚本）→ `verify/verify_matrix.py check`（52）→ CI 显式档四条（`verify_card_index.py --check --strict`、`verify_md_tables.py`、`verify_no_policy_hardcode.py`、`verify_lint.py`）→ `scripts/structure-guard.py --replay`（64）+ close-readiness 的"仅对声明真锚点的 Sprint 文档"分支（Sprint-17 填锚点后首次受检）→ 两个前端 `npm ci` + build（本批未触前端源码，预期不受影响）。
