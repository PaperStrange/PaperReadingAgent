# 3-LEARNED —— 开发经验教训（踩坑记录 / 验证记录 / 已知限制）

> 适用于 `PaperReading-Windows`。规范/运行见 `1-WORKFLOW.MD`，架构见 `2-ARCHITECTURE.MD`。
> 本文件记录**踩过的坑、为什么、怎么解决**，以及历次验证结果与遗留限制。

---

## 1. 踩坑记录（含原因与解决）

### 1.1 DeepSeek 无 embedding API → 本地向量化
- 现象：DeepSeek 平台只提供 `deepseek-v4-flash / -pro / -flash-vision-exp`，无 embedding 端点。
- 解决：`embedding="st-multi-qa-MiniLM-L6-cos-v1"`（paperqa 的 `embedding_model_factory` 支持 `st-` 前缀 → `SentenceTransformerEmbeddingModel`）；`embedding_config` 在 `st-` 前缀时只传 `{"batch_size": N}`（否则 `name` 与工厂注入的 `name` 冲突）。384 维、首次从 HuggingFace 下载 ~90MB。

### 1.2 DeepSeek 思考模式与 litellm 不兼容
- 现象：`deepseek-v4-flash` 默认"思考模式"返回 `reasoning_content`；DeepSeek 要求多轮对话原样回传该字段，litellm 不回传 → 后续工具调用 400：`The reasoning_content in the thinking mode must be passed back to the API.`。
- 尝试与结论：直接传 `thinking` 参数被 litellm 拒绝（`openai does not support parameters: ['thinking']`）；`allowed_openai_params=['thinking']` 无效（仍把 thinking 作为 openai SDK 关键字透传）。**最终**：`extra_body={"thinking": {"type": "disabled"}}` 经 litellm `extra_body` 透传，成功关闭思考模式（实测 `reasoning_content: None`）。

### 1.3 证据上下文含图片 → 文本模型报错
- 现象：`summary_llm` 为 `deepseek-v4-flash`（纯文本）时，`aget_evidence` 对含图片的证据片段报 `This model does not support image`。
- 解决：证据摘要改用视觉模型 `openai/deepseek-v4-flash-vision-exp`；主 LLM（答案/引用）仍用 flash（快、便宜）。

### 1.4 runtime_trace.py 破坏 staticmethod/classmethod（原文件缺陷）
- 现象：后端 `load_index`（在 RuntimeTracer 上下文内）报
  `TypeError: SearchIndex.filehash() takes 1 positional argument but 2 were given`，最终 `ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)`。
- 根因：`_install()` 用 `getattr(cls, name)` 拿到未绑定纯函数后 `setattr(cls, name, wrapped)`，把 `@staticmethod` 变成普通实例方法 → 实例调用多传 `self`。
- 解决：改用 `inspect.getattr_static` 识别描述符，`staticmethod/classmethod` 包装后仍以描述符安装，`__exit__` 还原描述符。**macOS 版同缺陷，已同步修复。**

### 1.5 fhlmi / litellm 大版本漂移
- 现象：pip 默认解析到 `fhlmi 1.0.5 / litellm 1.84.1`，Agent 路径报
  `TypeError: LiteLLMModel.select_tool.<locals>._acompletion() takes 0 positional arguments but 1 was given`。
- 解决：按 mac `paper-qa/uv.lock` 固定 `fhlmi==0.42.1`、`litellm==1.76.1`。

### 1.6 Windows 控制台中文乱码
- 现象：Python 打印中文在 GBK 控制台显示为 `��`/`鐢ㄤ腑鏂�...`。
- 解决：脚本/命令行设 `PYTHONUTF8=1`（后端子进程同样注入）；仅显示层问题，不影响 API 返回值。

### 1.7 `npm run dev -- --host ...` 在 Windows 上参数透传失败
- 现象：vite 绑定到 IPv6 localhost 且根路径 404。
- 解决：`start-frontend.ps1` 直接调用 `node_modules\.bin\vite.cmd --host 127.0.0.1 --port 5173 --strictPort`。

### 1.8 Graphviz 二进制缺失（可选）
- 现象：`graphviz` Python 包就绪但无系统 `dot`，SVG/PNG 下载按钮报 `ExecutableNotFound`。
- 结论：`st.graphviz_chart` 与 DOT 下载不受影响；SVG/PNG 下载需 `winget install Graphviz.Graphviz`（本机 winget 源不可用，已降级处理）。

### 1.9 旧 DashScope 密钥全部失效（账户问题，非代码问题）
- `sk-6d83…`：账户欠费（`Arrearage`）；`sk-d70b…`：模型无权限；`sk-proj-…`：OpenAI 配额超限。
- 结论：请求均成功到达服务端并返回账户级错误 → 端点/模型名/请求格式正确。全链路改用 DeepSeek key（用户指定）。

## 2. 验证记录（Windows，实际执行）

### 2.1 冒烟（`verify/verify_smoke.py`）—— 8 项中 7 项通过
| 检查 | 结果 |
|---|---|
| paperqa 导入 v2026.1.6.dev10+g36348d0ca | ✅ |
| backend/main.py 加载（FastAPI 8 条路由） | ✅ |
| RuntimeTracer（19 个显式目标） | ✅ |
| streamlit / litellm / PyMuPDF（25 页渲染） | ✅ |
| graphviz python 包 + SVG | ⚠️ 缺系统 dot（可选） |
| PDF 解析器自动发现（paperqa_pymupdf） | ✅ |

### 2.2 全链路端到端（`verify/verify_e2e.py`，真实 DeepSeek）✅
- 后端 8787 `/api/health` ✅ → `load_index`（74 追踪事件）✅ → `retrieve` 候选 `['PaperQA2.pdf']` ✅
- `parse_chunk_embed`（含 vision 图片增强）✅ → `evidence`（10 条上下文）✅
- `answer`：**1656 字符带引用答案**（Skarlinski2024 pages 1-2 等）✅
- 结论：透明流水线在 Windows 上完整跑通。

### 2.3 Agent 流程（`verify/verify_agent.py`）✅
- `agent_query(agent_type="fake")` → **status: success**，8 条上下文 + 引用答案；
- 翻译接口：`'PaperQA2执行检索增强生成。'` ✅。

### 2.4 前端与 Streamlit ✅
- `npm ci` + `npm run build`：197 模块；`dist` 与 mac 版同源（hash 一致）。
- Vite dev：`/`、`/index.html`、`/src/main.jsx` 均 200。
- `streamlit run --server.headless true`：8501 返回 200（11KB HTML）。

## 3. 已知限制

- 图片内容参与回答依赖 `deepseek-v4-flash-vision-exp`（思考已禁用）；图片多时 parse/evidence 变慢（单 PDF 约 50s+）。
- Agent(ToolSelector) 对模型工具调用格式稳定性未全量验证（macOS 基线即常 status=fail）；优先透明流程。
- 无浏览器内逐句高亮；"句子级"信息以 chunk 文本 + 页码预览提供。
- 本地向量模型首次使用需联网（HF，~90MB）。
- Graphviz 二进制可选；缺失时仅影响 SVG/PNG 下载按钮。
