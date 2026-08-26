# PaperReading（macOS 版）

> 基于 **PaperQA2** 的论文问答可视化原型：论文 PDF 放入目录，在浏览器 GUI 里按
> 6 节点流水线完成索引、检索、解析/向量化、证据摘要与带引用的上下文回答，
> 并提供函数级运行时追踪与 PDF 页码预览。原始部署路径 `/Volumes/Extreme SSD/vscode_projects/PaperReading`。

---

## 功能一览

| 功能 | 说明 |
|---|---|
| 📄 论文入库 | PDF/TXT/MD/HTML 放入 `data/pdf/`，自动解析文本与图片媒体 |
| 🔍 全文 + 向量索引 | Tantivy 全文索引 + DashScope 向量化（`~/.pqa/indexes`） |
| 🧩 可视化流水线 | ReactFlow 6 节点：`config → load_index → retrieve → parse_chunk_embed → evidence → answer` |
| 📊 函数级追踪 | 每步展示 paperqa 内部函数调用图（调用树、耗时、PDF 页码预览） |
| 🌐 上下文问答 | 基于整篇论文（文字 + 图片）生成答案，附引用与来源页码 |
| 🖥️ 双界面 | ReactFlow 前端（5173）+ Streamlit 调试 UI（8501）+ FastAPI 后端（8787） |

---

## 文档目录

本仓库中所有以 `.md` 结尾的文档（依赖包与 `.venv` 内的第三方文档除外）：

### 本项目维护的文档

| 文件 | 说明 |
|---|---|
| [`README.md`](README.md) | 项目入口：功能、部署、验证 |
| [`docs/1-WORKFLOW.MD`](docs/1-WORKFLOW.MD) | 项目工作流：开发规范、知识管理、项目管理、运行手册 |
| [`docs/2-ARCHITECTURE.MD`](docs/2-ARCHITECTURE.MD) | 系统架构：架构图、模块职责、数据流、模型与存储约定 |
| [`docs/3-LEARNED.MD`](docs/3-LEARNED.MD) | 开发经验教训：踩坑记录、验证记录、已知限制 |
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

| 依赖 | 要求 | 检查命令 |
|---|---|---|
| macOS | 任意（原始环境为 Apple Silicon） | — |
| Python | `>= 3.11`（原始环境 3.13） | `python --version` |
| Node.js / npm | `>= 18` / `>= 9` | `node --version && npm --version` |
| DashScope API Key | 一个可用 key（阿里百炼） | `source ~/.secrets/paperqa.env` |

> 原仓库密钥使用 `openai/qwen-omni-turbo` + `openai/text-embedding-v4`（DashScope OpenAI 兼容端点）；
> 当前旧 key 已失效（账户问题），需换成可用 key。

---

## 本地部署

### 第 0 步：获取代码

```bash
git clone -b mac https://github.com/PaperStrange/PaperReadingAgent.git
cd PaperReadingAgent
```

### 第 1 步：安装 Python 依赖

```bash
python -m venv paper-qa/.venv
source paper-qa/.venv/bin/activate
pip install --upgrade pip
export SETUPTOOLS_SCM_PRETEND_VERSION="2026.1.6.dev10+g36348d0ca"
pip install "fhlmi==0.42.1" "litellm==1.76.1"      # 对齐 uv.lock
pip install -e ./paper-qa
pip install -e "./paper-qa/packages/paper-qa-pypdf[media]"
pip install -e ./paper-qa/packages/paper-qa-pymupdf
pip install streamlit fastapi uvicorn pydantic sentence-transformers pymupdf graphviz
```

### 第 2 步：安装前端依赖

```bash
cd paper-qa-script/reactflow-paperqa-prototype/frontend
npm install
```

### 第 3 步：配置 API Key

```bash
source ~/.secrets/paperqa.env    # 或 export OPENAI_API_KEY=sk-...
```

### 第 4 步：启动后端并验证

```bash
python paper-qa-script/reactflow-paperqa-prototype/backend/main.py
# 另开终端验证：
curl http://127.0.0.1:8787/api/health     # 期望 {"status":"ok"}
```

### 第 5 步：启动前端并验证

```bash
cd paper-qa-script/reactflow-paperqa-prototype/frontend
npm run dev
# 浏览器打开 http://127.0.0.1:5173
```

### 第 6 步（可选）：启动 Streamlit

```bash
streamlit run paper-qa-script/streamlit_paperqa_app.py
```

### 第 7 步：跑通第一个问答

浏览器打开 5173 → **Config** 节点确认参数 → **Load Index** → 依次或 `Run All` 执行
`Retrieve / Parse Chunk Embed / Gather Evidence / Generate Answer`。

---

## 验证安装

| 检查项 | 命令 | 期望结果 |
|---|---|---|
| 后端存活 | `curl http://127.0.0.1:8787/api/health` | `{"status":"ok"}` |
| 前端页面 | 浏览器 5173 | 6 节点画布 |
| 测试 | `uv run pytest -n auto`（`paper-qa/` 内） | 通过 |

---

## 安全说明

- **密钥不落库**：API Key 一律通过环境变量 `OPENAI_API_KEY` 或本地 `paper-qa-script/.env` 提供（以 `paper-qa-script/.env.example` 为模板，`.env` 已被 `.gitignore` 忽略）；代码中不再硬编码任何密钥。
- **后端仅监听本机**：FastAPI 绑定 `127.0.0.1:8787`，不对公网暴露；CORS 仅允许 `http://localhost:5173` / `http://127.0.0.1:5173`。
- **前端渲染安全**：React 默认转义后端返回文本；Streamlit 的 DOT→SVG 图渲染已做特殊字符转义，避免注入。
- **⚠ 请轮换密钥**：历史提交中曾包含真实密钥（已用 `git filter-repo` 从全部历史清除并强推）。为彻底安全，请到服务商控制台**撤销并重新生成**曾暴露的 DashScope / OpenAI Key。

---

## 下一步

- 开发规范 / 运行手册：`docs/1-WORKFLOW.MD`
- 系统架构与文件职责：`docs/2-ARCHITECTURE.MD`
- 踩坑与验证记录：`docs/3-LEARNED.MD`

---

## 版本控制

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（本仓库）｜`windows`（Windows 移植版）
