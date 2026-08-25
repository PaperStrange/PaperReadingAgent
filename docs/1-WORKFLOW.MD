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

规则：

1. **新增知识先归类**：属于流程 → 1，属于结构 → 2，属于经验/教训 → 3；无法归类才新开编号文档。
2. **变更同步**：代码、依赖、模型、路径等发生变更时，必须同步更新对应文档。
3. **macOS / Windows 双轨**：两仓库文档结构一致（同名三件套），内容分别描述各自平台；共性内容允许重复但不允许互相矛盾。
4. 架构图统一用 Mermaid（GitHub 原生渲染），必要时附文字版时序图。

## 2. 开发规范

- **改动范围**：Windows 移植只允许改 `PaperReading-Windows`；原文件仅当发现原代码缺陷时修改（对应 macOS 仓库同文件）。
- **保留原代码**：所有被替换的 macOS 原始配置/路径，用 `[macOS original]` 注释保留，**不删除**。
- **密钥**：一律读取环境变量 `OPENAI_API_KEY`（或 config 节点 `params.api_key`），默认值可写但正式提交前确认；旧密钥以注释保留。
- **依赖锁定**：与 macOS `paper-qa/uv.lock` 对齐（fhlmi==0.42.1、litellm==1.76.1）；直接 `pip install` 会解析到更高大版本，需显式锁定。
- **Python**：3.11+（本机 3.13）；**Node**：18+（本机 23）。
- **编码**：Windows 控制台 GBK 会导致中文乱码，脚本/命令行建议 `PYTHONUTF8=1`。
- **提交**：新文件夹内 `git commit`；`node_modules/`、`.venv/`、`dist/`、`__pycache__/`、`data/parsed/*.jsonl`、`._*`（AppleDouble）不入库（见 `.gitignore`）。

## 3. 项目管理（分支与远程）

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（macOS 原版）｜`windows`（本仓库 Windows 移植版）
- 约定：每类工作一个提交；提交信息用 `type: 说明`（如 `fix:` / `docs:` / `feat:`）。

## 4. 运行手册（Windows）

### 4.1 一次性环境准备

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
# 与 mac uv.lock 对齐的锁定版本
.\.venv\Scripts\python.exe -m pip install "fhlmi==0.42.1" "litellm==1.76.1"
# 前端依赖
cd paper-qa-script\reactflow-paperqa-prototype\frontend
npm ci
```

### 4.2 启动（三终端）

```powershell
# 终端 1：FastAPI 后端（127.0.0.1:8787）
.\scripts\start-backend.ps1
# 终端 2：前端（127.0.0.1:5173）
.\scripts\start-frontend.ps1
# 终端 3（可选）：Streamlit 调试 UI（127.0.0.1:8501）
.\scripts\start-streamlit.ps1
```

浏览器打开 http://127.0.0.1:5173 。

### 4.3 使用流程（ReactFlow 原型）

1. 打开前端 → **1) Config** 节点：确认/填写 `api_key`（DeepSeek key，`.env` 已含默认值）、`paper_directory`（默认 `data/pdf`，相对后端 cwd）。
2. 依次或 `Run All (Left-to-Right)` 执行：**Load Index → Retrieve → Parse Chunk Embed → Gather Evidence → Generate Answer**。
3. 点击任一节点，右侧"函数子画布"展示该步骤函数调用图；节点卡片可展开文本/页码预览图/中文翻译。
4. 顶栏 `New Run ID` 分组一次实验；`New Session` 重建会话（会话为后端内存态）。

### 4.4 命令行脚本

```powershell
.\.venv\Scripts\python.exe .\paper-qa-script\manual_index_paper.py     # 建索引 + 交互问答
.\.venv\Scripts\python.exe .\paper-qa-script\manual_test_internet_connection.py  # 连通性
```

### 4.5 验收脚本

```powershell
$env:OPENAI_API_KEY = "<DeepSeek key>"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py   # 8 项冒烟（离线）
.\.venv\Scripts\python.exe .\verify\verify_e2e.py     # 全链路（真实 API）
.\.venv\Scripts\python.exe .\verify\verify_agent.py   # Agent 流程 + 翻译
```

详见 `verify/README.md` 与 `docs/3-LEARNED.MD` 的验证记录。
