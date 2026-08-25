# 1-WORKFLOW —— 项目工作流（开发规范 / 知识管理 / 项目管理）

> 适用范围：`PaperReading-MAC`（分支 `mac`，macOS 原版，原始部署 `/Volumes/Extreme SSD/vscode_projects/PaperReading`）。
> 架构见 `2-ARCHITECTURE.MD`，经验教训见 `3-LEARNED.MD`。

---

## 1. 知识管理规范

文档统一放在 `docs/`，按"一类问题一个文档"拆分，根目录 `README.md` 只做入口：

| 文档 | 负责回答 |
|---|---|
| `docs/1-WORKFLOW.MD` | 开发规范、知识管理规范、项目管理、运行手册 |
| `docs/2-ARCHITECTURE.MD` | 系统架构、模块职责、数据流、模型与存储约定 |
| `docs/3-LEARNED.MD` | 开发经验教训、踩坑记录、验证记录、已知限制 |

规则：

1. 新增知识先归类（流程→1，结构→2，经验/教训→3）；无法归类才新开编号文档。
2. 代码/依赖/模型/路径变更必须同步更新对应文档。
3. macOS / Windows 双轨：两仓库文档结构一致（同名三件套），内容分别描述各自平台；共性内容允许重复但不矛盾。
4. 架构图用 Mermaid。

## 2. 开发规范

- **改动范围**：mac 仓库只保留原版；仅当模拟运行发现原文件代码缺陷时，才直接修改原文件（并同步到 windows 仓库）。
- **密钥**：读取环境变量 `OPENAI_API_KEY`；`.env`/脚本中旧 key 保留注释备查。
- **依赖**：`paper-qa/uv.lock` 锁定（fhlmi==0.42.1、litellm==1.76.1 等）；venv 位于 `paper-qa/.venv`，Python 3.13。
- **入库排除**：`node_modules/`、`__pycache__/`、`.pytest_cache/`、`._*`（AppleDouble）、`data/parsed/*.jsonl`、`tmp.log`、`dist/`（本仓库经 `.git/info/exclude` 排除，避免新增文件污染原目录）。
- 常见 macOS 噪音：`find ./ -type f -name '._*' -delete` 清理 AppleDouble。

## 3. 项目管理（分支与远程）

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`mac`（本仓库）｜`windows`（Windows 移植版）
- 约定：每类工作一个提交；提交信息 `type: 说明`。

## 4. 运行手册（macOS）

来自 `常用sh命令合集.txt` 的原始命令：

```bash
# 激活环境（venv 位于 paper-qa/.venv，Python 3.13）
source "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/.venv/bin/activate"

# 加载密钥（bash 风格 .env）
source ~/.secrets/paperqa.env

# 运行测试
uv run pytest -n auto

# 启动 ReactFlow 原型后端 (127.0.0.1:8787)
pip install -r ".../reactflow-paperqa-prototype/backend/requirements.txt"
python ".../reactflow-paperqa-prototype/backend/main.py"

# 启动前端 (127.0.0.1:5173)
cd ".../reactflow-paperqa-prototype/frontend"
npm install
npm run dev

# CLI 交互式问答（输出日志）
"$VENV/bin/python" ".../paper-qa-script/manual_index_paper.py" 2>&1 | tee tmp.log
```

macOS 环境关键版本：Python 3.13（Homebrew）、paperqa `2026.1.6.dev10+g36348d0ca`（本地源码）、依赖见 `paper-qa/uv.lock`。

使用流程与 Windows 版一致（Config 节点 → Load Index → Retrieve → Parse Chunk Embed → Evidence → Answer），
模型默认：`openai/qwen-omni-turbo` + `openai/text-embedding-v4`（DashScope OpenAI 兼容端点）。
