# doc-audit 报告（target=working-tree, focus=links/stale-facts/contradictions/tables）

## 必须修（4 条，均已修）
1. architecture.MD §3.2 role 示例按分支命名 → 已改职能名 + task_id 承载分支。
2. 多处"四评审代理/四份 spec" → 已统一"三职能 spec（workspace-check 主代理手册）"。
3. 账本 CLI "三子命令" → 已改"8 子命令"；docs/agents/README 补 update。
4. backlog A-FN/A-UC/A-SPEC/A-LEDGER/A-IDE 状态 → 已改 ✅ 完成。

## 建议修（6 条，均已修）
5. verify_agentops.py 未入脚本清单 → README(根)/1-WORKFLOW §5.5/verify/README 已补。
6. architecture.MD focus 5 维 vs code-review 6 维 → 已改"以各职能 spec 枚举为准"。
7. §3.2 cost_est/spec_source 字段与 registry 实际不符 → 已按实际修订。
8. 头部/P4/:71 陈旧状态（"待用户评审"） → 已更新为阶段 2 进行中/已解决。
9. spec 位置 docs/agents/*.md → 已改 docs/agents/functions/*.md。
10. UC-7 调研出处引用不准 → 已改"§2.2 文件为源 / §2.3 账本模型"。

## 已核对且一致（供参考）
- ✅ 链接全部可达（sprint-8 ↔ phases ↔ ROADMAP 层级正确）；三查执行者三处一致；用例表 12 条 ≥10；表格无畸形；3-LEARNED 1.28 编号与分类索引一致；registry 三条 run 与 sprint 文档一致。

## 一句话总结
无死链、执行者/用例表/编号一致；问题集中在 Sprint-8 交付后清单类旧文档未同步——10 条已全部修复闭环。
