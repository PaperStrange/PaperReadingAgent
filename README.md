# PaperReading（Windows 移植版）

> 基于 **PaperQA2** 的论文问答可视化原型：把论文 PDF 放入目录，在浏览器 GUI 里按
> 6 节点流水线完成**索引 → 检索 → 解析/分块/向量化 → 证据摘要 → 带引用的上下文回答**，
> 并提供函数级运行时追踪与 PDF 页码预览。由 macOS 原版（分支 `mac`）移植而来。

---

## 功能一览

| 功能 | 说明 |
|---|---|
| 📄 论文入库 | 把 PDF/TXT/MD/HTML 放入 `data/pdf/`，自动解析文本、图片、公式/表格媒体 |
| 🔍 全文 + 向量索引 | Tantivy 全文索引 + 本地向量化（`~/.pqa/indexes`），检索候选论文 |
| 🧩 可视化流水线 | ReactFlow 画布 6 节点：`config → load_index → retrieve → parse_chunk_embed → evidence → answer`，可单步 / 一键串行 |
| 📊 函数级追踪 | 每一步展示 paperqa 内部函数调用图（调用树、耗时、参数/返回值、PDF 页码预览） |
| 🌐 上下文问答 | 基于整篇论文（文字 + 图片内容）生成答案，附引用与来源页码 |
| 🖥️ 双界面 | ReactFlow 前端（5173）+ Streamlit 调试 UI（8501）+ FastAPI 后端（8787） |
| ⌨️ CLI | `manual_index_paper.py` 建索引 + 交互问答；`manual_test_internet_connection.py` 连通性测试 |

> 说明：代码中**没有**"PDF 上传 + 摘要 + 浏览器内句子划线高亮"界面；"句子级"信息以
> chunk 文本 + 追踪卡片中的页码预览图 + 中文翻译呈现（详见 `docs/2-ARCHITECTURE.MD`）。

---

## 文档目录

本仓库中所有以 `.md` 结尾的文档（依赖包与 `.venv` 内的第三方文档除外）：

### 本项目维护的文档

| 文件 | 说明 |
|---|---|
| [`README.md`](README.md) | 项目入口：功能、部署、验证、故障排查 |
| [`docs/1-WORKFLOW.MD`](docs/1-WORKFLOW.MD) | 项目工作流：开发规范、知识管理、项目管理、运行手册 |
| [`docs/2-ARCHITECTURE.MD`](docs/2-ARCHITECTURE.MD) | 系统架构：架构图、模块职责、数据流、模型与存储约定 |
| [`docs/3-LEARNED.MD`](docs/3-LEARNED.MD) | 开发经验教训：踩坑记录、验证记录、已知限制 |
| [`docs/4-ALGORITHM.MD`](docs/4-ALGORITHM.MD) | **前后端决策逻辑与算法**：DSL 规则 + 决策表 + UML（类图/时序图/状态机），每条规则标注代码位置 |
| [`docs/5-VERSIONS.MD`](docs/5-VERSIONS.MD) | **发版记录与版本号规范**（`年.月.日-v(R.R.R)`；首个版本在 roadmap 全部 Sprint 完成后发布） |
| [`verify/README.md`](verify/README.md) | 验收脚本（`verify_smoke/e2e/agent/provider_switch/embed_load/remote_e2e` + `gui_check*.mjs`）使用说明 |
| `docs/iteration/` | 迭代增量文档（重构分析、Sprint 记录、性能分析；**仅 windows 分支维护**，不进 main/mac） |
| [`paper-qa-script/reactflow-paperqa-prototype/README.md`](paper-qa-script/reactflow-paperqa-prototype/README.md) | ReactFlow 前端 + FastAPI 后端原型说明 |
| [`paper-qa-script/paperqa_system_report.md`](paper-qa-script/paperqa_system_report.md) | paperqa 源码静态分析报告（371 个函数、入口签名、调用路径） |

### vendored PaperQA2 上游文档

| 文件 | 说明 |
|---|---|
| [`paper-qa/README.md`](paper-qa/README.md) | PaperQA2 上游主文档（Quickstart、算法、Settings 速查） |
| [`paper-qa/CONTRIBUTING.md`](paper-qa/CONTRIBUTING.md) | 上游贡献指南 |
| [`paper-qa/docs/tutorials/settings_tutorial.md`](paper-qa/docs/tutorials/settings_tutorial.md) | Settings 配置教程 |
| [`paper-qa/docs/tutorials/where_do_I_get_papers.md`](paper-qa/docs/tutorials/where_do_I_get_papers.md) | 如何获取论文 |
| [`paper-qa/docs/tutorials/running_on_lfrqa.md`](paper-qa/docs/tutorials/running_on_lfrqa.md) | 在 LFRQA 基准上运行 |
| [`paper-qa/docs/tutorials/querying_with_clinical_trials.md`](paper-qa/docs/tutorials/querying_with_clinical_trials.md) | 临床试验数据查询 |
| [`paper-qa/packages/paper-qa-pypdf/README.md`](paper-qa/packages/paper-qa-pypdf/README.md) | PyPDF reader 子包 |
| [`paper-qa/packages/paper-qa-pymupdf/README.md`](paper-qa/packages/paper-qa-pymupdf/README.md) | PyMuPDF reader 子包 |
| [`paper-qa/packages/paper-qa-docling/README.md`](paper-qa/packages/paper-qa-docling/README.md) | Docling reader 子包 |
| [`paper-qa/packages/paper-qa-nemotron/README.md`](paper-qa/packages/paper-qa-nemotron/README.md) | Nemotron reader 子包 |

---

## 先决条件

| 依赖 | 版本要求 | 检查命令 |
|---|---|---|
| 操作系统 | Windows 10/11 x64 | — |
| Python | `>= 3.11`（本机验证 3.13） | `python --version` |
| Node.js | `>= 18`（本机验证 23） | `node --version` |
| npm | `>= 9`（本机验证 10.9） | `npm --version` |
| API Key | DeepSeek / DashScope / OpenAI / OpenRouter 任选其一 | 见"第 3 步" |

- 首次运行会**联网下载**：Python 依赖（pip）、前端依赖（npm）、本地向量模型
  `multi-qa-MiniLM-L6-cos-v1`（约 90MB，HuggingFace）。
- 可选：系统 Graphviz 二进制（`winget install Graphviz.Graphviz`），仅影响 SVG/PNG 下载按钮。

先确认运行时：

```powershell
python --version
node --version
npm --version
```

---

## 本地部署

### 第 0 步：获取代码

```powershell
git clone -b windows https://github.com/PaperStrange/PaperReadingAgent.git
cd PaperReadingAgent          # 进入仓库根目录，后文用 <ROOT> 表示
```

> 若已在本机 `D:\All-Downloads\PaperReading\PaperReading-Windows`，直接把该目录当作 `<ROOT>` 即可。

### 第 1 步：安装 Python 依赖

在仓库根目录执行（自动创建 `.venv`、安装 paper-qa 源码包 + 后端 + 本地向量化依赖，
并把 `fhlmi/litellm` 锁定到与 macOS 一致的版本）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
```

<details>
<summary>等效的手动安装命令（可选）</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
$env:SETUPTOOLS_SCM_PRETEND_VERSION = "2026.1.6.dev10+g36348d0ca"
.\.venv\Scripts\python.exe -m pip install "fhlmi==0.42.1" "litellm==1.76.1"
.\.venv\Scripts\python.exe -m pip install -e .\paper-qa
.\.venv\Scripts\python.exe -m pip install -e ".\paper-qa\packages\paper-qa-pypdf[media]"
.\.venv\Scripts\python.exe -m pip install -e .\paper-qa\packages\paper-qa-pymupdf
.\.venv\Scripts\python.exe -m pip install -r .\requirements-windows.txt
```

</details>

### 第 2 步：安装前端依赖

```powershell
cd paper-qa-script\reactflow-paperqa-prototype\frontend
npm ci          # 按 package-lock.json 精确安装（首次约 1–2 分钟）
cd ..\..\..     # 回到 <ROOT>
```

### 第 3 步：配置 API Key 与服务商

复制模板为 `.env` 并填入密钥（`.env` 已被 `.gitignore` 忽略，不会入库）：

```powershell
Copy-Item paper-qa-script\.env.example paper-qa-script\.env
notepad paper-qa-script\.env
```

内容示例（`PAPERQA_PROVIDER` 选择服务商，按需填对应 key）：

```text
export PAPERQA_PROVIDER=deepseek          # deepseek | dashscope | openai
export DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
# export DASHSCOPE_API_KEY=sk-你的DashScope密钥
# export OPENAI_API_KEY=sk-你的OpenAI密钥
```

> - 也可不写 `.env`：直接设环境变量，或在网页 Config 节点填写 `api_key` / `provider`。
> - 密钥读取顺序：服务商专属环境变量（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY`）→ 通用 `OPENAI_API_KEY` → `.env`。
> - 各服务商默认模型/向量化映射见文末「模型服务商切换」。

### 第 4 步：启动后端并验证

> **脚本启动方式（重要）**：`.ps1` 文件在 Windows 上默认关联记事本，**双击或在 cmd 里运行都会打开记事本**。
> 两种正确启动方式任选其一：
> - **双击 `scripts\start-backend.bat`**（或任意终端运行 `scripts\start-backend.bat`）——自动以跳过执行策略的方式启动；
> - 在 **PowerShell** 里执行 `powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1`。

新开一个终端，在仓库根目录：

```powershell
.\scripts\start-backend.bat
```

看到 `Uvicorn running on http://127.0.0.1:8787` 即成功。另开终端验证：

```powershell
curl.exe http://127.0.0.1:8787/api/health
# 期望输出： {"status":"ok"}
```

### 第 5 步：启动前端并验证

**再开一个终端**，在仓库根目录：

```powershell
.\scripts\start-frontend.bat
```

看到 `VITE v5.x ready` 后，浏览器打开 **http://127.0.0.1:5173** 应出现
"PaperQA ReactFlow Prototype" 画布（6 个节点）。

### 第 6 步（可选）：启动 Streamlit 调试 UI

**第三个终端**：

```powershell
.\scripts\start-streamlit.bat
```

浏览器打开 **http://127.0.0.1:8501**。

### 第 7 步：跑通第一个问答

1. 浏览器打开 http://127.0.0.1:5173 。
2. 点击左侧 **1) Config** 节点，确认参数（也可用顶部「模型配置」面板下拉选择，自动带出相关字段）：
   - `api_key`（留空则用 `.env`）、`provider`（deepseek/dashscope/openai/openrouter 或自定义）、
     `paper_directory`（默认 `data/pdf`，相对后端工作目录）、
   - `model` / `embedding_model`（默认随 provider 自动填充，见文末「模型服务商切换」）。
   - **改参数后直接运行任意下游节点会自动先重跑 Config**（保证目录/模型等与当前配置一致）；retrieve 输出含 `result`：`ranked`=BM25 命中排序 / `fallback_first_n`=零命中回退取索引前 N 个文件（如中文 query 在英文分块上零命中）。
3. 点击 **2) Load Index**（首次约 1–2 分钟：解析 PDF + 本地向量化 + 写索引）。
4. 依次点击 **3) Retrieve → 4) Parse Chunk Embed → 5) Gather Evidence → 6) Generate Answer**
   （或顶栏 `Run All (Left-to-Right)` 一键执行）。
5. 在 **6) Generate Answer** 节点查看 `output.answer`（带引用）与 `references`；
   点击任一节点后，右侧"函数子画布"展示该步骤的函数调用图。

### 第 8 步：验证安装（自动化）

```powershell
$env:PAPERQA_PROVIDER = "deepseek"               # 与 .env 一致即可
$env:DEEPSEEK_API_KEY = "sk-你的DeepSeek密钥"      # 若 .env 已配置可跳过
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py             # 8 项冒烟（离线）
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py   # 服务商切换/路由（离线+连通）
.\.venv\Scripts\python.exe .\verify\verify_e2e.py               # 全链路（真实 API，本地目录）
.\.venv\Scripts\python.exe .\verify\verify_embed_load.py        # Embedding 三步（run/load/缓存）
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py        # remote 数据源全链路（联网，arXiv）
.\.venv\Scripts\python.exe .\verify\verify_agent.py             # Agent 流程（fake）+ 翻译（需先跑过 e2e）
node .\verify\gui_check.mjs           # GUI 全链路（需前后端已启动）
node .\verify\gui_check_remote.mjs    # GUI remote 数据源（需前后端已启动 + 联网）
node .\verify\gui_check_s4.mjs        # Sprint-4：光标/面板联动（需前后端已启动）
```

`verify_e2e.py` 期望输出（节选）：

```text
[ok] backend healthy
[ok] load_index ...   [ok] retrieve ...   [ok] parse_chunk_embed ...
[ok] evidence contexts: 9   [ok] answer chars: 1681
[written] ...verify_e2e_result.json   (exit code 0)
```

---

## 验证安装

| 检查项 | 命令 | 期望结果 |
|---|---|---|
| 后端存活 | `curl.exe http://127.0.0.1:8787/api/health` | `{"status":"ok"}` |
| 前端页面 | 浏览器 http://127.0.0.1:5173 | 6 节点画布 + Config 数据源面板 |
| Streamlit | 浏览器 http://127.0.0.1:8501 | 配置侧边栏 |
| 依赖版本 | `.\.venv\Scripts\python.exe -m pip show fhlmi litellm` | `0.42.1` / `1.76.1` |
| 全链路 | `.\.venv\Scripts\python.exe .\verify\verify_e2e.py` | 最终 `answer chars` 且 exit 0 |
| remote 数据源 | `.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py` | `remote_sources` 明细 + `answer chars`（需联网） |

---

## 故障排查

| 现象 | 处理 |
|---|---|
| `python` 不是内部或外部命令 | 安装 Python 3.11+ 并勾选 "Add to PATH" |
| `npm` 找不到 | 安装 Node.js LTS（自带 npm） |
| 双击/运行 `.ps1` 却打开**记事本** | Windows 默认用记事本打开 `.ps1`。改用 `.bat`（`scripts\start-*.bat`，可双击）或 `powershell -ExecutionPolicy Bypass -File .\scripts\start-*.ps1` |
| 后端 8787 端口被占用 | 结束占用进程或改用 `uvicorn` 的 `--port`；前端 `--port 5173` 同理 |
| 首次问答很久 / 下载模型 | 本地向量模型首次需从 HuggingFace 下载 ~90MB，请等待 |
| 中文在控制台乱码 | 启动前设 `$env:PYTHONUTF8 = "1"` |
| 提问返回空/失败 | 确认所选服务商的 key 有效、账户有额度（`.env` 里 `PAPERQA_PROVIDER` 与 key 对应）；换 `fake` Agent 或透明流程 |
| SVG/PNG 下载按钮报 `ExecutableNotFound` | 代码会自动发现常见 Graphviz 安装目录；仍失败则手动装 `winget install Graphviz.Graphviz` 并确认 `dot` 在 PATH（可选） |
| 更多踩坑 | 见 `docs/3-LEARNED.MD` |

---

## 安全说明

- **密钥不落库**：API Key 一律通过环境变量或本地 `paper-qa-script/.env` 提供（以 `paper-qa-script/.env.example` 为模板，`.env` 已被 `.gitignore` 忽略）；服务商由 `PAPERQA_PROVIDER` 切换，代码中不再硬编码任何密钥。
- **后端仅监听本机**：FastAPI 绑定 `127.0.0.1:8787`，不对公网暴露；CORS 仅允许 `http://localhost:5173` / `http://127.0.0.1:5173`。
- **前端渲染安全**：React 默认转义后端返回文本；Streamlit 的 DOT→SVG 图渲染已做特殊字符转义，避免注入。
- **⚠ 请轮换密钥**：历史提交中曾包含真实密钥（已用 `git filter-repo` 从全部历史清除并强推）。为彻底安全，请到服务商控制台**撤销并重新生成**曾暴露的 DeepSeek / DashScope / OpenAI Key。

---

## 下一步

- 开发规范 / 项目管理 / 更完整运行手册：`docs/1-WORKFLOW.MD`
- 系统架构与文件职责：`docs/2-ARCHITECTURE.MD`
- **前后端决策逻辑与算法（DSL+UML）**：`docs/4-ALGORITHM.MD`
- **发版记录与版本号规范**：`docs/5-VERSIONS.MD`
- 踩坑记录与验证记录：`docs/3-LEARNED.MD`

---

## 模型服务商切换

统一通过环境变量 `PAPERQA_PROVIDER`（或 Config 节点「模型配置」面板的 Provider 下拉框）切换服务商：

| 服务商 | LLM / 视觉模型 | 向量化 | API Base |
|---|---|---|---|
| `deepseek`（默认） | `openai/deepseek-v4-flash` / `openai/deepseek-v4-flash-vision-exp` | `st-multi-qa-MiniLM-L6-cos-v1`（本地） | `https://api.deepseek.com` |
| `dashscope` | `openai/qwen-omni-turbo` | `openai/text-embedding-v4`（API） | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `openai` | `gpt-4o-mini` | `text-embedding-3-large`（API） | OpenAI 官方默认 |
| `openrouter` | `openrouter/auto`（智能路由，可指定任意模型如 `openrouter/anthropic/claude-sonnet-4`） | 无 API → 自动 HF 多语言模型 | `https://openrouter.ai/api/v1` |

**自定义 provider（Sprint-4）**：复制 `paper-qa-script/providers.example.json` 为 `providers.json`（gitignored）增改条目，或用环境变量 `PAPERQA_PROVIDERS_JSON`（JSON 字符串，优先级最高）；前端下拉经 `/api/providers` 自动列出（不含密钥）。字段：`api_base / model(必填) / vision_model / embedding / embedding_local / has_embedding_api / key_envs / thinking_disabled`。

密钥按顺序读取：服务商专属环境变量（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY`）→ 通用 `OPENAI_API_KEY` → 本地 `paper-qa-script/.env`。

**显式参数覆盖（Config 节点 JSON 编辑，优先级最高）**：

- `provider`：切服务商（内置 4 家或自定义名，重设 api_base/model/embedding 默认值）。
- `model`：指定该服务商的任意 LLM 模型，如 `provider=openai` + `model="gpt-5"`（litellm 路由到 OpenAI 官方端点，需有效 key 与模型权限；gpt-5 时 paperqa 会把 temperature 强制为 1）。
- `vision_model`：证据摘要/图片增强模型（含图片上下文必须支持视觉），留空随 provider 默认。
- `embedding_model`：`st-` 前缀 = HuggingFace 任意 SentenceTransformer 模型（本地已缓存或首次自动下载，**不依赖 provider 是否有 embedding API**，如 `st-BAAI/bge-small-en-v1.5`）；其它名 = litellm API 向量（需 provider 支持）；`litellm-` 前缀可强制 API 路径。切换后需重建索引。

**Embedding 智能默认（`embedding_model` 缺省时自动生效，均可手动覆盖）**：

> 注意：前端 Config 节点**默认参数已显式填 `st-multi-qa-MiniLM-L6-cos-v1`**——此时不触发智能推荐；在面板选「Embedding → 自动」或删除 JSON 中的 `embedding_model` 后，才按以下规则自动选择。

- 服务商**有** embedding API（openai/dashscope）→ 自动用其最新策展模型（openai=`text-embedding-3-large`，dashscope=`openai/text-embedding-v4`）。
- 服务商**无** embedding API（deepseek）→ 自动查询 HuggingFace 下载量最高且**兼容中文**的 SentenceTransformer 模型（当前为 `paraphrase-multilingual-MiniLM-L12-v2`，4600 万+ 下载），首次自动下载；结果缓存 24h，离线/超时回落 `st-multi-qa-MiniLM-L6-cos-v1`（设 `PAPERQA_EMBED_RECOMMEND_LIVE=0` 可关闭在线查询）。
- 推荐结果与理由在 config 步骤输出 `embedding_resolved` 与 `config_notes.hints` 中展示；逻辑在 `app/embedding_recommender.py`（`EmbeddingRecommender` 接口，未来 E3 可替换为 agent 推荐步骤）。

### 配置多个 Key 会不会冲突？—— 不会（重要参数配置说明）

key 与服务商**一一对应**，同时配置多家 key 互相独立、不会串用：

| 你配置的 key | `PAPERQA_PROVIDER` | 实际使用 |
|---|---|---|
| `DEEPSEEK_API_KEY` + `DASHSCOPE_API_KEY` + `OPENAI_API_KEY` 都填 | `deepseek` | ✅ 只取 `DEEPSEEK_API_KEY`，其余闲置 |
| 同上 | `dashscope` | ✅ 只取 `DASHSCOPE_API_KEY` |
| 同上 | `openai` | ✅ 只取 `OPENAI_API_KEY` |
| 只填通用 `OPENAI_API_KEY` | `deepseek` / `dashscope` | ⚠️ 会用它**兜底**（见下） |

**解析优先级**：服务商专属 key（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY`）→ 通用 `OPENAI_API_KEY` → `.env`。

**⚠ 唯一要注意的一点**：若某服务商**没配专属 key**，会回退用通用 `OPENAI_API_KEY`。此时若 `PAPERQA_PROVIDER=deepseek`（或 `dashscope`）而 `OPENAI_API_KEY` 是另一家的 key，就会拿错 key 去调对应端点，导致鉴权失败。

**推荐做法**：各家 key 要么都填各自正确的，要么只填当前要用的那一家，并保证 `PAPERQA_PROVIDER` 与所填 key 一致。例如只用 DeepSeek：

```text
export PAPERQA_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
# export DASHSCOPE_API_KEY=...     # 闲置，仅当切到 dashscope 才用
# export OPENAI_API_KEY=...        # 仅当切到 openai 或用它兜底
```

### 如何提供其他服务商的 Key

| 服务商 | 环境变量 | Key 获取入口 |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com → API Keys |
| DashScope（阿里百炼） | `DASHSCOPE_API_KEY` | https://bailian.console.aliyun.com → API-KEY 管理 |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

填入 `paper-qa-script/.env`（或直接设环境变量）即可，例如切换 DashScope：

```text
export PAPERQA_PROVIDER=dashscope
export DASHSCOPE_API_KEY=sk-你的DashScope密钥
```

### 如何测试切换是否生效

```powershell
# 1) 纯配置/路由验证（无需有效 key，会打印全注册表 provider 的解析结果与端点路由）
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py

# 2) 端到端问答（用某个服务商的真实 key）
$env:PAPERQA_PROVIDER = "dashscope"
$env:DASHSCOPE_API_KEY = "sk-你的DashScope密钥"
.\.venv\Scripts\python.exe .\paper-qa-script\manual_test_internet_connection.py   # 快速连通性
.\.venv\Scripts\python.exe .\verify\verify_e2e.py                                # 全链路问答
```

> 判定标准：`verify_provider_switch.py` 中 deepseek 应为 `SUCCESS`；
> dashscope/openai 用无效 key 时，错误信息应来自**各自端点**（aliyun / platform.openai.com），
> 这证明路由正确——换成有效 key 后即可成功。

## 数据源（Sprint-3）

Config 节点顶部有「数据源」面板，两种模式：

| 模式 | 说明 |
|---|---|
| `local`（默认） | 用 `paper_directory` 本地论文目录（`data/pdf`），行为与之前完全一致；**支持嵌套子目录（默认递归）与工作区外绝对路径（如 `D:\...\_papers`），Windows 长路径（>260 字符）自动加 `\\?\` 前缀**；隐藏目录（如 `.qoder`）自动跳过 |
| `remote` | 逐行填 `source_urls`（PDF/HTML 直链）/ `source_arxiv_ids`（如 `2409.13740`，走 export.arxiv.org 免 key）/ `source_dois`（Unpaywall 查开放全文，需环境变量 `UNPAYWALL_EMAIL=你的邮箱`）→ 统一下载到 `data/remote/<index_name>/`（已在 .gitignore）→ 复用原有索引/解析管线 |

`manifest_file`（可选）：元数据 CSV/JSON（相对论文目录），对索引文件做元数据增强。
远程下载有安全防护：仅公网 http/https、拒绝内网/本机地址、单文件 200MB 上限、失败逐源报告。
索引损坏（如中断残留）会在下次 `load_index{build:true}` 时自动删除重建。

## 版本控制

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`main`（跨平台融合/集成分支）｜`mac`（macOS 原版）｜`windows`（本仓库，迭代分支）
- 约定：`windows` 改动经 PR 合并进 `main`（`docs/iteration/` 只保留在 windows，不进 main/mac）
