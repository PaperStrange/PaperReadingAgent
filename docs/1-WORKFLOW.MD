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
| `docs/iteration/` | 敏捷迭代：`sprint/<日期>-sprint-N.md`（Sprint 计划/执行/Retro + **项目管理与关闭证据**）+ 迭代中新增的其它项目文档 |

规则：

1. 新增知识先归类（流程→1，结构→2，经验/教训→3）；无法归类才新开编号文档。
2. **敏捷迭代**：功能/体验类工作按 Sprint 推进，Sprint 文档统一放 `docs/iteration/sprint/`，迭代中新增项目文档放 `docs/iteration/`（详见 §4）。
3. 代码/依赖/模型/路径变更必须同步更新对应文档。
4. macOS / Windows 双轨：两仓库文档结构一致（同名三件套），内容分别描述各自平台；共性内容允许重复但不矛盾。
5. 架构图用 Mermaid。

## 2. 开发规范

- **改动范围**：mac 仓库只保留原版；仅当模拟运行发现原文件代码缺陷时，才直接修改原文件（并同步到 windows 仓库）。
- **密钥**：读取环境变量 `OPENAI_API_KEY` 或本地 `paper-qa-script/.env`（以 `.env.example` 为模板）；**代码与文档中禁止出现真实密钥**，`.env` 已被 `.gitignore` 忽略。
- **服务商切换**：`PAPERQA_PROVIDER=deepseek|dashscope|openai` 统一切换；各服务商映射集中在 `paper-qa-script/provider_config.py`。
- **安全**：后端 CORS 仅允许本地前端来源、仅监听 `127.0.0.1`；公开仓库前先确认无密钥残留并轮换曾暴露的密钥。
- **依赖**：`paper-qa/uv.lock` 锁定（fhlmi==0.42.1、litellm==1.76.1 等）；venv 位于 `paper-qa/.venv`，Python 3.13。
- **入库排除**：`node_modules/`、`__pycache__/`、`.pytest_cache/`、`._*`（AppleDouble）、`data/parsed/*.jsonl`、`tmp.log`、`dist/`、`.env`（见 `.gitignore`）。
- 常见 macOS 噪音：`find ./ -type f -name '._*' -delete` 清理 AppleDouble。

## 3. 项目管理（分支与远程）

- 远程：`https://github.com/PaperStrange/PaperReadingAgent.git`
- 分支：`main`（跨平台融合/集成分支）｜`mac`（本仓库 macOS 原版）｜`windows`（Windows 移植版）
- 约定：`windows` / `mac` 各自改动后，通过 **Pull Request 合并到 `main`**；每类工作一个提交，提交信息 `type: 说明`。

## 4. Sprint（迭代）项目管理与关闭标准

> 适用：所有功能/体验类改动。Sprint 文档统一放 `docs/iteration/sprint/<日期>-sprint-N.md`；迭代中新增项目文档放 `docs/iteration/`。

### 4.1 Sprint 生命周期

`Plan（目标+Backlog+验收标准）` → `Dev（按 US 拆解实现）` → `Verify（可运行验证）` → **`Close（关闭评审）`**。

### 4.2 Sprint 关闭：必须有足够 solid 的证据 + 理由

**关闭 Sprint 的前提是"证据充分、理由明确"。证据需同时包含图文（例如浏览器截图）与文字，并附理由，统一写入该 Sprint 文档的「项目管理与证据」板块。** 缺少证据或无法自证"达成目标"的项不能标记为 done。

#### 证据 checklist（按需选取，尽可能覆盖）

| 类别 | 示例 |
|---|---|
| 🖼️ 功能截图（before/after） | 浏览器截图（面板缩放、全屏、lightbox、按钮、连线效果） |
| 🖼️ 运行/接口输出 | 后端 API 返回、`verify_*.py` 实测输出、日志 tail |
| 🖼️ 命令与产物 | `npm run build`、pytest / e2e 结果、生成的报告 |
| 📝 验收用例 | 对应 Backlog US-* 的验收标准逐条说明，标注通过/未通过 |
| 📝 理由/权衡 | 为什么这么做、关键取舍、为什么不采用其它方案、局限 |
| 📝 边界与回归 | 受影响面、是否破坏既有功能、（可选）回归验证结果 |

截图存放到 `docs/iteration/sprint/`，Markdown 相对路径引用；关闭时做 Self-check（每个 US 有证据、结论可复现、记录了权衡/局限、无回归或已记录）。

### 4.3 Sprint 文档模板

见 `docs/iteration/sprint/_template-sprint.md`。关闭时把第 4.2 节的**项目管理与证据**板块填实。

## 5. 运行手册（macOS）

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
