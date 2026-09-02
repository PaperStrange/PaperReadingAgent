# 1-WORKFLOW —— 项目工作流（开发规范 / 知识管理 / 项目管理）

> 适用范围：`PaperReading-Windows`（分支 `windows`，由 macOS 版 `mac` 分支移植而来）。
> 本文件记录**怎么组织项目、怎么开发、怎么运行**；架构见 `2-ARCHITECTURE.MD`，**决策逻辑/算法（DSL+UML）见 `4-ALGORITHM.MD`**，踩坑与经验见 `3-LEARNED.MD`。

---

## 1. 知识管理规范

本仓库文档统一存放在 `docs/`，按"一类问题一个文档"拆分，根目录 `README.md` 只做入口并引用以下文档：

| 文档 | 负责回答 |
|---|---|
| `docs/1-WORKFLOW.MD` | 开发规范、知识管理规范、项目管理、运行手册 |
| `docs/2-ARCHITECTURE.MD` | 系统架构、模块职责、数据流、模型与存储约定 |
| `docs/3-LEARNED.MD` | 开发经验教训、踩坑记录、验证记录、已知限制 |
| `docs/4-ALGORITHM.MD` | **前后端决策逻辑与算法**：DSL 规则、决策表、UML 类图/时序图/状态机（每条规则标注代码位置，防漂移清单见其 §12） |
| `docs/5-VERSIONS.MD` | **发版记录与版本号规范**（`年.月.日-v(R.R.R)`；首个版本在 roadmap 全部 Sprint 完成后发布） |
| `docs/iteration/` | 敏捷迭代：**`ROADMAP.MD`（全局 Now/Next/Later）** + `phases/<阶段>/{README,roadmap,backlog,分析文档}.MD`（分阶段管理，backlog 卡独立登记）+ `sprint/<日期>-sprint-N.md`（Sprint 计划/执行/Retro + **关闭证据**） |

规则：

1. **新增知识先归类**：属于流程 → 1，属于结构 → 2，属于**决策/算法 → 4**，属于经验/教训 → 3；无法归类才新开编号文档。
2. **敏捷迭代**：功能/体验类工作按 Sprint 推进，Sprint 文档统一放 `docs/iteration/sprint/`，迭代中新增的项目文档放 `docs/iteration/`（详见 §4）。
3. **变更同步**：代码、依赖、模型、路径等发生变更时，必须同步更新对应文档；**任何决策逻辑改动必须同步 `4-ALGORITHM.MD`（并核对 §12 防漂移清单）**。
4. **macOS / Windows 双轨**：两仓库文档结构一致（同名三件套），内容分别描述各自平台；共性内容允许重复但不允许互相矛盾。
5. 架构图统一用 Mermaid（GitHub 原生渲染），必要时附文字版时序图。

## 2. 开发规范

- **改动范围**：Windows 移植只允许改 `PaperReading-Windows`；原文件仅当发现原代码缺陷时修改（对应 macOS 仓库同文件）。
- **保留原代码**：所有被替换的 macOS 原始配置/路径，用 `[macOS original]` 注释保留，**不删除**。
- **密钥**：一律读取环境变量或本地 `paper-qa-script/.env`（以 `.env.example` 为模板），**代码与文档中禁止出现真实密钥**；`.env` 已被 `.gitignore` 忽略。解析优先级：config 节点 `params.api_key` → 服务商专属环境变量（`DEEPSEEK_API_KEY`/`DASHSCOPE_API_KEY`/`OPENAI_API_KEY`/`OPENROUTER_API_KEY`）→ 通用 `OPENAI_API_KEY` → `.env`。
- **服务商切换**：`PAPERQA_PROVIDER=deepseek|dashscope|openai|openrouter|<自定义名>` 统一切换；服务商模型/向量化/密钥映射集中在 `paper-qa-script/provider_config.py`（内置 4 家 + `providers.json`/`PAPERQA_PROVIDERS_JSON` 自定义，显式参数优先级更高）；配置**唯一真源**（分组 schema/默认值/影响提示）在 `paper-qa-script/app/config_schema.py`（`python -m app.config_schema` 可生成/自检）。
- **安全**：后端 CORS 仅允许本地前端来源、仅监听 `127.0.0.1`；前端渲染依赖 React 默认转义 + Streamlit DOT 转义；如需公开仓库，先确认无密钥残留（`git grep` 全历史）并轮换曾暴露的密钥。
- **依赖锁定**：与 macOS `paper-qa/uv.lock` 对齐（fhlmi==0.42.1、litellm==1.76.1）；直接 `pip install` 会解析到更高大版本，需显式锁定。
- **Python**：3.11+（本机 3.13）；**Node**：18+（本机 23）。
- **编码**：Windows 控制台 GBK 会导致中文乱码，脚本/命令行建议 `PYTHONUTF8=1`。
- **提交**：新文件夹内 `git commit`；`node_modules/`、`.venv/`、`dist/`、`__pycache__/`、`data/parsed/*.jsonl`、`._*`（AppleDouble）不入库（见 `.gitignore`）。

## 3. 项目管理（分支与远程）

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`main`（跨平台融合/集成分支）｜`mac`（macOS 原版）｜`windows`（Windows 移植版）
- 约定：`windows` / `mac` 各自改动后，通过 **Pull Request 合并到 `main`**；每类工作一个提交，提交信息用 `type: 说明`（如 `fix:` / `docs:` / `feat:`）。
- **PR 工具**：创建/更新/合并 PR 一律用 `scripts\github-pr.ps1`（create/patch/merge/get 子命令，UTF-8 安全）。**禁止**直接用 `Invoke-RestMethod` 传中文字符串 Body（PS 5.1 会按 GBK 编码 → GitHub 乱码，见 `3-LEARNED.MD` 1.18）。**（Windows-only；mac 侧等价用 `gh pr create/patch/merge` 或 Web UI，中文 Body 注意 UTF-8。）**
- **分支保护（2026-08-30，A-M10）**：`main` 已启用保护——**必须经 PR 合并**（直推拒绝）、必需状态检查 = CI「Offline suite + builds (Windows)」（未绿时 API 合并会被拒，等 CI 转绿再 merge）、禁止 force push / 删除、enforce_admins 开启。`windows`/`mac` 不保护（工作分支允许历史整理）。
- **同步节奏（2026-08-31 用户决策定稿，含 push 与 PR 两层）**：
  1. **本地 commit**：按逻辑单元（卡/子步骤）提交，信息 `type: 说明`；commit 不触发任何远程动作；
  2. **push windows 节奏**：**会话结束 + 里程碑（卡/阶段完成、流程确认）批量 push**，不逐卡 push；风险操作（切分支/rebase）前或长时间离开前 push 兜底备份；push 前先本地跑受影响的最小检查；
  3. **windows CI 状态口径**：允许中途红（WIP 状态），但 **Sprint 关闭前必须绿**；连续红不修 → 暂停开新卡；CI 已加 `concurrency` 去重（同 ref 连续 push 只跑最新，防排队堆积）；
  4. **PR main**：Sprint 关闭（三查通过）后**统一批量提交**，不逐卡 PR——main 只接收"已验证的里程碑快照"（1.45：先合门、后 ✅），减少 CI/评审噪音并保持 main 状态一致；**例外①** Blocker/Critical 或安全修复可即时同步（先修后补 sprint 记录）；**例外②** 跨 sprint 长任务可在**天然里程碑（阶段完成）**时补一次 PR（该阶段产物仍须三查）。

## 4. Sprint（迭代）项目管理与关闭标准

> 适用：所有功能/体验类改动。Sprint 文档统一放 `docs/iteration/sprint/<日期>-sprint-N.md`；
> 迭代中新增的其它项目文档（如架构调整、性能分析）放 `docs/iteration/`。

### 4.1 Sprint 生命周期

`Plan（目标+Backlog+验收标准+**时间盒**）` → `Dev（按 US 拆解实现，**开卡/推进/关卡**）` → `Verify（可运行验证）` → **`三查（固定动作）`** → **`经验教训总结（关闭前置必做）`** → **`Close（关闭评审）`**。

**调研前置（2026-08-30 用户要求）**：任务输入含调研要求（research/调研/选型/对比/评估/最佳实践等关键词，完整规则见 `agents/functions/tech-research.md` Trigger 节）时，**先自动跑 tech-research 深度调研**——多来源对比分析（≥3 来源/论断 + 对比矩阵 + 结论建议），把调研报告注入上下文，**再开始规划任务**；不得"搜几个网页就下结论"。流程定义在 `agents/fanout.json` 的 `planning_pipeline`（条件/顺序可调）。

**时间盒与过程监管（2026-08-30 用户要求制度化；2026-08-30 补充自主开卡制）**：
- 每个 Sprint 在 Planning 时**声明时间范围**（起止日/小时）与预估工时；无时间盒不开卡。
- **燃尽图随每张卡推进更新**（每完成/关闭一卡记一个里程碑与剩余点），而非关闭时一次性补图——供项目经理（用户）随时监管进度。
- **自主开卡制（2026-08-30 用户确认）**：时间盒与 Sprint 计划批准后，主代理**自行开卡/推进/关卡，无需逐卡确认**；汇报频率 = 里程碑摘要（每完成一组卡或每 N 点一次），用户通过看板/燃尽图随时抽查。
- **例外仍需确认**：阻塞超时 / 砍范围 / 插新卡 / 方向或样式级决策 / 时间盒调整；其余执行细节自主。
- 过程中**一次开一张卡**并推进到 DONE（或明确 BLOCKED + 理由）；Sprint 超时未完成 → 与用户确认**续期 / 拆卡 / 砍范围**三选一，不得无声延期。
- 卡的状态流转与验收证据同步写入 Sprint 文档 §3/§5/§7，用户可随时审计。

**经验教训总结（2026-08-30 用户要求固化，关闭前置必做）**：
- 一查/二查（文档/代码审查）完成、**Close 之前**必须执行（fan-out 五步第 4 步，先于三查环境核验）——由 `agents/functions/lessons-learned.md` 职能（子代理）产出 3-LEARNED 新条目草稿 + 分类索引更新建议，主代理审核后回填；无真教训可明说"本轮无需新增"，但**步骤不可跳过**。
- **fan-out 顺序与运行条件为可调配置**：关闭流程五步（scope→doc-audit→code-review→lessons→workspace-check）定义在 `agents/fanout.json`（条件/顺序/执行者可调，看板可编辑）——用户可通过看板观察 agent 执行对功能开发部署进度的影响，并据此调整顺序与运行判断条件。

### 4.2 Sprint 关闭：必须有足够 solid 的证据 + 理由

**关闭 Sprint 的前提是"证据充分、理由明确"。证据需同时包含图文（例如浏览器截图）与文字，并附理由，统一写入该 Sprint 文档的「项目管理与证据」板块。** 缺少证据或无法自证"达成目标"的项不能标记为 done。

#### 三查（每个 Sprint 关闭前的固定动作，2026-08-30 起制度化；Sprint-8 起按职能 spec fan-out）

> 执行方式：按 `agents/functions/` 固定 spec 派出子代理（prompt 零漂移），每任务经 `scripts/agent-ops.py` 记账（register→finish，见 `agents/README.md`）；报告用 `parse-report` 结构化后按 §4.4 分诊闭环。
> **执行顺序（用户问题①修正，2026-08-30）**：先跑 **impact-assessment（影响范围评估，新子代理）**——复合指标 `(0.8×A + 0.2×B)×100`（A=核心功能覆盖率/13、B=核心 API 覆盖率/10），**阈值 X=50**：`>50` → 全量档（整个代码库）；`≤50` → 窄档（Sprint 修改文件 ∪ 核心文件区域）。再按该范围执行一查/二查——**审查范围不得默认收窄到 Sprint 交付物**，偏离 recommended_scope 须在 Sprint §9 记录理由。

| # | 检查 | 内容 | 执行者（spec） |
|---|---|---|---|
| 〇查 范围 | **影响范围评估**（fan-out 第一道闸门） | 变更模块归类 → A（13 项核心功能触达）/B（10 条路由触达）→ composite（阈值 X=50）→ 两档 recommended_scope | 子代理 `functions/impact-assessment.md` × 1 任务 |
| 一查 文档 | 文档一致性审计（范围 = 〇查 recommended_scope） | 死链/陈旧事实/跨文档矛盾/缺失知识；**4-ALGORITHM.MD 逐条对照代码**（其 §12 防漂移清单） | 子代理 `functions/doc-audit.md` × 1 任务（target=working-tree，scope 入参） |
| 二查 代码 | windows + main 双分支 code review（范围 = 〇查 recommended_scope） | 正确性/安全/SSOT/兼容性/架构分层；main 侧重合并完整性与悬空引用；**功能-测试配对核查（TG-1，2026-08-31）**：用户可见功能（节点/路由/数据源/provider/表单字段）必须同 PR 交付对应 verify case（离线断言或联网 e2e/GUI check），并在覆盖矩阵登记（TG-2 落地后） | 子代理 `functions/code-review.md` × 2 任务（target=branch:windows、branch:main 并行，scope 入参） |
| 三查 环境 | 工作区与功能完整性 | `git status` 零残留、本地已合并分支清理、.gitignore 覆盖、端口卫生、回归（smoke/e2e/新增端点/GUI）全绿 | **主代理** `functions/workspace-check.md`（起服务/杀进程不子代理化） |

> 经验教训总结（lessons-learned）为 fan-out 五步第 4 步（在一查/二查之后、三查环境核验之前执行），见 §4.1 与 `agents/fanout.json`；不入上表（三查固定动作之外的关闭前置步骤）。

> 三查可委托评审代理并行执行；**发现项必须修复闭环后（修复 → 回归 → 文档同步 → PR 同步 main）才允许 Close**；结论写入该 Sprint 文档的「评审/同步记录」节。

#### 证据 checklist（按需选取，尽可能覆盖）

| 类别 | 示例 |
|---|---|
| 🖼️ 功能截图（before/after） | 浏览器截图（面板缩放、全屏、lightbox、按钮、连线效果） |
| 🖼️ 运行/接口输出 | 后端 API 返回、`verify_*.py` 实测输出（时间/状态/样本）、日志 tail |
| 🖼️ 命令与产物 | `npm run build`、pytest / e2e 结果、生成的报告 |
| 📝 验收用例 | 对应 Backlog US-* 的验收标准逐条说明，标注通过/未通过 |
| 📝 功能-测试配对（TG-1） | 每个用户可见功能（节点/路由/数据源/provider/表单字段）列出对应 verify case 与覆盖矩阵登记 |
| 📝 理由/权衡 | 为什么这么做、关键取舍、为什么不采用其它方案、局限 |
| 📝 边界与回归 | 受影响面、是否破坏既有功能、（可选）回归验证结果 |

#### 截图要求

- 能**直观反映改动**：例如拖拽后的分栏比例、全屏后的整体视图、放大后的图片、新增按钮及其点击后的结果。
- 标注**时间/环境**（可选）：截图文件名或 caption 标注日期与操作。
- 存放到 `docs/iteration/sprint/<run>.png`（连同该 sprint 文档一起入库），在 Markdown 里用相对路径引用，例如：
  ```markdown
  ![分栏拖拽](./2026-08-26-pane-resize.png)
  ```

#### 关闭时的 Self-check

- [ ] 每个 US 有对应证据（截图 + 文字），逐条说明通过情况
- [ ] 结论来自**可复现**的证据（命令/截图），而非推测
- [ ] 记录了关键权衡/理由与已知局限
- [ ] 未破坏既有功能（或有明确回归记录）
- [ ] sprint 文档已入库并随分支同步到 `docs/iteration/sprint/`
- [ ] **三查已完成且发现项闭环**（文档/双分支 code review/工作区与功能完整性），结论写入 Sprint 文档
- [ ] 决策逻辑变更已同步 `4-ALGORITHM.MD` 并核对 §12；windows 已 PR 同步 main（不含 `docs/iteration/`）
- [ ] **用户可见功能均有对应 verify case 与矩阵登记（TG-1 规则，2026-08-31）**；缺失即不得关闭，须补 case 或说明豁免理由（经用户确认）

### 4.3 Sprint 文档模板

见 `docs/iteration/sprint/_template-sprint.md`（**仅 windows 分支维护**）。关闭时把第 4.2 节的**项目管理与证据**板块填实。

### 4.4 Sprint / Bug / 日常维护 的判定标准（2026-08-30 制度化）

> 方法论依据：缺陷**严重度分诊**（Blocker/Critical/Major/Minor/Trivial 分级，见 [NRAO Issue 类型](https://open-confluence.nrao.edu/pages/diffpagesbyversion.action?pageId=29529259&originalVersion=3&revisedVersion=8) 与 [Zowe 社区 triage 指南](https://github.com/zowe/community/pull/1980)）；**维护 vs 项目**的区别（纠正性/适应性维护 vs 立项开发，见 [EMI 软件维护与支持计划](https://twikiai07.cern.ch/twiki/pub/EMI/DeliverableDSA11/EMI-DSA1.1-1277556-SoftwareMaintenanceAndSupportPlan-v0.9.pdf) 与 [项目和维护的主要区别](https://worktile.com/kb/p/3913291)）；**服务等级（Classes of Service）**与"非计划工作预算"思想（[Kanban 术语表](https://kanban.university/glossary/)；为缺陷/验收修复预留 sprint 产能的讨论见 [SoftwareEngineering.SE](https://softwareengineering.stackexchange.com/posts/311947/revisions)）。

**三类工作定义与判定（按顺序问 5 个问题）**：

1. 是否引入**用户可见的新能力 / 协议变更**（新端点、新面板、新数据源类型、SSE/请求字段变化）？
2. 是否触碰**决策逻辑**（`4-ALGORITHM.MD` §3–§10 任一规则变化，含默认值/优先级/短路顺序）？
3. 是否**跨层**（后端编排+前端 UI+文档 同时改）或**新增模块**？
4. 预估规模是否 ≥ **8 点 / 2 个模块**，或同类问题 ≥ **3 个**（成批）？
5. 是否属于 **roadmap 主题**（原规划或已批准的新增候选）？

| 判定 | 条件 | 处理路径 |
|---|---|---|
| **新 Sprint** | 命中任一 1/2/5，或命中 3/4 | 完整 Sprint 流程（planning/看板/燃尽/DoD/三查），写 `docs/iteration/sprint/<日期>-sprint-N.md` |
| **插队 Sprint** | 用户实测驱动的**成批修复**（≥3 个同源问题或合计 >8 点），须用户提出或明确批准 | 同新 Sprint 流程，sprint 文档标注"插队"，阶段 `roadmap.MD` §2 实际实录登记 |
| **Bug（直接修复）** | 单点根因、不改设计/接口/协议、≤2h、纯缺陷或回归 | `fix:` 提交 + 对应回归（smoke/e2e/GUI 按需）+ 有教训记 `3-LEARNED` + PR 同步；**不写 sprint 文档** |
| **日常维护** | 文档勘误/知识管理、依赖 pin、清理/环境 SOP、验证脚本维护、≤5 点且行为不变的小重构 | `docs:`/`chore:` 提交 + PR 同步；不写 sprint 文档 |

**严重度分诊（决定时效，不决定归属）**：`Blocker`（主流程不可用/数据损坏）→ 立即 fix 或立即插队；`Critical`（核心功能失效，有规避）→ 当日内；`Major`（功能缺陷/无规避）→ 纳入最近 sprint 或批处理；`Minor/Trivial`（体验/文案/样式）→ backlog 候选，凑批后进插队 sprint。

**非计划工作预算**：每个 Sprint 预留 **~20% 产能**应对 Blocker/Critical 缺陷与紧急维护；超出预算则先补计划再执行（新 sprint 或插队 sprint），**禁止长期游离于流程之外**。

**边界澄清（本项目经验）**：单文件"改了目录没生效"这类**流程缺陷**，若修复需要前后端协同+新增决策规则（如 Sprint-5 的自动重跑+状态失效），属于插队 sprint；若只是文案/样式单点问题，属 Bug/维护。判断先例见 `docs/iteration/sprint/2026-08-30-sprint-4.md`（插队，**仅 windows 分支维护**）与 Sprint-5（插队，后补三查整改）。

**预研上下文传递（2026-08-31 制度化，用户建议）**：

1. 探讨性预研（涉及用户选择/确认的调研讨论，如方案菜单、采纳范围、成本拍板）在结束或中断时，**必须落盘**为预研笔记（**仅 windows 分支维护**，main 无此目录 → 注入规则在 main 为 no-op）：按领域归档 `docs/iteration/pre-research/<领域>/<日期>-<主题>.MD`（领域 = tech/product/marketing，跨领域治理笔记放根目录；**一领域 = 一 agent = 一账本 role = 一笔记目录**，隔离与侧重点见 `docs/iteration/pre-research/2026-08-31-domain-governance.MD`）。要素：背景 / 现状证据 / 结论（方案菜单+推荐）/ 来源 / **用户决策记录（chronological）** / 注入指引；落盘后同步更新 `docs/iteration/pre-research/README.md` 追溯索引。
2. planning 时：任务主题命中某预研笔记（按笔记"注入指引"的关键词匹配）→ **笔记作为 tech-research 的 `context` 输入，并在任务分解前注入规划上下文**；开卡时卡片链接对应笔记（见 `agents/fanout.json` planning_pipeline 的 `pre_research` 字段）。
3. **基线规则**：tech-research 以笔记记录的既定决策为基线——不重复调研已决路线、不静默改向；发现与既定决策矛盾 → 报告"翻案建议"交用户裁决，不得自行推翻。
4. 目的：避免方案路线决策在后续流程中**重复出现/前后矛盾**，预研结论与用户确认是规划管线的资产而非一次性对话。

## 5. 运行手册（Windows）

> **新用户请先看根目录 `README.md` 的"本地部署"**（含先决条件、一步步部署、验证安装、故障排查）。
> 本节约为开发者的完整运行手册，命令与 README 一致。

### 5.1 一次性环境准备

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows   # 或你的仓库根目录
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1   # 含锁定 fhlmi/litellm 版本（对齐 mac uv.lock）+ requirements-windows.txt
# 前端依赖
cd paper-qa-script\reactflow-paperqa-prototype\frontend
npm ci
```

### 5.2 启动（三终端）

```powershell
# 终端 1：FastAPI 后端（127.0.0.1:8787）
.\scripts\start-backend.ps1
# 终端 2：前端（127.0.0.1:5173）
.\scripts\start-frontend.ps1
# 终端 3（可选）：Streamlit 调试 UI（127.0.0.1:8501）
.\scripts\start-streamlit.ps1
```

> 若 `.ps1` 被记事本打开：用 `powershell -ExecutionPolicy Bypass -File .\scripts\start-*.ps1`，或双击 `scripts\start-*.bat`。

浏览器打开 http://127.0.0.1:5173 。

### 5.3 使用流程（ReactFlow 原型）

1. 打开前端 → **1) Config** 节点：`api_key` 留空即可（读环境变量 / `.env`）；确认 `paper_directory`（默认 `data/pdf`，相对后端 cwd）与「数据源」面板（local/remote 模式，见 README「数据源」节）。
2. 依次或 `Run All (Left-to-Right)` 执行：**Load Index → Retrieve → Parse Chunk Embed → Gather Evidence → Generate Answer**。
3. 点击任一节点，右侧"函数子画布"展示该步骤函数调用图；节点卡片可展开文本/页码预览图/中文翻译。
4. 顶栏 `New Run ID` 分组一次实验；`New Session` 重建会话（会话为后端内存态）。

### 5.4 命令行脚本

```powershell
.\.venv\Scripts\python.exe .\paper-qa-script\manual_index_paper.py     # 建索引 + 交互问答
.\.venv\Scripts\python.exe .\paper-qa-script\manual_test_internet_connection.py  # 连通性
```

### 5.5 验收脚本

```powershell
$env:PAPERQA_PROVIDER = "deepseek"                  # 与服务商一致
$env:DEEPSEEK_API_KEY = "<DeepSeek key>"             # 若 .env 已配置可跳过
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py             # 8 项冒烟（离线）
.\.venv\Scripts\python.exe .\verify\verify_prune_callbacks.py   # litellm 回调裁剪（离线）
.\.venv\Scripts\python.exe .\verify\verify_agentops.py          # AgentOps 账本 CLI 用例断言（离线）
.\.venv\Scripts\python.exe .\verify\verify_config_schema.py     # 配置 SSOT 一致性 + M7 零硬编码 + Settings 升级基线（离线）
.\.venv\Scripts\python.exe .\verify\verify_matrix.py check      # 覆盖矩阵防漂移（离线；改动脚本元数据后先 derive）
.\.venv\Scripts\python.exe .\verify\verify_index_health.py      # 索引三重探针 + 自愈（离线）
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py   # 服务商切换/路由实证（联网）
.\.venv\Scripts\python.exe .\verify\verify_e2e.py               # 全链路（真实 API）
.\.venv\Scripts\python.exe .\verify\verify_e2e_openai.py        # OpenAI provider+embedding 全流程（账户需余额）
.\.venv\Scripts\python.exe .\verify\verify_e2e_dashscope.py    # dashscope 全流程 + deepseek 同进程切换（联网）
.\.venv\Scripts\python.exe .\verify\verify_agent.py             # Agent 流程 + 翻译（需 e2e 先跑过）
.\.venv\Scripts\python.exe .\verify\verify_embed_load.py        # Embedding 三步
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py        # remote 数据源全链路（联网）
.\.venv\Scripts\python.exe .\verify\eval_retrieve.py            # 检索质量小样本评测（F4）
node .\verify\gui_check.mjs          # GUI 全链路（需前后端已启动）
node .\verify\gui_check_remote.mjs   # GUI remote 数据源（需前后端 + 联网）
node .\verify\gui_check_s4.mjs       # Sprint-4：光标/面板联动（需前后端已启动）
node .\verify\gui_check_s5.mjs       # Sprint-5：自动重跑/双模式/计时冻结（需前后端已启动）
node .\verify\gui_check_s7.mjs       # Sprint-7：多节点并发计时（需前后端已启动）
node .\verify\gui_check_dashboard.mjs         # 看板概览页截图（需 agents-dashboard 已启动，8600）
node .\verify\gui_check_dashboard2.mjs        # 看板 spec 编辑页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_costs.mjs   # 看板成本/上下文页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_report.mjs  # 看板报告浏览页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_dashboard_fanout.mjs   # 看板 fan-out 配置页截图（需 agents-dashboard 已启动）
node .\verify\gui_check_config_schema.mjs      # Sprint-11/12/13：schema 清单/全字段表单截图 + 字段级校验 + defaults-derived（需前后端已启动）
```

详见 `verify/README.md` 与 `docs/3-LEARNED.MD` 的验证记录。
