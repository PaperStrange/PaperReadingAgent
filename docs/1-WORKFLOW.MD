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
| `docs/iteration/` | 敏捷迭代：`sprint/<日期>-sprint-N.md`（Sprint 计划/执行/Retro + **项目管理与关闭证据**）+ 迭代中新增的其它项目文档 |

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
- **PR 工具**：创建/更新/合并 PR 一律用 `scripts\github-pr.ps1`（create/patch/merge/get 子命令，UTF-8 安全）。**禁止**直接用 `Invoke-RestMethod` 传中文字符串 Body（PS 5.1 会按 GBK 编码 → GitHub 乱码，见 `3-LEARNED.MD` 1.18）。

## 4. Sprint（迭代）项目管理与关闭标准

> 适用：所有功能/体验类改动。Sprint 文档统一放 `docs/iteration/sprint/<日期>-sprint-N.md`；
> 迭代中新增的其它项目文档（如架构调整、性能分析）放 `docs/iteration/`。

### 4.1 Sprint 生命周期

`Plan（目标+Backlog+验收标准）` → `Dev（按 US 拆解实现）` → `Verify（可运行验证）` → **`三查（固定动作）`** → **`Close（关闭评审）`**。

### 4.2 Sprint 关闭：必须有足够 solid 的证据 + 理由

**关闭 Sprint 的前提是"证据充分、理由明确"。证据需同时包含图文（例如浏览器截图）与文字，并附理由，统一写入该 Sprint 文档的「项目管理与证据」板块。** 缺少证据或无法自证"达成目标"的项不能标记为 done。

#### 三查（每个 Sprint 关闭前的固定动作，2026-08-30 起制度化）

| # | 检查 | 内容 | 产物 |
|---|---|---|---|
| 一查 文档 | 全量文档一致性审计 | 死链/陈旧事实（路由数、行数、组数、provider 清单等）/跨文档矛盾/缺失知识；**4-ALGORITHM.MD 逐条对照代码**（其 §12 防漂移清单） | 问题清单（必须修/建议修） |
| 二查 代码 | windows + main 双分支 code review | 正确性/安全/SSOT/兼容性/架构分层；main 侧重合并完整性与悬空引用 | 分级问题清单（critical/major/minor/nit） |
| 三查 环境 | 工作区与功能完整性 | `git status` 零残留、本地已合并分支清理、.gitignore 覆盖、回归（smoke/e2e/新增端点/GUI）全绿 | 清洁确认 + 回归输出 |

> 三查可委托评审代理并行执行；**发现项必须修复闭环后（修复 → 回归 → 文档同步 → PR 同步 main）才允许 Close**；结论写入该 Sprint 文档的「评审/同步记录」节。

#### 证据 checklist（按需选取，尽可能覆盖）

| 类别 | 示例 |
|---|---|
| 🖼️ 功能截图（before/after） | 浏览器截图（面板缩放、全屏、lightbox、按钮、连线效果） |
| 🖼️ 运行/接口输出 | 后端 API 返回、`verify_*.py` 实测输出（时间/状态/样本）、日志 tail |
| 🖼️ 命令与产物 | `npm run build`、pytest / e2e 结果、生成的报告 |
| 📝 验收用例 | 对应 Backlog US-* 的验收标准逐条说明，标注通过/未通过 |
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

### 4.3 Sprint 文档模板

见 `docs/iteration/sprint/_template-sprint.md`。关闭时把第 4.2 节的**项目管理与证据**板块填实。

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
| **插队 Sprint** | 用户实测驱动的**成批修复**（≥3 个同源问题或合计 >8 点），须用户提出或明确批准 | 同新 Sprint 流程，sprint 文档标注"插队"，roadmap §7 实录登记 |
| **Bug（直接修复）** | 单点根因、不改设计/接口/协议、≤2h、纯缺陷或回归 | `fix:` 提交 + 对应回归（smoke/e2e/GUI 按需）+ 有教训记 `3-LEARNED` + PR 同步；**不写 sprint 文档** |
| **日常维护** | 文档勘误/知识管理、依赖 pin、清理/环境 SOP、验证脚本维护、≤5 点且行为不变的小重构 | `docs:`/`chore:` 提交 + PR 同步；不写 sprint 文档 |

**严重度分诊（决定时效，不决定归属）**：`Blocker`（主流程不可用/数据损坏）→ 立即 fix 或立即插队；`Critical`（核心功能失效，有规避）→ 当日内；`Major`（功能缺陷/无规避）→ 纳入最近 sprint 或批处理；`Minor/Trivial`（体验/文案/样式）→ backlog 候选，凑批后进插队 sprint。

**非计划工作预算**：每个 Sprint 预留 **~20% 产能**应对 Blocker/Critical 缺陷与紧急维护；超出预算则先补计划再执行（新 sprint 或插队 sprint），**禁止长期游离于流程之外**。

**边界澄清（本项目经验）**：单文件"改了目录没生效"这类**流程缺陷**，若修复需要前后端协同+新增决策规则（如 Sprint-5 的自动重跑+状态失效），属于插队 sprint；若只是文案/样式单点问题，属 Bug/维护。判断先例见 `docs/iteration/sprint/2026-08-30-sprint-4.md`（插队）与 Sprint-5（插队，后补三查整改）。

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
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py   # 服务商切换/路由
.\.venv\Scripts\python.exe .\verify\verify_e2e.py               # 全链路（真实 API）
.\.venv\Scripts\python.exe .\verify\verify_embed_load.py        # Embedding 三步
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py        # remote 数据源全链路（联网）
node .\verify\gui_check.mjs          # GUI 全链路（需前后端已启动）
node .\verify\gui_check_remote.mjs   # GUI remote 数据源（需前后端 + 联网）
```

详见 `verify/README.md` 与 `docs/3-LEARNED.MD` 的验证记录。
