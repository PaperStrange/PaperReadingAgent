"""Sprint-16 M16（调研工作流 v2.0）：调研归档完整性校验器。

校验 agents/runs/<run_id>/ 是否满足 tech-research spec v2.0 的归档契约：
- quick 档：仅要求 report.md（非空 + 含证据索引表节）
- expert/scholar 档：report.md + context.md + reasoning.md + evidence/*.md
  * evidence 文件必须含 url / tier / fetched_at / fetch_status / supports 五个字段
    与一段 verbatim 原文引用块（fetch_status=failed 时须有 reason，可无引用）
  * report.md ↔ evidence/ **双向**交叉引用（2026-09-20 走查修复；同日复核 run-053 收紧范围）：
    ① 索引表必须点名每个 evidence 文件（正向）；
    ② 索引表点名的文件必须真实存在于磁盘（反向）。缺②则"删掉被引用的证据文件"仍判 PASS
       （spec 契约：a citation without an evidence file is a violation）。
    **两条都只在"证据索引表所在小节"（§7 或标题含『证据索引表』）内判定**：正文顺带提及
    别处的 evidence 文件名（跨 run 引用、URL 片段）不是"结论 ↔ 证据行"的引用，扫全文会误红；
    文件名比较**大小写不敏感**（Windows 语义，避免跨平台判定不一致）。
  * 证据文件遍历**不跟随目录 junction/软链**，且有文件数上限（超限 FAIL）——
    `rglob` 跟随 junction 且无环检测会让门禁**挂死不返回**（round-3 major#4 实测）：
    门禁宁可"快速判 FAIL"，也不允许"永不结束"。

用法：
  .venv\\Scripts\\python.exe verify\\verify_archive.py <run_dir> --depth expert
  .venv\\Scripts\\python.exe verify\\verify_archive.py --selftest
"""
from __future__ import annotations
VERIFY_META = {'features': 'M16 调研归档完整性校验：report/context/reasoning/evidence 契约 + 证据索引表双向交叉引用（限定 §7 索引表区间、大小写不敏感；fail-closed）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import argparse
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # 控制台中文不乱码（GBK 默认）

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("quick", "expert", "scholar")
ALIASES = {"normal": "expert", "deep": "scholar"}
EVIDENCE_FIELDS = ("url:", "tier:", "fetched_at:", "fetch_status:", "supports:")
EVIDENCE_FILE_CAP = 500  # 证据文件数上限（超限判 FAIL：防异常目录/junction 造成的爆炸式遍历）

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


# 索引表内的证据文件引用形态：`evidence/NN-slug.md`（可带反斜杠）或裸名 `NN-slug.md`。
# 复核 run-053 后放宽：接受 .markdown、1~3 位编号与非 ASCII 文件名（`\w` 含中日韩字符）。
# **清单侧必须同步放宽**（round-2 major#3：只放宽解析侧会让真实存在的 .markdown 被误判悬空）。
_EVIDENCE_NAME = r"[\w.\-]+\.(?:md|markdown)"
EVIDENCE_REF_RE = re.compile(rf"evidence[/\\]({_EVIDENCE_NAME})", re.I)
BARE_EVIDENCE_REF_RE = re.compile(rf"(?<![\w/\\-])(\d{{1,3}}-{_EVIDENCE_NAME})", re.I)


def evidence_index_section(report_text: str) -> str:
    """取"证据索引表所在小节"正文（§7，或任意标题含『证据索引表』的小节）。

    交叉引用只在此区间内判定——契约约束的是"结论 ↔ 证据行"的索引表，不是全文。
    标题行末尾允许无换行（EOF 直接结束，nit#9）。
    """
    m = re.search(r"^##\s*7\.[^\n]*(?:\n|$)(.*?)(?=^##\s|\Z)", report_text, re.M | re.S)
    if m:
        return m.group(1)
    m = re.search(r"^#{2,4}[^\n]*证据索引表[^\n]*(?:\n|$)(.*?)(?=^#{2,4}\s|\Z)", report_text, re.M | re.S)
    return m.group(1) if m else ""


def find_report(run_dir: Path) -> Path | None:
    """账本约定 = <role>.report.md；兼容 report.md 与任意 *.report.md。"""
    for name in ("tech-research.report.md", "report.md"):
        p = run_dir / name
        if p.is_file():
            return p
    hits = sorted(run_dir.glob("*.report.md"))
    return hits[0] if hits else None


def _is_linklike(p: Path) -> bool:
    """目录是否是链接类（符号链接 / Windows junction）——用于遍历时剪枝。"""
    try:
        if p.is_symlink():
            return True
        isj = getattr(os.path, "isjunction", None)  # Python 3.12+
        if isj and isj(p):
            return True
    except OSError:
        return True
    return False


def iter_evidence_files(ev_dir: Path) -> list[Path]:
    """列出 `evidence/` 下的证据文件（含子目录）。

    - **不跟随目录 junction/软链**（复核 round-3 major#4：`rglob` 会跟随且无环检测 →
      `evidence/` 内若有指回自身的 junction，`check_archive` 会**挂死不返回**；实测 25s 未返回、
      3 层 junction 拖到 5 分钟 / 632MB。归档由 agent 正常生成时不会出现 junction，
      但门禁宁可"快速判 FAIL"也不能"永不结束"）；
    - 遍历顺序确定（排序），便于断言可复现。
    """
    out: list[Path] = []
    if not ev_dir.is_dir():
        return out
    for root, dirs, files in os.walk(ev_dir, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not _is_linklike(Path(root) / d))
        for fn in sorted(files):
            if fn.lower().endswith((".md", ".markdown")):
                p = Path(root) / fn
                if p.is_file() and not p.is_symlink():
                    out.append(p)
        if len(out) > EVIDENCE_FILE_CAP:
            break
    return sorted(out)


def check_archive(run_dir: Path, depth: str) -> bool:
    """返回值 = 是否通过；同时打印逐项断言。"""
    global passed, failed
    depth = norm_depth(depth)
    ok("档案目录存在", run_dir.is_dir(), str(run_dir))
    ok("深度档位合法", depth in TIERS, f"depth={depth}")

    report = find_report(run_dir)
    ok("report 文件存在（<role>.report.md）", report is not None, str(report))
    report_text = report.read_text(encoding="utf-8") if report else ""
    ok("report 非空", len(report_text.strip()) > 200, f"chars={len(report_text)}")
    # 根因断言与区间定位复用同一实现（minor#7）：口径不一致会让"根因放行、区间失败"互相打架。
    ok("report 含证据索引表节", bool(evidence_index_section(report_text)), "§7 或标题含『证据索引表』的小节")

    if depth == "quick":
        return failed == 0

    for name in ("context.md", "reasoning.md"):
        p = run_dir / name
        ok(f"{name} 存在", p.is_file())
        if p.is_file():
            ok(f"{name} 非空", len(p.read_text(encoding="utf-8").strip()) > 80)

    ev_dir = run_dir / "evidence"
    # 清单侧与解析侧口径一致（major#3）：`.md` + `.markdown` 都算证据文件；
    # 用受限遍历容忍 evidence/ 子目录（minor#6）且**不跟随 junction**（round-3 major#4 防挂死）。
    ev_files = iter_evidence_files(ev_dir)
    if len(ev_files) > EVIDENCE_FILE_CAP:
        # 直接判 FAIL（不新增常驻断言，保持既有断言语义稳定）
        failed += 1
        print(f"FAIL: evidence/ 文件数超上限（防异常目录爆炸） files={len(ev_files)} > {EVIDENCE_FILE_CAP}")
        ev_files = ev_files[:EVIDENCE_FILE_CAP]
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

    if depth in ("expert", "scholar"):
        # 交叉引用（2026-09-20 走查修复 + 同日复核 run-053 收紧）：只判定证据索引表区间。
        idx_text = evidence_index_section(report_text)
        if not idx_text:
            ok("证据索引表引用全部 evidence 文件", False, "未定位到证据索引表区间（§7 或标题含『证据索引表』的小节）")
            ok("索引表点名的 evidence 文件全部存在", False, "同上：区间缺失，无法做反向校验")
        else:
            lowered = idx_text.lower()
            # ① 正向：索引表必须点名每个 evidence 文件（大小写不敏感）
            unreferenced = [ev.name for ev in ev_files if ev.name.lower() not in lowered and ev.stem.lower() not in lowered]
            ok("证据索引表引用全部 evidence 文件", not unreferenced, f"unreferenced={unreferenced}")
            # ② 反向：索引表点名的文件必须在 evidence/ 里真实存在（修复前只查正向 → 漏检）
            cited = set(EVIDENCE_REF_RE.findall(idx_text)) | set(BARE_EVIDENCE_REF_RE.findall(idx_text))
            have = {ev.name.lower() for ev in ev_files}
            dangling = sorted(n for n in cited if n.lower() not in have)
            ok("索引表点名的 evidence 文件全部存在", not dangling, f"dangling={dangling} cited={len(cited)}")

    if depth == "scholar":
        low = report_text
        ok("scholar 档含反向证据/改判条件节", ("反向" in low) or ("改判" in low))

    return failed == 0


def _run_isolated(fn, *args):
    """跑一次校验并隔离计数器（自检里的负例不计入全局 failed）。

    返回 `(result, (passed, failed), failures)`；`failures` = 失败断言名列表——
    负例判据据此核对"失败项**是**目标断言"，而不是只看失败条数（复核 run-053 minor）。
    捕获到的逐项输出在返回前原样回放到 stdout，保持自检可读性。
    """
    global passed, failed
    saved = (passed, failed)
    passed = failed = 0
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = fn(*args)
        local = (passed, failed)
    finally:
        passed, failed = saved
    text = buf.getvalue()
    sys.stdout.write(text)
    failures = [ln.split("FAIL: ", 1)[1].strip() for ln in text.splitlines() if ln.startswith("FAIL: ")]
    return result, local, failures


def selftest() -> int:
    """自检：合规档案（PASS）+ scholar 档（PASS）+ 空报告（FAIL）+ 被引用证据缺失（FAIL）
    + 正文提及别处证据名（PASS，防误报）+ 索引表点名不存在的 .markdown（FAIL，防漏报）
    + 索引表点名已存在的 .markdown（PASS，防假红）+ 嵌套子目录证据（PASS，防假红）。"""
    global passed, failed
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "run-good"
        (good / "evidence").mkdir(parents=True)
        (good / "tech-research.report.md").write_text(
            "# tech-research report\n" + "填充" * 200 + "\n## 7. 证据索引表\n| 结论 | evidence |\n|---|---|\n| c1 | 01-official.md |\n| c2 | 02-second.md |\n"
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
        (good / "evidence" / "02-second.md").write_text(
            "# evidence 02\n- url: https://example.com/second\n- tier: tier2\n- fetched_at: 2026-09-12\n"
            "- fetch_status: ok\n- supports: c2\n## 原文段落（verbatim）\n> second official statement\n",
            encoding="utf-8",
        )
        print("== selftest: 合规档案（期望 PASS）==")
        good_result, (_, good_failed), _ = _run_isolated(check_archive, good, "expert")
        print("== selftest: 合规档案在 scholar 档（期望 PASS）==")
        scholar_result, (_, scholar_failed), _ = _run_isolated(check_archive, good, "scholar")

        print("== selftest: 缺件档案（期望 FAIL）==")
        bad = Path(td) / "run-bad"
        bad.mkdir()
        (bad / "tech-research.report.md").write_text("# empty\n", encoding="utf-8")
        bad_result, (_, bad_failed), _ = _run_isolated(check_archive, bad, "expert")

        # 2026-09-20 走查修复的回归负例：索引表仍点名 02，但 02 已被删除 → 必须判 FAIL，
        # 且**唯一失败项就是反向断言**（证明红灯确实来自它，而不是被别的断言顺带拦下）。
        print("== selftest: 索引表引用的证据文件缺失（期望 FAIL，唯一失败项=反向断言）==")
        dangling = Path(td) / "run-dangling"
        shutil.copytree(good, dangling)
        (dangling / "evidence" / "02-second.md").unlink()
        dangling_result, (_, dangling_failed), dangling_fails = _run_isolated(check_archive, dangling, "expert")

        # 防**误报**回归（复核 run-053 major#1）：正文顺带提及别处的 evidence 文件名
        # （跨 run 引用 / URL 片段）不算悬空引用 → 期望 PASS。
        print("== selftest: 正文提及别处证据文件名（期望 PASS，防误报）==")
        prose = Path(td) / "run-prose"
        shutil.copytree(good, prose)
        rp = prose / "tech-research.report.md"
        rp.write_text(
            rp.read_text(encoding="utf-8")
            + "\n另可对照 run-047 的 `evidence/01-elsewhere.md`、裸名 03-third.md、"
            + "相对路径 ..\\..\\agents\\runs\\run-047\\evidence\\11-elsewhere.md 与 https://example.com/evidence/09-third.md 。\n",
            encoding="utf-8",
        )
        prose_result, (_, prose_failed), _ = _run_isolated(check_archive, prose, "expert")

        # 防**漏报**回归（复核 run-053 minor）：索引表点名不存在的 .markdown / 一位数编号也要拦住。
        print("== selftest: 索引表点名不存在的 .markdown（期望 FAIL，唯一失败项=反向断言）==")
        weird = Path(td) / "run-weird"
        shutil.copytree(good, weird)
        wp = weird / "tech-research.report.md"
        wp.write_text(
            wp.read_text(encoding="utf-8").replace(
                "| c2 | 02-second.md |\n", "| c2 | 02-second.md |\n| c3 | 07-third.markdown |\n"
            ),
            encoding="utf-8",
        )
        weird_result, (_, weird_failed), weird_fails = _run_isolated(check_archive, weird, "expert")

        # 防**假红**回归（round-2 major#3）：解析侧放宽到 .markdown 时，清单侧必须同步放宽——
        # 否则真实存在且被 §7 点名的 .markdown 证据会被误判悬空（自相矛盾）。
        print("== selftest: 索引表点名已存在的 .markdown（期望 PASS，防假红）==")
        md_ext = Path(td) / "run-md-ext"
        shutil.copytree(good, md_ext)
        (md_ext / "evidence" / "03-extra.markdown").write_text(
            "# evidence 03\n- url: https://example.com/extra\n- tier: tier2\n- fetched_at: 2026-09-12\n"
            "- fetch_status: ok\n- supports: c3\n## 原文段落（verbatim）\n> extra evidence statement\n",
            encoding="utf-8",
        )
        mp = md_ext / "tech-research.report.md"
        mp.write_text(
            mp.read_text(encoding="utf-8").replace(
                "| c2 | 02-second.md |\n", "| c2 | 02-second.md |\n| c3 | 03-extra.markdown |\n"
            ),
            encoding="utf-8",
        )
        md_ext_result, (_, md_ext_failed), _ = _run_isolated(check_archive, md_ext, "expert")

        # 防**假红**回归（round-2 minor#6）：evidence/ 子目录里的文件按 basename 被点名 → 必须 PASS。
        print("== selftest: 嵌套子目录证据被点名（期望 PASS，防假红）==")
        nested = Path(td) / "run-nested"
        shutil.copytree(good, nested)
        (nested / "evidence" / "2026-09").mkdir()
        shutil.move(
            str(nested / "evidence" / "02-second.md"),
            str(nested / "evidence" / "2026-09" / "02-second.md"),
        )
        nested_result, (_, nested_failed), _ = _run_isolated(check_archive, nested, "expert")

        ok("selftest 合规档案全部断言通过", good_result and good_failed == 0)
        ok("selftest 合规档案在 scholar 档通过", scholar_result and scholar_failed == 0)
        ok("selftest 缺件档案被拒（且确有失败项）", (not bad_result) and bad_failed > 0)
        ok(
            "selftest 被引用证据缺失被拒（唯一失败项=反向断言）",
            (not dangling_result)
            and len(dangling_fails) == 1
            and dangling_fails[0].startswith("索引表点名的 evidence 文件全部存在"),
        )
        ok("selftest 正文提及别处证据文件名不误判（防误报回归）", prose_result and prose_failed == 0)
        ok(
            "selftest 索引表点名不存在的 .markdown 被拒（唯一失败项=反向断言）",
            (not weird_result)
            and len(weird_fails) == 1
            and weird_fails[0].startswith("索引表点名的 evidence 文件全部存在"),
        )
        ok("selftest 索引表点名已存在的 .markdown 通过（防假红）", md_ext_result and md_ext_failed == 0)
        ok("selftest 嵌套子目录证据被点名通过（防假红）", nested_result and nested_failed == 0)
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
