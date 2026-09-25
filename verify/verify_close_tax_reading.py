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
                '报告缺失显式 SKIP 与反向对照自检',
    'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0,
    'routes': [], 'requires': ['none'],
}

import argparse
import io
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

# 控制台编码兜底（本仓既有口径）：Windows 默认 GBK 遇到 `⇒`／`—` 这类字符会
# `UnicodeEncodeError` —— 那会让闸门在**打印判据**时崩掉（不是判据本身出错）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "agents" / "runs"

TAX_RE = re.compile(r"关闭税读数\s*[:：]\s*(?P<body>.+?)\s*$")
LEVEL_RE = re.compile(r"^- \*\*(critical|major|minor|nit)\b")
NUMBERED_RE = re.compile(r"^\d+\.\s")
HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
KEYS = ("code_major", "code_critical", "doc_items")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    """自检断言（显式 `raise`，`-O` 删不掉；成功打印 `PASS:` 行）。"""
    global PASSED
    if not cond:
        raise AssertionError(f"{name} FAIL: {detail}")
    PASSED += 1
    print(f"PASS: {name} {detail}")


def parse_tax_line(doc: str) -> dict | None:
    """解析机读读数行 → `{code_major, code_critical, doc_items, runs}`；无该行 → None。

    **只认第一行**（同一文档里出现两行读数 = 两套口径，后面那行不算数也不放过）。
    """
    for line in doc.splitlines():
        m = TAX_RE.search(line)
        if not m:
            continue
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
        return out
    return None


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
    doc = io.open(path, encoding="utf-8", errors="replace").read()
    declared = parse_tax_line(doc)
    if declared is None:
        print(f"CLOSE-TAX SKIP（无 `关闭税读数:` 机读行，**不是通过**）：{path.name}")
        print("  → 已声明三查锚点的 Sprint 在关闭期必须补这一行"
              "（口径见 sprint-17.md §9.5；报告缺失的环境同样只报 SKIP）")
        return 0
    runs = [r for r in declared.get("runs") or []]
    if not runs:
        print("CLOSE-TAX FAIL（1 项）：机读行缺 `来源=`"
              "——没有来源就无法派生读数")
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
    print(f"CLOSE-TAX PASS：{path.name}（声明与报告派生逐字一致："
          + ", ".join(f"{k}={actual[k]}" for k in KEYS)
          + f"；来源 {len(runs)} 个 run）")
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


def selftest() -> int:
    """夹具自检：派生口径 + 声明比对 + 五条反向对照（改数字/缺键/增删发现/节外行/报告缺失）。"""
    with tempfile.TemporaryDirectory() as td:
        runs = Path(td) / "runs"
        (runs / "run-2026-01-01-code-review-001").mkdir(parents=True)
        (runs / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT, encoding="utf-8")
        (runs / "run-2026-01-01-doc-audit-002").mkdir(parents=True)
        (runs / "run-2026-01-01-doc-audit-002" / "doc-audit.report.md").write_text(
            DOC_RPT, encoding="utf-8")
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
        (runs / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            bumped, encoding="utf-8")
        actual2, _ = derive(declared["runs"], runs_dir=runs)
        ok("反向对照 C：报告**新增 1 条 major** ⇒ 派生值 2→3 且原声明随即 FAIL",
           actual2["code_major"] == 3
           and any("code_major" in p for p in compare(declared, actual2)),
           f"actual2={actual2}")
        # （本条反向对照的由来：我第一版把新增行写在 `## One-line summary` **之后**，
        #   派生值没变——那不是工具坏了，而是**节外行不计**。把它固化成边界断言。）
        (runs / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT + "\n- **major** `a.py:9`: 节外的一行\n", encoding="utf-8")
        actual3, _ = derive(declared["runs"], runs_dir=runs)
        ok("反向对照 C2：graded **节外**的 `- **major**` 不计（口径按节切）",
           actual3["code_major"] == 2, f"actual3={actual3}")
        (runs / "run-2026-01-01-code-review-001" / "code-review.report.md").write_text(
            CODE_RPT, encoding="utf-8")
        # 未发现 critical 的说明行不计（否则离线档会凭空多一条）
        ok("反向对照 D：`本轮未发现 critical` 的说明行**不计**（说明行 ≠ 发现）",
           count_code_report(CODE_RPT).get("critical", 0) == 0)
        # 机读行解析：全角冒号 / 中文来源键 / 缺行
        parsed = parse_tax_line("关闭税读数: code_major=1 code_critical=0 doc_items=2 "
                                "来源=run-a,run-b")
        ok("解析：全角冒号 + `来源=` 中文键可读",
           parsed == {"code_major": 1, "code_critical": 0,
                      "doc_items": 2, "runs": ["run-a", "run-b"]}, f"parsed={parsed}")
        ok("解析：文档里没有机读行 ⇒ None（调用方走显式 SKIP，不是 PASS）",
           parse_tax_line("# 随便一份文档\n没有读数行\n") is None)
        # 真数据入口：报告缺失时必须**具名 FAIL/SKIP**，不得静默算 0
        _, missing = derive(["run-2999-01-01-code-review-999"], runs_dir=runs)
        ok("反向对照 E：来源 run 的报告不存在 ⇒ 具名问题（不得把'查不到'算成 0）",
           any("不存在" in p for p in missing), f"problems={missing[:1]}")
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
    if rc == 0 and "--selftest" not in sys.argv:
        pass
    return rc


if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行"
                     "（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")


if __name__ == "__main__":
    raise SystemExit(main())
