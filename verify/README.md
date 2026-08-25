# verify/ 验证脚本说明

本目录是 Windows 移植的自动化验收工具（可重复执行）：

| 脚本 | 内容 | 运行前提 |
|---|---|---|
| `verify_smoke.py` | 8 项冒烟检查：paperqa 导入、后端 FastAPI 路由、RuntimeTracer、streamlit、litellm、PyMuPDF 页渲染、graphviz(py)、PDF 解析器自动发现 | 无 API 调用，纯离线 |
| `verify_e2e.py` | 启动真实后端 → 全链路 6 步（config→load_index→retrieve→parse_chunk_embed→evidence→answer），校验答案长度并保存结构化结果到 `verify_e2e_result.json` | 需要 `OPENAI_API_KEY` 环境变量（DeepSeek） |
| `verify_agent.py` | Agent 流程（fake agent）+ 翻译接口 | 同上，且索引 `verify_e2e_index` 已存在（e2e 先跑过） |

运行示例：

```powershell
$env:OPENAI_API_KEY = "<DeepSeek key>"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
.\.venv\Scripts\python.exe .\verify\verify_smoke.py
.\.venv\Scripts\python.exe .\verify\verify_e2e.py
.\.venv\Scripts\python.exe .\verify\verify_agent.py
```

已知差异：graphviz 系统二进制缺失时冒烟第 7 项报 `ExecutableNotFound`（可选安装，见 docs/03 §7）。
