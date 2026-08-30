# 阶段 roadmap：agents-infra（原规划冻结 + 实际实录）

> 归属：`docs/iteration/phases/agents-infra/`。全局三档视图见 `../../ROADMAP.MD`。
> 规则：**原规划一经制定即冻结**（§1 不改写）；执行情况只记入 §2 实际实录。

## 1. 原规划（2026-08-30 用户批准，冻结）

| 阶段 | 目标 |
|---|---|
| 阶段 1 | 调研近半年 agent 最佳实践（star>1000 仓库）+ 架构地基设计（为新增 agent 与 paper-qa workflow 引用打基础） |
| 阶段 2 | 三职能评审 spec（**按职能**划分，用户意见①：code-review / doc-audit / workspace-check 主代理手册）+ runtime 账本（registry.json + runs 报告）+ 跨 IDE 迁移说明（prompt_source 支持 GitHub raw skill.md）；**调研结论→用例表**（用户意见②）驱动开发验证 |
| 阶段 3 | 本地看板应用（前端简约互联网风；后端 Next.js+**SQLite**（用户采纳调研建议，替代 MongoDB）；检索与数据更新快速响应）；支持 spec 在线编辑、skill URL 配置、runtime 状态/自报上下文/估算消费展示、memory 报告浏览 |

> 项目管理：按 `1-WORKFLOW.MD` §4 走 Sprint（用户意见③）；PM 过程可 agent 固化的想法记入 backlog 备选卡 A-PM1~A-PM4。

## 2. 实际实录（随迭代更新）

| 实际 | 日期 | 内容 | 状态 |
|---|---|---|---|
| 阶段 1（调研+架构） | 2026-08-30 | 四条调研线（编排框架/skill 约定/可观测成本/看板栈）→ `architecture.MD` §1~§6；D6 MongoDB→SQLite（用户确认） | ✅ 完成（用户评审：三条修改意见 ①职能划分 ②用例表 ③Sprint 化） |
| Sprint-8（阶段1修订+阶段2） | 2026-08-30 | 职能化划分补充调研 + A-FN/A-UC/A-SPEC/A-LEDGER/A-IDE（`../sprint/2026-08-30-sprint-8.md`）；US-8.1~8.6 全部 DONE；三查按新协议 fan-out（2 code-review 任务 + 1 doc-audit，账本登记），发现项全部闭环；PR #23（`3d58081`） | ✅ 完成 |
| 用户问题修正（阶段 2 收尾） | 2026-08-30 | ① 审查范围不得默认收窄 → 新增 **impact-assessment 职能** + 核心功能覆盖率指标（4 方案对比选定 A，阈值 ≥60%），三查顺序加"〇查范围"；② 中间态/实时结果/留证文件出库（registry/runs/截图/分析产物 gitignore，本地保留） | ✅ 完成（PR #24 `1e78b60`） |
| 复合指标细化（用户问题①深化） | 2026-08-30 | 指标改为 **A+B 复合（权重 8:2）**：composite=(0.8A+0.2B)×100，阈值 **X=50** 两档（>50 全量代码库 / ≤50 Sprint 修改+核心文件区域，核心区域恒含）；impact-assessment spec **v1.1.0**；**双例子代理验证 PASS**（85.45→全量档、14.55→窄档，与修正 ground truth 一致） | ✅ 完成（PR #25 `0853f33`） |
| Sprint-9（阶段 3 看板） | 规划中 | A-DASH 看板应用 + 真实 fan-out 验收演示 | ⬜ 待启动 |

## 3. 落地映射

- 稳定交付物（随分支同步 main）：`docs/agents/`（职能 spec + README 跨 IDE 说明）、`scripts/agent-ops.py`、`agents-dashboard/`（阶段 3）；
- 仅 windows：本阶段 `docs/iteration/phases/agents-infra/` 全部规划/分析文档。
