# PaperReading（Windows 移植版）

> 由 macOS 原版（分支 `mac`）移植而来的论文问答可视化原型，基于 **PaperQA2**。
> 完整文档见 `docs/`，入口如下。

## 这是什么

把论文 PDF 放入 `data/pdf/`，在浏览器 GUI 中按 6 节点流水线
（config → load_index → retrieve → parse_chunk_embed → evidence → answer）
完成索引、检索、证据摘要与带引用的上下文回答（文字 + 图片内容），并提供函数级运行时追踪与 PDF 页码预览。

## 文档（知识管理）

| 文档 | 内容 |
|---|---|
| [`docs/1-WORKFLOW.MD`](docs/1-WORKFLOW.MD) | 项目工作流：开发规范、知识管理、项目管理、**运行手册** |
| [`docs/2-ARCHITECTURE.MD`](docs/2-ARCHITECTURE.MD) | 系统架构：架构图、模块职责、数据流、模型与存储约定 |
| [`docs/3-LEARNED.MD`](docs/3-LEARNED.MD) | 开发经验教训：踩坑记录、验证记录、已知限制 |

## 快速开始

```powershell
# 1) Python 虚拟环境 + 全部依赖
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
.\.venv\Scripts\python.exe -m pip install "fhlmi==0.42.1" "litellm==1.76.1"
cd paper-qa-script\reactflow-paperqa-prototype\frontend; npm ci; cd ..\..\..

# 2) 启动（三终端）
.\scripts\start-backend.ps1     # FastAPI 127.0.0.1:8787
.\scripts\start-frontend.ps1    # 前端 127.0.0.1:5173
.\scripts\start-streamlit.ps1   # 可选 Streamlit 127.0.0.1:8501
```

浏览器打开 http://127.0.0.1:5173 → 在 Config 节点填 DeepSeek Key（`.env` 已含默认值）→ 依次/一键执行 6 个节点。

## 默认模型

| 用途 | 默认值 |
|---|---|
| LLM（答案/引用） | `openai/deepseek-v4-flash` @ `https://api.deepseek.com` |
| 证据摘要 / 图片增强 | `openai/deepseek-v4-flash-vision-exp` |
| 向量化 | `st-multi-qa-MiniLM-L6-cos-v1`（本地，首次自动下载） |

## 验证

```powershell
.\.venv\Scripts\python.exe .\verify\verify_e2e.py    # 全链路（需 DeepSeek key）
.\.venv\Scripts\python.exe .\verify\verify_smoke.py  # 冒烟
```

最近一次全链路验证：**通过**（10 条上下文、1656 字符带引用答案），详见 `docs/3-LEARNED.MD` §2。

## 版本控制

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（macOS 原版）｜`windows`（本仓库）
