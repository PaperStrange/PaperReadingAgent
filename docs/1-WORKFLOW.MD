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
  4. **PR main**：Sprint 关闭（三查通过）后**统一批量提交**，不逐卡 PR——main 只接收"已验证的里程碑快照"（1.45：先合门、后 ✅），减少 CI/评审噪音并保持 main 状态一致；**例外①** Blocker/Critical 或安全修复可即时同步（先修后补 sprint 记录）；**例外②** 跨 sprint 长任务可在**天然里程碑（阶段完成）**时补一次 PR（该阶段产物仍须三查）。**⚠️ 用户明确（2026-09-12）：用户走查验收通过之前不得创建 PR**——不得以"提前验证 CI"为由先建 PR；CI 校验走 windows 分支 push 触发，或经用户同意后再建。**⚠️ 排除项两条（2026-09-25 code-review-072 实测）：** ① 不含 `docs/iteration/`（windows-only，main 无该目录）；② **不得删除 4 个 mac 启动脚本** `scripts/{setup-env,start-backend,start-frontend,start-streamlit}.sh`——`git diff --diff-filter=D` 会看到这 4 条删除，按字面 `git merge windows` 会把 mac 侧启动器删掉；它们**有意分叉保留**，同步时必须挡住删除。

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

**Sprint 度量与规模约束（2026-09-21 用户全数采纳，依据 Sprint-16 PM 复盘）**：

Sprint-16 暴露的四个管理问题（数据：日历 9 天但**只有 3 天有提交**；计划 19 点、实际含追加≈44 点；走查/复盘/闸门类工作**无预算位**；三查在交付日按窄档跑、重跑才翻为全量档）→ 立四条规则：

1. **有效工作日双口径**：Sprint 的时间盒同时记录 **日历跨度**与**有效工作日**（当日有相关提交/卡推进才算），燃尽图与排期以**有效工作日**为口径、日历跨度另列。禁止只用日历跨度宣称"用了 N 天"。
2. **Sprint 规模上限**：Planning 时声明计划点数并设上限；**追加卡（走查/评审/用户插入）计入上限**；触顶 → 与用户确认"顺延到下一 Sprint / 扩围 / 砍范围"三选一（沿用 §4.1 既有例外确认机制），不得静默膨胀（Sprint-16 实例：19 点计划 → +25 点追加）。
3. **治理额度预留**：每个 Sprint **预留约 20% 额度给验证与治理**（三查/复核/闸门/文档同步/复盘），且该额度**不可被功能卡挤占**；Sprint-16 的"关闭税"（7 代码 major + 12 文档项 + 3 轮修复验证复核）即因缺此预算而挤压收尾。
4. **〇查前置（范围双跑）**：**开工时先跑一次〇查 impact-assessment 定范围**（写入 Sprint §3 的"开工基线"），关闭时再跑一次；两次档位不一致（如 Sprint-16：开工窄档 32.8 → 关闭全量档 69.2）必须在 §9 记录差异原因。理由：只在关闭时定范围，会让整个 Sprint 按过窄的范围自测与自审。


**经验教训总结（2026-08-30 用户要求固化，关闭前置必做）**：
- 一查/二查（文档/代码审查）完成、**Close 之前**必须执行（fan-out 五步第 4 步，先于三查环境核验）——由 `agents/functions/lessons-learned.md` 职能（子代理）产出 3-LEARNED 新条目草稿 + 分类索引更新建议，主代理审核后回填；无真教训可明说"本轮无需新增"，但**步骤不可跳过**。
- **fan-out 顺序与运行条件为可调配置**：关闭流程五步（scope→doc-audit→code-review→lessons→workspace-check）定义在 `agents/fanout.json`（条件/顺序/执行者可调，看板可编辑）——用户可通过看板观察 agent 执行对功能开发部署进度的影响，并据此调整顺序与运行判断条件。

### 4.2 Sprint 关闭：必须有足够 solid 的证据 + 理由

**关闭 Sprint 的前提是"证据充分、理由明确"。证据需同时包含图文（例如浏览器截图）与文字，并附理由，统一写入该 Sprint 文档的「项目管理与证据」板块。** 缺少证据或无法自证"达成目标"的项不能标记为 done。

#### 三查（每个 Sprint 关闭前的固定动作，2026-08-30 起制度化；Sprint-8 起按职能 spec fan-out）

> 执行方式：按 `agents/functions/` 固定 spec 派出子代理（prompt 零漂移），每任务经 `scripts/agent-ops.py` 记账（register→finish，见 `agents/README.md`）；报告用 `parse-report` 结构化后按 §4.4 分诊闭环。
> **执行顺序（用户问题①修正，2026-08-30）**：先跑 **impact-assessment（影响范围评估，新子代理）**——复合指标 `(0.8×A + 0.2×B)×100`（A=核心功能覆盖率/13、B=核心 API 覆盖率/12），**阈值 X=50**：`>50` → 全量档（整个代码库）；`≤50` → 窄档（Sprint 修改文件 ∪ 核心文件区域）。再按该范围执行一查/二查——**审查范围不得默认收窄到 Sprint 交付物**，偏离 recommended_scope 须在 Sprint §9 记录理由。

| # | 检查 | 内容 | 执行者（spec） |
|---|---|---|---|
| 〇查 范围 | **影响范围评估**（fan-out 第一道闸门） | 变更模块归类 → A（13 项核心功能触达）/B（12 条路由触达）→ composite（阈值 X=50）→ 两档 recommended_scope | 子代理 `functions/impact-assessment.md` × 1 任务 |
| 一查 文档 | 文档一致性审计（范围 = 〇查 recommended_scope） | 死链/陈旧事实/跨文档矛盾/缺失知识/**时间记录准确性**；**4-ALGORITHM.MD 逐条对照代码**（其 §12 防漂移清单） | 子代理 `functions/doc-audit.md` × 1 任务（target=working-tree，scope 入参） |
| 二查 代码 | windows + main 双分支 code review（范围 = 〇查 recommended_scope） | 正确性/安全/SSOT/兼容性/架构分层；main 侧重合并完整性与悬空引用；**功能-测试配对核查（TG-1，2026-08-31）**：用户可见功能（节点/路由/数据源/provider/表单字段）必须同 PR 交付对应 verify case（离线断言或联网 e2e/GUI check），并在覆盖矩阵登记（TG-2 落地后） | 子代理 `functions/code-review.md` × 2 任务（target=branch:windows、branch:main 并行，scope 入参） |
| 三查 环境 | 工作区与功能完整性 | `git status` 零残留、本地已合并分支清理、.gitignore 覆盖、端口卫生、回归（smoke/e2e/新增端点/GUI）全绿 | **主代理** `functions/workspace-check.md`（起服务/杀进程不子代理化） |

> 经验教训总结（lessons-learned）为 fan-out 五步第 4 步（在一查/二查之后、三查环境核验之前执行），见 §4.1 与 `agents/fanout.json`；不入上表（三查固定动作之外的关闭前置步骤）。

> 三查可委托评审代理并行执行；**发现项必须修复闭环后（修复 → 回归 → 文档同步 → PR 同步 main）才允许 Close**；结论写入该 Sprint 文档的「评审/同步记录」节。

#### 修复验证复核（fix-verification review）——与"关闭三查"是两件事（2026-09-21 补定义）

**由来**：主代理在 Sprint 中途修完一个 finding（或用户走查发现）后，会让评审子代理**增量复核**该修复，而这类轮次的 **scope 是主代理自己挑的**（"改动的文件 + 直接调用方 + 相关断言"）。但 `agents/functions/code-review.md` 明确写着：`scope` **必须来自 impact-assessment**（`empty = full repo`；**never a self-chosen narrow scope**）、关闭三查还要 **windows + main 双分支**。此前两者**没有区分定义**，因此容易被误读为"二查已覆盖"（2026-09-21 用户质疑"窄范围复核的判断依据是啥"即由此而来）。

| | **关闭三查**（上表） | **修复验证复核**（本次补定义） |
|---|---|---|
| 触发 | Sprint 关闭前固定动作 | 主代理修完 finding 后（可多轮） |
| scope | **必须**来自〇查 impact-assessment 的 `recommended_scope` | **fix blast radius** = 改动文件 ∪ 直接调用方/消费方 ∪ 受影响断言与脚本 ∪ 该 finding 本身 |
| Timebox / cap | 关闭三查：cap 以各职能 spec 的 Configurable Parameters 为准（code-review 10 / **doc-audit 12** findings），Timebox 同见各 spec | **10~15 min / 5 findings**（§4.2 范围纪律：宁可交回部分 + 覆盖度说明） |
| 目标 | 完整性与兼容性（含 main 分支合并完整性） | 该修复是否真生效、是否引入新问题 |
| 交付 | **阻断 Close** | 不阻断；**不能替代**关闭三查 |
| 记录 | Sprint §9 三查记录 | Sprint §5 执行记录 + §9 明写"**此为修复验证、非二查**" |

**纪律**：① 每轮必须写明 scope 与**覆盖缺口**（哪些维度没看）；② 不得把修复验证计入三查覆盖；③ 关闭前仍须按 impact-assessment 范围跑齐 一查/二查（含 main）+ lessons 步骤——**修复验证不减少任何关闭项**。
**TG-11 补注（2026-09-23，复盘定稿）："那它凭什么 scope"必须有可执行答案**——修复验证复核的 scope **也必须声明来源**：`agent-ops.py register --scope-source self-chosen --deviation "<fix blast radius 与理由>"`（无理由 CLI 直接拒绝）；且它与关闭三查**分节记录**（Sprint §9 / §9.1），**不得混入同一节**（事故根因 R4：混节造成"覆盖存在"的错觉）。关闭前置闸门：`verify/verify_close_readiness.py`（CI 只对**声明了 `三查锚点`** 的 Sprint 文档执行）。
**账本支持（TG-10）**：多轮用 `agent-ops.py round <run_id> --note ... [--output-chars N] [--interrupted --impact ...]` 追加（终态 run 也可），中断/接管用 `agent-ops.py interrupt <run_id> --reason ... --impact ...` 留痕；`list` 显示 `rounds=/dur=/int=` 与 `scope=`（`self-chosen(!)` 高亮、评审类缺来源标 `(missing!)`）。

**fan-out 执行纪律（2026-09-12 制度化，Sprint-15/16 两次子代理无产出超时后固化）**：

1. **报告先行**：派发子代理时必须在 prompt 里要求"**第一步先落盘报告文件**（骨架→逐条覆盖更新）"；只把发现留在上下文中不落盘的运行视为未产出（超时后无任何资产可回收）。各派发型 spec（tech-research / impact-assessment / code-review / doc-audit / lessons-learned）已在正文加 Output discipline 段固化该要求。
2. **接管判据**：子代理**超过 spec Timebox（或 15 分钟无报告文件产出/无回报）** → 主代理**直接接管**，按同一 spec 全维度执行并落盘报告；在 Sprint §9 注明"子代理超时，主代理接管执行"及账本 run 状态。
3. **账本诚实**：接管运行同样登记账本（register→finish），报告写入 `agents/runs/<run_id>/<role>.report.md`；不得把未产出的子代理记为 succeeded 而不留报告。
4. **范围纪律**：Finding cap / Timebox 是硬约束——宁可交回"已写下的部分 + 覆盖度说明"，也不要为凑完整性无限扩张。

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
- 存放到 `docs/iteration/sprint/<run>.png`（连同该 sprint 文档一起入库），在 Markdown 里用相对路径引用（示意占位，非真实文件）：
  ```markdown
  ![分栏拖拽](./<sprint>-<run>.png)
  ```

#### 关闭时的 Self-check

- [ ] 每个 US 有对应证据（截图 + 文字），逐条说明通过情况
- [ ] 结论来自**可复现**的证据（命令/截图），而非推测
- [ ] 记录了关键权衡/理由与已知局限
- [ ] 未破坏既有功能（或有明确回归记录）
- [ ] sprint 文档已入库并随分支同步到 `docs/iteration/sprint/`
- [ ] **三查已完成且发现项闭环**（文档/双分支 code review/工作区与功能完整性），结论写入 Sprint 文档
- [ ] 决策逻辑变更已同步 `4-ALGORITHM.MD` 并核对 §12；windows 已 PR 同步 main（排除 `docs/iteration/`，且未删除 4 个 mac `.sh`：`scripts/{setup-env,start-backend,start-frontend,start-streamlit}.sh`）
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

Sprint-16 追加（provider 刷新 / 定时底座 / 分层验证）：

```powershell
# ① provider 官网调研刷新（F-AC8）：抓 meta.source_urls → M16 归档 + proposal；--apply 仅刷新 fetched_at/status
.\.venv\Scripts\python.exe .\scripts\refresh-providers.py --check                  # 到期判定（不联网）
.\.venv\Scripts\python.exe .\scripts\refresh-providers.py --fetch --apply          # 真实抓取 + 刷新元数据（模型名变更需人工确认）
.\.venv\Scripts\python.exe .\scripts\refresh-providers.py --migrate                # 旧 providers.json 拆成 providers/*.json

# ② 定时底座（TG-5）：单一入口，供手动 / 进程内调度 / Windows 任务计划调用
.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --list                     # 任务、间隔、上次运行、花费
.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --task nightly-suite --check-due   # 到期才跑（fail-closed 预算闸门）
.\.venv\Scripts\python.exe .\scripts\scheduled-tasks.py --task nightly-suite --record-cost 3.5  # 回填实测花费（联网档跑完后通常已由 suite 实测值**自动回填**，仅在未测量时人工补）
powershell -ExecutionPolicy Bypass -File .\scripts\register-scheduled-tasks.ps1 -Action register   # 注册周频任务计划（可选）
.\.venv\Scripts\python.exe .\scripts\report-freshness.py [--check]                 # M18 v1：调研报告时效（--check 有 stale 退出 1）

# ③ 分层验证（fail-closed；上限可配置）
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier offline                    # 离线档（CI/日常）
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier gui                        # GUI 档（需前后端已启动）
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier network --budget-cny 10    # 联网档（预估超上限直接拒绝启动）
.\.venv\Scripts\python.exe .\verify\run_suite.py --tier network --est-factor 1.0   # 预估安全系数可配（默认 1.3；亦可 env PAPERQA_EST_SAFETY_FACTOR）

# ④ 运行时可观测（后端已启动时）
Invoke-RestMethod http://127.0.0.1:8787/api/usage                                   # Retro③：本进程实测 token 用量与成本（CNY）
Invoke-RestMethod http://127.0.0.1:8787/api/checkpoints                             # F-AC16 v1：本地 checkpoint 只读索引（含逐篇载荷路径）
```

> HF 网络不可达时（模型已在本地缓存）设 `$env:HF_HUB_OFFLINE = "1"`（+ `TRANSFORMERS_OFFLINE=1`）避免 sentence-transformers 的 HEAD 重试阻塞调用。

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

## 6. 规则与纪律（政策数据化 / 文档规范 / 流程纪律；TG-15 起，2026-09-23 立规）

> 本节内容原编号为 `§3.1`；历史文档中出现的 `§3.1`/`§3`（指本节者）一律指向本节，不回改历史记录。

**规则**：`scripts/**` 与 `verify/**` 里的脚本**不得把政策写成常量**——角色集合、必填步骤/分支、
覆盖路径清单、阈值、状态白名单、归档识别前缀，一律来自下列**四处数据源**。唯一守门闸门 =
`verify/verify_no_policy_hardcode.py`（offline，纳入套件；豁免须在
`verify/policy-hardcode-exemptions.json` 写明 `category` + `reason`，**不提供整文件豁免**）。

> **闸门能力边界（诚实标注，2026-09-23 二查实测后补）**：该探测器是 AST 判据，能抓
> 角色集合/字典字面量、成员与等值判定、路径清单、状态白名单；**抓不到**字符串拼接
> （`"code-"+"review"`、`join(...)`）与一切非字面量取值。**角色名判据 = 仓库实际存在的
> spec 文件名**（而非"像小写连字符词"——后者实测误报 18 条）。因此它**不是**完备的守门人：
> 真正的防线是"政策只有一处真源 + 封闭世界自检"，探测器只是**回归拦截**。

| 数据源 | 放什么 | 例子 |
|---|---|---|
| `agents/fanout.json` | **流程需求**：关闭流水线有哪些步骤、每步 role、必填 target、是否产出账本 run（`close_ledger`/`close_targets`） | 加一条"安全检查"步骤 = 加一条 JSON 记录 |
| `agents/functions/<role>.md` frontmatter | **角色属性**：`scope_required`（是否必须声明 scope 来源）、`coverage_window`（是否参与 C3 覆盖） | 新增角色 = 新建 spec + 显式声明两字段 |
| `agents/policy.json` | **阈值与开关**：偏离理由最小长度、scope 引用前缀、覆盖路径清单、ruff 规则分级（含 **C 级棘轮 caps**：`lint_readability_ratchet` 的计数上限 + `measured_at` + `review_by`，只许下调）、归档识别前缀、**账本状态机**（`ledger_status`：状态集合/终态/流转/不可采信态）、C3-T 例外表路径与 doc-only 规则 | 调阈值 = 改一个数字 |
| `agents/policy/coverage-exceptions.json` | **C3-T 覆盖例外**：sha 钉死 + class + reason（表落后 → 闸门默认 FAIL 并点名） | 见该文件 `_rules_of_engagement` |

**三条不变式**（`verify/verify_close_readiness.py` 的判据，取代原先"按角色逐条写死"）：

- **C1 声明完备**——凡产出评审结论的 run 必须有 scope 声明（外部引用或自选理由）；
- **C2 指涉可核**——任何外部引用必须解析到"存在且处于可用终态"的对象；账本出现**无 spec 的 role** 即 FAIL（**不认角色名**）；
- **C3 覆盖闭环**——`git rev-list <锚点>..HEAD` 的**每个提交**必须有归属（run 窗口 / 例外表 / doc-only）。

**为什么"删声明"绕不过去（封闭世界）**：闸门枚举 spec 目录（不由政策自证），
**每个 spec 必须显式声明** `scope_required`/`coverage_window`——缺声明是**报错**而非放行；
`fanout.json` 的每个步骤 role 必须有 spec；`policy.json` 出现无人读取的键也算漂移（死数据）。
该自检由 `verify/agent_policy.py::closure_problems()` 提供，并在两个闸门的"自检 ⓪"里断言为空。

**锚点自动化（不再手抄）**：`agent-ops.py register` 记 `coverage_anchor`（默认当前 HEAD）、
`finish` 记 `covers_through`，于是每个 run 自带 `(anchor, through]` 覆盖窗口；
Sprint 文档里的 `三查锚点` 只用于**关闭判定**，不再是覆盖真源。

**关闭窗口的起点 = 本次关闭的「作用域 run」（B1，2026-09-25 close-blocker 批）**：
`verify/verify_close_readiness.py::ledger_close_window` 取 `agents/policy.json::close_gate.scope_ref_step`
（本仓 = `scope` 步，即 `fanout.json` 的 `order: 1`）在账本里**最新**那条 run 的 `started_at`
作为窗口起点，C1 判定域与 §9↔账本区间比对**共用同一个窗口**。
- **为什么不是"各必填步骤最新 run 的最小值"**（改前口径）：一个**与本次关闭无关的历史步骤 run**
  就能把窗口拉到它自己那一刻（实测：Sprint-16 补跑的 `lessons-learned-058` 把窗口定到
  4 天前 ⇒ 中间的历史 run 被拖进判定域、当期缺口反而被淹没）。
- **作用域 run 缺席 = 窗口不可推导 ⇒ `None` ⇒ 不过滤（fail-closed 全域）**，**不退回**旧口径。
- **收窄 ≠ 放宽**：窗口内当期缺口仍逐条 FAIL；窗口外另有 `check_requirements`
  （按 `fanout.json` 必填步骤、**不看窗口**）兜底"本期流水线没跑过"。
- `close_gate.scope_ref_step` 是数据：**装载时**校验它指向一个存在且 `close_ledger=true`
  的步骤（拼错会让窗口恒不可推导、判定域静默退回全域 ⇒ 当场抛 `PolicyError`）。

**覆盖窗口的两族缺陷与受控回填（B2/B4，2026-09-25）**：短 sha 会让
`CoverageWindow.covers()` 恒 False ⇒ 该窗口**静默消失**（不报任何错）。两族输入都必须能**合法修**，
否则闸门报的是"不可修的红"＝永久噪音：

| 症状（闸门原文） | 受控回填命令 | 约束 |
|---|---|---|
| `[C3-窗口] … 不是完整 40 位 sha` | `agent-ops.py set-anchor <run_id> --anchor <sha>` 或 `--covers-through <sha> --reason <理由>` | sha 规范化成完整 40 位、解析失败 fail-closed、`--reason` ≥10 字符、两端口**全部解析成功后才落库**、每次**实际变更**追加 `anchor_backfills`（含 `field`/`from`/`to`/`reason`/`by`）；**同值 = 无操作**（假留痕比无留痕更坏） |
| `[C1] 评审类 run … 未声明 scope 来源` | `agent-ops.py set-scope <run_id> --source self-chosen --deviation "<理由>" --reason <为什么回填>` | 校验**完全复用** `_validate_scope()`（与 `register` 逐条同口径）；`role` 取自账本行自身；每次实际变更追加 `scope_backfills` |

> **回填的是数据、不是判据**：不得为了让闸门变绿而在关闭闸门里开"逐条列名的例外"
> （那是把可修的账本缺口固化成长期放行规则），也**不得**回填一个未经证实的覆盖上界
> （例如 `--covers-through HEAD` 而该 run 实际没评审过那些提交——那是**伪造覆盖**）。

**空窗口语义按 run 类别分流（B3，2026-09-25）**：`coverage_anchor == covers_through`
（`register` 与 `finish` 落在同一提交）时：
- **作用域类 run 不承担内容覆盖** ⇒ 空区间**不判问题**。作用域类 = `close_gate.scope_ref_step`
  指向那一步的 role（本仓 `impact-assessment`）+ spec 声明 `coverage_window: none` 的 role。
  它只在 T0 界定本次关闭覆盖哪些变更，用"量内容覆盖的尺子"量它是结构性假红。
- **内容评审类 run**（spec 声明 `coverage_window: self` 的评审 role：`code-review` /
  `doc-audit` / `agent-onboarding-review`）声称覆盖内容却贡献 0 覆盖 ⇒ **仍判 FAIL** 并打印
  修复指引（`set-anchor --covers-through` 或重跑）。
- **短 sha 不在此豁免内**（另一族缺陷，任何 run 都判）。
- 语义真源 = `agents/policy.json::close_gate.coverage.scope_run_window`（缺键即 fail-closed）；
  判定**不按 role 名硬编码**：作用域类由 `scope_ref_step` 派生，其余由 spec frontmatter 派生
  （已用"把 `scope_ref_step` 改指别步 ⇒ 同一 role 判定翻转"做反向对照）。

**加东西时的正确动作（自查表）**：

| 要加/改 | 该改哪里 | 不该改哪里 |
|---|---|---|
| 新关闭步骤或新 target | `agents/fanout.json` | 任何 `.py` |
| 新角色 | 新建 `agents/functions/<role>.md` + 两个声明字段 | 任何角色名单常量 |
| 调阈值/路径/规则分级 | `agents/policy.json` | 脚本里的 `MIN_*`/`PATHS` |
| 覆盖归属例外 | `agents/policy/coverage-exceptions.json`（sha 钉死） | 闸门代码里的白名单 |
| 新增脚本的产物落点 | `agents/policy.json::artifact_paths` + `.gitignore`（**先确认已忽略**） | 仓库根 / 未忽略目录 / 逐条补 `.gitignore` |

**新脚本产物目录约定（TG-9，2026-09-25 交付｜Retro 行动项 ④）**：凡**新增或改动脚本**（`scripts/**`、`verify/**`、`src/**`、`paper-qa-script/**`）产出文件，产物一律写**已忽略路径**——运行态 JSON → `agents/runtime/`，日志/截图 → 已 gitignore 的 `verify/*.log`、`verify/*.png`，临时结果 → `%TEMP%`。**新增脚本前先确认产物路径已被 `.gitignore` 覆盖**，可核判据 = `git check-ignore --no-index <产物路径>` 退 0（写仓库根 = 直接在 `git status` 里多出未跟踪产物：本轮两次误入库 `verify_checkpoint_run.log`、`ci_fail_log.txt` 就是这个形态）。唯一真源 = `agents/policy.json::artifact_paths`（忽略根清单 / 已入库数据文件例外 / 临时落点写法 / 动态目标棘轮上限）；守门闸门 = `verify/verify_artifact_paths.py`（offline，纳入套件）：**源码里的写盘目标必须落在已忽略目录或 `%TEMP%`**，否则 FAIL 并逐条点名；**忽略根双向差集**——政策声明的每条根必须真被忽略（合成探针 `check-ignore` 命中，拼错即死配置）、`.gitignore` 里确有其行、且确有代码在用，反过来每个已被忽略的落点也必须能归到某条声明根上。**新脚本必须让产物落点可静态判定**（用模块级常量拼路径，别把落点交给函数参数/argv）：分解不出的"动态目标"按**文件**设上限，**未列入上限表的文件出现一处即 FAIL**，上限只许下调、到期（`review_by`）未重评也 FAIL。`.gitignore` 侧用**目录级 `dir/*` + `!` 白名单**（`agents/runtime/*` + `!agents/runtime/prices.json` + `!agents/runtime/tg14-baseline.json`）：**父目录被整体排除时 `!` 白名单不生效**（实测 `agents/runtime/` 写法下 `!prices.json` 仍判"已忽略"），故必须用 `dir/*` 形态才能同时表达"新产物默认忽略"与"数据文件入库"。反向对照（TG-6 ⑤"倒过来试"）：注入写仓库根的新脚本 → rc=1 点名；注入写默认落点的新脚本 → rc=0；并实测产物落入 `agents/runtime/` 后 `git status --porcelain` 为空。

**验收 case 与"证据形态"四件套（TG-6，2026-09-25 交付）**：任何**新验收 case / 新闸门**必须给出**四件套证据**——① **命令原文**（含解释器路径，如 `.venv\Scripts\python.exe verify\verify_x.py`）② **关键输出行**（点名失败项的**原文**，不接受只给结论或"读文档确认"）③ **退出码**（实测 rc，不是"应该会失败"）④ **反向对照**（同一判据在**未修复/旧实现或注入样本**上跑出 FAIL / 非零退出的记录——判据必须真能触发目标失效模式，同本节"交互类检查的反向对照规则"）。另：**新增 `verify/*.py` 闸门必须在成功路径打印一行可 grep 的机读证据行** `EVIDENCE: <脚本名> assertions=N rc=0`（失败与 SKIP 路径**不**打印——"跳过"不得冒充"通过"），供套件/CI/评审直接引用。**只对新增脚本生效，不回溯改造存量 20+ 脚本**；示范脚本 = `verify/verify_lint.py`（C 级可读性棘轮；其 `EVIDENCE:` 行的**具体计数随文件增删必然漂移，规范正文不得抄写**——见下条）。

**派生数字不得手抄（2026-09-25 交付，`TG-6` 尾批；根因＝一查 `run-2026-09-25-doc-audit-070` finding 1/2）**：文档里凡引用**派生数字**（卡数 / 文件数 / 脚本数 / 字节数 / 断言数 / C 级条数 / 棘轮计数），只有两种合法形态——**① 复现命令 + "以该命令输出为准"**；**② 标明时点的历史读数**（带 sha 或日期，并声明不得当作现值）。**写成"现测 <数字>"/"实测 <数字>"的当期主张即违规**——本 Sprint 实测：同一批闸门在同日 4 份文档里并存 3~4 个读数，无一与工具一致（断言数、C 级条数、卡数、字节数、脚本数五类全中）。**机检** = `verify/verify_derived_numbers.py`（offline，纳入套件；按文件设"违规处数"棘轮上限、只减不增，`review_by` 到期即 FAIL；含注入反向对照）。

**卡片来源与时间口径（2026-09-20 用户要求，全部 backlog 适用）**：卡除 卡号/主题/点/状态/Sprint 外，**来源必须带类型前缀**区分"原规划"与"后新增"，时间字段一律用**网络时间（UTC+8）**：

| 前缀 | 含义 | 例 |
|---|---|---|
| `[规划]` | 原规划（roadmap/预研阶段即存在的卡） | `[规划] F-AC8（F2 验收⑥）` |
| `[用户插入]` | 迭代中由用户新增的需求/要求 | `[用户插入] 前端运行参数显式配置面` |
| `[Bug]` | 缺陷（用户走查、三查、评审、自测发现均可） | `[Bug] 复制按钮状态串台` |
| `[走查]` | 用户走查/验收提出的疑问、改进建议 | `[走查] 报告时效与依据变更治理` |
| `[三查]` / `[评审]` | 内部评审（impact-assessment / doc-audit / code-review / lessons-learned）发现 | `[评审] load_state fail-open` |

时间写法统一 `YYYY-MM-DD（UTC+8）`（**取网络时间校准，不得用本机时区**——本机为 UTC+9，直接取本地时间会与仓库口径差一天）；历史卡按原样保留、不回填。

**日期必须每轮核验（2026-09-23 事故后补规，用户当场指出）**：新写/更新的文档日期一律取**当次**网络时间核验值（HTTP `Date` 响应头 → UTC+8），**不得沿用会话起始日期**（本次事故：跨日后仍按会话起点写 `2026-09-21`，实际已是 `2026-09-23`）。**可核判据**：文档内日期与该文件最近一次 `git log -1 --format=%cI` 的 committer 日期相差 **>1 天** → 记 `R2`（卡片内容漂移）告警并**当日更正**；更正方式为加"日期口径更正"注记，**不重命名文件**（避免链接churn）。

**卡片与文档的对应关系·术语与引用纪律（2026-09-21 用户提出结构性问题后立规）**：

用户原话："`phases` 下的所有文件夹，**单个卡片应该对应且唯一对应一个独立文档**。现在卡片内容全都记录在 backlog 中，有的卡片内容散落在 sprint 文档中到处都是。一旦卡片内容更新了其他几处万一有的地方漏了就直接造成文档内容漂移"。

1. **术语（强制）**：**`台账` 只指独立文件**（例：`TG-11` 的 `phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD`）。**写在卡片单元格里的清单不得称"台账"**，一律叫"**卡内实例清单**"（此前主代理混用该词，导致用户找不到对应文档——2026-09-21 用户指出）。
2. **唯一真源**：卡片的**正文、根因、机制、实例清单**的唯一真源 = 该卡所在的 `phases/<阶段>/backlog.MD` 卡片行（**`TG-14` 迁移后**改为 `phases/<阶段>/cards/<卡号>.md`，见卡 `TG-14`——该机制已于 2026-09-21 由 `TG-12` 的候选 N7 **提升为独立卡**）；**卡状态**的唯一真源 = 卡片行的"状态"列。
3. **引用纪律**：Sprint 文档 / roadmap / ROADMAP **只引用卡号 + 一句话摘要 + 该 Sprint 自身的过程记录（计划、看板、燃尽、证据、Retro、评审记录）**，**不得复制卡片正文**（根因/机制/长清单）。需要展开时给链接，不复制。
4. **漂移防线**：上述纪律由 `verify/verify_card_index.py` lint 强制，**判据逐条对应**——① 索引行 ↔ 卡片文件**双向**一一对应（含孤儿行/孤儿文件/重号）；② 卡号 ↔ 文件名一致（`card:` 字段）；③ 卡文件必备节在位；④ **Sprint 文档出现卡正文段落即 FAIL**（全文行级指纹比对，且堵掉"≥61 字符填充"规避）；⑤ 表格结构一致；**⑥ 状态三处同词**（卡文件 `## 状态` ↔ 索引行"状态"列 ↔ 该卡所属 Sprint 的**看板行**；状态词表与否定前缀是政策数据 `card_index.status_aliases` / `negation_prefixes`，匹配取最长别名优先，看板不可定位时只 WARN）；**⑦ 卡库存基线一致**（`agents/runtime/tg14-baseline.json` 的 `totals` 必须等于 `scripts/card-inventory.py` 的**当次**输出——该文件自称"当前真值快照"，刷新义务从此有执行点）。全部判据带**反向对照**自检（8 条）。
   **落地与更正（2026-09-25，关闭期）**：`TG-12`/N7 的机制已在 Sprint-17 由 `TG-14` 交付（`--strict` 自 2026-09-25 起即默认档）；**⑥ 是补做的**——一查 `run-2026-09-25-doc-audit-070` finding 5 指出"本条承诺了『状态与 Sprint 引用一致』但脚本里没有这条判据"（承诺未实现），同日补实现并当场抓出 `A-M12` 卡（卡文件写"工具已交付"、索引行写"候选"）的真实冲突。

**Markdown 结构编辑的前后守卫（A-M12，2026-09-25 交付；Sprint 归属仍为 Sprint-18/G2，仅交付提前）**：凡改动 Markdown **结构**（标题行 / 表格块）的编辑，一律 `scripts\structure-guard.py snapshot`（编辑前）→ 编辑 → `scripts\structure-guard.py verify`（编辑后）。`verify` **只对丢失/变形报错**（标题/锚点行的**数量减少**即"被删"、标题级别变化、表格块消失 / 列数变化 / 行数减少、文件消失），新增标题/表格/文件一律放行，**同一行就地改写**（数量不变、文本变了——如就地 retarget 一处 `§` 引用）只报 `[修改]` 也放行 ⇒ 它是**无条件动作**，不是"感觉动了结构才跑"；`rc≠0` 即先修再继续，有意改结构则人工确认后重做 `snapshot` 立新基线。该机制用 **5 次真实 R1 输入**做过复跑验证（另含反向对照：表格新增行必须放行 / 删行·改列数·删标题必须拦下、就地改写必须放行且不得误报"被删"、标题级别变化必须拦下）（`.venv\Scripts\python.exe scripts\structure-guard.py --replay` → `ALL PASS (N assertions)`，N 以实测输出为准；CI 每轮跑该自检）。**执行点声明（2026-09-25 一查 finding should-fix 3 要求显式标注）**：本条是 **prose-only**——"某次编辑前是否跑过守卫"**无机检**（无闸门能从事后状态反推编辑动作）；**可机检的部分**只有守卫自身的语义（`--replay` 的 5 类 R1 反向对照 + 真文件零改动摘要，CI 每轮执行）。

**子代理派单纪律（用户 2026-09-25 定规；反例留档 = `phases/agents-infra/2026-09-25-subagent-dispatch-failure-modes-case.MD`）**：**与子代理派单相关的一切漏洞/问题/事故，今后一律作为 `agents-infra` 的反例留档**——一案一节追加进上述文件（必须含 **6 要素**：现象 / 证据（可核）/ 根因 / 机制 / 反向对照 / 复用面），并同步本节规则。当前已落 7 条：
1. **不手抄标识符**：prompt 与命令里**禁止手抄 sha**（及其他可解析标识符）——由执行者 `git rev-parse` 或使用 CLI 默认值；工具侧必须解析+规范化+失败 fail-closed（反例＝短 sha `092a2f78` 让 3 个 run 的覆盖窗口静默作废）。
2. **中断可恢复**：修复/实现类派单**同样先登记 run** 并把任务清单与进度写入 run 目录（中断＝无遗言，仓库里必须看得出哪部分是半成品）；**同一批派单不得共享文件**（反例＝三个修复批并发改同一文件、余额耗尽后留下 `NameError` 半成品）。
3. **对照必须打真实入口**：新对照必须打**真实函数 / 真实仓库 / 真实子进程**；注入中间变量或用副本自造阈值的对照**视为未做对照**（反例＝B5 注入 `older_anchors` 躲过 `_is_ancestor` 的真实缺陷）。
4. **按提交态复核**：任何"已修"结论的复核第一步是 `git show <sha>` 对比**提交态**；**报告与提交信息都只是主张**（反例＝报告称已修但提交里查不到；提交信息里断言数 10 vs 实测 13）。
5. **环境等价要连"能力"一起复制**：CI 等价模拟用 **`git clone`**（含 `.git`、全历史）；只复制文件的模拟（`git archive`）**不得**作为等价证据（反例＝archive 树假失败 2/24，clone 树 24/24 全绿）。
6. **派单前先复现前提**：凡以"某机制/闸门会生效"为前提的派单，先做最小复现；做不到就在 prompt 里要求执行者**先验前提、不成立立即回报**（反例＝我假设"登记 run 即归属覆盖"，而 C3 引擎当时 14/14 窗口全失效）。
7. **留档义务**：上述任一情形发生时，**当日**追加案例（不许只写在对话里）。
8. **机制缺口同样留档（用户 2026-09-25 追加定规）**：凡**闸门/机制类**缺陷（自指断言、空转与"没查也说查过了"、静默放宽、判定域错、读数手抄、上限自证…）**一律作为 `agents-infra` 反例留档**，落点 = `phases/agents-infra/2026-09-25-gate-mechanism-failure-modes-case.MD`（一案一节、6 要素齐全：现象/证据/根因/机制/反向对照/复用面），并在本节登记规则；派单类仍落姊妹文件 `2026-09-25-subagent-dispatch-failure-modes-case.MD`。**判据的"自述"不算证据**（闸门 docstring 写"真数据零假阳性"，实测 99 项里 98 项假红 ⇒ 已作为该文件案例 7）。
9. **提问纪律（用户 2026-09-25 要求；登记册 = `docs/6-DECISIONS.md`，卡 = `TG-20`）**：向用户提 **clarification question 之前必须先查登记册**，确认该问题是否已裁决；提问**必须自带三件事**——**(a) 已裁决项**（条目号 ＋ 原文摘引）、**(b) 本次未被覆盖的原因**、**(c) 证据**（`path:line` / 命令 / 读数）。**禁止裸提问**（只给选项、不给上下文与既往裁决）；出现即按第 8 条作为流程事故留档。理由（用户原话）："每次你问我问题不带上下文的时候我就得翻我们的对话记录，还得提醒你是不是之前做过类似确认/是不是缺少啥内容，我已经厌倦了这么做"。
10. **关闭税读数必须由工具派生（2026-09-25 立规；`TG-19` M-E）**：Sprint 文档的 §8 数据节必须带一行**机读读数**：
    `关闭税读数: code_major=<N> code_critical=<N> doc_items=<N> 来源=<run_id>,<run_id>,…`
    这三个数**只能**由 `verify/verify_close_tax_reading.py` 从**报告文件**派生（`code-review` 报告 `## Graded findings` 的 graded 行数；`doc-audit` 报告 `## Must fix` + `## Should fix` 的编号条数），**禁止手抄**。
    执行点：`verify/verify_close_tax_reading.py --sprint <Sprint 文档>`（`--sprint` 缺失即 FAIL 并点名差值；无该行 ⇒ 显式 SKIP，不是 PASS）。**由来（真实事故）**：Sprint-17 的记录曾抄进上一个 Sprint 的数字（文档项 `12` 实为 `11`、"19 条"实为 `21`），两个 Sprint 的 must-fix 数恰好都是 8 ⇒ 抄错后**算术自洽**，一查也没抓到（见 `sprint-17.md` §9.5、机制反例档案例 9）。

**交互类检查的反向对照规则（2026-09-21 用户拍板，称"倒过来试试"）**：新增的 **GUI / 交互类**检查**必须先在"未修复（或旧实现）"的代码上跑出 FAIL**，再在修复后转 PASS，并把该反例写进检查脚本注释与验收指南。理由：只证明"改完能过"不构成验证——`gui_check_s5/s7` 用程序化 `.click()` 点运行按钮，**结构上无法触发** F-AC13 的"首次点击被拖拽吃掉"，于是该 bug 存活了 4 个 sprint。记录在 `TG-6` ⑤。

**子代理中断/接管必须留痕（2026-09-21 用户对"运行时间变短/中途被停"提出疑虑后新增）**：主代理**中断（`interrupt_agent`）、杀掉子代理派生的进程、或按 §4.2 接管**时，必须记三件事——**何时、为什么、影响范围**（哪一轮评审/验证因此缺失、后来如何补做）。写入 Sprint 文档 §5/§9。**执行点声明（2026-09-25 一查 finding should-fix 3 要求显式标注；同日把"可机检的那半"补齐）**：① **机检部分**——`scripts/agent-ops.py interrupt` 强制要求 `--reason` 与 `--impact`（缺任一即 fail-closed，不再默认空串），且 `verify/verify_agentops.py` **UC-21** 断言"账本中每条 `interruptions[]` 事件的 `reason`/`impact` 均非空 + `interruptions_count` 与数组长度一致"（含注入空 reason 的反向对照）；② **prose-only 部分**——**"影响范围是否如实、是否与后来补做的情况一致"无机检**（判据只能判"非空"，判不了"对不对"），故该条**只做了一半机械化**，引用时须知边界。
> 依据：2026-09-20 我曾误杀复核子代理派生的套件进程树 3 次、并主动 `interrupt` 它 1 次（端口 8787 争用 + 避免在用户走查期间干扰前端）→ 其 round-3 因此顺延；若当时没留痕，账本里只会看到"首轮 53 秒 succeeded"，**看不出被中断过**（关联 `TG-10`：多轮次记录失真）。

**预研上下文传递（2026-08-31 制度化，用户建议）**：

1. 探讨性预研（涉及用户选择/确认的调研讨论，如方案菜单、采纳范围、成本拍板）在结束或中断时，**必须落盘**为预研笔记（**仅 windows 分支维护**，main 无此目录 → 注入规则在 main 为 no-op）：按领域归档 `docs/iteration/pre-research/<领域>/<日期>-<主题>.MD`（领域 = tech/product/marketing，跨领域治理笔记放根目录；**一领域 = 一 agent = 一账本 role = 一笔记目录**，隔离与侧重点见 `docs/iteration/pre-research/2026-08-31-domain-governance.MD`）。要素：背景 / 现状证据 / 结论（方案菜单+推荐）/ 来源 / **用户决策记录（chronological）** / 注入指引；落盘后同步更新 `docs/iteration/pre-research/README.md` 追溯索引。
2. planning 时：任务主题命中某预研笔记（按笔记"注入指引"的关键词匹配）→ **笔记作为 tech-research 的 `context` 输入，并在任务分解前注入规划上下文**；开卡时卡片链接对应笔记（见 `agents/fanout.json` planning_pipeline 的 `pre_research` 字段）。
3. **基线规则**：tech-research 以笔记记录的既定决策为基线——不重复调研已决路线、不静默改向；发现与既定决策矛盾 → 报告"翻案建议"交用户裁决，不得自行推翻。
4. 目的：避免方案路线决策在后续流程中**重复出现/前后矛盾**，预研结论与用户确认是规划管线的资产而非一次性对话。

**调研工作流分级与证据落档（M16，2026-09-12 落地；用户 2026-09-07 拍板 P1~P3）**：

1. **三级深度路由**（`agents/fanout.json` planning_pipeline 的 `depth` 字段）：**quick 工程级**（实现问题/工具用法/快速查证；3~5 源、1 维；**主代理直接执行**，零子代理成本——P2）/ **expert 领域专家级**（方案选型/最佳实践/跨方案对比；6~10 源、≥3 维、对比矩阵；默认档，子代理）/ **scholar 研究学者级**（架构决策/长期路线/发布级判断；≥12 源 + 全 tradeoff + 反向证据）。**阈值一律在 spec 可配置参数节**（P3：可调，不写死）；级别由任务难度自动建议、**用户可覆盖**；兼容旧别名 normal=expert、deep=scholar。
2. **决策证据落档（唯一真相）**：expert/scholar 档的 run 目录必须含 `context.md`（输入上下文快照：问题/深度/注入的预研基线与用户决策/约束/网络时间日期）、`evidence/<nn>-<slug>.md`（每条引用 = URL + 来源层级 + 抓取时间 + **逐字原文段落** + 支撑点；抓取失败须记 reason）、`reasoning.md`（证据→结论推导链 + 采信/排除理由 + 未决风险）。
3. **段落级溯源**：报告 §7 证据索引表把每条结论映射到 evidence 文件与段落摘录，供后续"引经据典"式讨论直接回溯。
4. **归档门禁**：`verify/verify_archive.py <run_dir> --depth <tier>`（缺件/空证据/字段缺失/索引表未引用/**索引表点名但磁盘缺失（悬空引用）**；交叉引用判定**限定在证据索引表区间内**、文件名**大小写不敏感** → fail-closed，退出非 0）；报告注入规划上下文前须过门禁（`agents/fanout.json` 的 `archive` 字段）。
