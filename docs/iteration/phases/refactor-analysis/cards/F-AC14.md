# F-AC14 **复制按钮状态串台**：点"复制答案"后"复制 output"/"复制报错"同时显示"已复制 ✓"——根因：`Flow

- `card`: F-AC14
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）**

## 规模
2

## 来源
**用户走查 2026-09-20（UTC+8）**：Sprint-16 走查新增问题②（用户要求"检查所有按钮行为"→ 审计已完成）；**2026-09-21** 评估已出并拍板 Sprint-17 插入、新检查须带反向对照

## Sprint
Sprint-17（治理批 G1 搭车）

## 正文
`[Bug]` **复制按钮状态串台**：点"复制答案"后"复制 output"/"复制报错"同时显示"已复制 ✓"——根因：`FlowNode.jsx` 三个复制按钮共用同一个 `copied` state（:42，被 :187/:199/:224 消费）。**全量按钮审计结论（2026-09-20）**：同一文件内 `FunctionTraceNode.jsx` 的"复制报错"用的是**独立** `errCopied`（:27/:155）、翻译按钮有 `disabled={translating}`（:122）、`SchemaForm.jsx` 各控件有 `disabled={readonly}`（:180~:265）、App 工具栏/子画布按钮均有 `active`/计数/title 反馈——**只有 FlowNode 这三个按钮有问题**。修法：按按钮各自一个 state（照抄 `FunctionTraceNode` 的写法）

## 证据
**影响评估（2026-09-21）**：见 [`2026-09-21-fac13-14-impact.MD`](../2026-09-21-fac13-14-impact.MD)——修复面=三个独立 state + 三个 timer；受影响检查 `gui_check_s15_output_view.mjs`（只断言剪贴板内容）与 `gui_check_s15_error_copy.mjs`（19 断言）**必须复跑**；新增 `gui_check_fac14_copy_state.mjs` 断言"点 A 时 B/C 文案不变 + 1.5s 后各自复位"
