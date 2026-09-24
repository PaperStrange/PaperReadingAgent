# TG-14 迁移交接单（一卡一文档 · 95 卡）

> 生成于 2026-09-23（D3），**给下一位执行者**（新会话 / 子代理）。
> 卡正文的唯一真源：`docs/iteration/phases/testing-governance/backlog.MD` 的 `TG-14` 行。
> 本文件是**操作手册 + 约束 + 验收判据**，不复制卡正文。

## 0. 一句话

把 `phases/<阶段>/backlog.MD` 表格单元格里的**卡片正文**搬到 `phases/<阶段>/cards/<卡号>.md`，
backlog 退化为**瘦索引**，全过程用**已建好的闸门**保证"一张卡都没丢、没漂移"。

## 1. 现状基线（可复现，勿手抄）

```powershell
.\.venv\Scripts\python.exe scripts\card-inventory.py --json agents\runtime\tg14-baseline.json
```

实测（2026-09-23，已订正卡内过期的"94/16"）：

| 阶段 | 卡数 | 结构 | 备注 |
|---|---|---|---|
| `testing-governance` | **17** | 1 张表 | **试点批次**（卡数已知、结构规整） |
| `mental-models` | 6 | 1 张表 | 第二批 |
| `agents-infra` | 25 | **3 张表** | 含 1 行 `—` 占位（**不计入卡数**，需保留或显式处置） |
| `refactor-analysis` | 47 | **3 张表** | 卡号形态最杂（`F1`/`M18`/`R-E3`/`F-AC16`） |
| **合计** | **95** | | 迁移后必须仍是 95 |

## 2. 硬约束（每条都有对应闸门，不许绕过）

1. **一卡一文件**：`phases/<阶段>/cards/<卡号>.md`；文件名 = 卡号（含大小写与连字符，如 `F-AC13.md`）。
2. **卡文件必备节**：`状态` / `规模` / `来源` / `Sprint` 四个二级标题（`## 状态` 等）；正文、证据可选。
3. **卡内必须有一行**：`- \`card\`: <卡号>`（卡号↔文件名一致性的判据）。
4. **backlog 只留瘦索引**：`卡号 | 一句话 | 状态 | Sprint | 文件链接`；
   **不得再放正文**（根因/机制/长清单一律进卡文件）。
5. **Sprint 文档 / roadmap 只按卡号引用**，不得复制卡正文（闸门按段落指纹比对）。
6. **`—` 占位行**：保留原样或显式说明，**不要**把它当卡建文件。
7. **多表结构必须保留**：`agents-infra` / `refactor-analysis` 的 backlog 有多张表（按主题分组），
   迁移后**分组标题与表的段落结构不变**，只是每张表从"正文表"变成"索引表"。

## 3. 验收判据（全部可执行，顺序即执行顺序）

```powershell
# ① 结构安全（改 backlog 必跑；未转义管道会把表格切坏）
.\.venv\Scripts\python.exe verify\verify_md_tables.py

# ② 卡索引：迁移期宽松档（只查"索引↔文件"双向一一对应）
.\.venv\Scripts\python.exe verify\verify_card_index.py --check

# ③ 卡索引：迁移完成后严格档（加"必备节"与"Sprint 不得复制卡正文"）
.\.venv\Scripts\python.exe verify\verify_card_index.py --check --strict

# ④ 不丢卡：卡数与卡号集合必须与基线一致
.\.venv\Scripts\python.exe scripts\card-inventory.py            # 总数应仍为 95
#    并逐阶段比对基线 JSON 的 card 字段集合（脚本已落盘基线）

# ⑤ 套件与矩阵（改了 verify/docs 就要跑）
.\.venv\Scripts\python.exe verify\run_suite.py --tier offline
.\.venv\Scripts\python.exe verify\verify_matrix.py check
```

**闸门自身也刚经过反向对照**（删卡文件 / 卡号不符 / 缺节 / Sprint 塞正文 / 孤儿文件 → 各自 FAIL），
所以"它通过"是有意义的；但**不要相信未经复现的声称**（本项目 2026-09-23 实测：复核子代理对一条
finding 的根因判断是错的，按实测纠正后才没修错地方）。

## 4. 建议的执行顺序（分批、每批一提交）

| 批次 | 范围 | 为什么这个顺序 |
|---|---|---|
| **P1（试点）** | `testing-governance`（17 卡） | 卡数已知、单表、我这两天的改动使它的卡正文最规范；**先在它身上定形式** |
| P2 | `mental-models`（6 卡） | 最小批次，验证"小阶段"形态 |
| P3 | `agents-infra`（25 卡，3 表） | 首次遇到多表 + `—` 占位 |
| P4 | `refactor-analysis`（47 卡，3 表） | 卡号形态最杂、单格最大（`A-M11` 7.9 KB 的同类样本在此） |

**每批做完就跑第 3 节的 ①②④ 并提交**；全部完成后跑 ③⑤ 并更新卡状态。

## 5. 已知坑（都是实测踩过的，别重复）

1. **`edit` 跨边界吃内容**：本 Sprint 三次 R1 事故全部发生在编辑 Markdown 表格/标题时
   （`old_string` 跨到相邻单元格或下一节标题）。**动表格优先用脚本做机械变换**，改完立刻跑 `verify_md_tables.py`。
2. **PowerShell here-string 会吃掉 `#` 注释与反斜杠转义**（实测两次踩坑）：
   超过两行的 Python 一律**写成文件再跑**，不要用 `python -c "..."` 内联。
3. **行尾**：仓库约定 **LF**（实测 377/400 文件为 LF，无 `.gitattributes`、`core.autocrlf=false`）。
   写文件用 `open(..., newline="")`，别用 `Path.write_text()`（Windows 会翻成 CRLF，让 diff 虚高数倍）。
4. **卡的正文里含表格 / `<br>` / 多层引用**：抽取时按"该行后续单元格全部内容"整体搬运，
   不要把内嵌 `|` 当分隔符（用 `verify_md_tables.py::split_row` 的同款口径：只切**未转义**管道）。
5. **`A-M11` 类超长卡**（单格 7.9 KB）搬运后要**逐段核对**是否完整（`cards/` 文件长度 ≈ 原单元格长度）。

## 6. 交付物

- `phases/<阶段>/cards/*.md`（95 个）
- 瘦索引化的 `phases/<阶段>/backlog.MD`（4 份）
- 若要动 Sprint 文档的引用方式：只改"引用"不改"正文"（闸门会拦）
- `TG-14` 卡状态更新（在 `testing-governance/backlog.MD` 或迁移后的 `cards/TG-14.md`）＋ Sprint-17 §3/§7 记录
