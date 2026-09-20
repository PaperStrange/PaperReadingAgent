# 阶段 backlog：refactor-analysis（卡独立管理）

> 归属：`docs/iteration/phases/refactor-analysis/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号（如 `F1`），本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4（Sprint/Bug/维护边界）。
> **卡片来源与时间口径（2026-09-20 用户要求）**：来源带类型前缀 `[规划]`/`[用户插入]`/`[Bug]`/`[走查]`/`[三查]`/`[评审]`；时间字段一律用**网络时间 UTC+8**（`YYYY-MM-DD（UTC+8）`），不得用本机时区（本机 UTC+9）。细则见 `1-WORKFLOW.MD` §3。

## 1. 功能卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 |
|---|---|---|---|---|---|
| R-C | C Agent 可观测闭环 + E3 v1 只读可视化（原规划 Sprint-4） | 未估 | ⏸ hold | — | **E3 v1 交付需用户 review** |
| R-E | E1/E2 pip 注入 + 版本检查/更新/回滚（原规划 Sprint-5） | 未估 | ⏸ hold | — | 依赖引擎适配层（已就绪） |
| R-D | D 单机多 worker + 会话外置 + 网关分流（原规划 Sprint-6） | 未估 | ⏸ hold | — | 依赖会话外置化 |
| R-E3 | E3 可编辑工作流（原规划 Sprint-7+） | 未估 | ⏸ hold | — | 依赖 R-C 验收 |
| F1 | 检索体验与查询质量：多语检索 | 13 | ✅ 完成(v1) | Sprint-6 | v1=关键词重试+命中理由；后续：query 翻译/双语索引（F4 评测选型） |
| F2 | 配置面板深化 + SSOT 驱动前端（/api/config_schema + 全字段交互 + 单一受控状态） | 16（分阶段：A 5 + B 6 + C 5） | ✅ 完成（阶段 A=Sprint-11、B=Sprint-12、C=Sprint-13 全完成，转用户验收） | — | 评审 m1 欠账 + m10 遗留；M7 并入；阶段拆解见 Sprint-11 §0 |
| F3 | Agent 接入后端 + 事件时间线雏形 | 未估 | 候选 | — | R-C 的前置步骤 |
| F4 | 本地评测基准（检索/证据/答案三环） | 3(起步) | ✅ 起步 | Sprint-6 | `verify/eval_retrieve.py`；后续扩充语料 |
| F-AC1 | F2 验收①1.1：标题字号收敛 + 卡片内字体类型统一（token 化），排查全部卡片批量修 | 2 | ✅ 完成（走查 PASS） | Sprint-15 | 用户 F2 验收 2026-08-31 |
| F-AC2 | F2 验收①1.2：hints 限高滚动 + 影响上浮标题聚合（"LLM（6项，3项被改动）"改动数标红） | 2 | ✅ 完成（走查返工已闭环：无默认值字段计数 + 输入全非受控杜绝光标跳） | Sprint-15 | 用户 F2 验收 2026-08-31 + 走查 2026-09-10 |
| F-AC3 | F2 验收①1.3：新增 `local_dir` 字段（默认 data/pdf）+ 后端接线 + 数据源条件隐藏无关参数（schema show-if 语义）+ 排查其他卡片交互 | 4 | ✅ 完成（走查 PASS） | Sprint-15 | 用户 F2 验收 2026-08-31 |
| F-AC4 | F2 验收②：节点运行完成后自动收起全部展开项，仅留 output_snapshot | 1 | ✅ 完成（走查 PASS） | Sprint-15 | 用户 F2 验收 2026-08-31（Q4 口径） |
| F-AC5 | F2 验收③：subcanvas 桌面分辨率响应式自适应（手机暂不考虑） | 1 | ✅ 完成（走查 PASS） | Sprint-15 | 用户 F2 验收 2026-08-31 |
| F-AC6 | F2 验收④：失败一键复制 + 任意状态框选复制已完成卡片 + 主画布报错摘要+可展开完整堆栈；**走查追加**：节点报错后 Function Subcanvas 自动定位到报错卡片（五轮：多报错卡时定位最新一张 + "定位下一处报错"逆序循环按钮；七轮：报错卡 zIndex 10000 压顶 + 按 fn_title 找卡居中，不按相对位置；八轮：定位目标 zIndex 10001+描边高亮唯一压顶、循环基准按当前可见定位卡逆序、防回跳） | 3 | ✅ 完成（走查五~八轮全闭环，用户复验通过） | Sprint-15 | 用户 F2 验收 2026-08-31（Q5 口径）+ 走查 2026-09-10 |
| F-AC7 | F2 验收⑤：执行状态信息仅展示在执行节点下（作用域修复）；**走查语义修正**：切换后展示**切换后节点**的状态行（无状态显示 idle），而非直接不显示 | 1 | ✅ 完成（走查返工已闭环） | Sprint-15 | 用户 F2 验收 2026-08-31 + 走查 2026-09-10 |
| F-AC8 | F2 验收⑥：provider_config 拆**一 provider 一文件** + tech-research 官网调研更新 + **定时更新（默认两周）**（与 M9 共用调度） | 6 | ✅ 完成（Sprint-16：providers/*.json + 刷新脚本 + M16 归档 + 两周定时）。**决策终态**：dashscope model 由用户拍板 `openai/qwen3.5-omni-plus`（官网证据，已实测可用）；**遗留待用户决定**：二轮研究判定 `openrouter model = needs_review`（现值保留、候选未采纳）；`platform.openai.com` **403** → 按 fail-closed 保留旧文件 | Sprint-16 | 用户 F2 验收 2026-08-31（Q1 方案）；调研结论 run-047 |
| F-AC9 | F2 验收⑦：subcanvas 手动切换节点 → 主画布联动定位（双向联动）；**走查返工**：主画布选中未生效 + 切换后 subcanvas 内容居中/刷新竞态（空白/不相关卡片） | 1 | ✅ 完成（走查返工已闭环：onInit 实例 + setCenter） | Sprint-15 | 用户 F2 验收 2026-08-31 + 走查 2026-09-10 |
| F-AC10 | F2 验收⑧：**文献级 embedding checkpoint**——每篇完成即落盘，失败续跑未完成文献；持续迭代主题 | 4 | ✅ 完成（Sprint-16：逐篇原子落盘 + 零成本复用 + 四重边界，22 断言 PASS） | Sprint-16 | 用户 F2 验收 2026-08-31（Q2 粒度）；调研结论 run-047 |
| F-AC11 | 走查 N1（2026-09-10）：卡片 output 字段**完整查看**（展开/一键复制全文），answer 节点**答案全文展示**（当前 JsonTree 截断 180 字且无复制） | 2 | ✅ 完成（Sprint-15 收尾批，四轮定稿；tooltip 按用户要求移除） | Sprint-15 | 用户走查 2026-09-10 |
| F-AC12 | 走查 N2（2026-09-10）：fn 卡**论文截图清晰度**提升（runtime_trace 0.45 缩放 → 高分辨率渲染；关联 `docs/iteration/embed-optimization.MD` 预分割卡「文本/图片/表格/公式」US-5 后续） | 2 | ✅ 完成（Sprint-15 收尾批，预览 1.0 缩放 + 1.2MB 护栏，612×792 实证） | Sprint-15 | 用户走查 2026-09-10 |
| F-AC13 | `[Bug]` 节点运行按钮**点击 1~2 次无响应**（第 3 次才生效）——**根因已定位（2026-09-20 全量按钮审计）**：`FlowNode.jsx` 中带 `nodrag nopan` 的只有文本区（:120）与 output 块（:177/:242/:249），而 **5 个运行按钮所在的 `.node-actions`（:133、:146）完全没有该 class** → mousedown 阶段被 ReactFlow 拖拽/选择吃掉首次点击。修法：给 `.node-actions`（或每个按钮）加 `nodrag nopan`（与既有两处一致） | 2 | **计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）** | — | **用户走查 2026-09-20（UTC+8）**：Sprint-16 走查新增问题①；**2026-09-21** 用户要求"影响范围评估下再交给我看看"→ 评估已出；同日拍板 **Sprint-17 插入**、**接受"不能从按钮行拖动节点"**、**要求新检查先在未修复代码上跑出 FAIL（反向对照，用户称"倒过来试试"）** | **影响评估（2026-09-21）**：见 [`2026-09-21-fac13-14-impact.MD`](2026-09-21-fac13-14-impact.MD)——最小修复面=2 行 class；受影响检查 `gui_check_s5/s7` 用程序化点击**不会因此变红**；⚠ 关键发现：**现有 GUI 检查全用 `.click()`，结构上无法触发本 bug** → 修复必须同时新增**真实鼠标 down/up 序列**检查 + 反向对照。关联：运行按钮无 `disabled`、`runSingleNode` 无 `running` 早退 → 按用户 2026-09-21 口径"**允许运行中点击**"，重复点击语义未定义 → 只记 `F-AC17`，不实现 |
| F-AC14 | `[Bug]` **复制按钮状态串台**：点"复制答案"后"复制 output"/"复制报错"同时显示"已复制 ✓"——根因：`FlowNode.jsx` 三个复制按钮共用同一个 `copied` state（:42，被 :187/:199/:224 消费）。**全量按钮审计结论（2026-09-20）**：同一文件内 `FunctionTraceNode.jsx` 的"复制报错"用的是**独立** `errCopied`（:27/:155）、翻译按钮有 `disabled={translating}`（:122）、`SchemaForm.jsx` 各控件有 `disabled={readonly}`（:180~:265）、App 工具栏/子画布按钮均有 `active`/计数/title 反馈——**只有 FlowNode 这三个按钮有问题**。修法：按按钮各自一个 state（照抄 `FunctionTraceNode` 的写法） | 2 | **计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）** | — | **用户走查 2026-09-20（UTC+8）**：Sprint-16 走查新增问题②（用户要求"检查所有按钮行为"→ 审计已完成）；**2026-09-21** 评估已出并拍板 Sprint-17 插入、新检查须带反向对照 | **影响评估（2026-09-21）**：见 [`2026-09-21-fac13-14-impact.MD`](2026-09-21-fac13-14-impact.MD)——修复面=三个独立 state + 三个 timer；受影响检查 `gui_check_s15_output_view.mjs`（只断言剪贴板内容）与 `gui_check_s15_error_copy.mjs`（19 断言）**必须复跑**；新增 `gui_check_fac14_copy_state.mjs` 断言"点 A 时 B/C 文案不变 + 1.5s 后各自复位" |
| F-AC15 | `[用户插入]` **运行参数显式配置面**：把目前只存在于 CLI/env/spec 的参数在**前端显式可见/可配置**。**现状清单（2026-09-20 审计）**——前端只暴露引擎配置（`/api/config_schema`，7 分组 23 字段）；以下**全部前端不可见**：① `PAPERQA_PROVIDER`（默认服务商）、`PAPERQA_PROVIDERS_JSON`（自定义注册覆盖）；② `PAPERQA_PROVIDER_INTERVAL_DAYS`（provider 刷新周期 14 天）；③ `PAPERQA_NIGHTLY_BUDGET_CNY`（套件预算 10）+ `PAPERQA_SCHEDULE_<TASK>_DAYS`（prices 7 / nightly-suite 7 / providers 14）；④ `PAPERQA_SCHEDULE_STATE`（状态文件路径）；⑤ `PAPERQA_LITELLM_CALLBACK_LIMIT`（回调上限 20，钳制 ≤30）；⑥ `PAPERQA_EMBED_RECOMMEND_LIVE`（embedding 联网实测开关）；⑦ 调研**深度阈值**（`agents/functions/tech-research.md` 可配置参数节 + `fanout.json` depth 路由，CLI `--depth` 仅供校验覆盖）；⑧ 一批纯 CLI 开关（`run_suite --tier/--scripts/--dry-run/--json`、`scheduled-tasks --list/--check-due/--force/--record-cost`、`fetch-prices --apply`、`register-scheduled-tasks.ps1`、`verify_archive --depth`） | 3 | **计划中（Sprint-17，用户 2026-09-21 拍板）** | Sprint-17 | **用户走查 2026-09-20（UTC+8）**：B-15 存疑；**2026-09-21** 用户要求"9 个 env + spec 阈值具体有哪些"→ 清单已出；同日拍板：**v1 范围按建议（A 研究设置可改 / B 成本与用量只读 / C 数据源与决策只读+可选动作 / D 保持 CLI）**，且 **Sprint-17 需准备不同 use-case 组合供用户人工体验测试** | **详细清单（2026-09-21）**：见 [`2026-09-21-config-surface-inventory.MD`](2026-09-21-config-surface-inventory.MD)——每个 env 的默认值/读取点/作用、spec 6 项阈值 + 三档档表、state 2 键、CLI 开关 6 组、**7 类硬编码常量（连 env 都没有）**、建议 v1 分区 A/B/C/D |
| F-AC16 | `[用户插入]` **checkpoint 可见性与可复现**：前端展示命中的 checkpoint 明细（`checkpoint_key`/`manifest`/逐篇状态），支持按路径定位并用既有 checkpoint 复现——目的：pro 用户成本感知 + 单篇复现 + 幻觉核查 | 3 | **v1 ✅ 完成（2026-09-21）**；剩余增量待排期 | Sprint-16（走查追问 v1） | **用户走查 2026-09-20（UTC+8）**：CK-1 存疑；**2026-09-21** 要求"第一版实现达到 Sprint-17 可做原型验证的可靠程度" | **v1 证据**：`app/checkpoint_index.py`（只读，逐篇 `payload_path/payload_exists/payload_bytes`，坏件 fail-soft）+ `GET /api/checkpoints`（第 12 条路由）+ 前端 `CheckpointPanel.jsx`（工具按钮 → 命名空间 → 展开逐篇载荷路径可复制）；回归 `verify_checkpoint_index.py` **29 断言**（含路径穿越防护）+ `gui_check_fac16_checkpoint.mjs` **10 断言**（真实 15 命名空间、零成本）。**Sprint-17 原型候选（用户 2026-09-21：暂不动，待真实用户数据）**：① 一键"用该 checkpoint 重放"；② 按文献粒度成本展示 |

## 2. 维护卡

| 卡号 | 主题 | 规模(点) | 状态 | 所属 Sprint | 来源/备注 | 依据 |
|---|---|---|---|---|
| M1 | 索引一致性增强：Tantivy 段损坏探测升级（files.zip + meta.json + tantivy open 三重探针） | 3 | ✅ 完成 | Sprint-7 | `verify/verify_index_health.py`（合成六形态 + 真实构建自愈） |
| M2 | `prune_litellm_callbacks` 上限配置化（env `PAPERQA_LITELLM_CALLBACK_LIMIT`） | 1 | ✅ 完成 | Sprint-7 | `verify_prune_callbacks.py` 覆盖默认/覆盖/非法回落 |
| M3 | staging 清理 UI/自动清理；DOI 源真实 `UNPAYWALL_EMAIL` 实测 | 3 | 候选（用户指示未处理） | — | **Sprint-7 保持未完成**：staging 清理 UI + 真实邮箱实测留待后续 |
| M4 | 多节点并发计时显示；`runStartTimesRef` 清理 | 1 | ✅ 完成 | Sprint-7 | App.jsx subcanvas 计时聚合 + 结束清理；npm build 通过 |
| M5 | `verify_provider_switch` 对 openrouter/自定义连通实测；gui 依赖显式化 | 2 | ✅ 完成 | Sprint-7 | 占位 key 端点级拒绝断言（路由实证）；**真实 openrouter key 实测=用户资源门控**；README 前提显式化 |
| M6 | 文档/知识管理例行勘误（随三查进行） | 1 | 持续 | Sprint-7 | 本轮勘误：verify/README 表格列数错位、README/1-WORKFLOW 清单补全、4-ALGORITHM 行号锚点漂移等。⚠️ **同类问题持续复发**：doc-audit 026（4-ALGORITHM §9.2 DSL 描述旧控件）、Sprint-15 日期整体漂移、Sprint-16 内**修了三轮**（`6ecee2a` / Round-5 `bdc669b` / `2e1d20f`+`4e17ddd`）→ 已按用户 2026-09-21 要求立卡 **`TG-12`（testing-governance）文档内容漂移复盘 + 派生事实机制**；**建议复盘时决定 M6 并入 TG-12 或保留为执行项**（"随三查勘误"是人工兜底，不是机制） |
| M7 | 默认值漂移收敛：chunk/temperature 等默认值在 config_schema/App.jsx/provider_config/engine 重复 4 处（唯一真源原则） | 3 | 计划中（并入 F2 阶段 A = Sprint-11 US-11.2） | Sprint-7 全量 review | 与 F2（SSOT 驱动前端）同源，已并入 F2 |
| M8 | remote_resolver SSRF DNS rebinding TOCTOU 强化（解析后 IP 复检） | 2 | 候选 | Sprint-7 全量 review | 理论性；现状已有逐跳重定向复检 + 内网段拒绝 |
| M9 | 价表填充改自动化：按 provider 官网**固定 URL 抓取单价** + `prices.json` 更新 + 定时刷新机制——原 agents-infra A-M1 迁入 | 1 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 阶段 1 预研 / 用户 2026-08-31 | 用户已验证官网详情页+文档可固定 URL 直接访问抓取；填后看板成本口径完整 |
| M10 | fetch-spec 成功路径测试（sha256 命中/失配）+ 账本并发锁——原 agents-infra A-M4 迁入 | 2 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | Sprint-8 二查 nit | |
| M11 | 三查执行器 agent 固化（fan-out 自动派发 + 账本登记 + 分诊）——原 agents-infra A-PM1 迁入（备选） | 3 | 候选（备选） | 用户 2026-08-30 | fanout.json 已为可调配置，固化执行器属演进项 |
| M12 | Sprint 文档模板生成 agent（planning→燃尽→Retro 自动起草）——原 agents-infra A-PM2 迁入（备选） | 2 | 候选（备选） | 用户 2026-08-30 | |
| M13 | 调研结论→用例生成 agent 固化——原 agents-infra A-PM3 迁入（备选） | 2 | 候选（备选） | 用户 2026-08-30 | |
| M14 | 新 agent 上线评审 agent——原 agents-infra A-PM4 迁入（备选） | 2 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-30（+2026-08-31 底座批次） | 与 `_template-agent.md` 模板联动 |
| M15 | 领域治理壳落地：product/marketing 笔记目录 + 追溯索引登记 + fanout 路由预留（完整 spec 等对应领域讨论启动时再填） | 1 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | 用户 2026-08-31（底座批次） | 依据 `pre-research/2026-08-31-domain-governance.MD` §3/§6 |
| M16 | **调研工作流深化（知识沉淀）**：① 三级深度响应（工程级/领域专家级/研究学者级，场景自适应+用户可覆盖；工程级=主代理直接执行）；② 决策证据落档（context.md + evidence/ 快照，唯一真相）；③ 段落级溯源 + 思考过程附件（reasoning.md + 证据索引表，支持引经据典讨论） | 6 | ✅ 完成（Sprint-16：tech-research v2.0 + fanout v5 depth 路由 + `verify_archive.py` 门禁 + 首跑演示 provider 官网调研 28/28 PASS；2026-09-20 走查修复交叉引用双向校验） | Sprint-16 | 用户 2026-09-07 | 设计草案 `pre-research/tech/2026-09-07-research-workflow.MD`；阈值可配置（spec 可配置参数节/fanout 可调） |
| M17 | ~~思维模型管理~~ → **迁出（2026-09-07 用户拍板）**：成立独立阶段 `phases/mental-models/`（MM-1~MM-5，9 点），M17 内容并入 | — | 迁出 | 用户 2026-09-07 | 预研基线 `pre-research/tech/2026-09-07-mental-models.MD` |
| M18 | `[走查]` **报告时效与依据变更治理**：provider 模型信息/证据源更新后，旧调研报告与其证据快照如何标记"依据已变/被取代" | 2 | **v1 ✅ 完成（2026-09-21）**；剩余增量待排期 | Sprint-16（走查追问 v1） | **用户走查 2026-09-20（UTC+8）**：M16-5 存疑；**2026-09-21** 要求 v1 可靠到可做 Sprint-17 原型验证 | **v1 证据**：`scripts/report-freshness.py`（三条判定：provider 在归档之后刷新过 / §7 表格行点名证据缺失 / 证据晚于报告被改动；容差 3600s 可配；`--check` 有 stale 退出 1；只分析调研归档；**无时区信息按 UTC+8**）+ `verify_freshness.py` **17 断言**；真实数据 **3 fresh / 2 stale**（run-047 与首轮 provider 刷新已被 09-20 刷新取代）。**Sprint-17 原型候选（用户 2026-09-21：暂不动，待真实用户数据）**：① 逐结论溯源（结论↔evidence↔provider 现值）；② 前端 stale 徽标；③ `--check` 接入夜间套件 |
| F-AC17 | `[用户插入]` **运行中重复点击的行为定义（仅记录，不实现）**：用户 2026-09-21 口径——"**允许用户在运行中点击**"；**重复点击行为未定义**（当前代码无 `disabled`、`runSingleNode` 无 `running` 早退）。是否需要定义"忽略/排队/并行/取消重跑"等语义，**待更多真实用户数据观察后再定**；卡内保留候选语义清单与判据草案，**不纳入任何 Sprint 实现范围** | 2 | 候选（**仅记录，待用户数据**） | — | **用户插入 2026-09-21（UTC+8）** | 关联 `F-AC13`（同一批运行按钮）、`TG-6`（人机交互验收面） |

### 2.1 与 hold 状态的关系

- R-C（C+E3 v1）仍 hold；**若用户先做 F2/F3/F1 后续，E3 v1 的可视化验收闸门（用户 review）不变**。
- R-E/R-D/R-E3 的 hold 不阻塞功能卡 F 系列：F3 即 R-C 的解冻前置步骤；R-E 依赖的引擎适配层已就绪、R-D 依赖会话外置化、R-E3 依赖 R-C 验收。
- 插队/新 Sprint 的启动按 `1-WORKFLOW.MD` §4.4 判定；新卡完成后在 `roadmap.MD` §2 实际实录登记。

## 3. 已完成归档（示例与速查）

| 卡号 | 主题 | 完成 Sprint |
|---|---|---|
| R-A | 配置 SSOT + 策展 schema（原规划 Sprint-2 部分） | Sprint-2 |
| R-B | 数据源抽象（原规划 Sprint-3） | Sprint-3 |
| F-EXT1 | 体验修复 + provider 扩展（插队） | Sprint-4 |
| F-EXT2 | 实战问题修复（插队） | Sprint-5 |
