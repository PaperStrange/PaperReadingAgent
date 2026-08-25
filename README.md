# PaperReading（macOS 版）

> 基于 **PaperQA2** 的论文问答可视化原型（ReactFlow 6 节点流水线 + FastAPI + Streamlit 调试 UI）。
> 原始部署路径：`/Volumes/Extreme SSD/vscode_projects/PaperReading`。

## 文档（知识管理）

| 文档 | 内容 |
|---|---|
| [`docs/1-WORKFLOW.MD`](docs/1-WORKFLOW.MD) | 项目工作流：开发规范、知识管理、项目管理、**运行手册** |
| [`docs/2-ARCHITECTURE.MD`](docs/2-ARCHITECTURE.MD) | 系统架构：架构图、模块职责、数据流、模型与存储约定 |
| [`docs/3-LEARNED.MD`](docs/3-LEARNED.MD) | 开发经验教训：踩坑记录、验证记录、已知限制 |

## 快速开始（macOS）

```bash
source "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/.venv/bin/activate"
source ~/.secrets/paperqa.env

# 后端 127.0.0.1:8787
python ".../reactflow-paperqa-prototype/backend/main.py"
# 前端 127.0.0.1:5173
cd ".../reactflow-paperqa-prototype/frontend" && npm install && npm run dev
```

默认模型：`openai/qwen-omni-turbo` + `openai/text-embedding-v4`（DashScope OpenAI 兼容端点）。

## 版本控制

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（本仓库）｜`windows`（Windows 移植版）

## 说明

- 原文件缺陷（`runtime_trace.py` 对 staticmethod 的破坏）已在模拟运行中发现并修复，见 `docs/3-LEARNED.MD`。
- 旧 DashScope 密钥均已失效（账户问题）；Windows 移植版已改用 DeepSeek，见 windows 仓库 `docs/`。
