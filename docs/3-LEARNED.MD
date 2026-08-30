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
- 旧 DashScope 密钥：账户欠费（`Arrearage`）；另一 DashScope 密钥：模型无权限；OpenAI 密钥：配额超限（均为账户侧问题）。
- 结论：请求均成功到达服务端并返回账户级错误 → 端点/模型名/请求格式正确。全链路改用 DeepSeek key（用户指定）。

### 1.10 ReactFlow 节点内的 fixed 弹层被 transform 祖先裁剪（Sprint-1 证据收集时发现）
- 现象：chunk 图片 lightbox（`position:fixed;inset:0`）在 DOM 里存在但截图看不到。
- 根因：ReactFlow 节点容器带 `transform: translate(...)`，CSS `fixed` 在 transform 祖先内退化为相对其定位并被裁剪。
- 解决：lightbox 改用 **React Portal**（`createPortal(…, document.body)`）渲染到 body，脱离 transform 上下文。
- 教训：**凡悬浮层/弹层出现在画布节点内部，一律用 Portal 挂到 body**；用浏览器截图（Playwright）验证"看得见"而不只看 DOM 存在。

### 1.11 批量杀进程误伤宿主会话（运维纪律）
- 现象：一次 `Get-Process node|python | Stop-Process` 清理开发服务器，导致运行器工具调用被中断。
- 教训：**禁止宽泛按进程名批量杀进程**。停止服务优先：明确 PID / 端口级确认 / 由服务自身停止信号；工具自身宿主进程（如 Web 运行器）绝不触碰。

### 1.12 Playwright 驱动 ReactFlow 交互的技巧（Sprint 证据标准配套）
- 现象：Playwright 点击 ReactFlow 节点内按钮/图片常失败（元素在 transform 容器内、"outside of viewport"、点击被节点拖拽拦截）。
- 解决：点击"Run All"等顶栏按钮走正常 click；节点内部 img 用 `page.evaluate(() => img.dispatchEvent(new MouseEvent('click',{bubbles:true})))` 派发；截图后用 `read_image` 逐张核对内容是否符合需求卡片。

### 1.13 依赖漂移教训升级：需要"框架适配层 + 版本检查"（Sprint-2 动机）
- 回顾 1.5（fhlmi/litellm 大版本漂移）与 vendor 本地注入的维护痛点 → 决策：引入 `EngineAdapter` 接口、支持 pip 包注入与版本检查/回滚（见 `docs/iteration/refactor-analysis.MD` 主题 E1/E2）。
- 教训：**版本 pin 不要散落在注释里**，要进可校验的配置/锁文件；框架升级必须有回归锚点。

### 1.14 pydantic `model_json_schema()` 在复杂类型上会整体失败 → 用 `model_fields` 逐段导航（US-2.1）
- 现象：paperqa `Settings.model_json_schema()` 抛 `PydanticInvalidForJsonSchema`（`AsyncContextSerializer` 无法 JSON-Schema 化），整个 schema 都拿不到，不能做"自动抽取默认值"。
- 解决：改为 `Settings.model_fields` 逐段导航（`parsing.use_doc_details`、`answer.evidence_k`…），注解经 `Optional/Union` 解包、遇非 BaseModel 容器（如 `MaybeDict`）视为叶子；解析失败回落策展默认值。一致性自检同样走 `_path_exists`（防拼写错误）。
- 教训：**别把框架的整树 schema 生成当免费午餐**；按需逐字段读取 + 回落策略，才能既自动抽取又不被框架类型卡死。

### 1.15 大文件分层拆分三件套：逐字迁移 + 线协议比对 + 每卡回归（US-2.2/US-2.5）
- 做法：557 行 `main.py` 拆成 路由/编排/引擎适配 三层时，六步逻辑**逐字迁移**（diff 只应出现 `self._engine.` 前缀与 `on_event` 回调）；SSE 消息改为事件模型构造后，用单元脚本把新旧**线字段集合逐一比对**（function_trace 17 键、step_done ok/fail 键集），再跑 smoke/e2e/embed_load/GUI 四层回归。
- 教训：**"行为不变"要靠三层证据**——(1) 代码级逐字迁移 (2) 协议级字段比对 (3) 运行级回归一致；三者齐了才算 DONE，而不是"看起来一样"。

### 1.16 远程数据源三教训：跨节点参数要会话化、httpx 异常 str 为空、第三方 API 的隐形门槛（Sprint-3）
- 现象：Run All 全链路中 load_index 读不到 config 节点的数据源参数（各节点参数相互独立）→ 索引 0 文件；arXiv 失败时错误明细为空串（httpx 异常 `str()` 为空）；Unpaywall 对示例邮箱返回 422。
- 解决：config 步骤把数据源参数写入 `SessionState.data_source_params`（会话级持久化，显式传参可覆盖）；错误捕获 `str(exc) or repr(exc) or type(exc).__name__` 兜底 + 超时单独语义；DOI 源改读 `UNPAYWALL_EMAIL` 环境变量并给中文指引。
- 教训：**跨步骤共享的配置要落在会话/状态里而不是指望节点参数**；**记录错误时永远给 repr 兜底**（网络库异常常是空 str）；**接第三方 API 先实测其隐形门槛**（真实邮箱、限流、422 语义）。

### 1.17 双分支 code review 的价值：安全/资源/隐私三类漏洞在合并前拦截（Sprint-3 评审轮）
- 现象：windows 评审发现 4 项必须修复——SSRF（远程下载可访问内网/本机）、下载无上限全量内存缓冲、api_key 明文进 input_snapshot/run_records、前端面板对字符串参数崩溃；main 评审发现"PR 只合了 Sprint-2、Sprint-3 未同步"的合并完整性缺口。
- 解决：SSRF 校验 + 重定向逐跳复检（沙箱透明代理 198.18/15 豁免）；200MB 上限 + 流式临时文件；`_redact_secrets` 脱敏；`toText()` 归一化；另修 m2/m3/m5/m6/m8/m9/m11 共 7 项；随后 PR #3 补同步 main。
- 教训：**评审要覆盖"新增的攻击面"而非只查老代码**——本次新增的网络下载/快照持久化正是漏洞高发区；**评审结论要落到 commit 与文档闭环**（sprint-3 §9 记录发现→修复→回归的完整链路）。

### 1.18 PowerShell 5.1 的编码陷阱：Invoke-RestMethod 中文 Body 变乱码 + 无 BOM 中文 .ps1 语法错
- 现象：PR #2 标题/正文中文在 GitHub 显示为乱码（GBK 字节被按 UTF-8 解析）；`scripts/github-pr.ps1` 首版（含中文注释）报 "Unexpected token" 语法错。
- 根因：PS 5.1 把 `Invoke-RestMethod -Body <字符串>` 按 **ANSI 代码页（中文 Windows=GBK）** 编码发出，GitHub 按 UTF-8 解析 → 乱码；同理 PS 5.1 把**无 BOM 的 UTF-8 .ps1 按 ANSI 读**，中文注释的误读会吞掉换行、破坏解析。
- 解决：① API 调用改 `[System.Text.Encoding]::UTF8.GetBytes($json)` 字节数组 + `ContentType "application/json; charset=utf-8"`；② 沉淀 `scripts/github-pr.ps1`（UTF-8 字节体，纯 ASCII 脚本）；③ 用 PATCH 修复 PR #2 正文。
- 教训：**跨编码边界（PS 控制台 GBK / 文件 UTF-8 / 网络 UTF-8）传非 ASCII 文本时，永远显式指定 UTF-8 字节，别信默认值**；`.ps1` 要么纯 ASCII 注释，要么存成带 BOM 的 UTF-8。

## 2. 验证记录（Windows，实际执行）

### 2.1 冒烟（`verify/verify_smoke.py`）—— 8/8 通过
| 检查 | 结果 |
|---|---|
| paperqa 导入 v2026.1.6.dev10+g36348d0ca | ✅ |
| backend/main.py 加载（FastAPI 7 条 API 路由） | ✅ |
| RuntimeTracer（19 个显式目标） | ✅ |
| streamlit 1.62.0 | ✅ |
| litellm | ✅ |
| PyMuPDF 页渲染（PaperQA2.pdf 25 页） | ✅ |
| graphviz python 包 + SVG（自动发现 `C:\Program Files\Graphviz\bin` 的 dot） | ✅ |
| PDF 解析器自动发现（paperqa_pymupdf） | ✅ |

> 早期版本第 7 项曾因缺系统 dot 报 `ExecutableNotFound`（可选安装）；现已自动发现，仅当系统完全未装 Graphviz 时才提示。

### 2.2 全链路端到端（`verify/verify_e2e.py`，真实 DeepSeek）✅
- 后端 8787 `/api/health` ✅ → `load_index`（74 追踪事件）✅ → `retrieve` 候选 `['PaperQA2.pdf']` ✅
- `parse_chunk_embed`（含 vision 图片增强）✅ → `evidence`（9~10 条上下文）✅
- `answer`：**约 1600~1800 字符带引用答案**（Skarlinski2024 pages 1-2 等，示例值随 LLM 输出波动）✅
- 结论：透明流水线在 Windows 上完整跑通。

### 2.3 Agent 流程（`verify/verify_agent.py`）✅
- `agent_query(agent_type="fake")` → **status: success**，8 条上下文 + 引用答案；
- 翻译接口：`'PaperQA2执行检索增强生成。'` ✅。

### 2.4 前端与 Streamlit ✅
- `npm ci` + `vite build`：198 模块（Sprint-3 增加 `DataSourcePanel.jsx` 后）；Vite dev `/` 等均 200。
- `streamlit run --server.headless true`：8501 返回 200。

### 2.5 Sprint-2/3 新增验证（`verify/`）

| 脚本 | 结果（最近一次实测） |
|---|---|
| `verify_provider_switch.py` | 三服务商 `build_settings` 输出一致；deepseek 真实 key SUCCESS；dashscope/openai 占位 key 报各自端点错误（证明路由正确） |
| `verify_embed_load.py` | run 30.5s / 同会话 load 0.0s / 新会话缓存 load 0.0s，texts=23 一致 |
| `verify_remote_e2e.py` | remote+arXiv：下载 1.78MB → 索引 1 文件 → retrieve 1 候选 → evidence 9 contexts → answer 1663 字符 |
| `gui_check.mjs` | GUI Run All 六步 → 答案含 Skarlinski（截图 `us2-06.png`） |
| `gui_check_remote.mjs` | 面板切 remote + arXiv → Run All → 答案含 PaperQA2（截图 `us3-remote.png`） |

## 3. 已知限制

- 图片内容参与回答依赖 `deepseek-v4-flash-vision-exp`（思考已禁用）；图片多时 parse/evidence 变慢（单 PDF 约 50s+）。
- Agent(ToolSelector) 对模型工具调用格式稳定性未全量验证（macOS 基线即常 status=fail）；优先透明流程。
- 无浏览器内逐句高亮；"句子级"信息以 chunk 文本 + 页码预览提供。
- 本地向量模型首次使用需联网（HF，~90MB）。
- Graphviz 二进制可选；缺失时仅影响 SVG/PNG 下载按钮。

## 4. 安全整改记录（仓库公开前）

为把仓库公开，完成以下安全整改：

| 项 | 整改内容 |
|---|---|
| 密钥硬编码 | 删除所有源码/文档中的真实 API Key；CLI 脚本改为从环境变量 / `.env` 读取；新增 `.env.example` 模板，`.env` 加入 `.gitignore` |
| git 历史密钥 | 用 `git filter-repo --replace-text` 清洗**全部历史提交**中的 4 组密钥并强推（旧历史不可逆重写） |
| CORS | 后端 `allow_origins` 由 `*` 收紧为仅 `http://localhost:5173` / `http://127.0.0.1:5173` |
| 前端注入 | React 默认转义后端文本；Streamlit `_dot_escape` 增加 DOT 特殊字符转义（`< > { } | \ " \n`） |
| 监听范围 | 后端仅监听 `127.0.0.1`（不对外网暴露） |
| 输出编码 | CLI 脚本 `sys.stdout.reconfigure(utf-8)` 修复 GBK 控制台打印 emoji/中文崩溃 |
| SSRF 防护（Sprint-3） | 远程数据源下载前校验 URL：仅 http/https、拒绝本机/内网/链路本地/保留地址，重定向逐跳复检（≤5 跳）；沙箱透明代理段 198.18.0.0/15 豁免并注释 |
| 下载上限（Sprint-3） | 单文件 200MB 上限（Content-Length 预检 + 流式计数）+ 流式写 `.part` 临时文件后原子改名，防内存/磁盘被打爆 |
| 密钥脱敏（Sprint-3） | `orchestration._redact_secrets`：`input_snapshot`/`run_records` 中 api_key/token 等递归脱敏为 `***`（session_records API 不再泄露明文） |
| 事件历史上限（Sprint-3） | `RunEventBroker` 历史 500 条/键，防内存无界增长 |

- **仍需用户操作**：曾暴露过的 DeepSeek Key（以及其他旧密钥）请在服务商控制台**撤销并重新生成**。
- 验证：整改后 `verify_smoke.py` 8/8、`manual_test_internet_connection.py` 正常连接、`git grep` 全历史无密钥；Sprint-3 安全项由 windows 分支 code review（sprint-3 文档 §9）复核并回归通过。
