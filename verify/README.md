# verify/ 验证脚本说明

本目录是 Windows 移植的自动化验收工具（可重复执行）：

| 脚本 | 内容 | 运行前提（显式化，Sprint-7 M5） |
|---|---|---|
| `verify_smoke.py` | 8 项冒烟检查：paperqa 导入、后端 FastAPI 路由、RuntimeTracer、streamlit、litellm、PyMuPDF 页渲染、graphviz(py)、PDF 解析器自动发现 | 无 API 调用，纯离线；无需启动服务 |
| `verify_prune_callbacks.py` | Sprint-5/M2：litellm 回调去重裁剪单元证据（超上限 32 项 → 去重保留最近 N；`PAPERQA_LITELLM_CALLBACK_LIMIT` 可覆盖默认 20） | 无 API 调用，纯离线 |
| `verify_agentops.py` | Sprint-8/A-UC：AgentOps 账本 CLI 用例断言（UC-1/2/3/4/5/7/9/10 + 三查修正回归；隔离到临时 `AGENT_OPS_DIR`） | 无 API 调用，纯离线 |
| `verify_index_health.py` | Sprint-7/M1：索引一致性三重探测（files.zip / index/meta.json / tantivy 段）合成形态 + 真实构建后篡改 meta.json → 整目录重建自愈 | 无 API key、无远程 LLM 调用（manifest 提供 citation；本地 ST 权重从 HF 缓存加载，首次需联网下载）；索引隔离到临时 `PQA_HOME` |
| `verify_provider_switch.py` | 验证服务商切换（内置 4 家 + 自定义）：配置解析、密钥优先级、build_settings、**路由实证断言**（deepseek 真实 key 应 SUCCESS；dashscope/openai/openrouter/自定义 用占位 key 应拿到端点级拒绝=路由正确） | 联网；deepseek 真实 key（`.env` 或 `OPENAI_API_KEY`）；**真实 openrouter key 实测为用户资源门控**（占位 key 只证路由不证配额） |
| `verify_e2e.py` | 启动真实后端（8787）→ 全链路 6 步，校验答案长度并保存结构化结果到 `verify_e2e_result.json` | 需要 `OPENAI_API_KEY`（DeepSeek）+ 本地 st- 向量模型；联网 |
| `verify_e2e_openai.py` | Sprint-7 追加：**OpenAI 作为 provider + embedding**（gpt-4o-mini + text-embedding-3-large）全流程 + 同进程 deepseek→openai 切换（key 隔离回归） | 需要真实 `OPENAI_API_KEY`（**账户需有余额**）+ `DEEPSEEK_API_KEY`（Phase 2）；联网 |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | 同上，且索引 `verify_e2e_index` 已存在（e2e 先跑过） |
| `verify_embed_load.py` | parse_chunk_embed 三种模式：run（重跑）/load 同会话（秒级）/load 新会话（embed 缓存），校验 texts 数量一致 | 需要 `OPENAI_API_KEY`（DeepSeek）+ 本地 st- 向量模型 |
| `verify_remote_e2e.py` | remote 数据源全链路（Sprint-3）：config(remote+arXiv) → load_index（下载+索引）→ retrieve → parse → evidence → answer | 需要 `OPENAI_API_KEY`；联网（export.arxiv.org） |
| `eval_retrieve.py` | Sprint-6/F4：检索质量小样本评测（双语料 + 策略断言 + 负对照，报告 hit@1） | 需要 `OPENAI_API_KEY` + 本地 st- 向量模型 |
| `gui_check.mjs` | GUI 全链路：Playwright 打开前端 → 点 "Run All (Left-to-Right)" → 等待答案出现 → 截图 | 后端 8787 + 前端 5173 **已启动**；Playwright Chromium 已安装；`.env`/`OPENAI_API_KEY` 已配；`node verify\gui_check.mjs`（playwright 取前端 node_modules） |
| `gui_check_remote.mjs` | GUI 远程数据源（Sprint-3）：Config 面板切 remote + 填 arXiv ID → Run All → 答案出现 → 截图 `us3-remote.png` | 同 `gui_check.mjs` + 联网（export.arxiv.org） |
| `gui_check_s4.mjs` | Sprint-4：光标不跳末尾 + provider 下拉联动（openrouter/deepseek 自动带出） | 同 `gui_check.mjs` |
| `gui_check_s5.mjs` | Sprint-5：自动重跑 config、retrieve 双模式标记、计时冻结、复制报错按钮（7 项断言） | 同 `gui_check.mjs` |
| `gui_check_s7.mjs` | Sprint-7 M4：多节点并发计时显示（retrieve+evidence 并发 → `A X.Xs · B Y.Ys`）+ 完成后冻结 | 同 `gui_check.mjs` |
| `gui_check_dashboard.mjs` | Sprint-9：看板概览页截图（状态卡片/环形图/账本列表） | agents-dashboard 已启动（8600，生产模式）；Playwright Chromium 已安装 |
| `gui_check_dashboard2.mjs` | Sprint-9：看板 spec 编辑页截图 | 同 `gui_check_dashboard.mjs` |
| `gui_check_dashboard_costs.mjs` | Sprint-9：看板成本/上下文页截图（CNY 合计、pending 标注、上下文占用） | 同 `gui_check_dashboard.mjs` |
| `gui_check_dashboard_report.mjs` | Sprint-9：看板报告浏览页截图（run 详情 + 报告全文） | 同 `gui_check_dashboard.mjs` |

运行示例：

```powershell
$env:OPENAI_API_KEY = "<DeepSeek key>"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py
.\.venv\Scripts\python.exe .\verify\verify_prune_callbacks.py
.\.venv\Scripts\python.exe .\verify\verify_agentops.py           # AgentOps 账本 CLI 用例断言（离线）
.\.venv\Scripts\python.exe .\verify\verify_index_health.py
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py   # 联网
.\.venv\Scripts\python.exe .\verify\verify_e2e.py
.\.venv\Scripts\python.exe .\verify\verify_e2e_openai.py       # OpenAI provider+embedding 全流程（账户需余额）
.\.venv\Scripts\python.exe .\verify\verify_agent.py
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py       # Sprint-3 remote 全链路（联网）
node .\verify\gui_check.mjs          # GUI（需先启动前后端）
node .\verify\gui_check_remote.mjs   # GUI remote 数据源（需先启动前后端 + 联网）
node .\verify\gui_check_s7.mjs       # Sprint-7 M4 并发计时（需先启动前后端）
node .\verify\gui_check_dashboard.mjs         # Sprint-9 看板概览页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard2.mjs        # Sprint-9 看板 spec 页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_costs.mjs   # Sprint-9 看板成本页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_report.mjs  # Sprint-9 看板报告页截图（需 agents-dashboard 已启动）
```

已知差异：graphviz 已自动发现（冒烟第 7 项扫描常见安装目录）；仅当系统完全未安装 Graphviz 时才报 `ExecutableNotFound`（可选安装，见 `docs/3-LEARNED.MD` 验证记录）。
