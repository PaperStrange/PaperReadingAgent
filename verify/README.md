# verify/ 验证脚本说明

本目录是 Windows 移植的自动化验收工具（可重复执行）。

> **SSOT 与分层运行（TG-2 / TG-5）**：脚本全集、tier（offline/gui/network）、预估耗时与成本、前置依赖以 [`TEST-MATRIX.MD`](TEST-MATRIX.MD) 为唯一真源（由各脚本头部 `VERIFY_META` 派生，`verify_matrix.py check` 防漂移）。分层执行用：
> - `python verify\run_suite.py --tier offline`（零网络零 key；CI/本地默认）
> - `python verify\run_suite.py --tier gui`（需前后端 + Playwright）
> - `python verify\run_suite.py --tier network --budget-cny 10`（真实 API，**fail-closed + 预算闸门**：预估超上限直接拒绝启动；**跑完按实测成本聚合**，`scheduled-tasks` 据此自动回填三态闸门）
>
> 本文件说明脚本**用途与运行前提**；新增脚本请同步在下方表格登记（矩阵会自动纳入校验）。
>
> **新脚本产物目录约定（TG-9）**：**新增脚本前先确认产物路径已被 `.gitignore` 覆盖**——产物一律写**已忽略目录**（运行态 JSON → `agents/runtime/`；日志/截图 → `verify/*.log`、`verify/*.png`；临时结果 → `%TEMP%`），写仓库根 = 直接在 `git status` 里多出未跟踪产物（本轮已因此误入库 `verify_checkpoint_run.log` / `ci_fail_log.txt`）。可核判据：`git check-ignore --no-index <产物路径>` 退 0；唯一的忽略根清单/已入库数据例外/动态目标棘轮 = `agents/policy.json::artifact_paths`，守门闸门 = `verify_artifact_paths.py`（offline）；规则条文见 `docs/1-WORKFLOW.MD` §6「新脚本产物目录约定」。
>
> **验收证据四件套（TG-6，2026-09-25 立规）**：**新增** `verify/*.py` 闸门须给出**四件套**——① 命令原文（含解释器路径）② 关键输出行（点名失败项原文）③ 退出码（实测 rc）④ **反向对照**（未修复/旧实现或注入样本上的 FAIL 记录）；并在**成功路径**打印一行可 grep 的机读证据行 `EVIDENCE: <脚本名> assertions=N rc=0`（失败/SKIP 不打印）。**存量脚本不回溯改造**；示范 = `verify_lint.py`（C 级可读性棘轮，caps 真源 `agents/policy.json::lint_readability_ratchet`）。条文见 `docs/1-WORKFLOW.MD` §6「验收 case 与证据形态四件套」。

| 脚本 | 内容 | 运行前提（显式化，Sprint-7 M5） |
|---|---|---|
| `verify_deduction_rates.py` | **§2.1.1/Sprint-17**：**扣率口径闸门**——未闭环 critical/major 的扣率真源 = `agents/policy.json::deduction_rates`（比例表 / 同根因合并开关 / 封顶 / 取整步长 / 棘轮折算 / "未闭环"四判据），读取器 `Policy.deduction_rates()` + 纯函数 `deduction_for()`。**本文件不出现任何比例数值**：期望值一律由政策算出（`2.5 − 2.5×ratios[major]`），否则闸门自己就成了第二份政策。反向对照两组：**fail-closed**（缺键/比例超界·负值·字符串·布尔/全 0/步长非法/判据缺证据·id 重复·无 `requires_due_date`/折算级别越界，共 14 例）与**数据驱动**（改政策比例 → 结果随之改变；关掉合并开关 → 同根因不再合并；显式传 `rates` 时不读任何文件）。含封顶（3 条不同根因 critical → 剩余 0）与"封顶优先于取整"（0.98 点卡不倒扣） | **offline 档**；`python verify\verify_deduction_rates.py`（自检）；`--show` 打印当前生效口径；首次实际结算时才加 CLI（§2.1.1） |
| `verify_smoke.py` | 8 项冒烟检查：paperqa 导入、后端 FastAPI 12 条路由、RuntimeTracer、streamlit、litellm、PyMuPDF 页渲染、graphviz(py)、PDF 解析器自动发现 | 无 API 调用，纯离线；无需启动服务 |
| `verify_prune_callbacks.py` | Sprint-5/M2：litellm 回调去重裁剪单元证据（超上限 32 项 → 去重保留最近 N；`PAPERQA_LITELLM_CALLBACK_LIMIT` 可覆盖默认 20） | 无 API 调用，纯离线 |
| `verify_agentops.py` | Sprint-8/A-UC：AgentOps 账本 CLI 用例断言（UC-1~UC-14：状态机/成本/防双写/价表/并发锁/抓取解析 + 三查修正回归 + **UC-14=TG-11 评审 scope 来源闸门**；UC-11/12=M10、UC-13=M9；隔离到临时 `AGENT_OPS_DIR`） | 无 API 调用，纯离线 |
| `verify_close_readiness.py` | **TG-15/Sprint-17**：关闭前置闸门（**三条不变式 + 全数据驱动**——TG-11 版按角色写死的 6 条判据已删除）——**C1 声明完备**（凡 spec 声明 `scope_required: true` 的 run 必须有 scope 声明）/ **C2 指涉可核**（外部引用必须解析到"存在且可用"的对象；账本出现无 spec 的 role 即 FAIL，不认角色名）/ **C3 覆盖闭环**（`git rev-list <锚点>..HEAD` **每个提交**必须有归属：run 窗口（`coverage_anchor`/`covers_through` 自动记录）/ C3-T 例外表（sha 钉死）/ doc-only 自动归类）+ §9 run 表↔账本**双向**一致。**必填步骤与 target 来自 `agents/fanout.json`**，角色属性来自各 spec frontmatter，阈值来自 `agents/policy.json`；**变异用例从 fanout 自动生成**（每步/每 target 各抽掉一次 → 必须 FAIL）。默认跑自检（断言数随新增判据增长，**不要手抄具体数字**——以脚本输出的 `ALL PASS (N assertions)` 为准）；`--sprint <文件>` 为真数据校验（**CI 只对声明了 `三查锚点` 的 Sprint 文档执行**），`--no-coverage` 关闭覆盖检查 | 离线；真数据模式调用本地 `git rev-list`，无网络 |
| `verify_no_policy_hardcode.py` | **TG-15⑦/Sprint-17**：**硬编码政策闸门**（"政策必须在数据文件，不许写进代码"）——AST 判定 R1 政策常量赋值（角色集合/阈值）、R2 成员判定字面量（`x in {"code-review"}`）、R3 覆盖路径清单；豁免台账 `policy-hardcode-exemptions.json` 每条**须写 category+reason**（不提供整文件豁免），另有就地豁免形态 `X = _exempted_local(...)`（理由写在赋值处）。含反向对照：三类注入必须 FAIL、`load_policy()` 写法必须放行、就地豁免只放行该处（同文件真硬编码仍被抓）、**`--dir` 分支的真实退出码**（有发现非 0 / 无发现 0 / 打印含 `file` 定位） | 离线；`python verify\verify_no_policy_hardcode.py`（`--dir <d>` 只扫指定目录，退出码 1=有发现） |
| `verify_lint.py` | **G1/Sprint-17（§2.3 Python 行）**：ruff 闸门——**A 级** `E9,F63,F7,F82` 与 **B 级** `F401,F811,F841,E702,E711,E712,E722,W292` 全仓必须 0；**C 级** `D101-103,E501` 走**棘轮**（caps + `review_by` 来自 `agents/policy.json::lint_readability_ratchet`，计数 > cap 即 FAIL 并点名；cap 只许下调）。含"坏文件必 FAIL / 好文件必 PASS / 干净副本零 problem / 注入 1 处 C 级违规必 FAIL / caps 缺键·多键·过期必 FAIL"反向对照；工具缺失 **fail-closed（退 2）**，`--allow-missing` 显式 SKIP。**TG-15：覆盖路径与规则分级改由 `agents/policy.json`（`lint_paths`/`lint_rules`）提供**，不再写死在本文件 | 无网络、无 API 调用（ruff 本地二进制；pin 见 `requirements-windows.txt`） |
| `verify_index_health.py` | Sprint-7/M1：索引一致性三重探测（files.zip / index/meta.json / tantivy 段）合成形态 + 真实构建后篡改 meta.json → 整目录重建自愈 | 无 API key、无远程 LLM 调用（manifest 提供 citation；本地 ST 权重从 HF 缓存加载，首次需联网下载）；索引隔离到临时 `PQA_HOME` |
| `verify_config_schema.py` | Sprint-11/13/F2：配置 SSOT 一致性断言——schema 结构/默认值/pydantic_path、validate_config 行为、**M7 前端零硬编码**（App.jsx n1 不得含 16 个配置键字面量）、**Settings 升级基线护栏**（77 字段路径 vs `settings_baseline.json`，`--regen-baseline` 重建） | 无 API 调用，纯离线 |
| `verify_provider_switch.py` | 验证服务商切换（内置 4 家 + 自定义）：配置解析、密钥优先级、build_settings、**路由实证断言**（deepseek 真实 key 应 SUCCESS；dashscope/openai/openrouter/自定义 用占位 key 应拿到端点级拒绝=路由正确） | 联网；deepseek 真实 key（`.env` 或 `OPENAI_API_KEY`）；**真实 openrouter key 实测为用户资源门控**（占位 key 只证路由不证配额） |
| `verify_e2e.py` | 启动真实后端（8787）→ 全链路 6 步，校验答案长度并保存结构化结果到 `verify_e2e_result.json`；**TG-4 起共享 `e2e_common.py` 基座（config 恒显式 provider/vision_model）** | 需要 `DEEPSEEK_API_KEY` + 本地 st- 向量模型；联网 |
| `verify_e2e_openai.py` | Sprint-7 追加：**OpenAI 作为 provider + embedding**（gpt-4o-mini + text-embedding-3-large）全流程 + 同进程 deepseek→openai 切换（key 隔离回归）；**TG-4 修复 1.46**：config 恒显式携带 vision_model，共享 `e2e_common.py` 基座 | 需要真实 `OPENAI_API_KEY`（**账户需有余额**，无 DeepSeek 兜底）+ `DEEPSEEK_API_KEY`（Phase 2，或通用 `OPENAI_API_KEY` 兜底）；联网 |
| `verify_e2e_dashscope.py` | 校验 deepseek→dashscope 全流程切换：Phase 1 dashscope 全链路 6 步 + Phase 2 同进程 deepseek 全流程（key/配置隔离回归）；**TG-4 起共享 `e2e_common.py` 基座** | 需要 `DASHSCOPE_API_KEY` + `DEEPSEEK_API_KEY`；联网 |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | 同上，且索引 `verify_e2e_index` 已存在（e2e 先跑过） |
| `verify_embed_load.py` | parse_chunk_embed 三种模式：run（重跑）/load 同会话（秒级）/load 新会话（embed 缓存），校验 texts 数量一致 | 需要 `DEEPSEEK_API_KEY`（或通用 `OPENAI_API_KEY` 兜底）+ 本地 st- 向量模型 |
| `verify_remote_e2e.py` | remote 数据源全链路（Sprint-3）：config(remote+arXiv) → load_index（下载+索引）→ retrieve → parse → evidence → answer | 需要 `OPENAI_API_KEY`；联网（export.arxiv.org） |
| `eval_retrieve.py` | Sprint-6/F4：检索质量小样本评测（双语料 + 策略断言 + 负对照，报告 hit@1） | 需要 `DEEPSEEK_API_KEY`（或通用 `OPENAI_API_KEY` 兜底）+ 本地 st- 向量模型 |
| `gui_check.mjs` | GUI 全链路：Playwright 打开前端 → 点 "Run All (Left-to-Right)" → 等待答案出现 → 截图 | 后端 8787 + 前端 5173 **已启动**；Playwright Chromium 已安装；`.env`/`OPENAI_API_KEY` 已配；`node verify\gui_check.mjs`（playwright 取前端 node_modules） |
| `gui_check_remote.mjs` | GUI 远程数据源（Sprint-3）：Config 面板切 remote + 填 arXiv ID → Run All → 答案出现 → 截图 `us3-remote.png` | 同 `gui_check.mjs` + 联网（export.arxiv.org） |
| `gui_check_s4.mjs` | Sprint-4：光标不跳末尾 + provider 下拉联动（openrouter/deepseek 自动带出） | 同 `gui_check.mjs` |
| `gui_check_s5.mjs` | Sprint-5：自动重跑 config、retrieve 双模式标记、计时冻结、复制报错按钮（7 项断言） | 同 `gui_check.mjs` |
| `gui_check_s7.mjs` | Sprint-7 M4：多节点并发计时显示（retrieve+evidence 并发 → `A X.Xs · B Y.Ys`）+ 完成后冻结 | 同 `gui_check.mjs` |
| `gui_check_dashboard.mjs` | Sprint-9：看板概览页截图（状态卡片/环形图/账本列表） | agents-dashboard 已启动（8600，生产模式）；Playwright Chromium 已安装 |
| `gui_check_dashboard2.mjs` | Sprint-9：看板 spec 编辑页截图 | 同 `gui_check_dashboard.mjs` |
| `gui_check_dashboard_costs.mjs` | Sprint-9：看板成本/上下文页截图（CNY 合计、pending 标注、上下文占用） | 同 `gui_check_dashboard.mjs` |
| `gui_check_dashboard_report.mjs` | Sprint-9：看板报告浏览页截图（run 详情 + 报告全文） | 同 `gui_check_dashboard.mjs` |
| `gui_check_dashboard_fanout.mjs` | Sprint-10：看板 fan-out 配置页截图（两条流水线可视化 + JSON 编辑器） | 同 `gui_check_dashboard.mjs` |
| `gui_check_config_schema.mjs` | Sprint-11/12/13：Config 节点 schema 清单/全字段表单截图 + 字段级校验证据（非法温度值 → 错误态）+ defaults-derived-from-schema 断言 | 后端 8787 + 前端 5173 已启动；Playwright Chromium 已安装 |
| `verify_matrix.py` | TG-2：覆盖矩阵 SSOT——从各脚本头部 `VERIFY_META` 派生 `TEST-MATRIX.MD`；`check` 模式逐字节防漂移（CI 离线套件内） | 离线；`derive` 生成矩阵 / `check` 校验 |
| `verify_local_dir.py` | Sprint-15/F-AC3：引擎接线实证——临时目录 `paper_directory` → config → load_index(build) → retrieve，断言候选来自该临时目录 | **offline 档**：自举后端（8787 需空闲）；本地 st- 向量模型；**免密**（CSV manifest 提供 citation + 占位 key → 构建全程无 LLM 调用，见 3-LEARNED 1.30 追加） |
| `verify_f12_preview_res.py` | Sprint-15/F-AC12：论文截图预览分辨率护栏（缩放 1.0 + 尺寸上限）实证 | 离线；本地 st- 向量模型 |
| `verify_checkpoint.py` | Sprint-16/F-AC10：**文献级 embedding checkpoint**——首跑全嵌入 → 重跑 `reused=2/embedded=0`（零成本）→ 文件变更/载荷损坏/模型不匹配/切块口径/同内容去重五重边界 | **network 档**（parse 链路含真实 LLM 引用推断调用）：需 `DEEPSEEK_API_KEY`；自举后端（8787 需空闲）；本地 st- 向量模型；`HF_HUB_OFFLINE=1` 可避免联网校验 |
| `verify_archive.py` | Sprint-16/M16：**调研归档完整性门禁**（report/context/reasoning/evidence 五字段 + verbatim 引用块 + 证据索引表**双向**交叉引用：正向=每个 evidence 文件须被索引表点名，反向=索引表点名的文件须存在于磁盘；**判定限定在证据索引表区间内**（正文顺带提及别处证据名不算引用）、文件名**大小写不敏感**、**`.md`/`.markdown` 均可且容忍子目录**、**遍历不跟随 junction/软链 + 文件数上限**（防挂死/爆炸）；**2026-09-20 走查修复 + 复核 run-053 三轮收紧**；quick 档豁免）；`--selftest` 内置八例（合规 expert/scholar 通过 + 空报告被拒 + 被引用证据缺失被拒 + 正文提及不误判 + 索引表 `.markdown` 漏报被拦 + 已存在 `.markdown` 不假红 + 嵌套子目录不假红） | 离线；`python verify\verify_archive.py <run_dir> --depth expert` |
| `verify_providers.py` | Sprint-16/F-AC8：**provider 一文件**加载/来源标记/覆盖优先级/非法文件跳过/无密钥泄漏/调研 meta 契约 + 离线刷新链（归档+proposal+meta 刷新）与**抓取失败保留旧文件**、到期判定可配置 | 离线（目录重定向到临时目录，不改动仓库文件） |
| `verify_runner.py` | Sprint-16/TG-5：分层 runner + 定时底座断言（offline 全绿 / 注入失败 fail-closed / 预算超限拒绝启动退出 3 / env 上限可配置 / due 未到期跳过 / cost unknown 拒绝放行退出 4 / record-cost 回填 / providers 未就绪 UNAVAILABLE / **TG-7：状态文件损坏或结构非法 → 拒绝执行退出 2 + `.corrupt` 副本留存；带 BOM 的合法状态仍被读取**） | 离线（合成 fixture，不跑真实套件） |
| `run_suite.py` | Sprint-16/TG-5：**分层 runner 本体**（按 `VERIFY_META.tier` 执行 offline/gui/network；fail-closed；三态预算闸门；结果 JSON 原子落盘；**Retro③：聚合子脚本经 `PAPERQA_SUITE_METRICS` 回报的实测成本 → `cost_measured_cny`/`cost_status`**）。命名不带 `verify_` 前缀 → 不纳入矩阵校验，但同样带 `VERIFY_META` | 离线自身；视 tier 而定 |
| `verify_usage.py` | Sprint-16/Retro③：**token 用量采集与成本换算回归**（对象/dict 响应解析、累计与增量、价表查找与 `openai/` 前缀归一化、**缺价不臆测**、token×单价×fx 换算式、回调幂等与**抗 prune 裁剪**、**计费键取"能定价的名字"**+`reported_as` 可追溯） | 离线；`python verify\verify_usage.py` |
| `verify_checkpoint_index.py` | Sprint-16/F-AC16 v1：**checkpoint 只读索引回归**（扫描/排序/逐篇 `payload_path`+`payload_exists`+字节数、坏 manifest fail-soft、`namespace_detail` 与 `resolve_payload`、字段白名单、空目录） | 离线（合成 fixture，不碰真实 `~/.pqa`）；`python verify\verify_checkpoint_index.py` |
| `verify_freshness.py` | Sprint-16/M18 v1：**报告时效检测回归**（stale/suspect/fresh 三态、只分析调研归档、正文提及不算引用、**无时区信息按 UTC+8**、容差可配、`--check` 退出码、容错） | 离线（合成 fixture）；`python verify\verify_freshness.py` |
| `verify_ledger_rounds.py` | Sprint-16/TG-10：**账本多轮次记录回归**（终态 run 仍可 `round` 追加、`rounds[0]` 保留首轮快照、`rounds_count`/`output_chars` 累加、`list` 的 `dur` 反映累计时长、`round --interrupted` 与独立 `interrupt` 写原因/影响/来源、非法 run 非零退出；`AGENT_OPS_DIR` 重定向到临时目录） | 离线（`AGENT_OPS_DIR` 重定向到临时目录，不碰真实账本）；`python verify\verify_ledger_rounds.py` |
| `verify_ledger_measurement.py` | Sprint-17/TG-13：**账本『测量化』闸门**——口径可核（`dur`=墙钟累计/`rounds` 真源=报告轮次/缺值必须显式 `unknown`，真源 `agents/policy.json::ledger_measurement`）+ 账本↔`agents/runs/**` **双向**一致（白名单 `agents/policy/run-dir-exceptions.json`，每条须写 reason 且只减不增）+ 时间戳退化（相同/`0.00`/整十分钟/负值/缺失）+ `rounds` vs 报告轮次 + **终态已写回** + `measurement_source`/`dur_minutes` 契约 + **历史棘轮**（计数上限 + `review_by`，截止日之后一律严格）；默认模式 = 真实账本 + 30 条自检（含四类反向对照样本） | **offline 档**；`python verify\verify_ledger_measurement.py`（真实账本 + 自检）；反向对照样本：`--emit-fixture <kind> --agents-root %TEMP%\tg13-rc\<kind>` 后用 `--agents-root` 判定（样本不写进仓库） |
| `verify_artifact_paths.py` | **TG-9/Sprint-17**：**产物目录约定闸门**——"脚本源码里的写盘路径必须落在已忽略目录或 `%TEMP%`"。AST 严格分解写盘目标（`open(...,"w")`／`write_text`／`mkdir`／`os.replace`／`shutil.*`／`.mjs` 截图名；名字按赋值链还原、`os.environ.get` 取默认落点）→ 逐条 `git check-ignore --no-index` 判定；**忽略根双向差集**（政策 `ignored_roots` 每条必须真被忽略、`.gitignore` 里确有其行、且确有代码在用；政策 ↔ 忽略文件 ↔ 代码三方互为解释）；**动态目标棘轮**（按文件设上限，未列入上限表的新文件出现动态目标即 FAIL）；**反向对照**：注入"写到仓库根"的新脚本 → rc=1 点名，注入"写默认落点 `agents/runtime/`"→ rc=0，并实测产物落入默认落点后 `git status --porcelain` 为空 | **offline 档**；需 `git`（判据用 `git check-ignore` / `git status`）；`python verify\verify_artifact_paths.py`（默认＝真实仓库 + 10 条自检）；`--report` 打印动态目标分布；`--scan-root <dir>` / `--emit-fixture <kind>` 用于注入样本（样本一律写 `%TEMP%`） |
| `gui_check_fac16_checkpoint.mjs` | Sprint-16/F-AC16 v1：**Checkpoints 只读面板**（API 形状 + 面板开关 + 真实命名空间行数一致 + 逐篇载荷路径形如 `<key>/<dockey>.json.gz` + 复制按钮）；**零成本**，不触发 LLM | 后端 8787 + 前端 5173 + Playwright |
| `gui_check_s15_*.mjs`（10 个） | Sprint-15 F2 验收修复族：`typography`（字体统一）/`hints_title`（聚合+限高）/`local_dir`（条件隐藏）/`collapse`（完成后收起）/`status_scope`（状态作用域）/`responsive`（三档分辨率）/`bidi_link`（双向联动）/`error_copy`（复制+报错定位 19 断言）/`output_view`（output/答案全文）/`cursor`（光标不跳+改动计数） | 后端 8787 + 前端 5173 已启动 + Playwright（`output_view` 为 network 档，需 key） |

运行示例：

```powershell
$env:OPENAI_API_KEY = "<DeepSeek key>"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py
.\.venv\Scripts\python.exe .\verify\verify_prune_callbacks.py
.\.venv\Scripts\python.exe .\verify\verify_agentops.py           # AgentOps 账本 CLI 用例断言（离线）
.\.venv\Scripts\python.exe .\verify\verify_no_policy_hardcode.py # TG-15⑦：政策硬编码闸门（离线）
.\.venv\Scripts\python.exe .\verify\verify_config_schema.py     # 配置 SSOT 一致性 + M7 零硬编码 + Settings 升级基线（离线）
.\.venv\Scripts\python.exe .\verify\verify_index_health.py
.\.venv\Scripts\python.exe .\verify\verify_matrix.py check         # 覆盖矩阵防漂移（离线；改动脚本元数据后先 derive）
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py   # 联网
.\.venv\Scripts\python.exe .\verify\verify_e2e.py
.\.venv\Scripts\python.exe .\verify\verify_e2e_openai.py       # OpenAI provider+embedding 全流程（账户需余额）
.\.venv\Scripts\python.exe .\verify\verify_e2e_dashscope.py   # dashscope 全流程 + deepseek 同进程切换（联网）
.\.venv\Scripts\python.exe .\verify\verify_agent.py
.\.venv\Scripts\python.exe .\verify\verify_embed_load.py        # Embedding 三步（run/load/缓存）
.\.venv\Scripts\python.exe .\verify\eval_retrieve.py            # 检索质量小样本评测（F4）
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py       # Sprint-3 remote 全链路（联网）
node .\verify\gui_check.mjs          # GUI（需先启动前后端）
node .\verify\gui_check_remote.mjs   # GUI remote 数据源（需先启动前后端 + 联网）
node .\verify\gui_check_s4.mjs       # Sprint-4 光标 + provider 联动（需先启动前后端）
node .\verify\gui_check_s5.mjs       # Sprint-5 自动重跑/双模式/复制报错（需先启动前后端）
node .\verify\gui_check_s7.mjs       # Sprint-7 M4 并发计时（需先启动前后端）
node .\verify\gui_check_dashboard.mjs         # Sprint-9 看板概览页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard2.mjs        # Sprint-9 看板 spec 页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_costs.mjs   # Sprint-9 看板成本页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_report.mjs  # Sprint-9 看板报告页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_fanout.mjs   # Sprint-10 看板 fan-out 配置页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_config_schema.mjs      # Sprint-11 Config 节点 schema 清单截图（需前后端已启动）
```

Sprint-16 新增（分层 runner 与门禁）：

```powershell
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier offline                  # 分层执行：offline 全绿才通过（fail-closed）
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier network --budget-cny 10  # 联网档：预估超上限直接拒绝启动（退出 3）
.\.venv\Scripts\python.exe .\verify\verify_archive.py agents\runs\<run_id> --depth expert  # 调研归档门禁
.\.venv\Scripts\python.exe .\verify\verify_checkpoint.py      # F-AC10 断点续跑（建议加 HF_HUB_OFFLINE=1）
.\.venv\Scripts\python.exe .\verify\verify_providers.py       # F-AC8 provider 一文件 + 刷新链
.\.venv\Scripts\python.exe .\verify\verify_runner.py          # TG-5 runner/定时/预算闸门
.\.venv\Scripts\python.exe .\verify\verify_ledger_measurement.py  # TG-13 账本测量化闸门（真实账本 + 反向对照自检）
.\.venv\Scripts\python.exe .\verify\verify_artifact_paths.py      # TG-9 产物目录约定闸门（写盘落点必须已忽略/在 %TEMP%）
.\.venv\Scripts\python.exe .\verify\verify_deduction_rates.py     # §2.1.1 扣率口径闸门（政策数据 + 纯函数 deduction_for 正反例）
.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --list # 定时任务与到期状态（prices/nightly-suite/providers）
```

已知差异：graphviz 已自动发现（冒烟第 7 项扫描常见安装目录）；仅当系统完全未安装 Graphviz 时才报 `ExecutableNotFound`（可选安装，见 `docs/3-LEARNED.MD` 验证记录）。
