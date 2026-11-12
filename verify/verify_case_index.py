"""A-CASE 形态↔主案例一致性闸门（零依赖、只读）。

扫两份反例语料档的 `## 案例 N` 标题行，解析两种标记：
`**形态**：F/G<n>｜<形名>｜主案例 `#N`` 与 `同形态见主案例 `#N``，
对照卡 `cards/A-CASE.md` 的形态清单表判五条：

  ① 每个案例都有形态标签（漏标即 FAIL，逐条点名文件:行）；
  ② 每个形态码恰 1 个主案例，且次要案例的指针指向该主案例；
  ③ 主案例 heading 的形名、卡片表的主案例列与表一致（表是真源）；
  ④ 表里的码在语料里至少出现一次（死码即 FAIL）；
  ⑤ 语料里出现但表里没有的码 ⇒ FAIL（未登记形态）。

反向对照在 `%TEMP%` 副本上**真驱动**（真写文件、真读、真跑 `check()`）：
干净副本 / 删标签 / 双主案例 / 未登记码 / 形名漂移 / 死码 各一条。

用法：
  .venv\\Scripts\\python.exe verify\\verify_case_index.py
  .venv\\Scripts\\python.exe verify\\verify_case_index.py --selftest
"""
from __future__ import annotations

VERIFY_META = {
    "features": (
        "A-CASE 形态↔主案例一致性：两份反例语料的案例标题必须带形态标签、"
        "每形态恰 1 个主案例、形名与卡片表一致、表里无死码、语料无未登记码；"
        "反向对照五组（删标签/双主案例/未登记/形名漂移/死码）＋干净副本；"
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
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.harness import finish, ok, skip

if not __debug__:  # -O 会剥离 assert ⇒ 判据静默空转
    raise SystemExit("本闸门不得在 -O 下运行（判据会被剥离）")

BASE = "docs/iteration/phases/agents-infra/"
CARD_REL = BASE + "cards/A-CASE.md"
CORPUS_F = (BASE + "2026-09-25-subagent-dispatch-"
            "failure-modes-case.MD")
CORPUS_G = (BASE + "2026-09-25-gate-mechanism-"
            "failure-modes-case.MD")
CORPUS_RELS = (CORPUS_F, CORPUS_G)

# 标题行：`## 案例 <N>｜<标题> ｜ **形态**：…`（无标签的行也要被认出来）
CASE_HEAD_RE = re.compile(r"^##\s+案例\s+(?P<num>\d+)\s*｜(?P<title>.*)$")
# 形态标记：`**形态**：F4｜<形名>｜主案例 `#7`` / `…｜同形态见主案例 `#7``
TAG_RE = re.compile(
    r"\*\*形态\*\*\s*[：:]\s*(?P<code>[FG]\d+)\s*｜\s*"
    r"(?P<name>.+?)\s*｜\s*(?P<marker>同形态见主案例|主案例)"
    r"\s*`#(?P<ref>\d+)`")
FORM_CODE_RE = re.compile(r"^[FG]\d+$")

# 反向对照的改动锚点（**唯一**字面串；命中次数 != 1 即夹具错误）
OLD_SECONDARY = ("**形态**：F4｜多写入者同改一处：文件占用未声明"
                 "｜同形态见主案例 `#7`")
OLD_PRIMARY = ("**形态**：F4｜多写入者同改一处：文件占用未声明"
               "｜主案例 `#7`")
OLD_MARKER = "多写入者同改一处：文件占用未声明｜同形态见主案例 `#7`"
F12_ROW = "| F12 | 验证落在产出物上、而非消费点上 | 案例 13 |"


class Case(NamedTuple):
    """一条案例标题行的解析结果（缺标签时 code/name/marker 为空）。"""

    rel: str
    line: int
    num: int
    title: str
    code: str
    name: str
    marker: str
    ref: int


def _read(path: Path) -> str:
    """读 UTF-8 文本，CRLF 归一为 LF。"""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def parse_headings(text: str, rel: str) -> list[Case]:
    """解析一份语料档里全部 `## 案例 N` 标题行（含缺标签 / 多标签）。"""
    out: list[Case] = []
    for i, line in enumerate(text.splitlines(), 1):
        head = CASE_HEAD_RE.match(line)
        if not head:
            continue
        tag = TAG_RE.search(line)
        title = head["title"].split("｜")[0].strip()
        if tag:
            out.append(Case(rel, i, int(head["num"]), title,
                            tag["code"], tag["name"].strip(),
                            tag["marker"], int(tag["ref"])))
        else:
            out.append(Case(rel, i, int(head["num"]), title,
                            "", "", "", 0))
    return out


def parse_card_forms(text: str) -> tuple[dict[str, str], dict[str, int],
                                         list[str]]:
    """解析卡片里的三列表格（形态码｜形名｜主案例），返回表与表问题。"""
    names: dict[str, str] = {}
    prim: dict[str, int] = {}
    problems: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        row = line.strip()
        if not row.startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) != 3 or not FORM_CODE_RE.match(cells[0]):
            continue
        code = cells[0]
        if code in names:
            problems.append(
                f"[表] 形态码 {code} 在卡片清单表里出现多次（行 {i}）")
            continue
        names[code] = cells[1]
        num = re.search(r"\d+", cells[2])
        if num:
            prim[code] = int(num.group(0))
    if not names:
        problems.append("[表] 卡片 A-CASE.md 的形态清单表解析为空")
    return names, prim, problems


def judge(cases: list[Case], names: dict[str, str],
          prim: dict[str, int]) -> list[str]:
    """五条判据的**纯函数**：返回问题清单（空 = 全过）。"""
    problems: list[str] = []
    tagged = [c for c in cases if c.code]
    for c in cases:
        if not c.code:
            problems.append(
                f"[① 形态标签] {c.rel}:{c.line} 案例 {c.num} 没有形态标记"
                "（应有 **形态**：F/G<n>｜<形名>｜主案例/同形态）")
    codes = sorted({c.code for c in tagged} | set(names))
    for code in codes:
        group = [c for c in tagged if c.code == code]
        primaries = [c for c in group if c.marker == "主案例"]
        if len(primaries) != 1:
            where = "、".join(
                f"{c.rel}:{c.line} 案例 {c.num}" for c in primaries) or "（无）"
            problems.append(
                f"[② 主案例唯一] 形态 {code} 有 {len(primaries)} 个主案例："
                f"{where}")
            continue
        first = primaries[0]
        for c in group:
            if c.marker == "同形态见主案例" and c.ref != first.num:
                problems.append(
                    f"[② 主案例指向] {c.rel}:{c.line} 案例 {c.num} 指向 "
                    f"`#{c.ref}`，但 {code} 的主案例是 案例 {first.num}"
                    f"（{first.rel}:{first.line}）")
        if code not in names:
            continue
        if first.name != names[code]:
            problems.append(
                f"[③ 形名一致] 形态 {code} 主案例 {first.rel}:{first.line} "
                f"的形名 {first.name!r} ≠ 卡片表 {names[code]!r}")
        want = prim.get(code)
        if want is not None and want != first.num:
            problems.append(
                f"[③ 形名一致] 形态 {code} 表的主案例列写 案例 {want}，"
                f"语料主案例是 案例 {first.num}（{first.rel}:{first.line}）")
    for code in sorted(names):
        if not any(c.code == code for c in tagged):
            problems.append(
                f"[④ 死码] 形态 {code}（{names[code]}）在卡片表里，"
                "但两份语料一次都没出现")
    for c in cases:
        if c.code and c.code not in names:
            problems.append(
                f"[⑤ 未登记形态] {c.rel}:{c.line} 案例 {c.num} 用了 "
                f"{c.code}，但卡片形态清单表里没有这个码")
    return problems


def _stats(cases: list[Case], names: dict[str, str]) -> dict:
    """扫描读数（供上屏与断言，不参与判定）。"""
    return {
        "cases": len(cases),
        "forms": len(names),
        "primaries": sum(1 for c in cases if c.marker == "主案例"),
        "secondary": sum(1 for c in cases if c.marker == "同形态见主案例"),
    }


def check(root: Path = ROOT) -> tuple[list[str], dict]:
    """读卡与两份语料，返回 `(问题清单, 统计)`；缺文件 ⇒ 问题（fail-closed）。"""
    wanted = (CARD_REL, *CORPUS_RELS)
    missing = [rel for rel in wanted if not (root / rel).is_file()]
    if missing:
        return [f"[输入] 缺文件：{rel}" for rel in missing], {}
    names, prim, problems = parse_card_forms(_read(root / CARD_REL))
    cases: list[Case] = []
    for rel in CORPUS_RELS:
        cases += parse_headings(_read(root / rel), rel)
    return problems + judge(cases, names, prim), _stats(cases, names)


def _by(problems: list[str], prefix: str) -> list[str]:
    """按判据前缀取问题子集。"""
    return [p for p in problems if p.startswith(prefix)]


def _brief(problems: list[str]) -> str:
    """一条详情串（首两条问题，完整点名；空 ⇒ `0 条`）。"""
    return "；".join(problems[:2]) if problems else "0 条"


def _has(problems: list[str], prefix: str, *needles: str) -> bool:
    """是否存在一条问题：以 prefix 开头且含全部 needles。"""
    return any(p.startswith(prefix) and all(n in p for n in needles)
               for p in problems)


def _replaced(text: str, old: str, new: str) -> str:
    """唯一字面替换；命中次数 != 1 即抛（夹具改错处比没有夹具更坏）。"""
    hit = text.count(old)
    if hit != 1:
        raise SystemExit(
            f"selftest 夹具错误：{old!r} 命中 {hit} 次（应为 1）")
    return text.replace(old, new)


def run_real() -> None:
    """真数据逐判据断言（每条 FAIL 的完整点名已先逐行打印）。"""
    problems, stats = check(ROOT)
    print(f"扫描 {stats.get('cases', 0)} 条案例 / "
          f"{stats.get('forms', 0)} 个形态"
          f"（主案例 {stats.get('primaries', 0)}）")
    for p in problems:
        print(f"  - {p}")
    ok("输入：卡与两份语料齐备", bool(stats), f"stats={stats}")
    ok("表：清单可解析且码不重复", not _by(problems, "[表]"),
       _brief(_by(problems, "[表]")))
    ok("① 每条案例都有形态标签", not _by(problems, "[①"),
       _brief(_by(problems, "[①")))
    ok("② 每个形态恰 1 个主案例", not _by(problems, "[②"),
       _brief(_by(problems, "[②")))
    ok("③ 主案例形名与表一致", not _by(problems, "[③"),
       _brief(_by(problems, "[③")))
    ok("④ 表里没有死码", not _by(problems, "[④"),
       _brief(_by(problems, "[④")))
    ok("⑤ 语料没有未登记形态", not _by(problems, "[⑤"),
       _brief(_by(problems, "[⑤")))
    ok("表与语料非空",
       stats.get("forms", 0) > 0 and stats.get("cases", 0) > 0,
       f"cases={stats.get('cases', 0)} forms={stats.get('forms', 0)}")


def selftest() -> None:
    """在 `%TEMP%` 副本上真写、真读、真跑 `check()` 的六组反向对照。"""
    with tempfile.TemporaryDirectory(prefix="case-index-") as td:
        base = Path(td)
        (base / CARD_REL).parent.mkdir(parents=True, exist_ok=True)
        (base / CORPUS_F).parent.mkdir(parents=True, exist_ok=True)
        (base / CARD_REL).write_text(
            _read(ROOT / CARD_REL), encoding="utf-8", newline="\n")
        f_clean = _read(ROOT / CORPUS_F)
        g_clean = _read(ROOT / CORPUS_G)
        (base / CORPUS_F).write_text(f_clean, encoding="utf-8",
                                     newline="\n")
        (base / CORPUS_G).write_text(g_clean, encoding="utf-8",
                                     newline="\n")
        problems, stats = check(base)
        ok("(d) 干净副本 ⇒ PASS（0 问题）",
           not problems and stats.get("primaries") == stats.get("forms"),
           _brief(problems))

        (base / CORPUS_F).write_text(
            _replaced(f_clean, OLD_SECONDARY, "｜同形态见主案例 `#7`"),
            encoding="utf-8", newline="\n")
        problems, _ = check(base)
        ok("(a) 删掉一个形态标签 ⇒ ① FAIL 并点名案例 8",
           _has(problems, "[①", "案例 8"), _brief(problems))
        (base / CORPUS_F).write_text(f_clean, encoding="utf-8",
                                     newline="\n")

        (base / CORPUS_F).write_text(
            _replaced(f_clean, OLD_MARKER,
                      "多写入者同改一处：文件占用未声明｜主案例 `#8`"),
            encoding="utf-8", newline="\n")
        problems, _ = check(base)
        ok("(b) 同一形态两个主案例 ⇒ ② FAIL 并点名 F4",
           _has(problems, "[②", "F4", "2 个主案例", "案例 7", "案例 8"),
           _brief(problems))
        (base / CORPUS_F).write_text(f_clean, encoding="utf-8",
                                     newline="\n")

        (base / CORPUS_F).write_text(
            _replaced(f_clean, OLD_SECONDARY,
                      OLD_SECONDARY.replace("F4", "F99")),
            encoding="utf-8", newline="\n")
        problems, _ = check(base)
        ok("(c) 未登记形态码 ⇒ ⑤ FAIL 并点名 F99",
           _has(problems, "[⑤", "F99"), _brief(problems))
        (base / CORPUS_F).write_text(f_clean, encoding="utf-8",
                                     newline="\n")

        (base / CORPUS_F).write_text(
            _replaced(f_clean, OLD_PRIMARY,
                      "**形态**：F4｜形名漂移探针｜主案例 `#7`"),
            encoding="utf-8", newline="\n")
        problems, _ = check(base)
        ok("(e) 主案例形名漂移 ⇒ ③ FAIL 并点名 F4",
           _has(problems, "[③", "F4", "形名漂移探针"),
           _brief(problems))
        (base / CORPUS_F).write_text(f_clean, encoding="utf-8",
                                     newline="\n")

        card_clean = _read(base / CARD_REL)
        (base / CARD_REL).write_text(
            _replaced(card_clean, F12_ROW,
                      F12_ROW + "\n| F99 | 死码探针 | 案例 1 |"),
            encoding="utf-8", newline="\n")
        problems, _ = check(base)
        ok("(f) 表里留下死码 ⇒ ④ FAIL 并点名 F99",
           _has(problems, "[④", "F99"), _brief(problems))
        (base / CARD_REL).write_text(card_clean, encoding="utf-8",
                                     newline="\n")


def main() -> int:
    """CLI 入口：默认真数据 ＋ 反向对照；`--selftest` 只跑反向对照。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="A-CASE 形态↔主案例一致性闸门")
    ap.add_argument("--selftest", action="store_true",
                    help="只跑 %TEMP% 合成副本上的反向对照")
    args = ap.parse_args()
    if not args.selftest:
        if not (ROOT / "docs/iteration").is_dir():
            skip("no-iteration-docs", "形态↔主案例",
                 "本分支无 docs/iteration（判据无从执行）")
            return finish("verify_case_index.py", tag="CASE-INDEX")
        run_real()
    selftest()
    return finish("verify_case_index.py")


if __name__ == "__main__":
    sys.exit(main())
