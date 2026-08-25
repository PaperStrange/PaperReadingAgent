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

## 先决条件 Prerequisites

| 依赖 | 要求 | 检查命令 |
|---|---|---|
| macOS | 任意（原始环境为 Apple Silicon） | — |
| Python | `>= 3.11`（原始环境 3.13） | `python --version` |
| Node.js / npm | `>= 18` / `>= 9` | `node --version && npm --version` |
| DashScope API Key | 一个可用 key（阿里百炼） | `source ~/.secrets/paperqa.env` |

> 原仓库密钥使用 `openai/qwen-omni-turbo` + `openai/text-embedding-v4`（DashScope OpenAI 兼容端点）；
> 当前旧 key 已失效（账户问题），需换成可用 key。

---

## 本地部署（一步一步）

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
# paper-qa 源码包需 setuptools-scm 版本伪装
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

## 下一步

- 开发规范 / 运行手册：`docs/1-WORKFLOW.MD`
- 系统架构与文件职责：`docs/2-ARCHITECTURE.MD`
- 踩坑与验证记录：`docs/3-LEARNED.MD`

---

## 版本控制

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（本仓库）｜`windows`（Windows 移植版）
