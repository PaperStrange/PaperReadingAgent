# 2026-09-21 lint 工具依赖安全与数据隐患前置核查（§2.4 / G1 第一项）

> ⚠️ **已被取代（2026-09-21 同日）**：本文件为**仅凭 `web_search` 标题/URL** 写成的草案（成因：harness `web_fetch` 对所有域名返回"非公网 IP"）。**其数值不得引用。** 同日经**进程级探针**证明"同机 `urllib` 可直连 PyPI / registry.npmjs.org / api.osv.dev（均 HTTP 200）"后已重做一手核查 → 权威文件：[`2026-09-21-lint-deps-security-check.MD`](2026-09-21-lint-deps-security-check.MD)（其 §8 逐条列出与本草案的差异）。本文件**保留为审计痕迹**（记录"把**工具**失败误当**环境**失败"这一过程事故），不再更新。

**状态**：本文件是 G1 第一项任务的产出——按 `docs/iteration/sprint/2026-09-21-governance-batch-plan.MD` §2.4「依赖引入前置：安全与数据隐患核查」（用户 2026-09-21 D7 附加前提）对 §2.3 闸门候选的六个依赖逐一执行六项核查（已知漏洞 / 安装脚本与构建期执行 / 数据外发与遥测 / 许可证 / 维护活跃度与来源 / 最小化）；**本次核查项 1（已知漏洞）未能按 §2.4 指定的 OSV API / pip-audit / npm audit 方式执行**（本执行环境 DNS 将 `api.osv.dev`、`pypi.org`、`registry.npmjs.org`、`github.com`、`raw.githubusercontent.com`、`osv.dev`、`www.powershellgallery.com`、`eslint.org` 等全部解析到非公网 IP，`web_fetch` 100% 失败），因此下文所有漏洞结论均来自**搜索引擎命中的公开页面标题/URL**，凡未能实际打开原文者一律标注 `未核实（原因）`，**未通过核查**，不得据本文件单方面放行。**本次未安装、未运行任何包管理器、未修改任何其他文件。**

---

## 0. 核查规程原文与本文件证据等级

§2.4 规则原文（引用）：

> **规则**：**任何**为 §2.3 闸门引入的新依赖（`ruff` / `eslint` / `prettier` / `@typescript-eslint` / `yamllint` / `PSScriptAnalyzer` 及其插件），在引入前必须完成下列核查，**任一项不通过 → 拒绝引入或换等价替代**；结果记入 Sprint §9（含核查命令与原始输出）。

| # | 核查项 | §2.4 具体要求 | 不通过的处理 |
|---|---|---|---|
| 1 | **已知漏洞** | `pip-audit` / `npm audit` / **OSV API**（`https://api.osv.dev/v1/query`）逐包按版本查已知 CVE/OSV | 有 high/critical → 拒绝或换替代 |
| 2 | **安装脚本与构建期执行** | 检查是否带 `postinstall`/`setup.py` 执行、是否需要 node-gyp/编译工具链 | 需构建期执行的 → 需用户批准 |
| 3 | **数据外发 / 遥测** | 是否有 telemetry / 上传代码或路径 / 默认联网抓取；**离线运行验证**（断网跑一遍闸门） | 有联网行为且不可关 → 拒绝 |
| 4 | **许可证** | 许可证类型（MIT/Apache-2.0/PSF 等）与本项目分发兼容性 | 不兼容 → 拒绝 |
| 5 | **维护活跃度与来源** | 官方仓库 / 下载量 / 最近发布日期（供应链风险）；**锁版本**进锁文件 | 冷门或长期不维护 → 换替代 |
| 6 | **最小化** | 能用既有工具（`verify_*.py` 自研断言、`json`/schema 校验）解决的**不引入新依赖** | — |

**本次证据等级（必须如实理解）**：

- **A 级（本次实际执行）**：`web_search` 命中页面的标题与 URL。标题本身是可核验的公开事实载体，但**不含正文**。
- **B 级（本次执行失败）**：`web_fetch` 全部失败（错误信息统一为 `URL hostname "<host>" resolves to a non-public IP address`）。已尝试并对全部六个包的目标源各失败至少一次：`pypi.org`、`registry.npmjs.org`、`raw.githubusercontent.com`、`api.osv.dev`、`osv.dev`、`github.com`、`eslint.org`、`www.powershellgallery.com`。
- **结论**：**核查项 1 本次未按规程执行**（OSV API 不可达）；**核查项 2/3/4/5 中的多数细节为 `未核实`**。因此本文件对六个包的定位是「把已知风险讲清楚 + 把未知项列全」，**不是**「已通过 §2.4」。

**本仓库现状（用于核查项 6，本地只读检查所得）**：

- 既有机制：`verify/` 下 30+ 个自研断言脚本（`verify_runner.py` / `verify_config_schema.py` / `verify_matrix.py` / `verify_index_health.py` 等）+ `verify/run_suite.py --tier offline` 分层闸门；`.github/workflows/ci.yml` 已跑「整个 offline 档」。
- 两个前端子项目的 `package.json` 中**均未安装** `eslint` / `prettier` / `@typescript-eslint` / `eslint-plugin-react`（本地 `node_modules` 只读检查：全部 `ABSENT`），但二者**都已有 `package-lock.json`**（agents-dashboard 71945 B、frontend 53578 B）→ 具备「可 pin 可锁」的前提。
- `agents-dashboard` 本地 `typescript@5.9.3`、`next@16.3.3`；CI 已使用 `npm ci --ignore-scripts`（`ci.yml` 第 73–77 行注释明确写着「当前依赖树无任何 install script，此旗标为显式拒绝安装期脚本的无害空操作」）→ **本仓库已有「拒绝安装期脚本」的既定文化，核查项 2 在本项目不是形式主义**。
- `.venv` 内已存在 `pyyaml 6.0.3`（但属传递依赖，非本仓库声明依赖，见 §5）。
- 仓库内 `.ps1` 文件仅 **7 个**（排除 `node_modules`/`.venv`）：`scripts/` 下 `github-pr.ps1`、`register-scheduled-tasks.ps1`、`setup-env.ps1`、`start-agents-dashboard.ps1`、`start-backend.ps1`、`start-frontend.ps1`、`start-streamlit.ps1`。
- 仓库内 YAML 文件 **881 个**（排除 `node_modules`/`.venv`/`.next`/`.git`）：其中 `.agents/notes/**` 占 **827 个**（形如 `*.i18n.yaml` 的**双语文档一致性记录**，典型内容 6 行，如 `README.md: <blob-hash>`）、`paper-qa/tests` 46 个（vendored 上游）、`paper-qa/packages` 6 个、`.github/workflows/ci.yml` **1 个**、`paper-qa/.pre-commit-config.yaml` 1 个（vendored）。

---

## 1. `ruff`（Python linter/formatter，含 pydocstyle `D` 规则）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **发现 1 条**：`CVE-2025-62518`（Fedora 为 `ruff 0.14.2` 发安全更新，标题分别为「Fedora 42: ruff 0.14.2 Important Parser Fix CVE-2025-62518 Advisory」与「Fedora 41: ruff 0.14.2 Security Update for CVE-2025-62518 Released」）。该 CVE 同时命中 Rust crate `quote-use`（「Fedora 41: rust-quote-use Critical CVE-2025-62518 Desynchronization Issue」）→ 判断为 ruff 的 Rust 依赖链问题，**修复版 ≤ 0.14.2**。NVD CVSS 分值、受影响版本区间、`ruff` 自身是否算受影响组件：`未核实（原因：无法打开 linuxsecurity / OSV / NVD 页面；web_fetch 被阻断）`。**OSV API 未查询**（见 §0）。 |
| 2 | 安装脚本与构建期执行 | 旁证表明 PyPI 发布 **wheel 内含预编译二进制**，正常情况下安装期不触发本地编译：搜索命中 `astral-sh/ruff` issue **#26362「No ruff binary in 0.15.19 wheel」**（即「wheel 里应该有二进制」是预期行为，缺了才是 bug）。**wheel 是否覆盖 Windows/amd64、是否存在 sdist-only 平台、`pip install` 是否跑 `setup.py`：`未核实（原因：无法读取 PyPI JSON 的 `urls[].packagetype` 字段）`**。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开 astral.sh 官方文档；搜索未命中任何 ruff telemetry/联网行为页面——这既不能证明有，也不能证明无）`。**必须补做断网实跑**（§2.4 核查项 3 明文要求「离线运行验证」）。 |
| 4 | 许可证 | `未核实（原因：未取得 LICENSE 原文）`。旁证：Debian main 收录 `ruff`（存在 `ruff_0.0.291+dfsg1-4_copyright`，`+dfsg1` 后缀通常意味着已剥离非自由内容）→ 属 DFSG 自由许可。**SPDX 标识待确认**（社区普遍认知为 MIT，本次未取得一手证据，不作断言）。 |
| 5 | 维护活跃度与来源 | 官方仓库：`github.com/astral-sh/ruff`（Astral）。**版本密度极高**：本次搜索窗口内即命中 `0.15.4` / `0.15.15` / `0.15.21` / `0.16.0`（有官方博客 `astral.sh/blog/ruff-v0.16.0`）/ `0.16.6` / `0.16.7` / **`0.16.8`**（renovate 与 dependabot 均已在 2026 年内升到 0.16.8；Fedora fc45 亦已有 `ruff-0.16.8-1.fc45` 构建）→ **本次可确认的最新稳定版为 `0.16.8`**。最近发布日期、月度下载量：`未核实（原因：无法读取 PyPI JSON `upload_time` 与 pypistats）`。 |
| 6 | 最小化 | **无法用既有机制替代**。`verify_*.py` 能断言「某个 docstring 存在/某 JSON 有某字段」，但 pydocstyle `D` 规则（D205/D400/D401 等）需要对 Python **AST + docstring 语法**做系统化判定，自研等于重写一个 linter。ruff 是单二进制、零运行期依赖、可 pin，属「引入即收敛」的少数派工具。 |

**判定：引入但需用户批准（建议 pin `ruff==0.16.8`）**——理由：核查项 **1 未按 §2.4 指定方式完成**（OSV API 不可达），仅凭搜索引擎命中证明「0.16.8 远高于已知修复版 0.14.2」；核查项 3/4 亦为 `未核实`。批准前建议在**联网环境**补跑 `pip-audit` / OSV 查询并把原始输出记入 Sprint §9。

---

## 2. `eslint`（+ react plugin，用于 JS/JSX）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **发现 2 条，均落在 eslint 依赖生态上**：<br>① `CVE-2025-50537` —— 「eslint: Denial of Service via stack overflow when serializing objects with circular references」；IBM 安全公告明确写「uses eslint-9.17.0 … which is vulnerable to CVE-2025-50537」→ **9.17.0 受影响**；命中页显示 CVSS **5.5（medium）**（feedly 标题「CVE-2025-50537 / openjsf / 5.5 / exploit + patch」）。**修复版本号：`未核实`**。<br>② `GHSA-xffm-g5w8-qvg7` —— 「**@eslint/plugin-kit** is vulnerable to Regular Expression Denial of Service attacks through ConfigCommentParser」。`vercel/turborepo` PR **#11705** 标题即为「fix: Upgrade eslint to v10 to resolve @eslint/plugin-kit ReDoS vulnerability」→ **升级到 eslint v10 即消除**；`eslint` 自身版本区间与 GHSA severity：`未核实（原因：无法打开 osv.dev / GitHub Advisory 页面）`。<br>**若 pin `eslint@10.11.0`（> v10.0.0），上述两条均在射程之外。** |
| 2 | 安装脚本与构建期执行 | 三个 npm 包的 `package.json` 的 `scripts` 字段（是否含 `postinstall`/`install`/`preinstall`）**`未核实（原因：无法读取 registry.npmjs.org）`**。缓解：本仓库 CI 已对前端使用 `npm ci --ignore-scripts`（`ci.yml` 第 73–77 行），**建议 eslint 一并纳入该旗标**；若某包真的依赖安装期脚本，`--ignore-scripts` 会立刻暴露为运行失败，属 fail-closed。补充环境事实：搜索结果命中「**npm v12 disables auto-run install scripts and remote dependency paths by default**」→ 新版 npm 默认不再自动执行安装脚本，风险面进一步收窄（该结论来自第三方页面标题，`未核实` 官方 changelog）。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开 eslint.org 文档）`。搜索命中「Eslint Privacy Analysis — Data Collection & Tracking \| Nerq」（第三方隐私分析页）与 `eslint/eslint` issue **#10602「Feature: Collect Metrics for most common rule setting」**（说明「收集使用指标」在该项目是**被讨论过的 feature request**，而非既有行为）→ **倾向为无遥测，但不构成证据**。必须补做断网实跑。 |
| 4 | 许可证 | `未核实（原因：无法读取 npm manifest 的 `license` 字段与 LICENSE 文件）`。旁证：搜索命中 `eslint/eslint` Discussion **#17064「License references not clear」**——连上游社区都在讨论许可证引用表述不清，**本项目应在引入前把 LICENSE 原文归档留证**。 |
| 5 | 维护活跃度与来源 | 官方仓库：`github.com/eslint/eslint`；官方博客：`eslint.org/blog`。**最新版本确认到 `v10.11.0`**（官方博客 URL 落在 `2026/09/`，GitHub Release 页 `releases/tag/v10.11.0`）；`v10.0.0` 发布于 **2026-02**（`eslint.org/blog/2026/02/eslint-v10.0.0-released/`）。npm 周下载量：`未核实（原因：无法读取 registry.npmjs.org）`；旁证命中 `packages.ecosyste.ms/registries/npmjs.org/packages/eslint`、`getcommit.dev/blog/25-npm-packages-scored/`（后者是对 25 个头部 npm 包的供应链风险打分）。**react plugin 的版本/维护/许可证：本次未单独核查 → `未核实`。** |
| 6 | 最小化 | **部分可替代、部分不可**。既有 `verify/gui_check*.mjs` 是**运行期 GUI 断言**（Playwright 式点击/截图），不覆盖「未使用变量/未定义变量/JSX 可访问性」这类静态问题——静态可读性闸门确实没有既有等价物。**但**：<br>① `agents-dashboard` 用 Next 16，历史上 `next lint` 提供内置 ESLint；Next 16 是否仍提供、是否已移除：`未核实`（本地 `node_modules/next` 存在，但本次为只读范围核查，未展开 `next/dist/docs`）。<br>② React 17+ 的 JSX 自动运行时使 `react/react-in-jsx-scope` 一类经典规则失效，**`eslint-plugin-react` 的边际价值需要单独论证**；若不引入它，`@eslint/js` recommended + `eslint-plugin-react-hooks` 可能已覆盖主要风险。 |

**判定：引入但需用户批准（建议 pin `eslint@10.11.0`）**——需批准的原因有两条：**(a)** 核查项 1 未按 §2.4 指定方式执行，且该生态本次**确实命中了 CISA KEV 级别的供应链事件**（见 §3 的 `CVE-2025-54313`，受影响包正是 ESLint 插件生态）；**(b)** react plugin 的必要性未论证，存在最小化空间。批准前须先确认：pin 版本、`--ignore-scripts`、以及是否真的需要 `eslint-plugin-react`。

---

## 3. `prettier`（`--check`，JS/JSX/TS/TSX）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **本次最重要的发现，且已被武器化**：`CVE-2025-54313` —— 「**eslint-config-prettier, eslint-plugin-prettier, synckit, @pkgr/core, napi-postinstall** have embedded malicious code」，命中页标注 **CVSS 7.5（high）**、EPSS 11.62%。**已被列入 CISA KEV**：CISA 公告页「CISA Adds Four Known Exploited Vulnerabilities to Catalog」（2026-01-22），SecurityAffairs 标题明确点名「**Prettier eslint-config-prettier** … flaws to its Known Exploited Vulnerabilities catalog」；法方 CERT 亦发出「Vulnérabilité dans Prettier」告警。<br>**关键区分（必须写清）**：被投毒的是 **prettier 的 ESLint 集成插件生态**（`eslint-config-prettier` / `eslint-plugin-prettier`）及其共享依赖（`synckit` / `@pkgr/core` / `napi-postinstall`），**不是 `prettier` 核心包本身**。本次未取得任何指向 `prettier` 核心包的 advisory → 「prettier 核心无已知漏洞」这句话**不成立**（因为 OSV 未查），只能说**未命中**。受影响版本区间与修复版本：`未核实（原因：无法打开 dependabot/GHSA/CISA 正文）`。 |
| 2 | 安装脚本与构建期执行 | `未核实（原因：无法读取 registry.npmjs.org 的 manifest）`。**注意**：上一条 CVE 的受影响包之一正是 `napi-postinstall`（npm 生态的安装期脚本执行器），这直接说明**「prettier 相关生态」的安装期脚本面是被真实利用过的攻击面**。缓解措施同 §2：`npm ci --ignore-scripts`。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开 prettier.io 文档）`。搜索命中繁体中文页「Visual Studio 离线安装 Prettier 完整指南」——说明「离线使用 prettier」是被实践过的场景，但**不是官方离线声明**。必须补做断网实跑。 |
| 4 | 许可证 | `未核实（原因：未能读取 npm manifest 的 `license` 字段）`。 |
| 5 | 维护活跃度与来源 | 官方站点/仓库：`prettier.io`、`github.com/prettier/prettier`。**最新版本确认到 `3.9.1`**（多处 dependabot bump「prettier from 3.8.4 to 3.9.1」与 forgejo-helm「update dependency prettier to v3.9.1」）；**`3.9.0` 发布于 2026-06-27**（官方博客 URL `prettier.io/blog/2026/06/27/3.9.0`）。npm 周下载量：`未核实`。<br>**额外的供应链风险信号**：搜索命中「compromised-packages-check … July 6–7 2026 multi-campaign npm batch (163 packages) \| **Logger/chalk/prettier typosquat cluster (33 packages)**」→ 2026 年 7 月存在**针对 prettier 的仿冒包集群**。这不是 prettier 自身的问题，但**要求本项目把包名与 registry 来源钉死**（`prettier` 而非任何近似名）。 |
| 6 | 最小化 | **无既有等价机制**。`ruff format` 覆盖 Python，`verify_*.py` 覆盖断言，但 JS/JSX/TS/TSX 的**统一格式化**在本仓库完全空白（`npm run build` 只编译不格式化）。若「readability lint gates」要求格式化一致性，prettier 是当前唯一现实选择。反之，若闸门只要求「可读性规则」而**不要求统一格式化**，则 prettier 可整体砍掉——**这是本项目需要先回答的问题**。 |

**判定：引入但需用户批准（建议 pin `prettier@3.9.1`）**——需批准的原因：核查项 1 未按 OSV 执行，且 prettier 生态在 2026 年 1 月刚发生被 CISA KEV 收录的供应链事件、7 月又出现 typosquat 集群。**批准时必须附带两条硬约束**：① **禁止引入 `eslint-config-prettier` 与 `eslint-plugin-prettier`**（`CVE-2025-54313` 直接命中，`eslint --fix` 与 prettier 的职责边界靠人工约定即可，不值得为此引入 KEV 级风险面）；② 安装一律 `npm ci --ignore-scripts` + lock 文件 pin。

---

## 4. `@typescript-eslint`（parser + plugin，用于 TS/TSX）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **未发现 8.x 现网公告**。搜索只命中 `security.snyk.io` 的**历史版本页**（`@typescript-eslint/parser` **4.31.3-alpha.2**、**4.22.1**）——即 Snyk 有该包的条目但命中的都是远古版本，与本次要 pin 的 8.70.x 无关。**OSV API 未查询**。→ 结论只能写：**未命中，不等于无漏洞**。`未核实（原因：OSV/GHSA 未查，Snyk 页面未打开）`。 |
| 2 | 安装脚本与构建期执行 | `未核实（原因：无法读取 registry.npmjs.org）`。已知该 monorepo 以纯 JS/TS 实现为主、通过 `typescript-estree` 调用 TypeScript 编译器 API，通常不需要 node-gyp——**这是先验，不是本次证据**。缓解同 §2（`--ignore-scripts`）。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开 typescript-eslint.io 文档）`。必须补做断网实跑。 |
| 4 | 许可证 | `未核实（原因：未取得 LICENSE 原文）`。 |
| 5 | 维护活跃度与来源 | 官方仓库：`github.com/typescript-eslint/typescript-eslint`（monorepo，同时发布 `@typescript-eslint/parser` 与 `@typescript-eslint/eslint-plugin`）。**最新版本确认到 `v8.70.1`**（GitHub Release 页 `releases/tag/v8.70.1`）；其他命中版本：`8.66.0`（dependabot bump）、`8.57.2`（Sonatype）。仓库维护活跃度旁证：`deps.dev/project/github/typescript-eslint%2Ftypescript-eslint`、`releasealert.dev` 的 parser 发布订阅源。最近发布日期与周下载量：`未核实`。<br>**未核实项（会影响能否引入）**：`typescript-eslint` 对 TypeScript 版本有**支持区间**约束（官方页 `typescript-eslint.io/users/dependency-versions/` 存在，但正文未取得）；本机 `agents-dashboard` 锁定 `typescript@5.9.3`，**8.70.x 是否支持 TS 5.9 未核实**。 |
| 6 | 最小化 | **有部分既有替代**。本仓库已锁定 `typescript@5.9.3`（`agents-dashboard`），**`tsc --noEmit` 本身即可覆盖大量「可读性/正确性」问题**（未使用局部变量需 `noUnusedLocals`、隐式 any 需 `noImplicitAny`、strict 系列），而这是**已存在、零新增依赖**的能力。`@typescript-eslint` 的增量价值在于**与 ESLint 共用一套报告/忽略机制**（若同时引入 eslint），以及 `no-floating-promises` 等**类型感知规则**（这类规则 `tsc` 给不了，是它真正的不可替代处）。<br>→ **最小化结论：若只是为了「TS 也能被 lint」，先检查 `agents-dashboard/tsconfig.json` 的 strict 开关是否已开满；只有在明确需要类型感知规则（如 `no-floating-promises`、`no-misused-promises`）时，引入才成立。** |

**判定：引入但需用户批准（建议 pin `@typescript-eslint/parser@8.70.1` + `@typescript-eslint/eslint-plugin@8.70.1`，两者必须同版本同源）**——需批准的原因：**(a)** 核查项 1 未按规程执行；**(b)** 与本地 `typescript@5.9.3` 的兼容区间未核实，存在引入即报错的风险；**(c)** 其价值高度依赖「是否真的需要类型感知规则」，否则 `tsc --noEmit` + strict 已足够，属最小化可直接砍掉的一项。另外它**逻辑上依赖 §2 的 eslint 先被批准**（parser 无 ESLint 宿主无意义），应作为**同一批次捆绑决策**。

---

## 5. `yamllint`（YAML）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **未命中任何 advisory**。搜索只命中 Snyk 的**历史版本页**（`yamllint 1.27.0`、`yamllint 1.8.2`）与包主页 `security.snyk.io/package/pip/yamllint`。**OSV API 未查询** → `未核实（原因：OSV 不可达；Snyk 页面未打开）`。**未命中 ≠ 无漏洞。** |
| 2 | 安装脚本与构建期执行 | `未核实（原因：无法读取 PyPI JSON 的 `urls[].packagetype`）`。先验：yamllint 是**纯 Python** 包，通常同时提供 wheel 与 sdist，不涉及编译工具链——**先验，非本次证据**。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开官方文档）`。必须补做断网实跑。 |
| 4 | 许可证 | `未核实（原因：未取得 LICENSE 原文）`。**旁证较强**：Debian main 收录 `yamllint`（`tracker.debian.org/.../copyright-1.37.1-1` 与 `changelog-1.38.0-1` 均存在），NetBSD pkgsrc 亦有 `textproc/py-yamllint` 提交（2026-01-13）→ 属 DFSG 自由许可。**但社区普遍认知的 GPL-3.0 未取得一手确认；若确为 GPL-3.0，作为开发期工具（不随产物分发）通常兼容，但需按 §2.4 核查项 4「与本项目分发兼容性」由用户确认。** |
| 5 | 维护活跃度与来源 | 官方仓库：`github.com/adrienverge/yamllint`。**最新版本确认到 `1.38.0`**（Debian unstable `yamllint (1.38.0-1)` changelog、Fedora `yamllint-1.38.0-1.fc44`、多处 dependabot「bump yamllint from 1.37.1 to 1.38.0」、`pyspect.com/package-release/yamllint/1.38.0`）；**`1.37.1` 仍是若干发行版主线版本**（Fedora 42 RPM、Debian `yamllint_1.37.1-1_copyright`）→ 说明 1.38.0 是较新的发布。最近发布日期与月下载量：`未核实`。 |
| 6 | 最小化 | **本次六个候选中最小化证据最充分的一个，建议不引入。** 理由三条：<br>① **本仓库自己的 YAML 只有 `./github/workflows/ci.yml` 一个文件**（881 个命中里 827 个是 `.agents/notes/**` 的双语文档一致性记录，46+6 个在 vendored `paper-qa/` 内）。<br>② **那 827 个 `.i18n.yaml` 是「记录」而非「手写配置」**：实测 `README.i18n.yaml` 仅 6 行，形如 `README.md: <git-blob-sha1>`，且文件头注释直接写明由 `pnpm run verify-translation-pairing --write …` 生成 → **对生成物做风格 lint 的收益极低**（真出问题也是生成器该修）。<br>③ **既有机制已覆盖核心诉求**：`.venv` 内已有 `pyyaml 6.0.3`（虽是传递依赖），一个 ~50 行的 `verify/verify_yaml.py` 用 `yaml.safe_load` + 形状断言，即可覆盖「语法合法性」与「i18n 记录的 key/value 形状」，**与 §2.4 核查项 6 的示例（`json`/schema 校验）逐字对应**。<br>**唯一反例**：yamllint 能查 `syntax`+`truthy`+`indentation`+`line-length` 这类**风格**问题，自研脚本查不了（要查就得重写规则集）。若用户认为 `ci.yml` 一个文件也值得风格闸门，可只对该文件引入——但那仍是「一个文件 vs 一个新依赖」的取舍。 |

**判定：建议不引入（用既有机制：自研 `verify/verify_yaml.py` + 既有 PyYAML/schema 校验）**——若用户坚持引入风格闸门，退让方案是 **建议替换为「自研脚本 + 仅对 `ci.yml` 生效」**；确需引入时 pin `yamllint==1.38.0`，并须先补齐核查项 1/3/4。

---

## 6. `PSScriptAnalyzer`（PowerShell 模块，PowerShell Gallery）

| # | 核查项 | 结论 |
|---|---|---|
| 1 | 已知漏洞 | **存在一个强信号但内容未取得**：搜索命中 ReversingLabs Spectra Assure 页面「**Vulnerabilities - PSScriptAnalyzer@1.19.0**」（`secure.software/psgallery/packages/psscriptanalyzer/vulnerabilities/1.19.0`）→ 表明**至少对 1.19.0 有已登记的漏洞条目**；同站另有 PSScriptAnalyzer 的 `dependencies` 与 `behaviors` 页面（说明该站做了依赖与行为画像）。**条目编号、severity、影响区间、是否影响 1.25.0：`未核实（原因：无法打开页面；OSV API 不可达）`。** 除此之外未命中任何 PSScriptAnalyzer 的 CVE/GHSA。 |
| 2 | 安装脚本与构建期执行 | **分发方式**：以 PowerShell 模块形式经 **PowerShell Gallery（PSGallery）** 分发，标准安装方式为 `Install-Module PSScriptAnalyzer`（搜索旁证：`actions/runner-images` issue **#2659「Add PSScriptAnalyzer Powershell module」**，即 CI 镜像层面对该模块的安装讨论）。<br>**`Install-Module` 是否执行任意代码**——机制层面需分清两件事：`Install-Module` 做的是 **NuGet 包下载+解包+落盘**，本身**不执行**模块代码；**真正的代码执行发生在 `Import-Module`（加载 `.psm1`）时**。因此「安装期任意代码」风险主要取决于 PSGallery 上游包内容与签名状态。**该包是否含安装期脚本、是否由 Microsoft 签名、包内容清单：`未核实（原因：无法打开 powershellgallery.com 包页）`。**<br>**缓解建议**：引入时用 `Save-Module` 落盘 + 人工审阅后再 `Import-Module`（而非直接 `Install-Module` 后立即导入），并把具体版本号写进文档以复现。 |
| 3 | 数据外发 / 遥测 | `未核实（原因：无法打开 Microsoft Learn 文档）`。搜索命中 `github.com/PowerShell/PowerShell` PR **#11514「Adding PowerShell Editor Services and PSScriptAnalyzer to tracked modules」**（属 PowerShell 自身的模块追踪机制），**不能**据此推断遥测。必须补做断网实跑（分析 7 个 `.ps1` 时断网）。 |
| 4 | 许可证 | `未核实（原因：未取得 LICENSE 原文）`。旁证：包归属 **`PowerShell` GitHub 组织（微软官方）**，搜索命中 `StartAutomating/PSScriptAnalyzer` 镜像的 `build.psm1` 含「Copyright (c) Microsoft Corporation. All rights reserved.」→ **Microsoft 版权声明确认**；但**「All rights reserved」不等于 MIT 授权**，SPDX 标识（社区普遍认知 MIT）**未取得一手确认**。 |
| 5 | 维护活跃度与来源 | 官方仓库：**`github.com/PowerShell/PSScriptAnalyzer`**（微软 PowerShell 官方组织）。**最新版本确认到 `1.25.0`**（`newreleases.io/project/github/PowerShell/PSScriptAnalyzer/release/1.25.0`）；官方 CHANGELOG 存在于 `raw.githubusercontent.com/PowerShell/PSScriptAnalyzer/main/CHANGELOG.MD`；官方文档 `learn.microsoft.com/.../psscriptanalyzer/whats-new-in-pssa`（含多语言版本，说明属微软正式文档化产品）。**1.1.1 是历史版本**（命中旧版 PSGallery 前门 URL）。最近发布日期、PSGallery 下载量：`未核实`。 |
| 6 | 最小化 | **反方证据很强**：本仓库 `.ps1` 仅 **7 个**，且全部在 `scripts/` 下、多为几十行以内的启动/注册脚本（`github-pr.ps1` 5156 B、`register-scheduled-tasks.ps1` 3592 B 为最大两个）；**为 7 个短脚本引入一整个 PowerShell 模块，是本次六个候选中「投入/收益比」最差的一个**。<br>**正方证据**：既有机制在本项目**偏弱**——`verify_*.py` 全部是 Python 断言，**对 PowerShell 脚本零覆盖**；`git diff` 式的人工 review 是当前唯一手段。PSScriptAnalyzer 的 `PSUseApprovedVerbs`、`PSAvoidUsingWriteHost`、`PSUseShouldProcessForStateChangingFunctions` 等规则**确实提供了自研脚本难以低成本复刻的领域知识**。<br>→ 结论：**不是「用既有机制即可解决」，而是「样本量太小，是否值得」需要用户拍板**。 |

**判定：引入但需用户批准（建议 pin `PSScriptAnalyzer@1.25.0`）**——需批准的原因三条：**(a)** 核查项 1 存在一条**未能读取内容的 PSScriptAnalyzer@1.19.0 漏洞登记**，必须先确认它是否波及 1.25.0；**(b)** 核查项 4 的许可证 SPDX 未取得一手证据（微软官方仓库旁证强，但未闭环）；**(c)** 仅 7 个 `.ps1`，需用户确认「为 7 个脚本引入一个模块」是否值得。批准后建议以 `Save-Module` 落盘审阅替代直接 `Install-Module`。

---

## 结论汇总表

| 包 | 建议 pin 版本 | 版本确认度 | 许可证 | 安装期脚本执行 | 离线可行 | 本次命中的漏洞 | 判定 |
|---|---|---|---|---|---|---|---|
| `ruff` | `0.16.8` | 版本号确认（多源）；**发布日期未核实** | `未核实`（旁证：Debian main 收录） | 预期 wheel 内含预编译二进制（旁证：issue #26362）；**未见本地编译要求** | `未核实`（需断网实跑） | `CVE-2025-62518`（Fedora「Important」，修复 ≤ 0.14.2，pin 版本远高于修复版） | **引入但需用户批准** |
| `eslint` | `10.11.0` | 版本号确认（官方博客 2026/09 + GitHub Release）；`v10.0.0`=2026-02 | `未核实` | `未核实`；**建议 `--ignore-scripts`** | `未核实`（需断网实跑） | `CVE-2025-50537`（CVSS 5.5 medium，9.17.0 受影响，修复版本未核实）；`GHSA-xffm-g5w8-qvg7`（`@eslint/plugin-kit` ReDoS，升级 v10 即消除） | **引入但需用户批准** |
| `prettier` | `3.9.1` | 版本号确认（多处 bump）；`3.9.0`=**2026-06-27** | `未核实` | `未核实`；**建议 `--ignore-scripts`** | `未核实`（需断网实跑） | **核心包未命中**；生态命中 `CVE-2025-54313`（**CVSS 7.5 high，已入 CISA KEV**，受影响包为 `eslint-config-prettier`/`eslint-plugin-prettier`/`synckit`/`@pkgr/core`/`napi-postinstall`）；2026-07 有 prettier typosquat 集群 | **引入但需用户批准**（附硬约束：不得引入 `eslint-config-prettier`/`eslint-plugin-prettier`） |
| `@typescript-eslint`（parser+plugin） | `8.70.1`（两者同版本） | 版本号确认（GitHub Release v8.70.1） | `未核实` | `未核实`；**建议 `--ignore-scripts`** | `未核实`（需断网实跑） | 未命中现网公告（仅 Snyk 4.x 历史页）→ **未核实，非「无漏洞」** | **引入但需用户批准**（且与 §2 eslint 捆绑决策） |
| `yamllint` | `1.38.0`（若坚持引入） | 版本号确认（Debian/Fedora/pyspect 多源） | `未核实`（旁证：Debian main 收录） | `未核实`（预期纯 Python wheel/sdist） | `未核实` | 未命中任何 advisory（仅 Snyk 1.27.0/1.8.2 历史页）→ **未核实** | **建议不引入（用既有机制）** |
| `PSScriptAnalyzer` | `1.25.0` | 版本号确认（GitHub Release 1.25.0） | `未核实`（旁证：微软官方 org；「All rights reserved」声明≠MIT 授权） | `Install-Module` 不执行代码，**`Import-Module` 才执行模块代码**；包内是否含安装脚本 `未核实` | `未核实`（需断网实跑） | 命中「PSScriptAnalyzer**@1.19.0** 漏洞页」存在性信号，**内容/编号/影响区间未核实** | **引入但需用户批准** |

**对本表的整体解读（重要）**：六个包**没有任何一个**完成了 §2.4 全部六项。差别只在「未完成的项有多关键」：`yamllint` 是**因最小化而主动建议不引入**（不依赖漏洞结论），其余五个的 blocker **一律是核查项 1 未按 OSV API 执行 + 核查项 3 未做断网实跑**。**按 §2.4「任一项不通过 → 拒绝引入或换等价替代」的字面要求，这五个现在都应处于「未通过」状态**；本文件把它们标为「引入但需用户批准」，是因为失败原因属于**核查手段缺失（环境阻断）而非发现了高风险**——`ruff`/`eslint`/`prettier` 三项还额外给出了「pin 该版本即可避开已命中漏洞」的正面证据。**最终解释权归用户。**

---

## 未核实项清单

### A. 因环境阻断而全包通用的未核实项（根因：`web_fetch` 全部失败，DNS 将目标域名解析到非公网 IP）

| # | 未核实内容 | 需要什么才能核实 |
|---|---|---|
| A1 | **所有包的 OSV / GHSA / CVE 完整清单**（§2.4 核查项 1 的规定动作） | 可联网环境下 `curl https://api.osv.dev/v1/query`（`{"package":{"name":"<pkg>","ecosystem":"PyPI\|npm"}}`）或 `pip-audit` / `npm audit`；原始输出记入 Sprint §9 |
| A2 | 所有包的 `upload_time` / `time`（**精确发布日期**） | PyPI JSON `releases[v][0].upload_time_iso_8601`；npm `registry.npmjs.org/<pkg>` 的 `time` 字段 |
| A3 | 所有包的**下载量**（PyPI 月下载 / npm 周下载 / PSGallery 下载） | `pypistats.org/api/packages/<pkg>/recent`；`api.npmjs.org/downloads/point/last-month/<pkg>`；PSGallery 包页 |
| A4 | 所有包的 **LICENSE 原文与 SPDX 标识**（`ruff`/`eslint`/`prettier`/`@typescript-eslint`/`yamllint`/`PSScriptAnalyzer`） | 各包仓库根目录 LICENSE 文件；npm manifest `license` 字段；PyPI `info.license` |
| A5 | 所有包的 **`postinstall`/`install` 脚本清单**（§2.4 核查项 2） | `registry.npmjs.org/<pkg>/<ver>` 的 `scripts` 字段；或安装后审阅 `node_modules/<pkg>/package.json` |
| A6 | 所有包的**遥测/联网行为**（§2.4 核查项 3 前半） | 官方文档 privacy/telemetry 章节 + **断网实跑**（§2.4 明文规定的验证方式，本次无法执行） |
| A7 | `@typescript-eslint@8.70.1` 与本地 `typescript@5.9.3` 的**兼容区间** | `typescript-eslint.io/users/dependency-versions/` 正文，或本地装后实跑 |

### B. 单包专属未核实项

| 包 | 未核实内容 | 需要什么才能核实 |
|---|---|---|
| `ruff` | `CVE-2025-62518` 的 NVD CVSS 分值、受影响版本区间、**ruff 是否算「受影响组件」还是仅传递依赖受影响** | linuxsecurity Fedora advisory 正文 / NVD / OSV |
| `ruff` | PyPI 上是否存在 **sdist-only 场景**、Windows amd64 wheel 覆盖情况 | PyPI JSON `urls[]` 的 `packagetype` 与 `filename` |
| `eslint` | `CVE-2025-50537` 的**修复版本号**（只知道 9.17.0 受影响、v10 已修复 ReDoS 另一条） | GHSA/NVD 正文 |
| `eslint` | `eslint-plugin-react` 的版本/维护活跃度/许可证/安装脚本 | npm registry + 仓库页 |
| `eslint` | **Next 16 是否仍内置 `next lint`**（若有，则可不引入 eslint 或减少插件） | 本地 `agents-dashboard/node_modules/next/dist/docs/` 或 nextjs.org 文档 |
| `prettier` | `CVE-2025-54313` 的**具体受影响版本区间与修复版本**（决定「项目里是否可能间接引入」） | dependabot/GHSA/CISA KEV 正文 |
| `prettier` | `prettier` **核心包**是否存在任何 advisory（本次仅知「未命中」） | OSV API |
| `PSScriptAnalyzer` | 「PSScriptAnalyzer**@1.19.0** 漏洞」的**条目编号 / severity / 是否影响 1.25.0** | `secure.software/psgallery/packages/psscriptanalyzer/vulnerabilities/1.19.0` 正文 |
| `PSScriptAnalyzer` | PSGallery 包的**签名状态与包内容清单** | PSGallery 包页 / `Save-Module` 后本地解包审阅 |
| `yamllint` | 若用户推翻「不引入」结论：License SPDX（疑为 GPL-3.0，**未确认**）与是否影响分发 | 仓库 LICENSE / Debian copyright 文件正文 |
| 全部 | 「2026-07 npm typosquat 集群」与「Logger/chalk/prettier typosquat cluster」的**权威来源** | GitHub Security Advisory / npm 官方公告正文 |

### C. 需要用户决策（本文件无法代替）

1. **是否接受「核查项 1 未按 OSV API 执行」的前提下放行**——若不可接受，则六个包**全部暂缓**，等联网环境补跑。
2. **是否需要 prettier**：闸门要的是「可读性规则」还是「统一格式化」？若只是前者，prettier 可整体砍掉。
3. **是否需要 `eslint-plugin-react`**：React 17+ 自动 JSX 运行时下，其经典规则多数失效，最小化空间待确认。
4. **`@typescript-eslint` 的价值锚点**：若不需要类型感知规则（`no-floating-promises` 等），改用既有 `tsc --noEmit` + tsconfig strict 即可，零新增依赖。
5. **7 个 `.ps1` 是否值得引入整个 `PSScriptAnalyzer` 模块**。
6. **`yamllint` 的最终取舍**：接受「自研 `verify/verify_yaml.py`」，还是坚持对 `ci.yml` 单文件做风格闸门。

---

## 证据来源

**本次实际执行的核查手段**：`web_search`（唯一成功通道）。以下 URL 均为搜索结果命中的页面；**未打开正文**，仅标题与 URL 可核验。

**目标源（本次尝试并失败，用于说明 §2.4 核查项 1/2/5 无法按规程执行）**

- `https://pypi.org/pypi/ruff/json` —— 失败：`resolves to a non-public IP address`
- `https://pypi.org/pypi/yamllint/json` —— 失败：同上
- `https://registry.npmjs.org/eslint/latest` —— 失败：`resolves to a non-public IP address`
- `https://api.osv.dev/v1/query` —— 失败：`resolves to a non-public IP address`
- `https://osv.dev/list?q=ruff&ecosystem=PyPI` —— 失败：同上
- `https://github.com/astral-sh/ruff/releases` —— 失败：同上
- `https://raw.githubusercontent.com/astral-sh/ruff/main/CHANGELOG.md` —— 失败：同上
- `https://eslint.org/blog/2026/09/eslint-v10.11.0-released/` —— 失败：同上
- `https://www.powershellgallery.com/packages/PSScriptAnalyzer` —— 失败：同上

**`ruff`**

- https://newreleases.io/project/pypi/ruff/release/0.16.6
- https://newreleases.io/project/github/astral-sh/ruff/release/0.16.7
- https://astral.sh/blog/ruff-v0.16.0
- https://github.com/astral-sh/ruff/issues/26362 （No ruff binary in 0.15.19 wheel）
- https://linuxsecurity.com/advisories/fedora/fedora-42-ruff-2025-a77c1f005b-d4u4kmgam3wr （CVE-2025-62518 / Important）
- https://linuxsecurity.com/advisories/fedora/fedora-41-ruff-2025-43a0bff5ea-emphylh3hmh1
- https://linuxsecurity.com/advisories/fedora/fedora-41-rust-quote-use-2025-43a0bff5ea-kmj6elkazkhm （rust-quote-use Critical）
- https://openkoji.iscas.ac.cn/koji/buildinfo?buildID=238921 （ruff-0.16.8-1.fc45）
- https://metadata.ftp-master.debian.org/changelogs//main/r/ruff/ruff_0.0.291+dfsg1-4_copyright
- https://pypistats.org/packages/ruff

**`eslint`**

- https://eslint.org/blog/2026/09/eslint-v10.11.0-released/
- https://github.com/eslint/eslint/releases/tag/v10.11.0
- https://eslint.org/blog/2026/02/eslint-v10.0.0-released/
- https://app.opencve.io/cve/CVE-2025-50537
- https://www.ibm.com/support/pages/node/7262741 （eslint-9.17.0 vulnerable to CVE-2025-50537）
- https://ubuntu.com/security/CVE-2025-50537
- https://feedly.com/cve/CVE-2025-50537 （CVSS 5.5）
- https://dbugs.ptsecurity.com/vulnerability/PT-2026-4771
- https://dependabot.ecosyste.ms/advisories/GHSA-xffm-g5w8-qvg7 （@eslint/plugin-kit ReDoS）
- https://osv.dev/vulnerability/GHSA-xffm-g5w8-qvg7
- https://github.com/vercel/turborepo/pull/11705 （upgrade eslint to v10 以消除该 ReDoS）
- https://github.com/eslint/eslint/discussions/17064 （License references not clear）
- https://github.com/eslint/eslint/issues/10602 （Collect Metrics feature request）
- https://nerq.ai/safe/eslint/privacy
- https://packages.ecosyste.ms/registries/npmjs.org/packages/eslint
- https://security.snyk.io/package/npm/eslint
- https://getcommit.dev/blog/25-npm-packages-scored/

**`prettier`**

- https://prettier.io/blog/2026/06/27/3.9.0
- https://dependabot.ecosyste.ms/hosts/GitHub/repositories/astiskala%2Flunch-buddy/issues/192 （3.8.4 → 3.9.1）
- https://code.forgejo.org/forgejo-helm/forgejo-helm/pulls/1615 （update prettier to v3.9.1）
- https://dependabot.ecosyste.ms/advisories/CVE-2025-54313 （eslint-config-prettier / eslint-plugin-prettier / synckit / @pkgr/core / napi-postinstall 内嵌恶意代码）
- https://cvemate.com/vulnerability/CVE-2025-54313 （CVSS 7.5 / EPSS 11.62%）
- https://www.cisa.gov/news-events/alerts/2026/01/22/cisa-adds-four-known-exploited-vulnerabilities-catalog （2026-01-22 加入 KEV）
- https://securityaffairs.com/187241/security/u-s-cisa-adds-prettier-eslint-config-prettier-vite-vitejs-versa-concerto-sd-wan-orchestration-platform-and-synacor-zimbra-collaboration-suite-flaws-to-its-known-exploited-vulnerabilities-catal.html
- https://www.cyber-reunion.fr/alertes-securite/vulnerabilite-dans-prettier/
- https://vulnerability.circl.lu/known-exploited-vulnerabilities-catalog/76b72db4-4d4f-4703-8cbb-155d34ad7cd5
- https://github.com/jaschadub/compromised-packages-check/blob/main/README.md （2026-07 typosquat 集群，含 prettier cluster）
- https://security.snyk.io/package/npm/%252540kurtinatlanta%25252Fprettier
- https://www.pkgpulse.com/packages/prettier

**`@typescript-eslint`**

- https://github.com/typescript-eslint/typescript-eslint/releases/tag/v8.70.1
- https://releasealert.dev/feeds/npmjs/@typescript-eslint/parser
- https://typescript-eslint.io/users/dependency-versions/
- https://deps.dev/project/github/typescript-eslint%2Ftypescript-eslint
- https://security.snyk.io/package/npm/%40typescript-eslint%2fparser/4.22.1
- https://security.snyk.io/package/npm/%40typescript-eslint%2fparser/4.31.3-alpha.2
- https://guide.sonatype.com/component/maven/org.mvnpm.at.typescript-eslint%3Atypes/8.57.2/versions

**`yamllint`**

- https://tracker.debian.org/media/packages/y/yamllint/changelog-1.38.0-1
- https://tracker.debian.org/media/packages/y/yamllint/copyright-1.37.1-1
- https://metadata.ftp-master.debian.org/changelogs//main/y/yamllint/yamllint_1.37.1-1_copyright
- https://openkoji.iscas.ac.cn/koji/buildinfo?buildID=211948 （yamllint-1.38.0-1.fc44）
- https://pyspect.com/package-release/yamllint/1.38.0
- https://github.com/crytic/slither/pull/2945
- https://github.com/esphome/esphome/pull/13192
- https://mail-index.NetBSD.org/pkgsrc-changes/2026/01/13/msg337974.html
- https://security.snyk.io/package/pip/yamllint
- https://security.snyk.io/package/pip/yamllint/1.27.0
- https://github.com/Jayman2000/yamllint-pr/blob/master/pyproject.toml

**`PSScriptAnalyzer`**

- https://newreleases.io/project/github/PowerShell/PSScriptAnalyzer/release/1.25.0
- https://raw.githubusercontent.com/PowerShell/PSScriptAnalyzer/main/CHANGELOG.MD
- https://learn.microsoft.com/en-us/powershell/utility-modules/psscriptanalyzer/whats-new-in-pssa?view=ps-modules
- https://learn.microsoft.com/en-us/powershell/utility-modules/psscriptanalyzer/overview?view=ps-modules
- https://secure.software/psgallery/packages/psscriptanalyzer/vulnerabilities/1.19.0
- https://secure.software/psgallery/packages/psscriptanalyzer/dependencies
- https://secure.software/psgallery/packages/psscriptanalyzer/behaviors
- https://github.com/actions/runner-images/issues/2659
- https://github.com/PowerShell/PowerShell/pull/11514
- https://github.com/StartAutomating/PSScriptAnalyzer/blob/master/build.psm1
- https://frontdoor-powershellgallery-cthqd0epb9c7c8fe.z01.azurefd.net/packages/PSScriptAnalyzer/1.1.1

**环境/生态旁证**

- https://mallory.ai/stories/019eb326-b344-77d9-8159-b366dcf81835 （npm v12 默认禁用自动安装脚本）
- https://docs.skpr.io/changelog/2025-09-18-npm-ignore-scripts/
- https://osv.dev/vulnerability/MAL-2026-5470 （OSV 恶意包条目存在性信号，归属包名未核实）

**本仓库内部证据（本地只读检查，非网络来源）**

- `docs/iteration/sprint/2026-09-21-governance-batch-plan.MD` §2.4 规则原文与核查表
- `.github/workflows/ci.yml`（`npm ci --ignore-scripts`、offline tier 闸门）
- `agents-dashboard/package.json` + `package-lock.json`、`paper-qa-script/reactflow-paperqa-prototype/frontend/package.json` + `package-lock.json`
- `paper-qa/.pre-commit-config.yaml`（vendored：上游已 pin `ruff v0.14.4`、`prettier v3.6.2`）
- `.agents/notes/README.i18n.yaml`（i18n 一致性记录样例）
- `.venv/Lib/site-packages/pyyaml-6.0.3.dist-info`
- `verify/` 目录清单（30+ `verify_*.py` 与 `gui_check*.mjs`）
