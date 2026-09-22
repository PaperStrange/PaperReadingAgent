# lint 闸门候选依赖 —— §2.4 引入前置核查（安全与数据隐患）

> **状态：条件通过（不允许直接引入，须按 §5 先补两项 + 按 §6 由用户裁定取舍）**
> **本文件 = §2.4 的一手证据台账**（原始数值由**进程级**读取 PyPI / registry.npmjs.org / api.osv.dev 得到，见 §7；收集于 2026-09-21 UTC+8）。Sprint-17 §9 引用本文件，不复制其数值。
> **方法学更正（重要）**：本环境 **harness 的 `web_fetch` 工具对所有域名一律返回"resolves to a non-public IP address"**（pypi.org / registry.npmjs.org / api.osv.dev / github.com / raw.githubusercontent.com 均如此），但**普通进程的网络是通的**——同机 `urllib` 直连 PyPI/npm/OSV 均返回 HTTP 200。因此本文件**不使用**任何"搜索结果标题"作为数值来源；早前"仅检索标题"的草案已改名为 `2026-09-21-lint-deps-security-check.search-only-draft.MD` 并保留为审计痕迹（差异见 §8）。

---

## 1. 候选清单与当前状态

| 语言/文件 | 量（2026-09-21 `git ls-files`） | 候选工具 | 引入批次 |
|---|---|---|---|
| Python | 112 | `ruff` | G1 |
| JavaScript / JSX | 26 mjs + 7 jsx | `eslint`（+ react 插件）、`prettier --check` | G2 |
| TypeScript / TSX | 17 | `@typescript-eslint`（parser+plugin）、`prettier --check` | G2 |
| YAML | 53（**自有仅 `.github/workflows/ci.yml` 1 个**） | `yamllint`（或自研） | G2 |
| PowerShell | 7 | `PSScriptAnalyzer` | G2 |

**本机/CI 前置条件（一手）**：本机 `node v26.8.2`、`npm 12.0.2`；CI `node-version: 22`（满足 eslint 10 的 `^22.13.0`）；Python 依赖入口 `requirements-windows.txt`（CI 第 42/110 行）；两个前端各有独立 `package.json` + `package-lock.json`（`agents-dashboard/`、`paper-qa-script/reactflow-paperqa-prototype/frontend/`），**当前均未安装 eslint/prettier/typescript-eslint**（`.bin` 探测为 False）。

---

## 2. 逐包结论（全部为一手读数）

| 包 | 最新版本（发布时间，UTC） | 许可证（一手） | 安装期脚本 / 构建 | 已知漏洞（OSV + GitHub Advisory） | 近月下载量 | 处置建议 |
|---|---|---|---|---|---|---|
| `ruff` | **0.16.8**（2026-09-16） | **MIT**（PyPI `license_expression` + LICENSE 文件） | 无（**win_amd64 wheel 就绪**，无需编译；sdist 亦在） | **OSV：该包任何版本 0 条；GitHub Advisory：0 条** | — | **可引入**，但建议与仓库既有 pin 对齐（见 §3.2） |
| `prettier` | **3.9.8**（2026-09-17） | MIT（registry `license`） | 无安装脚本；**运行时依赖 0 个** | **0 条**（核心包） | 4.72 亿 | **可引入**；**硬约束**：不得引入 `eslint-config-prettier`/`eslint-plugin-prettier`（§3.1） |
| `eslint` | **10.11.0**（2026-09-18，发布 3 天） | MIT（LICENSE = OpenJS Foundation） | 无安装脚本（`preinstall/install/postinstall/prepare` 均无） | 本包 **0 条**；**依赖树存在未按版本解析的告警信号**（§3.3） | 5.75 亿 | **条件可引入**：必须做"按锁定版本"的复核（§5.1） |
| `@typescript-eslint/parser` | **8.70.1**（2026-09-21） | MIT | 无安装脚本 | 本包 0 条；依赖 `debug` 有 MAL 信号 | 5.04 亿 | 条件可引入（与 eslint 捆绑决策） |
| `@typescript-eslint/eslint-plugin` | **8.70.1**（2026-09-21） | MIT | 无安装脚本 | 本包 0 条 | 4.62 亿 | 同上；**先评估是否必要**（§6.4） |
| `eslint-plugin-react` | **7.37.5**（**2025-04-03**，约 17 个月前） | MIT | 无安装脚本（仅 `prepack`） | 本包 0 条；依赖树 `minimatch`/`semver` 告警信号 | 2.24 亿 | **建议不引入或延后**（§3.4） |
| `yamllint` | **1.38.0**（2026-01-13） | **GPL-3.0-or-later**（PyPI `license_expression` + LICENSE 文件） | 无（pure-python wheel） | 0 条 | — | **建议不引入**：许可证需判断 + 自有 YAML 只 1 个文件 → 自研 `verify_yaml.py`（§3.5） |
| `PSScriptAnalyzer` | **1.25.0**（2026-03-20；共 38 版） | MIT（LICENSE = Microsoft） | 无依赖（PowerShell 模块） | **OSV 无 PowerShell 生态 → 无法按包查询**（未核实） | — | **延后到 G2 再定**：只服务 7 个 `.ps1`（§3.6） |

---

## 3. 关键发现

### 3.1 恶意代码事件已确证（草案线索成立，并升级为硬约束）
OSV 对 `eslint-config-prettier` / `eslint-plugin-prettier` / `synckit` / `@pkgr/core` / `napi-postinstall` 五个包均返回：
- `GHSA-f29h-pxvx-f335`（别名 **CVE-2025-54313**，severity **HIGH**，摘要："… have embedded malicious code"）；
- 另有 `MAL-2025-6021/6022/6023/6025/6026`（恶意包条目）。

→ **硬约束（有据）**：lint 闸门**不得**引入 `eslint-config-prettier` 与 `eslint-plugin-prettier`（及 `synckit`/`@pkgr/core`/`napi-postinstall`）。**`prettier` 核心包不受影响**（0 运行时依赖、0 告警）。
→ 附带结论：**eslint 与 prettier 不做"规则集成"**，仅各自独立运行（`eslint .` + `prettier --check .`）——这恰好也是 G1/G2 闸门的设计意图。

### 3.2 仓库里已经存在上游 pin（最小化与一致性）
`paper-qa/.pre-commit-config.yaml`（vendored，一手）已 pin：`ruff v0.14.4`、`black 25.11.0`、`prettier v3.6.2`，并带 `mixed-line-ending` / `end-of-file-fixer` / `trailing-whitespace` 三个钩子。
→ 处置：**优先复用已在仓库出现过的版本**（ruff `0.14.4` 经 OSV 实测 **0 条告警**，见 §7 探针），或明确记录"为何升到 0.16.8"。**禁止沉默漂移**——同一工具两处不同 pin 就是 TG-12 型漂移。
→ 附带：`mixed-line-ending` 钩子正好对应本轮实测到的"编辑引入 CRLF → 全文件假 diff"问题（§8 附注），G1 的仓库结构闸门可直接覆盖该形态。

### 3.3 `eslint` 依赖树必须按锁定版本复核（不能凭"本包 0 条"结案）
`eslint@10.11.0` 的**声明依赖**在 OSV 中"按包名（不限定版本）"命中告警信号：
`ajv`、`debug`（含 **MAL-2025-46974**）、`minimatch`、`cross-spawn`、`glob-parent`、`eslint-scope`、`@humanfs/node`、`@eslint/plugin-kit`（`GHSA-xffm-g5w8-qvg7` ReDoS）、**`file-entry-cache`（MAL-2026-11970）**。
→ 这些是"**该包某些版本**受影响"的信号，**不等于**我们锁定版本受影响；**也不等于安全**。必须做 §5.1 的锁定版本复核，否则"无已知漏洞"就是无据陈述（正是 A-M11 C2b"检查在骗人"的形态）。

### 3.4 `eslint-plugin-react` 价值/维护度双低
最后发布于 **2025-04-03**（约 17 个月前）；依赖树含 `minimatch`/`semver` 告警信号；React 17+ 自动 JSX 运行时使多数经典规则（`react/react-in-jsx-scope` 等）失去意义。
→ 建议：**不引入**（或延后），JSX 侧只保留 `eslint:recommended` + 少量规则。

### 3.5 `yamllint`：GPL-3.0 + 自有 YAML 仅 1 个文件
一手：LICENSE 文件为 **GNU GPL v3**，PyPI `license_expression = GPL-3.0-or-later`。开发期工具通常不构成分发问题，但**需用户判断**（本仓库分发口径未在本卡确认）。同时 §2.4 第 6 项（最小化）：**本仓库自有 YAML 只有一个 `.github/workflows/ci.yml`**。
→ 建议：**自研 `verify/verify_yaml.py`（~50 行，PyYAML 已在 `.venv` 内）**，覆盖 `ci.yml` 的结构断言；等自有 YAML 增长再评估 `yamllint`。

### 3.6 `PSScriptAnalyzer`：没有可用的漏洞库通道
最新 1.25.0（2026-03-20，距今约 6 个月）、MIT、无依赖。但 **OSV 无 PowerShell ecosystem**，`api.osv.dev` 无法按包查询；只能人工查 GitHub Advisory / 厂商公告。
→ 该包的"漏洞核查"**在本环境无法按 §2.4 第 1 项完成**；加上只服务 7 个 `.ps1` → **延后到 G2**，或只启用极小规则集并**在 Sprint §9 显式记为"第 1 项未完成"**。

---

## 4. §2.4 六项逐项判定（总表）

| # | 核查项 | ruff | eslint | prettier | @typescript-eslint | eslint-plugin-react | yamllint | PSScriptAnalyzer |
|---|---|---|---|---|---|---|---|---|
| 1 | 已知漏洞 | ✅ 0 条（OSV 全版本 + GH） | ⚠️ 本包 0 条 / **依赖树待按锁定版本复核** | ✅ 0 条（0 依赖） | ⚠️ 本包 0 条 / `debug` 信号 | ⚠️ 本包 0 条 / 依赖树信号 | ✅ 0 条 | ❌ **无查询通道（未核实）** |
| 2 | 安装期脚本/构建 | ✅ wheel 就绪 | ✅ 无 | ✅ 无 | ✅ 无 | ✅ 无（仅 prepack） | ✅ pure wheel | ✅ 无依赖（但 `Install-Module` 会执行发布者代码，见 §5.2） |
| 3 | 遥测/离线 | ⚠️ 未做断网实跑 | ⚠️ 同 | ⚠️ 同 | ⚠️ 同 | ⚠️ 同 | ⚠️ 同 | ⚠️ 同 |
| 4 | 许可证 | ✅ MIT | ✅ MIT | ✅ MIT | ✅ MIT | ✅ MIT | ❌ **GPL-3.0-or-later** | ✅ MIT |
| 5 | 维护度/来源 | ✅ astral-sh，活跃 | ✅ OpenJS，3 天前发版 | ✅ 活跃 | ✅ 同日发版 | ❌ 17 个月未发版 | ✅ 活跃 | ⚠️ 6 个月前，38 版 |
| 6 | 最小化 | ⚠️ 与上游 pin 需对齐 | ✅ | ✅ | ⚠️ 能否用 `tsc --noEmit` 替代待定 | ❌ 价值低 | ❌ 自研更小 | ⚠️ 仅 7 个 ps1 |

**结论**：**没有任何一个包"六项全绿"**。§2.4 的"任一项不通过 → 拒绝引入或换等价替代"在本轮的实际含义：
- **直接拒绝**：`eslint-config-prettier`、`eslint-plugin-prettier`（第 1 项 HIGH + 恶意代码）。
- **建议替换/不引入**：`yamllint`（第 4/6 项）→ 自研 `verify_yaml.py`；`eslint-plugin-react`（第 5/6 项）→ 不引入。
- **条件引入（须补 §5.1 + 用户确认）**：`ruff`、`eslint`、`prettier`、`@typescript-eslint`。
- **延后**：`PSScriptAnalyzer`（第 1 项无通道）。

---

## 5. 待补两项（补完才允许"引入"）

### 5.1 按**锁定版本**复核依赖树漏洞面（G1 第一项任务的收尾）
做法（任一，须留原始输出到 Sprint §9）：
1. 在两个前端各自 `npm ci --ignore-scripts` 后执行 `npm audit --json`（锁定版本口径），JSON 摘要落盘；
2. 或对锁文件做 OSV 批查（`POST https://api.osv.dev/v1/querybatch`，按 `name@version` 逐条），列出命中条目与"修复版本"；
3. Python 侧 `ruff`：确认无额外传递依赖，并对**最终锁定版本**再跑一次 OSV 查询。
**判定**：命中 high/critical 且无修复版本 → 拒绝或换替代（§2.4 原文）。

### 5.2 断网实跑（第 3 项）+ 安装期脚本的复核
- 断网实跑：在无网络环境执行一次 `verify_lint.py`（G1 交付物）并留证；若工具在断网时请求网络（更新检查等）→ **记为不通过**。
- 安装期脚本：本轮已从 **registry 的 `versions[latest].scripts`** 判定 npm 侧 `preinstall/install/postinstall/prepare` **均不存在**（一手）；**CI 另有 `npm ci --ignore-scripts`**（`.github/workflows/ci.yml:77`，一手，注释引用 Sprint-10 调研 + `3-LEARNED` 1.31）→ 双保险。`Install-Module`（PowerShell 模块）会执行发布者代码，属"需用户批准"类；若最终引入 PSScriptAnalyzer 须走批准。

---

## 6. 需要用户裁定（6 项）

> **裁定结果（用户 2026-09-21，UTC+8）**：`L1=a` `L2=b` `L3=a` `L4=c` `L5=a` `L6=b`（答复原文：`L1=a L2=b L3=a L4=c L5=a L6=b`）。逐项后果见 §6.2。

| # | 问题 | 主代理建议（未答复即按此默认执行） | **用户裁定** |
|---|---|---|---|
| 1 | 是否接受"**条件通过**"中间态（先补 §5.1/§5.2 再引入），还是"未完成第 1 项一律不得引入"？ | **接受条件通过**：第 1 项可按锁定版本补做，且 ruff/prettier 已 0 告警 | **a = 条件通过**（按 §6.1 的"先查后装"顺序执行） |
| 2 | 闸门要"**统一格式化**"还是只"**可读性规则**"？若只要后者，`prettier` 可整体砍掉（少一个工具、少一次格式化大 diff） | 先只对**新增/改动文件**跑 `prettier --check`；若嫌吵则砍掉 | **b = 只查新增与改动文件** |
| 3 | `eslint-plugin-react` 是否引入？ | **不引入**（§3.4） | **a = 不引入** |
| 4 | `@typescript-eslint` 是否必要？替代方案 = 既有 `tsc --noEmit` + `tsconfig` strict（**零新增依赖**）；只有 `no-floating-promises` 这类类型感知规则不可替代 | 先把 `tsc --noEmit` 进闸门，`@typescript-eslint` 延后观察 | **c = 两者都上**（`tsc --noEmit` + `@typescript-eslint`） |
| 5 | `PSScriptAnalyzer`：7 个 `.ps1` 是否值得引入整个模块（且漏洞核查无 OSV 通道）？ | **延后到 G2**；如引入，§9 记为"第 1 项未完成" | **a = 延后到 G2** |
| 6 | `yamllint`：接受自研 `verify_yaml.py`（~50 行），还是坚持引入 GPL-3.0 的 `yamllint`？ | **自研**（§3.5） | **b = 引入 `yamllint`**（GPL-3.0 由用户接受，见 §6.2） |

### 6.1 逐项详解（决策简报）

**共同前提（先对齐三条，否则逐项都难判断）**
1. 闸门要解决的是"**人类读得懂**"这条 `code major` 判据**可执行**，不是"风格统一"。判断每个工具只问一句：**它抓的是可读性，还是格式偏好？**
2. 引入成本 ≠ 安装：每个工具 = 一条 CI 步骤 + 一份配置 + 一个 pin + **一次全仓基线（常伴随大 diff，恰是 R1/R2 盲区）** + §2.4 两项待补 + 明确的"工具缺失时 **fail-closed** 还是显式 `skipped`"策略。
3. **只有 L1 真正卡 G1**（Python 112 文件是最大面）；**L2~L6 属 G2 面**，本轮先定方向、G2 再落，选错的成本是方向成本而非返工。

| # | 选项 | 立即后果 | 建议 + 理由 |
|---|---|---|---|
| **L1** | (a) 条件通过 / (b) 两项补完才允许装 / (c) 不引新依赖、全自研 | (b)(c) 使 G1 只剩自研结构断言 | **(a)**，但把顺序做对：**先用"不执行安装脚本"的方式生成锁定版本清单并做 OSV 批查，通过后才真正安装**（npm：`npm install --package-lock-only --ignore-scripts` → `npm audit --json` **在无 `node_modules` 状态下**；Python：`pip download <pin> --no-deps` 取 wheel 校验依赖）。这样"第 1 项"是**先查后装**，不是绕过 |
| **L2** | (a) 不引 / (b) 只查新增与改动文件 / (c) 全仓一次性重排 | (c) 产生全仓格式化 diff（须独立提交 + `.git-blame-ignore-revs`，否则真实改动被淹没） | **(b) 且只检查不自动写**：要的是"新代码读得懂"，不是"长得一样"；先避开大 diff 风险 |
| **L3** | (a) 不引（只用 `eslint:recommended`）/ (b) 引 `eslint-plugin-react` / (c) 只引 `eslint-plugin-react-hooks`（**不在 §2.4 候选清单 → 需单独核查**） | (c) 多一次 §2.4 | **(a)**；若在意 hooks 依赖数组类真 bug，把 (c) 单列成 G2 小项后补核查 |
| **L4** | (a) 只上 `tsc --noEmit`（**零新增依赖**）/ (b) 上 `@typescript-eslint` / (c) 两者 | 只有 (b) 拿得到 `no-floating-promises` 等**类型感知**规则 | **(a) 先上**；(b) 待 G2 用"是否真漏过 bug"决定——新增依赖越多，§2.4 维护面越大 |
| **L5** | (a) 延后到 G2 / (b) 引入但只启用极小规则集（§9 显式记"第 1 项未完成"）/ (c) 自研轻量断言 | 仅服务 7 个 `.ps1`；**OSV 无 PowerShell 生态** | **(a)**；(c) 更对症——本仓 PS 事故都是**环境语义**（BOM/AMSI/退出码）而非风格，留 G2 决定 |
| **L6** | (a) 自研 `verify_yaml.py` / (b) `yamllint`（**GPL-3.0-or-later**）/ (c) 都不做 | (b) 需你先给**许可证口径**（本仓是否分发/私有部署给第三方） | **(a)**：最小化 + 免许可证判断 + 把我们真正关心的几条钉死 |

**答复方式**：`L1=a L2=b L3=a L4=a L5=a L6=a`（未答复则按上表建议执行，并在 Sprint-17 §9 记为"默认执行、可回溯"）。

### 6.2 裁定后的执行清单（用户 2026-09-21 裁定：`L1=a L2=b L3=a L4=c L5=a L6=b`）

| # | 裁定 | 必须做的动作 | 落批次 |
|---|---|---|---|
| **L1=a** | 条件通过 | ① 按"**先查后装**"顺序：`npm install --package-lock-only --ignore-scripts`（**无 `node_modules`**）→ `npm audit --json`；Python 侧 `pip download <pin> --no-deps` 确认零传递依赖；② 通过后才 `npm ci --ignore-scripts` / `pip install`；③ **原始输出入 Sprint §9**；④ 不通过则回滚并退回 (b) | **G1**（第一项任务；先做 Python/ruff 侧） |
| **L2=b** | prettier 只查新增与改动文件 | ① `prettier --check` 的输入 = `git diff --name-only <base>...HEAD`（只含新增/改动，**不重排历史文件**）；② 只检查不自动写；③ 禁止 `eslint-config-prettier`/`eslint-plugin-prettier`（§3.1 硬约束）；④ 版本口径记明（我们用 3.9.8 vs 上游 vendored v3.6.2） | **G2** |
| **L3=a** | 不引入 `eslint-plugin-react` | JSX 侧只用 `eslint:recommended`（如需 hooks 类规则，另开小项并补 §2.4） | **G2** |
| **L4=c** | `tsc --noEmit` + `@typescript-eslint` **都上** | ① `tsc --noEmit`（零新依赖）先进闸门；② `@typescript-eslint` parser+plugin 同 pin `8.70.1`，走 L1 的"先查后装"；③ **补一项未核实**：`@typescript-eslint@8.70.1` 与本机 `typescript ^5` 的**支持区间**须实测（版本不匹配要显式降/升 pin） | **G2** |
| **L5=a** | `PSScriptAnalyzer` 延后 | 本轮不引入；G2 再评估时**先解决"第 1 项无 OSV 通道"**（人工查 GitHub Advisory 并留证，或改用自研环境语义断言） | **G2**（评估） |
| **L6=b** | 引入 `yamllint`（GPL-3.0-or-later） | ① **许可证口径由用户接受**：`yamllint` 仅作**开发期/CI 工具**、不随产品分发；② pin `1.38.0`（pure-python wheel）；③ **改判条件（必须写进 G2 记录）**：若将来项目改为**分发**（打包 `node_modules`/Python 环境给第三方、或把 lint 工具链随产品发布），GPL 问题**须重新评估**；④ 闸门仍要做"YAML 结构断言"（自有仅 `ci.yml` 1 个文件） | **G2** |

---

## 7. 原始证据（一手读数，摘要）

**探针**（2026-09-21，本机 `.venv` 解释器；harness `web_fetch` 被阻但进程直连成功）：
```
GET  https://pypi.org/pypi/ruff/json               -> 200 bytes=6110276   ruff latest=0.16.8
GET  https://registry.npmjs.org/eslint             -> 200 bytes=2085131   dist-tags.latest=10.11.0
POST https://api.osv.dev/v1/query  ruff@0.14.4     -> 200 vulns=0
```
**收集脚本**：临时目录 `dep_precheck.py`（**非仓库文件**；逻辑 = 逐包读 registry + OSV `query` + GitHub Advisory API + PowerShell Gallery OData），要点：
- `ruff`：`latest=0.16.8 uploaded=2026-09-16T15:53:57Z`；wheel `ruff-0.16.8-py3-none-win_amd64.whl`；`license_expression=MIT`；`osv_for_version=[]`、`osv_any_version_count=0`、`gh_advisories=[]`。
- `yamllint`：`latest=1.38.0 uploaded=2026-01-13`；`license_expression=GPL-3.0-or-later`；OSV/GH 均 0。
- `eslint`：`latest=10.11.0 published=2026-09-18T20:15:36Z`；`license=MIT`；`engines.node=^20.19.0 || ^22.13.0 || >=24`；`has_install_script=False`；`downloads_last_month=575060073`；`osv_for_version=[]`、`osv_any_version_count=0`；依赖树信号见 §3.3。
- `prettier`：`latest=3.9.8 published=2026-09-17T21:41:05Z`；`license=MIT`；`scripts={}`、`dependencies={}`；OSV/GH 均 0；`downloads_last_month=472473901`。
- `@typescript-eslint/parser`、`@typescript-eslint/eslint-plugin`：均 `8.70.1 published=2026-09-21`；MIT；无安装脚本；OSV/GH 均 0。
- `eslint-plugin-react`：`latest=7.37.5 published=2025-04-03`；MIT；无安装脚本；本包 OSV 0；依赖树 `minimatch`/`semver` 信号。
- `PSScriptAnalyzer`：`FindPackagesById` 返回 **38 版**；`1.25.0 published=2026-03-20T19:25:00Z`；`license_url=…/PSScriptAnalyzer/blob/main/LICENSE`（一手拉取 = **MIT**，Microsoft）。
- 许可证一审（LICENSE 文件直读）：ruff **MIT**、yamllint **GPL-3**、PSScriptAnalyzer **MIT**、eslint **MIT**（OpenJS Foundation）。
- 仓库侧一手：`paper-qa/.pre-commit-config.yaml` → `ruff v0.14.4` / `prettier v3.6.2` / `black 25.11.0` + `mixed-line-ending` 等钩子；`.github/workflows/ci.yml:77` → `npm ci --ignore-scripts`；两个前端 `package.json`+`package-lock.json`，当前均无 eslint/prettier。

---

## 8. 与"仅检索标题"草案的差异（审计痕迹）

早前草案（harness `web_fetch` 全阻、只拿到 `web_search` 标题/URL）的数值**部分与时序不符**，逐条对照：

| 项 | 草案说法 | 一手复核 |
|---|---|---|
| prettier pin | `3.9.1`（3.9.0 = 2026-06-27） | registry `latest = **3.9.8**`（2026-09-17）→ 以 3.9.8 或**锁定版本实际解析值**为准 |
| ruff pin | `0.16.8` | ✅ 一致（2026-09-16）；但**仓库已 vendored `v0.14.4`**（草案未提） |
| eslint 版本 | `10.11.0` | ✅ 一致（2026-09-18 发布） |
| CVE-2025-54313 | 称 2026-01-22 入 CISA KEV、EPSS 11.62% | **条目成立**（OSV `GHSA-f29h-pxvx-f335`，HIGH，五个包内嵌恶意代码）；**"入 KEV 日期 / EPSS 数值"未复核** |
| eslint CVE-2025-50537 | 称 9.17.0 受影响 | **OSV 对 `eslint` 任何版本均为 0 条**；该编号在 OSV 中查不到 → **未核实**（若将来降级到 9.x 需另查） |
| `yamllint` 结论 | 建议不引入（自研） | ✅ 一致，且补充**许可证 = GPL-3.0** 这一更强理由 |
| 安装期脚本 | npm 三包"未核实" | ✅ 本轮一手核实为**无安装脚本**（registry `scripts` 字段） |
| 版本发布日期/下载量/许可证 | 全部"未核实" | ✅ 本轮全部取得一手值（§2/§7） |

### 附注：本轮顺带实测到的仓库结构缺陷（已在本批修复）
- **表格结构非法**：4 份 `phases/*/backlog.MD` 存在"表头列数 ≠ 行内列数"（testing-governance 6 vs 7、refactor-analysis 6 vs 7、agents-infra 5 vs 4~7），其中 7 行属**非末尾单元格缺失**（内容渲染到错误列名下）→ 已统一为 7 列表头并补占位；判据已写入计划 §2.3。
- **行尾漂移**：仓库基线为 **LF**，本轮编辑引入 **CRLF** → 48/25/74/32 行出现"全文件假 diff"（真实改动仅 10/3/4/10 行），已回退为 LF。**这是 R1/R2 的检测盲区**：全文件重写会掩盖真实改动 → 建议 `verify_lint.py` 增"行尾一致性 + diff 规模异常"断言（上游 `mixed-line-ending` 钩子即为此形态）。

**未核实项清单（本轮仍缺）**：① 断网实跑（§5.2）；② 锁定版本依赖树漏洞面（§5.1）；③ `PSScriptAnalyzer` 的漏洞条目（无 OSV 通道）；④ `@typescript-eslint@8.70.1` 与本机 `typescript ^5`（agents-dashboard）的支持区间未逐版本核对；⑤ 各包遥测/联网行为的**文档级**证据未逐条抄录（只做了"依赖/安装脚本"层面的判定）。
