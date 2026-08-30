# AgentOps 架构地基设计（阶段 1 产出，完成）

> 归属：`docs/iteration/phases/agents-infra/`（仅 windows 分支）。
> 状态：**阶段 1 完成**——§1 现状约束、§2 四条调研线结论、§3 架构设计（§3.2/§3.3 部分为草稿级）、§4 已确认决策、§5 待决策。**待用户评审确认后进入阶段 2**。

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

**⚠️ 与用户原倾向（Next.js+MongoDB）的差异**：建议 MongoDB→SQLite，理由如上；**待用户确认**（D6 更新）。

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

### 3.1 agent 定义格式（依据 §2.3/§2.4 定稿）

文件：`docs/agents/<role>.md`（阶段 2 起步；未来可升级为 `<name>/SKILL.md` 目录形式保持兼容）。

```markdown
---
name: code-review-windows            # 必填，= 文件名
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
# 步骤（检查清单）
# 输出模板（critical/major/minor/nit + 文件:行 + 建议修法 + 是否本轮必修）
# 禁止（只报真实问题等）
```

- body = 可直接粘贴给子代理的完整 prompt（D1）；spec 变更必须升 `version`，账本记录 `spec_source: name@version`。

### 3.2 账本数据模型（草稿，来源：调研线 3 推荐 + D4 自报估算口径）

`docs/agents/runtime/registry.json`（数组，一条 = 一次子代理 run）：

```json
{
  "run_id": "uuid",
  "task_id": "str",
  "role": "code-review-windows | code-review-main | doc-audit | ...",
  "spec_source": "spec名@git-sha（或 github raw URL）",
  "model": "str",
  "status": "queued|running|succeeded|failed|cancelled",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "input_chars": 0,
  "output_chars": 0,
  "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0},
  "context_occupancy": {"input_tokens": 0, "max_context": 0, "ratio": 0.0},
  "cost_est": {"input": 0, "output": 0, "total": 0, "currency": "USD"},
  "result_files": ["docs/agents/runs/<run_id>/<role>.report.md"],
  "tags": {},
  "error": "str"
}
```

- 估算公式：`cost = input×P_in + output×P_out + cache_read×P_cr + cache_write×P_cw`；P 取自本地价表（由 LiteLLM `model_prices_and_context_window.json` 派生精简版，入库 `docs/agents/runtime/prices.json`，可人工覆盖）；
- 无 token 上报时 `tokens ≈ chars/4`（中英混合 /3.5）并打 `estimated=true`；
- 上下文占用展示 = `input_tokens / max_context`（工具结果与 memory 计入 input 后膨胀自然可见）；
- 命名对齐 OTel GenAI SemConv（usage 四列含 cache 分列）。

### 3.3 fan-out 协议与分诊闭环（草稿，来源：Sprint-7 实测 + 1-WORKFLOW §4.2/§4.4）

**触发分级**：
| 场景 | 子代理组合 | 说明 |
|---|---|---|
| Sprint 关闭三查 | `code-review-windows` + `code-review-main` + `doc-audit` 三并行 | 环境核验留主代理（D2） |
| Bug/日常维护（≤2h 直接修） | 1 个 `code-review-windows` 或主代理自查 | 避免小事大动干戈 |
| 并行开发（模式 A） | 每张不相交卡 1 个实现子代理 | 前置：Sprint 文档含**文件所有权地图**，无交集才并行 |

**输入**：spec 文件（本地或 github raw 拉取，D5）+ 本轮上下文（分支/commit/工作区 diff 范围、评审重点）。
**输出模板（所有评审代理统一）**：分级问题清单 `critical/major/minor/nit`（每条 = 文件:行 + 问题 + 建议修法 + 是否本轮必修）+ main 代理附同步文件清单 + 一句话总结。
**分诊闭环**：主代理按 `1-WORKFLOW.MD` §4.4 分诊——必修 → 立即修 + 回归；建议修 → 回流 backlog 卡；pre-existing → 新卡登记；结论写入 Sprint 文档 §9（三查记录）。
**账本**：`scripts/agent-ops.py` 子命令 `register/update/finish` 落 `docs/agents/runtime/registry.json` + `runs/<run_id>/<role>.report.md`（子代理报告的原文存档 = memory 浏览入口）。

### 3.4 看板技术栈与数据层（依据 §2.2；**数据层待用户确认**）

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
| D6 | 看板 = 独立轻量应用（新端口），简约互联网风；后端倾向 Next.js + MongoDB 轻量数据层，主打检索/更新快速响应 | 用户确认 2026-08-30 |
| D7 | 三阶段：① 调研+架构 ② 四代理 spec/账本/跨 IDE ③ 看板 | 用户确认 2026-08-30 |

## 5. 待决策/讨论点（阶段 1 评审提交项）

- **P1（核心）**：数据层 MongoDB → SQLite（调研线 4 明确建议弃用 MongoDB：Windows 本地单人 + 文件账本为源 + 检索为主场景，SQLite 零运维/读更快/FTS5 够用）。若采纳，D6 更新为 "Next.js + SQLite"；若不采纳，按 mongod 服务/Atlas/MongoMemoryServer 三形态再评估（调研结论：均不优于 SQLite）。
- P2：看板端口与启动脚本（沿用 scripts/start-*.ps1 模式，建议端口 8600）。
- P3：registry.json 为唯一账本源（文件权威），SQLite 仅为派生索引——看板编辑 spec 直写文件、账本记录只经 agent-ops CLI 追加（避免双写）。默认按此执行，无异议即定。
