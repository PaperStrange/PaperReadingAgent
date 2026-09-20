"""M18 v1：报告时效检测（`scripts/report-freshness.py`）的离线回归。

全部**合成 fixture**（不碰真实 `agents/runs`、不联网、零成本），并通过 CLI 参数重定向，
顺带验证命令行契约（`--runs-dir/--providers-dir/--json/--check/--only`）：
  ① 依据未变 → `fresh`；② provider 在归档之后刷新过 → `stale`（原因点名 provider）；
  ③ 报告 §7 点名的证据缺失 → `stale`；④ 证据在报告之后被改动 → `suspect`；
  ⑤ 只分析**调研归档**（无 report / 非调研 role 跳过——真实数据上曾把 `1-WORKFLOW.MD` 误判为缺失证据）；
  ⑥ 结果 JSON 结构（summary/reports/providers）；
  ⑦ `--check` 退出码（有 stale → 1；全 fresh → 0）；⑧ `--only` 过滤；
  ⑨ `+0900` 偏移时间可解析；⑩ providers 目录缺失/坏文件不影响主流程；⑪ runs 目录不存在 → 0 份、退出 0。

Run: .venv\\Scripts\\python.exe verify\\verify_freshness.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'M18 v1 报告时效检测：fresh/stale/suspect 三态规则 + CLI 契约（--check/--only/重定向）+ 偏移时间解析 + 容错（离线合成 fixture）', 'tier': 'offline', 'providers': [], 'est_seconds': 8, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "report-freshness.py"
PY = sys.executable
PASSED = 0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(SCRIPT), *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)


def write_report(run_dir: Path, title: str, cites: list[str]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| 结论 | `evidence/{n}` | ok | 摘录 |" for n in cites)
    rp = run_dir / "tech-research.report.md"
    rp.write_text(
        f"# tech-research report（{title}）\n" + "填充" * 120 + f"\n## 7. 证据索引表\n| 结论 | evidence | 状态 | 摘录 |\n|---|---|---|---|\n{rows}\n",
        encoding="utf-8",
    )
    return rp


def write_evidence(run_dir: Path, name: str, fetched_at: str, supports: str = "demo") -> Path:
    ev = run_dir / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    p = ev / name
    p.write_text(
        f"# evidence\n- url: https://example.com/{name}\n- tier: tier1\n- fetched_at: {fetched_at}\n"
        f"- fetch_status: ok\n- supports: {supports}\n## 原文段落（verbatim）\n> demo quote\n",
        encoding="utf-8",
    )
    return p


def build_providers(d: Path, fetched_at: str | None, model: str = "m1") -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "base.json").write_text(json.dumps({
        "name": "base", "model": model, "embedding": "e1",
        "meta": {"fetched_at": fetched_at, "source_urls": ["https://example.com"], "last_refresh_status": "ok"},
    }, ensure_ascii=False), encoding="utf-8")
    return d


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        runs = base / "runs"
        out_json = base / "freshness.json"

        # ① fresh：provider 刷新时间早于证据
        a = runs / "run-a"
        rp_a = write_report(a, "fresh case", ["01-a.md"])
        write_evidence(a, "01-a.md", "2026-09-10 10:00 +0800")
        prov_old = build_providers(base / "prov_old", "2026-08-01T00:00:00+08:00")

        # ② stale：provider 在归档之后刷新过
        b = runs / "run-b"
        write_report(b, "refreshed-since case", ["01-b.md"])
        write_evidence(b, "01-b.md", "2026-09-01 10:00 +0800")
        prov_new = build_providers(base / "prov_new", "2026-09-15T09:30:00+0900")  # +0900 偏移

        # ③ stale：报告点名但磁盘缺失
        c = runs / "run-c"
        write_report(c, "missing-evidence case", ["01-c.md", "02-missing.md"])
        write_evidence(c, "01-c.md", "2026-09-20 10:00 +0800")

        # ④ suspect：证据在报告之后被改动
        d = runs / "run-d"
        rp_d = write_report(d, "evidence-modified case", ["01-d.md"])
        ev_d = write_evidence(d, "01-d.md", "2026-09-20 10:00 +0800")
        os.utime(rp_d, (time.time() - 3600, time.time() - 3600))
        os.utime(ev_d, (time.time(), time.time()))

        # ⑤ 非调研目录（无 report）→ 跳过
        (runs / "run-not-research").mkdir(parents=True, exist_ok=True)
        (runs / "run-not-research" / "context.md").write_text("x", encoding="utf-8")

        # ⑤b 非调研 role 的报告（引用项目文档、无 evidence/）→ **跳过**（真实数据上曾产生假阳性）
        docref = runs / "run-docref"
        docref.mkdir(parents=True, exist_ok=True)
        (docref / "code-review.report.md").write_text(
            "# code-review report\n" + "正文" * 60 + "\n## 7. 证据索引表\n| 结论 | evidence |\n|---|---|\n| a | `1-WORKFLOW.MD` |\n",
            encoding="utf-8",
        )

        # ⑤c 调研归档：正文（§7 之外）提到形如证据名的文件 → **不算引用**（只在索引表区间内判定）
        bodymention = runs / "run-bodymention"
        write_report(bodymention, "body-mention case", ["01-e.md"])
        write_evidence(bodymention, "01-e.md", "2026-09-19 10:00 +0800")
        rp_bm = bodymention / "tech-research.report.md"
        rp_bm.write_text(
            rp_bm.read_text(encoding="utf-8") + "\n另见正文提及 `9-gone.md` 与 `evidence/08-ghost.md`（非索引表引用）。\n",
            encoding="utf-8",
        )

        # 有 stale 的场景（prov_new 晚于 run-a 证据）
        res = run(["--runs-dir", str(runs), "--providers-dir", str(prov_new), "--json", str(out_json)])
        ok("① 退出码 0（普通模式即使有 stale 也成功）", res.returncode == 0, f"exit={res.returncode}")
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        by_id = {r["run_id"]: r for r in payload["reports"]}
        ok("⑤ 只分析调研归档（5 份；无 report 与非调研 role 均跳过）", len(payload["reports"]) == 5, str(sorted(by_id)))
        ok("⑤b 非调研 role 报告（引用 `1-WORKFLOW.MD`）被跳过，不产生假阳性",
           "run-docref" not in by_id, str(sorted(by_id)))
        ok("⑤c 正文（§7 之外）提及的疑似证据名不算引用（只在索引表区间内判定）",
           by_id["run-bodymention"]["status"] == "fresh", json.dumps(by_id["run-bodymention"]["reasons"], ensure_ascii=False))
        ok("② provider 在归档之后刷新过 → stale 且原因点名",
           by_id["run-b"]["status"] == "stale" and any("base" in w for w in by_id["run-b"]["reasons"]),
           json.dumps(by_id["run-b"]["reasons"], ensure_ascii=False))
        ok("③ 报告点名证据缺失 → stale",
           by_id["run-c"]["status"] == "stale" and any("缺失" in w for w in by_id["run-c"]["reasons"]),
           json.dumps(by_id["run-c"]["reasons"], ensure_ascii=False))
        ok("④ 证据晚于报告被改动 → suspect（非 stale）",
           by_id["run-d"]["status"] == "suspect", json.dumps(by_id["run-d"]["reasons"], ensure_ascii=False))
        ok("⑨ `+0900` 偏移时间被解析（provider fetched_ts 非空）",
           payload["providers"]["base"]["fetched_ts"] is not None, str(payload["providers"]["base"]["fetched_ts"]))
        ok("⑥ 结果 JSON 结构齐备", {"generated_at", "summary", "reports", "providers"} <= set(payload),
           str(sorted(payload)))
        ok("⑥ summary 计数与明细一致",
           payload["summary"]["total"] == 5
           and payload["summary"]["stale"] == len([r for r in payload["reports"] if r["status"] == "stale"])
           and payload["summary"]["suspect"] == len([r for r in payload["reports"] if r["status"] == "suspect"]),
           json.dumps(payload["summary"], ensure_ascii=False))

        # ⑨b 时区口径：证据头 `... UTC+8`（字面标签）+ provider meta `+08:00`，同轮刷新差 < 容差 → fresh
        tz_case = runs / "run-tz"
        write_report(tz_case, "timezone case", ["01-tz.md"])
        write_evidence(tz_case, "01-tz.md", "2026-09-20 23:23 UTC+8")
        prov_tz = base / "prov_tz"
        prov_tz.mkdir(parents=True, exist_ok=True)
        (prov_tz / "base.json").write_text(json.dumps({
            "name": "base", "model": "m1", "embedding": "e1",
            "meta": {"fetched_at": "2026-09-20T23:23:45+08:00"},
        }, ensure_ascii=False), encoding="utf-8")
        res_tz = run(["--runs-dir", str(runs), "--providers-dir", str(prov_tz), "--json", str(base / "tz.json"),
                      "--only", "run-tz"])
        tz_payload = json.loads((base / "tz.json").read_text(encoding="utf-8"))
        ok("⑨b `UTC+8` 字面标签 + `+08:00` 同轮刷新 → fresh（不因本机 UTC+9 偏 1 小时误判）",
           res_tz.returncode == 0 and tz_payload["reports"][0]["status"] == "fresh",
           json.dumps(tz_payload["reports"][0]["reasons"], ensure_ascii=False))

        # ⑨c 复核 Round 5 major#2：§7 写成**项目符号**（无表格行）时，点名缺失的证据也必须报出来
        #     （此前只认表格行 → 该形态完全静默假阴性，且与归档门禁口径不一致）
        bullet = runs / "run-bullet"
        bullet.mkdir(parents=True, exist_ok=True)
        (bullet / "tech-research.report.md").write_text(
            "# tech-research report（bullet §7）\n" + "填充" * 120
            + "\n## 7. 证据索引表\n- 结论 c1 → `evidence/01-b.md`\n- 结论 c9 → `evidence/09-ghost.md`\n",
            encoding="utf-8",
        )
        write_evidence(bullet, "01-b.md", "2026-09-19 10:00 +0800")
        res_bullet = run(["--runs-dir", str(runs), "--providers-dir", str(prov_tz), "--json", str(base / "b.json"),
                          "--only", "run-bullet"])
        bp = json.loads((base / "b.json").read_text(encoding="utf-8"))
        ok("⑨c §7 用项目符号时也能报出点名缺失（Round 5 major#2 回归）",
           res_bullet.returncode == 0 and bp["reports"][0]["status"] == "stale"
           and any("09-ghost.md" in w for w in bp["reports"][0]["reasons"]),
           json.dumps(bp["reports"][0]["reasons"], ensure_ascii=False))

        # ⑨d 复核 minor#2：只有空 `evidence/` 目录、报告名又不是 tech-research → 不算调研归档（跳过）
        empty_ev = runs / "run-empty-ev"
        (empty_ev / "evidence").mkdir(parents=True, exist_ok=True)
        (empty_ev / "code-review.report.md").write_text("# code-review\n" + "正文" * 60, encoding="utf-8")
        res_skip = run(["--runs-dir", str(runs), "--providers-dir", str(prov_tz), "--json", str(base / "e.json")])
        ep = json.loads((base / "e.json").read_text(encoding="utf-8"))
        ok("⑨d 空 evidence/ + 非 tech-research 报告 → 跳过",
           all(r["run_id"] != "run-empty-ev" for r in ep["reports"]), str([r["run_id"] for r in ep["reports"]]))

        # ⑨e 复核 minor#3：同目录多报告时按 `find_report` 口径取 `tech-research.report.md`
        multi = runs / "run-multi-report"
        write_report(multi, "multi case", ["01-m.md"])
        write_evidence(multi, "01-m.md", "2026-09-19 10:00 +0800")
        (multi / "code-review.report.md").write_text("# other role report\n" + "正文" * 60, encoding="utf-8")
        run(["--runs-dir", str(runs), "--providers-dir", str(prov_tz), "--json", str(base / "m.json"),
             "--only", "run-multi-report"])
        mp = json.loads((base / "m.json").read_text(encoding="utf-8"))
        ok("⑨e 多报告目录按 tech-research.report.md 口径分析（与归档门禁一致）",
           bool(mp["reports"]) and mp["reports"][0]["report"].endswith("tech-research.report.md"),
           mp["reports"][0]["report"] if mp["reports"] else "no report")

        # ⑨f 复核 minor#6：`--fail-on suspect` 时"仅 suspect"也要退 1（默认阈值下退 0）
        only_suspect = runs / "run-only-suspect"
        rp_os = write_report(only_suspect, "only suspect", ["01-s.md"])
        ev_os = write_evidence(only_suspect, "01-s.md", "2026-09-19 10:00 +0800")
        os.utime(rp_os, (time.time() - 7200, time.time() - 7200))
        os.utime(ev_os, (time.time(), time.time()))
        res_s = run(["--runs-dir", str(runs), "--providers-dir", str(prov_old), "--json", str(base / "s.json"),
                     "--only", "run-only-suspect", "--check", "--fail-on", "suspect"])
        ok("⑨f --fail-on suspect → 仅 suspect 也退 1", res_s.returncode == 1, f"exit={res_s.returncode}")
        res_s0 = run(["--runs-dir", str(runs), "--providers-dir", str(prov_old), "--json", str(base / "s0.json"),
                      "--only", "run-only-suspect", "--check"])
        ok("⑨f 默认阈值下仅 suspect → 退 0", res_s0.returncode == 0, f"exit={res_s0.returncode}")

        # ⑦ --check：有 stale → 退出 1
        res_check = run(["--runs-dir", str(runs), "--providers-dir", str(prov_new), "--json", str(out_json), "--check"])
        ok("⑦ --check 有 stale → 退出 1", res_check.returncode == 1, f"exit={res_check.returncode}")

        # ⑦b 全 fresh（老 provider + 只扫 run-a）→ 退出 0
        res_fresh = run(["--runs-dir", str(runs), "--providers-dir", str(prov_old), "--json", str(out_json),
                         "--only", "run-a", "--check"])
        ok("⑦ --check 全 fresh → 退出 0", res_fresh.returncode == 0, f"exit={res_fresh.returncode}")
        payload_fresh = json.loads(out_json.read_text(encoding="utf-8"))
        ok("⑧ --only 只分析匹配子串的归档",
           [r["run_id"] for r in payload_fresh["reports"]] == ["run-a"]
           and payload_fresh["reports"][0]["status"] == "fresh",
           json.dumps([(r["run_id"], r["status"]) for r in payload_fresh["reports"]], ensure_ascii=False))

        # ⑩ providers 目录缺失 / 含坏文件 → 不崩
        res_noprov = run(["--runs-dir", str(runs), "--providers-dir", str(base / "nope"), "--json", str(base / "n2.json"),
                          "--only", "run-a"])
        ok("⑩ providers 目录缺失 → 正常完成（providers={}）", res_noprov.returncode == 0, f"exit={res_noprov.returncode}")
        bad_dir = base / "prov_bad"
        bad_dir.mkdir()
        (bad_dir / "broken.json").write_text("{ not json", encoding="utf-8")
        res_bad = run(["--runs-dir", str(runs), "--providers-dir", str(bad_dir), "--json", str(base / "n3.json"),
                       "--only", "run-a"])
        ok("⑩ providers 坏文件被跳过且不崩", res_bad.returncode == 0, f"exit={res_bad.returncode}")

        # ⑪ runs 目录不存在 → 0 份归档、退出 0
        res_empty = run(["--runs-dir", str(base / "no-runs"), "--providers-dir", str(prov_old),
                         "--json", str(base / "n4.json")])
        ok("⑪ runs 目录不存在 → 0 份归档且退出 0", res_empty.returncode == 0 and "0 份归档" in res_empty.stdout,
           (res_empty.stdout or "").strip().splitlines()[0][:60] if res_empty.stdout else "")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
