# 3-LEARNED —— 开发经验教训（macOS 版）

> 适用于 `PaperReading-MAC`。规范/运行见 `1-WORKFLOW.MD`，架构见 `2-ARCHITECTURE.MD`。

---

## 1. 发现并修复的原文件代码缺陷

### runtime_trace.py 破坏 staticmethod/classmethod 语义
- 现象：后端 `load_index`（在 RuntimeTracer 上下文内执行 `get_directory_index`）报
  `TypeError: SearchIndex.filehash() takes 1 positional argument but 2 were given`，
  最终 `ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)`。
- 根因：`_install_module_targets()` 把 `@staticmethod`（`SearchIndex.filehash`）也纳入补丁目标；
  `_install()` 经 `getattr(cls, name)` 拿未绑定纯函数后直接 `setattr(cls, name, wrapped)`，
  静态方法被替换成普通实例方法——实例调用 `self.filehash(body)` 时包装器收到 `(self, body)` 两个实参。
  `@classmethod` 存在同类问题。
- 影响：所有带追踪的执行流（后端 load_index、Streamlit 构建索引）都会失败——**macOS 上同样触发**。
- 修复：`_install()` 用 `inspect.getattr_static()` 识别原始描述符，`staticmethod/classmethod` 包装后仍以描述符安装，
  `__exit__` 还原原始描述符。文件：`paper-qa-script/runtime_trace.py`（已同步到 windows 仓库）。

## 2. macOS 基线既有问题（非本次引入）

- **Agent(ToolSelector) 常 status=fail**：`tmp.log` 显示每次 ToolSelector 问答最终 `MalformedMessageError`
  （Qwen 未按工具调用格式返回）。可用 `Agent 模式=fake`（稳定）或"透明流程（推荐）"。
- **终端乱码**：`tmp.log` 中问题文本以 GBK/UTF-8 混码（如 `鐢ㄤ腑鏂囧洖绛斾竴涓?`），是终端编码问题，非代码问题。
- **旧 DashScope 密钥全部失效**（账户问题，非代码问题）：其中一个 DashScope 密钥欠费（Arrearage）、
  另一个 DashScope 密钥模型无权限、OpenAI 密钥配额超限。

## 3. 验证记录（对原代码的模拟运行验证）

本仓库为 macOS 原版，无法在 Windows 原生运行；采用**对原代码的模拟运行验证**：
把原文件完整复制到独立环境（逐字节一致），在 Windows x64 + Python 3.13 上安装依赖并执行，
从而发现原文件自身的问题（该类问题在 macOS 上同样会发生）。

环境：Windows 11 x64 / Python 3.13.2 / Node 23；依赖按 `paper-qa/uv.lock` 版本（fhlmi 0.42.1、litellm 1.76.1）。

| 检查 | 结果 |
|---|---|
| paperqa 导入 v2026.1.6.dev10+g36348d0ca | ✅ |
| backend/main.py 加载（FastAPI 8 条路由） | ✅ |
| RuntimeTracer（19 个显式目标） | ✅ |
| streamlit / litellm / PyMuPDF（25 页渲染） | ✅ |
| graphviz python 包 | ⚠️ 缺系统 dot（可选） |
| PDF 解析器自动发现（paperqa_pymupdf） | ✅ |
| 带追踪 load_index | ❌→✅（修复 runtime_trace 后通过，74 追踪事件） |

## 4. 结论与经验

- 原代码整体结构清晰、跨平台兼容良好；唯一的代码级缺陷集中在 `runtime_trace.py` 的描述符处理。
- 全链路问答在 Windows 上改用 DeepSeek 后完整跑通（见 windows 仓库 `docs/3-LEARNED.MD`）；macOS 侧因 DashScope 账户欠费未能在线复跑，但请求格式/端点连通性已验证。
- 经验：给"透明流程 + fake agent"留默认值，比 ToolSelector 更稳；函数级追踪务必保持描述符语义。

## 5. 安全整改记录（仓库公开前）

| 项 | 整改内容 |
|---|---|
| 密钥硬编码 | 删除所有源码/文档中的真实 API Key；CLI 脚本改为从环境变量 / `.env` 读取；新增 `.env.example` 模板，`.env` 加入 `.gitignore` |
| git 历史密钥 | 用 `git filter-repo --replace-text` 清洗**全部历史提交**中的密钥并强推 |
| CORS | 后端 `allow_origins` 由 `*` 收紧为仅本地前端来源 |
| 前端注入 | Streamlit `_dot_escape` 增加 DOT 特殊字符转义 |
| 监听范围 | 后端仅监听 `127.0.0.1` |

- **仍需用户操作**：曾暴露过的 DashScope / OpenAI Key 请在服务商控制台**撤销并重新生成**。
