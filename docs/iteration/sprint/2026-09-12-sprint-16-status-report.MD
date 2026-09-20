# Sprint-16 收尾状态汇总报告（供 HOLD 复核）

> 生成时间：**2026-09-21（UTC+8）**｜性质：**只读汇总**（不改变任何交付内容）
> 关联文档：Sprint 正文 `2026-09-12-sprint-16.md`（§1–§10）｜验收指南 `2026-09-12-sprint-16-acceptance-guide.MD`（45 判定格）｜规则绕过证据台账 `../phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD`
> 分支状态：`windows` @ **`e07f535`**，工作树**干净**，**28 个未推送提交**；`origin/windows` @ `2155070`｜当前回归：离线套件 **SUITE PASSED（14 脚本）**、矩阵 **CHECK OK（45 脚本）**

---

## 1. 一句话结论

**19 点全部交付、用户走查未通过 0 项、回归全绿**；但 Sprint-16 **不能关闭**——三查跑完（09-12）之后又落地 **20 个提交**，使原三查结论**实质失效**，而后续 5 轮复核的 scope 全部是自选范围（不构成二查覆盖）。关闭前置 = **重跑三查**，然后才谈 PR。

---

## 2. 交付与证据（四卡 = 19 点，全部 DONE）

| 卡 | 点 | 终态证据 |
|---|---|---|
| **M16** 调研工作流 v2.0 | 6 | spec v2.0 + `fanout.json` v5 depth 路由 + `verify_archive.py`：真实归档 **28/28 PASS**、`--selftest` **8 例 PASS**（含防误报/防漏报/防假红）；run-047 复算 22/22 |
| **F-AC10** 文献级 checkpoint | 4 | `verify_checkpoint.py` **33 断言**：首跑 `embedded=2` → 重跑 `reused=2/embedded=0`（零嵌入成本）+ 四重边界（文件变更/载荷截断/模型不匹配/同内容去重）；**实测 ¥0.016965**（12 调用 / 4,473 tokens） |
| **TG-5** 分层 runner + 定时底座 | 3 | `verify_runner.py` **42 断言**；三档 offline/gui/network；三态预算闸门（超限拒跑=3 / 成本 unknown 拒放行=4 / 自动回填解除）+ `register-scheduled-tasks.ps1` |
| **F-AC8** provider 一文件 + 定时调研 | 6 | `verify_providers.py` **33 断言**；真实官网调研 3 家成功、openai 403 按 fail-closed 保留旧文件；二轮刷新归档 **28/28**；`openai/qwen3.5-omni-plus` 实机验证（`verify_e2e_dashscope.py` 六步全链 PASS，**实测 ¥1.013377**） |

**燃尽**：Planning 19 → M16 13 → F-AC10 9 → TG-5 6 → F-AC8 **0**（§4）。

---

## 3. 当前回归读数（2026-09-21 实跑，非引用）

| 项 | 读数 |
|---|---|
| 离线套件 `run_suite.py --tier offline` | **SUITE PASSED（14 脚本）**，`suite_exit=0` |
| 覆盖矩阵 `verify_matrix.py check` | **CHECK OK：45 脚本与 TEST-MATRIX.MD 一致**（offline 14 / gui 21 / network 10） |
| 关键脚本断言数 | runner **42**、agentops **42**、providers **33**、checkpoint 33（network）、config_schema 114、usage **27**、checkpoint_index **29**、freshness **22**、ledger_rounds **13**、archive 28 + selftest 8 |
| 前端构建 | 334.31 KB（2026-09-20 终态） |

---

## 4. DoD（9 项：8 项已勾，唯一未勾 = PR）

已勾：① 每卡验收证据；② 结论来自可复现证据；③ 权衡/理由/局限；④ 未破坏既有功能（全量回归 + smoke + 矩阵）；⑤ 三查完成且发现项闭环（**⚠️ 见 §6：该勾选的时效性正是本次 HOLD 的对象**）；⑥ 用户走查完成（09-20，未通过 0）；⑦ 走查期新增改动经独立复核（4 轮）；⑧ 付费项实测留证。

未勾：**⑨ windows 已 PR 同步 main + main CI 绿** → **HOLD**（用户 2026-09-21 决定：后续改动会新增测试项/代码，须先重跑三查）。

---

## 5. 复核与账本轨迹

- 关闭三查（09-12 23:49:04→23:57:06 UTC+8）：`run-048` 〇查 / `run-049` 一查 / `run-050`+`run-051` 二查（windows+main）/ `run-052` lessons——五条 `task_id` 均为 `Sprint-16 close`。
- 走查期独立复核：`run-2026-09-20-code-review-053`，**5 轮**（round-1 2 major/5 minor/3 nit 全修；round-2 抓出我引入的 major#3；round-3 抓出 junction 挂死 major#4；round-4 审 TG-7 + Retro③；round-5 审 F-AC16/M18 v1 + est 系数，3 major 全闭环）。
- 账本可观测性已修（TG-10）：run-053 由"53 秒 / 12800 字符"更正为 **`rounds=5 / dur=241.3m / int=2`**（含 2 次中断留痕）。

---

## 6. 事故与处置（诚实清单）

| # | 事件 | 处置 |
|---|---|---|
| 1 | **M16 归档门禁长期假绿灯**（交叉引用只有单向；"删掉被引用证据"仍 PASS） | 改**双向**交叉引用 + 判定限定证据索引表区间 + 大小写不敏感；`selftest` 2→8 例；原漏检变体由 PASS 转 **FAILED** |
| 2 | **预算闸门 fail-open**（状态文件带 BOM/损坏 → 静默重置 → 连带真跑一次联网套件，估算损失 ≈**¥1.0**） | TG-7 当日闭环：`utf-8-sig` 容忍 BOM、解析失败 **fail-closed 退出 2** + `.corrupt` 副本；`verify_runner` ⑩a/⑩b/⑩c 回归 |
| 3 | 走查环境事故：自举后端被作业包装器带走 + 套件静默复用用户 dev 后端（8787） | 立卡 **TG-8**（Sprint-17）：端口占用即 fail-fast、只回收自己拉起的进程、统一注入离线开关 |
| 4 | 费用误算口径：回调异步落地 → 空账被当 `0.0` → 闸门误判 measured | 空账 = `None` + `no_data`；`settle()` 有界等待；suite 只认 `calls>0` |
| 5 | **`--est-factor nan` 穿透预算闸门**（NaN 比较恒 False） | `math.isfinite` 一并挡 `nan/inf`，预算入口同样加固；`verify_runner` ⑬a–f 6 种负例 |
| 6 | M18 报告时效：§7 写成项目符号时"点名证据缺失"完全静默（假阴性） | 无表格行时退化判整段 §7 + 回归 ⑨c |
| 7 | Vite watcher `EBUSY` 崩服两次；经典 JSX 运行时缺 `import React` | `vite.config.mjs` `server.watch.ignored`；组件补 `import React`；教训入 1.60 |
| 8 | **规则绕过事件**（自选窄范围复核绕过 §4.2 / `code-review.md:34`） | 立卡 **TG-11** + 证据台账；方案 M1~M4 保留、**Sprint-16 期间不做代码改动**（用户 2026-09-21 明确） |
| 9 | 越界先例：09-12 提前建 PR #50 | 用户"没验收前不要提PR"→ PR 关闭、分支删除；规则加固至 §3.4（**该规则同样没有执行点**，属 TG-11 复盘输入） |

---

## 7. 成本账（本轮真实花费）

| 项 | 金额 | 口径 |
|---|---|---|
| `N-1 verify_checkpoint.py` | **¥0.016965** | 实测（12 调用 / 4,473 tokens） |
| `N-2 verify_e2e_dashscope.py` | **¥1.013377** | 实测（40 调用 / 125,670 tokens） |
| BOM 事故误跑（事件 #2） | ≈**¥1.0** | 估算（三态闸门旧值） |
| 走查期子代理复核（run-053 5 轮） | ≈¥0.03（首轮记账值） | 估算（历史轮次未逐轮采集 token） |
| **累计** | **≈¥2.06** | 明细见验收指南 §13.6 |

> 估算偏差已校准：`N-1` ¥0.05→**0.02**、`N-2` ¥0.5→**1.1**（`est_cost_cny` 终态）；安全系数 `--est-factor` 默认 **1.3** 且可配置（CLI > env > 默认）。

---

## 8. 未解决待办（HOLD 复核清单）

### ① 阻塞关闭（唯一硬阻塞，无需决策）
**三查重跑**：〇查 impact-assessment → 一查 doc-audit → 二查 code-review（**windows + main 两个 run**）→ lessons-learned。**输入必须包含**：Round-5 的 3 个 major；**20 个未覆盖提交**清单（`895e811`→`bdc669b`）；"R4 的 4 条发现 = 作者已修、复核未复验"标注；变更集新增 1 条用户可见路由（11→12）+ 1 个面板 + 3 个新验证脚本（B 口径 10 条路由需复核）；矩阵 re-derive；两条未回填教训（NaN 穿透数值闸门、§7 行形态假阴性）。

### ② 待你拍板
| 项 | 状态 | 备注 |
|---|---|---|
| `config_schema` 的 provider **hint 文案陈旧** | ⚠️ **仍未决策**（全仓无决策记录） | 文案级；改文本会扩大三查范围 → 建议排在重跑之后或并入 S17 |
| **TG-10 ③** 看板 UI 展示 `rounds/dur/int` | 未决策（CLI v1 已完成） | 属代码改动，同样受"重跑前冻结代码"约束 |
| **F-AC8 遗留**：二轮研究 `openrouter model = needs_review` | 现值保留、候选未采纳 | 需你确认是否采纳；`openai` 403 属 fail-closed 预期 |
| **其余 network 脚本的 `est_cost_cny` 校准** | 未校准（10 个 network 脚本中仅 2 个已按实测校准） | 未校准者沿用旧估值（如 `verify_e2e.py` ¥0.3、`verify_e2e_openai.py` ¥1、`verify_remote_e2e.py` ¥0.4），可能误拒/误放；建议随夜间套件首跑后按实测批量校准 |
| **TG-11 D3/D4** | 未答 | 三查锚点是否入 §6 DoD 必填；§9 分区是否只对新文档生效（复盘时定稿） |
| **验收指南 45 个判定格仍未回勾** | 走查结论已记录在指南 §11 / Sprint §10，但格子是空的 | 可选：由我按已记录结论回勾，或保留为你的自用清单 |

### ③ 已排 / 待复盘（Sprint-17 及以后，约 16 点）
`F-AC13`（运行按钮 `nodrag`，2，插队卡，须带**反向对照**新检查）、`F-AC14`（复制状态串台，2，插队卡）、`F-AC15`（配置面 A/B/C/D，3，需备 use-case 组合供人工体验）、`TG-8`（自举端口自检 + 离线开关，2）、`TG-9`（产物目录约定，1）、`TG-11`（**规则绕过复盘 + 闸门**，3；复盘后另开）、`TG-12`（**文档内容漂移复盘 + 派生事实机制**，3；用户 2026-09-21 插卡，含 4 波漂移证据与 N1~N6 机制候选）。

> 两张**复盘卡**（`TG-11` / `TG-12`）当前均为"证据/台账已固化、复盘待做、**代码零改动**"；复盘结论可能推翻各自的初稿对策（M1~M4 / N1~N6）。

### ④ 仅记录 / 待真实用户数据（不做）
`F-AC16` 增量（一键重放、按文献粒度成本）、`M18` 增量（逐结论溯源、前端 stale 徽标、接入夜间套件）、`F-AC17`（运行中重复点击语义）、`MM-1`~`MM-6`（思维模型阶段，已 defer）。

---

## 9. 顺序约束与建议

1. **先修文档口径**（本轮已做，见 §10）——让接下来的一查审的是修正后的状态。
2. **重跑前冻结代码**：任何新代码/文案改动都会再次扩大三查范围，甚至让重跑结果立即失效（本次事故的重演机制）。→ 因此 TG-10 ③ / hint 文案 / F-AC13-15 都应排在重跑之后。
3. 三查重跑 → 结论记录 §9 → **你确认** → push → `sync/sprint-16` PR（排除 `docs/iteration/`）→ CI 绿 → 合并 → 关闭。

---

## 10. 本轮修正的陈旧口径（5 类，均已完成）

| # | 位置 | 修正前 → 修正后 |
|---|---|---|
| 1 | 验收指南 §5 第 3 条 | `CHECK OK: 44 脚本` → **45 脚本**（差值为 TG-10 的 `verify_ledger_rounds.py`） |
| 2 | 验收指南 §5 第 7 条 + §5.1 注 | `SUITE PASSED (11 scripts)` / "现行 11 脚本" → **14 脚本**（并列出新增 4 个脚本名） |
| 3 | 验收指南 §5 第 2/8 条 + §13.6 + TG-7 段 | runner `26 断言` → **42**；usage `21 断言` → **27**（历史读数加"当日 N"标注） |
| 4 | 验收指南 TG-1 判定格 + §9 `N-1`/`N-2` 估算 | "13 个 offline 脚本 / 44 脚本" → **14 / 45**；`N-1` ¥0.05→**0.02**、`N-2` ¥0.5→**1.1**（并注明原估与实测） |
| 5 | 验收指南 §10 已知局限 1/3 条 + backlog 卡状态 | 第 1 条"成本未测量"→**已解决（实测值）**；第 3 条时区口径→**已被二轮刷新覆盖（`+08:00`）**；TG-5 卡"计划中"→**✅ 完成**；F-AC8 卡"待确认"→**决策终态 + 遗留项**；Sprint §3/§7 TG-5 行"10/11 脚本、26 断言"→**14 脚本、42 断言**；F-AC8 行"矩阵 41"→**45**；M16 行 `selftest 4 例`→**8 例** |

---

## 11. 附录：关键索引

- **提交流**：`windows` @ `2c4e173`（收尾文档修正）｜未推送 **24** 提交｜`origin/windows` @ `2155070`
- **三查记录**：`agents/runs/run-2026-09-12-{impact-assessment-048,doc-audit-049,code-review-050,code-review-051,lessons-learned-052}/`
- **走查期复核**：`agents/runs/run-2026-09-20-code-review-053/code-review.report.md`（账本 `rounds=5`）
- **归档门禁证据**：`agents/runs/run-2026-09-12-provider-refresh-001/`、`run-2026-09-20-provider-refresh-001/`（均 28/28）
- **预跑日志**：`verify/acceptance-sprint16-2026-09-20.log`（本地）
- **规则绕过证据台账**：`docs/iteration/phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD`
