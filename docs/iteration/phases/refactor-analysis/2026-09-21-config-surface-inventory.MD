# 运行参数配置面清单（F-AC15 输入材料，2026-09-21 UTC+8）

> 归属：`docs/iteration/phases/refactor-analysis/`（仅 windows 分支）。
> 来源：用户 2026-09-20 走查存疑 B-15（"深度阈值怎么是命令传参？不应该是前端显式配置吗？类似的还有哪些"）；用户 2026-09-21 要求"9 个 env + spec 阈值具体有哪些"。
> 用途：这是 `F-AC15`（运行参数显式配置面）的范围输入；**"建议归属"列待用户勾选**后再开卡实现。

## 0. 一句话现状

前端**只**暴露"引擎配置"（`GET /api/config_schema`，7 分组 **23** 字段）；**运行/运维/研究类参数（env 9 个 + spec 阈值 6 项 + 深度档表 + state 配置 + 一批 CLI 开关 + 若干硬编码常量）全部前端不可见**。

---

## 1. 前端已可见：引擎配置（7 分组 23 字段，SSOT = `app/config_schema.py`）

| 分组 | 字段 |
|---|---|
| LLM（6） | `provider`、`api_key`、`api_base`、`model`、`vision_model`、`temperature` |
| Embedding（2） | `embedding_model`、`embedding_batch_size` |
| Parsing（5） | `chunk_chars`、`chunk_overlap`、`recurse_subdirectories`、`use_doc_details`、`multimodal` |
| Agent（1） | `rebuild_index` |
| Answer（2） | `evidence_k`、`answer_length` |
| 数据源（6） | `data_source`、`paper_directory`、`source_urls`、`source_arxiv_ids`、`source_dois`、`manifest_file` |
| Index（1） | `index_name` |

## 2. env 参数（`PAPERQA_*`，共 9 个，其中 1 个是内部用）

| # | 变量 | 默认值 | 读取点 | 作用 | 建议归属（待你勾选） |
|---|---|---|---|---|---|
| 1 | `PAPERQA_PROVIDER` | `deepseek` | `paper-qa-script/provider_config.py:68` | 默认服务商（前端下拉可覆盖单次运行，但"默认值"本身只能改 env） | ☐ 前端可改（与 LLM 分组同屏） |
| 2 | `PAPERQA_PROVIDERS_JSON` | 空 | `provider_config.py:139/170` | 自定义 provider 注册（JSON 字符串，**合并优先级最高**） | ☐ 保持 CLI/env（含密钥，不宜入 UI） |
| 3 | `PAPERQA_PROVIDER_INTERVAL_DAYS` | `14` | `scripts/refresh-providers.py:454`（`DEFAULT_INTERVAL_DAYS=14`） | provider 官网调研刷新周期（口径①） | ☐ 前端可改（研究设置区） |
| 4 | `PAPERQA_NIGHTLY_BUDGET_CNY` | `10` | `verify/run_suite.py:49`、`scripts/scheduled-tasks.py:167` | 夜间套件单轮预算上限（口径②）；优先级 CLI > env > state.config | ☐ 前端可改（成本设置区） |
| 5 | `PAPERQA_SCHEDULE_STATE` | `agents/runtime/schedule.json` | `scheduled-tasks.py:97` | 调度状态文件路径 | ☐ 保持 CLI/env（部署细节） |
| 6 | `PAPERQA_SCHEDULE_<TASK>_DAYS`（如 `..._PROVIDERS_DAYS`） | prices `7` / nightly-suite `7` / providers `14` | `scheduled-tasks.py:154`（`TASKS[*].interval_days`） | 每任务运行间隔 | ☐ 前端可改（研究设置区，只读展示 + 可改） |
| 7 | `PAPERQA_LITELLM_CALLBACK_LIMIT` | `20`（钳制 ≤30） | `paper-qa-script/app/engine.py:31` | litellm 回调保留数（长期运行防 MAX_CALLBACKS 溢出） | ☐ 只读展示（排障用） |
| 8 | `PAPERQA_EMBED_RECOMMEND_LIVE` | `1`（=0 关闭） | `paper-qa-script/app/embedding_recommender.py:89` | embedding 推荐是否联网实测 | ☐ 前端可改（离线场景开关） |
| 9 | `PAPERQA_SUITE_METRICS` | 空 | `verify/run_suite.py:149`、`verify/e2e_common.py:165` | **内部**：套件→脚本的用量指标文件（run_suite 自动设置/清理） | ☐ 内部，不入 UI |

> 另有非 `PAPERQA_` 但同类的：API 密钥（`DEEPSEEK_API_KEY`/`DASHSCOPE_API_KEY`/`OPENAI_API_KEY`，来自 `paper-qa-script/.env`；前端 `api_key` 字段可覆盖）与 `HF_HUB_OFFLINE`（离线启动开关，运维用）。

## 3. spec / 路由参数（M16 调研工作流）

来源：`agents/functions/tech-research.md` 的 **Configurable Parameters 节**（spec 明示"只改这一节与档位表，不改正文规则"）+ `agents/fanout.json` 的 `depth` 路由。

| # | 参数 | 当前值 | 含义 | 建议归属 |
|---|---|---|---|---|
| 1 | `depth tiers` | 见下方档表 | 每档的来源数/维度阈值（P3：可调，正文不得写死） | ☐ 只读展示（报告里显示本次用了哪档） |
| 2 | `min_sources_per_claim` | `3` / `3` / `4`（quick/expert/scholar） | 达到才算"已确立"论断；不足标"弱证据" | ☐ 前端可改（研究设置区） |
| 3 | `source tiers` | tier1 官方文档 > tier2 权威论文/博客 > tier3 社区 | 引用须标层级，结论尽量落 tier1/2 | ☐ 保持 spec（文本规则） |
| 4 | `comparison dimensions` | 能力/成熟度/维护/生态/成本/风险（选 ≥3 并说明理由） | 对比矩阵维度 | ☐ 保持 spec（文本规则） |
| 5 | `timebox` | `30` / `45` / `90` min | 到点须写"目前覆盖"，不得静默截断 | ☐ 前端可改（研究设置区） |
| 6 | `archive validator` | `verify/verify_archive.py` | 归档完整性门禁路径 | ☐ 只读展示（指向脚本） |

**深度档表**：`quick` 3–5 源 / 1 维 / **主代理直执** / 归档仅 report；`expert` 6–10 源 / ≥3 维 / 子代理 / 全归档（默认档）；`scholar` ≥12 源 / 全 tradeoff（含反向证据）/ 子代理 / 全归档。

**路由**：`agents/fanout.json` 的 `planning_pipeline.depth`（档位由任务难度建议、**用户可覆盖**）与 `archive`（报告注入规划上下文前的门禁字段）。

## 4. state 文件配置（`agents/runtime/schedule.json`，gitignore）

| 键 | 默认 | 作用 | 建议归属 |
|---|---|---|---|
| `config.budget_cny` | `10.0` | 预算上限（env/CLI 可覆盖） | ☐ 前端可改（与 #4 同屏，显示"当前生效值 + 来源优先级"） |
| `config.interval_days.<task>` | 空（回落任务默认） | 每任务间隔覆盖 | ☐ 前端可改 |

## 5. 纯 CLI / PowerShell 开关（无 env 等价物）

| 工具 | 开关 | 作用 | 建议归属 |
|---|---|---|---|
| `verify/run_suite.py` | `--tier`、`--budget-cny`、`--verify-dir`、`--scripts`、`--json`、`--dry-run` | 分层执行/预算/筛选/结果落盘 | ☐ 只读展示（把"上次套件结果"可视化）+ `--dry-run` 按钮（可选） |
| `scripts/scheduled-tasks.py` | `--list`、`--task`、`--check-due`、`--force`、`--state`、`--dry-run`、`--record-cost` | 调度查询/放行/回填 | ☐ 前端"研究设置区"做只读展示 + `--record-cost` 回填入口（可选） |
| `scripts/refresh-providers.py` | `--fetch`、`--from-file`、`--check`、`--migrate`、`--apply`、`--accept provider:field=value`、`--interval-days`、`--provider` | provider 调研刷新与决策采纳 | ☐ 只读展示 proposal（哪些字段待确认）+ 采纳按钮（可选，需二次确认） |
| `scripts/fetch-prices.py` | `--check`、`--apply` | 价表抓取 | ☐ 只读展示 `scraped_at` 与覆盖模型数 |
| `scripts/register-scheduled-tasks.ps1` | `-Action register/query/unregister` | Windows 任务计划注册（口径①：需人工） | ☐ 保持 CLI（明确"不自动注册"） |
| `verify/verify_archive.py` | `--depth`、`--selftest` | 归档门禁 | ☐ 只读展示（最近一次门禁结果） |

## 6. 硬编码常量（**连 env 都没有** —— P3"阈值不写死"的漏网之鱼）

| 常量 | 值 | 位置 | 说明 | 建议 |
|---|---|---|---|---|
| checkpoint 命名空间保留数 | `20` | `app/orchestration.py:205`（`_CHECKPOINT_NAMESPACE_KEEP`） | 超出即按 mtime 收敛旧命名空间 | ☐ 建议入配置（env/前端只读） |
| checkpoint 收敛宽限期 | `86400.0` s | `app/orchestration.py:209`（`grace_s` 默认） | 防并发误删 | ☐ 建议入配置 |
| provider 抓取响应体上限 | `3 * 1024 * 1024` | `scripts/refresh-providers.py:48`（`MAX_BYTES`） | 防超大响应 | ☐ 保持常量（安全护栏） |
| provider 抓取 SSRF 白名单 | 硬编码域名表 | `refresh-providers.py` 同文件 | 只允许官方域名 + 逐跳复检 | ☐ 保持常量（安全护栏） |
| 复制按钮反馈时长 | `1500` ms | `frontend/src/FlowNode.jsx:53` | 已复制提示时长 | ☐ 保持常量（UI 细节） |
| 用量稳定等待 | quiet `0.6` s / max `5` s | `verify/e2e_common.py`（Retro③） | 覆盖回调异步落地 | ☐ 保持常量（验证内部） |
| 各脚本 `est_seconds` / `est_cost_cny` | 见 `verify/TEST-MATRIX.MD` | 各脚本 `VERIFY_META` | 预算闸门预检上界 | ☐ 保持脚本内（SSOT 在矩阵） |

## 7. 建议的 v1 分区（供你勾选后开卡）

- **A. 研究设置区（可改）**：调研深度阈值（`min_sources_per_claim`、`timebox`、默认档位）、provider 刷新周期、套件预算与三任务间隔 —— 对应上表 #3/#4/#6 + spec #2/#5。
- **B. 成本与用量（只读）**：当前预算上限与来源优先级、上次套件实测成本（`verify/suite_result.json`）、`/api/usage` 进程累计 —— 复用 Retro③ 已落地的数据。
- **C. 数据源与决策（只读 + 可选动作）**：provider proposal 待确认字段、`prices.json` 抓取时间与覆盖、最近一次归档门禁结果。
- **D. 保持 CLI**：密钥类、SSRF 白名单、任务计划注册（口径①）、内部指标文件路径。
