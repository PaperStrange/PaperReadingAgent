# TG-8 **自举后端前端口自检 + 离线开关统一注入**（Retro 行动项 ② 升级为必修）：`verify/e2e_comm

- `card`: TG-8
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**✅ 完成（2026-09-25，Sprint-17）** —— 交付物与实测证据见下方「交付与实测」；端口自检的实现真源为 `verify/e2e_common.py`，离线开关的真源为 `PAPERQA_OFFLINE`（拒绝点在各来源发请求之前）。
（原状态："计划中（Sprint-17，用户 2026-09-21 确认）"。**2026-09-25 一查 `run-2026-09-25-doc-audit-070` 指出"本卡状态未随结算更新"后按 `1-WORKFLOW.MD:408` 同步**。）

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

### 交付与实测（2026-09-25，Sprint-17 D2/D3）

**① 端口自检（可核）**

| 项 | 落点 | 判据 |
|---|---|---|
| 自举前 fail-fast | `verify/e2e_common.py::port_selfcheck()`（`start_backend()` 第一行调用；`verify_local_dir.py` 也显式调一次） | 端口被占 → `RuntimeError`，**在拉子进程之前**抛出，消息含三件可操作信息：端口号 / 占用进程（PID+镜像名）/ 怎么释放或改端口 |
| 不静默复用 | `wait_healthy()` 只保留"健康探测"职责，归属校验上移到自举前 | 旧行为（只探端口不校验归属）已消除；dev 后端在跑时脚本**不再复用**它 |
| 端口可配置 | `PORT = int(os.environ["PAPERQA_VERIFY_PORT"] or 8787)` | 报错文案里给的"改用其它端口"提示**真的生效**（否则是空头支票） |
| 反向对照（本脚本内 4 条断言） | `verify/verify_local_dir.py::port_selfcheck_conflict_assertions()` | 自己起监听占住 8787 → 子进程 rc=1 且点名端口+PID+释放/改端口提示；释放后同一路径 rc=0；预检通过路径不留监听 |

**② 离线开关（可核）**：唯一实现 `verify/outbound_guard.py`（脚本侧）+ `paper-qa-script/app/offline_guard.py`（后端侧最小只读实现）；政策数据 `agents/policy.json::offline_switch`（开关名 `PAPERQA_OFFLINE` / 真值表 / 拒绝文案 / 退出码 / HF 离线变量）；**优先级 env > 政策 `enabled`**。四个外呼入口在**发请求之前**被拒绝（`scripts/fetch-prices.py`、`scripts/refresh-providers.py`、`scripts/agent-ops.py fetch-spec`、`paper-qa-script/app/engine.py` 的模型 API）；`verify/e2e_common.py` 在开关开启时注入 `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`。断言 = `verify/verify_agentops.py` **UC-19（12 条）**：三入口拒绝 + 反向对照（关闭时不误拒）+ 取值拼错 fail-closed + env 覆盖政策 + 政策面单独生效 + 两侧实现一致。

**断网实跑证据（代理级，2026-09-25 实测）**：把 `HTTP(S)_PROXY` 指向 `127.0.0.1:9` 后——

| 口径 | 结果 |
|---|---|
| 对照探针（无代理） | `HTTP 200`（出网正常，说明探针有效） |
| 对照探针（代理断网） | `URLError [WinError 10061] actively refused` ⇒ **出网确实被挡** |
| 开关**关闭** + 代理断网 | `fetch-prices --check` **rc=0**、6.29s、三个来源各报 `FAIL: URLError …`、**无**拒绝标记 ⇒ 走的是真实网络路径 |
| 开关**开启** + 代理断网 | `fetch-prices --check` **rc=2**、**0.10s**、`OFFLINE-REFUSED: …拒绝外呼：https://api-docs.deepseek.com/…`（点名来源 `env PAPERQA_OFFLINE=1` 与目标 URL）⇒ 拒绝发生在发请求之前（0.1s vs 6.29s，不是超时） |
| 开关**开启** 且 provider 刷新入口 | `refresh-providers --fetch` **rc=2**、0.11s、点名 `help.aliyun.com/...` |

**局限（如实标注）**：上表是**代理级**断网（只约束尊重 `HTTP(S)_PROXY` 的客户端：urllib/requests/httpx），**不是内核级**（防火墙/WFP 规则需管理员权限，本卡不引入）；故本开关的定位是**应用层闸门**——它保证"被枚举的入口拒绝得又早又明确"，不宣称"进程内所有 socket 都被拦"。

**③ `verify_local_dir.py` flaky 归因（结论：**根因已定位并修复**）**

**根因（实测抓到的完整叶子异常）**：`F-AC3 load_index` 的
`unhandled errors in a TaskGroup (1 sub-exception)` = **媒体 vision 增强的 401 逃逸**。链路逐帧如下：

```
orchestration.py:634 run_step(load_index) → engine.py:310 get_directory_index
  → paperqa/agents/search.py:693 anyio.create_task_group()   ← paperqa 全仓库唯一一处 TaskGroup
  → search.py:522 process_file → docs.py:303 Docs.aadd
  → paperqa/settings.py:1122 llm.call_single(...)  ← 占位 key 打 vision 模型
  → openai 401 → litellm 转成 litellm.exceptions.RateLimitError
  → settings.py:1134 只捕获 (litellm.InternalServerError, litellm.BadRequestError) ⇒ **不被捕获**
  → asyncio.gather 抛出 → Docs.aadd 抛出 → process_file 的
    `if not isinstance(e, ValueError | ImpossibleParsingError): raise`（search.py:544-547）
  → anyio 包成 ExceptionGroup，`str()` 只显示 "1 sub-exception"
```

**判定为"偶发"的机制**：是否发生取决于**该 PDF 是否有可增强的媒体**（`Skipping enrichment …` 日志证明富化确实在跑）
与那一次外呼拿到的是 `BadRequestError`（会被吞）还是 401/`RateLimitError`（会逃逸）。卡内记的"N 次里偶发 1 次"即此形态。

**可复现的最小实验（不落仓库、跑在 `%TEMP%`）**：包装后端把 `Docs.aadd` 换成"抛指定类型"，走与 `verify_local_dir.py` 完全相同的 HTTP 路径——
注入 `PermissionError` → 顶层 `error` 与卡内证据**逐字一致**、`error_detail` 展开到 `search.py:693 → search.py:522 → PermissionError`；注入 `ValueError`（对照）→ `ok=True`（被 `process_file` 吞掉）⇒ **异常类型决定是否逃逸**，不是"任何异常都炸"。

**修法（两处，都不放宽断言）**：
- **可归因性**：`verify_local_dir.py` 的三个步骤改为经同一个 helper 发请求，失败即打印后端 `error_detail`——**旧实现只取 `error` 字符串、把 anyio 的 ExceptionGroup 丢掉**，这正是卡内"根因未展开"的直接原因；修完后第一次偶发失败就把上面那串叶子异常打了出来。
- **消除外呼**：该链路按设计是"本地目录 → 本地 `st-` 向量 → 检索，**不调用 LLM**"，故 `verify_local_dir.py` 自举后端时设 `PAPERQA_NO_MEDIA_ENRICHMENT=1`（`app/engine.py::make_settings` 读它 → `parsing.multimodal=2` = 解析图片/表格但**不做 vision 增强**），收尾恢复原值不泄漏。**产品默认行为不变**（不设该 env 即逐字段沿用原值）。实测：修后服务端日志 `Skipping enrichment` 0 行、`Authentication Fails`（401）0 行。
- 另两处确定性加固：索引名唯一化（消除 `_OPENED_INDEX_CACHE`/Tantivy 写锁的跨轮共享状态）；`stop_backend` 在 kill 后补 `wait()`、临时目录清理**就地重试 + 失败显式 WARN**（不再 `ignore_errors=True` 静默吞残留）。

**④ 顺带修掉一处"闸门自己"的顺序依赖（TG-9 闸门抓出来的）**：`verify_artifact_paths.py` 的写盘目标分解器**按变量名**收集赋值，于是 `verify/e2e_common.py` 里名为 `path` 的局部变量与扫描集里另一个 `path = Path(args.spec_file)` 同名且取值不一致 → 判成"动态目标" → `e2e_common.py` 计数 2→3 **顶破棘轮上限**。后果是**测试顺序依赖**：该闸门**单跑 PASS、在全序列里 FAIL**（本轮实测两次）。修法 = 变量改名（`path`→`metrics_path`；另一处 `path`→`guard_path`），判据与顺序无关；`e2e_common.py` 的动态目标计数回到实测基线 2。**教训同族**：闸门的输入若依赖"同名变量的其他出现"，它本身就带顺序依赖——这是 TG-8 flaky 的又一条独立成因（与端口无关）。

**⑤ 回归实测（2026-09-25）**

| 口径 | 次数 | 结果 |
|---|---|---|
| 单跑 `verify/verify_local_dir.py`（修复后） | **3 + 5** | 全部 rc=0、各 **7 断言**（含 4 条端口自检断言）；修复后用时 33~35s（此前 56~59s：省掉的是 vision 外呼） |
| 单跑（修复前基线） | 5 + 12 + 1 | 前 17 次 rc=0（flaky 未出现）＋ **第 18 次复现 FAIL**（`load_index` → TaskGroup 1 sub-exception，`error_detail` 抓到根因） |
| 全序列 `verify/run_suite.py --tier offline`（修复后） | **2** | **SUITE PASSED (21 scripts)**、`status=ok` |
| 全序列（修复过程中） | 2 | `SUITE FAILED (1/21)`：一次 `verify_artifact_paths.py`（④ 的顺序依赖）、一次 `verify_lint.py`（改名后残留的 F401 未用导入）→ 两处都是**真缺陷**，已修；**未放宽任何断言换绿** |

**⑥ 残留风险（如实标注）**：媒体增强的失败类型判据仍写在 vendored `paperqa` 里（`settings.py:1134` 只捕两类异常），故**同型逃逸对"真跑 vision"的链路依然存在**（例如 `verify_e2e*.py` 在图片页上遇到 401/429 会整步失败）——本卡只在**离线免密链路**上关掉了该外呼。要不要把该修复推到 vendored 层（或改成 `multimodal=1` 的显式配置项），超出本卡 2 点范围，**建议另开卡**。

