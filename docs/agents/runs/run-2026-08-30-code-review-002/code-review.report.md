# code-review 报告（target=branch:main, focus=correctness/compat/merge-completeness）

> 已核对：main=origin/main 84b79dc，windows HEAD=2655919（评审时点）；verify_agentops 18/18 PASS、registry 哈希 MATCH。

## 分级问题清单
- major scripts/agent-ops.py:209：result-file relative_to 硬编码默认账本根（AGENT_OPS_DIR 重定向崩溃，已复现）。**已修：改用 _AGENTS_BASE**。
- major scripts/agent-ops.py:289：parse-report 正则把 ASCII 冒号当分隔符，`engine.py:202` 被截断为 where='engine.py'、行号混入 text。**已修：按首个全角冒号切分；UC-5 增 where 断言（24 断言 PASS）**。
- minor docs/agents/README.md:3/14/39：指向 docs/iteration（windows-only）的引用在 main 上悬空。**已修：改为纯文本措辞**。
- minor registry.json：3 条 running 开账本入库。**已修：本轮三条 run 已 finish 闭环**。
- minor runs/ 入库 vs gitignore 未定。**已定：runs/ 为审计底稿入库，README 注明**。
- nit finish 允许 queued→terminal。**已修：finish 仅 running→terminal**。
- nit fetch-spec 提取 source 块值不 strip 引号。**已修**。

## 同步/完整性说明
- 需同步 main（必须，9 文件）：docs/agents/README.md、docs/agents/functions/*.md×3、docs/agents/runtime/{prices.json,registry.json}、scripts/agent-ops.py、verify/verify_agentops.py、docs/1-WORKFLOW.MD；另 3-LEARNED.MD（1.28，已含入同步分支）。
- 排除：docs/iteration/** 全部 18 项。
- main 落后代码文件：scripts/agent-ops.py、verify/verify_agentops.py（本轮同步）；scripts/*.sh×4 为 main 融合分支刻意保留（非 windows 删除项）。
- main 既有 docs/iteration 行内引用 16 处：pre-existing（代码跨域 prose 引用，标注"仅 windows 维护"），记入 backlog 备选清理（A-M2 候选）。

## 一句话总结
交付物整体可用；parse-report 位置截断（核心分诊链路）已修并加断言；同步清单边界清晰。
