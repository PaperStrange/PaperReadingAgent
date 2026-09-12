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
| `gui_check_s15_bidi_link.mjs` | Sprint-15 F-AC9：subcanvas 手动切换节点 → 主画布联动选中并定位对应节点 | gui | — | 40s | ¥0 | — | playwright, servers |
| `gui_check_s15_collapse.mjs` | Sprint-15 F-AC4：节点运行完成后自动收起全部展开项，仅 output_snapshot 保持展开 | gui | — | 50s | ¥0 | /api/run_step | playwright, servers |
| `gui_check_s15_cursor.mjs` | Sprint-15 走查修复：真实键盘输入光标不跳（JSON 编辑区/表单输入）+ 无默认值字段（api_key）改动计数 | gui | — | 50s | ¥0 | /api/config/validate | playwright, servers |
| `gui_check_s15_error_copy.mjs` | Sprint-15 F-AC6：失败一键复制（主卡+fn 卡，含完整堆栈）+ fn 卡框选复制 + 主画布错误摘要可展开 + 多报错卡定位按钮显隐 + 走查七轮报错卡 zIndex 压顶与 fn_title 定位 + 走查八轮定位目标抬层 10001 高亮 | gui | — | 120s | ¥0 | /api/run_step | playwright, servers |
| `gui_check_s15_hints_title.mjs` | Sprint-15 F-AC2：hints 限高滚动 + 分组标题影响聚合（N项，M项被改动，M 标红） | gui | — | 45s | ¥0 | /api/config_schema, /api/config/validate | playwright, servers |
| `gui_check_s15_local_dir.mjs` | Sprint-15 F-AC3：local 模式显示论文目录并隐藏远程源三字段、remote 模式恢复；Index 组不再含论文目录 | gui | — | 45s | ¥0 | /api/config_schema | playwright, servers |
| `gui_check_s15_output_view.mjs` | Sprint-15 F-AC11：output 一键复制全文 + answer 节点答案全文展示（不截断） | network | deepseek | 300s | ¥0.4 | /api/run_step | keys, network, playwright, servers |
| `gui_check_s15_responsive.mjs` | Sprint-15 F-AC5：分栏自适应——1280/1366/1920 桌面宽度下无横向溢出、fn 卡片完整可见 | gui | — | 60s | ¥0 | /api/run_step | playwright, servers |
| `gui_check_s15_status_scope.mjs` | Sprint-15 F-AC7：步骤状态行仅展示当前查看节点的完成/失败文案（切换即更替，不残留他节点） | gui | — | 60s | ¥0 | /api/run_step | playwright, servers |
| `gui_check_s15_typography.mjs` | Sprint-15 F-AC1 排版统一断言：标题字号/字体族 token 一致性（node-title 13px、block 标题 12px、字体族统一） | gui | — | 40s | ¥0 | — | playwright, servers |
| `gui_check_s4.mjs` | 光标三断言（插入/位置/连续编辑）+ provider 联动四断言 | gui | — | 30s | ¥0 | — | playwright, servers |
| `gui_check_s5.mjs` | 自动重跑 config / retrieve 双模式标记 / 复制报错按钮 / 计时冻结 | gui | — | 40s | ¥0 | — | playwright, servers |
| `gui_check_s7.mjs` | 多节点并发计时显示 + 完成后冻结 | gui | — | 60s | ¥0 | — | playwright, servers |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | network | deepseek | 60s | ¥0.3 | /api/translate_preview, /api/run_step | keys, network, index |
| `verify_agentops.py` | AgentOps 账本 CLI 用例断言 UC-1~UC-13（离线；UC-11/12=M10，UC-13=M9） | offline | — | 10s | ¥0 | — | none |
| `verify_archive.py` | M16 调研归档完整性校验：report/context/reasoning/evidence 契约 + 证据索引表交叉引用（fail-closed） | offline | — | 5s | ¥0 | — |  |
| `verify_config_schema.py` | 配置 SSOT 一致性 + M7 前端零硬编码 + Settings 升级基线护栏（114 断言，离线） | offline | — | 5s | ¥0 | /api/config_schema, /api/config/validate | none |
| `verify_e2e.py` | deepseek 全链路 6 步（LLM+vision + 本地 st- 向量） | network | deepseek | 120s | ¥0.3 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_e2e_dashscope.py` | dashscope 全链路 6 步 + 同进程 deepseek 切换隔离回归 | network | dashscope, deepseek | 150s | ¥0.5 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_e2e_openai.py` | OpenAI provider+embedding 全流程 + 同进程 deepseek→openai 切换隔离回归 | network | openai, deepseek | 150s | ¥1 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network, balance |
| `verify_embed_load.py` | parse_chunk_embed 三种模式：run/load 同会话/load 新会话（embed 缓存） | network | deepseek | 90s | ¥0.3 | /api/run_step | keys, network |
| `verify_f12_preview_res.py` | F-AC12 预览清晰度实证：1.0 缩放渲染，PNG 宽度 ≥500px（旧 0.45 为 ~268px） | offline | — | 10s | ¥0 | — | none |
| `verify_index_health.py` | 索引一致性三重探针 + 损坏自愈（合成六形态，离线） | offline | — | 20s | ¥0 | — | none |
| `verify_local_dir.py` | F-AC3 引擎接线实证：临时目录 paper_directory → load_index → retrieve 候选来自该目录 | offline | — | 90s | ¥0 | /api/new_session, /api/run_step | self-boots-backend |
| `verify_provider_switch.py` | provider 切换路由实证：内置 4 家 + 自定义（端点级拒绝断言） | network | deepseek, dashscope, openai, openrouter | 30s | ¥0.1 | /api/providers | keys, network |
| `verify_prune_callbacks.py` | litellm 回调裁剪：上限 env 可配 + 非法值回落 + 钳制（离线） | offline | — | 2s | ¥0 | — | none |
| `verify_remote_e2e.py` | remote 数据源全链路（arXiv 下载+索引+6 步） | network | deepseek | 180s | ¥0.4 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session | keys, network |
| `verify_smoke.py` | 冒烟 8 项：paperqa 导入/后端 10 路由加载/runtime_trace 目标/PDF 解析等（离线） | offline | — | 10s | ¥0 | /api/new_session, /api/run_step, /api/stream/{session_id}/{run_id}, /api/session_records/{session_id}, /api/reset_session, /api/health, /api/providers, /api/config_schema, /api/config/validate, /api/translate_preview | none |

共 37 个脚本：offline 8 / network 9 / gui 20。
