# A-COST 成本归属：finish --usage-* 未用 ⇒ 损失只能从会话日志反推

- `card`: A-COST
- 索引: [../backlog.MD](../backlog.MD)

## 状态
候选

## 规模
3

## 来源
2026-09-29 用户要求反例加「实际损失」并用报价表计价时暴露

## Sprint
—

## 正文
`scripts/agent-ops.py` 早已支持 `--usage-in/--usage-out/--usage-cache-read/--usage-cache-write`，但 `agents/runtime/registry.json` 里 **99 条 run 只有 8 条带 `usage`**（且都是夹具数字）⇒ **真实工作一条 usage 都没有**，成本**无法按 run 归属**。

后果：反例档的实际损失只能从会话日志按时间窗／步段反推，**分段规则靠人判**（案例 12 明写 ±2.3 倍不确定度）。

**方向**：`finish` 时从会话日志自动带入 usage，或至少强制显式声明「本 run 未记 usage」。

**验收**：新增 run 的账本行带真实 usage，且「某批花了多少」可由账本直接算出。
