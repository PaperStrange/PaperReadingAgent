# 1-WORKFLOW —— 项目工作流（开发规范 / 知识管理 / 项目管理）

> 适用范围：`PaperReading-Windows`（分支 `windows`，由 macOS 版 `mac` 分支移植而来）。
> 本文件记录**怎么组织项目、怎么开发、怎么运行**；架构见 `2-ARCHITECTURE.MD`，踩坑与经验见 `3-LEARNED.MD`。

---

## 1. 知识管理规范

本仓库文档统一存放在 `docs/`，按"一类问题一个文档"拆分，根目录 `README.md` 只做入口并引用以下文档：

| 文档 | 负责回答 |
|---|---|
| `docs/1-WORKFLOW.MD` | 开发规范、知识管理规范、项目管理、运行手册 |
| `docs/2-ARCHITECTURE.MD` | 系统架构、模块职责、数据流、模型与存储约定 |
| `docs/3-LEARNED.MD` | 开发经验教训、踩坑记录、验证记录、已知限制 |
| `docs/iteration/` | 敏捷迭代：`sprint/<日期>-sprint-N.md`（Sprint 计划/执行/Retro + **项目管理与关闭证据**）+ 迭代中新增的其它项目文档 |

规则：

1. **新增知识先归类**：属于流程 → 1，属于结构 → 2，属于经验/教训 → 3；无法归类才新开编号文档。
2. **敏捷迭代**：功能/体验类工作按 Sprint 推进，Sprint 文档统一放 `docs/iteration/sprint/`，迭代中新增的项目文档放 `docs/iteration/`（详见 §4）。
3. **变更同步**：代码、依赖、模型、路径等发生变更时，必须同步更新对应文档。
4. **macOS / Windows 双轨**：两仓库文档结构一致（同名三件套），内容分别描述各自平台；共性内容允许重复但不允许互相矛盾。
5. 架构图统一用 Mermaid（GitHub 原生渲染），必要时附文字版时序图。

## 2. 开发规范

- **改动范围**：Windows 移植只允许改 `PaperReading-Windows`；原文件仅当发现原代码缺陷时修改（对应 macOS 仓库同文件）。
- **保留原代码**：所有被替换的 macOS 原始配置/路径，用 `[macOS original]` 注释保留，**不删除**。
- **密钥**：一律读取环境变量 `OPENAI_API_KEY` 或本地 `paper-qa-script/.env`（以 `.env.example` 为模板），**代码与文档中禁止出现真实密钥**；`.env` 已被 `.gitignore` 忽略。
- **服务商切换**：`PAPERQA_PROVIDER=deepseek|dashscope|openai` 统一切换；各服务商的模型/向量化/密钥映射集中在 `paper-qa-script/provider_config.py`（显式参数优先级更高）。
- **安全**：后端 CORS 仅允许本地前端来源、仅监听 `127.0.0.1`；前端渲染依赖 React 默认转义 + Streamlit DOT 转义；如需公开仓库，先确认无密钥残留（`git grep` 全历史）并轮换曾暴露的密钥。
- **依赖锁定**：与 macOS `paper-qa/uv.lock` 对齐（fhlmi==0.42.1、litellm==1.76.1）；直接 `pip install` 会解析到更高大版本，需显式锁定。
- **Python**：3.11+（本机 3.13）；**Node**：18+（本机 23）。
- **编码**：Windows 控制台 GBK 会导致中文乱码，脚本/命令行建议 `PYTHONUTF8=1`。
- **提交**：新文件夹内 `git commit`；`node_modules/`、`.venv/`、`dist/`、`__pycache__/`、`data/parsed/*.jsonl`、`._*`（AppleDouble）不入库（见 `.gitignore`）。

## 3. 项目管理（分支与远程）

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`main`（跨平台融合/集成分支）｜`mac`（macOS 原版）｜`windows`（Windows 移植版）
- 约定：`windows` / `mac` 各自改动后，通过 **Pull Request 合并到 `main`**；每类工作一个提交，提交信息用 `type: 说明`（如 `fix:` / `docs:` / `feat:`）。

## 4. Sprint（迭代）项目管理与关闭标准

> 适用：所有功能/体验类改动。Sprint 文档统一放 `docs/iteration/sprint/<日期>-sprint-N.md`；
> 迭代中新增的其它项目文档（如架构调整、性能分析）放 `docs/iteration/`。

### 4.1 Sprint 生命周期

`Plan（目标+Backlog+验收标准）` → `Dev（按 US 拆解实现）` → `Verify（可运行验证）` → **`Close（关闭评审）`**。

### 4.2 Sprint 关闭：必须有足够 solid 的证据 + 理由

**关闭 Sprint 的前提是"证据充分、理由明确"。证据需同时包含图文（例如浏览器截图）与文字，并附理由，统一写入该 Sprint 文档的「项目管理与证据」板块。** 缺少证据或无法自证"达成目标"的项不能标记为 done。

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

### 4.3 Sprint 文档模板

见 `docs/iteration/sprint/_template-sprint.md`。关闭时把第 4.2 节的**项目管理与证据**板块填实。

## 5. 运行手册（Windows）

> **新用户请先看根目录 `README.md` 的"本地部署"**（含先决条件、一步步部署、验证安装、故障排查）。
> 本节约为开发者的完整运行手册，命令与 README 一致。

### 5.1 一次性环境准备

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
# 与 mac uv.lock 对齐的锁定版本
.\.venv\Scripts\python.exe -m pip install "fhlmi==0.42.1" "litellm==1.76.1"
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

浏览器打开 http://127.0.0.1:5173 。

### 5.3 使用流程（ReactFlow 原型）

1. 打开前端 → **1) Config** 节点：确认/填写 `api_key`（DeepSeek key，`.env` 已含默认值）、`paper_directory`（默认 `data/pdf`，相对后端 cwd）。
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
$env:OPENAI_API_KEY = "<DeepSeek key>"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py   # 8 项冒烟（离线）
.\.venv\Scripts\python.exe .\verify\verify_e2e.py     # 全链路（真实 API）
.\.venv\Scripts\python.exe .\verify\verify_agent.py   # Agent 流程 + 翻译
```

详见 `verify/README.md` 与 `docs/3-LEARNED.MD` 的验证记录。
