# Sprint-16 用户验收指南（数据准确性 + 成本韧性 + 调研工作流深化）

> **验收对象**：Sprint-16 四卡 / 19 点（M16 6 + F-AC8 6 + F-AC10 4 + TG-5 3）
> **依据**：`docs/iteration/sprint/2026-09-12-sprint-16.md` §2（验收标准）、§2.1（验收 case）、§7（证据）
> **走查日**：**2026-09-20**（UTC+8，取网络时间校准）。Sprint 时间盒为 09-12 ~ 09-15，走查顺延 5 天，作为过程事实记录。
> **状态**：**待人工走查**。规则：**用户验收通过前不创建 PR**（`docs/1-WORKFLOW.MD` §3.4）。
> **前端本轮零改动**（〇查确认），因此交互验收只有"回归不坏"；新能力集中在 **CLI / API / 产出文件**，多数项不需要启动服务。

---

## 本指南怎么用

1. **§5** 一次跑完 7 条零成本证据（约 3~5 分钟）→ 覆盖四卡自动证据主体；
2. **§6** 逐卡对着"通过判据"过一遍（多数只需看文件或看 §5 输出，不必再执行）；
3. **§7** 是这轮最该盯的 **fail-closed 边界行为**（16 条）——数据准确性与成本韧性的真正判据在这里；
4. **§8** GUI 回归 4 项（要起前后端，可选）；**§9** 联网/花钱项（可选，不影响结论）；
5. **§10** 已知局限与未纳入本轮的项（含 1 条需你拍板的小项）；
6. **§12** 把结论逐条回传即可（PASS/FAIL + 备注），无需分析原因。

---

## 一、这轮验收真正要判断的三件事

| 维度 | 通过判据（一句话） | 反例（出现即不通过） |
|---|---|---|
| **数据准确性** | provider 配置**一 provider 一文件**、生效来源可溯（file/legacy/env）、刷新失败**不写坏文件** | 改了 `providers/dashscope.json` 但生效值仍来自别处；抓取失败却写了半截文件 |
| **成本韧性** | embedding **逐篇落盘**、重跑**只补缺口**、预算**未测量即不放行** | 重跑 `reused=0` 全量重嵌入（白花钱）；`unknown` 被当"没超预算"放行 |
| **调研工作流** | 归档含**逐字证据**、缺件**必判 FAIL**、三级深度阈值**可配** | 报告结论在 `evidence/` 里查不到原文；删掉证据文件门禁仍 PASS |

---

## 二、你已拍板的两处口径（本指南按此验收，不再重复讨论）

| # | 口径 | 落地位置（可核对） | 判定 |
|---|---|---|---|
| ① | F-AC8 的"定期刷新" = **14 天 due 判定**；系统任务计划**可选、不自动注册**（触发权在用户/调度器） | `scripts/scheduled-tasks.py` → `TASKS["providers"]["interval_days"] = 14`；`scripts/register-scheduled-tasks.ps1` 需人工执行 | ☐ |
| ② | TG-5 夜间套件 = **周频 + 单次 ¥10 上限**（可配）+ fail-closed + **不进 CI**（CI 只跑 offline 档） | `TASKS["nightly-suite"]["interval_days"] = 7`；`PAPERQA_NIGHTLY_BUDGET_CNY` 默认 10；`.github/workflows/ci.yml` 只调用 `run_suite.py --tier offline` | ☐ |

其余既定口径（本轮一并核对，见 §6）：**改配置即生效、不写死常量**；**offline 档必须无密钥可跑**；**成本未测量 ≠ 未超预算**。

---

## 三、前置准备

### 3.1 环境

```powershell
# 每次新开终端都要做的事
cd D:\All-Downloads\PaperReading\PaperReading-Windows
$env:PYTHONIOENCODING='utf-8'      # 中文输出不乱码
```

- Python 一律用仓库虚拟环境：`.\.venv\Scripts\python.exe`
- **§5 / §6 / §7 / §9 不需要启动任何服务**（verify 脚本自带被测环境）
- 只有 **§8 GUI 回归** 需要起前后端

### 3.2 会直接影响你判断的 4 个坑（先看，避免误判 FAIL）

| 现象 | 真实原因 | 处理 |
|---|---|---|
| HF 模型加载卡住 / `/api/health` 无响应 / Playwright 超时 | 联网校验 HuggingFace 不可达（3-LEARNED 1.55） | 起服务前设 `$env:HF_HUB_OFFLINE=1` |
| `WinError 10048` 端口占用 | network 档脚本会自举后端，与 dev server 抢 8787 | 先停 dev 服务，或只跑 `--tier offline` |
| 退出码 1（`refresh-providers.py --check`） | **1 = 有到期项**，是信号不是失败 | 见 §6 `PV-4`；退出 2 才是参数/环境错误 |
| 退出码 3 / 4（`run_suite.py` / `scheduled-tasks.py`） | **3 = 超预算拒绝启动；4 = 成本未测量/超限拒绝放行** | 这是**设计行为**，见 §7 `B-8` / `B-9` |
| 后端跑着跑着没了 / 8787 被别的进程占住 | ① 后端若用**会话托管作业**启动，包装器退出会带走子进程；② **套件脚本（含 offline 档）会使用 8787**：`verify/e2e_common.wait_healthy` 只探测端口、**不校验"响应的服务是不是自己启的"** → 已存在的 dev 后端会被静默复用/顶替（2026-09-20 走查实证：后端两次消失） | 走查期间**不要跑** §5 第 7 条（`run_suite.py --tier offline`）；跑套件前先停 dev 服务、跑完确认无残留进程。本次走查的后端以**独立进程**启动（`Start-Process`，不挂作业树；listener PID 记在 §3.3），若需重启：设 `HF_HUB_OFFLINE=1` 后用 `Start-Process` 拉起 `paper-qa-script\reactflow-paperqa-prototype\backend\main.py`，再验 `/api/health` |

### 3.3 状态文件与产物（都是 gitignore 的本地运行时状态，可安全删除重跑）

| 路径 | 作用 |
|---|---|
| `agents/runtime/schedule.json` | 定时任务 `last_run` / 成本状态（**当前不存在** = 从未真实运行过，见 §6 `TG-4`） |
| `agents/runtime/provider_refresh_status.json` | 首轮 provider 调研结论（4 家 verdict） |
| `agents/runtime/provider_refresh_proposal.json` | 待人工确认的字段变更提案 |
| `agents/runs/run-2026-09-12-provider-refresh-001/` | M16 首跑归档（报告 + context + reasoning + `evidence/01..08`） |
| `verify/backend-dev.log` / `verify/backend-dev.err.log` | 本次走查 dev 后端的 stdout/stderr（`verify/*.log` 已 gitignore）；后端以独立进程运行，listener PID = **21900**（父进程 7196） |

---

## 四、验收点位编号（本文档全篇用这套编号）

| 卡 | 验收标准 | 边界专项 | 点数 |
|---|---|---|---|
| M16 调研工作流 v2.0 | `M16-1` ~ `M16-5` | `B-14`、`B-14b`、`B-15` | 6 |
| F-AC10 文献级 checkpoint | `CK-1` ~ `CK-4` | `B-1` ~ `B-6` | 4 |
| TG-5 分层 runner + 定时底座 | `TG-1` ~ `TG-5` | `B-7` ~ `B-10` | 3 |
| F-AC8 provider 一文件 + 定时调研 | `PV-1` ~ `PV-5` | `B-11` ~ `B-13` | 6 |
| GUI 回归 | `G-1` ~ `G-4` | — | — |
| 联网/花钱项（可选） | `N-1` ~ `N-4` | — | — |

---

## 五、零成本自动证据（建议第一步；2026-09-20 现场复跑）

> 全部命令在仓库根目录执行；**不调用付费模型、0 成本**（第 7 条是纯本地套件，走 st- 本地向量）。若你的网络到 HuggingFace 不通、本地模型加载变慢，先 `$env:HF_HUB_OFFLINE='1'` 再跑第 7 条。
> **走查前主代理已按本表预跑一遍**（含 GUI 与边界演示），完整原始输出在 `verify/acceptance-sprint16-2026-09-20.log`（gitignore，本地留证）；下表的"09-20 实测"就是它的结论，你可以直接抽查复跑。

| # | 命令 | 期望输出（判据） | 09-20 实测 |
|---|---|---|---|
| 1 | `.\.venv\Scripts\python.exe .\verify\verify_providers.py` | `ALL PASS (33 assertions)`，退出 0 | ✅ 33/33 |
| 2 | `.\.venv\Scripts\python.exe .\verify\verify_runner.py` | `ALL PASS (26 assertions)`，退出 0（20 原有 + TG-7 三例 + Retro③ 两例 + …） | ✅ 26/26 |
| 3 | `.\.venv\Scripts\python.exe .\verify\verify_archive.py agents\runs\run-2026-09-12-provider-refresh-001 --depth expert` | `=== ALL PASS: 28 passed / 0 failed ===`（含**双向**交叉引用断言） | ✅ 28/28 |
| 4 | `.\.venv\Scripts\python.exe .\verify\verify_archive.py --selftest` | `=== selftest PASS: 8 passed / 0 failed ===`（合规 expert/scholar 通过 + 空报告被拒 + **被引用证据缺失被拒** + **正文提及别处证据名不误判** + **索引表 `.markdown` 漏报被拦** + **已存在 `.markdown` 不假红** + **嵌套子目录不假红**） | ✅ 8/8 |
| 5 | `.\.venv\Scripts\python.exe .\verify\verify_matrix.py check` | `CHECK OK: 44 脚本与 TEST-MATRIX.MD 一致` | ✅ 44 脚本（走查期依次加入 `verify_usage.py`/`verify_checkpoint_index.py`/`verify_freshness.py`/`gui_check_fac16_checkpoint.mjs`，40→41→44） |
| 6 | `foreach ($f in Get-ChildItem agents\functions\*.md) { .\.venv\Scripts\python.exe .\scripts\agent-ops.py validate-spec $f.FullName }` | 8 个 spec 全 PASS | ✅ 8/8 |
| 7 | `.\.venv\Scripts\python.exe .\verify\run_suite.py --tier offline` | `SUITE PASSED (11 scripts)`，退出 0（fail-closed；含 `verify_usage.py`） | ✅ 11/11（见 §5.1） |
| 8 | `.\.venv\Scripts\python.exe .\verify\verify_usage.py` | `ALL PASS (21 assertions)`（Retro③ 用量采集与成本换算口径） | ✅ 21/21 |

### 5.1 第 7 条的复跑记录（2026-09-20 现场）

**档位构成**（`run_suite.py --tier offline --dry-run`，零成本）：

```
== run_suite tier=offline scripts=10 est_cost=0.0 CNY budget=10.0 CNY ==
  - verify_agentops.py (est 10s / 0 CNY)
  - verify_archive.py (est 5s / 0 CNY)
  - verify_config_schema.py (est 5s / 0 CNY)
  - verify_f12_preview_res.py (est 10s / 0 CNY)
  - verify_index_health.py (est 20s / 0 CNY)
  - verify_local_dir.py (est 90s / 0 CNY)
  - verify_providers.py (est 20s / 0 CNY)
  - verify_prune_callbacks.py (est 2s / 0 CNY)
  - verify_runner.py (est 60s / 0 CNY)
  - verify_smoke.py (est 10s / 0 CNY)
DRY-RUN: 未执行任何脚本。
```

**实跑尾部**（`run_suite.py --tier offline`，`suite_exit=0`）：

```
--- verify_runner.py: exit=0 (1.32s) ---
--- verify_smoke.py: exit=0 (12.59s) ---
=== 8/8 checks passed ===

SUITE PASSED (10 scripts)
```

> 套件全程 `est_cost=0`（无付费调用；`verify_local_dir.py` 走 st- 本地向量 + CSV manifest 提供 citation，故无需密钥）；**fail-closed**：任一脚本失败即整体非零（见 §7 `B-7`）。
>
> **修复后复跑（同日，三轮）**：`verify_archive.py` 补反向交叉引用 → 按独立复核收紧（判定限定证据索引表区间 + 大小写不敏感）→ 再按 round-2 统一两侧口径（`.md`/`.markdown` + 嵌套目录）。真实归档 `ALL PASS: 28 passed / 0 failed`、`--selftest` `8 passed / 0 failed`、原漏检变体 `FAILED 25/1`、`run_suite.py --tier offline` **`SUITE PASSED (11 scripts)`**（完整输出见预跑日志 `verify/acceptance-sprint16-2026-09-20.log`）。
>
> **注**：上表"档位构成"是加入 `verify_usage.py` **之前**的读数（10 脚本）；现行 offline 档为 **11 脚本**（新增 Retro③ 计量回归），用 `run_suite.py --tier offline --dry-run` 可复核。

> 说明：`verify_checkpoint.py`（33 断言）**不在 offline 档**——其 parse 链路含真实 LLM 调用，分级为 network 档（估算 ¥0.05），见 §9 `N-1`。

---

## 六、逐卡验收详表（19 个判定格）

### 6.1 M16 调研工作流深化 v2.0（6 点）

**验收标准（§2 原文）**：① spec v2.0 含三级阈值与归档规则（阈值可配置）；② `fanout.json` depth 路由；③ `verify_archive.py` 对缺件/空证据判 FAIL；④ 首跑演示归档完整；⑤ 工程级由主代理直执（P2）。

| 编号 | 怎么验 | 通过判据 | 证据 | 判定 |
|---|---|---|---|---|
| `M16-1` | 看 `agents/functions/tech-research.md`：版本号 + 三级深度表 + Archive Requirements + 可配置参数节 | 版本 **v2.0.0**；`quick` 3~5 源/1 维/**主代理直执**、`expert` 6~10 源/≥3 维/子代理（默认）、`scholar` ≥12 源+反向证据；阈值全部落在**可配置参数节**（非硬编码） | spec 文件本身 | ☐ |
| `M16-2` | 看 `agents/fanout.json` | 版本 **v5**；`planning_pipeline` 含 `depth` 路由 + `archive` 门禁字段；`executor` 按深度分流（subagent / main-agent） | fanout.json | ☐ |
| `M16-3` | §5 第 3、4 条 | 真实归档 **28/28** PASS；`--selftest` **八例**（合规 expert/scholar + 空报告被拒 + 被引用证据缺失被拒 + 正文提及不误判 + `.markdown` 漏报被拦 + 已存在 `.markdown` 不假红 + 嵌套子目录不假红）；交叉引用为**双向**（点名 + 落地），判定**限定在证据索引表区间内**、文件名大小写不敏感、`.md`/`.markdown` 与嵌套目录口径两侧一致 | `verify_archive.py` | ☐ |
| `M16-4` | 打开 `agents/runs/run-2026-09-12-provider-refresh-001/` | 四件齐备：`tech-research.report.md`、`context.md`、`reasoning.md`、`evidence/01..08-*.md`；报告含 **§7 证据索引表**；每个 evidence 文件含五字段（`url`/`tier`/`fetched_at`/`fetch_status`/`supports`）+ **verbatim 原文引用块** | 该归档目录 | ☐ |
| `M16-5` | 看报告 §7 → 任选一行 → 打开对应 evidence 文件 | 能"引经据典"逐字回溯：例如 report 里 `qwen3.5-omni-plus` 的结论可定位到 `evidence/02-help-aliyun-com-zh-model-studio-models.md` 的 verbatim 段（阿里云『图像与视频理解』列表） | 报告 + evidence | ☐ |

### 6.2 F-AC10 文献级 embedding checkpoint（4 点）

**验收标准（§2 原文）**：① 正常链路逐篇落盘、全部就绪才标 `ready`；② 中断续跑只补缺口（embedding 调用计数断言）；③ 指纹/模型不匹配判重跑；④ 与 `embed_mode=load` 缓存语义衔接。

| 编号 | 怎么验 | 通过判据 | 证据 | 判定 |
|---|---|---|---|---|
| `CK-1` | 看 `paper-qa-script/app/orchestration.py` 的 checkpoint 子系统；或 §9 `N-1` 跑一次 | manifest + 载荷按 **命名空间** `sha1(论文目录\|索引名\|嵌入模型)[:16]` 落盘；逐篇 `_atomic_write_json`（tmp + `os.replace`）；**全部走完才置 `ready`**，单篇失败先写 `status=error` 再抛出 | `verify_checkpoint.py` 断言 ①、⑤ | ☐ |
| `CK-2` | §9 `N-1`（真实重跑） | 输出 `checkpoint{reused=2, embedded=0}`（**零嵌入成本**），`texts_count` 与首跑一致 → 只补缺口 | `verify_checkpoint.py` 断言 ② | ☐ |
| `CK-3` | §7 `B-3`、`B-5` | 文件指纹（`size:mtime_ns`）或模型名变化 → 判需重跑；manifest 自述 `checkpoint_key`（防"假绿"） | 断言 ③、⑤、⑦b | ☐ |
| `CK-4` | 看 `app/engine.py` 的 `export_doc` / `restore_doc` + 复用判定条件 | 复用需同时满足：`status=ready` + 指纹一致 + **`chunk_chars`/`chunk_overlap` 一致** + 载荷可读 + 还原成功；还原走 `Text(doc=doc, **raw)`（paperqa 类型不出 engine 层） | 断言 ④、⑦b | ☐ |

### 6.3 TG-5 分层 runner + 定时底座（3 点）

**验收标准（§2 原文）**：① offline 层全绿退出 0；② 注入失败脚本 → 非零（fail-closed）；③ 预算上限 env/配置可调且超限拒跑；④ due 判定到期执行、未到期跳过并写 `last_run`；⑤ 周频夜间套件配置化。

| 编号 | 怎么验 | 通过判据 | 证据 | 判定 |
|---|---|---|---|---|
| `TG-1` | §5 第 7 条；另可用 `run_suite.py --tier network --dry-run` **零成本**看 network 档构成与预估花费 | `SUITE PASSED`，退出 0，**13 个 offline 脚本**全绿；`--tier gui\|network` 同样按 `VERIFY_META.tier` 分层（44 脚本 SSOT 见 `verify/README.md`） | `run_suite.py` | ☐ |
| `TG-2` | §7 `B-7` | 任一脚本失败 → **整体非零**（不"部分通过"） | `verify_runner.py` 断言 ② | ☐ |
| `TG-3` | §7 `B-8` / `B-9` + 看优先级 | 上限优先级 **CLI > env `PAPERQA_NIGHTLY_BUDGET_CNY` > 配置默认 10**；改 env 即生效 | 断言 ③、④ | ☐ |
| `TG-4` | `.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --list` | 三任务与间隔：`prices` 7 天、`nightly-suite` 7 天、`providers` **14 天**；`due` 判定与上次运行可见（当前状态文件不存在 → 显示"从未运行"） | 实测输出见 §6.3 附 | ☐ |
| `TG-5` | 看 `TASKS` 定义 + `scripts/register-scheduled-tasks.ps1` | 间隔/预算均可 env/state 覆盖（`PAPERQA_SCHEDULE_<TASK>_DAYS`、`PAPERQA_NIGHTLY_BUDGET_CNY`）；任务计划注册脚本**需人工执行**（口径 ①） | 脚本本身 | ☐ |

**§6.3 附：`--list` 实测输出（2026-09-20）**

```
state: D:\All-Downloads\PaperReading\PaperReading-Windows\agents\runtime\schedule.json
budget_cny: 10.0
  nightly-suite  间隔    7 天 | 上次 从未 | 花费 - | due=True（从未运行）| 夜间全量联网套件（fail-closed，受预算上限约束）
  prices         间隔    7 天 | 上次 从未 | 花费 - | due=True（从未运行）| 价表抓取（M9，官网固定 URL）
  providers      间隔   14 天 | 上次 从未 | 花费 - | due=True（从未运行）| provider 官网调研刷新（F-AC8：抓取 + M16 归档 + proposal；模型名变更需人工确认）
```

### 6.4 F-AC8 provider 一文件 + 官网调研刷新（6 点）

**验收标准（§2 原文）**：① 切 provider 只加载对应文件（输出与文件一致）；② 旧 `providers.json` 合并/迁移语义不回归；③ 官网调研更新一次（M16 归档结构）+ `fetched_at`/`source_urls` 记录；④ 两周 due 判定正确；⑤ 官网不可达 → 保留旧文件 + 状态记录。

| 编号 | 怎么验 | 通过判据 | 证据 | 判定 |
|---|---|---|---|---|
| `PV-1` | 看 `paper-qa-script/providers/{deepseek,dashscope,openai,openrouter}.json`（**4 个文件**，`name` = 文件名）；§8 `G-2` 看下拉联动 | 运行配置与文件逐字段一致；`provider_source()` 标记来源 = `file`；加载顺序 **代码兜底 < `providers/*.json` < 旧 `providers.json` < env `PAPERQA_PROVIDERS_JSON`** | `verify_providers.py` 断言 ①②③ | ☐ |
| `PV-2` | §7 `B-12`、`B-13`；看仓库已无 `paper-qa-script/providers.json`（已迁移） | 旧文件语义仍被支持（优先级层）+ `--migrate` 可拆解；非法文件只跳过并给原因；未知 provider → `ValueError` 列可选值 | 断言 ④⑤⑦ | ☐ |
| `PV-3` | 看 `providers/dashscope.json` 的 `meta` + `agents/runtime/provider_refresh_status.json` | `meta.source_urls`、`fetched_at`、`last_refresh_status`、`refresh_notes` 齐备；首轮 4 家 verdict：dashscope embedding `no_change`（**澄清 F2 台账『注释失实』一说**）、deepseek model/embedding `no_change`、openrouter model `needs_review`（现值保留）、openai `error`（403）。**时序说明（不算不一致）**：status JSON 里 dashscope model 仍写 `current=openai/qwen-omni-turbo` + `needs_review`——那是首轮判定当时的值；你随后拍板改为 `openai/qwen3.5-omni-plus`，决策依据留在 `dashscope.json` 的 `refresh_notes` 第 3 条 | 文件 + status | ☐ |
| `PV-4` | `.\.venv\Scripts\python.exe .\scripts\refresh-providers.py --check` | 已刷新者未到期、**从未成功者判 due**；**退出码 1 = 有到期项（信号）**，退出 2 = 参数/环境错误 | 实测输出见 §6.4 附 | ☐ |
| `PV-5` | §7 `B-11` | 抓取失败 → **provider 文件逐字节未变** + `last_refresh_status=error` 记录；不写坏文件 | 断言 ⑩ | ☐ |

**§6.4 附：`--check` 实测输出（2026-09-20，间隔 14 天）**

```
providers: 4（间隔 14 天）
  dashscope    due=False  未到期（剩 6.11 天）
  deepseek     due=False  未到期（剩 6.11 天）
  openai       due=True  无 fetched_at 记录
  openrouter   due=False  未到期（剩 6.11 天）
```

> 读法：4 家里 3 家在 09-12 首轮刷新成功 → 未到期（剩约 6 天）；`openai` 官网 403 → `fetched_at: null` → **判 due**（口径：从未成功刷新者应尽快重试）。这正是 `PV-4` 要看的两种分支。

---

## 七、边界与 fail-closed 专项（16 条，本轮最该盯的部分）

> 多数边界已固化在 verify 脚本里；下表给出**人工可复现的触发方式**与**期望的"拒绝/退让"行为**。

| 编号 | 场景 | 触发方式（零成本可复现） | 期望行为（判据） | 覆盖证据 | 判定 |
|---|---|---|---|---|---|
| `B-1` | checkpoint 正常链路 | `N-1` 或看断言 ① | 逐篇落盘，全部就绪才 `ready` | checkpoint ① | ☐ |
| `B-2` | checkpoint 断点续跑 | `N-1`（重跑，首跑档案已在） | `reused=2 / embedded=0`（零嵌入成本） | checkpoint ② | ☐ |
| `B-3` | 文件变更 / 模型不匹配 | `verify_checkpoint.py`（§9 `N-1`，¥0.05）自动注入：touch mtime / 篡改 manifest | 仅受影响篇重跑；模型不匹配 → **全部重跑**（fail-closed） | checkpoint ③⑤ | ☐ |
| `B-4` | 载荷损坏 | `verify_checkpoint.py` 自动注入：截断 `.json.gz` | 该篇重跑，另一篇仍复用；**manifest 自述 `checkpoint_key`** 防假绿 | checkpoint ④ | ☐ |
| `B-5` | 切块口径变更 | `verify_checkpoint.py` 自动注入：改 `chunk_chars`/`chunk_overlap` | **不复用旧分块**，全部重跑 | checkpoint ⑦b | ☐ |
| `B-6` | 同内容文件 | `verify_checkpoint.py` 自动注入：放入同内容文件 | 记 `deduped`，**不算失败**（paperqa 按 content_hash 去重） | checkpoint ⑥ | ☐ |
| `B-7` | 套件中有脚本失败 | `verify_runner.py`（§5 第 2 条，**0 成本**）注入失败脚本 | 整体**退出非 0**（fail-closed，不"部分通过"） | runner ② | ☐ |
| `B-8` | 预算超限 | `.\.venv\Scripts\python.exe .\verify\run_suite.py --tier network --budget-cny 0.01` | **拒绝启动**、退出 **3**、明确文案、**不执行任何脚本**（闸门在启动前判定，故该命令 **0 成本**可复现） | runner ③ | ☐ |
| `B-9` | 成本未测量 / 超限 | **零成本安全复现**（临时状态文件 + `--dry-run`；`last_run` 取 8 天前以便"到期"）：见 §13.4 命令 | **拒绝放行、退出 4**；记录 `last_blocked_at/reason`；`--record-cost` 回填或 `--force` 可解除；`unknown` + 上轮失败 → **自愈放行** | runner ⑦⑧⑨b⑨c | ☐ |
| `B-10` | **定时任务**未到期 / 已到期（prices / providers / nightly-suite 按 `interval_days` 判定；**与"provider 模型或服务到期"无关**） | 见 §13.4 命令（未到期 / 到期两例） | 未到期 → `SKIP` 且**不动状态**；已到期 → 执行并**原子写** `schedule.json` 的 `last_run` | runner ⑤⑥ | ☐ |
| `B-11` | 官网不可达 | 看 `provider_refresh_status.json` 的 `openai`（403） | **旧文件逐字节保留** + 状态记 `error`；不写坏文件 | providers ⑩ | ☐ |
| `B-12` | 非法 provider 文件 | `verify_providers.py`（§5 第 1 条，**0 成本**）自动注入：坏 JSON / 缺 model / name 不符 | 只跳过该文件并**给出原因**，其余 provider 照常可用 | providers ④ | ☐ |
| `B-13` | 未知 provider | `verify_providers.py` 自动 | `ValueError` 并列出可选值（含自定义来源提示） | providers ⑦ | ☐ |
| `B-14` | 归档缺件 / **悬空引用** | **已预置负例样本**（走查前预跑生成）：`agents\runs\_acceptance-scratch-2026-09-20\archive-missing-evidence`（= 首跑归档副本，删掉了被报告 §7 引用的 `evidence/06-*.md`）→ 直接跑 `.\.venv\Scripts\python.exe .\verify\verify_archive.py .\agents\runs\_acceptance-scratch-2026-09-20\archive-missing-evidence --depth expert` | **判 FAIL 并指明缺件**：`FAIL: 索引表点名的 evidence 文件全部存在 dangling=['06-platform-openai-com-docs-guides-embeddings.md']`，退出 1。同类负例 `e-dangling-reference`（报告引用不存在的文件名）。⚠ **该格 09-20 预跑曾误判 PASS（缺陷），已修并复核收紧**，见 §10.A | 走查修复 + `--selftest` 第 4 例 | ☐ |
| `B-14b` | 防**误报**（合规归档不该被冤枉） | 复核冻结的反例集：`.\.venv\Scripts\python.exe .\verify\verify_archive.py .\agents\runs\run-2026-09-20-code-review-053\counterexample\C2-prose-mention --depth expert`（C3 跨 run 路径 / C4 URL 片段同理） | **应 PASS（`28/0`）**：正文顺带提及别处的证据文件名不算悬空引用（修复前误判 `27/1`） | 复核 run-053 major#1 + `--selftest` 第 5 例 | ☐ |
| `B-15` | 深度阈值可配 | 换 `--depth quick`（quick 档豁免 evidence 门禁）/ `expert` | 判据随深度变化，**阈值不写死** | archive `--depth` | ☐ |

---

## 八、GUI 回归（4 项，需启动前后端；本轮前端零改动）

### 8.1 启动（两个终端）

```powershell
# 终端 1：后端（注意 HF 离线开关，见 §3.2）
$env:HF_HUB_OFFLINE='1'
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1     # 端口 8787

# 终端 2：前端
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1    # 端口 5173
```

浏览器打开 http://127.0.0.1:5173 （页面打不开时先访问 http://127.0.0.1:8787/api/health 看后端是否存活）

> **缓存口径（实测）**：Vite dev server 对 HTML 与模块发 `Cache-Control: no-cache` + `ETag`，`/api/*` 不带头（无启发式新鲜度）→ **普通刷新即可，无需硬刷新或清缓存**。若服务在走查前被重启过，**停服前开着的旧标签页必须重载一次**（否则连的是已死的旧实例）；想一步排除"旧标签页 + 缓存"两个变量，直接 **Ctrl+Shift+N 无痕窗口**打开。provider 带出的模型名由后端实时现读 `providers/*.json`，改配置不需要重启后端。

| 编号 | 操作 | 通过判据 | 判定 |
|---|---|---|---|
| `G-1` | `node .\verify\gui_check_s4.mjs` | **光标三断言**（中部插入 / 插入后光标位置 232 / 连续编辑）+ **provider 联动四断言**（下拉四项含 `openrouter` / 切 `openrouter` 带出 `api_base`+`model` 且**不写** `embedding_model` / 切 `deepseek` 同上 / 自动提示含"多语言"）逐行均 PASS | ☐ |
| `G-2` | `node .\verify\gui_check_config_schema.mjs` | `US-13.1 defaults-derived-from-schema: PASS`（表单默认值全部由 schema 派生，无手写字面量） | ☐ |

> 09-20 预跑截图（可直接打开看，无需重跑）：`verify/gui_check_s4.png`、`verify/f2-schema-form.png`、`verify/f2-schema-form-validation.png`。
| `G-3` | 页面手动：Config 节点 → provider 下拉切 `dashscope` / `deepseek` | 切 dashscope 带出 `openai/qwen3.5-omni-plus`（**你本轮拍板的新模型**）与 `openai/text-embedding-v4`；切回 deepseek 时 `embedding_model` 被删除 | ☐ |
| `G-4` | 手动：Config 表单温度填 `5` | 字段红框 + 错误文案（防抖约 1 秒）；清空后消失 | ☐ |

### 8.2 新增字段在 API 层的核对（前端未展示，属预期）

```powershell
Invoke-RestMethod http://127.0.0.1:8787/api/providers | ConvertTo-Json -Depth 4
```

期望：每个 provider 含 `name / api_base / model / vision_model / embedding / source / fetched_at / source_urls`，且 **`source = "file"`**、**绝不含任何密钥字段**。`source`/`fetched_at`/`source_urls` 是 F-AC8 新增的来源可溯信息，**前端本轮零改动故未渲染**（仅 API/CLI 可见）——这是口径而非缺陷。

---

## 九、联网 / 花钱项（可选，不影响本次结论）

| 编号 | 命令 | 估算成本 | 期望 | 判定 |
|---|---|---|---|---|
| `N-1` | `.\.venv\Scripts\python.exe .\verify\verify_checkpoint.py` | ¥0.05（network 档） | `ALL PASS (33 assertions)`；含首跑 `embedded=2` → 重跑 `reused=2/embedded=0` | ☐ |
| `N-2` | `.\.venv\Scripts\python.exe .\verify\verify_e2e_dashscope.py` | ¥0.5（估，**本轮未测量**） | 六步全链 PASS（答案含引用；同进程切 deepseek 隔离） | ☐ |
| `N-3` | `.\.venv\Scripts\python.exe .\scripts\refresh-providers.py --fetch --apply` | 免费（打第三方官网） | 产出 M16 归档 + proposal + status；**openai 403 为预期**（保留旧文件） | ☐ |
| `N-4` | `.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --task providers --check-due` | 免费（真实抓取） | 到期 → 执行刷新并写 `last_run`（**会创建 `agents/runtime/schedule.json`**） | ☐ |

> 不做 §9 也不影响验收结论：对应行为已由 §5 的离线证据与 §7 边界断言覆盖（`N-1` 的成本缺口见 §10-1）。

---

## 十、已知局限与未纳入本轮的项（诚实清单）

| # | 事项 | 影响面 | 是否影响本轮验收 |
|---|---|---|---|
| 1 | **成本未测量**：e2e 脚本不采 token 用量 → `N-2` 实际花费未知（估算上限 ¥0.5）；TG-5 的 `unknown` 需 `--record-cost` 人工回填 | 成本可见性 | 否（闸门行为正确：未测量即拒绝放行）；已列 Sprint-17 行动项 |
| 2 | **openai 官网 403** → `fetched_at: null`，永远判 due | 数据新鲜度 | 否（fail-closed 预期行为，非缺陷） |
| 3 | 首轮写入的 3 个文件（dashscope/deepseek/openrouter）`fetched_at` 为 `2026-09-12T23:52:36+0900`（UTC+8 口径修复**之前**写入）；修复后新写入为 `+08:00` | 时间口径一致性 | 否（时区感知解析正确，剩余天数偏差 1 小时）；如需统一可重跑 `N-3` |
| 4 | `config_schema` 的 `provider` 字段 **hint 文案陈旧**：只提 `providers.json / PAPERQA_PROVIDERS_JSON`，未提新的 `providers/*.json` | **GUI 可见文案**（不改行为） | 否（文案级）；**需你决定**：本轮修（改文本 + 复跑 114 断言）或并入 Sprint-17 |
| 5 | `HF_HUB_OFFLINE` 需手动设置；e2e/verify 脚本未统一处理 | 使用体验 | 否（已文档化）；Sprint-17 行动项 ② |
| 6 | 端口冲突未在脚本内自检 | 使用体验 | 否（§3.2 已提示）；Sprint-17 行动项 ② |
| 7 | 新脚本产物目录约定未写入 README/工作流 | 仓库卫生 | 否（`*.log`/运行时状态已 gitignore）；Sprint-17 行动项 ④ |
| 8 | **mental-models（MM-1~5）按你指示暂缓**，不在本轮 | 范围 | 否（口径已确认） |
| 9 | 子代理无产出时的接管判据已制度化（报告先行 + 15 分钟接管），但本轮仍出现两次主代理兜底 | 流程 | 否（纪律已落地，Sprint-17 观察） |

---

### 10.A 走查预跑发现并已闭环的项（2026-09-20）

> 你在走查前，我用**变异测试**（拿真实归档做负例）过了一遍门禁，发现 1 个真缺陷并已修复闭环。这格现在应该是 PASS，且**反证是可复现的**。

| 发现 | 证据（修复前 → 修复后） | 处置 |
|---|---|---|
| **第一轮（我预跑发现）**：M16 归档门禁的交叉引用**只有单向**：报告点名的证据文件缺失/悬空时不判 FAIL（违反 spec 归档契约 "a citation without an evidence file is a violation"）；自带"缺件"负例实为**空报告**，故自检长期假绿灯 | 删掉被引用的 `evidence/06-*.md`：`ALL PASS 25/0` → `FAILED 25/1`（`dangling=['06-...']`）；报告引用不存在文件：`ALL PASS 25/0` → `FAILED 25/1`；清空证据文件两版均 FAILED（未削弱） | 已修：交叉引用改**双向**（正向点名 + 反向落地）且 `expert`/`scholar` 两档都查；`--selftest` 2→4 例。复验：真实归档 28/28、selftest 4/4、矩阵一致、离线套件 **SUITE PASSED** |
| **第二轮（独立 code-review `run-2026-09-20-code-review-053` 复核后收紧，2 major/5 minor/3 nit）**：① 反向校验扫了**整篇报告** → 正文顺带提及别处证据名（跨 run 引用 / 相对路径 / URL 片段）会**把合规归档误判 FAIL**（我此前"run-047 无回归"的结论因此不成立）；② 大小写口径不一致（正向不敏感 / 反向敏感）→ Windows 假绿、敏感 FS 假红；③ 索引表里 `.markdown`／一位数编号的悬空引用静默漏检 | 复核以逐字副本冻结反例：C2/C3/C4 误红 `FAILED 27/1`、C5 漏报 `ALL PASS 28/0`、C1 `28/0`、C5b（`.md` 对照）`27/1` | 已按建议收紧：判定区间**限定证据索引表**（区间缺失则 fail-closed）、basename **小写集合**比较、引用识别放宽到 `.md|.markdown` 与 1~3 位编号、`--selftest` 4→**6 例**（补防误报 + 防漏报回归）、负例判据改为"唯一失败项名 == 目标断言"。**复跑**：C2/C3/C4 转 `28/0`、C5 转 `27/1`、C5b 仍 `27/1`（旧行为对照）、真实归档 `28/0` 与 run-047 `22/0`、离线套件仍 **SUITE PASSED** |
| **第三轮（同一复核的 round-2）**：确认前两项闭环，但抓到**我新引入的 major#3** —— 解析侧放宽到 `.md\|.markdown` 却没同步放宽**清单侧**（仍 `glob("*.md")`）→ **真实存在且被 §7 点名的 `.markdown` 证据被误判悬空（假红）**，而正向又因 stem 命中假绿（同一口径两侧不一致）；另有 minor：`evidence/` 子目录既漏校验又假红、根因断言与区间定位口径不一致、§7 标题行无换行匹配失败、非 ASCII 文件名不可见 | 复核样本 `R3b` 修复前 `FAIL dangling=['05-extra.markdown']` → 修复后 **`ALL PASS 18/0`** | 已修：清单侧同步 `rglob("*.md")+rglob("*.markdown")`（容忍子目录）、根因断言复用区间定位、标题行 `(?:\n\|$)`、字符类 `[\w.\-]`；`--selftest` 6→**8 例**（补"已存在 `.markdown` 不假红""嵌套子目录不假红"）。复跑：C5 仍 `27/1`、C5b 仍 `27/1`、真实归档 `28/0` 与 `22/0`、矩阵一致、离线套件 **SUITE PASSED** |

> **教训已入** `docs/3-LEARNED.MD` 的 **1.57**：交叉引用必须双向；范围要限定在承载契约的区间；跨平台口径（大小写/路径分隔符）要显式统一；**同一口径的"解析侧/清单侧"必须同步放宽**（只放宽一侧 = 假红与假绿并存）；放宽遍历范围必须同时设"链接/环"与规模上限；自检负例要成对（防误报 + 防漏报 + 防假红）并核对失败项名字。

> **走查后追加（同一复核 run-053 第 3/4 轮，2026-09-20）**：第 3 轮确认上述闭环，并抓出 `rglob` **跟随 junction 导致门禁挂死**（自指 junction 下 25s 未返回、3 层拖到 5 分钟/632MB）→ 改为受限遍历 + 文件数上限，**实测 0.1s 返回**；第 4 轮审 TG-7 与 Retro③ 计量链（critical 无），抓出"回调异步落地 → 空账被当 `0.0` → 闸门误判 measured 且低估金额"与"自动回填未与本轮绑定"两条 major，均已闭环并加回归（`verify_usage.py` **27 断言**、`verify_runner.py` **31 断言**）。

---

## 十一、判定汇总（回传用）

> **用户走查结论（2026-09-20，UTC+8）**：**未通过 = 暂未发现**（45 个判定格无 FAIL）；**存疑 6 项**见 §13.2（已逐条答复，其中 3 项转卡）、**新增问题 2 项**见 §13.1（已立卡 `F-AC13`/`F-AC14`）；走查期间发现并闭环 2 个真缺陷（M16 门禁反向校验、TG-7 闸门 fail-open），详见 §10.A。

| 区块 | 判定格数 | PASS | FAIL | 备注 |
|---|---|---|---|---|
| §2 口径确认 | 2 | | | |
| §6.1 M16 | 5 | | | |
| §6.2 F-AC10 | 4 | | | |
| §6.3 TG-5 | 5 | | | |
| §6.4 F-AC8 | 5 | | | |
| §7 边界专项 | 16 | | | |
| §8 GUI 回归 | 4 | | | |
| §9 联网项（可选） | 4 | | | |
| **合计** | **45** | | | |

**通过后的流程**（无需你操作）：写 §10 用户验收记录 → Sprint-16 关闭（DoD/ROADMAP/版本表同步）→ 推 windows 提交 → 创建 `sync/sprint-16` PR 同步 main（排除 `docs/iteration/`）→ CI 绿 → 合并。
**出现 FAIL 的流程**：按 §12 反馈 → 修复闭环 → 复验（只需复跑受影响编号）。

---

## 十二、问题反馈模板

```
【验收项】编号（如 B-9 / PV-4 / G-3）
【操作】  你做了什么（命令原文；GUI 则给点击顺序与输入值）
【实际】  看到什么——截图最直接（Win+Shift+S 可粘贴）；报错文字原样贴
【期望】  你认为应该是什么样
```

约定：不用分析原因，给"实际 vs 期望"的差距即可；命令报错请附**退出码**（`$LASTEXITCODE`）与最后 10 行输出。

---

## 十三、走查反馈与答复（2026-09-20，UTC+8）

> 用户走查结论：**未通过 = 暂未发现**（45 个判定格无 FAIL）；另有**新增问题 2 项**、**存疑 6 项**。本章为答复与处置记录（用户的措辞与编号原样保留）。

### 13.1 新增问题（已立卡，来源=用户走查）

| # | 用户描述 | 代码事实（本次核查） | 卡 |
|---|---|---|---|
| 1 | 点节点 button 经常 1~2 次无反应，第 3 次后才 run，怀疑与拖拽 node 冲突 | **根因已定位（2026-09-20 全量按钮审计）**：`FlowNode.jsx` 里带 `nodrag nopan` 的只有文本区与 output 块，**5 个运行按钮所在的 `.node-actions` 没有**该 class → 首次点击在 mousedown 阶段被画布拖拽/选择吃掉 | `F-AC13`（2 点，候选；**附带待确认项**：运行按钮无 `disabled`，`runSingleNode` 无 `running` 早退 → 重复点击是否并发触发需实测） |
| 2 | 点"复制答案"后"复制 output"也同步显示"已复制"，两个按钮同时变 | **已确认根因**：`FlowNode.jsx` 三个复制按钮共用同一个 `copied` state（line 42，被 187 / 199 / 224 三处消费）→ 任一按钮点击都会把三处一起置为"已复制 ✓"。**全量审计结论**：同仓库其它按钮（`FunctionTraceNode` 的 `errCopied`、翻译按钮 `disabled`、`SchemaForm` 的 `readonly`、App 工具栏与子画布按钮的 `active`/计数/title）均正常，**问题只在这三个按钮** | `F-AC14`（2 点，候选；用户要求"检查所有按钮行为"→ 已完成，见左） |

### 13.2 存疑答复（编号为用户所给）

| 编号 | 你的疑问 | 现状事实（已核代码 / 已实跑） | 处置 |
|---|---|---|---|
| `M16-5` | 模型信息更新后会影响更新前的报告吗？现在怎么处理 | **不改写旧报告**：evidence 是**抓取快照**（verbatim 原文 + `fetched_at`），报告只引用不重写；provider 更新写 `refresh_notes` + proposal/status。**但目前没有"依据已变"的提示机制**——旧报告不会自动标记"其依据已被新版官网文档取代" | 立卡 `M18`（报告时效与依据变更治理） |
| `CK-1` | 前端能看到载入的 checkpoint 文件吗（pro 用户成本感知 + 定位复现 + 幻觉核查） | **v1 已交付（2026-09-21）**：新增只读索引 `app/checkpoint_index.py` + 第 **12** 条路由 `GET /api/checkpoints`（`?key=` 明细）+ 前端工具按钮 `Checkpoints（本地复用/载荷路径）` → `CheckpointPanel.jsx`：命名空间列表（key/状态/文献数/载荷字节/模型与切块口径）+ 展开**逐篇载荷路径（可一键复制）**；回归 `verify_checkpoint_index.py` **29 断言** + `gui_check_fac16_checkpoint.mjs` **10 断言**（真实 15 个命名空间、零成本）。交付前状态为"仅后端 step 输出 `checkpoint{...}`、前端零展示"——已不再是现状 | 卡 `F-AC16`（v1 ✅；增量"一键用该 checkpoint 重放 / 按文献粒度成本展示"**待真实用户数据**，Sprint-17 再定） |
| `TG-1`~`TG-5` | 看起来都是脚本执行结果的校验，不像给我看的，跳过 | 属实：TG-5 这张卡的性质是**回归与调度底座**，判据天然是脚本断言（退出码 / 闸门 / 到期判定）；"人工可感面"在 §7/§8 | 计入 `TG-6`：验收指南须**分栏标注**"机器回归项 / 人工可感项"，机器项不占用户走查时间 |
| `B-9` | 预算超限场景没能模拟，跳过 | 已用**临时状态文件 + `--dry-run`** 复现全部五分支，零成本零风险（命令见 §13.4）：`unknown` → REFUSED(4)、`over_budget` → REFUSED(4)、`unknown`+上轮失败 → 自愈放行、`over_budget`+`--force` → 覆盖放行、`measured` → 放行 | 无需你操作；若你想自己复跑，命令已给 |
| `B-10` | "未到期 / 到期"指代不明，像是说 provider 列表到期导致原大模型不能用 | 是**我措辞的问题**：这里的到期指**定时任务**（`prices` 7 天 / `providers` 14 天 / `nightly-suite` 7 天）按 `interval_days` 的 due 判定，**与模型或服务到期无关** | 已改 §7 `B-10` 措辞 + 给复现命令（§13.4） |
| `B-15` | 深度阈值为什么是命令传参？不应该是前端显式配置吗？还有哪些类似 | 现状三类入口：① **前端可见可改**＝引擎配置（`/api/config_schema`，7 分组 23 字段，含 provider/model/embedding/chunk 等）；② **spec/配置节**＝调研深度阈值（`agents/functions/tech-research.md` 可配置参数节）与 `fanout.json` 的 `depth` 路由；③ **CLI/env/state**＝provider 刷新周期、夜间套件频率与预算、checkpoint 保留数。**②③ 目前前端不可见**——用户要用就得改文件或传参 | 立卡 `F-AC15`（运行参数显式配置面 + "哪些该上前端"清单） |

### 13.3 付费项（§9）执行审批流程（用户口径）

用户 2026-09-20 口径：**可以先执行，但必须先给出预计花费报告并获批准**，以便用真实数据支撑 billing plan 设计。预算报告已给出（N-1 ≤¥0.05 / N-2 ≤¥0.5 / N-3、N-4 ¥0，小计 ≈¥0.55），用户选择"**先打通 token 计量再跑**"。

**计量链路已落地并验证（2026-09-20，Retro③）**：`app/usage.py`（litellm 回调实测 token，抗 prune 裁剪；计费键取"能定价的名字"；缺价不臆测）→ `GET /api/usage` / step `output["usage"]` → `e2e_common.report_usage()`（`MEASURED_*` + 指标文件）→ `run_suite` 聚合 `cost_measured_cny` → `scheduled-tasks` **自动回填**三态闸门。回归：`verify_usage.py` **21 断言**、`verify_runner.py` ⑪a/⑪b；真实实测一次短调用 **¥0.0002**（42+7 tokens，计费键 `deepseek-v4-flash`）。

> 因此本节的执行结果给出的是**实测成本**（token 实测 + 本地价表换算），不再是估算上界。价表缺价的模型（当前 dashscope `qwen3.5-omni-plus` / `text-embedding-v4` 无价目）会显式列入 `unpriced_models`，此时成本记 `unknown`——**不臆测**，并作为"补价目"的待办暴露出来。

### 13.6 付费项执行记录（2026-09-20，**实测**）

| 编号 | 命令 | 结果 | 实测用量 / 成本 |
|---|---|---|---|
| `N-1` | `verify_checkpoint.py` | ✅ **ALL PASS 33 断言**，退出 0 | **¥0.016965** —— 12 次调用 / **4,473 tokens**（4,032 prompt + 441 completion），计费键 `deepseek-v4-flash`，无缺价 |
| `N-2` | `verify_e2e_dashscope.py` | ✅ 六步全链（dashscope + 同进程切 deepseek 隔离），退出 0 | **¥1.013377** —— 40 次调用 / **125,670 tokens**：`qwen3.5-omni-plus` 18 次/48,348、`deepseek-v4-flash-vision-exp` 16 次/43,225、`text-embedding-v4` 4 次/31,435、`deepseek-v4-flash` 2 次/2,662。**注**：运行时 dashscope 两模型缺价目 → 成本如实记 `unknown`（不臆测）；随后用 `fetch-prices.py --apply`（免费）补齐价目，按**同一批实测 token** 重算得此值 |
| `N-3` | `refresh-providers.py --fetch --apply` | ✅ 由 `N-4` 经调度器执行**同一条命令**（避免重复抓取同一批官网） | ¥0（不调模型） |
| `N-4` | `scheduled-tasks.py --task providers --check-due` | ✅ **首次创建** `agents/runtime/schedule.json`（`last_status=ok`，29.87s）；真实抓取 3 家成功 + `openai` 403 **fail-closed 保留旧文件**；产出归档 `run-2026-09-20-provider-refresh-001`（**M16 门禁 28/28 PASS**，`cited=8 dangling=[]`） | ¥0 |

**估算 vs 实测（billing plan 的直接输入）**

| 项 | `VERIFY_META` 估算上界 | 实测 | 偏差 |
|---|---|---|---|
| `N-1` | ¥0.05 | **¥0.0170** | 实测 ≈ 估算的 **1/3** |
| `N-2` | ¥0.5 | **¥1.0134** | 实测 ≈ 估算的 **2 倍**（`qwen3.5-omni-plus` 输出单价 1.1e-05 USD/token 偏高） |
| 本轮小计 | ¥0.55 | **¥1.0303** | 估算整体偏低 **+87%** |

- 价表刷新（免费）顺带补齐了 dashscope 两个模型的官方单价并捕获 openrouter 价格漂移 → 已提交 `agents/runtime/prices.json`。
- **已按实测校准** `verify_checkpoint.py`（0.05 → 0.02）与 `verify_e2e_dashscope.py`（0.5 → 1.1）的 `est_cost_cny`；其余 network 脚本仍是未校准估算（后续跑一次即可校准）。

### 13.4 `B-9` / `B-10` 零成本复现命令（可直接粘贴）

```powershell
$py = '.\.venv\Scripts\python.exe'
$tmp = Join-Path $env:TEMP 'sprint16-b9b10'; New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$old = [long]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) - 8*86400   # 8 天前 → 保证"已到期"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)                 # 关键：不可用 PS 5.1 的 utf8（会带 BOM → 状态被静默忽略）

# B-9① 到期 + 上轮成本未回填 → 期望 REFUSED / 退出 4
$f1 = Join-Path $tmp 'unknown.json'
[System.IO.File]::WriteAllText($f1, '{"schema":1,"tasks":{"nightly-suite":{"last_run":' + $old + ',"last_cost_status":"unknown"}}}', $utf8NoBom)
& $py .\scripts\scheduled-tasks.py --task nightly-suite --check-due --dry-run --state $f1

# B-9② 到期 + 上轮实测超上限 → 期望 REFUSED / 退出 4
$f2 = Join-Path $tmp 'over.json'
[System.IO.File]::WriteAllText($f2, '{"schema":1,"tasks":{"nightly-suite":{"last_run":' + $old + ',"last_cost_status":"over_budget","last_cost_cny":999.0,"last_cost_cap_cny":10.0}}}', $utf8NoBom)
& $py .\scripts\scheduled-tasks.py --task nightly-suite --check-due --dry-run --state $f2

# B-10 未到期 → SKIP（last_run=刚刚）；已到期 → RUN（last_run=0）
$now = [long]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
$f3 = Join-Path $tmp 'fresh.json'
[System.IO.File]::WriteAllText($f3, '{"schema":1,"tasks":{"providers":{"last_run":' + $now + '}}}', $utf8NoBom)
& $py .\scripts\scheduled-tasks.py --task providers --check-due --dry-run --state $f3
```

> 全程 `--dry-run`：**只打印不执行、不写状态**；`--state` 指向临时文件，真实 `agents/runtime/schedule.json` 不受影响。

### 13.5 走查期间发生的事故（如实记录）

准备 B-9 演示时，我用 PowerShell 5.1 的 `Set-Content -Encoding utf8` 写临时状态文件 → **带 BOM** → `load_state()` 解析失败但**静默返回默认空状态** → `nightly-suite` 被判"从未运行"并**真实启动联网套件**，约 3 分钟后随命令超时终止（已完成 `eval_retrieve` / `gui_check_s15_output_view` / `verify_agent` 三个脚本，`verify_checkpoint` 中断；**按 `VERIFY_META` 估算 ≈ ¥1.0**，实测花费仍缺测量）。已定位为**产品级 fail-open 缺陷**并立卡 `TG-7`。

**TG-7 已闭环（2026-09-20 当日，用户选择"现在修"）**：`load_state()` 改为 **fail-closed**——文件不存在=全新状态；**存在但解析失败或结构非法 → 退出码 2 拒绝执行** + 损坏文件另存 `.corrupt` + 修复指引；读取用 `utf-8-sig` **容忍 BOM**（编码伪影不误判为损坏）。回归证据：`verify_runner.py` **24 断言全 PASS**（⑩a 截断 JSON→拒 2 且无 RUN + 留副本 / ⑩b 带 BOM 的合法状态仍被读到 → 闸门 REFUSED(4) / ⑩c 顶层非对象→拒 2）；**BOM 反证由 `RUN` 转为 `REFUSED(4)`**（§13.4 命令即可复现）。

> 因此 §13.4 里"不可用 PS 5.1 的 utf8（会带 BOM）"这条现在**不再是风险**（BOM 被容忍），但**写损坏文件仍会被拒绝**——这正是我们要的行为。事故未影响验收结论，dev 服务与前端未受影响。

---

## 附：证据索引

| 类别 | 位置 |
|---|---|
| Sprint 记录 | `docs/iteration/sprint/2026-09-12-sprint-16.md`（§2 标准 / §2.1 case / §7 证据 / §9 三查） |
| verify 脚本（40 个 SSOT + 分层说明） | `verify/README.md`；矩阵 `verify/TEST-MATRIX.MD` |
| 本轮新增脚本 | `verify/run_suite.py`、`verify/verify_runner.py`、`verify/verify_providers.py`、`verify/verify_checkpoint.py`、`verify/verify_archive.py` |
| 本轮新增/改造实现 | `paper-qa-script/provider_config.py`、`paper-qa-script/providers/*.json`、`paper-qa-script/app/orchestration.py`、`paper-qa-script/app/engine.py`、`scripts/{refresh-providers,scheduled-tasks,register-scheduled-tasks}.{py,ps1}` |
| M16 规范与路由 | `agents/functions/tech-research.md`（v2.0.0）、`agents/fanout.json`（v5） |
| 首跑归档（本地、gitignore） | `agents/runs/run-2026-09-12-provider-refresh-001/`（28/28 PASS） |
| 三查运行档案（本地） | `agents/runs/run-2026-09-12-{impact-assessment-048,doc-audit-049,code-review-050,code-review-051,lessons-learned-052}` |
| 跨平台同步 | `windows` 分支（本轮交付）；`main` 待验收后经 PR 同步（排除 `docs/iteration/`；4 个 `scripts/*.sh` 删除**不**外传） |
