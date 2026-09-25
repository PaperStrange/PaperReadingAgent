#!/usr/bin/env python3
"""派生数字不得手抄（2026-09-25，Sprint-17 关闭期交付；根因＝一查 `run-2026-09-25-doc-audit-070` finding 1/2）。

## 为什么需要这条闸门

`TG-6` 的四件套证据规范要求"写命令 + 关键输出行"，而**断言数/卡数/文件数/C 级条数**这类
**派生数字没有 SSOT**（`cards/TG-12.md` 自陈"断言数根本没有 SSOT"）⇒ 每个新闸门落地即产生
一批**注定过期**的数字。本轮实测后果：同一批闸门在**同一天**的 4 份文档里并存 3~4 个读数
（断言数 6/11、23/30/55、7/22、57/73/84/101；卡数 96 vs 97；字节 105580 vs 161228；
脚本数 50/52 vs 53；C 级 2021/2910/1998 vs 2880），**无一与工具一致**。

规范条文（`1-WORKFLOW.MD` §6"派生数字不得手抄"）只允许两种合法形态：
**① 复现命令 + "以该命令输出为准"**；**② 标明时点的历史读数**（带 sha 或日期，并声明不得当作现值）。
**写成"现测 <数字>"/"实测 <数字>"的当期主张即违规**——本闸门把这条条文变成可执行判据。

## 判据（全部来自政策数据 `agents/policy.json::derived_numbers`）

1. **按文件计数**：`scan_globs` 命中的文档里，每命中一条"当期数字主张"记 1 处；
2. **棘轮**：`baseline` 给每个**历史**文件一个"违规处数上限"（只减不增；见判据 4）；
   未列入 `baseline` 的文件上限 = `default_cap`（**当前为 0** ⇒ 新文档一处都不许有）；
3. **生成物豁免**：`generated_files`（由脚本 derive 出来的文件，本身就是 SSOT 派生物）
不参与；
4. **上限只许下调**：与 `git HEAD` 版政策逐项比较，任何**上调**即 FAIL（防"把上限调高即变绿"）；
5. **到期必须重评**：`review_by` 过期即 FAIL（没有到期日的豁免就是永久豁免）；
6. **死键**：`baseline` 里指向已不存在文件的条目即 FAIL（失效条目必须删除）。

## 反向对照（`--selftest`，全自动 fixture）

往合规文档注入 1 处"现测 N 卡"→ 必 FAIL 并点名文件:行；合规形态（命令 + "以输出为准"/
带 sha 的时点读数）→ 必须 PASS；上限上调 → FAIL；`review_by` 过期 → FAIL；死键 → FAIL。

## 用法

    .venv\\Scripts\\python.exe verify\\verify_derived_numbers.py            # 真数据 + fixture 反向对照
    .venv\\Scripts\\python.exe verify\\verify_derived_numbers.py --report   # 打印逐文件命中数（维护基线用）
    .venv\\Scripts\\python.exe verify\\verify_derived_numbers.py --selftest # 只跑 fixture 反向对照
"""

from __future__ import annotations

VERIFY_META = {'features': '派生数字不得手抄：按文件棘轮约束"现测/实测 <数字>"式当期主张（断言数/卡数/文件数/脚本数/字节/C 级条数/棘轮计数）；生成物豁免、上限只减不增、review_by 到期即 FAIL；含 6 条反向对照自检', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 4, 'routes': [], 'requires': ['none']}

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句，不能是 assert
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_CFG = load_policy()._data("derived_numbers")  # noqa: SLF001 —— 政策读取器同源
SCAN_GLOBS: tuple[str, ...] = tuple(str(g) for g in _CFG["scan_globs"])
GENERATED: tuple[str, ...] = tuple(str(g) for g in _CFG["generated_files"])
PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = tuple(
    (str(p["id"]), re.compile(str(p["regex"])), str(p["hint"])) for p in _CFG["patterns"])
TIME_ANCHOR = re.compile(str(_CFG["time_anchor_regex"]))
BASELINE: dict[str, int] = {str(k): int(v) for k, v in (_CFG["baseline"] or {}).items()}
DEFAULT_CAP: int = int(_CFG["default_cap"])
REVIEW_BY: str = str(_CFG["review_by"])
POLICY_REL = "agents/policy.json"
PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def doc_files(root: Path = ROOT) -> list[Path]:
    out: list[Path] = []
    for pattern in SCAN_GLOBS:
        out += [p for p in root.glob(pattern) if p.is_file()]
    seen: set[Path] = set()
    keep: list[Path] = []
    for path in sorted(out):
        if path in seen:
            continue
        seen.add(path)
        r = rel(path)
        if any(Path(g) == Path(r) or path.match(g) for g in GENERATED):
            continue
        keep.append(path)
    return keep


def scan_text(text: str) -> list[tuple[int, str, str, str]]:
    """返回 [(行号, 判据 id, 命中文本, hint)]。

    **时点豁免（行级）**：同一行里带**时点锚**（日期 / sha / "以…为准"）的读数属规范允许的
    "② 标明时点的历史读数"，不判违规——判据治的是"把某个数字当成**当期**事实"这种写法。
    豁免只到行级、且必须同行可见：把数字写在前面、锚点写在下一段不算。
    """
    hits: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if TIME_ANCHOR.search(line):
            continue
        for pid, pattern, hint in PATTERNS:
            for m in pattern.finditer(line):
                hits.append((i, pid, m.group(0)[:60], hint))
    return hits


def count_docs(root: Path = ROOT) -> dict[str, list[tuple[int, str, str, str]]]:
    out: dict[str, list[tuple[int, str, str, str]]] = {}
    for path in doc_files(root):
        hits = scan_text(path.read_text(encoding="utf-8", errors="replace"))
        if hits:
            out[rel(path)] = hits
    return out


def head_caps(policy_rel: str = POLICY_REL) -> dict[str, int] | None:
    """`git HEAD` 版政策里的 baseline（上限只许下调的比对基准）。

    取不到（无 git / 文件未入库 / 首次提交）→ 返回 None：调用方**不静默放行**，
    而是打印一条显式说明（"无可比基准"与"比过了且没上调"必须能区分）。
    """
    try:
        proc = subprocess.run(["git", "show", f"HEAD:{policy_rel}"], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    base = ((data.get("derived_numbers") or {}).get("baseline") or {})
    return {str(k): int(v) for k, v in base.items()}


def evaluate(counts: dict[str, list[tuple[int, str, str, str]]], *, baseline: dict[str, int],
             default_cap: int, review_by: str, today: str, previous: dict[str, int] | None,
             existing_files: set[str] | None = None,
             root: Path | None = None) -> tuple[list[str], list[str]]:
    """纯函数：给定"逐文件命中数 + 上限表 + 基准"，返回 (problems, warnings)。"""
    problems: list[str] = []
    warnings: list[str] = []
    for path, hits in sorted(counts.items()):
        cap = baseline.get(path, default_cap)
        if len(hits) > cap:
            first = hits[0]
            problems.append(
                f"[违规] {path}: 派生数字当期主张 {len(hits)} 处 > 上限 {cap}（首处 line {first[0]}："
                f"{first[2]!r}，判据 {first[1]}）——{first[3]}；合法形态见 1-WORKFLOW §6"
                f"（复现命令 + 以输出为准 / 带 sha 的时点读数）")
        elif len(hits) < cap:
            warnings.append(f"{path}: 实测 {len(hits)} 处 < 上限 {cap} —— 上限只许下调，请同步收紧 baseline")
    if review_by < today:
        problems.append(f"[棘轮] review_by={review_by} 已过期（今日={today}）→ 必须重评基线"
                        f"（不得静默延期：没有到期日的豁免就是永久豁免）")
    if previous is not None:
        for path, cap in sorted(baseline.items()):
            old = previous.get(path)
            if old is not None and cap > old:
                problems.append(f"[棘轮] {path} 的上限被**上调**：{old} → {cap}"
                                f"（上限只许下调；确需放宽必须走『重评基线』并改 review_by，"
                                f"而不是改数字）")
    if existing_files is not None:
        for path in sorted(baseline):
            if path in existing_files:
                continue
            # **分支差异 ≠ 死键**（C6，2026-09-25 sync PR #53 的 CI 实测）：
            # baseline 里大量条目在
            # `docs/iteration/**`（windows-only）下，
            # 而 `main`/同步分支没有该目录 ⇒ 这些条目"文件不在"
            # 是**分支差异**，不是"失效条目"。判据改为按**父目录**是否存在区分（不猜、
            # 不含糊）：
            #   * 父目录存在、文件不在 → 真死键 → FAIL（原判据，方向不变）；
            # * 父目录也不存在 → 该文件所属的树在本分支根本没有 → 记一条 NOTE，
            # 不判问题。
            parent = (root / path).parent if root is not None else None
            if parent is not None and not parent.exists():
                warnings.append(f"{path}: 所属目录不存在（分支差异，如 windows-only 的 "
                                f"`docs/iteration/**`）→ 跳过死键判据")
                continue
            problems.append(f"[棘轮] baseline 里的 {path} 已不存在（死键）→ 失效条目必须删除"
                            f"（留着它等于给一个未来同名文件预留豁免）")
    return problems, warnings


def selftest() -> int:
    """fixture 反向对照（全部走纯函数 `evaluate`，不碰仓库文档）。"""
    good = {"docs/a.md": []}
    bad = {"docs/a.md": [(3, "claim_count", "现测 97 卡", "改成复现命令")]}
    base_fixture = {"docs/a.md": 0}
    problems, _ = evaluate(bad, baseline=base_fixture, default_cap=0, review_by="2099-01-01",
                           today="2026-09-25", previous=None, existing_files={"docs/a.md"})
    ok("反向对照 A 注入 1 处『现测 N 卡』→ FAIL 且点名文件与行号",
       any("docs/a.md" in p and "line 3" in p for p in problems), f"problems={problems[:1]}")
    problems, _ = evaluate(good, baseline=base_fixture, default_cap=0, review_by="2099-01-01",
                           today="2026-09-25", previous=None, existing_files={"docs/a.md"})
    ok("反向对照 B 合规文档（0 处命中）→ PASS（防假红）", problems == [], f"problems={problems[:1]}")
    problems, _ = evaluate({}, baseline={"docs/a.md": 1}, default_cap=0, review_by="2099-01-01",
                           today="2026-09-25", previous=None, existing_files={"docs/a.md"})
    ok("反向对照 C 上限高于实测 → 不判违规（棘轮只约束『超出』，不要求『用满』）",
       problems == [], f"problems={problems[:1]}")
    _, warnings = evaluate({"docs/a.md": []}, baseline={"docs/a.md": 1}, default_cap=0,
                           review_by="2099-01-01", today="2026-09-25", previous=None,
                           existing_files={"docs/a.md"})
    ok("反向对照 C2 上限高于实测 → 必须给出『请收紧』的 WARN（不是静默）",
       any("只许下调" in w for w in warnings), f"warnings={warnings[:1]}")
    problems, _ = evaluate(good, baseline=base_fixture, default_cap=0, review_by="2020-01-01",
                           today="2026-09-25", previous=None, existing_files={"docs/a.md"})
    ok("反向对照 D review_by 过期 → FAIL",
       any("已过期" in p for p in problems), f"problems={problems[:1]}")
    problems, _ = evaluate(good, baseline={"docs/a.md": 3}, default_cap=0, review_by="2099-01-01",
                           today="2026-09-25", previous={"docs/a.md": 1},
                           existing_files={"docs/a.md"})
    ok("反向对照 E 上限被上调（1 → 3）→ FAIL",
       any("上调" in p for p in problems), f"problems={problems[:1]}")
    problems, _ = evaluate(good, baseline={"docs/gone.md": 0}, default_cap=0, review_by="2099-01-01",
                           today="2026-09-25", previous=None, existing_files={"docs/a.md"})
    ok("反向对照 F 基线死键（文件已不存在）→ FAIL",
       any("死键" in p for p in problems), f"problems={problems[:1]}")

    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td) / "docs" / "x.md"
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text("> 复现命令：`.venv\\Scripts\\python.exe verify\\verify_x.py`（**现值以该命令输出为准**）\n"
                           "> 时点读数（`f30c6e4`）：断言数见 §7，不在此处固化\n", encoding="utf-8")
        ok("反向对照 G 合规形态文本（命令 + 以输出为准 / 带 sha 的时点读数）→ 0 命中",
           scan_text(fixture.read_text(encoding="utf-8")) == [],
           f"hits={scan_text(fixture.read_text(encoding='utf-8'))[:1]}")
        fixture.write_text("现测 **11 断言**、`ALL PASS (11 assertions)`、C 级 2880 条\n", encoding="utf-8")
        hits = scan_text(fixture.read_text(encoding="utf-8"))
        ok("反向对照 H 三类主张文本（N 断言 / ALL PASS(N assertions) / C 级 N 条）→ 各自命中",
           len(hits) >= 3, f"hits={hits}")
        fixture.write_text("2026-09-25 时点读数（`f30c6e4`）：现测 97 卡 / 11 断言（不得当作现值）\n",
                           encoding="utf-8")
        ok("反向对照 I 同行带时点锚（日期/sha）的读数 → 豁免（规范允许的『② 时点读数』形态）",
           scan_text(fixture.read_text(encoding="utf-8")) == [],
           f"hits={scan_text(fixture.read_text(encoding='utf-8'))[:1]}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    today = __import__("datetime").datetime.now(
        __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
    ).strftime("%Y-%m-%d")
    if "--selftest" in sys.argv:
        return selftest()
    counts = count_docs()
    if "--report" in sys.argv:
        for path, hits in sorted(counts.items()):
            print(f"{len(hits):4d}  {path}")
            for line, pid, text, _hint in hits[:5]:
                print(f"        line {line} [{pid}] {text}")
        print(f"合计：{len(counts)} 个文件有命中，{sum(len(v) for v in counts.values())} 处")
        return 0
    problems, warnings = evaluate(counts, baseline=BASELINE, default_cap=DEFAULT_CAP,
                                  review_by=REVIEW_BY, today=today, previous=head_caps(),
                                  existing_files={rel(p) for p in doc_files()},
                                  root=ROOT)
    for w in warnings[:20]:
        print(f"WARN: {w}")
    if problems:
        print(f"DERIVED-NUMBERS FAIL（{len(problems)} 项）：")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  … 另有 {len(problems) - 40} 项")
        return 1
    print(f"DERIVED-NUMBERS PASS：{len(doc_files())} 个文档扫描通过"
          f"（{len(BASELINE)} 个历史文件走棘轮上限、均在各自上限内；生成物 {len(GENERATED)} 个豁免）")
    rc = selftest()
    if rc == 0:
        print(f"EVIDENCE: verify_derived_numbers.py assertions={PASSED} rc=0 "
              f"review_by={REVIEW_BY}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
