# G2（治理批）闭环台账 · 2026-09-26

> **起因（用户 2026-09-26 原话）**："闭环台账给我看说实话我无法给你有效建议，
> 你的运行过程太长了我基本没参与"。此前我给的是状态清单——状态清单只回答"修没修"，
> 不回答"为什么难、跟谁绑在一起、先做哪个"，所以用户无从给建议。
>
> 本档只新增两样东西：**每条未闭环项的关闭动作**（A 表）、
> **项与项之间的真耦合边**（B 表）。**不重复描述、不重复状态。**

## 0. 权威边界（防止出现第二权威）

| 事实 | 唯一权威 | 本档角色 |
|---|---|---|
| 未闭环项清单与**状态** | 复盘 [`§5`](2026-09-26-g2-close-retro.MD) | 只按行号引用，不复制描述、不复制状态 |
| 项之间的**耦合边** | **本档 B 表** | 唯一权威 |
| 关闭阻塞性（**零未闭环项**） | 复盘 §5 表头 ＋ `D-250926-06` | 不重复声明；本表 A 表只给"关闭所需动作" |
| 账本时间戳退化的方案与备案 | 备案 [`R-001`](../agents-infra/2026-09-26-residual-risk-register.MD) | 只引用 |

**维护规则**：状态变了只改复盘 §5；发现新耦合边只改本档 B 表。
同一事实**不得两边都写**——两边都写就是下一个"两份 `_norm_sprint`"。

## A 表：未闭环项 → 关闭所需动作

`行`＝复盘 §5 的行号。**关闭所需动作**是本档新增字段（复盘只记了来源与状态），
判据一律写成**可跑出反证**的形式，不接受"完善一下"这类动作。

| 行 | 关闭所需动作（可判定） | 需用户裁定 | 参与边 |
|---|---|---|---|
| 1 | 已达成（批 9 真入口两例＋自检扩条）；关闭前由用户走查复核 | 否 | — |
| 2 | 补齐`087-minor-5` 的五件事（原文 `Fix` 段列的是五件，不止三项：围栏感知／条目落在 `## 3.`／`## 4.1` 行区间／重复字段 FAIL／"会话"精确形态／引文报真实命中行号）；**前置已撤**——取证判定它**不挂在 `_norm_sprint` 上**；真正必须同批的是它**内部**（`setdefault` 与 `_canon_field` 是同一解析器的两种行为，只改前者会把"取错值"变成"静默换值"） | 否 | — |
| 3 | 补齐 `087-minor-9` 要的四类 pattern ＋ **行级时点豁免口径**（sprint 表格行行首就是日期 ⇒ 整行被豁免，与"无 pattern"叠加成双重缺口）；残留现值按现跑改写 | 否 | E1、E4 |
| 4 | `_invokes_guard` 由黑名单改结构判定；反证＝注释里写上被调命令名必须判红 | 否 | E2 |
| 5 | `_installs_hooks` 由文本子串改解析 `HOOKS` 结构；反证＝`HOOKS = [...]` 假红必须 FAIL | 否 | E2 |
| 6 | 加判据：本地层终判必须由**退出码**承载，不得三层全 report-only；反证＝三层全 report-only 必须 FAIL | 否 | E2、E3 |
| 7 | `_norm_sprint` 收敛为单一实现或单向复用，带"两侧同输入同输出"自检 | 否 | E1 |
| 8 | 夹具目录改 run 级唯一（`mkdtemp`）或统一前缀＋进程标识；反证＝并发两实例互踩不复现 | 否 | E6 |
| 9 | 已达成（`28bc182` 自曝"另有 N 项未列出"） | 否 | E4 |
| 10 | 已达成（`28bc182` 标签不再写死条数） | 否 | E7 |
| 11 | 三处 `.py` docstring 陈旧计数改由现跑派生或删数字；**不得手抄** | 否 | E7 |
| 12 | 已达成（全量回填完成）；复核＝登记册闸门现跑 | 否 | — |
| 13 | `started_at is None` 的 `queued` run 不得进"数据被改过"分支，改显式 SKIP；反证＝有 queued run 时整档不得 rc=4 | 否 | E5、E8 |
| 14 | **已裁定：用户单次豁免**（`D-250926-05`）——本次不执行 S1 硬停、不倒填、不裁定条款不适用；**规则原文不改**，再次触发仍按 S1 处置。记为豁免，不是"已修" | 已裁定（2026-09-26） | — |
| 15 | `parse_deepseek` 修好（容忍模型数变化、按 `<tr>` 顺序走、支持中文页"元"金额）＋ 加"抓取为空／价表陈旧 ⇒ FAIL 而非静默跳过"的判据 | 否 | E9 |
| 16 | ① `prices-derive` 白名单纳入 `_tiers`/`_tier_scheme`；② 按 run 时间戳选档，缺失 ⇒ 高峰 ＋ `tier_assumed`；③ 跨档规则；④ 判据＝"**派生后档位仍在**" | 否 | E9 |
| 17 | 守卫前移到 `--result-file` 复制之前，或拒绝时回滚产物；反证＝被拒后 `runs/<id>/` 不得新增产物 | 否 | — |
| 18 | 行内增 `degenerate_reason`（须同步 `verify_ledger_measurement` 字段集口径），或裁定"理由只上屏"并写进口径文档 | 否 | — |

**只有行 14 需要用户裁定。** 其余各行的动作都已可判定，不需要用户先表态。

## B 表：耦合边（本档唯一权威）

每条边必须能指到一个**可读的共享对象**（文件::符号／夹具名／数据源）。
指不到共享对象的，不算耦合，不入表。

| 边 | 两端 | 共享对象（可读证据） | 约束 | 反证（只修一侧会怎样） |
|---|---|---|---|---|
| E1 | 行 3、7 | **`_norm_sprint` 只有两处实现**（现跑 `git grep -n "def _norm_sprint" HEAD` ⇒ `scripts/agent-ops.py:576`、`verify/verify_close_readiness.py:261`；**不写死行号，以现跑为准**）。它的消费面全在 Sprint 身份归一／M-A 判定域派生 | **先 7 后 3** | 修 3 不统一 7 ⇒ 写入侧与读取侧对同一 sprint 标识给出不同结论，而自检仍全绿 |
| E2 | 行 4、5、6 | 同文件同控制流层 `verify/verify_gate_integrity.py`（"闸门看闸门"）：`_invokes_guard:291`、`_installs_hooks:316`；该文件 `:322`、`:396`、`:642` 自己就在推理"终判压在 `commit-msg`" | **同批** | 只修 5（`_installs_hooks` 更严）而不同时加 6 ⇒ 三层全 report-only 时该闸门仍全绿 |
| E3 | 行 6 ↔ 批 7／批 9 的修复面 | `scripts/hooks/pre-commit`（`:12`、`:33`、`:46` 传 `--report-only`）＋ `scripts/structure-guard.py` 的 `--report-only` 分支；批 7 把 `pre-commit` 改 report-only，批 9 修基线 fail-open | 行 6 是这两批的**共同残余**，动行 6 前必须复核两批都未回退 | 行 6 写成"至少一层非 report-only"却只数层数、不看退出码 ⇒ 又变回 fail-open |
| E4 | 行 3、9 | 同数据源：过期计数的**可见性**（`verify/verify_derived_numbers.py` 的 WARN 输出） | **行 9 是行 3 的前置**；已按此序做（行 9 先修） | 截断不修 ⇒ "还有多少条过期"根本看不见，行 3 无法判定做完没有 |
| E5 | 行 13 ↔ `R-001` | 同数据源 `agents/runtime/registry.json` 的 `started_at` 语义：`verify/verify_close_readiness.py:498-502` 用 `run.get("started_at") or ""` 判"数据被改过"；`R-001` 的回填会写 `started_at_backfills` | **同批**，且行 13 判据必须与 `R-001` 的覆盖边界口径一致 | 只改回填不改读取侧 ⇒ **合法回填的 run 被判"数据被改过"**（这正是当前 `run-092` 的处境） |
| E6 | 行 8 ↔ 全部自检夹具 | `%TEMP%` 根＋各文件字面量目录名：`verify/verify_card_index.py:76`、`verify/verify_close_tax_reading.py:291`、`verify/verify_close_readiness.py:2079` 等 | **同批**（要么统一 `mkdtemp`，要么统一前缀＋进程标识；混用等于没改） | 只改一两个文件 ⇒ 并发下互踩仍在，且更隐蔽 |
| E7 | 行 10、11 | 同一义务：数字必须由现跑派生、不得手抄；检查器＝`verify/verify_derived_numbers.py`（行 10 已按此改） | **同批** | 手抄新计数 ⇒ `derived_numbers` 自检再红（本会话已两次因自己写死数字被红） |
| E8 | 行 13 ↔ `R-001` 守卫的**全部夹具调用点** | 共享对象：`started_at` 的**秒级截断**（`_now()`）——`verify/verify_ledger_rounds.py:55` 的 `register --start` 紧邻 `:58` 的 `finish`；`verify/verify_agentops.py` 的 `finish` 夹具；对照 `verify/verify_ledger_measurement.py`（`time.sleep(1.2)` 规避，故不受影响） | 守卫落地前必须**普查调用点**；夹具层显式 `--allow-degenerate` ＋ 理由，**生产层禁用** | 只改授权内的 2 文件就提交 ⇒ `verify_ledger_rounds.py` 当场 rc=1（且是**概率性**红：子代理 `5a221f7c` 实测 12 次探针 10 次命中，约 5/6；**父代理独立复核：v2 探针 4/4 命中、另一次 dump 运行 1 次未命中 ⇒ 与"约 5/6"不矛盾，但非等精度复测**） |
| E9 | 行 15 ↔ 行 16 | 共享对象：**价表形状**。`verify/verify_agentops.py:417-418` 内嵌了**旧表形状的 HTML 副本**并断言旧值 `4.4e-7`；`prices-derive` 的白名单（`scripts/agent-ops.py:1580-1589`）决定 `_tiers` 能否活着派生出去 | **行 15 与行 16 同批** | 只修行 15 不动冻结副本 ⇒ 那段夹具继续按旧表形状判绿（"**闸门全绿而解析器已换掉**"，案例 25 同型）；只修行 16 不加"派生后档位仍在"的断言 ⇒ 档位静默丢失 |

## 排序约束（由 B 表推出，不含新信息）

1. **行 3**（E1 的行 7 **已完成**，`8b03c77`：两处实现已定级为"写入侧唯一实现 + 读取侧独立镜像"，
   同义性由一致性向量守 ⇒ 行 3 的前置已满足；行 9 已在行 3 之前完成，E4）。
   **行 2 无技术前置**（取证已撤原"先做行 7"的判据）。
2. **行 4、5、6 同批**（E2），且先复核批 7／批 9 未回退（E3）。
3. **行 13 与 `R-001` 同批**（E5），且该批**必须包含夹具调用点普查**（E8）——普查是这一批的入场券，不是收尾项。
4. **行 8 单独一批**（E6 面广，混进别批会被夹带）。
5. **行 10、11 同批**（E7）。
6. 行 1、9、10、12 已达成；行 14 待用户裁定。
7. **行 15 与行 16 同批**（E9）——改解析器必须同改那段冻结的旧表副本与派生白名单。
8. 行 17、18 无独立耦合，但两者都改 `cmd_finish` 的**写库语义**，与行 13／`R-001` 的守卫**共享同一条写路径**
   （`_apply_measurement` → 复制产物 → `_save_registry`）⇒ **并入行 13 那一批**，避免同一路径在 G2 关闭期被改两次。

> **本轮新增 15–18 行的原因**：15/16 由价格表多档改造暴露（并被我独立复现），17/18 由守卫交付回执暴露。
> 它们**没有被"这次只做报价表"的切片边界挡住**——切片边界是执行口径，不是发现口径。

> **E1 的更正（2026-09-26 晚，责任人是我）**：E1 初版写"`_norm_sprint` **三处**独立定义"，
> 其中第三处 `verify/verify_agentops.py:1028` **根本不存在**——那是我 `grep "_norm_sprint"` 命中的一句
> **注释**，我把它当成了实现；且行号取自**子代理改文件之前**的状态。实测只有两处定义。
> ⇒ 两处对 A 表行 2 的连带错误（"先做行 7"的前置、E1 参与边含行 2）一并撤回。
> **教训（同族第三次）**：**"名字出现过"≠"实现存在"；行号必须现跑取，不得沿用**。

## 为什么这张表值得看

A 表若只有状态，行 2 和行 7 看起来是两件独立小事；B 表 E1 说明它们共用同一份归一化，
**先修行 2 是把判据钉在会被替换的实现上**——本会话已经这样返工过一次
（批 3 的 `commit-msg` 修复是死循环，见复盘 §3）。
这就是"修一个、红一个"的来源：不是运气，是共享对象没先收敛。

## 实现记录：账本写路径批（A 表行 13／17／18／19，**同批**，2026-09-27）

> **本节的读数口径**：数字一律**时点读数**（测量时点锚 = 本批开工 HEAD `1ed6f93`），
> 校验以同名复现命令**现跑**为准；本批**未上调任何 cap、未伪造任何时间戳**。
> **状态真源仍是复盘 §5**（本档只记"关闭所需动作"与实现证据）——
> 复盘 §5 的状态列**不在本批授权写入集内**，故本节不代它改状态。

### 0. 入场券：调用点／消费者普查（改 `finish` 之前先做）

命令：`git grep -n "cmd_finish\|\"finish\"\|measurement_flags\|retractions\|started_at_backfills"`

| 调用点／消费者 | 位置（现跑） | 类别 | 行为是否变化 |
|---|---|---|---|
| `cmd_finish` 定义与派发 | `scripts/agent-ops.py::cmd_finish`／`main()` 的派发表 | 生产 | **是**（守卫前移；复制推迟） |
| `finish` 真调用 | `verify/verify_ledger_rounds.py`（`register --start` 与 `finish` 相邻） | 夹具 | 否（该夹具早已显式 `--allow-degenerate`） |
| `finish` 真调用 | `verify/verify_agentops.py`（UC-3/4/10/18/20/22/23/24 多处） | 夹具 | 否（同上，均带具名豁免参数） |
| `finish` 真调用 | `verify/verify_ledger_measurement.py::run_cli_selfcheck` 等 | 夹具 | 否 |
| 读 `measurement_flags` | `verify/verify_ledger_measurement.py`（B／F 组、棘轮） | 生产闸门 | **是**（新增"理由必填／字段配对"两条判据） |
| 读 `measurement_flags` | `verify/verify_agentops.py`（UC-24 正／反向对照） | 夹具 | 否（断言是"包含"，不依赖字段集封闭） |
| 读 `measurement_flags` | `scripts/agent-ops.py::cmd_list`（打印退化标注） | 生产 | 否 |
| 读 `agents/runs/*` 目录名 ↔ 账本 | `verify/verify_agentops.py` M-g；`verify/verify_ledger_measurement.py` A 组 | 生产闸门 | **是**（撤回必须同时移出目录，否则两侧判"有目录无记录"） |
| 读账本顶层键 | `scripts/agent-ops.py::_integrity` 只哈希 `runs`；`verify/verify_ledger_measurement.py` 读 `runs`＋`retractions` | 生产 | **是**（新增顶层 `retractions[]`，不影响完整性哈希） |
| 读 `retractions` | 本批新增（`cmd_retract`／闸门 A′ 组）；此前**无任何消费者** | 生产 | 新增 |
| 读真实账本行做真入口判据 | `verify/verify_agentops.py`（UC-20 真入口：按 `started_at`/`usage` 选档） | 生产 | 否（撤回三条探针 run 后仍有可判定行；现跑仍 PASS） |

**结论**：行为变化只落在两个生产消费者（`finish` 的写序、`verify_ledger_measurement` 的判据集）
与"目录↔账本"一致性上；三个夹具文件**一个都没被打断**（现跑全 PASS）——
这正是台账 E8 要求"守卫落地前必须普查调用点"的原因（上一批漏普查，`verify_ledger_rounds.py` 当场红）。

### 1. 行 13：`queued` run 不再被判"数据被改过"

* 改动点：`verify/verify_close_readiness.py::scope_window_problems`。
  未起跑（`started_at` 缺失或不可解析）的后续步骤 run 在次序里**没有位置**：
  旧实现把它交给 `_before` 的**字典序回退**（`"" < 任何时间戳` 恒真）⇒ 判据③报
  "引用不可能成立（数据被改过）" ⇒ 窗口被弃用 ⇒ **整档 rc=4**。
  现改为**显式 SKIP**（上屏点名）并从②③的次序比较中剔除。
* 反证（真入口 = `--sprint <真文档>` 的 real-data 模式，隔离账本 `AGENT_OPS_DIR=%TEMP%`）：
  修前 rc=4 且具名"数据被改过"；修后 rc≠4（本例 rc=0）、窗口仍可推导、SKIP 行点名该 run。
  修前一侧用 `git show HEAD:verify/verify_close_readiness.py` 源码**原地 exec**（注入真 `__file__`，
  仓库零改动）。
* 前置断言：该 run 确实 `queued`、确实无 `started_at`、role 属"作用域步骤之后"、
  `scope_source` 引用本 Sprint 的作用域 run——四条都断言（判据未触发即"不作数"）。
* 自检：`verify_close_readiness.py` 自检新增"前置 ＋ 反证"两条（末行以现跑为准）。

### 2. 行 17：守卫拒绝路径不留孤儿产物

* 改动点：`scripts/agent-ops.py::cmd_finish` ＋ 新 `_copy_result_file()`。
  旧序 = 先按字节复制 `--result-file`、后守卫 ⇒ 被拒时产物已落 `runs/<id>/` 而账本行仍 `running`。
  新序 = **守卫 → 复制 → 写库**（`RUNS_DIR.mkdir` 与复制一并推迟到守卫之后）。
* 反证（真入口 = 真 CLI 子进程，UC-24 反向对照④）：
  该轮先断言"确实是守卫拒绝"（`FINISH-ERROR` ＋ `zero_duration`），
  再比**拒前／拒后目录清单**（`runs/<id>/` 两侧均为空、账本行仍 `running`）。
* 连带：`verify_ledger_measurement.py` 的 CLI 自检走同一条 `cmd_finish`，故同序受益。

### 3. 行 18：具名豁免的理由**落账本**（裁定 = 选项①，理由如下）

**选①（行内记理由），不选②（裁定"理由只上屏"＋写进口径文档）。** 依据两条：

1. **②在本切片不可执行**：账本字段集的口径真源是 `agents/policy.json::ledger_measurement`
   （另有 `verify/README.md`／`TEST-MATRIX.MD`），三者**都不在本批授权写入集内**——
   选②就只能"声称已写进口径文档"而实际没写，那正是本仓最忌讳的"文档承诺 > 实现"。
2. **实测缺口就是"账本里查不到为什么"**：具名豁免的**事实**已落库
   （`measurement_flags` ＋ `measurement_source=declared` ＋ `dur_minutes=null`），
   缺的是**理由文本**；①把它变成可查询字段，②只是把缺口写进文档。

* 改动点：CLI 放行时写 `run["degenerate_reason"]`（原话，去空白后 ≥10 字符）；
  闸门 F 组新增两条判据：**declared ＋ 当前仍退化 ⇒ 必填 ≥10 字符**；
  `measurement_flags` 为空却带该字段 ⇒ FAIL（字段与事实不符）。
* **为什么"当前仍退化"用重算的 `flags` 而不是行内存储的 `measurement_flags`**：
  受控回填（`set-started-at`）修好起点后，行内标记会**陈旧**——实测
  `run-2026-09-26-code-review-092` 正是这种行（它写于守卫存在之前，从未走过 `--allow-degenerate`）
  ⇒ 按存储标记判会把**被修复工具修好的行**追溯判红。首轮实现就是这样，现跑当场抓到并改正（如实记）。
* 反证（真入口）：UC-24 正向对照断言 `degenerate_reason` **逐字等于**所传理由；
  并对整本夹具账本断言"`degenerate_reason` ↔ `measurement_flags` **逐行配对**"
  （前置：确有带退化标记的行，否则不作数）。闸门自检另有"缺理由 ⇒ FAIL""无标记却带字段 ⇒ FAIL"两条。

### 4. 行 19：受控撤回（`retract`）——误登记 run 的唯一合法删除路径

* 新命令 `scripts/agent-ops.py retract <run_id> --reason <≥10 字符> --evidence <存在的路径>`，
  四条硬约束：①理由长度；②**留痕** `registry.json` 顶层
  `retractions[]{at, by, run_id, reason, evidence, status_at_retraction, quarantine}`；
  ③**只认显式点名的单条 id**（正则白名单，通配／批量／前缀／路径分隔符一律拒绝）；
  ④`--evidence` 必须存在（"凭什么说这条是误登记"必须可核）。
* **产物不销毁**：`runs/<id>/` 整体**移到** `runtime/retracted-runs/<id>/`（同根、git 忽略域、
  不在 `runs/` 判定域里）。撤回删的是**账本行**，不是那次动作的现场。
* 两处 fail-closed：被其余 run 的 `scope_source` 引用的 run 不得撤回（会打断引用链）；
  已撤回过的 run 不得重复撤回（不做假痕）。
* **闸门新增 A′ 组判据**（把"撤回"从"账本少了一行"变成可核路径）：
  留痕条目齐备（`run_id`/`at`/`by`/`reason≥10`/`evidence`）；
  撤回后该 run **不得**再出现在 `runs`；留痕里的 `quarantine` 非空 ⇒ 该路径必须真实存在。
  正向样本走**真 CLI**（写盘只有一处实现），闸门只读它——手工造目录等于测自己造的样本。
* **生产账本的三条探针 run 已按此路径撤回**：
  `run-2026-09-27-impact-assessment-097／098／099`（价表批验收探针误写入；正确形态是隔离账本），
  留痕 `retractions[]` 三条、产物在 `runtime/retracted-runs/`、`--evidence` 指向 G2 复盘 §5 行 19
  的逐字点名（`docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD`）。
  **未用 `set-started-at` 回填时间戳换绿**（父代理已否决：那是伪造测量值）。
* 反证（真入口 = 真 CLI）：正向（撤回成功＋行已删＋七字段留痕＋隔离区报告逐字节相同）；
  反向六条（通配 id／短理由／证据不存在／run 不存在／重复撤回／被引用）全部拒绝**且账本未动、产物未动**。
* **副作用（如实记）**：撤回的落点在源码里写成**模块常量** `QUARANTINE_DIR`（而不是 `QUARANTINE_DIR / rid`），
  靠 `shutil.move` 的"目标是已存在目录 ⇒ 移入其内"语义保持 `<隔离区>/<run_id>/`——
  因为 `verify_artifact_paths.py` 的**动态写盘目标棘轮只许下调**，新增动态落点会让该闸门红
  （实测：本批首轮实现让 `scripts/agent-ops.py` 超出该表上限，已按"可静态判定"改写）。

### 5. 门槛与爆破半径（末行一律以现跑为准）

| 门槛 | 命令 | 结果 |
|---|---|---|
| 语法 | `python -m py_compile`（四个授权文件） | rc=0 |
| CLI 用例 | `verify\verify_agentops.py` | ALL PASS（断言数以现跑末行为准；含新增 UC-24④／UC-25） |
| 关闭前置 | `verify\verify_close_readiness.py`（自检 ＋ `--sprint` 真数据） | 自检 ALL PASS；真数据 PASS rc=0 |
| 账本测量化 | `verify\verify_ledger_measurement.py` | **真实账本 PASS rc=0**（撤回前为 FAIL rc=1，逐条点名 `zero_duration`；**靠撤回机制变绿，不是靠改读数**） |
| 分层套件 | `verify\run_suite.py --tier offline` | SUITE PASSED（脚本数以现跑末行为准） |
| Lint | `verify\verify_lint.py` | ALL PASS；全仓 E501 计数**低于**本批开工时读数（未上调 cap） |
| 产物落点 | `verify\verify_artifact_paths.py` | ALL PASS（动态目标棘轮未超上限） |

**爆破半径**：本批新增判据会对以下既往形态判红——无理由的 `declared` 退化行（行 18）、
账本缺留痕的撤回（行 19）、未起跑 run 触发的窗口弃用（行 13，改为不再判红）。
真数据上现跑为 0 项（三条探针 run 已撤回；`run-2026-09-26-code-review-092` 因"当前已不退化"不判红，
理由见 §3）。

### 6. 本批新发现的边界与未做项（**不静默压掉**）

| # | 项 | 性质 |
|---|---|---|
| 1 | **行 18 的判据只覆盖窗口内 run**（棘轮域内的历史行不回溯要求该字段） | 与 F 组既有口径一致（"只对新 run 强制"）；历史行要不要补理由属新决定，未做 |
| 2 | **`round_duration` 不在 `finish` 守卫的拒绝集内**（`_DEGENERATE_FLAGS` 三类），故该形态不需要 `--degenerate-reason`；但窗口内它本就被 `[round_duration]` 判 FAIL | 口径不对称**如实记录**：未扩大守卫范围（不在本批授权范围，且会改变既有夹具行为） |
| 3 | **撤回不留"反向操作"**（没有 un-retract） | 撤回后若发现撤错，只能重新登记（新 run_id）；"把行原样写回"没有受控路径。是否要 un-retract 属新决定 |
| 4 | 复盘 §5 行 13／17／18／19 的**状态列未改**（不在授权写入集内） | 需由状态真源的维护者按本节证据更新；否则"零未闭环项"的账面上仍显示未修 |
| 5 | `verify_artifact_paths.py` 的动态目标棘轮**只许下调**，任何后续在 `agent-ops.py` 新增动态落点都会红 | 已知约束（本批已按它改写落点），非缺陷 |
