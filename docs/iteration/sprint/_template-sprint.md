# Sprint N（YYYY-MM-DD）—— <一句话目标>

> 归属：`docs/iteration/sprint/`。复制本文件为 `<YYYY-MM-DD>-sprint-N.md` 后填写（按 Sprint-2/3 已确立的标准格式）。
> 输入：阶段 backlog 卡（`../phases/<阶段>/backlog.MD` 卡号，如 F1）+ 迭代背景/分析文档（`../` 即 `docs/iteration/` 下）。
> 范围：注明涉及分支（默认 windows 迭代 + 完成后同步 main 的对应部分；MAC 验证跳过）。

## 1. Sprint Planning

- **Goal**：<一句话目标 + 关键勘察/背景结论>
- **团队与产能**：团队 = 1（AI 开发者）；预估 **N 点 / ~M h**（故事点 + 预估工时双轨）。
- **周期**：起止与状态（是否 hold、是否有 review 闸门——如 E3 v1 需用户 review）。

## 2. Backlog（用户故事 + 验收标准 + 估算）

| 卡号 | ID | 用户故事 | 验收标准 | 点数 | 预估工时 |
|---|---|---|---|---|---|
| F1 | US-N.1 | <用户故事> | ① <可测标准> ② … | n | mh |

> 卡号对应 `phases/<阶段>/backlog.MD`（无对应卡写 `—`）；本 Sprint 完成后回填该卡的状态。

## 3. 任务看板（Kanban：开卡/推进/完成）

| 卡片 | 状态 | 点 | 开始 | 完成 |
|---|---|---|---|---|
| US-N.1 … | ⬜ TODO | n | | |

> 开卡规则：一次开一张卡并推进到 DONE（或明确 BLOCKED + 理由）；每张卡完成后跑对应回归并记录证据。

## 4. 燃尽图（Burn-down，随进展更新）

总点数 N。

| 里程碑 | 剩余点 | 说明 |
|---|---|---|
| Sprint 开始 | N | YYYY-MM-DD |

```text
剩余
N ┤●
  │
0 └───────────────────────── 时间
    开始 →（继续）
```

## 5. 执行记录（Standup 日志）

- YYYY-MM-DD Sprint Planning 完成；开卡 …。
- YYYY-MM-DD US-N.x DONE：<摘要>；回归证据见 §7。

## 6. Definition of Done（每张卡与整个 Sprint）

- [ ] 行为/验收目标达成（对应回归证据）
- [ ] 分层/命名符合 `refactor-analysis.MD` 目标架构
- [ ] 新边界类型化（pydantic），无复制粘贴的配置/常量
- [ ] 文档同步：`3-LEARNED.MD`（经验教训）、本 Sprint 文档
- [ ] 无密钥/安全回归；提交规范（`type: 说明`）

## 7. 项目管理与证据（Sprint Review 时填实 —— 图文 + 理由）

| US | 证据（截图/命令输出） | 通过情况 | 理由/说明 |
|---|---|---|---|
| US-N.1 | 🖼️ `![说明](./<run>.png)` / `cmd 输出` | 通过 / 部分 / 未通过 | <为什么达成/局限> |

### 权衡与理由 / 边界与回归 / 关闭 Self-check

- <为什么这么做 / 不采用其它方案 / 局限>
- <受影响面 / 回归验证结果>

- [ ] 每个 US 有对应证据（图文 + 说明）
- [ ] 结论来自可复现证据（命令/截图）而非推测
- [ ] 记录关键权衡/理由/局限
- [ ] 未破坏既有功能（或有回归记录）
- [ ] sprint 文档已入库并随分支同步
- [ ] **三查完成且发现项闭环**（一查文档一致性含 4-ALGORITHM 对照 / 二查 windows+main 双分支 code review / 三查工作区零残留+回归全绿），结论写入 §9
- [ ] windows 已 PR 同步 main（不含 `docs/iteration/`）

## 8. 回顾 Retro（Sprint Review 后填）

**做得好（Keep）** / **可改进（Improve）** / **行动项（Action）**（逐条编号，未落实项后续标注状态）

## 9. 评审/同步记录（三查结论 + PR 同步，Sprint 关闭必填）

- 一查（文档审计）结论与修复映射；
- 二查（双分支 code review）分级结论与修复映射；
- 三查（工作区/功能完整性）：`git status` 零残留、回归（smoke/e2e/新增端点/GUI）输出摘要；
- PR 同步 main 结果（PR 号/合并 sha，不含 `docs/iteration/`）。
