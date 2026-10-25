#!/usr/bin/env python3
"""关闭税读数**必须由工具派生**（`TG-19` M-E；`TG-6` 四件套：命令/输出/rc/反向对照）。

**要治的是什么**（2026-09-25 实测事故）：`M1 关闭税`（`code major` / `文档项`）
是 G2 的头号指标，但它的读数此前**只能手抄**——Sprint-17 的记录里因此抄进了
**上一个 Sprint** 的数字（文档项 `12` 实为 `11`、"19 条"实为 `21`），
而两个 Sprint 的 must-fix 数恰好都是 8，抄错后**算术自洽**，连一查都没抓到
（见 `sprint-17.md` §9.5 与机制反例档案例 9）。

**机制**：Sprint 文档里放一行**机读**读数（口径见 §9.5）：

    关闭税读数: code_major=7 code_critical=3 doc_items=11 来源=<run_id>,…

本闸门**从这些 run 的报告文件重新派生**同一组数字，并与该行**逐字比较**：

* `code_major` / `code_critical`：`code-review` 报告 `## Graded findings` 节内
  `^- **<级别>**` 开头的**行数**（"本轮未发现 critical"这类**说明行不计**）；
* `doc_items`：`doc-audit` 报告 `## Must fix` + `## Should fix` 两节内
  `^\\d+\\.` 的**编号条数**。

**退出码**：0=通过或显式 SKIP；1=读数与报告不一致（逐项点名）；
2=文档不可解析/无该行（fail-closed）。
**镜像**：`--sprint <doc>` 真数据模式；无参 = 自检（夹具 + 反向对照）。
报告目录 `agents/runs/**` 被 `.gitignore` 忽略 ⇒ 全新 checkout 没有它，
本闸门按同一口径走**显式 SKIP**（不是 PASS）。
"""

from __future__ import annotations

VERIFY_META = {
    'features': '关闭税读数机器派生（TG-19 M-E）：从 code-review / doc-audit 报告重新'
                '派生 code_major / code_critical / doc_items，并要求 Sprint 文档的'
                '机读读数行与之逐字一致（禁止手抄）；含缺失行 fail-closed、'
                '报告缺失显式 SKIP 与反向对照自检；另核**复盘 §5 的状态计数可解析**'
                '（`状态码` 列收敛五元词表／机读声明计数＝逐行实数／§5.0 逐行清单与之'
                '逐行对钉／凡 `已修` 行必须能指到落地提交）',
    'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0,
    'routes': [], 'requires': ['none'],
}

import argparse
import io
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

# 本闸门要解析**复盘 §5 表**（状态计数档），故复用 `verify_md_tables` 的**同一套**
# 切分器：`\|` 是内容、裸 `|` 才是分隔。**不另写一份**——两份切分器必然漂移
# （复盘行 7 的教训：同一口径两份实现）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verify.agent_policy import path_in_head                    # noqa: E402
from verify.verify_md_tables import split_row as _split_row     # noqa: E402

# 控制台编码兜底（本仓既有口径）：Windows 默认 GBK 遇到 `⇒`／`—` 这类字符会
# `UnicodeEncodeError` —— 那会让闸门在**打印判据**时崩掉（不是判据本身出错）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "agents" / "runs"

TAX_RE = re.compile(r"^[ \t]*关闭税读数\s*[:：]\s*(?P<body>.+?)\s*$", re.MULTILINE)
# "该文档自称已关闭"的判据：声明了**真锚点**（十六进制）或 §9 有 run 表行。
# 为什么要它：读数行**缺失**时不能一律 SKIP——已关闭的 Sprint 必须补这一行
# （2026-09-25 独立复核 `run-…083` major/minor：删掉读数行即 rc=0，
# 等于给"没写读数"开后门）。
ANCHOR_RE = re.compile(r"三查锚点\s*[:：]\s*`?([0-9a-fA-F]{7,40})`?")
RUN_ROW_RE = re.compile(r"^\s*\|\s*run-", re.MULTILINE)
LEVEL_RE = re.compile(r"^- \*\*(critical|major|minor|nit)\b")
NUMBERED_RE = re.compile(r"^\d+\.\s")
HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
KEYS = ("code_major", "code_critical", "doc_items")

# 夹具落点**必须可静态判定**（`verify_artifact_paths.py` 的政策）：落点写成
# "`Path(tempfile.mkdtemp(...))` 的**单次局部赋值** + 字面量段"（行 8 起改为唯一名，
# 并发不互踩）。挂函数参数/argv 会被判"动态目标"（新脚本出现即 FAIL；2026-09-25
# 实测踩过两次）；同一名字多处赋值也会判不动，故全文只赋值一次。

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    """自检断言（显式 `raise`，`-O` 删不掉；成功打印 `PASS:` 行）。"""
    global PASSED
    if not cond:
        raise AssertionError(f"{name} FAIL: {detail}")
    PASSED += 1
    print(f"PASS: {name} {detail}")


def parse_tax_line(doc: str) -> tuple[dict | None, list[int]]:
    """解析机读读数行 → `({...} | None, 命中行号)`。

    **行首锚定**（`^[ \\t]*关闭税读数…`）：正文里顺带提一句
    "关闭税读数: code_major=…"**不算**读数行
    ——否则一句叙述就能顶替机读行（2026-09-25 独立复核 major：
    `TAX_RE` 原无行首锚点、且只认第一处匹配，
    实测在真行**之前**写一句同形叙述即可让闸门 `PASS`，而底部的真读数行从未被读）。
    调用方负责：**命中 ≠ 1 行**时的判定（0 行 = 缺读数；≥2 行 = 两套口径）
    ——二者都不是"通过"。
    """
    hits = [(i, m) for i, line in enumerate(doc.splitlines(), 1)
            for m in [TAX_RE.match(line)] if m]
    if not hits:
        return None, []
    lineno, m = hits[0]
    body = m.group("body")
    out: dict = {"runs": []}
    for token in body.replace("；", " ").split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        key = key.strip()
        if key in KEYS:
            out[key] = int(value) if value.strip().lstrip("-").isdigit() else value
        elif key in ("来源", "runs"):
            out["runs"] = [r for r in re.split(r"[,\s]+", value) if r]
    return out, [ln for ln, _ in hits]


def claims_closure(doc: str) -> bool:
    """文档是否自称已关闭（声明真锚点 或 §9 有 run 行）
    ——决定"缺读数行"是 FAIL 还是 SKIP。"""
    return bool(ANCHOR_RE.search(doc)) or bool(RUN_ROW_RE.search(doc))


# ------------------------------------------------- 状态计数可解析（本批新增）
#
# 要治的是什么（`run-2026-09-30-implementation-110` 的派单问题 A）：复盘 §5 的
# "未闭环项"表有 51 行，**状态此前不可机读**——状态词混在长句子里，于是两个 agent
# 对同一张表数出了两套结果，而"零未闭环项"的结论正建立在这套计数上。
#
# 处置：给 §5 表加**独立机读列 `状态码`**（词表收敛五元）＋ 一行**机读声明**
# （`状态计数: 已修=N …`）＋ §5.0 逐行清单（`行｜状态｜落地提交/run｜依据`）。
# 本档的判据把三处**逐行对钉**：任一处改了而另两处没改 ⇒ FAIL。
# 口径同 `TG-19` M-E：**读数必须由工具派生，禁止手抄**。
STATUS_TOKENS = ("已修", "未修", "部分", "只报", "用户豁免")
STATUS_TABLE_HEADER = ("#", "项", "来源", "状态说明（依据）", "状态码")
STATUS_DETAIL_HEADER = ("行", "状态", "落地提交/run", "依据（可复跑）")
RETRO_REL = ("docs/iteration/phases/testing-governance/"
             "2026-09-26-g2-close-retro.MD")
# 机读声明行。用 `search`（不是 `match`）：真行形如
# `> **状态计数（机读，…）**：状态计数: 已修=46 …`——行首那段 `状态计数（` 后面
# 不是冒号，故只会在**第二处**命中（这一条是本档写第一版时踩过的坑）。
STATUS_COUNT_RE = re.compile(r"状态计数\s*[:：]\s*(?P<body>.+?)\s*$")
# "落地提交/run" 的机检形态：sha（≥7 位十六进制）或 `run-<日期>-…`。
LANDING_RE = re.compile(r"(?:\b[0-9a-f]{7,40}\b|run-\d{4}-\d{2}-\d{2}-)")


def find_table(doc: str, header: tuple[str, ...]) -> tuple[list[list[str]], int]:
    """按**逐字表头**定位一张 Markdown 表 → `(数据行, 表头行号)`；找不到 ⇒ `([], 0)`。

    只认"表头逐字相等"的表：本档里 §3 A 表／§4 表／§5 表**行号重叠**（各自 1..N），
    靠表头区分才不会张冠李戴——这正是上一批数错行的机制。
    """
    lines = doc.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        if tuple(_split_row(line)) != header:
            continue
        rows: list[list[str]] = []
        for j in range(i + 1, len(lines)):
            if not lines[j].lstrip().startswith("|"):
                break
            cells = _split_row(lines[j])
            if cells and all(c and set(c) <= set("-: ") for c in cells):
                continue                      # `|---|…|` 分隔行
            rows.append(cells)
        return rows, i + 1
    return [], 0


def _leading_status(cell: str) -> str | None:
    """`状态说明` 单元格**开头**的状态词（没有 ⇒ `None`）。

    `部分已修` 归一成 `部分`（真档的历史措辞）。只认**行首**——正文中间提到别的
    状态词不算（例如"该行原记未修）"这类括注）。
    """
    text = cell.lstrip("*> \t")
    if text.startswith("部分已修"):
        return "部分"
    for tok in STATUS_TOKENS:
        if text.startswith(tok):
            return tok
    return None


def parse_status_counts(doc: str) -> tuple[dict | None, list[int]]:
    """解析机读声明行 → `({token: N, "合计": N} | None, 命中行号)`。

    命中 ≠ 1 行时的判定由调用方负责（0 行 = 无声明；≥2 行 = 两套口径）——二者都不是通过。
    """
    hits = [(i, m) for i, line in enumerate(doc.splitlines(), 1)
            for m in [STATUS_COUNT_RE.search(line)]
            if m and "=" in m.group("body")]
    if not hits:
        return None, []
    _, m = hits[0]
    out: dict = {}
    for token in m.group("body").replace("；", " ").split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        key = key.strip()
        if key in STATUS_TOKENS or key == "合计":
            out[key] = int(value) if value.strip().isdigit() else value
    return out, [ln for ln, _ in hits]


def status_count_problems(doc: str) -> list[str]:
    """§5 状态读数**可解析且自洽**（纯函数；反向对照直接驱动它）。

    五道判据：
      ① 表结构——表头逐字＝`STATUS_TABLE_HEADER`；每行 5 格；首列行号 1..N **连续**；
      ② 词表——`状态码` 列每一格 ∈ `STATUS_TOKENS`（收敛到有限集，不允许自由文本）；
      ③ 计数——机读声明行的五个词 ＋ `合计` 与**逐行实数**逐项相等（禁止手抄）；
      ④ 逐行对钉——§5.0 清单覆盖同一组行号、状态与 §5 表**逐行相同**，
         且凡 `已修` 行必须能指到具名 sha／run（"已修"不得是无签发的空话）；
      ⑤ 行内不矛盾——`状态说明` 若以状态词开头，该词必须等于 `状态码`
         （"唯一真源"不许被同一行的散文当场推翻）。
    """
    problems: list[str] = []
    rows, _hline = find_table(doc, STATUS_TABLE_HEADER)
    if not rows:
        return [f"[状态计数] 找不到带 `状态码` 列的 §5 表（表头应为 "
                f"{' | '.join(STATUS_TABLE_HEADER)}）⇒ 状态读数无从复算（fail-closed）"]
    tokens: dict[int, str] = {}
    for idx, cells in enumerate(rows, 1):
        if len(cells) != len(STATUS_TABLE_HEADER):
            problems.append(
                f"[状态计数] §5 表第 {idx} 条数据行单元格数 {len(cells)} ≠ "
                f"表头 {len(STATUS_TABLE_HEADER)}（首列 {cells[0]!r}）"
                f"——机读列被合并/多了分隔符")
            continue
        try:
            n = int(cells[0])
        except ValueError:
            problems.append(f"[状态计数] §5 表首列不是行号：{cells[0]!r}")
            continue
        tok = cells[-1]
        if tok not in STATUS_TOKENS:
            problems.append(
                f"[状态计数] 行 {n} 的状态码 {tok!r} 不在词表 {list(STATUS_TOKENS)} 内"
                f"（词表必须收敛到有限集，否则又变成自由文本）")
        # 判据⑤：**同一行内不许自相矛盾**——`状态说明` 若以状态词开头，该词必须与
        # `状态码` 相同。本批第一版就是靠这条抓到的：行 4/5/6/11/13 的说明格仍是裸
        # `未修`，而机读列已改判 `已修`（"唯一真源"当场被自己一行推翻）。
        lead = _leading_status(cells[3])
        if lead is not None and lead != tok:
            problems.append(
                f"[状态计数] 行 {n} 自相矛盾：`状态说明` 以 {lead!r} 开头，"
                f"`状态码` 却是 {tok!r}——同一行不许有两个状态")
        tokens[n] = tok
    nums = sorted(tokens)
    if nums != list(range(1, len(nums) + 1)):
        problems.append(f"[状态计数] §5 表行号必须连续 1..N：实测 {nums[:6]}…"
                        f"{nums[-3:] if nums else '（空）'}")

    declared, hit_lines = parse_status_counts(doc)
    if declared is None:
        problems.append("[状态计数] 文档里没有机读声明行"
                        "（形如 `状态计数: 已修=N … 用户豁免=N 合计=N`）⇒ 计数无从核对"
                        "（fail-closed；手抄的计数不算读数）")
    elif len(hit_lines) > 1:
        problems.append(f"[状态计数] 有 {len(hit_lines)} 行机读声明（行 {hit_lines}）"
                        f"——两行读数＝两套口径，先合并成唯一一行")
    else:
        actual = Counter(tokens.values())
        for tok in STATUS_TOKENS:
            want = declared.get(tok)
            if want is None:
                problems.append(f"[状态计数] 声明行缺 `{tok}=`——五个词一个都不能省"
                                f"（少一个就等于少一项读数）")
            elif not isinstance(want, int):
                problems.append(f"[状态计数] 声明行 `{tok}=` 不是整数：{want!r}")
            elif want != actual.get(tok, 0):
                problems.append(f"[状态计数] {tok} 声明 {want} ≠ 逐行实数 "
                                f"{actual.get(tok, 0)}（计数必须由工具派生，禁止手抄）")
        total = declared.get("合计")
        if total is None:
            problems.append("[状态计数] 声明行缺 `合计=`")
        elif total != len(tokens):
            problems.append(f"[状态计数] 合计 声明 {total} ≠ 表内行数 {len(tokens)}")

    detail, _dline = find_table(doc, STATUS_DETAIL_HEADER)
    if not detail:
        problems.append(f"[状态计数] 找不到 §5.0 逐行状态清单（表头应为 "
                        f"{' | '.join(STATUS_DETAIL_HEADER)}）⇒ 无逐行举证可对钉")
        return problems
    dm: dict[int, tuple[str, str]] = {}
    for cells in detail:
        if len(cells) != len(STATUS_DETAIL_HEADER):
            problems.append(f"[状态计数] §5.0 行 {cells[0]!r} 单元格数 "
                            f"{len(cells)} ≠ 表头 {len(STATUS_DETAIL_HEADER)}")
            continue
        try:
            n = int(cells[0])
        except ValueError:
            problems.append(f"[状态计数] §5.0 首列不是行号：{cells[0]!r}")
            continue
        dm[n] = (cells[1], cells[2])
    if sorted(dm) != nums:
        only_d = sorted(set(dm) - set(tokens))
        only_t = sorted(set(tokens) - set(dm))
        problems.append(f"[状态计数] §5.0 与 §5 表的行集合不一致："
                        f"只在 §5.0＝{only_d[:8]}，只在 §5 表＝{only_t[:8]}")
    for n in sorted(set(dm) & set(tokens)):
        dstat, dland = dm[n]
        if dstat != tokens[n]:
            problems.append(f"[状态计数] 行 {n}：§5 表状态码 {tokens[n]!r} ≠ §5.0 清单 "
                            f"{dstat!r}——同一行被两处写成了两个状态")
        if tokens[n] == "已修" and not LANDING_RE.search(dland):
            problems.append(f"[状态计数] 行 {n} 记为 `已修`，但 §5.0 的『落地提交/run』"
                            f"{dland!r} 指不到具名 sha／run"
                            f"（『已修』必须能指到落地提交，否则改判并写理由）")
    return problems


def status_count_gate() -> tuple[str, list[str]]:
    """真数据档：拿**仓库里的复盘档**跑 `status_count_problems` → `(判决, 输出行)`。

    判决三态，口径同 `verify_md_tables.coverage_problems` 的**分支差异 vs 被删**三分法：
      * `pass`——文件在，且逐行自洽；
      * `fail`——文件在但不自洽，**或**文件在 `HEAD` 里存在而工作区被删
        （被删 ≠ 分支差异）；
      * `skip`——文件既不在工作区、也不在本分支 `HEAD`（windows-only 治理子树）⇒ 该档
        无从执行；调用方据此**不得**打印 `CLOSE-TAX PASS` 横幅（`TG-19` M-B）。
    """
    retro = ROOT / RETRO_REL
    if retro.is_file():
        found = status_count_problems(io.open(retro, encoding="utf-8",
                                              errors="replace").read())
        if found:
            head = (f"CLOSE-TAX FAIL（{len(found)} 项）——复盘 §5 的状态读数"
                    f"不可解析／不自洽：{RETRO_REL}")
            return "fail", [head] + [f"  - {p}" for p in found[:20]]
        return "pass", [f"CLOSE-TAX PASS（状态计数档）：{RETRO_REL} 的 "
                        f"`状态码` 列词表合法、声明计数＝逐行实数、"
                        f"§5.0 逐行一致且 `已修` 行均有落地签发"]
    if path_in_head(ROOT, RETRO_REL):
        return "fail", [f"CLOSE-TAX FAIL（1 项）：{RETRO_REL} 在 `HEAD` 里**存在**、"
                        f"工作区却缺失 ⇒ 这是**被删**（不是分支差异）；状态读数的真源"
                        f"被删 ⇒ fail-closed"]
    return "skip", [f"CLOSE-TAX SKIP（状态计数档）：{RETRO_REL} 不在本分支"
                    f"（windows-only 治理子树）⇒ 该档未执行——**本行不是通过**"]


def count_code_report(text: str) -> Counter:
    """code-review 报告 → `Counter({级别: 行数})`（**只数 graded 节内**）。"""
    counts: Counter = Counter()
    section: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEADING_RE.match(line)
        if m:
            section = m.group("title")
            continue
        if section != "Graded findings":
            continue
        lm = LEVEL_RE.match(line)
        if not lm:
            continue
        if "未发现" in line:  # "本轮未发现 critical" 是 0 说明行，不是一条发现
            continue
        counts[lm.group(1)] += 1
    return counts


def count_doc_report(text: str) -> int:
    """doc-audit 报告 → `## Must fix` + `## Should fix` 的编号条数。"""
    total = 0
    section: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEADING_RE.match(line)
        if m:
            section = m.group("title")
            continue
        if section in ("Must fix", "Should fix") and NUMBERED_RE.match(line):
            total += 1
    return total


def report_files(run_id: str, runs_dir: Path = RUNS_DIR) -> list[Path]:
    """该 run 目录下的报告文件（不存在 ⇒ 空列表，由调用方报具名问题）。"""
    d = runs_dir / run_id
    return sorted(d.glob("*.report.md")) if d.is_dir() else []


def derive(run_ids: list[str], *, runs_dir: Path = RUNS_DIR) -> tuple[dict, list[str]]:
    """从报告文件派生读数；返回 `(读数, 问题)`。报告缺失 ⇒ 具名问题（fail-closed）。"""
    out = {k: 0 for k in KEYS}
    problems: list[str] = []
    for rid in run_ids:
        files = report_files(rid, runs_dir)
        if not files:
            problems.append(f"[派生] {rid} 的报告文件不存在"
                            f"（`{runs_dir.name}/{rid}/*.report.md`）"
                            f"⇒ 读数无从派生；报告目录被忽略时请在本机/关闭期跑")
            continue
        for path in files:
            text = io.open(path, encoding="utf-8", errors="replace").read()
            if "code-review.report.md" in path.name:
                c = count_code_report(text)
                out["code_major"] += c.get("major", 0)
                out["code_critical"] += c.get("critical", 0)
            elif "doc-audit.report.md" in path.name:
                out["doc_items"] += count_doc_report(text)
            else:
                problems.append(f"[派生] {path.name} 不是已知的报告类型"
                                f"（code-review / doc-audit）——来源列里只放这两类 run")
    return out, problems


def compare(declared: dict, actual: dict) -> list[str]:
    """声明 vs 派生逐键比较（缺键也算问题：少一项读数不得静默）。"""
    problems: list[str] = []
    for key in KEYS:
        want, got = declared.get(key), actual.get(key)
        if want is None:
            problems.append(f"[读数] 机读行缺 `{key}=`——三个键都必须写"
                            f"（缺一个就等于少一项读数）")
        elif want != got:
            delta = int(want) - int(got) if isinstance(want, int) else "?"
            problems.append(f"[读数] {key} 声明 {want} ≠ 报告派生 {got}（差 {delta}）"
                            f"——读数必须由工具派生，禁止手抄")
    return problems


def check_sprint(sprint_file: Path, *, runs_dir: Path = RUNS_DIR) -> int:
    """真数据模式：解析读数行 → 从报告派生 → 逐字比较（0 通过 / 1 不一致 / 2 不可解析）。"""
    path = Path(sprint_file)
    if not path.is_file():
        print(f"CLOSE-TAX-ERROR: Sprint 文档不存在：{path}（fail-closed）")
        return 2
    if not runs_dir.is_dir():
        print(f"CLOSE-TAX SKIP（报告目录不存在：{runs_dir}，**不是通过**）")
        print("  → `agents/runs/**` 被 .gitignore 忽略 ⇒ 全新 checkout "
              "没有它是正常状态；"
              "读数派生是**本机/关闭期动作**。")
        return 0
    doc = io.open(path, encoding="utf-8", errors="replace").read()
    declared, hit_lines = parse_tax_line(doc)
    if len(hit_lines) > 1:
        print(f"CLOSE-TAX FAIL（1 项）：文档里有 **{len(hit_lines)} 行**机读读数"
              f"（行 {hit_lines}）——两行读数 = 两套口径，先合并成唯一一行")
        return 1
    if declared is None:
        if claims_closure(doc):
            print(f"CLOSE-TAX FAIL（1 项）：{path.name} 自称已关闭"
                  f"（声明了真锚点或 §9 有 run 行）却没有 `关闭税读数:` 机读行"
                  f"——关闭期必须补这一行（口径见 sprint-17.md §9.5）")
            return 1
        print(f"CLOSE-TAX SKIP（未自称关闭、也无读数行，**不是通过**）：{path.name}")
        return 0
    runs = [r for r in declared.get("runs") or []]
    if not runs:
        print("CLOSE-TAX FAIL（1 项）：机读行缺 `来源=`——没有来源就无法派生读数")
        return 1
    actual, problems = derive(runs)
    problems += compare(declared, actual)
    if problems:
        print(f"CLOSE-TAX FAIL（{len(problems)} 项）——声明 vs 报告派生：")
        print(f"  声明 = " + ", ".join(f"{k}={declared.get(k)}" for k in KEYS))
        print(f"  派生 = " + ", ".join(f"{k}={actual[k]}" for k in KEYS))
        for p in problems[:20]:
            print(f"  - {p}")
        return 1
    # 状态计数档（本批新增）：复盘 §5 的"未闭环项"状态必须**可机读且自洽**——
    # 它正是"零未闭环项"这条关闭结论的读数来源，不核它等于把结论建在手抄数字上。
    verdict, lines = status_count_gate()
    for line in lines:
        print(line)
    if verdict == "fail":
        return 1
    if verdict == "skip":
        # M-B：SKIP 档**不得**打印 `CLOSE-TAX PASS` 横幅，也不打印 `EVIDENCE:`
        # （证据行只属于"判据真的跑过且通过"）。
        print(f"CLOSE-TAX SKIP（读数档通过，但状态计数档在本分支无从执行）"
              f"——**本档不是通过**：{path.name}")
        return 0
    print(f"CLOSE-TAX PASS：{path.name}（声明与报告派生逐字一致："
          + ", ".join(f"{k}={actual[k]}" for k in KEYS)
          + f"；来源 {len(runs)} 个 run）")
    # 真数据 PASS 档也要机读证据行（二查 `run-…-087` minor 6：`1-WORKFLOW.MD:387` 的
    # "证据形态四件套"要求新闸门给 `EVIDENCE:` 行，而此前只有自检档打印）
    print(f"EVIDENCE: verify_close_tax_reading.py rc=0 "
          f"mode=real-data "
          + " ".join(f"{k}={actual[k]}" for k in KEYS)
          + f" sources={len(runs)}（断言数只在自检档有意义，此处不写死）")
    return 0


# --------------------------------------------------------- 自检（夹具 + 反向对照）

CODE_RPT = """# code-review report (fixture)

## Graded findings

- **critical** — 本轮未发现 critical（离线档默认关闭）
- **major** `a.py:1`: 第一条 major
- **major** `a.py:2`: 第二条 major
- **minor** `a.py:3`: 一条 minor

## One-line summary

ok
"""

DOC_RPT = """# doc-audit report (fixture)

## Must fix

1. 第一条必修
2. 第二条必修

## Should fix

1. 一条应修

## Verified consistent (for reference)

- 无
"""

# 状态计数档的夹具：模拟复盘 §5 的**三处结构**（机读列 ＋ 声明行 ＋ 逐行清单）。
# 注意第一处 `状态计数（机读…）` **不带冒号**——真档就长这样，而它曾经让第一版
# 正则用 `match` 时恰好命中错位置；夹具把它固定成回归样本。
STATUS_FIXTURE_DECL = ("> **状态计数（机读，2026-01-01 现跑）**："
                       "状态计数: 已修=1 未修=1 部分=0 只报=1 用户豁免=0 合计=3")
STATUS_FIXTURE = """# 复盘（夹具）

## 5. 未闭环项

| # | 项 | 来源 | 状态说明（依据） | 状态码 |
|---|---|---|---|---|
| 1 | 甲项 | 一查 | **已修**（`abc1234`）：修好了 | 已修 |
| 2 | 乙项 | 一查 | 未修 | 未修 |
| 3 | 丙项 | 一查 | **只报**（原因：体例） | 只报 |

""" + STATUS_FIXTURE_DECL + """

### 5.0 逐行状态清单

| 行 | 状态 | 落地提交/run | 依据（可复跑） |
|---|---|---|---|
| 1 | 已修 | `abc1234` | 该提交触及甲项 |
| 2 | 未修 | — | 无落地提交 |
| 3 | 只报 | `P6` 裁定 | 具名技术债（父代理裁定） |
"""


def selftest() -> int:
    """夹具自检：派生口径 + 声明比对 + 五条反向对照（改数字/缺键/增删发现/节外行/报告缺失）。"""
    # 行 8：夹具落点 = **run 级唯一目录**（`mkdtemp`）。原实现写死
    # `%TEMP%/close-tax-fixture`：并发实例一开跑就 `rmtree` 掉该目录，
    # 本实例写到一半的夹具随之消失（实测两真实例同跑 ⇒ PermissionError）。
    # 回收语义：`finally` 里显式 `rmtree`（`mkdtemp` 不自动回收）。
    tax_root = Path(tempfile.mkdtemp(prefix="close-tax-fixture-"))
    try:
        # 落点写成"单条表达式"（`tax_root` + 字面量段）：`tax_root` 是 `mkdtemp`
        # 的直接结果且全文只赋值一次，闸门才判得动落点（见本文件顶部注释）。
        (tax_root / "runs"
         / "run-2026-01-01-code-review-001").mkdir(parents=True)
        (tax_root / "runs"
         / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT, encoding="utf-8")
        (tax_root / "runs"
         / "run-2026-01-01-doc-audit-002").mkdir(parents=True)
        (tax_root / "runs"
         / "run-2026-01-01-doc-audit-002" / "doc-audit.report.md").write_text(
            DOC_RPT, encoding="utf-8")
        runs = tax_root / "runs"
        declared = {"code_major": 2, "code_critical": 0, "doc_items": 3,
                    "runs": ["run-2026-01-01-code-review-001",
                             "run-2026-01-01-doc-audit-002"]}

        actual, problems = derive(declared["runs"], runs_dir=runs)
        ok("派生：夹具两个 run 的报告 → code_major=2 / code_critical=0 / doc_items=3",
           actual == {"code_major": 2, "code_critical": 0, "doc_items": 3}
           and not problems, f"actual={actual} problems={problems[:1]}")
        ok("正向对照：声明与派生一致 ⇒ 无问题（防假红）",
           compare(declared, actual) == [], f"problems={compare(declared, actual)[:1]}")
        bumped_declared = {**declared, "code_major": 3}
        ok("反向对照 A：把记录里的数字改 1（code_major 2→3）⇒ FAIL 且点名差值",
           any("code_major" in p and "差" in p
               for p in compare(bumped_declared, actual)),
           f"problems={compare(bumped_declared, actual)[:1]}")
        dropped = {k: v for k, v in declared.items() if k != "code_critical"}
        ok("反向对照 B：缺一个键（不写 code_critical）⇒ FAIL（少一项读数不得静默）",
           any("code_critical" in p for p in compare(dropped, actual)))
        # 报告增删 1 条 ⇒ 派生值必须跟着变（否则就是"工具读死值"）
        bumped = CODE_RPT.replace(
            "\n## One-line summary",
            "\n- **major** `a.py:9`: 新增的一条 major\n\n## One-line summary")
        (tax_root / "runs"
         / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            bumped, encoding="utf-8")
        actual2, _ = derive(declared["runs"], runs_dir=runs)
        ok("反向对照 C：报告**新增 1 条 major** ⇒ 派生值 2→3 且原声明随即 FAIL",
           actual2["code_major"] == 3
           and any("code_major" in p for p in compare(declared, actual2)),
           f"actual2={actual2}")
        # （本条反向对照的由来：我第一版把新增行写在 `## One-line summary` **之后**，
        #   派生值没变——那不是工具坏了，而是**节外行不计**。把它固化成边界断言。）
        (tax_root / "runs"
         / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT + "\n- **major** `a.py:9`: 节外的一行\n", encoding="utf-8")
        actual3, _ = derive(declared["runs"], runs_dir=runs)
        ok("反向对照 C2：graded **节外**的 `- **major**` 不计（口径按节切）",
           actual3["code_major"] == 2, f"actual3={actual3}")
        (tax_root / "runs"
         / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT, encoding="utf-8")
        # 未发现 critical 的说明行不计（否则离线档会凭空多一条）
        ok("反向对照 D：`本轮未发现 critical` 的说明行**不计**（说明行 ≠ 发现）",
           count_code_report(CODE_RPT).get("critical", 0) == 0)
        # 机读行解析：全角冒号 / 中文来源键 / 缺行
        # 机读行解析：行首锚定 / 全角冒号 / 中文来源键 / 缺行 / 两行
        parsed, lines = parse_tax_line(
            "关闭税读数: code_major=1 code_critical=0 doc_items=2 "
            "来源=run-a,run-b")
        ok("解析：全角冒号 + `来源=` 中文键可读（并返回命中行号）",
           parsed == {"code_major": 1, "code_critical": 0,
                      "doc_items": 2, "runs": ["run-a", "run-b"]}
           and lines == [1], f"parsed={parsed} lines={lines}")
        mid, mid_lines = parse_tax_line(
            "本节按 `关闭税读数: code_major=999 来源=run-x` 的口径复算。\n")
        ok("反向对照 A2（复核 major 的原始探针）：**行中**的同形叙述**不算**读数行"
           "（行首锚定；否则一句正文就能顶替机读行）",
           mid is None and mid_lines == [], f"parsed={mid} lines={mid_lines}")
        two, two_lines = parse_tax_line(
            "关闭税读数: code_major=7 code_critical=3 doc_items=11 来源=run-a\n"
            "关闭税读数: code_major=999 code_critical=0 doc_items=0 来源=run-b\n")
        ok("反向对照 A3：两行读数 ⇒ 命中 2 行（调用方据此 FAIL，不当'只认第一行'放行）",
           two_lines == [1, 2] and two is not None, f"lines={two_lines}")
        ok("解析：文档里没有读数行 ⇒ (None, [])",
           parse_tax_line("# 随便一份文档\n没有读数行\n") == (None, []))
        ok("自称关闭的判据：真锚点 ⇒ True；无锚点无 run 行 ⇒ False",
           claims_closure("三查锚点: `a89b2821`\n") is True
           and claims_closure(
               "| run-2026-09-25-code-review-083 | code-review |\n") is True
           and claims_closure("# 草稿\n今天没做什么\n") is False)
        # 真数据入口：报告缺失时必须**具名 FAIL/SKIP**，不得静默算 0
        _, missing = derive(["run-2999-01-01-code-review-999"], runs_dir=runs)
        ok("反向对照 E：来源 run 的报告不存在 ⇒ 具名问题（不得把'查不到'算成 0）",
           any("不存在" in p for p in missing), f"problems={missing[:1]}")

        # ---- 状态计数档（本批新增）：纯函数 ＋ 六条反向对照 ------------------
        ok("状态计数：夹具文档（§5 表 ＋ 机读声明 ＋ §5.0 清单三处一致）⇒ 零问题",
           status_count_problems(STATUS_FIXTURE) == [],
           f"{status_count_problems(STATUS_FIXTURE)[:1]}")
        ok("状态计数：声明行的两处 `状态计数` 只在**带冒号**那处命中"
           "（行首那段 `状态计数（机读）` 不得被当成读数行）",
           parse_status_counts(STATUS_FIXTURE)[1] == [11],
           f"hits={parse_status_counts(STATUS_FIXTURE)[1]}")
        ok("状态计数反证①：声明把 `已修=1` 改成 `已修=2` ⇒ FAIL 且点名差值"
           "（禁止手抄计数）",
           any("已修" in p and "逐行实数" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("已修=1 未修=1", "已修=2 未修=1"))))
        ok("状态计数反证②：某行状态码写成词表外的自由文本（`已修好`）⇒ FAIL",
           any("不在词表" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("修好了 | 已修 |", "修好了 | 已修好 |"))))
        ok("状态计数反证③：删掉机读声明行 ⇒ FAIL（没有声明就无从核对，不是放行）",
           any("没有机读声明行" in p for p in status_count_problems(
               STATUS_FIXTURE.replace(STATUS_FIXTURE_DECL + "\n", ""))))
        ok("状态计数反证④：§5.0 与 §5 表把同一行写成两个状态 ⇒ FAIL"
           "（唯一真源被两处写岔）",
           any("两个状态" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("| 2 | 未修 | — | 无落地提交 |",
                                      "| 2 | 已修 | — | 无落地提交 |"))))
        ok("状态计数反证⑤：记为 `已修` 但 §5.0 的落地提交栏是 `—` ⇒ FAIL"
           "（『已修』必须能指到落地提交）",
           any("指不到具名" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("| 1 | 已修 | `abc1234` |", "| 1 | 已修 | — |"))))
        ok("状态计数反证⑥：把 `状态码` 列整列删掉（表退化成 4 列）⇒ FAIL"
           "（找不到机读列，fail-closed）",
           any("找不到带 `状态码` 列" in p for p in status_count_problems(
               STATUS_FIXTURE.replace(" | 状态码 |", " |").replace(
                   " | 已修 |", " |").replace(" | 未修 |", " |").replace(
                   " | 只报 |", " |"))))
        # 判据⑤ 的反向对照（本批第一版**真的**踩过：机读列已改判 `已修`，而说明格
        # 仍是裸 `未修` ⇒ 同一行两个状态）。两个样本：裸词、以及 `部分已修` 归一形态。
        ok("状态计数反证⑦：说明格以**与状态码相反**的状态词开头"
           "（`未修` vs 机读 `已修`）⇒ FAIL（行内不许自相矛盾）",
           any("自相矛盾" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("| **已修**（`abc1234`）：修好了 | 已修 |",
                                      "| 未修 | 已修 |"))))
        ok("状态计数反证⑦′：`部分已修` 归一为 `部分` 后与机读列比对"
           "（措辞变体不得绕过这条判据）",
           _leading_status("**部分已修**；基准漂移") == "部分"
           and _leading_status("已修（`abc1234`）") == "已修"
           and _leading_status("该行原记未修") is None
           and any("自相矛盾" in p for p in status_count_problems(
               STATUS_FIXTURE.replace("| **已修**（`abc1234`）：修好了 | 已修 |",
                                      "| **部分已修** | 已修 |"))))
    finally:
        shutil.rmtree(tax_root, ignore_errors=True)
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    """CLI：`--sprint <doc>` 真数据模式；无参 = 自检（与其余闸门同构）。"""
    ap = argparse.ArgumentParser(description="关闭税读数机器派生（TG-19 M-E）")
    ap.add_argument("--sprint", default="", help="Sprint 文档路径（真数据模式）")
    args = ap.parse_args()
    if "--selftest" in sys.argv or not args.sprint:
        rc = selftest()
        if rc == 0:
            print(f"EVIDENCE: verify_close_tax_reading.py assertions={PASSED} "
                  f"rc=0 mode=selfcheck")
        return rc
    rc = check_sprint(Path(args.sprint))
    return rc


if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行"
                     "（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")


if __name__ == "__main__":
    raise SystemExit(main())
