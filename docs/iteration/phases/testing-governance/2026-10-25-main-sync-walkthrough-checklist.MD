# main 同步走查清单（2026-10-25）

> **用途**：用户对"windows → main 同步"的验收。
> **对象**：`main` 上的 `cdec4d2`（第一次同步）＋ 第二次同步提交（本清单所在批，落地后见 PR）。
> **性质**：**只读**走查。下列命令都不改仓库、不推送、不合并；任何一条给出"不符合预期"即**判不通过**并记档。
> **原则**：本清单**只列能被现跑否证的项**；凡是"看起来应该没问题"的都不算通过。

---

## §1 结构验收（同步形态是否正确）

| # | 检查 | 命令 | 通过标准 |
|---|---|---|---|
| 1.1 | 同步提交是**单亲**（不是真 merge 混入 main 历史） | `git log <sync-sha> --format='%h %p' -1` | 恰好 **1 个父提交**，且父＝同步前的 `main` 顶端 |
| 1.2 | 合并提交是**真 merge** | `git log origin/main -1 --format='%h %p'` | **2 个父** = `<旧 main>` ＋ `<sync-sha>` |
| 1.3 | `docs/iteration/**` **不进 main** | `git ls-tree -r --name-only origin/main -- docs/iteration \| measure-object -line` | **0 行** |
| 1.4 | `docs/6-DECISIONS.md` **在 main** | `git ls-tree origin/main -- docs/6-DECISIONS.md` | 有 1 行输出（blob 存在） |
| 1.5 | 4 个 mac 启动脚本**未被删除** | `git ls-tree -r --name-only origin/main -- scripts/setup-env.sh scripts/start-backend.sh scripts/start-frontend.sh scripts/start-streamlit.sh` | **4 行** |
| 1.6 | 树内容 = windows 树 − iteration（无第三处偏差） | `git diff --name-status <sync-sha> <windows-sha>` | 仅出现 `A docs/iteration/…`（186 条）与 `D scripts/*.sh`（4 条），**无其它行** |

---

## §2 判据验收（main 形态下这些门必须绿）

在**全新 clone 的主机**上执行（或用同步树），不要用 windows 工作树代替：

| # | 检查 | 命令 | 通过标准 |
|---|---|---|---|
| 2.1 | 离线套件走**第三态**而非失败 | `python verify/run_suite.py --tier offline` | 末行 `SUITE PASSED (N scripts, M skipped)`，**rc=3**，且 **0 个 FAILED** |
| 2.2 | SKIP 是**具名**的、且不是冒充通过 | 同上 | 恰好 3 条：`verify_agentops.py[spec-absent-on-branch]`、`verify_close_readiness.py[spec-absent-on-branch]`、`verify_usage.py[rev-absent-on-branch]`；末行含 `SKIP≠PASS` |
| 2.3 | CI 的套件门**明确说明放行理由** | 看 CI 日志 `Offline verify suite` 步 | 出现 `零失败 ＋ 有具名 SKIP ⇒ 本步放行（显式说明，非静默）` |
| 2.4 | 登记册在 main 上**走真数据**（不是缺席档） | `python verify/verify_decision_register.py` | `DECISION-REGISTER PASS`，`pointers=1248`、`quotes_drift=0`，且**不出现** `rc=0 ＋ SKIP 横幅` |
| 2.5 | 结构守卫在 PR 场景下**不误判** | 看 CI 日志 `structure-guard.py verify --from-git` | 基线为 **`base.sha`**（main 提交），结论 `STRUCTURE PASS`；**不得**出现 186 项"文件消失" |
| 2.6 | 前端两次构建 | CI 日志 `Build reactflow frontend` / `Build agents-dashboard` | 两步都 **success** |

---

## §3 交付内容验收（这次同步带上了什么）

| # | 检查 | 通过标准 |
|---|---|---|
| 3.1 | `docs/1-WORKFLOW.MD` 的**排除项③已翻转** | 文中写"`docs/6-DECISIONS.md` **纳入 main**（2026-10-03 用户批准）"，且**不再**写"不进 main" |
| 3.2 | `baseline-reform` 阶段存在且已入 ROADMAP | `docs/iteration/phases/baseline-reform/` 四文件存在；`docs/iteration/ROADMAP.MD` 的 Next 表含该阶段（注：本目录在 windows 侧，main 不含 `docs/iteration/**` ⇒ 此项在 **windows 树**上查） |
| 3.3 | C 级棘轮**到期收租**已生效 | `python verify/verify_lint.py` 末行含 `D101=0/12`、`D102=23/46`、`E501=2493/2494`；`review_by=2026-10-31` 到期时要求"严格小于"（见 `BR-1` §9/§10） |
| 3.4 | sprint PNG 已入库（16 处图片链接不再断） | `git ls-files "docs/iteration/sprint/*.png"` ⇒ **11** 条 |
| 3.5 | 忽略规则形状漏网已堵 | `git check-ignore --no-index -v -- ci_fail_log.txt` 与 `-- verify_checkpoint_run.log` ⇒ **rc=0**（修前 rc=1）；`git ls-files -z \| git check-ignore --no-index -z --stdin` ⇒ **零命中**（578 个已跟踪文件零误伤） |

---

## §4 我明确**没有**证明的（走查时不要当成通过）

| # | 事实 | 后果 |
|---|---|---|
| 4.1 | `docs/6-DECISIONS.md` 里 **1106 处指向 `docs/iteration/**` 的指针**在 main 上**未做内容核对** | 它们被"行 39 棘轮上限 1106"钉住，只保证**不再增加**；**内容正确性未验** |
| 4.2 | `CI-CLOSE-SKIP-GATE` 在 main 上**按设计跳过**（无 sprint docs） | 只证"不阻断"，**不证"关闭判定真跑过"** |
| 4.3 | 结构守卫的 `--replay` 自检只证"守卫能拦"，不证"每个 PR 都跑" | 不可跳过层由 CI 命令位置机检（`A-M12①`）保证；本条仍是"半自动" |
| 4.4 | `verify/**` 仍有 **23 条 D102**（缺方法 docstring） | 不影响 2026-10-31 义务（D102 现值 23 < 基线 46），但**不是零债务** |
| 4.5 | 两次同步之间 main 的 `docs/iteration/**` 仍缺失，`verify_card_index.py` 等以 iteration 为条件根的判据在 main 上走条件根 | 这是**设计如此**（windows-only 子树），不是缺陷 |

---

## §5 红旗清单（出现任一即**判不通过**）

1. `docs/iteration/**` 有任意 1 个文件进了 main。
2. 4 个 mac `.sh` 少了任意 1 个。
3. 同步提交有 **2 个父**（说明被做成了 merge，破坏历史形态）。
4. `SUITE` 出现任何 **FAILED**（具名 SKIP 不算，但 rc=1 算）。
5. SKIP 横幅**缺 `<NAME> ` 首 token**（例如只写 `SKIP[…]`）⇒ 会被套件当失败或当静默跳过。
6. `verify_decision_register.py` 在 main 上输出了 `rc=0` 且**同时**打 SKIP 横幅（"自陈条数却跳过"）。
7. 任一 CI 必需检查不是 success。

---

## §6 签收

| 项 | 值 |
|---|---|
| 走查日期 | |
| 结论 | ☐ 通过　☐ 不通过（原因：） |
| 未通过项编号 | |
| 后续动作 | |
