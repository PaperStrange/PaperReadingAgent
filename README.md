# PaperReading（跨平台融合版）

> 基于 **PaperQA2** 的论文问答可视化原型：把论文 PDF 放入目录，在浏览器 GUI 里按
> 6 节点流水线完成**索引 → 检索 → 解析/分块/向量化 → 证据摘要 → 带引用的上下文回答**，
> 并提供函数级运行时追踪与 PDF 页码预览。
> 本分支为 `main`，是 `windows` 与 `mac` 两个平台分支的**融合版本**，Windows / macOS / Linux 均可运行。

---

## 功能一览

| 功能 | 说明 |
|---|---|
| 📄 论文入库 | 把 PDF/TXT/MD/HTML 放入 `data/pdf/`，自动解析文本、图片、公式/表格媒体 |
| 🔍 全文 + 向量索引 | Tantivy 全文索引 + 向量化（本地或 API，随服务商切换，`~/.pqa/indexes`） |
| 🧩 可视化流水线 | ReactFlow 画布 6 节点：`config → load_index → retrieve → parse_chunk_embed → evidence → answer`，可单步 / 一键串行 |
| 📊 函数级追踪 | 每一步展示 paperqa 内部函数调用图（调用树、耗时、参数/返回值、PDF 页码预览） |
| 🌐 上下文问答 | 基于整篇论文（文字 + 图片内容）生成答案，附引用与来源页码 |
| 🖥️ 双界面 | ReactFlow 前端（5173）+ Streamlit 调试 UI（8501）+ FastAPI 后端（8787） |
| 🔀 服务商切换 | `PAPERQA_PROVIDER=deepseek|dashscope|openai` 统一切换模型与密钥 |
| ⌨️ CLI | `manual_index_paper.py` 建索引 + 交互问答；`manual_test_internet_connection.py` 连通性测试 |

> 说明：代码中**没有**"PDF 上传 + 摘要 + 浏览器内句子划线高亮"界面；"句子级"信息以
> chunk 文本 + 追踪卡片中的页码预览图 + 中文翻译呈现（详见 `docs/2-ARCHITECTURE.MD`）。

---

## 文档目录

| 文件 | 说明 |
|---|---|
| [`README.md`](README.md) | 项目入口：功能、部署、验证、故障排查 |
| [`docs/1-WORKFLOW.MD`](docs/1-WORKFLOW.MD) | 项目工作流：开发规范、知识管理、项目管理、运行手册、分支协作 |
| [`docs/2-ARCHITECTURE.MD`](docs/2-ARCHITECTURE.MD) | 系统架构：架构图、模块职责、数据流、模型与存储约定 |
| [`docs/3-LEARNED.MD`](docs/3-LEARNED.MD) | 开发经验教训：踩坑记录、验证记录、已知限制 |
| [`verify/README.md`](verify/README.md) | 验收脚本（`verify_smoke/e2e/agent.py`）使用说明 |
| [`paper-qa-script/reactflow-paperqa-prototype/README.md`](paper-qa-script/reactflow-paperqa-prototype/README.md) | ReactFlow 前端 + FastAPI 后端原型说明 |
| [`paper-qa-script/paperqa_system_report.md`](paper-qa-script/paperqa_system_report.md) | paperqa 源码静态分析报告（371 个函数） |
| [`paper-qa/README.md`](paper-qa/README.md) 等 | vendored PaperQA2 上游文档（README/CONTRIBUTING/tutorials/packages） |

---

## 先决条件

| 依赖 | 要求 | 检查命令 |
|---|---|---|
| 操作系统 | Windows 10/11 x64 或 macOS（Apple Silicon/Intel） | — |
| Python | `>= 3.11`（验证 3.13） | `python --version` |
| Node.js / npm | `>= 18` / `>= 9` | `node --version && npm --version` |
| API Key | DeepSeek / DashScope / OpenAI 任选其一 | 见"第 3 步" |

- 首次运行会**联网下载**：Python 依赖、前端依赖、本地向量模型 `multi-qa-MiniLM-L6-cos-v1`（约 90MB）。
- 可选：系统 Graphviz 二进制，仅影响 SVG/PNG 下载按钮（代码会自动发现常见安装目录）。

---

## 本地部署

### 第 0 步：获取代码

```bash
git clone https://github.com/PaperStrange/PaperReadingAgent.git
cd PaperReadingAgent
```

### 第 1 步：安装 Python 依赖

**Windows（PowerShell）**：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
```

**macOS / Linux**：

```bash
bash scripts/setup-env.sh
```

（脚本会创建 `.venv`、安装 paper-qa 源码包、并把 `fhlmi/litellm` 锁定到与 `paper-qa/uv.lock` 一致的版本。）

### 第 2 步：安装前端依赖

```bash
cd paper-qa-script/reactflow-paperqa-prototype/frontend
npm ci          # Windows / macOS / Linux 通用；按 package-lock.json 精确安装
cd ../../..     # 回到仓库根目录
```

### 第 3 步：配置 API Key 与服务商

复制模板为 `.env` 并填入密钥（`.env` 已被 `.gitignore` 忽略，不会入库）：

```bash
# Windows
Copy-Item paper-qa-script\.env.example paper-qa-script\.env

# macOS / Linux
cp paper-qa-script/.env.example paper-qa-script/.env
```

编辑 `paper-qa-script/.env`：

```text
export PAPERQA_PROVIDER=deepseek          # deepseek | dashscope | openai
export DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
# export DASHSCOPE_API_KEY=sk-你的DashScope密钥
# export OPENAI_API_KEY=sk-你的OpenAI密钥
```

> 也可不写 `.env`：直接设环境变量，或在网页 Config 节点填写 `api_key` / `provider`。
> 密钥读取顺序：服务商专属环境变量 → 通用 `OPENAI_API_KEY` → `.env`。
> 各服务商默认模型/向量化映射见文末「模型服务商切换」。

> **脚本启动方式（Windows）**：`.ps1` 默认关联记事本，双击或在 cmd 运行都会打开记事本。
> 请改用 **`scripts\start-*.bat`（可双击）**，或在 PowerShell 执行 `powershell -ExecutionPolicy Bypass -File .\scripts\start-*.ps1`。

### 第 4 步：启动后端并验证

**Windows**：`.\scripts\start-backend.bat`　**macOS/Linux**：`bash scripts/start-backend.sh`

看到 `Uvicorn running on http://127.0.0.1:8787` 即成功。另开终端验证：

```bash
curl http://127.0.0.1:8787/api/health     # 期望 {"status":"ok"}
```

### 第 5 步：启动前端并验证

**Windows**：`.\scripts\start-frontend.bat`　**macOS/Linux**：`bash scripts/start-frontend.sh`

浏览器打开 **http://127.0.0.1:5173** 应出现 6 节点画布。

### 第 6 步（可选）：启动 Streamlit 调试 UI

**Windows**：`.\scripts\start-streamlit.bat`　**macOS/Linux**：`bash scripts/start-streamlit.sh`

浏览器打开 **http://127.0.0.1:8501**。

### 第 7 步：跑通第一个问答

1. 浏览器打开 http://127.0.0.1:5173 。
2. 点击左侧 **1) Config** 节点，确认 `provider` / `api_key` / `paper_directory`（默认 `data/pdf`，相对后端工作目录）。
3. 点击 **2) Load Index**（首次约 1–2 分钟）。
4. 依次或 `Run All` 执行 **Retrieve → Parse Chunk Embed → Gather Evidence → Generate Answer**。

### 第 8 步：验证安装（自动化）

```bash
# Windows
.\.venv\Scripts\python.exe .\verify\verify_smoke.py     # 8 项冒烟（离线）
.\.venv\Scripts\python.exe .\verify\verify_e2e.py       # 全链路（真实 API）

# macOS / Linux
.venv/bin/python verify/verify_smoke.py
.venv/bin/python verify/verify_e2e.py
```

---

## 模型服务商切换

统一通过环境变量 `PAPERQA_PROVIDER`（或 Streamlit 侧边栏"模型服务商"下拉框）在三个服务商间切换：

| 服务商 | LLM / 视觉模型 | 向量化 | API Base |
|---|---|---|---|
| `deepseek`（默认） | `openai/deepseek-v4-flash` / `openai/deepseek-v4-flash-vision-exp` | `st-multi-qa-MiniLM-L6-cos-v1`（本地） | `https://api.deepseek.com` |
| `dashscope` | `openai/qwen-omni-turbo` | `openai/text-embedding-v4`（API） | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `openai` | `gpt-4o-mini` | `text-embedding-3-small`（API） | OpenAI 官方默认 |

密钥按顺序读取：服务商专属环境变量（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY`）→ 通用 `OPENAI_API_KEY` → 本地 `paper-qa-script/.env`。显式传入的 `api_base/model/embedding_model` 参数优先级最高。

### 配置多个 Key 会不会冲突？—— 不会（重要参数配置说明）

key 与服务商**一一对应**，同时配置多家 key 互相独立、不会串用：`PAPERQA_PROVIDER=deepseek` 只取 `DEEPSEEK_API_KEY`、`dashscope` 只取 `DASHSCOPE_API_KEY`、`openai` 只取 `OPENAI_API_KEY`，其余 key 只是闲置。

**解析优先级**：服务商专属 key（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY`）→ 通用 `OPENAI_API_KEY` → `.env`。

**⚠ 唯一要注意的一点**：若某服务商**没配专属 key**，会回退用通用 `OPENAI_API_KEY`。此时若 `PAPERQA_PROVIDER` 指向该服务商而 `OPENAI_API_KEY` 是另一家的 key，会拿错 key 去调对应端点，导致鉴权失败。

**推荐做法**：只填当前要用的那一家 key，并保证 `PAPERQA_PROVIDER` 与所填 key 一致；其余 key 注释掉。例如只用 DeepSeek：

```text
export PAPERQA_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
# export DASHSCOPE_API_KEY=...
# export OPENAI_API_KEY=...
```

---

## 故障排查

| 现象 | 处理 |
|---|---|
| `python` / `node` / `npm` 找不到 | 安装对应运行时并加入 PATH |
| 后端 8787 端口被占用 | 结束占用进程或改用 `--port`；前端 `--port 5173` 同理 |
| 首次问答很久 / 下载模型 | 本地向量模型首次需联网下载 ~90MB，请等待 |
| 中文在 Windows 控制台乱码 | 启动前设 `$env:PYTHONUTF8 = "1"`（macOS 无此问题） |
| 提问返回空/失败 | 确认所选服务商 key 有效、账户有额度（`PAPERQA_PROVIDER` 与 key 对应） |
| SVG/PNG 下载按钮报 `ExecutableNotFound` | 代码会自动发现 Graphviz 目录；仍失败则手动安装并确认 `dot` 在 PATH |
| 更多踩坑 | 见 `docs/3-LEARNED.MD` |

---

## 安全说明

- **密钥不落库**：API Key 一律通过环境变量或本地 `paper-qa-script/.env` 提供（以 `.env.example` 为模板，`.env` 已被 `.gitignore` 忽略）；服务商由 `PAPERQA_PROVIDER` 切换，代码不硬编码任何密钥。
- **后端仅监听本机**：FastAPI 绑定 `127.0.0.1:8787`；CORS 仅允许本地前端来源。
- **前端渲染安全**：React 默认转义后端文本；Streamlit DOT→SVG 已做特殊字符转义。
- **⚠ 请轮换密钥**：历史提交中曾包含真实密钥（已用 `git filter-repo` 清除并强推），请到服务商控制台**撤销并重新生成**曾暴露的 Key。

---

## 分支协作

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- `main`：**本分支，Windows/macOS/Linux 跨平台融合版**（集成分支）
- `windows`：Windows 移植版（独立维护）
- `mac`：macOS 原版（独立维护）

> 协作约定：`windows` / `mac` 分支各自改动后，通过 **Pull Request 合并到 `main`**。
