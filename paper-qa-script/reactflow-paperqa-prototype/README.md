# PaperQA ReactFlow Prototype

A minimal prototype showing:

- Visual node editing and graph interaction with React Flow.
- Manual, per-node execution (`Run Node`) like ComfyUI style.
- Python backend step runner that executes PaperQA pipeline stages.

## Structure

- `backend/main.py`: FastAPI 路由层（7 条 API 路由 + SSE 事件传输 + 组合根）。
- `paper-qa-script/app/`: 分层实现（编排 `orchestration.py`、引擎适配 `engine.py`、
  配置 SSOT `config_schema.py`、事件模型 `events.py`、会话 `session_store.py`、
  数据源 `data_sources.py` + 远程解析 `remote_resolver.py`）。
- `frontend/`: React + Vite + React Flow UI（`src/App.jsx`、`FlowNode.jsx`、
  `DataSourcePanel.jsx`、`FunctionTraceNode.jsx`、`JsonTree.jsx`）。

<!--
## Backend run (macOS original)

```bash
cd "/Volumes/Extreme SSD/vscode_projects/PaperReading"
source "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/.venv/bin/activate"

pip install -r "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa-script/reactflow-paperqa-prototype/backend/requirements.txt"

python "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa-script/reactflow-paperqa-prototype/backend/main.py"
```
-->

## Backend run (Windows)

```powershell
# 从仓库根目录启动（config 节点的 paper_directory 相对路径 data/pdf 以后端 cwd 为基准）
cd D:\All-Downloads\PaperReading\PaperReading-Windows
.venv\Scripts\python.exe paper-qa-script\reactflow-paperqa-prototype\backend\main.py
```

Backend default: `http://127.0.0.1:8787`.

## Frontend run (Windows)

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows\paper-qa-script\reactflow-paperqa-prototype\frontend
npm install   # 或 npm ci
npm run dev
```

Open the Vite URL in browser (usually `http://127.0.0.1:5173`).

<!--
## Frontend run (macOS original)

```bash
cd "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa-script/reactflow-paperqa-prototype/frontend"

npm install
npm run dev
```
-->

## Node steps

1. `config`
2. `load_index`
3. `retrieve`
4. `parse_chunk_embed`
5. `evidence`
6. `answer`

You can run a single node manually or click `Run All (Left-to-Right)`.

## Config 数据源面板（Sprint-3）

Config 节点顶部有「数据源」面板（`DataSourcePanel.jsx`）：

- `local`（默认）：使用 `paper_directory` 本地论文目录。
- `remote`：URL / arXiv ID / DOI 列表逐行填写 → 统一下载到 `data/remote/<index_name>/`
  再建索引（arXiv 走 export.arxiv.org 免 key；DOI 走 Unpaywall，需环境变量
  `UNPAYWALL_EMAIL` 为真实邮箱）。
- `manifest_file`：可选元数据 CSV/JSON（相对论文目录），对索引文件做元数据增强。

## Run ID & snapshots

- Use the `Run ID` input in the top bar to group one experiment run.
- Click `New Run ID` to start a fresh run group.
- Each node stores and displays:
  - `input_snapshot`
  - `output_snapshot`
  - `function_trace` (paperqa-only, function-level)
  - `run_id`

## Extra debug data

- `parse_chunk_embed` now returns `sample_texts` so you can inspect plain-text previews
  instead of only hashed ids/doc keys.

## Function subgraph

- `Expand Selected Step Only` builds a call graph from `function_trace`.
- Edges are parent->child (`parent_call_id`) rather than plain linear time.
- Layout is expanded downward by call depth.

## Notes

- This is a prototype for transparency and interaction, not production-hardening.
- API key 可在 `config` 节点 `params.api_key` 覆盖；留空时读环境变量 / `paper-qa-script/.env`（按服务商）。
- Session state is in-memory and resets when backend restarts.
- Windows 默认模型：DeepSeek `openai/deepseek-v4-flash`（api_base `https://api.deepseek.com`）；
  图片/图表增强用 DeepSeek 视觉模型 `openai/deepseek-v4-flash-vision-exp`；
  向量化用本地 sentence-transformers（`st-multi-qa-MiniLM-L6-cos-v1`，无需 API key，首次使用自动下载模型）。
