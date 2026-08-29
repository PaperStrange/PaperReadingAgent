# verify/ 验证脚本说明

本目录是 Windows 移植的自动化验收工具（可重复执行）：

| 脚本 | 内容 | 运行前提 |
|---|---|---|
| `verify_smoke.py` | 8 项冒烟检查：paperqa 导入、后端 FastAPI 路由、RuntimeTracer、streamlit、litellm、PyMuPDF 页渲染、graphviz(py)、PDF 解析器自动发现 | 无 API 调用，纯离线 |
| `verify_e2e.py` | 启动真实后端 → 全链路 6 步（config→load_index→retrieve→parse_chunk_embed→evidence→answer），校验答案长度并保存结构化结果到 `verify_e2e_result.json` | 需要 `OPENAI_API_KEY` 环境变量（DeepSeek） |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | 同上，且索引 `verify_e2e_index` 已存在（e2e 先跑过） |
| `verify_provider_switch.py` | 验证服务商切换（deepseek/dashscope/openai）：配置解析、密钥优先级、build_settings、实际连通性/路由 | 无需有效 key；第 4 步 deepseek 需真实 key |
| `verify_embed_load.py` | parse_chunk_embed 三种模式：run（重跑）/load 同会话（秒级）/load 新会话（embed 缓存），校验 texts 数量一致 | 需要 `OPENAI_API_KEY`（DeepSeek）+ 本地 st- 向量模型 |
| `verify_remote_e2e.py` | remote 数据源全链路（Sprint-3）：config(remote+arXiv) → load_index（下载+索引）→ retrieve → parse → evidence → answer | 需要 `OPENAI_API_KEY`；联网（export.arxiv.org） |
| `gui_check.mjs` | GUI 全链路：Playwright 打开前端 → 点 "Run All (Left-to-Right)" → 等待答案出现 → 截图 | 后端 8787 + 前端 5173 已启动；`node verify\gui_check.mjs`（playwright 取前端 node_modules） |
| `gui_check_remote.mjs` | GUI 远程数据源（Sprint-3）：Config 面板切 remote + 填 arXiv ID → Run All → 答案出现 → 截图 `us3-remote.png` | 同上 + 联网 |

运行示例：

```powershell
$env:OPENAI_API_KEY = "<DeepSeek key>"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py
.\.venv\Scripts\python.exe .\verify\verify_e2e.py
.\.venv\Scripts\python.exe .\verify\verify_agent.py
.\.venv\Scripts\python.exe .\verify\verify_provider_switch.py
.\.venv\Scripts\python.exe .\verify\verify_remote_e2e.py   # Sprint-3 remote 全链路（联网）
node .\verify\gui_check.mjs          # GUI（需先启动前后端）
node .\verify\gui_check_remote.mjs   # GUI remote 数据源（需先启动前后端 + 联网）
```

已知差异：graphviz 系统二进制缺失时冒烟第 7 项报 `ExecutableNotFound`（可选安装，见 docs/03 §7）。
