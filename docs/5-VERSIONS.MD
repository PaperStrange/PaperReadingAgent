# 5-VERSIONS.MD —— 发版记录与版本号规范

> **定位**：记录每次发版的版本号、内容范围与证据；发版只在此文档登记，README/Release 引用本表。
> **首个版本发布时机**：完成阶段 roadmap 记录的全部 Sprint 后**第一次发版**（全局视图 `docs/iteration/ROADMAP.MD`、阶段 roadmap `docs/iteration/phases/refactor-analysis/roadmap.MD`——**均仅 windows 分支维护，main 分支无此文件**；当前尚未发布，见 §3）。

## 1. 版本号规范

- **格式**：`年.月.日-v(R.R.R)`，如 `2026.08.30-v1.0.0`。
- **含义**：
  - 前半 `年.月.日` = 发版日期（零填充两位）；
  - 后半 `R.R.R` = 语义化三段：**主版本.功能版本.修复版本**。
    - `主版本`：架构/不兼容变更（如分层重构落地、协议破坏性改动）→ +1，后两段归零；
    - `功能版本`：新功能（新 Sprint 主题、新面板/端点/数据源类型等）→ +1，修复段归零；
    - `修复版本`：缺陷/体验/文档修复（不发新功能的补丁）→ +1。
- 发版时在仓库打 **git tag**（如 `2026.08.30-v1.0.0`，打在 windows 同步进 main 的合并提交上），并在 GitHub Releases 引用 `docs/5-VERSIONS.MD` 对应行。

## 2. 发版记录

| 版本 | 日期 | 内容摘要 | 对应 Sprint / PR | 分支 |
|---|---|---|---|---|
| （首个版本待发布） | — | 完成 roadmap 全部 Sprint 后发布 `2026.xx.xx-v1.0.0` | — | windows → main |

> 规则：**只有完成"三查"并同步 main 后的提交才可计入发版**（见 `1-WORKFLOW.MD` §4.2）。

## 3. 首个版本 v1.0.0 的范围与进度（roadmap 全景）

| 主题 | 内容 | 状态（2026-09-12） |
|---|---|---|
| A 配置模型 SSOT | 策展 schema + `validate_config` + 前端展示（config_notes/影响提示） | ✅ Sprint-2 完成 |
| 分层地基 | 编排/引擎适配/事件模型/SessionStore（行为不变） | ✅ Sprint-2 完成 |
| B 数据源抽象 | local/URL/arXiv/DOI/manifest + 前端切换面板 + 安全防护 | ✅ Sprint-3 完成 |
| 体验与扩展（插队） | 光标草稿态、`\\?\` 长路径/索引自愈、OpenRouter+自定义 provider、`/api/providers`、ModelConfigPanel（**Sprint-12 起由 SchemaForm 取代**） | ✅ Sprint-4（插队）完成 |
| 实战修复（插队） | 自动重跑 config、retrieve 来源标记、litellm 回调防护、SSE 断连静默、UI 三件套 | ✅ Sprint-5（插队）完成 |
| F1 检索体验（新增候选） | 多语检索 v1（CJK 零命中关键词重试 + 命中理由）+ F4 评测基准起步 | ✅ Sprint-6 完成（v1） |
| 维护批清账（插队） | M1 索引三重探针 / M2 回调上限 env 配置 / M4 并发计时与清理 / M5 verify 路由实证 + gui 依赖显式化 / M6 文档勘误 + **全量 code review（windows+main）清技术账** | ✅ Sprint-7（插队）完成；M3 按用户指示留待后续 |
| AgentOps 基础设施（阶段） | 六职能 spec（调研/影响评估/代码审阅/文档审计/经验教训/工作区核验）+ 账本 CLI + 本地看板 + 轻量 CI | ✅ 阶段完成（Sprint-8 PM #23 · Sprint-9 PR #31 · Sprint-10 收口）；阶段已归档封存，剩余卡迁出 |
| 底座提前批次 | 领域治理壳 M15 / 测试矩阵 SSOT（TG-1/2）/ 账本互斥锁 M10 / 价表官网抓取 M9 / 新 agent 门禁 M14 | ✅ Sprint-14 完成（PR #48） |
| F2 配置面板深化（新增候选） | 阶段 A=SSOT 地基（`/api/config_schema` + `/api/config/validate` 端点、M7 默认值收敛锁）；阶段 B=SchemaForm 全字段交互表单（类型控件/字段级校验/impacts 常驻/provider 联动，取代手写面板）；阶段 C=手写字面量退役（schema 派生默认值 + 前端零硬编码）+ Settings 升级基线护栏 | ✅ 完成（阶段 A=Sprint-11、B=Sprint-12、C=Sprint-13） |
| F2 验收修复（交互信息类） | F-AC1~7/9/11/12：字体 token/hints 聚合/local 条件隐藏/完成后收起/响应式/失败复制与报错定位/状态作用域/双向联动/output 全文/截图清晰度 + TG-3 case-first | ✅ Sprint-15 完成（用户 2026-09-10 验收通过；PR #49） |
| 数据准确性 + 成本韧性 + 调研工作流 | F-AC8 一 provider 一文件 + 官网调研刷新（两周定时）；F-AC10 文献级 checkpoint（零成本续跑）；TG-5 分层 runner + 定时底座 + 三态预算闸门；M16 调研工作流 v2.0（三级深度 + 证据落档 + 归档门禁） | 🔄 **Sprint-16 四卡 19/19 DONE；用户走查已于 2026-09-20（UTC+8）完成、未通过 0 项（45 判定格无 FAIL）；三查重跑进行中（原三查因走查后 26 提交落地而失效）；待三查闭环 + PR/关闭** |
| C 可观测 + E3 v1 | Agent 结构化事件→时间线 + 工作流**只读可视化 v1** | ⏸ hold（**v1 需用户 review 后方可迭代**） |
| E1/E2 框架适配 | pip 注入 + 版本检查/更新/回滚 | ⏸ hold |
| D 基础设施 | 单机多 worker + 会话外置 + 网关分流 | ⏸ hold |
| E3 可编辑工作流 | 编排 DSL/配置 + 执行器 | ⏸ hold |

## 4. 发版流程（与 Sprint 关闭衔接）

1. 每个 Sprint 关闭前执行**三查**（文档审查 / windows+main code review / 工作区与功能完整性核验），修复项闭环；
2. windows 改动经 **PR 同步 main**（`docs/iteration/` 不入 main）；
3. 全部 roadmap Sprint 完成且三查通过 → 在本表登记版本行、打 tag、创建 GitHub Release；
4. 之后的功能/修复按 §1 递增版本号，每个版本一行，引用对应 Sprint/PR 与三查结论。
