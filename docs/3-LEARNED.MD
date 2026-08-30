# 3-LEARNED —— 开发经验教训（踩坑记录 / 验证记录 / 已知限制）

> 适用于 `PaperReading-Windows`。规范/运行见 `1-WORKFLOW.MD`，架构见 `2-ARCHITECTURE.MD`。
> 本文件记录**踩过的坑、为什么、怎么解决**，以及历次验证结果与遗留限制。

---

## 1. 踩坑记录（含原因与解决）

> **经验分类索引（2026-08-30 起维护）**：新教训按类归位，编号仍按时间递增（历史不改号）。

| 分类 | 条目 |
|---|---|
| 🖥️ 平台/环境（Windows·PowerShell·端口·编码） | 1.6、1.7、1.8、1.9、1.11、1.18、1.20、1.31 |
| 🧩 框架/服务商（paperqa·litellm·模型） | 1.1、1.2、1.3、1.4、1.14、1.25、1.27 |
| 📦 依赖与版本管理 | 1.5、1.13 |
| 🎨 前端与测试驱动（React·Playwright） | 1.10、1.12、1.19（光标部分） |
| 🛡️ 安全与防护 | 1.16、1.17、1.33、§4 整改表 |
| 🏗️ 工程方法（分层/一致性/自愈） | 1.15、1.17、1.19（长路径/注册表可扩展）、1.21、1.22、1.28、1.32 |
| 🔎 检索与算法改进 | 1.21（来源标记）、1.23 |
| 📋 项目管理与流程 | 1.17（评审闭环）、1.24、1.26、1.28（AgentOps 工程化）、1.29、1.30、1.34、`1-WORKFLOW.MD` §4.4 |

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
- 回顾 1.5（fhlmi/litellm 大版本漂移）与 vendor 本地注入的维护痛点 → 决策：引入 `EngineAdapter` 接口、支持 pip 包注入与版本检查/回滚（见 `docs/iteration/phases/refactor-analysis/refactor-analysis.MD` 主题 E1/E2，`docs/iteration/` 仅 windows 分支维护）。
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
- 教训：**跨编码边界（PS 控制台 GBK / 文件 UTF-8 / 网络 UTF-8）传非 ASCII 文本时，永远显式指定 UTF-8 字节，别信默认值**；`.ps1` 要么纯 ASCII 注释，要么存成带 BOM 的 UTF-8。**（Sprint-9 复发**：`start-agents-dashboard.ps1` 中文注释 + 无 BOM 被 PS 5.1 误读 → 全角括号吞引号、ParserError，已改纯 ASCII；此后"新 .ps1 纯 ASCII 或带 BOM"作为提交前自查项。）

### 1.19 Sprint-4 三个 Windows/前端硬骨头：受控输入光标跳、MAX_PATH、写死的 provider 表
- 现象：① Config JSON 编辑每敲一次光标跳最后一行（受控 textarea 被父组件回写格式化 JSON）；② 用户目录嵌套 PDF 索引报 FileNotFoundError（**Windows MAX_PATH 260 字符**——`\\?\` 前缀才能打开，普通 open 直接失败；递归本身 paperqa 默认已开）；③ provider 表写死三家，无法接 OpenRouter/自定义网关。
- 解决：① textarea 改本地草稿态（聚焦期间外部 params 不覆盖、失焦后跟随），Playwright 用 `execCommand("insertText")+setSelectionRange` 验证光标位置；② `make_settings` 对 Windows 绝对路径统一加 `\\?\` 前缀、parse 步骤拼接不再 re-resolve（否则丢前缀），另补索引损坏自愈（zlib/decompress 签名含 ExceptionGroup 子异常）与缺失目录友好报错；③ provider 注册表 = 内置 + `providers.json`/`PAPERQA_PROVIDERS_JSON` 合并，`/api/providers` 脱敏列表，前端下拉联动（有 embedding API 带出策展模型、无则清空交给 recommender）。
- 教训：**"递归/嵌套"这类问题先实测再归因**（真凶是 MAX_PATH 而非递归开关）；**Windows 深度路径操作永远考虑 260 上限**（`\\?\` 前缀 + 不 re-resolve）；**受控输入组件永远给"聚焦保护"**，否则格式化回写必然打断连续编辑。

### 1.20 后台任务停止 ≠ 端口释放：job_kill 只杀包装 shell，子进程会变孤儿占住端口
- 现象：Sprint-4 GUI 检查后，用户启动 dev server 报 `Error: Port 5173 is already in use`——vite(node) 与后端(python) 是当时后台任务的**子进程**，包装 pwsh 被停后它们存活下来继续监听 5173/8787。
- 解决（SOP）：`Get-NetTCPConnection -LocalPort <port> -State Listen` 定位 PID → `Get-CimInstance Win32_Process` 核对命令行确认是本项目进程 → **只对确认的 PID** `Stop-Process -Id`（绝不批量杀，见 1.11）→ 复查端口 FREE。
- 教训：**停止任何 dev server 后必须复查端口**；把"端口释放"纳入 Sprint 关闭三查的"三查 环境"固定项。

### 1.21 节点参数独立的三连坑：改配置要自动重跑、检索要显式标记来源、回调要设上限（Sprint-5）
- 现象：① 改论文目录后直接跑 load_index 仍索引旧目录（前端只标 stale，不自动重跑 config）→ parse 报 "no such file"；② retrieve top5 看起来与 query 无关——真实是**中文 query 在英文分块上 BM25 零命中 → 回退取索引前 N 个文件**；③ litellm `MAX_CALLBACKS limit of 30`——每次模型实例化（Router）注册 logger，长期运行累计爆表；④ 客户端关闭 SSE 后 `socket.send() raised exception` 噪音。
- 解决：① 下游节点运行前检查 config 节点 stale → 自动重跑 Config（失败中止）；parse 单文件失败给出"核对论文目录并重跑 Config→load_index"定位；② retrieve 按命中去重 + 输出 `result=ranked|fallback_first_n`（让用户看清选择逻辑）；③ 每次 run_step 前置 `_prune_litellm_callbacks`（去重保留最近 20）；④ stream 循环发送前检测 `request.is_disconnected()` 静默退出。
- 教训：**"改了却没生效"先查"哪个节点在用哪份参数"**——节点参数独立的设计下，必须让"配置变更"与"下游执行"自动耦合（stale→自动重跑）；**检索类输出永远带来源标记**，否则"排名"与"回退"无法区分；**第三方 SDK 的全局注册表（回调/钩子）要主动设上限与清理**。

### 1.22 索引对象存储与检索段的一致性：目录指纹 + 整目录重建（Sprint-5 关闭二查）
- 现象：同一索引名跨 paper_directory 复用时，Tantivy 检索段与 `docs/<hash>.zip` 对象存储残留旧引用 → retrieve 报 `No such file .../docs/4a86....zip`；只删损坏的 `files.zip` 无法自愈（段与对象存储不同步）。
- 解决：`load_index{build:true}` 前做一致性判定——索引目录写 **paper_directory 指纹 marker**（`paper_dir_marker.txt`）+ `files.zip` zlib 探针；指纹不一致或探针失败 → **整目录删除重建**；同目录同指纹保持增量（性能不回归）。实测"目录 A→B 切换"检索正确切换。
- 教训：**对象存储与检索索引是两份状态**，自愈必须保证两者同生共死（整目录重建），"只修一半"会留下更隐蔽的旧引用；**跨配置复用同一资源名（索引名）必须显式记录资源指纹**。

### 1.23 检索质量改进的顺序：先立评测基线（F4）再动检索（F1）（Sprint-6）
- 现象/决策：用户反馈"top5 与 query 无关"后，先建 `verify/eval_retrieve.py` 小样本基线（双语料 + 策略断言 + 负对照），再实现多语检索 v1——改动效果可量化对比（"什么是PaperQA？" 由 fallback → keyword_retry 命中，hit@1 A=3/3）。
- 做法：含 CJK 的 query 零命中 → 提取 `[A-Za-z][A-Za-z0-9\-]{2,}` 英文关键词重试（**确定性、零 LLM 成本**）；输出 `query_used/query_strategy/hit_note`；纯中文无关键词仍回退（记录为 F1 后续：query 翻译/双语索引）。
- 教训：**检索/排序类改动先有评测再动手**（否则"变好变坏"靠感觉）；**优化优先确定性方案**（关键词提取）再考虑 LLM 方案（翻译/改写），成本与延迟差一个数量级。

### 1.24 项目管理文档治理：两级 roadmap + 阶段 backlog 卡独立管理（PM 实践）
- 现象：roadmap 只挂在 `refactor-analysis.MD`（分析文档）里，重构收口后规划无处安放；Sprint/Bug/维护边界靠感觉。
- 解决（借鉴 Now/Next/Later + 滚动式规划 + 规划分层）：全局 `docs/iteration/ROADMAP.MD`（三档）↔ 阶段 `phases/<阶段>/{README,roadmap,backlog}.MD`（原规划冻结 + 实际实录 + 卡独立登记）；`1-WORKFLOW.MD` §4.4 制定 Sprint/Bug/维护判定五问 + 严重度分诊 + ~20% 非计划工作预算；分析文档回归纯分析定位。
- 教训：**文档职责要跟着项目生命周期走**——"分析文档"不该长期承载"规划文档"职责；**分级规划**（全局主题级 ↔ 阶段 roadmap ↔ Sprint 细节）比一份越滚越大的 roadmap 更抗漂移；**历史文档（原规划）冻结不重写，执行情况另册实录**。

### 1.25 索引构建的两个坑：TaskGroup 掩埋子异常；aadd 引用推断是隐藏的 LLM 调用（Sprint-7 M1）
- 现象：M1 离线验证脚本真实构建索引时报 `unhandled errors in a TaskGroup (1 sub-exception)`，编排层只透出这句话，**真因被 TaskGroup 掩埋**；去掉封装直接调 `get_directory_index` 复现，真因是 `Docs.aadd` 对首块文本做 **citation 推断 LLM 调用**（`citation_prompt`），占位 key → 401。
- 解决：① 诊断方法——**报错被 TaskGroup 聚合时，剥掉编排层直接复现拿完整 traceback**（别猜）；② 离线化——`aadd` 的 citation 调用可用 **manifest（CSV：file_location,citation,title）** 提供 citation 跳过（结构化提取另受 `use_doc_details` 门控，默认 False 不触发）；PDF 图片还会触发视觉增强 LLM，改用**无图 txt 语料**即可零 LLM 构建（索引探针/指纹/files.zip 逻辑与文件类型无关）。`verify/verify_index_health.py` 因此完全离线。
- 教训：**"构建索引"不是纯本地操作**——paperqa 的 `aadd` 默认会对每个文件做 LLM 引用推断（PDF 还有图片视觉增强），离线测试/无 key 场景必须显式提供 citation（manifest）或换无图语料；**框架把异常包进 TaskGroup 时，验证脚本要保留"直连复现"路径**。

### 1.26 维护批清技术账：把"建议修"沉淀为可执行的维护卡 + 关闭前全量 review（Sprint-7 PM 实践）
- 现象：历次 Sprint Retro/三查的"建议修/后续"散落各处，长期不做会累积成隐蔽技术账；用户要求"清完无遗漏"。
- 解决：backlog 维护卡 M1~M6 独立登记（来源标注 Sprint-5/6 Retro 与三查），用户批准后打包成插队 Sprint-7 一次性清零（M3 按用户指示保留未完成，卡上注明）；每个卡配**可复现 verify 证据**（index_health/prune_callbacks/provider_switch 升级），Sprint 关闭前再跑一次 windows+main 全量 code review 兜底。
- 教训：**三查的"建议修"必须回流 backlog 卡**，否则就是纸面闭环；**清账 Sprint 的 DoD 是"卡清零 + verify 证据入库 + 全量 review 无遗漏"**，而不是"看起来都改了"。

### 1.27 多 provider 共存的 key 污染：make_settings 写回 OPENAI_API_KEY（Sprint-7 用户 openai 实测引出）
- 现象：用户要求 deepseek 与 openai 双 key 共存并可用 openai 走全流程。排查发现 `make_settings` 会把解析出的 api_key 写回 `os.environ["OPENAI_API_KEY"]`——同进程先跑 deepseek 再切 openai 时，`resolve_key("openai")` 读到的通用变量已被 deepseek key 覆盖 → OpenAI 401。实测 openai key 本身有效（到达 OpenAI 端点并认证通过，报"账户无余额"是计费问题而非代码问题）。
- 解决：**移除写回**（paperqa 源码不读该环境变量，所有 litellm 调用都经 `litellm_params` 显式携带 key）；`verify_provider_switch` 新增 3b 离线断言（sentinel 验证不被覆盖 + `resolve_key('openai')` 取自身 key）；新增 `verify_e2e_openai.py` 双阶段固化（openai 全流程 + 同进程 deepseek→openai 切换）。
- 教训：**"把解析结果写回环境变量"是对共享状态的污染**——单 provider 时无害，多 provider 切换时是隐蔽雷；**跨 provider 共存要在真实切换路径上断言**，而不是只测各 provider 单独跑通。

### 1.28 AgentOps 基础设施三教训：职能化划分、用例驱动的调研落地、账本 CLI 的三个实现坑（Sprint-8）
- 现象/决策：① 用户指出评审代理"按分支划分"不合理——应**按职能划分**（分支只是任务参数）；调研印证业界共识（Anthropic 研究系统粒度=一职能一产出物一套工具；CodeRabbit 一 reviewer 五维度；OpenHands 三层模型最贴合）。② 调研结论若不转成**可测用例**，CR/文档审计无法保证实现遵循调研（缺失调研上下文）——故把每条调研结论写成"出处+可测断言+验证方式"（`architecture.MD` §7，原 12 条、UC-13 后增现 13 条），开发即验证。③ 账本 CLI 迭代中三个实现坑：状态机完整性校验写在**变更之后**（对已变数据算哈希必然失配）→ 校验必须放在加载时、任何变更前；`SystemExit("...")` 的消息落在 **stderr**（断言只看 stdout 会误判）；报告解析正则没料到 `- critical <位置>：<问题>` 中级别与位置间有空格 → 用 `\b`+位置捕获组而非假设级别后紧跟冒号。
- 教训：**agent 按职能/能力划分，目标对象（分支/PR/文件集）一律参数化**——同一 spec 换 task 参数即可复用；**调研结论必须"用例化"才能在 Sprint 里被验证**，否则调研与实现脱节；**CLI 的"防篡改校验"要在读取入口做**（写出口校验等于校验自己刚改的数据）；断言 CLI 输出时 stdout/stderr 都要看。

### 1.29 审查范围不得默认收窄 + 中间态文件不入库（用户两个问题，Sprint-8 收尾）
- 现象：① 三查评审超时后我把范围"时间盒化"收窄到 Sprint 交付物，被用户指出这**不能固化为规则**——审查范围应基于"影响范围评估"；且影响范围需要**量化指标**（建议与核心功能相关）。② `registry.json`/runs 报告/截图/静态分析产物等中间态、实时结果、留证文件被我 commit 追踪，污染仓库与远程。
- 解决：① 新增 **impact-assessment 职能**（`agents/functions/impact-assessment.md`）：11 项核心功能静态清单（**v1.2.1 起 12 项**：增 #12 AgentOps 看板，并重定位 reactflow 宿主路径）+ 模块→功能映射；指标方案对比（A 核心功能覆盖率 / B 核心 API 覆盖率 / C 风险加权文件覆盖率 / D 回归证据覆盖率）后选定 **A+B 复合（权重 8:2，阈值 X=50；v1.2 起 N_core/N_routes 运行前自检不写死）**，D 作辅助（后经复合指标细化，见 architecture §8.2 与 roadmap 实际实录 PR #25）；三查顺序 = 〇查范围 → 一查文档 → 二查代码 → 三查环境，recommended_scope 作为 scope 入参，偏离须在 Sprint §9 记理由。② 中间态/留证文件**全部出库**：gitignore + `git rm --cached`（本地保留），远程随 PR 同步清理；**prices.json 属配置（人工维护段）仍入库**——区分"配置输入"与"运行时产物"。
- 教训：**"临时处置"很容易被下一次执行当成"惯例"**——超时收窄是应急手段，规则必须显式写"不得默认收窄"并前置影响评估；**量化指标要多方案对比后选定**，且指标要与用户关心的事物（核心功能）对齐而非技术便利；**仓库边界**：源码/配置入库，运行时状态/生成物/留证截图一律 gitignore（本地留证即可，账本真相源不等于 git 追踪）。

### 1.30 Sprint-9 看板开发五教训 + CI/CD 与 git 卫生分层（Sprint-9 Day1）
- 现象：① Next 16 与训练数据不同——scaffold 自带 AGENTS.md 指引读 `node_modules/next/dist/docs/`（路由 params 是 Promise、`next dev -p` 而非 `--port` 等 breaking changes）；② dev 模式长时间热更新后 `/_next/static/chunks` 403（客户端 JS 加载失败、页面不水合、列表空）→ 重启或**改生产构建**（验收/演示用 `next build + next start`）；③ FTS5 虚拟表**不支持 UPDATE**（`no such column: T.report_body`）→ 内容变更用 delete+reinsert；连字符检索（`code-review`）需**短语查询**（双引号包裹）；④ PS 控制台 GBK 再次搅乱中文 API 往返测试（文件被写坏，git 恢复）→ **API 往返测试必须走 UTF-8 客户端（Node）**；⑤ agents/ 迁移时 Copy-Item 计数 9≠10 暴露 3 条账本 run 与报告文件遗漏 → 按会话留存内容重建——**目录迁移必须逐文件计数核对**。
- 决策：CI 做轻量（离线套件+双构建，push/PR 触发；真实 API e2e 仅 workflow_dispatch）；CD 不做（本地应用无部署目标）；git 卫生分四层——① spec 检查（workspace-check 远程分支 + code-review main 头分支删除）② 仓库 `delete_branch_on_merge`（对 API 合并**异步生效**，删已消失的 ref 报"failed to push some refs"=成功）③ helper merge 自动清理（`-C` 仓库根、跳过当前检出分支）④ 三查审计。
- 教训：**新大版本框架先读它自带的 docs/AGENTS.md 再写码**；**长跑 dev server 出诡异 403 先切生产构建验证**（dev 模式不是验收环境）；**全文检索记得查询端转义/短语化**；**目录搬迁用文件计数做完整性验收**；**工具链自动化（CI/分支清理）要分层设计**——平台设置治本、工具兜底、spec 审计保底。

### 1.31 CI 首跑三坑：版本注入、pwsh 失败传播、冷 runner 环境差异（Sprint-9 CI）
- 现象：① vendored paper-qa editable 安装无 .git 元数据 → setuptools-scm 无法推版本（本地预置环境掩盖此问题）；② pwsh step 只设 `$ErrorActionPreference` 未设 `$PSNativeCommandUseErrorActionPreference` → pip 静默失败而后续命令成功时 step 仍绿；且该变量是**强类型 Boolean**，赋字符串 `"True"` 报 `MetadataError`（必须 `$true`）；③ 冷 runner 无 Graphviz → `verify_smoke` 硬编码 `C:\Program Files\Graphviz` → 7/8 失败。
- 解决：install/verify 步骤加 `SETUPTOOLS_SCM_PRETEND_VERSION`（与 `paper-qa/src/paperqa/version.py` 一致）+ 两变量 fail-fast（`$true` 字面量）+ `choco install graphviz`；agents-dashboard 构建步骤 `npm ci --ignore-scripts`——**better-sqlite3 v13 的 GitHub release 无预编译资产（0 assets）**，install script 恒走 `prebuild-install || node-gyp`（冷 runner VS18 不被 node-gyp 识别、本机 VS2019 BuildTools 缺 Windows SDK，两端都编不了源码），但 npm 包内自带 N-API `prebuilds/*.node`，跳过 install script 即可在运行时由包内预编译支撑。
- 教训：**CI 与本地是两套环境**——版本推导、原生命令失败传播、系统二进制都不能假设"本地能跑 CI 就能跑"；CI 首跑要逐步骤盯 log 而非只看结论；pwsh 布尔型偏好变量只能赋 `$true/$false`；**原生依赖先查"包内 prebuild 是否存在、install script 是否画蛇添足"**，能用 `--ignore-scripts` 就不碰 node-gyp。

### 1.32 成本口径混算：分项 USD 未乘汇率、对象级却标 CNY（Sprint-9 二查）
- 现象：`_estimate_cost` 的 `input/output/cache_read/cache_write` 为 USD（未乘 fx），仅 `total` 乘 fx 且对象级 `currency="CNY"` → 按分项汇总的消费方得到 USD/CNY 混算。
- 解决：分项同样 ×fx（保持**分项之和 = total**）；verify_agentops 增加断言锁死"分项为 CNY 且分项之和=total"（26→28 断言）。
- 教训：**数值口径（单位/汇率）必须在单元断言锁死**；对象级 currency 标注是承诺，字段实际单位必须兑现——否则"看板显示 ¥、分项求和却是 $"。

### 1.33 本地看板安全边界：0.0.0.0 + 无鉴权写 + 路径穿越（Sprint-9 二查）
- 现象：`next start` 默认绑 0.0.0.0 + `/api/specs` PUT 无鉴权 → 局域网可覆盖 spec 源码；run-id 直接用作目录名无校验 → 路径穿越读 runs 目录之外文件；spec 名只做"剥离"而非白名单。
- 解决：启动脚本 `-H 127.0.0.1` 显式回环 + 端口占用预检；run-id 白名单 `^[A-Za-z0-9._-]+$` + `path.basename`/前缀双保险；spec 名白名单正则 + 自动补 `.md`——**顺带修掉 UI 打开 spec 404**（审查看到"端点在"，跑通 UI 路径才发现 name 无扩展名）。
- 教训：**本地工具不等于零攻击面**——监听端口 + 写端点就必须显式绑回环（+最小鉴权）；**路径/文件名一律白名单校验（拒绝而非剥离）**；**静态审查要连起来跑通 UI 路径**，端点在 ≠ 前端能用。

### 1.34 spec 升级的文档同步链：自检驱动升级 vs living 文档滞后（Sprint-9 一查）
- 现象：impact-assessment 008 运行前自检发现 2 条宿主路径重定位（映射表陈旧）→ 告警驱动 spec v1.2.1（N_core 11→12，增 #12 看板）；但升级后 1-WORKFLOW/agents README 仍写 11、backlog/roadmap 状态滞后、技术栈文档（Tailwind→antd）陈旧 → doc-audit 一次抓出 8 处 P1。
- 解决：编排方升级 spec 时同步 grep 全库改数字/路径/版本；doc-audit 逐条标出并回填。
- 教训：**spec 数字/常量变更是"文档一致性"变更，必须 grep 全库级联**；影响评估的"运行前自检"是活的防线——映射表与实际不符就要告警并升级 spec，而不是将就着算。

## 2. 验证记录（Windows，实际执行）

### 2.1 冒烟（`verify/verify_smoke.py`）—— 8/8 通过
| 检查 | 结果 |
|---|---|
| paperqa 导入 v2026.1.6.dev10+g36348d0ca | ✅ |
| backend/main.py 加载（FastAPI 8 条 API 路由） | ✅ |
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
| `verify_provider_switch.py` | 全注册表 provider（内置 4 家 + 自定义）`build_settings` 输出一致；deepseek 真实 key SUCCESS；其余占位 key 报各自端点错误（证明路由正确） |
| `verify_embed_load.py` | run 30.5s / 同会话 load 0.0s / 新会话缓存 load 0.0s，texts=23 一致 |
| `verify_remote_e2e.py` | remote+arXiv：下载 1.78MB → 索引 1 文件 → retrieve 1 候选 → evidence 9 contexts → answer 1663 字符 |
| `gui_check.mjs` | GUI Run All 六步 → 答案含 Skarlinski（截图 `us2-06.png`） |
| `gui_check_remote.mjs` | 面板切 remote + arXiv → Run All → 答案含 PaperQA2（截图 `us3-remote.png`） |

### 2.6 Sprint-7 维护批验证（`verify/`）

| 脚本 | 结果（最近一次实测） |
|---|---|
| `verify_index_health.py`（M1 新增） | 合成六形态探针全对 + 真实构建（txt+manifest，零 LLM）→ 篡改 meta.json 判损坏 → load_index 整目录重建自愈 → 探针 False；`paper_dir_marker.txt` 指纹写入确认 |
| `verify_prune_callbacks.py`（M2 升级） | 默认 20 / env=5 → 5 / env=abc,0 → 回落 20 / env=40 → 钳制 30，全部 PASS |
| `verify_provider_switch.py`（M5 升级） | deepseek 真实 SUCCESS；dashscope/openai/openrouter/自定义 占位 key 端点级拒绝（非连接类错误断言）→ 路由实证 PASS |
| `gui_check_s7.mjs`（M4 新增） | 并发 parse+retrieve 双节点计时 `A X.Xs · B Y.Ys` + 先完成节点冻结不被覆盖 + 完成后冻结（截图 `gui_check_s7*.png`） |
| `verify_e2e.py` | Sprint-7 改动后全链路六步 PASS（parse 30.3s / evidence 15.7s / answer 1502 字符；既有健康索引未被三重探针误判重建） |
| `verify_e2e_openai.py`（新增） | config(openai) PASS（provider+key 解析正确）；load_index 起被 OpenAI 计费拒绝（`no credits remaining`）——**key 有效、账户欠费**，完整流程待充值后一键复测；同进程 deepseek→openai key 隔离由 `verify_provider_switch` 3b 离线断言锁定 PASS |

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
