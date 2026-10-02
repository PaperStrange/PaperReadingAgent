# 阶段 backlog：baseline-reform（卡独立管理）

> 归属：`docs/iteration/phases/baseline-reform/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号，本表仅维护卡级信息。
> 启动判定引用 `docs/1-WORKFLOW.MD` §4.4。
> 卡正文自本阶段**成立起**即独立成文：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文。判据：`verify/verify_card_index.py`。

## 1. 功能卡

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| BR-1 | **现行基线逐条盘点 ＋ 分类法 ＋ 处置判据**：棘轮只防恶化不促改善、每次编辑都要付费 ⇒ 补"消费者／最近挡住的真实缺陷／最近返工代价"三格 | 候选 | — | [cards/BR-1.md](cards/BR-1.md) |

合计 **8 点**（M1 盘点已随本批交付 10 条；M2 分类与逐条裁定、M3 落地与反向对照待开）。

## 2. 启动条件

- 本阶段**无 Sprint**：`BR-1` 为「候选」，开 Sprint 按 `docs/1-WORKFLOW.MD` §4.4 判定（本批未开）。
- **授权依赖（必须写清）**：`BR-1` 的 M2/M3 多数处置要改 `agents/policy.json` 的五张上限表或 `verify/**` 的阈值表，而本批授权写入集**不含** `verify/**`、`scripts/**`（只读）⇒ 启动时须先确认写入集，否则只能交付"仅文字"判据（按 `docs/1-WORKFLOW.MD` §6.0 标注并写代价）。
- **全局 ROADMAP 未登记**：本阶段由 2026-10-03 用户原话直接新立，而 `docs/iteration/ROADMAP.MD` 不在本批授权写入集内 ⇒ 该档的"Now/Next 档阶段索引"尚未含本阶段（缺口如实记，见 `cards/BR-1.md` 的未决点）。
