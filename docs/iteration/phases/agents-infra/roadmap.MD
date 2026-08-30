# 阶段 roadmap：agents-infra（原规划冻结 + 实际实录）

> 归属：`docs/iteration/phases/agents-infra/`。全局三档视图见 `../../ROADMAP.MD`。
> 规则：**原规划一经制定即冻结**（§1 不改写）；执行情况只记入 §2 实际实录。

## 1. 原规划（2026-08-30 用户批准，冻结）

| 阶段 | 目标 |
|---|---|
| 阶段 1 | 调研近半年 agent 最佳实践（star>1000 仓库）+ 架构地基设计（为新增 agent 与 paper-qa workflow 引用打基础） |
| 阶段 2 | 四评审代理（按**职能**划分，用户意见①）spec 文件 + runtime 账本（registry.json + runs 报告）+ 跨 IDE 迁移说明（prompt_source 支持 GitHub raw skill.md）；**调研结论→用例表**（用户意见②）驱动开发验证 |
| 阶段 3 | 本地看板应用（前端简约互联网风；后端 Next.js+**SQLite**（用户采纳调研建议，替代 MongoDB）；检索与数据更新快速响应）；支持 spec 在线编辑、skill URL 配置、runtime 状态/自报上下文/估算消费展示、memory 报告浏览 |

> 项目管理：按 `1-WORKFLOW.MD` §4 走 Sprint（用户意见③）；PM 过程可 agent 固化的想法记入 backlog 备选卡 A-PM1~A-PM4。

## 2. 实际实录（随迭代更新）

| 实际 | 日期 | 内容 | 状态 |
|---|---|---|---|
| 阶段 1（调研+架构） | 2026-08-30 | 四条调研线（编排框架/skill 约定/可观测成本/看板栈）→ `architecture.MD` §1~§6；D6 MongoDB→SQLite（用户确认） | ✅ 完成（用户评审：三条修改意见 ①职能划分 ②用例表 ③Sprint 化） |
| Sprint-8（阶段1修订+阶段2） | 2026-08-30 | 职能化划分补充调研 + A-FN/A-UC/A-SPEC/A-LEDGER/A-IDE（`../sprint/2026-08-30-sprint-8.md`） | 🟢 进行中 |
| Sprint-9（阶段 3 看板） | 规划中 | A-DASH 看板应用 + 真实 fan-out 验收演示 | ⬜ 待启动 |

## 3. 落地映射

- 稳定交付物（随分支同步 main）：`docs/agents/`（职能 spec + README 跨 IDE 说明）、`scripts/agent-ops.py`、`agents-dashboard/`（阶段 3）；
- 仅 windows：本阶段 `docs/iteration/phases/agents-infra/` 全部规划/分析文档。
