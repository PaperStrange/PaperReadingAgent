"""§6 规则机检状态闸门（A-DECL；零依赖、只读）。

`docs/1-WORKFLOW.MD` §6 的每条**编号**规则，必须在文末 §6.1 的机读状态表里恰占一行，
并声明它的失败由谁看见。判据（每条 FAIL 都点名规则号与 `文件:行`）：

  ① **覆盖**：§6 规则域里的每个编号在 6.1 表里恰一行（§6 有、表里无 ⇒ FAIL）；
  ② **词表**：状态 ∈ {machine, declared-unverifiable, manual}；`placeholder` 只允许
     出现在 §6 自陈"本行不是规则"的编号空缺上；
  ③ **脚本存在**：`machine` 行必须给出可核的仓库相对脚本路径，且文件真实存在；
  ④ **理由与日期**：`declared-unverifiable` / `manual` 行必须有非空理由 + `YYYY-MM-DD`；
  ⑤ **死行与占位**：表里出现 §6 没有的规则号 ⇒ FAIL；占位与缺号错位 ⇒ FAIL；
  ⑥ **汇总**：打印三态计数（`machine` / `declared-unverifiable` / `manual` /
     `placeholder`）——这是"哪些规则无机检"的机读答案。

规则域 = §6 内**最长的从 1 起的连续编号序列**（现读 = 行 425–461，编号 1–19；
其中 15 是行内自陈"本行不是规则"的**编号空缺**），**外加**§6 内任何编号**大于该序列
最大号**的编号条目（新规则追加在 §6 末尾也逃不掉）。**只覆盖编号规则**：§6 内
非编号的散文规则不在域内——这条边界写在 6.1 节前言里，不静默。

反向对照（`--selftest`，在 `%TEMP%` 合成副本上**真跑同一 `check()`**）：注入假规则 20 /
把 machine 行改到不存在的脚本 / 改成非法状态词 / 删掉 `declared-unverifiable` 行的
理由与日期 / 干净副本 / 死行 / 占位错位，各一条。

用法：
  .venv\\Scripts\\python.exe verify\\verify_rule_index.py
  .venv\\Scripts\\python.exe verify\\verify_rule_index.py --selftest
"""
from __future__ import annotations

VERIFY_META = {
    "features": (
        "§6 规则机检状态（A-DECL）：§6 每条编号规则在 6.1 表里恰一行、状态封闭三词、"
        "machine 行引用的脚本必须存在、declared-unverifiable/manual 必须给理由+日期、"
        "死行与占位错位判红；汇总打印三态计数；反向对照七组"
        "（假规则/坏脚本/非法词/缺理由/干净副本/死行/占位）；"
        "条数见末行 `ALL PASS (N assertions)`"
    ),
    "tier": "offline",
    "providers": [],
    "est_seconds": 3,
    "est_cost_cny": 0,
    "routes": [],
    "requires": ["none"],
}

import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.harness import finish, ok

if not __debug__:  # -O 会剥离 assert ⇒ 判据静默空转
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（判据会被剥离）")

WORKFLOW_REL = "docs/1-WORKFLOW.MD"
SECTION_RULE_RE = re.compile(r"^##\s+6\.(?!\d)")
SECTION_61_RE = re.compile(r"^##\s+6\.1(?:\s|$)")
RULE_RE = re.compile(r"^(?P<num>\d+)\.\s+(?P<body>\*\*.*)$")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SCRIPT_RE = re.compile(r"`((?:verify|scripts|src)/[\w./-]+\.(?:py|mjs|ps1|sh))`")
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")
TABLE_HEADER = ("规则号", "状态", "执行点／判据", "理由或复核日期")
STATUSES = ("machine", "declared-unverifiable", "manual")
PLACEHOLDER = "placeholder"
GAP_MARKERS = ("编号空缺", "本行不是规则")
COLUMNS = ("num", "status", "evidence", "reason")


def _read(path: Path) -> str:
    """读 UTF-8 文本，CRLF 归一为 LF。"""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _cells(line: str) -> list[str]:
    """按管道切一格 Markdown 行（表格单元格内不得含裸管道）。"""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _num_cell(cell: str) -> int | None:
    """把首列解析成规则号（允许反引号包裹）；解析不出返回 None。"""
    match = re.fullmatch(r"`?(\d+)`?", cell.strip())
    return int(match.group(1)) if match else None


def parse_rules(lines: list[str]) -> tuple[dict[int, dict], list[str]]:
    """取 §6 规则域：最长从 1 起的连续编号序列 → `{编号: {line, gap}}`。"""
    start = next((i for i, ln in enumerate(lines) if SECTION_RULE_RE.match(ln)), None)
    if start is None:
        return {}, ["[输入] 找不到 §6 标题行（`## 6. ` 且不是 6.x 子节）"]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
               len(lines))
    seq: list[tuple[int, int, str]] = []
    for i in range(start + 1, end):
        match = RULE_RE.match(lines[i])
        if match:
            seq.append((int(match.group("num")), i + 1, match.group("body")))
    best: list[tuple[int, int, str]] = []
    for pos, item in enumerate(seq):
        if item[0] != 1:
            continue
        run = [item]
        for nxt in seq[pos + 1:]:
            if nxt[0] == run[-1][0] + 1:
                run.append(nxt)
            else:
                break
        if len(run) > len(best):
            best = run
    if not best:
        return {}, ["[输入] §6 内找不到从 1 起的连续编号规则序列"]
    top = best[-1][0]
    domain = best + [item for item in seq if item[0] > top]
    rules = {}
    for num, line, body in domain:
        rules[num] = {"line": line, "gap": any(m in body for m in GAP_MARKERS)}
    return rules, []


def parse_table(lines: list[str]) -> tuple[list[dict], list[str]]:
    """取 §6.1 的第一张表 → 行清单 `[{num, status, evidence, reason, line}]`。"""
    start = next((i for i, ln in enumerate(lines) if SECTION_61_RE.match(ln)), None)
    if start is None:
        return [], ["[输入] 找不到 §6.1 标题行（`## 6.1 …`）"]
    block: list[tuple[int, str]] = []
    i = start + 1
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].lstrip().startswith("|"):
            block.append((i + 1, lines[i]))
        elif block:
            break
        i += 1
    if len(block) < 3:
        return [], [f"[输入] §6.1 的表格不足三行（表头＋分隔＋数据），"
                    f"实际 {len(block)} 行"]
    problems: list[str] = []
    header = _cells(block[0][1])
    if tuple(header) != TABLE_HEADER:
        problems.append(f"[表头] {WORKFLOW_REL}:{block[0][0]} 表头是 {header}，"
                        f"应为 {list(TABLE_HEADER)}（机读真源的列序不得改）")
    if not SEPARATOR_RE.match(block[1][1].strip()):
        problems.append(f"[表头] {WORKFLOW_REL}:{block[1][0]} 第二行不是分隔行")
    rows: list[dict] = []
    for line_no, line in block[2:]:
        cells = _cells(line)
        if len(cells) != len(TABLE_HEADER):
            problems.append(f"[表结构] {WORKFLOW_REL}:{line_no} 单元格 "
                            f"{len(cells)} 个 ≠ {len(TABLE_HEADER)}（多/少一格）")
            continue
        rows.append({"num": _num_cell(cells[0]), "status": cells[1],
                     "evidence": cells[2], "reason": cells[3], "line": line_no})
    return rows, problems


def check(path: Path, root: Path = ROOT) -> tuple[list[str], dict[str, int]]:
    """读一份 `1-WORKFLOW.MD` 判六条判据，返回 `(问题清单, 三态计数)`。"""
    if not path.is_file():
        return [f"[输入] 文件不存在：{path}"], {}
    lines = _read(path).splitlines()
    rules, problems = parse_rules(lines)
    rows, table_problems = parse_table(lines)
    problems += table_problems
    counts = {status: 0 for status in STATUSES}
    counts[PLACEHOLDER] = 0
    by_num: dict[int, list[dict]] = {}
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] += 1
        num = row["num"]
        if num is not None:
            by_num.setdefault(num, []).append(row)

    for num, meta in sorted(rules.items()):
        got = by_num.get(num, [])
        if not got:
            problems.append(f"[① 覆盖] 规则 {num}（{WORKFLOW_REL}:{meta['line']}）"
                            f"在 §6.1 表里没有行 —— 新规则不声明状态就红")
        elif len(got) > 1:
            where = "、".join(str(r["line"]) for r in got)
            problems.append(f"[① 覆盖] 规则 {num} 在 §6.1 表里出现 {len(got)} 次"
                            f"（行 {where}）—— 每条规则应恰一行")

    for row in rows:
        num, status = row["num"], row["status"]
        where = f"{WORKFLOW_REL}:{row['line']}"
        if status not in STATUSES and status != PLACEHOLDER:
            problems.append(f"[② 词表] 规则 {num}（{where}）状态 {status!r} 不在三词表 "
                            f"{list(STATUSES)} 里")
        if status == "machine":
            scripts = SCRIPT_RE.findall(row["evidence"] + " " + row["reason"])
            if not scripts:
                problems.append(f"[③ 脚本] 规则 {num}（{where}）声明 machine 却没有给出"
                                f"可核的仓库相对脚本路径（`verify/…` 或 `scripts/…`）")
            for rel in scripts:
                if not (root / rel).is_file():
                    problems.append(f"[③ 脚本] 规则 {num}（{where}）引用的脚本 "
                                    f"{rel} 不存在 —— machine 行的执行点必须真实存在")
        if status in ("declared-unverifiable", "manual"):
            reason = row["reason"].strip()
            rest = DATE_RE.sub("", reason).strip(" —-（）()")
            if not reason or reason in ("—", "-"):
                problems.append(f"[④ 理由] 规则 {num}（{where}）状态 {status} 却"
                                f"没有理由")
            elif not DATE_RE.search(reason):
                problems.append(f"[④ 日期] 规则 {num}（{where}）状态 {status} 的理由"
                                f"缺 `YYYY-MM-DD` 复核日期")
            elif len(rest) < 4:
                problems.append(f"[④ 理由] 规则 {num}（{where}）只写了日期、没有"
                                f"理由内容")

    for num, got in sorted(by_num.items()):
        where = "、".join(str(r["line"]) for r in got)
        for row in got:
            if num not in rules:
                problems.append(f"[⑤ 死行] §6.1 表里的规则 {num}"
                                f"（{WORKFLOW_REL}:{row['line']}）在 §6 里不存在"
                                f" —— 表里有、§6 没有即死行")
            elif rules[num]["gap"] and row["status"] != PLACEHOLDER:
                problems.append(f"[⑤ 占位] 规则 {num}（{where}）在 §6 里是"
                                f"**编号空缺占位**，表里状态却是 {row['status']}"
                                f"（应 {PLACEHOLDER}）")
            elif not rules[num]["gap"] and row["status"] == PLACEHOLDER:
                problems.append(f"[⑤ 占位] 规则 {num}（{where}）在 §6 里是一条实规则，"
                                f"却被标成 {PLACEHOLDER}")
    return problems, counts


def _by(problems: list[str], prefix: str) -> list[str]:
    """按判据前缀取问题子集。"""
    return [p for p in problems if p.startswith(prefix)]


def _brief(problems: list[str]) -> str:
    """一条详情串（首两条问题；空 ⇒ `0 条`）。"""
    return "；".join(problems[:2]) if problems else "0 条"


def _has(problems: list[str], prefix: str, *needles: str) -> bool:
    """是否存在一条问题：以 prefix 开头且含全部 needles。"""
    return any(p.startswith(prefix) and all(n in p for n in needles)
               for p in problems)


def _count_line(counts: dict[str, int]) -> str:
    """三态计数的机读汇总行（本闸门唯一的汇总口径，别处不手抄）。"""
    total = sum(counts.values())
    parts = " / ".join(f"{status}={counts[status]}" for status in
                       (*STATUSES, PLACEHOLDER))
    return f"三态计数：{parts}（6.1 表共 {total} 行）"


def run_real() -> None:
    """真数据：打印问题与三态计数，逐判据断言（soft：失败仍跑完反向对照）。"""
    problems, counts = check(ROOT / WORKFLOW_REL)
    print(f"扫描 {WORKFLOW_REL}：§6 编号规则与 §6.1 表")
    for problem in problems:
        print(f"  - {problem}")
    print(_count_line(counts) if counts else "三态计数：解析失败（无计数）")
    ok("① §6 每条编号规则在 6.1 表里恰一行",
       not _by(problems, "[①"), _brief(_by(problems, "[①")), soft=True)
    ok("② 状态词表封闭（三词；placeholder 只给缺号）",
       not _by(problems, "[②"), _brief(_by(problems, "[②")), soft=True)
    ok("③ machine 行引用的脚本都存在",
       not _by(problems, "[③"), _brief(_by(problems, "[③")), soft=True)
    ok("④ declared-unverifiable/manual 都有理由与日期",
       not _by(problems, "[④"), _brief(_by(problems, "[④")), soft=True)
    ok("⑤ 无死行、占位只落在缺号上",
       not _by(problems, "[⑤"), _brief(_by(problems, "[⑤")), soft=True)
    ok("⑥ 表非空且三态计数覆盖全部数据行",
       sum(counts.values()) > 0, _count_line(counts) if counts else "空表", soft=True)


def _mutate_row(text: str, num: int, **fields: str) -> str:
    """把表里规则 `num` 那一行的指定列替换掉（缺行/多行 ⇒ 夹具错误）。"""
    lines = text.splitlines()
    hits = [i for i, ln in enumerate(lines) if ln.startswith(f"| {num} | ")]
    if len(hits) != 1:
        raise SystemExit(f"selftest 夹具错误：规则 {num} 命中 {len(hits)} 行")
    cells = _cells(lines[hits[0]])
    if len(cells) != len(COLUMNS):
        raise SystemExit(f"selftest 夹具错误：规则 {num} 行 {len(cells)} 格")
    for key, value in fields.items():
        cells[COLUMNS.index(key)] = value
    lines[hits[0]] = "| " + " | ".join(cells) + " |"
    return "\n".join(lines) + "\n"


def _append_row(text: str, row: str) -> str:
    """在 6.1 表的最后一行之后追加一行（找不到表行 ⇒ 夹具错误）。"""
    lines = text.rstrip("\n").splitlines()
    hits = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("|")]
    if not hits:
        raise SystemExit("selftest 夹具错误：副本里找不到表格行")
    lines.insert(hits[-1] + 1, row)
    return "\n".join(lines) + "\n"


def selftest() -> None:
    """在 `%TEMP%` 合成副本上真跑 `check()` 的七组反向对照。"""
    clean = _read(ROOT / WORKFLOW_REL)
    with tempfile.TemporaryDirectory(prefix="rule-index-") as td:
        base = Path(td)
        # 每份副本用**字面文件名**写盘（落点可静态判定为 %TEMP%，
        # `verify/verify_artifact_paths.py` 的动态目标棘轮要求）。
        (base / "clean.md").write_text(clean, encoding="utf-8", newline="\n")
        problems, counts = check(base / "clean.md")
        ok("(f) 干净副本 ⇒ PASS（0 问题，三态计数非空）",
           not problems and sum(counts.values()) > 0, _brief(problems))

        injected = clean.replace(
            "## 6.0 机制索引",
            "20. **假规则（selftest 注入）**：这行只用于反向对照。\n\n"
            "## 6.0 机制索引", 1)
        (base / "fake-rule.md").write_text(injected, encoding="utf-8", newline="\n")
        problems, _ = check(base / "fake-rule.md")
        ok("(a) §6 注入假规则 20 ⇒ ① FAIL 并点名规则 20",
           _has(problems, "[①", "规则 20"), _brief(_by(problems, "[①")))

        bad_script = _mutate_row(
            clean, 10, evidence="`verify/verify_rule_index_missing.py`：不存在")
        (base / "bad-script.md").write_text(bad_script, encoding="utf-8", newline="\n")
        problems, _ = check(base / "bad-script.md")
        ok("(b) machine 行改到不存在的脚本 ⇒ ③ FAIL 并点名该路径",
           _has(problems, "[③", "verify_rule_index_missing.py"),
           _brief(_by(problems, "[③")))

        bad_word = _mutate_row(clean, 10, status="auto")
        (base / "bad-word.md").write_text(bad_word, encoding="utf-8", newline="\n")
        problems, _ = check(base / "bad-word.md")
        ok("(c) 状态改成非法词 auto ⇒ ② FAIL 并点名 auto",
           _has(problems, "[②", "auto"), _brief(_by(problems, "[②")))

        stripped = _mutate_row(clean, 3, reason="—")
        (base / "no-reason.md").write_text(stripped, encoding="utf-8", newline="\n")
        problems, _ = check(base / "no-reason.md")
        ok("(d) 删掉 declared-unverifiable 行的理由/日期 ⇒ ④ FAIL 并点名规则 3",
           _has(problems, "[④", "规则 3"), _brief(_by(problems, "[④")))

        dead = _append_row(clean, "| 99 | manual | — | 死行探针（2026-11-13） |")
        (base / "dead-row.md").write_text(dead, encoding="utf-8", newline="\n")
        problems, _ = check(base / "dead-row.md")
        ok("(e) 表里多出 §6 没有的规则 99 ⇒ ⑤ FAIL 并点名死行",
           _has(problems, "[⑤", "99"), _brief(_by(problems, "[⑤")))

        misplaced = _mutate_row(clean, 14, status=PLACEHOLDER)
        (base / "placeholder.md").write_text(misplaced, encoding="utf-8", newline="\n")
        problems, _ = check(base / "placeholder.md")
        ok("(g) 把实规则 14 标成 placeholder ⇒ ⑤ FAIL 并点名占位错位",
           _has(problems, "[⑤", "规则 14", PLACEHOLDER),
           _brief(_by(problems, "[⑤")))


def main() -> int:
    """CLI 入口：默认真数据 ＋ 反向对照；`--selftest` 只跑反向对照。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="§6 规则机检状态闸门（A-DECL）")
    parser.add_argument("--selftest", action="store_true",
                        help="只跑 %TEMP% 合成副本上的反向对照")
    args = parser.parse_args()
    if not args.selftest:
        run_real()
    selftest()
    return finish("verify_rule_index.py")


if __name__ == "__main__":
    sys.exit(main())
