# agents/ —— 评审职能 spec 与 AgentOps 账本（跨 IDE 说明）

> 本目录是 AgentOps 基础设施的**稳定交付物**（随分支同步 main）：职能 spec（`functions/`）、runtime 账本（`runtime/`、`runs/`）。设计与决策见 `docs/iteration/phases/agents-infra/architecture.MD`（仅 windows 分支）。

## 1. 职能清单（按职能划分，非分支）

| 职能 | spec | 任务输入（参数化） | 执行方式 |
|---|---|---|---|
| 深度技术调研（规划前置，自动触发） | [`functions/tech-research.md`](functions/tech-research.md) | `{question, context, depth}` → 多来源深度调研报告（≥3 来源/论断 + 对比矩阵 + 结论建议） | 子代理——**任务含调研要求（关键词见 spec Trigger）时自动启用，报告注入上下文后才开始规划** |
| 影响范围评估（fan-out 第一道闸门） | [`functions/impact-assessment.md`](functions/impact-assessment.md) | `{change_set, scope_hint}` → 输出 A（核心功能覆盖率/13）、B（核心 API 覆盖率/10）、composite=(0.8A+0.2B)×100、**阈值 X=50** 两档 recommended_scope | 子代理（三查/review 前先跑） |
| 代码审阅 | [`functions/code-review.md`](functions/code-review.md) | `{target: branch:windows\|branch:main\|pr:<n>\|working-tree, scope, focus, strictness}` | 子代理（每任务一次） |
| 文档审计 | [`functions/doc-audit.md`](functions/doc-audit.md) | `{target, scope, focus, strictness}` | 子代理 |
| 经验教训总结（Sprint 关闭前置必做） | [`functions/lessons-learned.md`](functions/lessons-learned.md) | `{sprint_doc, change_commits}` → 3-LEARNED 新条目草稿 + 分类索引更新建议（主代理审核回填） | 子代理（一查/二查后、workspace-check 前；fan-out 第 4 步） |
| 工作区核验 | [`functions/workspace-check.md`](functions/workspace-check.md) | — | **主代理执行**（D2：起服务/杀进程不子代理化） |

> **spec 语言约定（用户要求 2026-08-30；tech-research 首跑调研实证）**：`functions/*.md` 正文为**英文**——① 编码健壮性：PS 5.1 无 BOM 时按 ANSI 误读非 ASCII（[微软官方文档](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_character_encoding)；同型事故 [codex#29085](https://github.com/openai/codex/issues/29085)、[spec-kit#4359](https://github.com/github/spec-kit/issues/4359)），英文/纯 ASCII 从机制上根除 mojibake，且不加 BOM（微软明确"避免 UTF-8 BOM"）；② 生态惯例：Agent Skills 规范 `name` 字段本就限 ASCII，[anthropics/skills](https://github.com/anthropics/skills) 等官方库全部英文。**报告输出仍为中文**（项目文档语言）；**Trigger 段触发关键词保留中英双语**（匹配对象是中文任务文本）。措辞参考 `.agents/skills/` 官方 SKILL.md（imperative、checklist、Sources of truth）。

- 同一职能对多个 target 各跑一次任务（如三查时 code-review 跑 windows+main 两任务），分支/PR 只是任务参数。
- **调研前置（用户要求 2026-08-30）**：任务输入含调研要求（research/调研/选型/对比/评估/最佳实践等关键词，完整规则见 tech-research spec Trigger 节）时，**先自动跑 tech-research 深度调研**（不是几个网页搜索就下结论），把调研报告注入上下文，**再开始规划任务**；流程定义在 [`fanout.json`](fanout.json) 的 `planning_pipeline`。
- **预研上下文传递（用户建议 2026-08-31，fanout v3 / tech-research v1.1.0）**：`docs/iteration/pre-research/`（仅 windows 分支）的预研笔记含用户决策记录；planning 时任务命中笔记 → 笔记作为 tech-research `context` 注入，既定决策为基线，矛盾以"翻案建议"交用户裁决（规则见 `1-WORKFLOW.MD` §4.4）。
- **审查范围不得默认收窄到 Sprint 交付物**：一律先由 impact-assessment 评估——composite>50 → 全量档（整个代码库）；≤50 → 窄档（Sprint 修改文件 ∪ 核心文件区域），recommended_scope 作为 code-review/doc-audit 的 `scope` 入参。
- **fan-out 顺序与运行条件（可调配置）**：Sprint 关闭流程五步定义在 [`fanout.json`](fanout.json) 的 `sprint_close_pipeline`——`scope → doc-audit → code-review → lessons-learned → workspace-check`（条件/顺序/执行者可调）；用户可通过看板观察各 agent 对开发部署进度的影响并**随时调整顺序与运行判断条件**（1-WORKFLOW §4.1）。
- 新增职能：复制 [`functions/_template-agent.md`](functions/_template-agent.md)（frontmatter 超集 + 五段式 + 可配置参数 + 输出模板，英文），升 `version`，跑 `agent-ops validate-spec` 后上线。

## 2. 账本 CLI（`scripts/agent-ops.py`，纯 Python 标准库）

```powershell
# 一个子代理 run 的完整生命周期（任何编排方/IDE terminal 都能执行）：
.\.venv\Scripts\python.exe .\scripts\agent-ops.py register --role code-review --task branch:windows --spec "code-review@1.1.0" --model deepseek-v4-flash --start
.\.venv\Scripts\python.exe .\scripts\agent-ops.py finish <run_id> --status succeeded --usage-in 10000 --usage-out 2000 --output-chars 3000 --result-file path/to/report.md
.\.venv\Scripts\python.exe .\scripts\agent-ops.py list --role code-review
```

- 账本 = 文件真相源：`runtime/registry.json`（append + sha256 完整性校验，手改即拒——防双写；**本地实时态，gitignore 不入库**）；`runs/<run_id>/<role>.report.md` 为报告存档（memory 浏览入口，**本地留证不入库**）；`runtime/prices.json` 为价表（auto 段由 litellm 价表派生，manual 段人工覆盖且**非 null 时优先于 auto**，`null` = 待填价 → 估算标 `pending_price`，**配置文件，入库**）。
- 成本估算：`usage × 单价`（含 cache 分列）；无 usage 时 `chars/4` 兜底并标 `estimated`；**单位 = CNY（用户决策 2026-08-30）**——价表单价为 USD/token，按 `prices.json meta.fx_usd_cny`（默认 7.2，可人工改）换算；口径 = **自报+估算**，精确账单以服务商后台为准。
- 其余子命令：`update`（进入 running + 补 usage）、`validate-spec`（spec frontmatter 校验）、`fetch-spec`（source 块远程拉取：url+ref+sha256 校验、仅 http/https 且拒绝私网/保留地址，失败/`--offline` 回退本地）、`parse-report`（critical/major/minor/nit 结构化，位置含 file:line）、`prices-derive`（价表再派生，保留 manual）。
- **run-id 日期口径**：`register` 自动生成的 run-id 日期取**本机时钟**；本机时钟偏移时（开发机曾 +09:00 且快约 13h），编排方必须用**网络时间（UTC+8）显式传 `--run-id`**（用户政策：时间以网络时间为准）。

## 3. 跨 IDE / 编排方迁移说明

spec 是纯 markdown（body = 可直接粘贴的完整 prompt），账本是纯 JSON，CLI 是纯标准库脚本——**不绑定任何 IDE/harness**：

| 编排方 | 用法 |
|---|---|
| 本会话（DSH） | 把 `functions/<fn>.md` 全文作为 subagent prompt + 任务输入 JSON 追加；run 前后跑 agent-ops register/finish |
| Cursor | 把 spec 内容加入 `.cursor/rules/`（或直接引用 `agents/functions/*.md`）；用 Terminal 跑 agent-ops |
| Claude Code | 复制 spec 到 `.claude/agents/<fn>.md`（frontmatter name/description 即用）；hooks 里调 agent-ops 记账 |
| CI（GitHub Actions） | spec 作为 workflow 步骤的 prompt 模板；`agent-ops.py` 纯标准库直接跑，账本随仓库提交 |
| 未来 paper-qa workflow | 走 CLI 契约 `agent-ops run <role> --context`（见 architecture.MD §3.5，阶段 3 后评估） |

**远程 skill 引用**（D5）：spec frontmatter 的 `source` 块 `{url, ref, sha256, fallback}`——`fetch-spec` 锁 ref 拉取并校验 sha256，失败自动回退本地并告警；修改远程 skill 需同步升 `version` 与 sha256。

## 4. 三查 fan-out（制度化后）

Sprint 关闭三查 = 〇查 `impact-assessment`（先跑，出 recommended_scope）→ `code-review` × 2 任务（branch:windows、branch:main）与 `doc-audit` × 1 任务并行 → `lessons-learned`（fan-out 第 4 步）→ 主代理执行 `workspace-check`；每任务一个账本 run（register→finish），报告 `parse-report` 结构化后按 `1-WORKFLOW.MD` §4.4 分诊闭环，结论写入 Sprint 文档 §9。
