# TEST-MATRIX.MD —— 覆盖矩阵（TG-2 SSOT，自动生成，勿手改）

> 唯一真源 = 各 verify 脚本头部的 `VERIFY_META`；本文件由 `verify_matrix.py derive` 生成，
> `verify_matrix.py check`（CI 离线套件）逐字节比对防漂移。手改本文件会被 check 拦下。

| 脚本 | 覆盖功能 | tier | providers | 预估时长 | 预估成本 | 路由 | 前置条件 |
|---|---|---|---|---|---|---|---|
| `eval_retrieve.py` | 检索质量小样本评测：双语料命中率 + hit@1 + 多语重试覆盖 | network | deepseek | 60s | ¥0.3 | /api/run_step | keys, network |
| `gui_check.mjs` | GUI 全链路：Run All 左到右 → 答案出现 → 截图 | gui | — | 120s | ¥0 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | playwright, servers |
| `gui_check_config_schema.mjs` | Config schema 清单/全字段表单截图 + 字段级校验 + defaults-derived-from-schema 断言 | gui | — | 60s | ¥0 | /api/config_schema, /api/config/validate | playwright, servers |
| `gui_check_dashboard.mjs` | 看板概览页 + spec 编辑页截图 | gui | — | 30s | ¥0 | — | playwright, dashboard |
| `gui_check_dashboard2.mjs` | 看板 spec 编辑器打开态截图 | gui | — | 20s | ¥0 | — | playwright, dashboard |
| `gui_check_dashboard_costs.mjs` | 看板成本/上下文页截图（CNY 合计/pending 标注） | gui | — | 30s | ¥0 | — | playwright, dashboard |
| `gui_check_dashboard_fanout.mjs` | 看板 fan-out 配置页截图（两条流水线+JSON 编辑器） | gui | — | 30s | ¥0 | — | playwright, dashboard |
| `gui_check_dashboard_report.mjs` | 看板报告浏览页截图（run 详情+报告全文） | gui | — | 30s | ¥0 | — | playwright, dashboard |
| `gui_check_remote.mjs` | GUI 远程数据源：remote+arXiv → Run All → 截图 | gui | — | 180s | ¥0 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | playwright, servers, network |
| `gui_check_s4.mjs` | 光标三断言（插入/位置/连续编辑）+ provider 联动四断言 | gui | — | 30s | ¥0 | — | playwright, servers |
| `gui_check_s5.mjs` | 自动重跑 config / retrieve 双模式标记 / 复制报错按钮 / 计时冻结 | gui | — | 40s | ¥0 | — | playwright, servers |
| `gui_check_s7.mjs` | 多节点并发计时显示 + 完成后冻结 | gui | — | 60s | ¥0 | — | playwright, servers |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | network | deepseek | 60s | ¥0.3 | /api/translate_preview, /api/run_step | keys, network, index |
| `verify_agentops.py` | AgentOps 账本 CLI 用例断言 UC-1~UC-12（离线；UC-11/12 为 M10 新增） | offline | — | 10s | ¥0 | — | none |
| `verify_config_schema.py` | 配置 SSOT 一致性 + M7 前端零硬编码 + Settings 升级基线护栏（114 断言，离线） | offline | — | 5s | ¥0 | /api/config_schema, /api/config/validate | none |
| `verify_e2e.py` | deepseek 全链路 6 步（LLM+vision + 本地 st- 向量） | network | deepseek | 120s | ¥0.3 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_e2e_dashscope.py` | dashscope 全链路 6 步 + 同进程 deepseek 切换隔离回归 | network | dashscope, deepseek | 150s | ¥0.5 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_e2e_openai.py` | OpenAI provider+embedding 全流程 + 同进程 deepseek→openai 切换隔离回归 | network | openai, deepseek | 150s | ¥1 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network, balance |
| `verify_embed_load.py` | parse_chunk_embed 三种模式：run/load 同会话/load 新会话（embed 缓存） | network | deepseek | 90s | ¥0.3 | /api/run_step | keys, network |
| `verify_index_health.py` | 索引一致性三重探针 + 损坏自愈（合成六形态，离线） | offline | — | 20s | ¥0 | — | none |
| `verify_provider_switch.py` | provider 切换路由实证：内置 4 家 + 自定义（端点级拒绝断言） | network | deepseek, dashscope, openai, openrouter | 30s | ¥0.1 | /api/providers | keys, network |
| `verify_prune_callbacks.py` | litellm 回调裁剪：上限 env 可配 + 非法值回落 + 钳制（离线） | offline | — | 2s | ¥0 | — | none |
| `verify_remote_e2e.py` | remote 数据源全链路（arXiv 下载+索引+6 步） | network | deepseek | 180s | ¥0.4 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_smoke.py` | 冒烟 8 项：paperqa 导入/后端 10 路由加载/runtime_trace 目标/PDF 解析等（离线） | offline | — | 10s | ¥0 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session, /api/health, /api/providers, /api/config_schema, /api/config/validate, /api/translate_preview | none |

共 24 个脚本：offline 5 / network 8 / gui 11。
