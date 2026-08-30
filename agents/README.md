# agents/ —— 评审职能 spec 与 AgentOps 账本（跨 IDE 说明）

> 本目录是 AgentOps 基础设施的**稳定交付物**（随分支同步 main）：职能 spec（`functions/`）、runtime 账本（`runtime/`、`runs/`）。设计与决策见 `docs/iteration/phases/agents-infra/architecture.MD`（仅 windows 分支）。

## 1. 职能清单（按职能划分，非分支）

| 职能 | spec | 任务输入（参数化） | 执行方式 |
|---|---|---|---|
| 影响范围评估（fan-out 第一道闸门） | [`functions/impact-assessment.md`](functions/impact-assessment.md) | `{change_set, scope_hint}` → 输出 A（核心功能覆盖率/11）、B（核心 API 覆盖率/8）、composite=(0.8A+0.2B)×100、**阈值 X=50** 两档 recommended_scope | 子代理（三查/review 前先跑） |
| 代码审阅 | [`functions/code-review.md`](functions/code-review.md) | `{target: branch:windows\|branch:main\|pr:<n>\|working-tree, scope, focus, strictness}` | 子代理（每任务一次） |
| 文档审计 | [`functions/doc-audit.md`](functions/doc-audit.md) | `{target, scope, focus, strictness}` | 子代理 |
| 工作区核验 | [`functions/workspace-check.md`](functions/workspace-check.md) | — | **主代理执行**（D2：起服务/杀进程不子代理化） |

- 同一职能对多个 target 各跑一次任务（如三查时 code-review 跑 windows+main 两任务），分支/PR 只是任务参数。
- **审查范围不得默认收窄到 Sprint 交付物**（用户问题①）：一律先由 impact-assessment 评估——composite>50 → 全量档（整个代码库）；≤50 → 窄档（Sprint 修改文件 ∪ 核心文件区域），recommended_scope 作为 code-review/doc-audit 的 `scope` 入参。
- 新增职能：在 `functions/` 新建 `<fn>.md`（frontmatter 超集 + 五段式），升 `version`，跑 `agent-ops validate-spec` 后上线（上线评估流程见阶段规划 backlog，后续迭代固化）。

## 2. 账本 CLI（`scripts/agent-ops.py`，纯 Python 标准库）

```powershell
# 一个子代理 run 的完整生命周期（任何编排方/IDE terminal 都能执行）：
.\.venv\Scripts\python.exe .\scripts\agent-ops.py register --role code-review --task branch:windows --spec "code-review@1.0.0" --model deepseek-v4-flash --start
.\.venv\Scripts\python.exe .\scripts\agent-ops.py finish <run_id> --status succeeded --usage-in 10000 --usage-out 2000 --output-chars 3000 --result-file path/to/report.md
.\.venv\Scripts\python.exe .\scripts\agent-ops.py list --role code-review
```

- 账本 = 文件真相源：`runtime/registry.json`（append + sha256 完整性校验，手改即拒——防双写；**本地实时态，gitignore 不入库**——用户问题②）；`runs/<run_id>/<role>.report.md` 为报告存档（memory 浏览入口，**本地留证不入库**）；`runtime/prices.json` 为价表（auto 段由 litellm 价表派生，manual 段人工覆盖且**非 null 时优先于 auto**，`null` = 待填价 → 估算标 `pending_price`，**配置文件，入库**）。
- 成本估算：`usage × 单价`（含 cache 分列）；无 usage 时 `chars/4` 兜底并标 `estimated`；口径 = **自报+估算**，精确账单以服务商后台为准。
- 其余子命令：`update`（进入 running + 补 usage）、`validate-spec`（spec frontmatter 校验）、`fetch-spec`（source 块远程拉取：url+ref+sha256 校验、仅 http/https 且拒绝私网/保留地址，失败/`--offline` 回退本地）、`parse-report`（critical/major/minor/nit 结构化，位置含 file:line）、`prices-derive`（价表再派生，保留 manual）。

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

Sprint 关闭三查 = `code-review` × 2 任务（branch:windows、branch:main）+ `doc-audit` × 1 任务并行，主代理执行 `workspace-check` 手册；每任务一个账本 run（register→finish），报告 `parse-report` 结构化后按 `1-WORKFLOW.MD` §4.4 分诊闭环，结论写入 Sprint 文档 §9。
