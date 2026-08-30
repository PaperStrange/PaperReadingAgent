# AgentOps 架构地基设计（阶段 1 产出，完成）

> 归属：`docs/iteration/phases/agents-infra/`（仅 windows 分支）。
> 状态：**阶段 1 完成**——§1 现状约束、§2 五条调研线结论、§3 架构设计、§4 已确认决策、§5 待决策、§6 交付物、§7 用例表。**阶段 2（Sprint-8）进行中**（US-8.1~8.5 DONE，三查收尾）。

## 1. 现状与约束（已核实）

### 1.1 编排方（本会话 DSH）能做什么

- 子代理工具：`subagent` / `subagent_fork`（后台默认、durable id、`send_message` 续聊同会话）、`workflow`（脚本化大规模 fan-out）、`ralph`（fresh-agent 迭代）、`list_agents`（children/descendants 三态：running/idle/ready）。
- **没有**子代理 token/上下文/成本的读取 API；状态只有三态；子代理内部对话流不对外暴露。
- 会话 skill 目录通过 `skill` 工具按名加载，**本会话无法注册新 skill** → 项目级 spec 文件（仓库内、版本化）是唯一可移植的"skill"载体。

### 1.2 已发生的实践（Sprint-7 实测）

- 三查 fan-out 3 子代理并行（code-review-windows / code-review-main / doc-audit）成功；prompt 每次临时编写 → **漂移根源，需固化 spec**。
- 环境核验（起服务/端口/回归）由主代理执行（避免 3-LEARNED 1.11 批量杀进程风险）——用户已确认保留在主代理。
- 多子代理并行开发约束：共享工作区与 git index → 采用**模式 A（子代理只改不相交文件集、不 commit；主代理统一 review/commit/回归）**，用户已确认；Sprint 文档需新增**文件所有权地图**。
- 文件交集风险：M1/M2/M4/M5 实测落在不相交文件（orchestration/engine/App.jsx/verify），可并行；有交集的卡需拆分或串行。

### 1.3 目标能力（用户要求）

- 看板展示：子代理配置文件、任务 runtime 状态、自报上下文占用、估算消费额度、memory 报告浏览、跨 IDE 迁移说明。
- 看板编辑：手动改子代理 prompt；指定 GitHub 上现有 skill.md（raw URL 拉取 + 本地回退）。
- 未来：新增更多 agent；paper-qa workflow 可引用这里的 agent 能力。

## 2. 调研结论

| 调研线 | 子代理 | 状态 |
|---|---|---|
| 多代理编排框架的 agent 定义/编排/可观测模式 | `230a3c0f` | ✅ 已返回（见 §2.3） |
| skill/spec 文件约定（SKILL.md、AGENTS.md、子代理定义） | `d89be0c2` | ✅ 已返回（见 §2.4） |
| LLM 可观测与成本估算（数据模型、单价估算） | `06b68f0f` | ✅ 已返回（见 §2.1） |
| 本地看板技术栈（Next.js+MongoDB vs 轻量替代） | `70891874` | ✅ 已返回（见 §2.2） |
| 职能/能力划分（用户意见①补充调研） | `e0d54678` | ✅ 已返回（见 §2.5） |

### 2.5 职能划分结论（子代理 e0d54678，用户意见①）

- **业界共识：按职能（角色/能力）划分，不按目标对象（分支）划分**——用户的直觉与主流一致。
- Anthropic 多代理研究系统：Lead（只编排）+ Researcher/Data Analyst/Report Writer，粒度 = "一个职能 = 一个产出物 + 一套专属工具"；命名动名词（-er）。
- Claude Code 官方：subagent 应"单一、定义清晰的任务"（narrowly scoped）。
- SKILL.md 粒度哲学：**skill = 窄而深的一项可复用过程能力；职能（spec）= 角色，skill = 任务**，一职能引用多 skill。
- **CodeRabbit**：一个 `code-reviewer` 职能，内部 安全/质量/最佳实践/性能/bug 五维度 = "职能内部任务"——直接印证"一职能多任务"；评审 agent 不按分支/语言拆，分支只是输入参数。
- **OpenHands microagents 三层模型（最贴合）**：knowledge（关键词触发窄能力）/ task（多步闭环工作流）/ repository（repo.md 常驻 = 目标对象参数）——**把"分支"下沉为 task 输入，而非职能维度**。
- MetaGPT/CrewAI：角色=职能（PM/架构师/QA），一个 agent 一个职责、避免重叠。

**采纳**（§3.1）：职能清单起步 3 个 `code-review` / `doc-audit` / `workspace-check`（主代理手册），**后增 `impact-assessment`（用户问题①，fan-out 闸门）共 4 职能**；预留 `test-audit` / `security-review` / `api-contract-review`；任务参数化 `{target 分支/PR, focus 维度, strictness}`；文件关系 = 职能 spec 一职能一文件（`agents/functions/<fn>.md`），任务 skill 按需窄化拆分（先内置为职能 spec 的维度清单）。

### 2.1 可观测性与成本追踪结论（子代理 06b68f0f）

- **Langfuse**（~11k★，self-host）：`Trace→Observation(span/generation/event)` 三级；generation 字段含 usage{input,output,total}、costDetails、prompt(name+version)、tags、sessionId——**usage 与 cost 均可自报**（或只报 usage 由价表算）。单机单 Postgres 可跑。
- **LangSmith**（商业）：run 树（llm/chain/tool/retriever），token usage 自报或回传，企业版才私有化 → 不适合我们。
- **Helicone**（~4k★）：代理层方案，需改 base_url 拦截 → 不适合"无计费 API"场景。
- **OpenTelemetry GenAI SemConv**（标准）：span 属性命名 `gen_ai.usage.input_tokens/output_tokens/cache_read_input_tokens/cache_creation_input_tokens`、`gen_ai.request.model`——**不含 cost**，命名规范可抄。
- **Phoenix/Arize**（~8k★）：默认 SQLite、上传 token 数由内置价表算 cost——本地单机最轻。
- **LiteLLM**（~15k★）：公开价表 `model_prices_and_context_window.json`（input/output/cache_read 单价、max_input_tokens）——**可复用的事实价表来源**。
- **计费 API 用法字段**：OpenAI `usage.prompt_tokens/completion_tokens/total_tokens(+cached_tokens)`；Anthropic `input/output + cache_creation/cache_read`（write≈1.25×、read≈0.1×）；无 token 时近似 `tokens ≈ chars/4`（中英混合 /3.5）。

**采纳到 §3 的要点**：① Langfuse 的 usage/cost 双轨（自报 + 价表计算）；② OTel SemConv 属性命名（cache 分列）；③ LiteLLM 价表 JSON 作为价格事实源。

### 2.2 本地看板技术栈结论（子代理 70891874）

- 对比结论：Next.js + MongoDB 在"本地单人、文件账本为源、检索为主"场景**偏重**——mongod 常驻服务（200MB+、端口/安全配置）、MongoDB 全文检索一般、需文件→库同步层；Atlas 需联网；MongoMemoryServer 仅测试不持久。
- **推荐：Next.js App Router + TailwindCSS + shadcn/ui + SQLite（better-sqlite3 + Drizzle）+ chokidar 文件监听**：
  1. Next.js 单进程承载 UI+API+Server Actions，免两套进程与 CORS；
  2. SQLite 单文件零运维、读更快、FTS5 全文检索够用（Drizzle 类型安全 ORM）——**弃 MongoDB**；
  3. **文件为真相源、SQLite 为派生只读索引**（chokidar 监听 registry.json/markdown 变更 → 增量 upsert；编辑 spec 直写文件）；
  4. UI 复用 shadcn-admin（satnaing/shadcn-admin，Vite 版布局范式）+ Tremor/Recharts（成本/状态图）+ TanStack Table（账本列表）。
- 退档方案：Vite+React+Express+SQLite（shadcn-admin 原栈）；Docusaurus 仅作 memory 报告浏览辅助。

**⚠️ 与用户原倾向（Next.js+MongoDB）的差异**：建议 MongoDB→SQLite，理由如上；**已获用户确认采纳（2026-08-30，D6 更新）**。

### 2.3 多代理编排框架结论（子代理 230a3c0f）

覆盖 LangGraph(~2万★)/CrewAI(~3.4万★)/AutoGen(~4万★)/OpenAI Agents SDK(~1.2万★)/Claude Agent SDK(~1万★)/PydanticAI/smolagents/Letta。

**该抄**：
1. **Agent 定义 = 声明式 spec**（CrewAI YAML / Claude Code subagent 配置）：name/role/prompt/tools/model，prompt 外置文件与代码分离；
2. **账本数据模型 = session→span→{token,cost,status} 三级**（OpenAI Agents SDK 内置账本最贴合）+ **hooks 生命周期回调做自动登记**（Claude hooks）→ 即我们的 `agent-ops register/finish`；
3. **fan-out = 类型化结果 + 并行**（LangGraph `Send` 动态并行、Pydantic `output_type`/`result_type` 强制 schema）→ 我们的统一报告模板（critical/major/minor/nit）。

**不抄**：LangGraph StateGraph/checkpointer、AutoGen 类型化消息总线、CrewAI/Letta 长期记忆层、各 SaaS dashboard——我们是短暂并行只读审计，不需要工作流引擎与长期记忆。

**结论**：四段流水（定义→编排→记账→看板）的最省力组合 = **声明式 spec + 结构化结果 + 并行 fan-out + SQLite 账本 + hooks 自动登记 + React 读表**，零重型框架依赖。

### 2.4 skill/spec 文件约定结论（子代理 d89be0c2）

- **SKILL.md 是事实标准**（anthropics/skills 172k★；obra/superpowers 280k★）：`<name>/SKILL.md`，name=目录名（hyphen-case），frontmatter 必填 name/description；
- **Claude Code 子代理**（143k★）：`.claude/agents/*.md`，frontmatter `name/description/tools/model`（+color/hooks）——"一文件=一子代理 prompt"最贴合；
- OpenHands（86k★）唯一带 `version`+`inputs` 参数 schema；Cursor Rules 的 globs/alwaysApply 可参考；
- **业界无内置"远程拉取 skill"标准** → raw URL 引用需自研：frontmatter 加 `source` 块 `{url, ref(commit/tag 锁定), sha256(校验), fallback(本地路径)}`——锁 ref + 验 hash，失败回退本地并告警（D5 的实现细节）。

**采纳到 §3.1**：frontmatter 超集 = 必填 `name`(=文件名)+`description`("何时用+做什么")；推荐 `tools/version/model`；可选 `metadata/globs/triggers/license`；body 按 角色→触发→步骤→输出模板→禁止 组织；`source` 块实现远程引用。




## 3. 架构设计（合成完毕，待用户评审）

### 3.1 agent 定义格式（依据 §2.3/§2.4/§2.5 定稿，Sprint-8 US-8.1）

**划分原则（用户意见① + §2.5 调研）**：按**职能**划分，不按分支——"团队中一个角色的一个闭环工作流 = 一个职能"；一个职能执行多个任务；任务 = skill（窄而深）或直接是职能 spec 内的维度清单；**分支/PR 下沉为任务参数（target）**。

**职能清单（定稿 4 个）**：`impact-assessment`（fan-out 闸门，子代理）、`code-review`、`doc-audit`、`workspace-check`（主代理手册，不子代理化）；预留 `test-audit` / `security-review` / `api-contract-review`。

**任务参数（每次执行的任务输入）**：
```json
{"target": "branch:windows | branch:main | pr:<n> | working-tree",
 "focus": ["<以各职能 spec 的 focus 枚举为准>"],  // code-review: correctness/security/ssot/compat/architecture/tech-debt；doc-audit: links/stale-facts/contradictions/algorithm-drift/tables/knowledge；空=全维度
 "strictness": "normal | strict"}
```

文件：`agents/functions/<fn>.md`（阶段 2 起步；未来任务窄化可拆 `<fn>/<task>.SKILL.md`）。

```markdown
---
name: code-review                    # 必填，= 文件名
description: 何时用 + 做什么（一句话，供自动委派/看板展示）
version: "1.0.0"                     # 推荐（OpenHands 范式；改 prompt 必升版本）
model: ""                            # 推荐；空 = 编排方默认
tools: []                            # 推荐；白名单收紧权限（Claude Code 范式）
metadata: {}                         # 可选：tags/owner/estimated_cost
# 远程 skill 引用（D5，自研；无则整块省略）：
source:
  url: https://raw.githubusercontent.com/.../SKILL.md
  ref: <commit|tag>                  # 锁定版本
  sha256: <hex>                      # 校验；不符则告警
  fallback: <本地 spec 路径>          # 拉取失败/校验失败回退
---

# 角色
# 触发（何时用）
# 任务输入（target/focus/strictness 参数说明）
# 步骤（检查清单，含默认维度）
# 输出模板（critical/major/minor/nit + 文件:行 + 建议修法 + 是否本轮必修）
# 禁止（只报真实问题等）
```

- body = 可直接粘贴给子代理的完整 prompt（D1）；spec 变更必须升 `version`，账本记录 `spec_source: name@version`。

### 3.2 账本数据模型（草稿，来源：调研线 3 推荐 + D4 自报估算口径）

`agents/runtime/registry.json`（数组，一条 = 一次子代理 run）：

```json
{
  "run_id": "uuid",
  "task_id": "branch:windows | branch:main | pr:<n> | working-tree",  // 分支/PR 走 task_id
  "role": "code-review | doc-audit | workspace-check | ...",          // 职能名（非分支）
  "spec_source": "spec名@version（或 github raw URL）",
  "model": "str",
  "status": "queued|running|succeeded|failed|cancelled",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "input_chars": 0,
  "output_chars": 0,
  "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0},
  "context_occupancy": {"input_tokens": 0, "max_context": 0, "ratio": 0.0},
  "cost_est": {"total": 0, "currency": "CNY", "estimated": false, "pending_price": false},
  "result_files": ["runs/<run_id>/<role>.report.md"],
  "tags": {},
  "error": "str"
}
```

- 估算公式：`cost = input×P_in + output×P_out + cache_read×P_cr + cache_write×P_cw`；P 取自本地价表（由 LiteLLM `model_prices_and_context_window.json` 派生精简版，入库 `agents/runtime/prices.json`，可人工覆盖）；
- 无 token 上报时 `tokens ≈ chars/4`（中英混合 /3.5）并打 `estimated=true`；
- 上下文占用展示 = `input_tokens / max_context`（工具结果与 memory 计入 input 后膨胀自然可见）；
- 命名对齐 OTel GenAI SemConv（usage 四列含 cache 分列）。

### 3.3 fan-out 协议与分诊闭环（草稿，来源：Sprint-7 实测 + 1-WORKFLOW §4.2/§4.4）

**触发分级**：
| 场景 | 子代理组合 | 说明 |
|---|---|---|
| Sprint 关闭三查 | **impact-assessment ×1（先）** → `code-review` 职能 × 2 任务（target=branch:windows、branch:main）+ `doc-audit` 职能 × 1 任务（scope=recommended_scope），并行 | 环境核验留主代理（D2）；**范围不得默认收窄到 Sprint 交付物**（§8 用户问题①） |
| Bug/日常维护（≤2h 直接修） | impact-assessment 快速版（主代理自查）→ 1 个 `code-review` 任务 | 避免小事大动干戈 |
| 并行开发（模式 A） | 每张不相交卡 1 个实现子代理 | 前置：Sprint 文档含**文件所有权地图**，无交集才并行 |

**输入**：spec 文件（本地或 github raw 拉取，D5）+ 本轮上下文（分支/commit/工作区 diff 范围、评审重点）。
**输出模板（所有评审代理统一）**：分级问题清单 `critical/major/minor/nit`（每条 = 文件:行 + 问题 + 建议修法 + 是否本轮必修）+ main 代理附同步文件清单 + 一句话总结。
**分诊闭环**：主代理按 `1-WORKFLOW.MD` §4.4 分诊——必修 → 立即修 + 回归；建议修 → 回流 backlog 卡；pre-existing → 新卡登记；结论写入 Sprint 文档 §9（三查记录）。
**账本**：`scripts/agent-ops.py` 8 子命令（register/update/finish/list/validate-spec/fetch-spec/parse-report/prices-derive）落 `agents/runtime/registry.json` + `runs/<run_id>/<role>.report.md`（子代理报告的原文存档 = memory 浏览入口）。

### 3.4 看板技术栈与数据层（依据 §2.2；**D6 已确认 SQLite**）

推荐：Next.js App Router + Tailwind + shadcn/ui + **SQLite**（better-sqlite3 + Drizzle + FTS5）+ chokidar 文件监听；文件为真相源、SQLite 为派生只读索引；编辑 spec 直写文件。UI 复用 shadcn-admin 范式 + Tremor/Recharts 成本图 + TanStack Table 账本列表。

### 3.5 paper-qa workflow 引用 agent 能力的接缝（草稿）

- **原则**：agent-ops 不与 paper-qa pipeline 耦合，暴露为**文件 + CLI/HTTP 契约**：`agent-ops run <role> --context <json|file>`；任何编排方（DSH 子代理、CI、IDE 规则、未来 paper-qa workflow）都能调用，spec/账本格式不写死任何具体 harness。
- **未来接法**（阶段 3 后评估）：① paper-qa 编排层把"评审/审计"作为特殊 Step 调用 agent-ops CLI（结果结构化进现有 `app/events` 事件模型）；② Sprint 文档声明式触发（sprint 文档的 三查 节 → agent-ops 清单）。
- **当前不实现**，仅保证数据模型兼容（registry 字段含 `task_id`、`role`、`result_files`，可被任何下游消费）。

## 4. 已确认决策

| # | 决策 | 来源 |
|---|---|---|
| D1 | spec 粒度 = 完整可粘贴 prompt（含输出模板、禁止事项） | 用户确认 2026-08-30 |
| D2 | 环境核验留在主代理，不子代理化 | 用户确认 2026-08-30 |
| D3 | 并行开发模式 A：改文件不 commit，主代理集成 | 用户确认 2026-08-30 |
| D4 | 指标口径 = 自报 + 按模型公开价估算（标注"估算"） | 用户确认 2026-08-30 |
| D5 | skill 来源 = GitHub raw URL 拉取 + 本地 spec 回退 | 用户确认 2026-08-30 |
| D6 | 看板 = 独立轻量应用（新端口），简约互联网风；后端 **Next.js + SQLite（better-sqlite3+Drizzle+FTS5）+ chokidar 文件监听**（用户采纳调研建议，由 MongoDB 改为 SQLite；文件为真相源、库为派生索引） | 用户确认 2026-08-30（原倾向 MongoDB，调研后改） |
| D7 | 三阶段：① 调研+架构 ② 四代理 spec/账本/跨 IDE ③ 看板 | 用户确认 2026-08-30 |

## 5. 待决策/讨论点（阶段 1 评审提交项）

- ~~P1（核心）：数据层 MongoDB → SQLite~~ → **已确认采纳 SQLite（2026-08-30），D6 已更新**。
- P2：看板端口与启动脚本（沿用 scripts/start-*.ps1 模式，建议端口 8600）。**环境已核实：8600 FREE；Node v23.10.0 / npm 10.9.2（Next.js 15 要求 Node≥18.18 ✓）**。
- P3：registry.json 为唯一账本源（文件权威），SQLite 仅为派生索引——看板编辑 spec 直写文件、账本记录只经 agent-ops CLI 追加（避免双写）。默认按此执行，无异议即定。
- ~~P4：用户要求先对阶段 1 设计提修改意见~~ → **已解决（2026-08-30）**：三条修改意见（①职能划分 ②用例表 ③Sprint 化）已全部落实并进入阶段 2（Sprint-8）。

### 5.1 阶段 3 技术风险预研（本轮已实测，附证据）

- **better-sqlite3 原生模块**：在 Node v23.10.0 上 `npm install better-sqlite3@13.0.3`（prebuilt，3s 装完）+ FTS5 实测（word/phrase/AND 查询均命中）→ **风险清除**；`engines: node>=22` 与本机匹配。
- **价表来源**：litellm 1.76.1 在 venv 内捆绑 `model_prices_and_context_window_backup.json`（1533 个模型，可离线读取）——`gpt-4o-mini`、`text-embedding-3-large` 有完整单价（in/out/cache）；**deepseek 系列 / qwen-omni-turbo / text-embedding-v4 / openrouter/auto 无条目** → `prices.json` 需人工覆盖段（由服务商页面填入），派生脚本只自动提取有单价的模型。

## 6. 阶段交付物清单与验收标准

### 阶段 2（职能化 spec/账本/跨 IDE，Sprint-8）

| 交付物 | 位置 | 验收标准 |
|---|---|---|
| 职能 spec（**按职能划分，用户意见①**：职能清单由 A-FN 调研定稿；如 code-review 职能以分支为任务参数，doc-audit 职能，workspace-check 为主代理手册） | `agents/functions/*.md` | frontmatter 超集 + body 五段式（角色/触发/步骤/输出模板/禁止）；可直接粘贴执行；同一职能可对多个任务参数执行 |
| 账本 CLI | `scripts/agent-ops.py` | **8 子命令**（register/update/finish/list/validate-spec/fetch-spec/parse-report/prices-derive）；落 `agents/runtime/registry.json`（§3.2 字段，含 task 参数）+ `runs/<run_id>/<role>.report.md` |
| 价表 | `agents/runtime/prices.json` | 由 LiteLLM 价表派生精简版（本项目用到的模型），可人工覆盖 |
| 用例表 | `architecture.MD` §7（A-UC） | ≥10 条"调研结论→可测断言"用例，Sprint 开发逐条验证 |
| 跨 IDE 迁移说明 | `agents/README.md` | spec 如何在 DSH/Cursor/Claude Code/CI 引用；账本脚本任意 terminal 可用；source 块远程引用流程 |
| 实战验证 | 下一次三查 | 按 §3.3 触发分级执行：职能 fan-out + 账本登记 + 分诊闭环，结果写入 Sprint §9 |

### 阶段 3（本地看板）

| 交付物 | 位置 | 验收标准 |
|---|---|---|
| 看板应用 | `agents-dashboard/`（Next.js App Router + Tailwind + shadcn/ui + better-sqlite3/Drizzle/FTS5 + chokidar） | 端口 8600；`scripts/start-agents-dashboard.ps1` 一键启动 |
| 页面 | ① 概览（任务 runtime 状态）② 账本列表（检索/过滤/聚合，TanStack Table）③ spec 编辑（直写文件）④ skill URL 配置（source 块编辑）⑤ 成本/上下文（Tremor/Recharts，自报+估算标注）⑥ memory 报告浏览 | 每页有对应 CRUD/检索交互；数据来自文件真相源 + SQLite 派生索引 |
| 验收演示 | 一次真实 fan-out | 看板完整呈现该次 fan-out 的 状态/自报上下文/估算成本/报告浏览 + spec 在线编辑生效 |

## 7. 调研结论→用例表（A-UC，用户意见②：Sprint 开发时逐条验证实现遵循调研结论）

> 每条用例 = 调研出处 + 可测断言 + 验证方式；验证方式标注 所属 US / 阶段（S8=本 Sprint，S9=看板 Sprint）。

| ID | 用例（可测断言） | 调研出处 | 验证方式 |
|---|---|---|---|
| UC-1 | `agents/functions/*.md` frontmatter 必填 `name`(=文件名)+`description`+`version` 且 name 唯一 | §2.4 SKILL.md/Claude subagents | `agent-ops validate-spec`（US-8.3/S8） |
| UC-2 | `source` 块含 `url+ref+sha256+fallback`；模拟拉取失败/校验不符 → 回退本地并告警 | §2.4 自研远程引用 + D5 | `agent-ops fetch-spec --offline` 断言（US-8.3/S8） |
| UC-3 | registry 条目含 §3.2 全部字段；状态机 queued→running→succeeded/failed/cancelled 合法流转，非法流转被拒 | §2.1 Langfuse / §2.3 账本模型 | CLI 往返测试（US-8.4/S8） |
| UC-4 | 成本估算 = usage×prices.json 单价（含 cache 分列）；无 usage 时 `chars/4` 兜底且 `estimated=true` | §2.1 LiteLLM 价表/双轨 | 给定输入输出断言计算值（US-8.4/S8） |
| UC-5 | 报告解析器能从 spec 输出模板解析出 critical/major/minor/nit 条目（文件:行+建议+必修标记） | §2.3 类型化结果（Pydantic output_type） | 样例报告解析断言（US-8.4/S8） |
| UC-6 | 同一 code-review 职能以 `task=branch:windows|main` 参数执行两次 → 两份报告 + 账本两条记录（task 区分） | §2.3 Send 并行 / 用户意见①职能化 | 真实 fan-out（S9 验收演示；S8 先以 dry-run 断言） |
| UC-7 | registry.json 为唯一账本源：记录只能经 agent-ops CLI 追加，看板/脚本直改会被校验拒绝（防双写） | §2.2 文件为源 / §2.3 账本模型 | CLI 追加 + 校验命令（US-8.4/S8；看板 S9） |
| UC-8 | SQLite 派生索引与文件源一致：registry.json 变更后（chokidar）库内检索结果更新 | §2.2 文件为源、库为索引 | S9 看板集成测试 |
| UC-9 | context_occupancy{input_tokens,max_context,ratio} 与 cost_est 在 finish 时可自报并可人工覆盖 | §2.1 自报+估算口径（D4） | CLI finish 参数断言（US-8.4/S8） |
| UC-10 | prices.json 含自动提取条目（gpt-4o-mini、text-embedding-3-large 完整单价）+ 人工覆盖段（deepseek/qwen/openrouter 可空，估算标 `pending_price`） | §2.1/§5.1 价表预研 | 派生脚本 + 断言（US-8.4/S8） |
| UC-11 | agent-ops CLI 纯 Python 标准库可跑（不依赖 DSH/仓库外工具）；spec 为纯 markdown | §3.5 CLI 契约 / 跨 IDE 需求 | 干净环境冒烟（US-8.5/S8） |
| UC-12 | 三查 fan-out = 职能级（code-review 跑 windows+main 两任务、doc-audit 一任务）且环境核验留主代理 | §3.3 触发分级 + D2 | Sprint-8 三查实操（US-8.6/S8） |
| UC-13 | 三查范围由 **impact-assessment 职能**输出确定（不得默认收窄到 Sprint 交付物）；复合指标 composite=(0.8A+0.2B)×100 阈值 X=50 → 全量档/窄档两档决策，与预计算 ground truth 一致 | §8（用户问题① + 复合指标细化） | 双例子代理验证（本次）+ 下一次三查实操 |

## 8. 影响范围评估与量化指标（用户问题①，2026-08-30）

### 8.1 规则修正

**审查范围不得默认收窄到"Sprint 交付物"**（Sprint-8 时间盒重试属临时处置，不是规则）。三查前必须先由 **impact-assessment 职能（新子代理）** 评估本次 Sprint/变更的影响范围，再据其输出确定 code-review/doc-audit 的审查范围（文件/模块清单）。

### 8.2 量化指标：方案对比与选择（用户细化 → 复合指标，2026-08-30）

| 方案 | 定义 | 计算 | 优点 | 缺点 |
|---|---|---|---|---|
| **A 核心功能覆盖率** | 触达的核心功能数 / 11 项核心功能清单（**v1.2.1 起 12 项**：增 #12 AgentOps 看板） | 模块→功能映射表 | 与"项目核心功能"直接对齐；可审计 | 清单需维护（每季度复核一次） |
| **B 核心 API 覆盖率** | 触达的 API 路由数 / 8 | 路由↔宿主模块映射表 | 最易算、零歧义 | 只覆盖后端路由 |
| C 风险加权文件覆盖率 | Σ(受审文件权重) / Σ(核心文件权重) | 权重表 | 细粒度 | 权重主观、难复现 |
| D 回归证据覆盖率 | 本轮回归脚本数 / 受影响模块关联脚本数 | 模块↔verify 映射 | 直接对验收充分性 | 度量对象不同（验证充分性） |

**最终选择（用户细化）：A 与 B 复合，权重 8:2**——`composite = (0.8×A + 0.2×B) × 100`（A、B 均为 [0,1] 比率，加权和即归一化百分比）；D 作为回归充分性辅助检查；C 弃用。

**两档范围规则（阈值 X=50，用户确认）**：
- `composite > 50` → **全量档**：审查范围 = **整个代码库**；
- `composite ≤ 50` → **窄档**：审查范围 = **Sprint 修改文件 ∪ 核心文件区域**（核心文件区域恒全部包含，用户确认——小改动也始终对照"皇冠明珠"区域审查）。

合理性自检（X=50）：A=7/11 仅 A 即 50.9 → 全量（改 7 项核心功能理应全库审查）；A=4/11、B=2/8 → 34.1 → 窄档。边界与直觉一致。

### 8.3 落地

- 职能 spec v1.2.1：`agents/functions/impact-assessment.md`（12 项核心功能 + 8 条路由↔宿主映射 + 复合公式 + 两档规则 + 核心文件区域清单（代码区/文档区）+ 输出模板含 A/B/composite/tier/recommended_scope；v1.2.1 增 #12 AgentOps 看板并重定位 reactflow 宿主路径）；
- fan-out 顺序：**impact-assessment（先）→ 按 recommended_scope 执行 code-review ×2 + doc-audit → workspace-check（主代理）**；范围默认取 recommended_scope，偏离需在 Sprint §9 记录理由；
- code-review/doc-audit spec 的"范围限定"段引用 impact-assessment 输出（task 输入含 `scope` 字段）；
- **验证方式（双例，用户确认）**：两组合成变更集跑真实子代理，对比预计算 ground truth（高影响例 → 期望全量档；低影响例 → 期望窄档），结果记录于 §8.4 并账本登记。

### 8.4 双例验证结果（2026-08-30 实测，账本 run-…-impact-assessment-001/002）

| 用例 | 代理输出 | ground truth（修正后） | 判定 |
|---|---|---|---|
| 高影响例（orchestration/engine/config_schema/provider/main.py/App.jsx/verify_e2e） | A=9/11=81.8%、B=8/8=100%、composite=85.45 → **全量档（整个代码库）** | 同左（初稿漏计 #7/#8 分段宿主，修正后一致） | ✅ PASS |
| 低影响例（verify_agentops/impact-assessment.md/sprint-8.md） | A=2/11=18.18%、B=0%、composite=14.55 → **窄档（修改文件 ∪ 核心文件区域）** | 同左 | ✅ PASS |

**结论：代理行为与定义预想一致**——数字计算、触达判定、档位决策、recommended_scope 均符合 spec v1.2.0；ground truth 修正说明：orchestration.py 整文件变更即触达其分段宿主功能（#1/#7/#8）。
