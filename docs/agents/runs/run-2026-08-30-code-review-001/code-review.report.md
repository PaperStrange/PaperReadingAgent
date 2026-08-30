# code-review 报告（target=branch:windows, focus=correctness/security/ssot/compat）

> 范围：Sprint-8 交付物（scripts/agent-ops.py、docs/agents/*、verify/verify_agentops.py、1-WORKFLOW §4.2）。已实测：registry integrity 哈希一致、list 只读正常、verify_agentops 18 断言 PASS。

## 分级问题清单
- major scripts/agent-ops.py:100：`_prices_for` 用 `auto.get(model) or manual.get(model)`，manual 段被降级为兜底而非"人工覆盖"（覆盖失效、无告警）。建议：manual 非 null 时优先。**已修（三查分诊）**。
- major scripts/agent-ops.py:173-183/192：状态机两条不一致终态路径——`update --status <终态>` 允许但不设 ended_at/cost；`finish` 允许 queued→terminal 绕过文档状态机。建议：update 只允许 running，finish 仅 running→terminal。**已修（三查分诊）**。
- minor scripts/agent-ops.py:257-281：fetch-spec 的 ref 未参与锁定、fallback 未使用（死字段）。**已修：{ref} 占位替换 + 声明性锁定说明**。
- minor scripts/agent-ops.py:272-273：fetch-spec 无 SSRF 防护。**已修：仅 http/https + 拒绝私网/回环/链路本地/保留地址**。
- minor scripts/agent-ops.py:209：result-file 路径基准硬编码默认账本根，AGENT_OPS_DIR 重定向下崩溃。**已修：改用 _AGENTS_BASE**。
- minor scripts/agent-ops.py:70,75-76：完整性哈希只覆盖 runs、删 integrity 键可绕过、无并发锁。**已修：缺 integrity 键即拒绝**；并发锁记录为已知边界（last-writer-wins，文档措辞改为"检测手改"）。
- minor 模块级：stdout 未 reconfigure UTF-8，非 UTF-8 Windows 终端乱码/崩溃。**已修：main() 开头 reconfigure**。
- minor code-review.md:26 / doc-audit.md:26：focus 枚举与 architecture.MD 漂移。**已修：architecture.MD 改为"以各职能 spec 枚举为准"，doc-audit 补 knowledge**。
- nit scripts/agent-ops.py:123：`k != "total"` 死条件。**已修**。
- nit registry.json：running 态 run 入库 + run_id 无查重。**已修：run_id 查重；本轮三条 run 已 finish 闭环**。

## 一句话总结
核心账本与价表 happy path 正确；两条会静默产出错误数据的路径（manual 覆盖失效、update 绕过 finish）已修复并新增回归断言（24 断言 PASS），技术账干净。
