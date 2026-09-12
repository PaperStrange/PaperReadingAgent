"""Sprint-16 M16（调研工作流 v2.0）：调研归档完整性校验器。

校验 agents/runs/<run_id>/ 是否满足 tech-research spec v2.0 的归档契约：
- quick 档：仅要求 report.md（非空 + 含证据索引表节）
- expert/scholar 档：report.md + context.md + reasoning.md + evidence/*.md
  * evidence 文件必须含 url / tier / fetched_at / fetch_status / supports 五个字段
    与一段 verbatim 原文引用块（fetch_status=failed 时须有 reason，可无引用）
  * report.md 的证据索引表必须引用全部 evidence 文件（引用缺失 = 不通过）

用法：
  .venv\\Scripts\\python.exe verify\\verify_archive.py <run_dir> --depth expert
  .venv\\Scripts\\python.exe verify\\verify_archive.py --selftest
"""
from __future__ import annotations
VERIFY_META = {'features': 'M16 调研归档完整性校验：report/context/reasoning/evidence 契约 + 证据索引表交叉引用（fail-closed）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import argparse
import re
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # 控制台中文不乱码（GBK 默认）

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("quick", "expert", "scholar")
ALIASES = {"normal": "expert", "deep": "scholar"}
EVIDENCE_FIELDS = ("url:", "tier:", "fetched_at:", "fetch_status:", "supports:")

passed = 0
failed = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS: {name} {detail}")
        return
    failed += 1
    print(f"FAIL: {name} {detail}")


def norm_depth(depth: str) -> str:
    d = (depth or "expert").strip().lower()
    return ALIASES.get(d, d)


def find_report(run_dir: Path) -> Path | None:
    """账本约定 = <role>.report.md；兼容 report.md 与任意 *.report.md。"""
    for name in ("tech-research.report.md", "report.md"):
        p = run_dir / name
        if p.is_file():
            return p
    hits = sorted(run_dir.glob("*.report.md"))
    return hits[0] if hits else None


def check_archive(run_dir: Path, depth: str) -> bool:
    """返回值 = 是否通过；同时打印逐项断言。"""
    depth = norm_depth(depth)
    ok("档案目录存在", run_dir.is_dir(), str(run_dir))
    ok("深度档位合法", depth in TIERS, f"depth={depth}")

    report = find_report(run_dir)
    ok("report 文件存在（<role>.report.md）", report is not None, str(report))
    report_text = report.read_text(encoding="utf-8") if report else ""
    ok("report 非空", len(report_text.strip()) > 200, f"chars={len(report_text)}")
    ok(
        "report 含证据索引表节",
        bool(re.search(r"^##\s*7\.", report_text, re.M)) or "证据索引表" in report_text,
    )

    if depth == "quick":
        return failed == 0

    for name in ("context.md", "reasoning.md"):
        p = run_dir / name
        ok(f"{name} 存在", p.is_file())
        if p.is_file():
            ok(f"{name} 非空", len(p.read_text(encoding="utf-8").strip()) > 80)

    ev_dir = run_dir / "evidence"
    ev_files = sorted(ev_dir.glob("*.md")) if ev_dir.is_dir() else []
    ok("evidence/ 目录存在且非空", bool(ev_files), f"files={len(ev_files)}")

    for ev in ev_files:
        text = ev.read_text(encoding="utf-8")
        head = text[:1200]
        missing = [f for f in EVIDENCE_FIELDS if f not in head]
        ok(f"{ev.name} 五字段齐备", not missing, f"missing={missing}")
        status = ""
        m = re.search(r"fetch_status:\s*(\w+)", head)
        if m:
            status = m.group(1).lower()
        if status == "failed":
            ok(f"{ev.name} 失败抓取有 reason", "reason" in head.lower())
        else:
            ok(f"{ev.name} 含 verbatim 原文引用块", "> " in text, "quote block")

    if depth == "expert" and ev_files:
        # 交叉引用：报告的证据索引表必须点名每个 evidence 文件
        unreferenced = [ev.name for ev in ev_files if ev.name not in report_text and ev.stem not in report_text]
        ok("证据索引表引用全部 evidence 文件", not unreferenced, f"unreferenced={unreferenced}")

    if depth == "scholar":
        low = report_text
        ok("scholar 档含反向证据/改判条件节", ("反向" in low) or ("改判" in low))

    return failed == 0


def _run_isolated(fn, *args):
    """跑一次校验并隔离计数器（自检里的负例不计入全局 failed）。"""
    global passed, failed
    saved = (passed, failed)
    passed = failed = 0
    try:
        result = fn(*args)
        local = (passed, failed)
    finally:
        passed, failed = saved
    return result, local


def selftest() -> int:
    """自检：合成一个最小合规档案（应为 PASS）+ 缺件档案（应为 FAIL）。"""
    global passed, failed
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "run-good"
        (good / "evidence").mkdir(parents=True)
        (good / "tech-research.report.md").write_text(
            "# tech-research report\n" + "填充" * 200 + "\n## 7. 证据索引表\n| 结论 | evidence |\n|---|---|\n| c1 | 01-official.md |\n"
            + "## 5. 改判条件\n反向证据缺失时改判\n",
            encoding="utf-8",
        )
        (good / "context.md").write_text("# 调研上下文快照\n" + "question/depth/date/基线决策" * 10, encoding="utf-8")
        (good / "reasoning.md").write_text("# 思考过程附件\n" + "结论推导链与采信排除" * 10, encoding="utf-8")
        (good / "evidence" / "01-official.md").write_text(
            "# evidence 01\n- url: https://example.com/doc\n- tier: tier1\n- fetched_at: 2026-09-12\n"
            "- fetch_status: ok\n- supports: c1\n## 原文段落（verbatim）\n> official statement here\n",
            encoding="utf-8",
        )
        print("== selftest: 合规档案（期望 PASS）==")
        good_result, (_, good_failed) = _run_isolated(check_archive, good, "expert")

        print("== selftest: 缺件档案（期望 FAIL）==")
        bad = Path(td) / "run-bad"
        bad.mkdir()
        (bad / "tech-research.report.md").write_text("# empty\n", encoding="utf-8")
        bad_result, (_, bad_failed) = _run_isolated(check_archive, bad, "expert")

        ok("selftest 合规档案全部断言通过", good_result and good_failed == 0)
        ok("selftest 缺件档案被拒（且确有失败项）", (not bad_result) and bad_failed > 0)
    print(f"\n=== selftest {'PASS' if failed == 0 else 'FAIL'}: {passed} passed / {failed} failed ===")
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="tech-research 归档完整性校验（M16）")
    ap.add_argument("run_dir", nargs="?", help="agents/runs/<run_id> 目录")
    ap.add_argument("--depth", default="expert", help="quick | expert | scholar（兼容 normal/deep）")
    ap.add_argument("--selftest", action="store_true", help="跑内置自检（合成档案）")
    args = ap.parse_args()

    if args.selftest or not args.run_dir:
        return selftest()

    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    print(f"== verify_archive: {run_dir} (depth={norm_depth(args.depth)}) ==")
    passed_flag = check_archive(run_dir, args.depth)
    print(f"\n=== {'ALL PASS' if passed_flag else 'FAILED'}: {passed} passed / {failed} failed ===")
    return 0 if passed_flag else 1


if __name__ == "__main__":
    sys.exit(main())
