# 阶段 backlog：refactor-analysis（卡独立管理）

> 归属：`docs/iteration/phases/refactor-analysis/`。卡状态流转：`候选 → 计划中 → 完成 / 取消`；
> 进入 Sprint 后由 Sprint 文档引用卡号（如 `F1`），本表仅维护卡级信息。
> 启动判定引用 `1-WORKFLOW.MD` §4.4（Sprint/Bug/维护边界）。
> **卡片来源与时间口径（2026-09-20 用户要求）**：来源带类型前缀 `[规划]`/`[用户插入]`/`[Bug]`/`[走查]`/`[三查]`/`[评审]`；时间字段一律用**网络时间 UTC+8**（`YYYY-MM-DD（UTC+8）`），不得用本机时区（本机 UTC+9）。细则见 `1-WORKFLOW.MD` §3。

## 1. 功能卡

> 卡正文自 2026-09-24（`TG-14` P4）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| R-C | C Agent 可观测闭环 + E3 v1 只读可视化（原规划 Sprint-4） | ⏸ hold | — | [cards/R-C.md](cards/R-C.md) |
| R-E | E1/E2 pip 注入 + 版本检查/更新/回滚（原规划 Sprint-5） | ⏸ hold | — | [cards/R-E.md](cards/R-E.md) |
| R-D | D 单机多 worker + 会话外置 + 网关分流（原规划 Sprint-6） | ⏸ hold | — | [cards/R-D.md](cards/R-D.md) |
| R-E3 | E3 可编辑工作流（原规划 Sprint-7+） | ⏸ hold | — | [cards/R-E3.md](cards/R-E3.md) |
| F1 | 检索体验与查询质量：多语检索 | ✅ 完成(v1) | Sprint-6 | [cards/F1.md](cards/F1.md) |
| F2 | 配置面板深化 + SSOT 驱动前端（/api/config_schema + 全字段交互 + 单一受控状态） | ✅ 完成（阶段 A=Sprint-11、B=Sprint-12、C=Sprint-13 全完成，转用户验收） | — | [cards/F2.md](cards/F2.md) |
| F3 | Agent 接入后端 + 事件时间线雏形 | 候选 | — | [cards/F3.md](cards/F3.md) |
| F4 | 本地评测基准（检索/证据/答案三环） | ✅ 起步 | Sprint-6 | [cards/F4.md](cards/F4.md) |
| F-AC1 | F2 验收①1.1：标题字号收敛 + 卡片内字体类型统一（token 化），排查全部卡片批量修 | ✅ 完成（走查 PASS） | Sprint-15 | [cards/F-AC1.md](cards/F-AC1.md) |
| F-AC2 | F2 验收①1.2：hints 限高滚动 + 影响上浮标题聚合（"LLM（6项，3项被改动）"改动数标红） | ✅ 完成（走查返工已闭环：无默认值字段计数 + 输入全非受控杜绝光标跳） | Sprint-15 | [cards/F-AC2.md](cards/F-AC2.md) |
| F-AC3 | F2 验收①1.3：新增 `local_dir` 字段（默认 data/pdf）+ 后端接线 + 数据源条件隐藏无关参数 | ✅ 完成（走查 PASS） | Sprint-15 | [cards/F-AC3.md](cards/F-AC3.md) |
| F-AC4 | F2 验收②：节点运行完成后自动收起全部展开项，仅留 output_snapshot | ✅ 完成（走查 PASS） | Sprint-15 | [cards/F-AC4.md](cards/F-AC4.md) |
| F-AC5 | F2 验收③：subcanvas 桌面分辨率响应式自适应（手机暂不考虑） | ✅ 完成（走查 PASS） | Sprint-15 | [cards/F-AC5.md](cards/F-AC5.md) |
| F-AC6 | F2 验收④：失败一键复制 + 任意状态框选复制已完成卡片 + 主画布报错摘要+可展开完整堆栈；**走查追加**：节点报 | ✅ 完成（走查五~八轮全闭环，用户复验通过） | Sprint-15 | [cards/F-AC6.md](cards/F-AC6.md) |
| F-AC7 | F2 验收⑤：执行状态信息仅展示在执行节点下（作用域修复）；**走查语义修正**：切换后展示**切换后节点**的状态行（ | ✅ 完成（走查返工已闭环） | Sprint-15 | [cards/F-AC7.md](cards/F-AC7.md) |
| F-AC8 | F2 验收⑥：provider_config 拆**一 provider 一文件** + tech-research 官 | ✅ 完成（Sprint-16：providers/*.json + 刷新脚本 + M16 归档 + 两周定时）。**决策终态**：dashscope model 由用户拍板 `openai/qwen3.5-omni-plus`（官网证据，已实测可用）；**遗留待用户决定**：二轮研究判定 `openrouter model = needs_review`（现值保留、候选未采纳）；`platform.openai.com` **403** → 按 fail-closed 保留旧文件 | Sprint-16 | [cards/F-AC8.md](cards/F-AC8.md) |
| F-AC9 | F2 验收⑦：subcanvas 手动切换节点 → 主画布联动定位（双向联动）；**走查返工**：主画布选中未生效 +  | ✅ 完成（走查返工已闭环：onInit 实例 + setCenter） | Sprint-15 | [cards/F-AC9.md](cards/F-AC9.md) |
| F-AC10 | F2 验收⑧：**文献级 embedding checkpoint**——每篇完成即落盘，失败续跑未完成文献；持续迭代主 | ✅ 完成（Sprint-16：逐篇原子落盘 + 零成本复用 + 四重边界，22 断言 PASS） | Sprint-16 | [cards/F-AC10.md](cards/F-AC10.md) |
| F-AC11 | 走查 N1（2026-09-10）：卡片 output 字段**完整查看**（展开/一键复制全文），answer 节点* | ✅ 完成（Sprint-15 收尾批，四轮定稿；tooltip 按用户要求移除） | Sprint-15 | [cards/F-AC11.md](cards/F-AC11.md) |
| F-AC12 | 走查 N2（2026-09-10）：fn 卡**论文截图清晰度**提升（runtime_trace 0.45 缩放 →  | ✅ 完成（Sprint-15 收尾批，预览 1.0 缩放 + 1.2MB 护栏，612×792 实证） | Sprint-15 | [cards/F-AC12.md](cards/F-AC12.md) |
| F-AC13 | 节点运行按钮**点击 1~2 次无响应**（第 3 次才生效）——**根因已定位（2026-09-20 全量按钮审计）* | **计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）** | Sprint-17（治理批 G1 搭车） | [cards/F-AC13.md](cards/F-AC13.md) |
| F-AC14 | **复制按钮状态串台**：点"复制答案"后"复制 output"/"复制报错"同时显示"已复制 ✓"——根因：`Flow | **计划中（Sprint-17 插队卡，用户 2026-09-21 拍板）** | Sprint-17（治理批 G1 搭车） | [cards/F-AC14.md](cards/F-AC14.md) |
| F-AC15 | **运行参数显式配置面**：把目前只存在于 CLI/env/spec 的参数在**前端显式可见/可配置**。**现状清单 | **计划中（Sprint-17，用户 2026-09-21 拍板）** | Sprint-17 | [cards/F-AC15.md](cards/F-AC15.md) |
| F-AC16 | **checkpoint 可见性与可复现**：前端展示命中的 checkpoint 明细（`checkpoint_key | **v1 ✅ 完成（2026-09-21）**；剩余增量待排期 | Sprint-16（走查追问 v1） | [cards/F-AC16.md](cards/F-AC16.md) |

## 2. 维护卡

> 卡正文自 2026-09-24（`TG-14` P4）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| M1 | 索引一致性增强：Tantivy 段损坏探测升级（files.zip + meta.json + tantivy open | ✅ 完成 | Sprint-7 | [cards/M1.md](cards/M1.md) |
| M2 | `prune_litellm_callbacks` 上限配置化（env `PAPERQA_LITELLM_CALLBAC | ✅ 完成 | Sprint-7 | [cards/M2.md](cards/M2.md) |
| M3 | staging 清理 UI/自动清理；DOI 源真实 `UNPAYWALL_EMAIL` 实测 | 候选（用户指示未处理） | — | [cards/M3.md](cards/M3.md) |
| M4 | 多节点并发计时显示；`runStartTimesRef` 清理 | ✅ 完成 | Sprint-7 | [cards/M4.md](cards/M4.md) |
| M5 | `verify_provider_switch` 对 openrouter/自定义连通实测；gui 依赖显式化 | ✅ 完成 | Sprint-7 | [cards/M5.md](cards/M5.md) |
| M6 | 文档/知识管理例行勘误（随三查进行） | 持续 | Sprint-7 | [cards/M6.md](cards/M6.md) |
| M7 | 默认值漂移收敛：chunk/temperature 等默认值在 config_schema/App.jsx/provid | 计划中（并入 F2 阶段 A = Sprint-11 US-11.2） | Sprint-7 全量 review | [cards/M7.md](cards/M7.md) |
| M8 | remote_resolver SSRF DNS rebinding TOCTOU 强化（解析后 IP 复检） | 候选 | Sprint-7 全量 review | [cards/M8.md](cards/M8.md) |
| M9 | 价表填充改自动化：按 provider 官网**固定 URL 抓取单价** + `prices.json` 更新 + 定 | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/M9.md](cards/M9.md) |
| M10 | fetch-spec 成功路径测试（sha256 命中/失配）+ 账本并发锁——原 agents-infra A-M4  | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/M10.md](cards/M10.md) |
| M11 | 三查执行器 agent 固化（fan-out 自动派发 + 账本登记 + 分诊）——原 agents-infra A-P | 候选（备选） | — | [cards/M11.md](cards/M11.md) |
| M12 | Sprint 文档模板生成 agent（planning→燃尽→Retro 自动起草）——原 agents-infra  | 候选（备选） | — | [cards/M12.md](cards/M12.md) |
| M13 | 调研结论→用例生成 agent 固化——原 agents-infra A-PM3 迁入（备选） | 候选（备选） | — | [cards/M13.md](cards/M13.md) |
| M14 | 新 agent 上线评审 agent——原 agents-infra A-PM4 迁入（备选） | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/M14.md](cards/M14.md) |
| M15 | 领域治理壳落地：product/marketing 笔记目录 + 追溯索引登记 + fanout 路由预留（完整 spe | ✅ 完成 | Sprint-14（2026-08-31，PR #48） | [cards/M15.md](cards/M15.md) |
| M16 | **调研工作流深化（知识沉淀）**：① 三级深度响应（工程级/领域专家级/研究学者级，场景自适应+用户可覆盖；工程级=主 | ✅ 完成（Sprint-16：tech-research v2.0 + fanout v5 depth 路由 + `verify_archive.py` 门禁 + 首跑演示 provider 官网调研 28/28 PASS；2026-09-20 走查修复交叉引用双向校验） | Sprint-16 | [cards/M16.md](cards/M16.md) |
| M17 | ~~思维模型管理~~ → **迁出（2026-09-07 用户拍板）**：成立独立阶段 `phases/mental-m | 迁出 | — | [cards/M17.md](cards/M17.md) |
| M18 | **报告时效与依据变更治理**：provider 模型信息/证据源更新后，旧调研报告与其证据快照如何标记"依据已变/被取 | **v1 ✅ 完成（2026-09-21）**；剩余增量待排期 | Sprint-16（走查追问 v1） | [cards/M18.md](cards/M18.md) |
| F-AC17 | **运行中重复点击的行为定义（仅记录，不实现）**：用户 2026-09-21 口径——"**允许用户在运行中点击**" | 候选（**仅记录，待用户数据**） | — | [cards/F-AC17.md](cards/F-AC17.md) |

### 2.1 与 hold 状态的关系

- R-C（C+E3 v1）仍 hold；**若用户先做 F2/F3/F1 后续，E3 v1 的可视化验收闸门（用户 review）不变**。
- R-E/R-D/R-E3 的 hold 不阻塞功能卡 F 系列：F3 即 R-C 的解冻前置步骤；R-E 依赖的引擎适配层已就绪、R-D 依赖会话外置化、R-E3 依赖 R-C 验收。
- 插队/新 Sprint 的启动按 `1-WORKFLOW.MD` §4.4 判定；新卡完成后在 `roadmap.MD` §2 实际实录登记。

## 3. 已完成归档（示例与速查）

> 本节源表只有 3 列（卡号｜主题｜完成 Sprint）：**无 状态/规模/来源 列**，迁移后这些字段以 `—` 标注（不臆造数据，守恒核对 ② 只认源格逐字节保留）；归档事实以本节标题为准。
> 卡正文自 2026-09-24（`TG-14` P4）起**独立成文**：见 `cards/<卡号>.md`；本表仅作**瘦索引**（卡号｜一句话｜状态｜Sprint｜文件），不再承载正文（根因/机制/长清单一律进卡文件）。判据：`verify/verify_card_index.py`。

| 卡号 | 一句话 | 状态 | Sprint | 文件 |
|---|---|---|---|---|
| R-A | 配置 SSOT + 策展 schema（原规划 Sprint-2 部分） | — | Sprint-2 | [cards/R-A.md](cards/R-A.md) |
| R-B | 数据源抽象（原规划 Sprint-3） | — | Sprint-3 | [cards/R-B.md](cards/R-B.md) |
| F-EXT1 | 体验修复 + provider 扩展（插队） | — | Sprint-4 | [cards/F-EXT1.md](cards/F-EXT1.md) |
| F-EXT2 | 实战问题修复（插队） | — | Sprint-5 | [cards/F-EXT2.md](cards/F-EXT2.md) |
