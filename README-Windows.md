# README（Windows 移植版）

> 由 macOS 原版（分支 `mac`）移植。完整说明见 `docs/`；本文件为快速上手。

## 这是什么

基于 **PaperQA2** 的论文问答可视化原型：把论文 PDF 放入 `data/pdf/`，在浏览器 GUI 中按
6 节点流水线（config → load_index → retrieve → parse_chunk_embed → evidence → answer）完成
索引、检索、证据摘要与带引用的上下文回答（文字+图片内容），并提供函数级运行时追踪与
PDF 页码预览。另有 Streamlit 调试 UI。

## 环境要求

- Windows 10/11 x64，Python 3.11+（推荐 3.13），Node 18+（推荐 20+），npm
- 可选：Graphviz 系统二进制（`winget install Graphviz.Graphviz`）

## 一次性安装

```powershell
# 1) Python 虚拟环境 + 全部依赖
powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1

# 2) 与 mac 环境对齐的锁定版本（避免 API 行为漂移）
.\.venv\Scripts\python.exe -m pip install "fhlmi==0.42.1" "litellm==1.76.1"

# 3) 前端依赖
cd paper-qa-script\reactflow-paperqa-prototype\frontend
npm ci
```

## 启动

```powershell
# 终端 1：FastAPI 后端（127.0.0.1:8787）
.\scripts\start-backend.ps1
# 终端 2：前端（127.0.0.1:5173）
.\scripts\start-frontend.ps1
# 可选 终端 3：Streamlit 调试 UI（127.0.0.1:8501）
.\scripts\start-streamlit.ps1
```

浏览器打开 http://127.0.0.1:5173 → 在 Config 节点填入 DeepSeek API Key（或已写入
`paper-qa-script\.env`）→ 依次/一键执行 6 个节点。

## 默认模型配置（Config 节点可改）

| 用途 | 默认值 |
|---|---|
| LLM（答案/引用） | `openai/deepseek-v4-flash` @ `https://api.deepseek.com` |
| 证据摘要（含图片） | `openai/deepseek-v4-flash-vision-exp` |
| 图片增强 | `openai/deepseek-v4-flash-vision-exp` |
| 向量化 | `st-multi-qa-MiniLM-L6-cos-v1`（本地，首次自动下载） |

## 验证

```powershell
.\.venv\Scripts\python.exe .\verify\verify_e2e.py    # 全链路（需 DeepSeek key）
.\.venv\Scripts\python.exe .\verify\verify_smoke.py  # 冒烟
```

最近一次全链路验证：**通过**（10 条上下文、1656 字符带引用答案），详见 `docs/03-…md` §5。

## 文档

- `docs/01-架构总览与文件说明.md` — 架构图（Mermaid）+ 全部文件职责
- `docs/03-Windows移植说明与运行手册.md` — 改动清单、踩坑记录、验证记录
- macOS 原版对应文档在 `PaperReading-MAC/docs/`
