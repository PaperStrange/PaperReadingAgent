# F2 全盘验收指南（2026-08-31）

> 依据：`docs/iteration/sprint/2026-08-31-sprint-13.md` §7「F2 用户验收清单」。本指南为验收执行版（操作步骤 + 通过判据 + 反馈模板）。
> 状态：**验收进行中**（前后端已由主代理启动：后端 8787 / 前端 5173，浏览器打开 http://127.0.0.1:5173）。

## 一、验收范围

F2 = 配置面板深化 + SSOT 驱动前端，三阶段成果：

- **阶段 A（Sprint-11）**：`/api/config_schema` + `/api/config/validate` 端点、M7 默认值收敛锁、只读字段清单
- **阶段 B（Sprint-12）**：SchemaForm 全字段交互表单（类型控件/字段级校验/impacts/provider 联动），取代三个手写面板
- **阶段 C（Sprint-13）**：手写字面量退役（默认值 schema 派生）、Settings 升级同步护栏（基线快照 + CI 检查）

共 10 项：自动证据 5 项 + 交互验收 5 项。

## 二、自动证据 5 项（2026-08-31 已由主代理现场复跑，用户可随时抽查复跑）

| # | 检查 | 复跑命令 | 结果 |
|---|---|---|---|
| 1 | config_schema 一致性 | `.\.venv\Scripts\python.exe .\verify\verify_config_schema.py` | ✅ 114 断言全 PASS（含前端零硬编码 23 键 + Settings 基线护栏） |
| 2 | 冒烟 + spec 校验 | `.\.venv\Scripts\python.exe .\verify\verify_smoke.py`；`foreach ($f in Get-ChildItem agents\functions\*.md) { .\.venv\Scripts\python.exe .\scripts\agent-ops.py validate-spec $f.FullName }` | ✅ 8/8 + 7/7 |
| 3 | 前端构建 | `npm run build`（frontend 目录） | ✅ 324KB |
| 4 | GUI 回归 s4 | `node .\verify\gui_check_s4.mjs`（需前后端已启动） | ✅ 光标 3 断言 + provider 联动 4 断言全 PASS |
| 5 | GUI schema 表单 | `node .\verify\gui_check_config_schema.mjs`（需前后端已启动） | ✅ defaults-derived-from-schema PASS + 截图 ×2（`verify\f2-schema-form.png`、`verify\f2-schema-form-validation.png`） |

## 三、交互验收 5 项（浏览器 http://127.0.0.1:5173）

| # | 操作 | 预期（通过判据） |
|---|---|---|
| 1 | 打开页面，看 Config 节点 | 全字段表单：7 分组 23 字段（LLM/Embedding/Parsing/Agent/Answer/数据源/Index），只读字段带 🔒 |
| 2 | 看 JSON 编辑区 | 页面加载后自动含 schema 默认值（如 `st-...` 模型、`chunk_chars: 5000`），无需手动输入 |
| 3 | temperature 输入 `5`，等约 1 秒 | 字段红框 + 红色错误文案（防抖 ~1s）；清空该字段 → 错误消失 |
| 4 | provider 下拉：切 dashscope，再切 deepseek | dashscope → api_base/model/vision/embedding 自动带出；deepseek → embedding_model 被删除、顶部 hints 出现"多语言"自动选择说明 |
| 5 | 看 impacts 提示区 | ⚠ 影响提示（重建索引/重下载模型/需联网）未切换时即常驻可见 |

## 四、问题反馈模板

```
【验收项】第几项 / 什么功能（如"第4项 provider 联动"）
【操作】  你做了什么（步骤顺序、输入值）
【实际】  看到什么——截图最直接（Win+Shift+S 可直接粘贴到对话）；报错文字原样贴
【期望】  你认为应该是什么样
```

约定：不用分析原因，给"实际 vs 期望"的差距即可；页面打不开 → 直接说"打不开"+浏览器提示；截图可附上或只报文件名。

## 五、验收结论回传

- 逐项 ✅/❌ 发回主代理 → 全过：停服务、F2 状态转"用户验收通过"；有 ❌：修复闭环后交用户复验。
- 全部通过后，F2 从"转用户验收"更新为"✅ 验收通过"（`5-VERSIONS.MD` §3 与 sprint 文档同步）。
