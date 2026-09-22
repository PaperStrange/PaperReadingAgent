"""TG-11 ③b：关闭前置闸门（offline）——把"三查失效"变成机器可判定的不等式。

背景：Sprint-16 的三查在 2026-09-12 跑过，之后仍有 20→26 个提交落地，
但**没有任何装置**表达"三查已失效"（证据：`phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD`）。
本脚本按 TG-11 卡 ③b 与证据台账 §4 的六个反向对照场景，把下列判据做成断言：

  ① 存在〇查 run（impact-assessment）且**早于**二查；
  ② 二查（code-review）**两条**：`task_id` 分别覆盖 `windows` 与 `main`；
  ③ 一查（doc-audit）与 lessons-learned 各 ≥1 条；
  ④ 每条 `scope_source=self-chosen` 的 run 必须有非空 `scope_deviation`；
  ⑤ Sprint §9 的结构化 run 表与账本**双向一致**（表里有 → 账本有；账本有 → 表里有）；
  ⑥ **三查锚点**：文档须声明 `三查锚点: <sha>`，且锚点之后不得有未评审提交（`git rev-list <sha>..HEAD` 为空）。

用法：
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py                  # 自检（合成 fixture）
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py --sprint <文件>  # 真数据校验（关闭时）

**为什么默认只跑自检**：Sprint-17 未关闭时真数据模式必然 FAIL（这是正确的 fail-closed 语义），
但会让 offline 套件长期变红。故套件跑自检；关闭时由主代理跑 `--sprint` 并把输出写进 Sprint §9；
M4（接入 CI / PR 前置）要求在 CI 里对**当前 Sprint**跑 `--sprint`。

§9 结构化 run 表的格式（M3，供本脚本解析）：
    | run_id | role | target | scope_source | coverage | deviation |
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-11 关闭前置闸门：〇查先于二查 / 二查双分支 / 一查+lessons / self-chosen 须 deviation / §9↔账本双向一致 / 三查锚点后无未评审提交（含 9 条自检反向对照）', 'tier': 'offline', 'providers': [], 'est_seconds': 10, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSE_ROLES = {"impact-assessment", "code-review", "doc-audit", "lessons-learned"}
ROW_SPLIT = re.compile(r"(?<!\\)\|")
ANCHOR_RE = re.compile(r"\**三查锚点\**\s*[:：]\s*`?([0-9a-fA-F]{7,40})`?")
TABLE_HEADER = "| run_id | role | target | scope_source | coverage | deviation |"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def warn(name: str, detail: str = "") -> None:
    print(f"WARN: {name} {detail}")


def registry_path() -> Path:
    base = Path(os.environ.get("AGENT_OPS_DIR", str(ROOT / "agents")))
    return base / "runtime" / "registry.json"


def parse_sprint(doc: str) -> dict:
    """解析 §9 结构化 run 表 + 三查锚点（容错：表格列数 ≥5 且首列以 run- 开头）。"""
    rows = []
    for line in doc.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in ROW_SPLIT.split(line)[1:-1]]
        if len(cells) >= 5 and cells[0].startswith("run-"):
            rows.append({
                "run_id": cells[0], "role": cells[1], "target": cells[2],
                "scope_source": cells[3], "coverage": cells[4],
                "deviation": cells[5] if len(cells) > 5 else "",
            })
    m = ANCHOR_RE.search(doc)
    return {"rows": rows, "anchor": m.group(1) if m else None}


def evaluate(sprint: dict, runs: list[dict], rev_list=None) -> list[str]:
    """返回失败原因列表（空 = 通过）。`rev_list(anchor) -> [sha,…]` 可注入，便于自检。"""
    problems: list[str] = []
    by_id = {r.get("run_id"): r for r in runs}
    table_ids = {row["run_id"] for row in sprint["rows"]}

    kick = [r for r in runs if r.get("role") == "impact-assessment"]
    second = [r for r in runs if r.get("role") == "code-review"]
    if not kick:
        problems.append("① 账本中没有〇查 run（impact-assessment）")
    if not second:
        problems.append("② 账本中没有二查 run（code-review）")
    if kick and second:
        k = min((r.get("started_at") or "") for r in kick)
        s = min((r.get("started_at") or "") for r in second)
        if not k or not s:
            problems.append("① 〇查/二查缺少 started_at，无法判定先后")
        elif k >= s:
            problems.append(f"① 〇查（{k}）未早于二查（{s}）")

    tasks = " ".join((r.get("task_id") or "") for r in second)
    for need in ("windows", "main"):
        if need not in tasks:
            problems.append(f"② 二查缺少 {need} 分支任务（task_id 中未见 '{need}'）")

    if not [r for r in runs if r.get("role") == "doc-audit"]:
        problems.append("③ 缺少一查（doc-audit）")
    if not [r for r in runs if r.get("role") == "lessons-learned"]:
        problems.append("③ 缺少 lessons-learned")

    for r in runs:
        if r.get("scope_source") == "self-chosen" and not (r.get("scope_deviation") or "").strip():
            problems.append(f"④ {r.get('run_id')} 自选范围但未声明 deviation")

    # ⑤ 双向一致：只看"关闭相关 role"，且以 §9 表中最早 run 为窗口起点（避免误报历史 sprint 的 run）
    window = [r.get("started_at") or "" for row in sprint["rows"]
              if (r := by_id.get(row["run_id"])) is not None]
    window_start = min(window) if window else None
    scoped = [r for r in runs if r.get("role") in CLOSE_ROLES
              and (window_start is None or (r.get("started_at") or "") >= window_start)]
    for rid in sorted(table_ids - set(by_id)):
        problems.append(f"⑤ §9 写了 run 但账本无记录：{rid}")
    for r in scoped:
        if r.get("run_id") not in table_ids:
            problems.append(f"⑤ 账本有 run 但 §9 run 表未登记：{r.get('run_id')}")

    anchor = sprint.get("anchor")
    if not anchor:
        problems.append("⑥ 未声明三查锚点（`三查锚点: <sha>`）→ 无法判定三查是否失效")
    elif rev_list is not None:
        dirty = rev_list(anchor)
        if dirty:
            problems.append("⑥ 三查锚点之后存在未评审提交：" + ", ".join(dirty[:5]))

    return problems


def git_rev_list(anchor: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(ROOT), "rev-list", f"{anchor}..HEAD"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return [f"<git rev-list 失败：{(r.stderr or '').strip()[:60]}>"]
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


# ---------------------------------------------------------------- 自检 fixture


def _run(rid: str, role: str, task: str, started: str, scope="", dev=None) -> dict:
    return {"run_id": rid, "role": role, "task_id": task, "started_at": started,
            "status": "succeeded", "scope_source": scope, "scope_deviation": dev}


def _doc(rows: list[dict], anchor: str | None) -> str:
    lines = ["# Sprint 示例", "", "## 9. 关闭三查记录（结构化 run 表）", "",
             TABLE_HEADER, "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            row["run_id"], row["role"], row.get("target", "-"),
            row.get("scope_source", "-"), row.get("coverage", "-"), row.get("deviation", "-")))
    if anchor:
        lines += ["", f"三查锚点: `{anchor}`"]
    return "\n".join(lines)


def _good() -> tuple[dict, list[dict]]:
    runs = [
        _run("run-k-001", "impact-assessment", "planned", "2026-09-21T01:00:00+00:00"),
        _run("run-d-002", "doc-audit", "docs", "2026-09-21T02:00:00+00:00",
             "impact-assessment:run-k-001"),
        _run("run-c-003", "code-review", "branch:windows", "2026-09-21T02:10:00+00:00",
             "impact-assessment:run-k-001"),
        _run("run-c-004", "code-review", "branch:main", "2026-09-21T02:20:00+00:00",
             "impact-assessment:run-k-001"),
        _run("run-l-005", "lessons-learned", "sprint-17", "2026-09-21T03:00:00+00:00"),
        _run("run-c-006", "code-review", "fix:bug", "2026-09-21T04:00:00+00:00",
             "self-chosen", "仅复现用户报告的按钮缺陷（偏离声明，留痕）"),
    ]
    rows = [{"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
             "scope_source": r.get("scope_source") or "-",
             "coverage": "core", "deviation": r.get("scope_deviation") or "-"} for r in runs]
    return parse_sprint(_doc(rows, "a" * 40)), runs


def main() -> int:
    if "--sprint" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--sprint") + 1])
        if not path.exists():
            print(f"CLOSE-READINESS-ERROR: Sprint 文档不存在：{path}（fail-closed，不静默放行）")
            return 2
        data = json.loads(registry_path().read_text(encoding="utf-8"))
        sprint = parse_sprint(path.read_text(encoding="utf-8"))
        problems = evaluate(sprint, data.get("runs", []), rev_list=git_rev_list)
        if problems:
            print(f"CLOSE-READINESS FAIL（{len(problems)} 项）：")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"CLOSE-READINESS PASS：{path.name}（run 表 {len(sprint['rows'])} 行，锚点 {sprint['anchor'][:8]}）")
        return 0

    # ---- 自检：六个反向对照场景（+ 三个边界）逐个断言
    good_sprint, good_runs = _good()
    ok("自检 ① 合规场景 + 锚点干净 → PASS", evaluate(good_sprint, good_runs, rev_list=lambda a: []) == [],
       "problems=[]")

    no_kick = [r for r in good_runs if r["role"] != "impact-assessment"]
    rows = [row for row in good_sprint["rows"] if row["role"] != "impact-assessment"]
    p = evaluate(parse_sprint(_doc(rows, "a" * 40)), no_kick, rev_list=lambda a: [])
    ok("自检 ② 省掉〇查 → FAIL", any(x.startswith("①") or x.startswith("⑤") for x in p), f"problems={p[:2]}")

    one_branch = [dict(r, task_id="branch:windows") if r["role"] == "code-review" else r
                  for r in good_runs if r["run_id"] != "run-c-004"]
    rows = [row for row in good_sprint["rows"] if row["run_id"] != "run-c-004"]
    p = evaluate(parse_sprint(_doc(rows, "a" * 40)), one_branch, rev_list=lambda a: [])
    ok("自检 ③ 二查只有 windows → FAIL", any(x.startswith("②") for x in p), f"problems={p[:2]}")

    selfchosen = [r if r["run_id"] != "run-c-006" else dict(r, scope_deviation=None) for r in good_runs]
    p = evaluate(good_sprint, selfchosen, rev_list=lambda a: [])
    ok("自检 ④ self-chosen 无 deviation → FAIL", any(x.startswith("④") for x in p), f"problems={p[:2]}")

    p = evaluate(good_sprint, good_runs, rev_list=lambda a: ["deadbeef1", "deadbeef2"])
    ok("自检 ⑤ 锚点后存在未评审提交（最小复现）→ FAIL", any(x.startswith("⑥") for x in p), f"problems={p[:2]}")

    ghost = parse_sprint(_doc(good_sprint["rows"] + [{"run_id": "run-ghost-999", "role": "code-review",
                                                      "target": "branch:main", "scope_source": "-",
                                                      "coverage": "core", "deviation": "-"}], "a" * 40))
    p = evaluate(ghost, good_runs, rev_list=lambda a: [])
    ok("自检 ⑥ §9 写了 run 但账本无记录 → FAIL", any("账本无记录" in x for x in p), f"problems={p[:2]}")

    rows = [row for row in good_sprint["rows"] if row["run_id"] != "run-c-006"]
    p = evaluate(parse_sprint(_doc(rows, "a" * 40)), good_runs, rev_list=lambda a: [])
    ok("自检 ⑦ 账本有 run 但 §9 未登记 → FAIL", any("未登记" in x for x in p), f"problems={p[:2]}")

    p = evaluate(parse_sprint(_doc(good_sprint["rows"], None)), good_runs, rev_list=lambda a: [])
    ok("自检 ⑧ 未声明三查锚点 → FAIL", any(x.startswith("⑥") for x in p), f"problems={p[:2]}")

    probe = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--sprint", "docs/iteration/sprint/__no_such_sprint__.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok("自检 ⑨ 真数据模式对不存在的 Sprint 文档 fail-closed（退出 2，不静默放行）",
       probe.returncode == 2 and "CLOSE-READINESS-ERROR" in (probe.stdout + probe.stderr),
       f"rc={probe.returncode} out={(probe.stdout + probe.stderr).strip()[:60]}")

    real = registry_path()
    if real.exists():
        n = len(json.loads(real.read_text(encoding="utf-8")).get("runs", []))
        warn("真数据模式未在自检中执行（需 `--sprint <当前 Sprint 文档>`）", f"账本 {n} 条：{real}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
