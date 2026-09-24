#!/usr/bin/env python3
"""A-M12：Markdown **结构守卫**（`snapshot` / `verify` / `--replay`）——把 R1 族事故从"事后自检"变成"前置拦截"。

**背景（可核）**：Sprint-17 内实测 **5 次**同型事故（R1-1~R1-5，逐条证据见
`docs/iteration/phases/agents-infra/2026-09-23-edit-boundary-incidents-case.MD`）：`edit`-style 文本替换的
`old_string` 跨到"我以为是边界、其实是内容"的位置，**静默吃掉**标题行 / 下一节标题 / 表格单元格边界。
5/5 全部由**事后**自检抓到——缺的不是注意力，而是**前置/通用**的结构守卫。本脚本就是那个守卫：

    snapshot → 编辑 → verify

`snapshot` 把**政策派生**的文档集合的结构清单落盘（默认 `agents/runtime/doc-structure.json`）；
`verify` 只对**丢失/变形**报错：新增标题 / 新增表格 / **表格新增行** / 新增文件一律 OK 并打印，
**同一行就地改写**（数量不变、文本变了）报 `[修改]` 也 OK，
因此它可以在**任何** Markdown 结构编辑前后无条件各跑一次，而不因"我刚加了内容 / 我刚改了一行"误报。

## 判据（verify，逐条对应 R1 的真实形态；**丢失 = 数量减少**）
  ① 标题**数量减少** → FAIL 点名 `文件:行 标题`（R1-1 `## 2. 启动条件`、R1-5 `## 7. 我接手的工作面`）
  ② 标题级别变化 → FAIL
  ③ 表格块消失 / 列数变化 / 行数减少 → FAIL（R1-3 数据行被顶掉一格、R1-4 整表被压成 1 格）
  ④ 文件消失 → FAIL
  ⑤ **同一行就地改写**（标题行 / 行首粗体锚点行：数量不变、文本变了）→ **不是丢失**：报 `[修改]`，rc=0
  退出码：rc=1 有任何丢失/变形；rc=0 否则。

**① 的边界（H1，2026-09-25 实测修正）**：旧实现按**文本集合**判标题与锚点行——基线里的那一行文本在
新文本里找不到 ⇒ 报「标题被删 / 锚点行被删」，同一行又被报成「新增」。于是**就地改一行**（补一个小节
号、retarget 一处 `§` 引用——batch G 实测 **5 份文档**的行首粗体锚点行）会同时拿到"被删"与"新增"两条
**相反**结论、rc=1：一次纯文本修改被误判为丢失，守卫从此变成噪音源。现改为**计数口径**：
**数量减少 = 丢失 → FAIL**；**数量不变而文本变了 = `[修改]` → rc=0**。
`--replay` 的 H1-a/H1-b/H1-c 三条对照把该契约钉成可执行断言（就地改写 rc=0 且输出**不得**含「被删」；
删标题 / 改级别必须仍 rc=1）。5 类 R1 事故全是"数量减少 / 表格变形"，计数口径**一条都没放过**。

**③ 的边界（F2，2026-09-25 实测修正）**：判据只对**丢失/变形**报错——表格**行数增加**（追加一行）
与新增表格块都是**新增**，rc=0 并打印 `[新增]`。旧实现把"追加一行"报成「表格列数变化」
（`row_columns` 两个列表长度不同 ⇒ 不等 ⇒ 命中列数分支），与本节契约相反；现逐行口径只对齐到
基线已有的那些行。`--replay` 的 F2-a~F2-d 四条对照把该契约钉成可执行断言。

**合法结构变更**（有意加列 / 改标题**级别** / 删行重排表格）会同样报 FAIL——这是**刻意的**：`verify`
不猜意图，编辑前后各跑一次时任何结构差分都必须由人确认，确认后**重做 `snapshot`** 即为新基线。
有意**改标题/锚点行的文字**只报 `[修改]`（rc=0），不需要人工确认——它不改变结构，只是内容更新。

## 文档集来自政策（**不写第二份路径清单**）
`agents/policy.json::md_table_docs` + `md_table_globs` 展开，与 `verify/verify_md_tables.py` 的"实扫集"
**同源同口径**（同一政策键、同一展开方式、同一 `split_row` 切分器）；真仓库模式下再调用
`verify_md_tables.coverage_problems()` 核对 `md_table_coverage` 的"应扫/实扫"双向差集
（**复用同一判据，不重写**——复制一份判据就是又一处会漂移的真源）。

## 快照 schema（自解释；各项均为 `行|…`，行尾空白一律忽略）
    headings : ["41|2|3. 项目管理（分支与远程）"]                        # 行|级别|文本
    anchors  : ["41|## 3. 项目管理（分支与远程）", "236|**卡片来源与时间口径…**：…"]   # 行|原文
    tables   : [{start_line, columns, rows, row_columns, header}]
      * `row_columns` 是**逐行**单元格数：某数据行被顶掉一格时**表头列数不变**，只有逐行口径
        看得见 R1-3（spec 的"列数/行数"是它的汇总，两者都记）。
      * `anchors` 除 `^#+ ` 标题行外**还收"行首粗体行"**（`**…**：…`）：R1-2 的真实输入被吃掉的是
        `**卡片来源与时间口径…**` 这行**粗体标题**，只认 `^#+` 会漏（`--replay` 的 R1-2 就是它）。
      * `headings` 在 spec 的"级别|文本"上加**行号**——① 要求点名 `文件:行 标题`，而标题被删后
        行号只存在于基线里（事后扫描无法复原它原本在哪一行）。

## 用法
    .venv\\Scripts\\python.exe scripts\\structure-guard.py snapshot [--root <dir>] [--out <json>]
    .venv\\Scripts\\python.exe scripts\\structure-guard.py verify   [--root <dir>] [--baseline <json>]
    .venv\\Scripts\\python.exe scripts\\structure-guard.py --replay
退出码：0=通过；1=有丢失/变形（verify）或自检断言失败（--replay）；2=政策/用法错误。

`--replay` = **5 类真实 R1 输入**（必须全部被拦下）+ **4 类 F2 反向对照**（追加行必须放行、
删行/改列数/删标题必须被拦下）+ **3 类 H1 就地改写对照**（同数量原地改标题行/锚点行必须放行并报
`[修改]`、改标题级别必须被拦下），全部在 `%TEMP%` 副本上跑，真文件只读。

`--root` 只改变"**文档树在哪**"（replay 的临时镜像用），**不改变"政策是什么"**：政策数据只有一个真源
`agents/policy.json`，不为副本再造第二份政策（否则"两处政策各说一套"就是下一类漂移）。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import PolicyError, load_policy  # noqa: E402
from verify.verify_md_tables import coverage_problems, split_row  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SNAPSHOT_REL = "agents/runtime/doc-structure.json"
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(\S.*)$")
BOLD_LEAD_RE = re.compile(r"^\*\*[^*\s].*\*\*")

_POLICY = None


class ReplayError(RuntimeError):
    """`--replay` 的构造步骤失败（临时副本里找不到"要吞掉的那一行"等）——自检自身坏了，必须显式失败。"""


def policy():
    """政策加载器（TG-15 唯一入口），进程内缓存：一次 replay 要跑十几次 CLI，不必重复读盘。"""
    global _POLICY
    if _POLICY is None:
        _POLICY = load_policy()
    return _POLICY


# --------------------------------------------------------------------------- 文档集（政策派生）

def doc_set(root: Path) -> list[str]:
    """政策派生的文档集 = `md_table_docs`（显式，保序）∪ `md_table_globs` 展开（在 `root` 下解析）。

    **不写路径清单**（TG-15 / `verify_no_policy_hardcode.py`）：换一棵树、加一条 glob 只改
    `agents/policy.json`。展开结果与 `verify_md_tables.py` 的"实扫集"必须相等（真仓库模式下由
    `coverage_problems()` 断言，见 `cmd_snapshot`）。
    """
    data = policy().policy_file
    out: list[str] = []
    for raw in (data.get("md_table_docs") or []):
        rel = str(raw).replace("\\", "/")
        if rel not in out:
            out.append(rel)
    for pattern in (data.get("md_table_globs") or []):
        for path in sorted(root.glob(str(pattern))):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel not in out:
                out.append(rel)
    return out


def coverage_report(root: Path) -> list[str]:
    """真仓库模式下核对"应扫/实扫"双向差集——**复用 `verify_md_tables` 的判据**（不重写）。

    `verify_md_tables.coverage_problems()` 返回 `(应扫, 实扫, problems)` 三元组，这里只取 problems
    （首版实测踩过：把整个三元组当 problems 迭代，于是把"应扫集"这份 160 条清单当成 3 条错误打印出来
    ——复用别人判据时**先看清返回契约**）。

    `--root`（临时镜像）模式不调用它：那份判据的路径按 `verify_md_tables.ROOT`（真仓库）解析，
    在镜像上跑会得到"检查了另一棵树"的假结论——**宁可明说跳过，也不给一个看起来成立的绿**。
    """
    if root.resolve() != ROOT.resolve():
        print("  [覆盖] --root 非仓库根：跳过 md_table_coverage 双向差集（政策集按该根解析）")
        return []
    expected, actual, problems = coverage_problems(policy())
    print(f"  [覆盖] 双向差集（判据复用 verify_md_tables）：应扫 {len(expected)} / 实扫 {len(actual)} → "
          f"{'一致' if len(expected) == len(actual) and not problems else '**不一致**'}")
    return list(problems)


# --------------------------------------------------------------------------- 结构扫描

def _table_record(block: list[tuple[int, str]]) -> dict:
    return {
        "start_line": block[0][0],
        "columns": len(split_row(block[0][1])),
        "rows": len(block),
        "row_columns": [len(split_row(row)) for _, row in block],
        "header": block[0][1],
    }


def scan_file(path: Path) -> dict:
    """抽一份文件的结构清单：`headings` / `tables` / `anchors`（口径见模块头 schema 节）。"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    headings: list[str] = []
    anchors: list[str] = []
    tables: list[dict] = []
    block: list[tuple[int, str]] = []
    for lineno, raw in enumerate(lines, 1):
        row = raw.rstrip()
        if row.strip().startswith("|"):
            block.append((lineno, row.strip()))
        elif block:
            tables.append(_table_record(block))
            block = []
        heading = HEADING_RE.match(row)
        if heading:
            headings.append(f"{lineno}|{len(heading.group(1))}|{heading.group(2).strip()}")
            anchors.append(f"{lineno}|{row}")
        elif BOLD_LEAD_RE.match(row):
            anchors.append(f"{lineno}|{row}")
    if block:
        tables.append(_table_record(block))
    return {"headings": headings, "tables": tables, "anchors": anchors}


def scan_docs(root: Path, rels: list[str]) -> tuple[dict[str, dict], list[str]]:
    files: dict[str, dict] = {}
    missing: list[str] = []
    for rel in rels:
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        files[rel] = scan_file(path)
    return files, missing


# --------------------------------------------------------------------------- 比对（只报丢失/变形）

def _plain_anchors(entries: list[str]) -> list[tuple[int, str]]:
    out = []
    for entry in entries:
        line, _, text = entry.partition("|")
        out.append((int(line), text))
    return out


def _heading_items(entries: list[str]) -> list[tuple[int, int, str]]:
    out = []
    for entry in entries:
        line, _, rest = entry.partition("|")
        level, _, text = rest.partition("|")
        out.append((int(line), int(level), text))
    return out


def _clip(text: str, limit: int = 100) -> str:
    """`[修改]` 判据的行文截断（锚点行可以长到几千字符，整行原文打印两遍会淹掉其它判据）。"""
    return text if len(text) <= limit else f"{text[:limit]}…（共 {len(text)} 字符）"


def _pair_leftovers(base_texts: list[str], cur_texts: list[str]) -> tuple[list[tuple[int, int]],
                                                                        list[int], list[int]]:
    """把"按原文对不上"的基线/现有序目一一配对——**配对即『就地修改』，落单的基线 = 丢失**。

    H1（2026-09-25）的判据核心：**丢失看数量，不看文本**。
    先按相似度（difflib）降序贪心配 `min(m, n)` 对，因此
      * `m == n`（数量不变）⇒ 全部配成对 ⇒ 无『被删』、无『新增』，只有 `[修改]`（rc=0）——
        这正是旧实现误报的那个输入；
      * `m > n`（数量减少）⇒ 最不像的那些基线条目落单 ⇒ 报『被删』（FAIL），余下的配成 `[修改]`：
        相似度排序让"改了一行 + 删了另一行"能各自点名（而不是把被删的那行也算成修改）。
    条目数很小（只处理对不上的残项），配对代价可忽略。
    """
    cands = sorted(((difflib.SequenceMatcher(None, btext, ctext).ratio(), bi, ci)
                    for bi, btext in enumerate(base_texts)
                    for ci, ctext in enumerate(cur_texts)),
                   key=lambda item: (-item[0], item[1], item[2]))
    pairs: list[tuple[int, int]] = []
    used_base: set[int] = set()
    used_cur: set[int] = set()
    for _, bi, ci in cands:
        if bi in used_base or ci in used_cur:
            continue
        used_base.add(bi)
        used_cur.add(ci)
        pairs.append((bi, ci))
        if len(pairs) == min(len(base_texts), len(cur_texts)):
            break
    pairs.sort()
    return pairs, [i for i in range(len(base_texts)) if i not in used_base], \
        [i for i in range(len(cur_texts)) if i not in used_cur]


def _heading_diff(rel: str, base: list[str], cur: list[str]) -> tuple[list[str], list[str], list[str]]:
    """标题比对（H1 起为**计数口径**）：返回 `(failed, modified, added)`。

    ① 原文（含级别）逐字相同的标题先一一对上——对上而**级别变了** ⇒ FAIL（级别是结构，不是文本）；
    ② 对不上的残项交给 `_pair_leftovers`：配成对 = `[修改]`（数量不变即 rc=0），
       落单的基线 = **数量减少** ⇒ FAIL『标题被删』，落单的现有 = 新增。
    """
    failures: list[str] = []
    modifications: list[str] = []
    additions: list[str] = []
    current = _heading_items(cur)
    used = [False] * len(current)
    base_left: list[tuple[int, int, str]] = []
    for bline, blevel, btext in _heading_items(base):
        hit = next((k for k, item in enumerate(current) if not used[k] and item[2] == btext), None)
        if hit is None:
            base_left.append((bline, blevel, btext))
            continue
        used[hit] = True
        cline, clevel, _ = current[hit]
        if clevel != blevel:
            failures.append(f"{rel}:{bline} 标题级别变化：{'#' * blevel} {btext} → 级别 {clevel}"
                            f"（现 {rel}:{cline}）")
    cur_left = [item for k, item in enumerate(current) if not used[k]]
    pairs, base_only, cur_only = _pair_leftovers([t for _, _, t in base_left],
                                                 [t for _, _, t in cur_left])
    for bi, ci in pairs:
        bline, blevel, btext = base_left[bi]
        cline, clevel, ctext = cur_left[ci]
        if clevel != blevel:
            failures.append(f"{rel}:{bline} 标题级别变化：{'#' * blevel} {btext} → 级别 {clevel}"
                            f"（现 {rel}:{cline}「{_clip(ctext, 60)}」）")
        else:
            modifications.append(f"{rel}:{bline} 标题被修改（{'#' * blevel}）：{_clip(btext)} → "
                                 f"{_clip(ctext)}（现 {rel}:{cline}）")
    for bi in base_only:
        bline, blevel, btext = base_left[bi]
        failures.append(f"{rel}:{bline} 标题被删：{'#' * blevel} {btext}")
    for ci in cur_only:
        cline, clevel, ctext = cur_left[ci]
        additions.append(f"{rel}:{cline} 新增标题：{'#' * clevel} {ctext}")
    return failures, modifications, additions


def _anchor_diff(rel: str, base: list[str], cur: list[str]) -> tuple[list[str], list[str], list[str]]:
    """锚点行比对（H1 起为**计数口径**）。`^#+ ` 标题锚点已由 `_heading_diff` 判（含级别与行号），
    这里只判**行首粗体行**——R1-2 被吃掉的那行正是粗体标题（`**卡片来源与时间口径…**`），只认 `^#+`
    会漏；反过来，若不跳过 `#` 行，同一个标题会被两条判据各报一遍。

    判据与标题同构（见 `_pair_leftovers`）：**数量减少 = 丢失（FAIL）；数量不变 = `[修改]`（rc=0）**。
    锚点行没有"级别"，故配对残项一律算 `[修改]`，不存在级别分支。
    """
    failures: list[str] = []
    modifications: list[str] = []
    additions: list[str] = []
    base_items = [(line, text) for line, text in _plain_anchors(base) if not text.startswith("#")]
    cur_items = [(line, text) for line, text in _plain_anchors(cur) if not text.startswith("#")]
    used = [False] * len(cur_items)
    base_left: list[tuple[int, str]] = []
    for bline, btext in base_items:
        hit = next((k for k, (_, text) in enumerate(cur_items) if not used[k] and text == btext), None)
        if hit is None:
            base_left.append((bline, btext))
            continue
        used[hit] = True
    cur_left = [item for k, item in enumerate(cur_items) if not used[k]]
    pairs, base_only, cur_only = _pair_leftovers([t for _, t in base_left], [t for _, t in cur_left])
    for bi, ci in pairs:
        (bline, btext), (cline, ctext) = base_left[bi], cur_left[ci]
        modifications.append(f"{rel}:{bline} 锚点行被修改：{_clip(btext)} → {_clip(ctext)}"
                             f"（现 {rel}:{cline}）")
    for bi in base_only:
        bline, btext = base_left[bi]
        failures.append(f"{rel}:{bline} 锚点行被删：{btext}")
    for ci in cur_only:
        cline, ctext = cur_left[ci]
        additions.append(f"{rel}:{cline} 新增锚点行：{ctext}")
    return failures, modifications, additions


def _row_diff_detail(rel: str, btable: dict, ctable: dict) -> str:
    """点名**第一处**列数不同的行。

    F2 起只对**基线已有的那些行**（`row_columns[:len(基线)]`）逐位对齐——行数增加时多出来的
    行不再进入对齐（它们是"新增"，不是"变形"），所以下标 `j` 仍与基线行一一对应，
    `ctable['start_line'] + j` 依旧是该行的真实行号。
    """
    brow = btable["row_columns"]
    crow = ctable["row_columns"]
    for j, (bc, cc) in enumerate(zip(brow, crow, strict=False)):
        if bc != cc:
            return (f"第 {j + 1} 行 {bc} 列 → {cc} 列（现 {rel}:{ctable['start_line'] + j}；"
                    f"表头 @{rel}:{btable['start_line']}）")
    return (f"逐行列数签名不同（基线 {brow} → 现 {crow}；表头 @{rel}:{btable['start_line']}）")


def _table_diff(rel: str, base: list[dict], cur: list[dict]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    additions: list[str] = []
    used = [False] * len(cur)
    for btable in base:
        hit = next((k for k, item in enumerate(cur) if not used[k] and item["header"] == btable["header"]), None)
        if hit is None:
            failures.append(f"{rel}:{btable['start_line']} 表格块消失：表头 {btable['header']}"
                            f"（基线 {btable['rows']} 行 × {btable['columns']} 列）")
            continue
        used[hit] = True
        ctable = cur[hit]
        # 判据顺序是**语义**问题（首版把两者的顺序写反，于是"删掉一整行"被报成"列数变化：
        # 表头 3 列 → 3 列"——行数少了却说列数变了）：先判**行数减少**（整行被吞），
        # 再判**列数变化**（行列不对齐 = 单元格被顶出，R1-3）。两者都 FAIL，但点名必须对得上事实。
        #
        # F2（2026-09-25 实测修正）：上面这版"先判行数、再判列数"只是把**行数减少**那一支修对了，
        # 行数**增加**时第二支照样误报——`ctable["row_columns"] != btable["row_columns"]` 在两个
        # 列表长度不同时**必然成立**（列表不等），于是"追加一行"被报成「表格列数变化」
        # （实测：`backlog.MD` 19→20 行、5 列不变，rc=1）。这与模块头「新增标题 / 新增表格 /
        # 新增文件一律 OK 并打印」的契约直接冲突：**行追加也是新增**。
        # 现把逐行口径**只对齐到基线已有的那些行**（`crow[:btable["rows"]]`）：
        #   行数减少 = 丢失 → FAIL；基线行的列数签名变了 = 变形 → FAIL；
        #   多出来的行 = 新增 → 放行并计入 additions（`verify` 打印 `[新增]`）。
        brow, crow = btable["row_columns"], ctable["row_columns"]
        if ctable["rows"] < btable["rows"]:
            failures.append(f"{rel}:{btable['start_line']} 表格行数减少："
                            f"{btable['rows']} 行 → {ctable['rows']} 行（表头 {btable['header']}）")
        elif crow[:len(brow)] != brow:
            failures.append(f"{rel}:{btable['start_line']} 表格列数变化："
                            f"{_row_diff_detail(rel, btable, ctable)}")
        elif ctable["rows"] > btable["rows"]:
            additions.append(f"{rel}:{ctable['start_line']} 表格新增行："
                             f"{btable['rows']} 行 → {ctable['rows']} 行"
                             f"（表头 {btable['header']}，列数 {ctable['columns']} 不变；新增不判失败）")
    for k, ctable in enumerate(cur):
        if not used[k]:
            additions.append(f"{rel}:{ctable['start_line']} 新增表格："
                             f"{ctable['columns']} 列 × {ctable['rows']} 行")
    return failures, additions


def compare(files: dict[str, dict], baseline: dict) -> tuple[list[str], list[str], list[str]]:
    """返回 `(failed, modified, added)`——`modified` 只用于报告，**不进 rc**（H1：同数量改写不是丢失）。"""
    failures: list[str] = []
    modifications: list[str] = []
    additions: list[str] = []
    for rel in sorted(baseline):
        base = baseline[rel]
        if rel not in files:
            failures.append(f"{rel} 文件消失：基线记录的 {len(base['headings'])} 个标题 / "
                            f"{len(base['tables'])} 个表格块无从核验")
            continue
        cur = files[rel]
        head_fail, head_mod, head_add = _heading_diff(rel, base["headings"], cur["headings"])
        anchor_fail, anchor_mod, anchor_add = _anchor_diff(rel, base["anchors"], cur["anchors"])
        table_fail, table_add = _table_diff(rel, base["tables"], cur["tables"])
        failures += head_fail + anchor_fail + table_fail
        modifications += head_mod + anchor_mod
        additions += head_add + anchor_add + table_add
    return failures, modifications, additions


# --------------------------------------------------------------------------- CLI

def _resolve_root(raw: str) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _resolve_json(raw: str) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def cmd_snapshot(root: Path, out: Path) -> int:
    pre = coverage_report(root)
    print(f"structure-guard snapshot：root={root} → {out}")
    if pre:
        print(f"STRUCTURE ERROR：政策扫描集自身不一致（{len(pre)} 项；判据复用 verify_md_tables）——"
              f"先修 agents/policy.json 的 md_table_coverage/md_table_docs/md_table_globs：")
        for item in pre[:10]:
            print(f"  - {item}")
        return 2
    rels = doc_set(root)
    files, missing = scan_docs(root, rels)
    snapshot = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool": "scripts/structure-guard.py",
        "root": str(root),
        "doc_set_source": "agents/policy.json::md_table_docs + md_table_globs（政策派生，无第二份路径清单）",
        "doc_count": len(files),
        "schema": {
            "headings": "行|级别|文本",
            "anchors": "行|原文（^#+ 标题行 + 行首粗体行）",
            "tables": "{start_line, columns, rows, row_columns, header}",
        },
        "files": files,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    heads = sum(len(f["headings"]) for f in files.values())
    anchors = sum(len(f["anchors"]) for f in files.values())
    tables = sum(len(f["tables"]) for f in files.values())
    print(f"  已记录 {len(files)} 文件 / 标题 {heads} / 锚点行 {anchors} / 表格块 {tables}")
    if missing:
        # 政策点名的文档缺失是"少扫"形态（verify_md_tables 的 fail-closed 判据管这件事），
        # 本脚本只如实报告、不静默跳过，也不重复判别人的判据。
        print(f"  WARN：政策扫描集内 {len(missing)} 个文件不存在（未被记录，先跑 verify_md_tables.py）："
              f"{missing[:5]}")
    print(f"  SNAPSHOT OK → {out}")
    return 0


def cmd_verify(root: Path, baseline_path: Path) -> int:
    if not baseline_path.is_file():
        print(f"STRUCTURE ERROR：基线不存在 {baseline_path}——先跑 "
              f"`structure-guard.py snapshot`（守卫必须有一份『编辑前』的结构清单才有意义）")
        return 2
    baseline_doc = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline = baseline_doc.get("files") or {}
    print(f"structure-guard verify：root={root} baseline={baseline_path}"
          f"（生成于 {baseline_doc.get('generated_at')}，基线 {len(baseline)} 文件）")
    coverage_report(root)
    current_set = doc_set(root)
    files, _ = scan_docs(root, list(baseline) + [rel for rel in current_set if rel not in baseline])
    failures, modifications, additions = compare(files, baseline)

    new_files = [rel for rel in current_set if rel not in baseline]
    for rel in sorted(new_files):
        cur = files.get(rel) or {}
        print(f"  [新增] {rel} 新增文件：{len(cur.get('headings', []))} 标题 / "
              f"{len(cur.get('tables', []))} 表格块（新增不判失败）")
    for line in additions[:20]:
        print(f"  [新增] {line}")
    if len(additions) > 20:
        print(f"  [新增] … 另有 {len(additions) - 20} 项新增（新增不判失败）")
    for line in modifications[:20]:
        print(f"  [修改] {line}")
    if len(modifications) > 20:
        print(f"  [修改] … 另有 {len(modifications) - 20} 项（**同数量就地改写**：不判失败；"
              f"确认无误后重做 snapshot 立新基线）")
    for line in failures:
        print(f"  [FAIL] {line}")
    if failures:
        print(f"\nSTRUCTURE FAIL（{len(failures)} 项丢失/变形；"
              f"修改 {len(modifications)} 项 / 新增 {len(additions) + len(new_files)} 项不判失败）")
        print("修法：① 补回被删的标题/锚点行（对照基线里的原文）；② 表格按基线补回单元格或整块；"
              "③ 若这是**有意的**结构变更，人工确认后重做 snapshot 立新基线。")
        return 1
    print(f"\nSTRUCTURE PASS（{len(baseline)} 文件无丢失/变形；"
          f"修改 {len(modifications)} 项 / 新增 {len(additions) + len(new_files)} 项）")
    return 0


# --------------------------------------------------------------------------- --replay（5 类真实输入）

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _blocks(lines: list[str]) -> list[tuple[int, int, list[str]]]:
    """表格块 `(起始下标, 结束下标(含), 行)`——与 `scan_file` 同口径（`strip()` 后以 `|` 开头）。"""
    out: list[tuple[int, int, list[str]]] = []
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|"):
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i - 1, [x.strip() for x in lines[start:i]]))
            start = None
    if start is not None:
        out.append((start, len(lines) - 1, [x.strip() for x in lines[start:]]))
    return out


def _drop_line(path: Path, pred, label: str) -> int:
    """删掉**整行**（R1-1/R1-2/R1-5 的真实形态：`old_string` 把边界行当锚点 → 该行消失）。"""
    lines = _read_text(path).split("\n")
    for i, line in enumerate(lines):
        if pred(line.rstrip()):
            del lines[i]
            _write_text(path, "\n".join(lines))
            return i + 1
    raise ReplayError(f"{label}：副本 {path.name} 里找不到要吞掉的那一行（真实输入漂了，请复核用例）")


def _escape_row(row: str) -> str:
    """把行内**未转义**的管道全部转义（= R1-4 的自写转义脚本把单元格边界也转义）。"""
    out: list[str] = []
    for i, ch in enumerate(row):
        if ch == "|" and (i == 0 or row[i - 1] != "\\"):
            out.append("\\|")
        else:
            out.append(ch)
    return "".join(out)


def _damage_r1_1(mirror: Path) -> list[str]:
    rel = "docs/iteration/phases/testing-governance/backlog.MD"
    line = _drop_line(mirror / rel, lambda s: s == "## 2. 启动条件", "R1-1")
    return [f"{rel}:{line}", "## 2. 启动条件", "标题被删"]


def _damage_r1_2(mirror: Path) -> list[str]:
    rel = "docs/1-WORKFLOW.MD"
    line = _drop_line(mirror / rel, lambda s: s.startswith("**卡片来源与时间口径"), "R1-2")
    return [f"{rel}:{line}", "卡片来源与时间口径", "锚点行被删"]


def _damage_r1_3(mirror: Path) -> list[str]:
    rel = "docs/iteration/sprint/2026-09-21-sprint-17.md"
    path = mirror / rel
    lines = _read_text(path).split("\n")
    for start, end, block in _blocks(lines):
        if "处置" not in block[0]:
            continue
        row = lines[end].rstrip()
        last = row.rfind("|")
        prev = row.rfind("|", 0, last)
        lines[end] = row[: prev + 1]
        _write_text(path, "\n".join(lines))
        return [f"{rel}:{end + 1}", "列数变化"]
    raise ReplayError("R1-3：副本里找不到含『处置』列的表格（§5 风险表）")


def _damage_r1_4(mirror: Path) -> list[str]:
    markers: list[str] = []
    for rel in ("docs/iteration/sprint/2026-09-07-sprint-15.md",
                "docs/iteration/sprint/2026-09-12-sprint-16.md"):
        path = mirror / rel
        lines = _read_text(path).split("\n")
        blocks = _blocks(lines)
        if not blocks:
            raise ReplayError(f"R1-4：副本 {path.name} 里没有表格块")
        start, end, _ = max(blocks, key=lambda b: b[1] - b[0])
        for i in range(start, end + 1):
            lines[i] = _escape_row(lines[i])
        _write_text(path, "\n".join(lines))
        markers.append(f"{rel}:{start + 1}")
    return markers


def _damage_r1_5(mirror: Path) -> list[str]:
    rel = "docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD"
    # 现场该标题被吞后已补回并重编号（`## 7.` → `## 8.`）且带了括注，故按前缀匹配——
    # 复现的是"这一行被吃掉"这个**输入形态**，不是某个固定的编号字符串。
    line = _drop_line(mirror / rel, lambda s: s.startswith("## 8. 我接手的工作面"), "R1-5")
    return [f"{rel}:{line}", "我接手的工作面", "标题被删"]


def _damage_f2_append(mirror: Path) -> list[str]:
    """F2-a：**追加一行**（复制末行，行数 +1、列数不变）——必须**放行**并报『新增』。

    这正是被误报的输入（旧实现：`backlog.MD` 19→20 行被报「表格列数变化」）。
    """
    rel = "docs/iteration/phases/testing-governance/backlog.MD"
    path = mirror / rel
    lines = _read_text(path).split("\n")
    blocks = _blocks(lines)
    if not blocks:
        raise ReplayError("F2-a：副本里没有表格块")
    _, end, _ = max(blocks, key=lambda b: b[1] - b[0])
    lines.insert(end + 1, lines[end])
    _write_text(path, "\n".join(lines))
    return [rel, "表格新增行"]


def _damage_f2_drop_row(mirror: Path) -> list[str]:
    """F2-b：**删掉一行数据行**（行数 −1、列数不变）——必须 FAIL 并点名该表。"""
    rel = "docs/iteration/phases/testing-governance/backlog.MD"
    path = mirror / rel
    lines = _read_text(path).split("\n")
    blocks = _blocks(lines)
    if not blocks:
        raise ReplayError("F2-b：副本里没有表格块")
    start, end, block = max(blocks, key=lambda b: b[1] - b[0])
    del lines[end]
    _write_text(path, "\n".join(lines))
    # 点名两件事：表的位置（`文件:表头行`）与表的身份（表头原文）
    return [f"{rel}:{start + 1}", "表格行数减少", block[0]]


def _damage_f2_shrink_cell(mirror: Path) -> list[str]:
    """F2-c：**某数据行少一格**（列数 5→4，行数不变）——必须 FAIL 并点名『表格列数变化』。

    R1-3 打的是 sprint-17 的处置表；本条打 `backlog.MD`，用来证明"列数"判据在**行数不变**时
    仍然只认列变形（与 F2-a"行数变了但列没变 → 放行"构成一对反向对照）。
    """
    rel = "docs/iteration/phases/testing-governance/backlog.MD"
    path = mirror / rel
    lines = _read_text(path).split("\n")
    blocks = _blocks(lines)
    if not blocks:
        raise ReplayError("F2-c：副本里没有表格块")
    start, end, _ = max(blocks, key=lambda b: b[1] - b[0])
    row = lines[end].rstrip()
    last = row.rfind("|")
    prev = row.rfind("|", 0, last)
    lines[end] = row[: prev + 1]
    _write_text(path, "\n".join(lines))
    return [f"{rel}:{start + 1}", "表格列数变化"]


def _damage_f2_drop_heading(mirror: Path) -> list[str]:
    """F2-d：**删掉整行标题**（`## 1. 功能卡`）——必须 FAIL 并点名。

    R1-1 删的是 `## 2. 启动条件`；本条删另一个标题，避免"只对某一个字符串成立"。
    """
    rel = "docs/iteration/phases/testing-governance/backlog.MD"
    line = _drop_line(mirror / rel, lambda s: s == "## 1. 功能卡", "F2-d")
    return [f"{rel}:{line}", "## 1. 功能卡", "标题被删"]


REPLAY_CASES = (
    ("R1-1", "锚点行被吞：`## 2. 启动条件` 整行标题消失（testing-governance/backlog.MD）",
     ["docs/iteration/phases/testing-governance/backlog.MD"], _damage_r1_1),
    ("R1-2", "下一节标题被吞：`**卡片来源与时间口径…**` 粗体标题行整行消失（docs/1-WORKFLOW.MD 插节时）",
     ["docs/1-WORKFLOW.MD"], _damage_r1_2),
    ("R1-3", "表格行的『处置』单元格被顶出（sprint-17 §5 风险表：该行只剩 2 列）",
     ["docs/iteration/sprint/2026-09-21-sprint-17.md"], _damage_r1_3),
    ("R1-4", "自写转义脚本把整表压成 1 格（sprint-15 + sprint-16 两份文档）",
     ["docs/iteration/sprint/2026-09-07-sprint-15.md",
      "docs/iteration/sprint/2026-09-12-sprint-16.md"], _damage_r1_4),
    ("R1-5", "追加新节时吞掉 `## 7. 我接手的工作面` 标题（本文档族；现场已补回并重编号为 §8）",
     ["docs/iteration/phases/testing-governance/2026-09-25-d2d3-parallel-session-quality-analysis.MD"],
     _damage_r1_5),
)

# F2（2026-09-25）：把模块头「新增一律放行，只对丢失/变形报错」的契约钉成**可执行**的四条对照。
# 旧实现实测：`ctable["row_columns"] != btable["row_columns"]` 在行数不同时必然成立 ⇒
# 「追加一行」（19→20 行、5 列不变）被判「表格列数变化」，rc=1，与契约相反。
# `want_rc` 是**期望**退出码：新增 = 0（放行），丢失/变形 = 1（拦下）。
F2_CASES = (
    ("F2-a", "追加一行数据行（行数 +1、列数不变）→ **必须放行**（rc=0）并报『新增』"
             "（旧实现误报『表格列数变化』= 契约反例）",
     ["docs/iteration/phases/testing-governance/backlog.MD"], _damage_f2_append, 0),
    ("F2-b", "删掉一行数据行（行数 −1）→ rc=1 且点名该表（`文件:表头行` + 表头原文 + 『表格行数减少』）",
     ["docs/iteration/phases/testing-governance/backlog.MD"], _damage_f2_drop_row, 1),
    ("F2-c", "某数据行少一格（列数 5→4、行数不变）→ rc=1 且点名『表格列数变化』",
     ["docs/iteration/phases/testing-governance/backlog.MD"], _damage_f2_shrink_cell, 1),
    ("F2-d", "删掉整行标题 `## 1. 功能卡` → rc=1 且点名『标题被删』",
     ["docs/iteration/phases/testing-governance/backlog.MD"], _damage_f2_drop_heading, 1),
)


def _rewrite_line(path: Path, prefix: str, rewrite, label: str) -> tuple[int, str, str]:
    """**就地改写**一行（行数不变、文本变了）——返回 `(行号, 原文, 新文)`。

    与 `_drop_line` 成对：同一条判据（"这一行的文本变了"）在旧实现下被报成『被删』，在计数口径下
    只该报 `[修改]`。找不到该行时抛 `ReplayError`（用例漂了必须显式失败，不静默放过）。
    """
    lines = _read_text(path).split("\n")
    for i, line in enumerate(lines):
        if line.rstrip().startswith(prefix):
            old = line.rstrip()
            lines[i] = rewrite(old)
            _write_text(path, "\n".join(lines))
            return i + 1, old, lines[i]
    raise ReplayError(f"{label}：副本 {path.name} 里找不到以 {prefix!r} 开头的行（真实输入漂了，请复核用例）")


def _damage_h1_heading(mirror: Path) -> list[str]:
    """H1-a：**标题行就地改写**（数量不变）——必须**放行**（rc=0）并报『标题被修改』。

    形态照抄实测到的假阳性：在一行标题里补一处括注（batch G 那批改的是行首粗体锚点行）。
    旧实现在同一份输出里既报『标题被删』又报『新增标题』、rc=1。
    """
    rel = "docs/1-WORKFLOW.MD"
    line, old, new = _rewrite_line(mirror / rel, "## 3. 项目管理（分支与远程）",
                                   lambda s: s.replace("（分支与远程）", "（分支与远程／提交纪律）", 1),
                                   "H1-a")
    # `[修改]` 行把级别与标题文本分开印（`标题被修改（##）：3. …`），故点名用去掉 `## ` 的文本。
    return [f"{rel}:{line}", "标题被修改", old[3:], new[3:]]


def _damage_h1_anchor(mirror: Path) -> list[str]:
    """H1-b：**行首粗体锚点行就地改写**（数量不变）——必须**放行**（rc=0）并报『锚点行被修改』。

    这是 batch G 真实踩到的输入：就地给锚点行补一处 `§` 引用（`**…**：` 行仍以 `**` 开头、
    整行只有一行，数量不变）。R1-2 打的是同一行——**删掉它必须 FAIL，改写它必须放行**。
    """
    rel = "docs/1-WORKFLOW.MD"
    line, old, new = _rewrite_line(mirror / rel, "**卡片来源与时间口径",
                                   lambda s: s.replace("**：", "；§4.2 亦适用**：", 1), "H1-b")
    return [f"{rel}:{line}", "锚点行被修改", "；§4.2 亦适用"]


def _damage_h1_level(mirror: Path) -> list[str]:
    """H1-c：**标题级别变化**（文本逐字不变、数量不变）——必须 FAIL 并点名『标题级别变化』。

    计数口径**不是**"只要数量不变就放行"：级别是结构（`##`→`###` 会改变文档树语义），
    它由"原文相同的标题对上之后比对级别"这一支独立判，与数量无关。
    """
    rel = "docs/1-WORKFLOW.MD"
    line, old, _ = _rewrite_line(mirror / rel, "## 3. 项目管理（分支与远程）",
                                 lambda s: "###" + s[2:], "H1-c")
    return [f"{rel}:{line}", "标题级别变化", old]


# H1（2026-09-25）：把「**同数量就地改写 = [修改]，不是丢失**」钉成三条可执行对照。
# 旧实现实测：batch G 就地 retarget 了 5 份文档的行首粗体锚点行 → 同一行被同时报成
# 「锚点行被删」（FAIL，rc=1）与「新增锚点行」——纯文本修改被误判成丢失，守卫变成噪音源。
# `want_rc` = 期望退出码；`must_not` = **禁止出现**的子串（就地改写不得留任何"被删"字样）。
H1_CASES = (
    ("H1-a", "标题行**就地改写**（数量不变）→ **必须放行**（rc=0）并报『标题被修改』，且不得出现『被删』"
             "（旧实现报『标题被删』= rc=1）",
     ["docs/1-WORKFLOW.MD"], _damage_h1_heading, 0, ["被删"]),
    ("H1-b", "行首粗体锚点行**就地改写**（`**…**：` 行数不变）→ rc=0 且报『锚点行被修改』，不得出现『被删』"
             "（旧实现报『锚点行被删』= rc=1；与 R1-2『删掉同一行必须 FAIL』构成反向对照）",
     ["docs/1-WORKFLOW.MD"], _damage_h1_anchor, 0, ["被删"]),
    ("H1-c", "标题**级别**变化（`## 3. …` → `### 3. …`，文本与数量都不变）→ rc=1 且点名『标题级别变化』"
             "（计数口径不放宽级别判据）",
     ["docs/1-WORKFLOW.MD"], _damage_h1_level, 1, []),
)

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"  PASS: {name} {detail}")


def _digest(root: Path, rels: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(rels):
        path = root / rel
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
    return digest.hexdigest()


def _mirror_copy(src_root: Path, mirror: Path, rels: list[str]) -> None:
    for rel in rels:
        dst = mirror / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_root / rel, dst)


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=str(ROOT))


def _evidence(text: str, markers: list[str]) -> str:
    """`--replay` 的取证标签顺序：先 `[FAIL]`，再 `[新增]`，最后 `[修改]`。

    F2-a 是"新增 → 放行"的对照，它的证据在 `[新增]` 行上；H1-a/H1-b 是"就地改写 → 放行"的对照，
    证据在 `[修改]` 行上——只在 `[FAIL]` 里找会取不到。"""
    lines = text.splitlines()
    for tag in ("[FAIL]", "[新增]", "[修改]"):
        for line in lines:
            if tag in line and any(m in line for m in markers):
                return line.strip()[:150]
    return text.strip().splitlines()[-1][:150] if text.strip() else ""


def cmd_replay() -> int:
    """在 `%TEMP%` 的**副本**上复跑两组自检，每组都必须被 `verify` 按预期处置：

    * **5 类真实 R1 输入**（标题/锚点被吞、单元格被顶出、整表被压平）→ 每类必须被拦下（rc=1）并点名；
    * **4 类 F2 反向对照**（追加行 / 删行 / 改列数 / 删标题）→ 前一类必须**放行**（rc=0，新增不是失败），
      后三类必须被拦下（rc=1）——直接钉住「新增一律放行，只对丢失/变形报错」这句契约；
    * **3 类 H1 反向对照**（标题行就地改写 / 行首粗体锚点行就地改写 / 标题级别变化）→ 前两类必须
      **放行并报 `[修改]`**（且输出里**不得**出现"被删"——旧实现正是在这里误报），第三类必须被拦下
      ——直接钉住「丢失看数量，不看文本」这句契约（H1，2026-09-25 实测修正）。

    三组都夹着一条"复原该文件后 rc=0"的收尾断言，证明判决来自损坏本身而不是副本漂移。

    **绝不动真文件**：所有损坏只发生在镜像里；收尾用"真实文件摘要（跑前 == 跑后）"作为断言，
    而不是靠"我记得没写"（判据取可核的值）。
    """
    print("structure-guard --replay：5 类真实 R1 输入 + 4 类 F2 反向对照 + 3 类 H1 就地改写对照，"
          "全在 %TEMP% 副本上复跑（真文件只读）")
    rels = doc_set(ROOT)
    digest_before = _digest(ROOT, rels)
    tmp = Path(tempfile.mkdtemp(prefix="structure-guard-replay-"))
    mirror = tmp / "repo-mirror"
    baseline = tmp / "doc-structure.json"
    try:
        _mirror_copy(ROOT, mirror, rels)
        temp_root = Path(tempfile.gettempdir()).resolve()
        ok("临时副本位于 %TEMP% 且不在仓库内（绝不动真文件）",
           mirror.resolve() != ROOT.resolve() and temp_root in mirror.resolve().parents,
           f"mirror={mirror}")
        mirrored = doc_set(mirror)
        ok(f"镜像完整：政策文档 {len(rels)} 份全部复制（副本集 == 政策集）",
           set(mirrored) == set(rels), f"副本 {len(mirrored)} / 政策 {len(rels)}")

        snap = _run_cli("snapshot", "--root", str(mirror), "--out", str(baseline))
        ok("snapshot → rc=0（编辑前结构清单已落盘）", snap.returncode == 0,
           f"rc={snap.returncode}；{snap.stdout.strip().splitlines()[-1][:80]}")

        clean = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
        ok("干净副本 verify → rc=0（防假红：未损坏的镜像不得报 FAIL）", clean.returncode == 0,
           f"rc={clean.returncode}；{clean.stdout.strip().splitlines()[-1][:80]}")

        summary: list[str] = []
        for case_id, desc, files, damage in REPLAY_CASES:
            print(f"\n[{case_id}] {desc}")
            markers = damage(mirror)
            bad = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            text = bad.stdout + bad.stderr
            ok(f"{case_id} 被拦下（verify rc=1）", bad.returncode == 1, f"rc={bad.returncode}")
            ok(f"{case_id} 点名到位（{'、'.join(markers)}）", all(m in text for m in markers),
               _evidence(text, markers))
            summary.append(f"{case_id} -> {_evidence(text, markers)}")
            _mirror_copy(ROOT, mirror, files)
            back = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            ok(f"{case_id} 复原该文件后 verify → rc=0（证明 FAIL 来自损坏本身，不是副本漂移）",
               back.returncode == 0, f"rc={back.returncode}")

        ok(f"真文件零改动：{len(rels)} 份文档摘要 跑前 == 跑后", _digest(ROOT, rels) == digest_before,
           f"sha256={digest_before[:16]}…")
        print("\n5 类 R1 复跑结果（旧实现：事后才发现；本机制：编辑后一跑即拦）：")
        for line in summary:
            print(f"  {line}")

        # ---- F2 反向对照（2026-09-25）：`_table_diff` 的"新增 vs 丢失/变形"契约 --------------
        print("\nF2 反向对照（表格行/列的『新增放行 ↔ 丢失变形拦下』契约，4 类）：")
        for case_id, desc, files, damage, want_rc in F2_CASES:
            print(f"\n[{case_id}] {desc}")
            markers = damage(mirror)
            res = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            text = res.stdout + res.stderr
            verdict = "放行（新增不是失败）" if want_rc == 0 else "拦下（丢失/变形）"
            ok(f"{case_id} verify rc={want_rc}（{verdict}）", res.returncode == want_rc, f"rc={res.returncode}")
            ok(f"{case_id} 点名到位（{'、'.join(markers)}）", all(m in text for m in markers),
               _evidence(text, markers))
            summary.append(f"{case_id} -> {_evidence(text, markers)}")
            _mirror_copy(ROOT, mirror, files)
            back = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            ok(f"{case_id} 复原该文件后 verify → rc=0（证明判决来自损坏本身，不是副本漂移）",
               back.returncode == 0, f"rc={back.returncode}")

        print("\nF2 四条对照结果（契约：新增放行 / 丢失·变形拦下）：")
        for line in summary[-len(F2_CASES):]:
            print(f"  {line}")

        ok(f"F2-a 的裁决行确实带『新增』标注（放行必须可核，不是静默 rc=0）",
           "表格新增行" in (summary[-len(F2_CASES)].split(" -> ", 1)[-1]),
           summary[-len(F2_CASES)].split(" -> ", 1)[-1])
        ok(f"真文件零改动（F2 对照后复检）：{len(rels)} 份文档摘要 跑前 == 跑后",
           _digest(ROOT, rels) == digest_before, f"sha256={digest_before[:16]}…")

        # ---- H1 就地改写对照（2026-09-25）：标题/锚点的"计数口径"契约 ------------------------
        print("\nH1 就地改写对照（数量不变 = `[修改]`，不是丢失；3 类）：")
        h1_start = len(summary)
        for case_id, desc, files, damage, want_rc, must_not in H1_CASES:
            print(f"\n[{case_id}] {desc}")
            markers = damage(mirror)
            res = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            text = res.stdout + res.stderr
            verdict = "放行（同数量就地改写不是丢失）" if want_rc == 0 else "拦下（丢失/变形）"
            ok(f"{case_id} verify rc={want_rc}（{verdict}）", res.returncode == want_rc, f"rc={res.returncode}")
            ok(f"{case_id} 点名到位（{'、'.join(markers)}）", all(m in text for m in markers),
               _evidence(text, markers))
            if must_not:
                ok(f"{case_id} 无 『{'/'.join(must_not)}』 误报（旧实现把就地改写报成『被删』）",
                   all(m not in text for m in must_not),
                   "未出现：" + "/".join(must_not))
            summary.append(f"{case_id} -> {_evidence(text, markers)}")
            _mirror_copy(ROOT, mirror, files)
            back = _run_cli("verify", "--root", str(mirror), "--baseline", str(baseline))
            back_text = back.stdout + back.stderr
            ok(f"{case_id} 复原该文件后 verify → rc=0（证明判决来自改写本身，不是副本漂移）",
               back.returncode == 0, f"rc={back.returncode}")
            if want_rc == 0:
                # 比"复原后 rc=0"更强的判据：复原后**不得**再出现 `[修改]`——证明那条标注确实
                # 来自本次改写，而不是副本里本来就有一处改写被这一次的 rc=0 掩盖掉。
                ok(f"{case_id} 复原后不再报『修改』（该标注来自本次改写，不是副本固有差异）",
                   "[修改]" not in back_text, f"rc={back.returncode}")

        print("\nH1 三条对照结果（契约：同数量就地改写放行并报『修改』／级别变化拦下）：")
        for line in summary[h1_start:]:
            print(f"  {line}")
        ok("H1-a/H1-b 的裁决行确实带『修改』标注（放行必须可核，不是静默 rc=0）",
           all("修改" in line.split(" -> ", 1)[-1] for line in summary[h1_start:h1_start + 2]),
           summary[h1_start].split(" -> ", 1)[-1])
        ok(f"真文件零改动（H1 对照后复检）：{len(rels)} 份文档摘要 跑前 == 跑后",
           _digest(ROOT, rels) == digest_before, f"sha256={digest_before[:16]}…")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="A-M12 Markdown 结构守卫（snapshot / verify / --replay）",
        epilog="rc: 0=通过 / 1=有丢失或变形 / 2=政策与用法错误")
    parser.add_argument("mode", nargs="?", choices=["snapshot", "verify"], default=None)
    parser.add_argument("--root", default="", help="文档树根（默认仓库根；replay 用它指向 %TEMP% 里的副本）")
    parser.add_argument("--out", default="", help=f"snapshot 落盘路径（默认 {SNAPSHOT_REL}）")
    parser.add_argument("--baseline", default="", help=f"verify 的基线（默认 {SNAPSHOT_REL}）")
    parser.add_argument("--replay", action="store_true",
                        help="用 5 类真实 R1 输入 + 4 类 F2 反向对照 + 3 类 H1 就地改写对照"
                             "在 %%TEMP%% 副本上复跑自检")
    args = parser.parse_args()

    if args.replay:
        if args.mode:
            print("STRUCTURE ERROR：--replay 不接受 mode（它自带 snapshot/verify 全流程）")
            return 2
        try:
            return cmd_replay()
        except (ReplayError, AssertionError) as exc:
            print(f"\nREPLAY FAIL: {exc}")
            return 1
    if not args.mode:
        parser.print_help()
        print("STRUCTURE ERROR：需要 mode（snapshot | verify）或 --replay")
        return 2

    root = _resolve_root(args.root) if args.root else ROOT
    try:
        if args.mode == "snapshot":
            out = _resolve_json(args.out) if args.out else ROOT / SNAPSHOT_REL
            return cmd_snapshot(root, out)
        baseline = _resolve_json(args.baseline) if args.baseline else ROOT / SNAPSHOT_REL
        return cmd_verify(root, baseline)
    except PolicyError as exc:  # 政策数据缺失/非法 → fail-closed（rc=2，与"验出丢失"的 rc=1 区分）
        print(f"STRUCTURE ERROR：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
