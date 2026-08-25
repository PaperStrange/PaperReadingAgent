# Windows 移植说明、运行手册与验证记录

## 1. 一句话总结

不做任何业务重构：原代码（macOS 版）完整保留并通过注释标记全部差异；为 Windows 的改动集中在
**模型接入（DeepSeek + 本地向量化）、路径可移植性、启动脚本、文档**，另修复一个原文件缺陷
（`runtime_trace.py` 对 staticmethod 的破坏，macOS 上同样会触发）。

## 2. 全部改动清单（相对 macOS 原始代码）

### 2.1 代码改动（均保留原代码块为 `[macOS original]` 注释）

| 文件 | 改动 |
|---|---|
| `paper-qa-script/runtime_trace.py` | **原文件缺陷修复**：`_install()` 经 `inspect.getattr_static` 识别 staticmethod/classmethod，包装后保持描述符语义；`__exit__` 还原原始描述符。修复依据：带追踪的执行流在 `SearchIndex.filehash`（@staticmethod）上报 `TypeError: takes 1 positional argument but 2 were given`。 |
| `backend/main.py` | `build_settings`：默认 api_base→`https://api.deepseek.com`、LLM→`openai/deepseek-v4-flash`、embedding→`st-multi-qa-MiniLM-L6-cos-v1`（st- 前缀按本地模型传 `{"batch_size":N}`，API 向量模型仍用完整 model_list 配置）；summary_llm 与 enrichment_llm→`openai/deepseek-v4-flash-vision-exp`（证据/图片含图时文本模型报 `does not support image`）；全部 chat 型 litellm_params 增加 `"extra_body":{"thinking":{"type":"disabled"}}`。 |
| `streamlit_paperqa_app.py` | 同 `build_settings` 改动；侧边栏默认值改为 DeepSeek/本地向量；默认论文目录改为仓库相对 `data/pdf`（`Path(__file__).parent.parent / "data/pdf"`）。 |
| `frontend/src/App.jsx` | config 节点默认参数：api_base/model/embedding_model/paper_directory（`"data/pdf"`，相对后端 cwd）。 |
| `manual_index_paper.py` | 密钥/模型换 DeepSeek；api_base 常量；paper_dir→`Path(__file__).parent.parent/"data/pdf"`；index_dir→`Path.home()/".pqa"/"indexes"/"debug_index"`。 |
| `python_qa.py` | 同上；embedding_config 在 st- 前缀时传 `{"batch_size":10}`。 |
| `manual_test_internet_connection.py` | 密钥/模型/api_base 换 DeepSeek。 |
| `paper-qa-script/.env` | `OPENAI_API_KEY` 换 DeepSeek key；两个旧 key 注释保留。 |
| `analysis 脚本（analyze/count_paperqa_functions）` | `ROOT`/`OUT_DIR` 由固定 mac 路径改为相对脚本定位。 |
| `reactflow-paperqa-prototype/README.md` | Windows 运行命令；macOS 原命令以注释保留。 |

### 2.2 新增文件

| 文件 | 作用 |
|---|---|
| `README-Windows.md` | 仓库根快速上手（本文件浓缩版）。 |
| `requirements-windows.txt` | 运行/调试依赖清单（paper-qa 本体与 reader 子包走本地源码安装命令）。 |
| `scripts/setup-env.ps1` | 一键创建 `.venv` + 安装全部依赖（含 `SETUPTOOLS_SCM_PRETEND_VERSION` 伪装版本）。 |
| `scripts/start-backend.ps1` | 导入 `.env` → 启动 FastAPI（8787），设 `HF_HUB_DISABLE_SYMLINKS_WARNING=1`。 |
| `scripts/start-frontend.ps1` | `npm ci`（首次）→ 直接调用 `vite.cmd --host 127.0.0.1 --port 5173 --strictPort`（Windows 上 `npm run dev --` 传参不可靠）。 |
| `scripts/start-streamlit.ps1` | 导入 `.env` → `streamlit run`。 |
| `verify/verify_smoke.py` | 8 项导入/组件冒烟检查。 |
| `verify/verify_e2e.py` | 驱动真实后端 6 步全链路（含 SSE 之外的 REST 调用与答案校验）。 |
| `verify/verify_agent.py` | `agent_query(fake agent)` + 翻译接口验证。 |
| `verify/verify_e2e_result.json` | 最近一次全链路验证结构化结果。 |
| `docs/` | 本文档目录。 |

## 3. 运行手册（Windows）

### 3.1 一次性环境准备

```powershell
cd D:\All-Downloads\PaperReading\PaperReading-Windows
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
# 前端依赖
cd paper-qa-script\reactflow-paperqa-prototype\frontend
npm ci
```

依赖版本注意（与 mac `uv.lock` 对齐，避免 API 行为漂移）：
`pip install "fhlmi==0.42.1" "litellm==1.76.1"`（直接 pip 安装会解析到更新的大版本）。

### 3.2 启动（三终端）

```powershell
# 终端 1 后端
.\scripts\start-backend.ps1        # http://127.0.0.1:8787
# 终端 2 前端
.\scripts\start-frontend.ps1       # http://127.0.0.1:5173
# 终端 3（可选）Streamlit 调试 UI
.\scripts\start-streamlit.ps1      # http://127.0.0.1:8501
```

### 3.3 使用流程（后端流程）

1. 打开 5173 → 点击 **1) Config** 节点：确认/填写 `api_key`（DeepSeek key）、`paper_directory`（默认 `data/pdf`，相对后端工作目录）。
2. **Load Index**（首次约 1-2 分钟：PDF 解析 + 本地向量化 + 写入 `~/.pqa/indexes/debug_index`）。
3. **Retrieve** → **Parse Chunk Embed**（含图片增强，约 50s）→ **Gather Evidence**（DeepSeek 证据摘要）→ **Generate Answer**。
4. 点击任一节点后右侧"函数子画布"展示该步骤的函数调用图；节点卡片可展开文本/预览图/翻译。
5. 也可用顶栏 `Run All (Left-to-Right)` 一键串行执行。

### 3.4 命令行脚本

```powershell
.\.venv\Scripts\python.exe .\paper-qa-script\manual_index_paper.py   # 建索引 + 交互问答
.\.venv\Scripts\python.exe .\paper-qa-script\manual_test_internet_connection.py  # 连通性
```

## 4. 关键适配原因（踩坑记录）

1. **DeepSeek 无 embedding API** → 本地 `st-multi-qa-MiniLM-L6-cos-v1`（`embedding_model_factory` 支持 `st-` 前缀，`paper-qa` 的 `local` 依赖；384 维，首次从 HF 下载）。若需换 API 向量模型，在 config 节点输入 `openai/<model>` 即可（后端会自动带上完整 model_list 配置）。
2. **DeepSeek 思考模式与 litellm 不兼容**：deepseek-v4-flash 默认返回 `reasoning_content`；DeepSeek 要求多轮对话中原样回传，litellm 不回传 → 400。解决：`extra_body={"thinking":{"type":"disabled"}}`（直接传 `thinking` 参数会被 litellm 以"不支持的参数"拒绝；`allowed_openai_params` 无效）。
3. **证据上下文含图片**：`summary_llm` 若为纯文本模型报 `This model does not support image` → 证据摘要用 `deepseek-v4-flash-vision-exp`；提问/引用仍用 flash（快）。
4. **runtime_trace 静态方法缺陷**（见 2.1）。
5. **fhlmi/litellm 大版本漂移**：pip 默认解析到 fhlmi 1.0.5/litellm 1.84.1，与 mac `uv.lock`（0.42.1/1.76.1）不一致导致 Agent 路径 `LiteLLMModel.select_tool._acompletion() takes 0 positional`（以及其他隐性差异）→ 按 uv.lock 固定版本。
6. **Windows 控制台编码**：启动脚本/命令行建议设置 `PYTHONUTF8=1`（本仓库 ps1 之外，直接命令行运行时设置），否则中文输出在 GBK 控制台乱码。
7. **Graphviz 二进制**：可选。`st.graphviz_chart` 无需二进制；SVG/PNG 下载按钮需要。安装：`winget install Graphviz.Graphviz`（本机验证时 winget 源不可用，服务端已无头像正常降级为"仅可下载 DOT"）。
8. **前端 SSE**：函数追踪通过 `/api/stream` 的 EventSource 推送；后端重启后旧 session 无效（前端 `New Session` 重新创建）。

## 5. 验证记录（Windows，实际执行）

### 5.1 冒烟验证（`verify/verify_smoke.py`）—— 8 项中 7 项通过

| 检查 | 结果 |
|---|---|
| paperqa 导入（v2026.1.6.dev10+g36348d0ca） | ✅ |
| backend/main.py 加载（FastAPI 8 条路由） | ✅ |
| RuntimeTracer 上下文（19 个显式目标） | ✅ |
| streamlit 1.62 / litellm / PyMuPDF（25 页渲染→base64） | ✅ |
| graphviz python 包 + SVG 渲染 | ⚠️ 缺系统 `dot` 可执行文件（可选装） |
| PDF 解析器自动发现（paperqa_pymupdf.parse_pdf_to_pages） | ✅ |

### 5.2 全链路端到端（`verify/verify_e2e.py`，真实 DeepSeek API）✅

- 后端 8787 启动 → `/api/health` ✅；session 创建 ✅
- `load_index`（含 74 个函数追踪事件）✅ → `retrieve` 候选 `['PaperQA2.pdf']` ✅
- `parse_chunk_embed`（50s，含 vision 图片增强）✅
- `evidence`：10 条上下文 ✅ → `answer`：1656 字符带引用答案（Skarlinski2024 pages 1-2 等）✅
- 结论：**透明流水线在 Windows 上完整跑通并产出高质量引用回答**。

### 5.3 Agent 流程（`verify/verify_agent.py`）✅

- `agent_query(..., agent_type="fake")` → **status: success**，8 条上下文+引用答案；
- `/api/translate_preview` 所用 LLM 直调翻译：`'PaperQA2执行检索增强生成。'` ✅；
- 修复前：thinking 模式导致 400（reasoning_content 回传），修复（extra_body）后通过。
- 注：macOS 基线中 ToolSelector 模式即常现 status=fail（tmp.log 佐证），本移植版同样的模型调用格式依赖——若需模型自主调工具，优先 `fake` 或透明流程。

### 5.4 前端与 Streamlit

- `npm ci` + `npm run build`：197 模块，构建产物与 mac 版 dist 同源（hash 一致）✅
- Vite dev（直接 `.bin\vite.cmd --host 127.0.0.1`）：`/`、`/index.html`、`/src/main.jsx` 均 200 ✅
- `streamlit run --server.headless true`：8501 返回 200（11KB HTML）✅
- 注意：`npm run dev -- --host …` 在 Windows 上参数透传失败（服务绑定到 IPv6 localhost 且根 404），已改用直接调用 vite.cmd。

### 5.5 原代码（macOS 版）模拟验证

- 全量导入/路由/追踪器/渲染/解析器均通过；发现并定位 2 个环境事实（DashScope 欠费、密钥失效）与 1 个原文件缺陷（runtime_trace staticmethod）。
- 旧 DashScope 密钥验证结果：`sk-6d83…` 欠费（Arrearage）、`sk-d70b…` 模型无权限、`sk-proj-…` OpenAI 配额超限——均为账户问题，_非代码问题_；因此全链路改用 DeepSeek 密钥（用户指定）完成。

## 6. 已知限制

- 图片内容参与回答依赖 `deepseek-v4-flash-vision-exp`（思考被禁用）；图片数量多时 parse/evidence 明显变慢（单 PDF 约 50s+）。
- Agent(ToolSelector) 对 DeepSeek 工具调用格式的稳定性未做全量验证（macOS 基线即不稳定）；建议透明流程。
- 无浏览器内逐句高亮；"句子级"信息以 chunk 文本+页码预览提供。
- 本地向量化模型首次使用需联网下载（约 90MB，HF）。
- Graphviz 二进制可选；缺失时仅影响 SVG/PNG 下载按钮（代码已降级处理）。
