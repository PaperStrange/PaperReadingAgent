# main 同步走查清单（大白话版）

> 这份是给**人**看的。每一项都是"复制一行命令 → 看输出像不像我写的标准"。
> 全部命令**只读**：不改文件、不推送、不合并。任何一条不对，就是**不通过**。
> 命令在仓库根目录（`PaperReading-Windows`）执行；Windows PowerShell 或任意终端都行。

---

## 先说结论：这次同步做了什么

把 `windows` 分支上验证过的代码**搬到了** `main`，但**没搬**两样东西：

1. **没搬 `docs/iteration/` 这个目录** —— 它是"开发过程记录"，只在 windows 上留；
2. **没删** 4 个 mac 启动脚本 —— 那是 mac 分支要用的。

搬的方式是"**先做一个单独的搬运提交，再合并**"（不是把 windows 的历史整个倒进 main），这样 main 的历史干净。

---

## 一共 8 项，逐项打勾

### ① main 上没有 `docs/iteration/`

```powershell
git ls-tree -r --name-only origin/main -- docs/iteration
```

- ✅ **什么都不输出** = 对。
- ❌ 出现任何文件名 = **不通过**（说明开发记录漏进 main 了）。

---

### ② main 上有"决策登记册"

```powershell
git ls-tree origin/main -- docs/6-DECISIONS.md
```

- ✅ 输出**一行**（开头 `100644 blob ...`）= 对。这个文件是"你拍过的每个板的账本"。
- ❌ 没有输出 = 不通过。

---

### ③ 4 个 mac 启动脚本还在

```powershell
git ls-tree -r --name-only origin/main -- scripts/setup-env.sh scripts/start-backend.sh scripts/start-frontend.sh scripts/start-streamlit.sh
```

- ✅ 输出行数**等于**命令里列的脚本数 = 对（**以命令输出为准**）。
- ❌ 少于命令里列出的条数 = 不通过（mac 用户会启动不了）。

---

### ④ 历史形状：搬运是"一个父"，合并是"两个父"

```powershell
git cat-file -p 259628f | Select-String "^parent "
git cat-file -p origin/main | Select-String "^parent "
```

- ✅ 第一条 **1 行**（"搬运提交"只能有一个父），第二条 **2 行**（"合并提交"正常两个父）。
- ❌ 搬运提交出现 2 行 = 不通过（历史形状坏了）。
- 看不懂可跳过：只影响历史整洁度，不影响功能。

---

### ⑤ main 上跑测试：应该"没有失败、但有 3 个跳过"

```powershell
python verify/run_suite.py --tier offline
```

- ✅ 末行以 `SUITE PASSED` 开头、**没有 `FAILED`**，且括号里带 `skipped`。**括号里的数字以你这次跑出来的为准**（不写死，避免抄旧读数）。
- ✅ 被跳过的脚本名里应含 `spec-absent`／`rev-absent` 一类字眼（意思是"main 上缺开发记录或历史版本，这几条判不了"）。**具体几个也以输出为准。**
- ❌ 出现 `SUITE FAILED` = **不通过**。
- ❌ 写 `PASSED` 但括号里**没有** `skipped` = 可疑（可能在假装通过）。

---

### ⑥ 决策登记册在 main 上能自检

```powershell
python verify/verify_decision_register.py
```

- ✅ 出 `DECISION-REGISTER PASS`，且**不**伴随 `SKIP` 字样。
- ❌ 出 `SKIP` 或 `FAIL` = 不通过。

---

### ⑦ CI 是不是真的绿

打开 <https://github.com/PaperStrange/PaperReadingAgent/actions>

- ✅ 最新几条 **都 success**；PR #54 / #55 的检查项 `Offline suite + builds (Windows)` 是绿色。
- ❌ 有任何红色 = 不通过。

---

### ⑧ 两个"已经修好"的小毛病

```powershell
git switch windows
git ls-files "docs/iteration/sprint/*.png" | Measure-Object -Line
git check-ignore --no-index -v -- ci_fail_log.txt
git check-ignore --no-index -v -- verify_checkpoint_run.log
```

- ✅ 第二条输出的 `Lines` 数**等于** `git ls-files "docs/iteration/sprint/*.png"` 的条数（图已入库，文档里的图不会再裂）。**以命令输出为准。**
- ✅ 后两条**都有输出**（这两个杂散文件已被忽略，不会再误入库）。
- ❌ 第二条没有输出、或后两条没输出 = 复查并记一笔（不一定要命）。

> 第 ⑧ 条要在 **windows** 分支看，因为 `docs/iteration/` 只在 windows 上。

---

## 我**没有**证明的事（重要，请知悉）

1. **真实联网、GUI 点击**没在这次 CI 里跑（CI 只跑离线测试 ＋ 前端构建）。
2. main 的决策登记册里有 **1106 处"某文件第 N 行"的引用**，那些文件在 main 上不存在 ⇒ **内容对不上是正常的**；我们只保证这些引用**数量不再增加**。
3. `verify/` 目录里还有 **23 处函数缺注释**（不影响功能，但不算干净）。

---

## 签收

| 项 | 填 |
|---|---|
| 走查日期 | |
| 结论 | ☐ 通过　☐ 不通过 |
| 哪几项不过（写编号） | |
| 想让我先修哪个 | |
