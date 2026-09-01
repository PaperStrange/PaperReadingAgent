# 预研笔记：e2e 测试与功能演进的同步治理（testing-governance）

> 状态：**初稿方案待确认**（2026-08-31）。本笔记是后续开卡时规划管线（tech-research）的强制上下文输入。
> 归属：`docs/iteration/pre-research/tech/`（仅 windows 分支维护；技术领域目录）。注入规则见 `1-WORKFLOW.MD` §4.4「预研上下文传递」。

## 1. 背景与用户关切

- 用户建议（2026-08-31）：后续新增功能时，e2e 测试应当同步更新——例如新增远程数据源后，该 case 应纳入测试；调研相关技术（如 TDD）和最佳实践，一起探讨。
- 事实核查：远程数据源 case **已覆盖**（`verify/verify_remote_e2e.py` + `verify/gui_check_remote.mjs`，Sprint-3）。真实问题是「功能必须带测试」靠 sprint DoD 自觉驱动，**无成文规则、无覆盖矩阵、无统一回归入口**。

## 2. 现状盘点（2026-08-31 实测）

| 层级 | 脚本 | 运行方式 |
|---|---|---|
| 离线确定性（CI 每 PR 门禁） | verify_smoke / verify_prune_callbacks / verify_agentops / verify_config_schema（114 断言）/ verify_index_health | 快、确定性、已自动化 |
| 联网全链路（LLM） | verify_e2e（deepseek）/ verify_e2e_openai / verify_e2e_dashscope / verify_remote_e2e / verify_agent / verify_embed_load / verify_provider_switch / eval_retrieve | 手动按需、单脚本逐个跑 |
| GUI 证据（Playwright） | gui_check*.mjs（s4/s5/s7/remote/dashboard×5/config_schema） | 手动、截图留证 |

三个缺口：① 无 feature↔test **覆盖矩阵**；② 联网套件**无 tier 元数据/统一 runner/定时回归**（CI 离线清单硬编码）；③ 无"新功能必须同步更新测试"的**成文规则**。

**漂移实锤（provider e2e 三脚本，2026-08-31 grep 实测）**：

| 脚本 | provider | vision_model | 风险 |
|---|---|---|---|
| verify_e2e.py（deepseek 原版） | ❌ 未传 | ❌ 未传 | 纯靠 .env 默认值，默认一变即静默失效 |
| verify_e2e_openai.py | ✅ | ❌ | Phase-1 vision 回落默认服务商（1.46 bug 类），被 openai billing 掩盖 |
| verify_e2e_dashscope.py | ✅ | ✅ | 唯一显式完整 |

三兄弟脚本、三种显式程度、零共享基座——即"测试只增不治"的实际后果。

## 3. 预研结论（方案菜单 + 推荐）

- **P1 成文规则**（≈0 成本）：DoD 增补"新增/修改用户可见功能（节点/路由/数据源/provider/表单字段）必须同 PR 交付对应 verify case + 覆盖矩阵登记"；三查清单加核查项。
- **P2 覆盖矩阵 SSOT**（对齐 1.39 同源）：脚本头部声明元数据（feature/route、tier=offline|network、provider、估时/估成本），derive/check 脚本生成并校验矩阵文档；CI 离线断言"矩阵与脚本一致"。
- **P3 分层 runner + 定时回归**：tier 标签 → 一键跑离线/联网子集；cron 每周夜间全量联网套件（fail-closed）。**需用户拍板 API 成本预算**（deepseek+dashscope 每轮约 ¥2~4 量级，精确估算待做；openai 看余额）。
- **P4 ATDD case-first**：新功能卡在规划期先写验收 case（步骤+断言），实现后跑绿留证据——适合 LLM 非确定性管线的 TDD 形态。
- **明确不做**：golden 匹配答案、每 PR 跑联网 e2e、GUI 截图进 CI 门禁。
- **推荐**：P1+P2+P4 打包"测试治理"工作项，P3 先出成本估算再单独决策。

## 4. 外部最佳实践来源

- 测试金字塔 / 少而精 e2e：[eficode](https://www.eficode.com/blog/improving-test-coverage-and-performance-with-test-pyramid)、[Feature-Sliced](https://feature-sliced.design/ja/blog/frontend-testing-strategy)、[Vendure](https://vendure.io/blog/what-s-up-with-e2e-tests)
- DoD 内置测试义务：[Miroverse DoD 模板](https://miro.com/templates/definition-of-done/)、[AWS 示例 ADR-008](https://aws-samples.github.io/sample-autonomous-cloud-coding-agents/decisions/adr-008-definition-of-done/)
- 联网/慢套件定时回归 + fail-closed：[herdbook #29](https://github.com/taco/herdbook/issues/29)、[QwenPaw 夜间 e2e 分片](https://github.com/agentscope-ai/QwenPaw/pull/7326)、[tiered e2e 分层](https://raw.githubusercontent.com/redwoodjs/sdk/2a545c32e016bd41b9003c525dac7448c4f7f239/.notes/justin/worklogs/2025-09-25-tiered-e2e-testing.md)
- LLM 输出用语义/结构断言（非 golden）：[阿里云](https://developer.aliyun.com/article/1755162)、[genai-rs #214](https://github.com/evansenter/genai-rs/commit/5f8bd4bca0b7ad9c1e4b24129d691a78847d9ad3)
- TDD 适用于确定性逻辑；ATDD 适用于非确定性输出（本笔记判断，结合上述来源）

## 5. 用户决策记录（chronological）

| 时间 | 决策 |
|---|---|
| 2026-08-31 | 采纳范围：**继续探讨，暂不开卡**；时机：继续讨论 |
| 2026-08-31 | **预研结果（含用户选择/确认）必须作为进入规划管线调研时的上下文**——避免方案路线决策在后续流程中重复出现/前后矛盾 → 落地为 `1-WORKFLOW.MD` §4.4「预研上下文传递」+ tech-research spec v1.1.0 + fanout.json v3 |
| 2026-08-31 | **D1 范围 = A（W1+W2+W3，不含 cron）** |
| 2026-08-31 | **D2 provider e2e 去漂移本次不做** → 另立候选卡 TG-4 |
| 2026-08-31 | **D3（W4 未来参数预决）**：每周一次、单轮预算上限 ¥10；**上限必须可配置（config/env 驱动，不得写死文件）** → 候选卡 TG-5 设计约束 |
| 2026-08-31 | **D4 时点 = 现在开卡（候选态）** → 卡入 `phases/testing-governance/backlog.MD`（TG-1~TG-5），ROADMAP Next 档登记 |

## 6. 注入指引（供 planning_pipeline / tech-research）

- 命中主题关键词：测试治理 / e2e 同步 / verify 覆盖矩阵 / 测试分层 runner / ATDD / 测试与功能演进同步
- 开卡时卡片必须链接本笔记；tech-research 以本笔记为基线：不重复调研已决路线（P1–P4 菜单与推荐、明确不做项），不静默改向；发现矛盾 → 以"翻案建议"交用户裁决。
- 待续事项：P3 的每跑成本精确估算；P1–P4 的验收标准细化；provider e2e 三脚本去漂移（参数化共享基座）可并入测试治理工作项。

## 7. 初稿方案（2026-08-31 已确认，开卡候选）

按 `1-WORKFLOW.MD` §4.4 判定：涉及 DoD/三查规则变更 + 跨脚本治理 + CI 流程变化 → **新 Sprint**。

| 工作项 | 内容（P 对应 §3 方案菜单） | 规模 | 验收标准草案 |
|---|---|---|---|
| W1 | P1 成文规则：DoD 增补"用户可见功能必须同 PR 交付 verify case + 矩阵登记"；三查核查项 | 1 点 | ① 规则文本入 §4.2/§4.4；② 反例演练：构造缺 case 的改动被三查拦下并留证据 |
| W2 | P2 覆盖矩阵 SSOT：脚本头部元数据声明 + `verify_matrix.py` derive/check + `verify/TEST-MATRIX.MD` + CI 离线断言 + 全量脚本登记（provider e2e 去漂移已按 D2 拆出，见 TG-4） | 4 点 | ① 矩阵生成且 check 模式 CI 断言"矩阵==脚本元数据"；② 全部 verify 脚本登记（tier/provider/估时） |
| W3 | P4 ATDD case-first：功能卡模板增"验收 case"节（实现前先写步骤+断言） | 1 点 | ① 下一张新功能卡含验收 case 且实现前写好；② 实现后跑绿留证据 |
| W4 | P3 分层 runner + 定时回归：tier 标签 + `run_suite` 一键离线/联网子集 + cron 夜间全量联网套件（fail-closed） | 3 点 | ① run_suite 离线/联网子集可用；② 首次夜间全量跑绿且预算内 |

合计 9 点 ≈ 1 个 sprint（含 20% 非计划缓冲）。

**决策结果（2026-08-31 已拍板，见 §5）**：D1=A（W1+W2+W3）；D2 去漂移单独立卡 TG-4；D3 预决 W4 参数（每周一次、¥10/轮、上限必须可配置）入 TG-5 设计约束；D4 现在开卡候选态 → `phases/testing-governance/backlog.MD`（TG-1~TG-5）。
