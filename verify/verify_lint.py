"""G1 Python 可读性/正确性闸门（ruff）——`§2.3` 语言覆盖表的 Python 行。

判定分级（**分级是刻意的**：先挡真 bug，再谈风格；理由与实测基线见 Sprint-17 §7 与
`pre-research/tech/2026-09-21-lint-deps-security-check.MD` §3.2）：

  * **A 级（硬，全仓）** `E9,F63,F7,F82` —— 语法错误 / 未定义名 / 非法语法类；基线 **0**。
  * **B 级（硬，全仓）** `F401,F811,F841,E702,E711,E712,E722,W292` —— 未用导入/变量、重复定义、
    分号多语句、与 None/True 比较、裸 except、缺行尾换行；基线 **0**（2026-09-23 一次清干净）。
  * **C 级（只报告，不判失败）** `D101,D102,D103,E501` —— docstring 与行宽；实测基线
    D101/102/103 = **610**、E501 = **1398**（2026-09-23）。**棘轮（ratchet）在 `TG-6` 卡实现**，
    本脚本只报数，避免"一次全仓重排"和假绿。

**反向对照**（`TG-6` ⑤"倒过来试"）：本脚本自检会先构造"坏文件"（未定义名 + 未用导入）要求
A/B 级判 FAIL，再构造"好文件"要求 PASS——两条断言在**没有 ruff 或规则选择写错**时都不可能同时成立。

工具缺失时 **fail-closed（退出 2）**；确需在无工具环境跳过时显式传 `--allow-missing`
（打印 `SKIP` + 原因，不静默）。

用法：
    .venv\\Scripts\\python.exe verify\\verify_lint.py
    .venv\\Scripts\\python.exe verify\\verify_lint.py --paths verify scripts   # 只看子集
"""

from __future__ import annotations
VERIFY_META = {'features': 'G1 Python ruff 闸门：A 级 E9/F63/F7/F82 与 B 级 F401/F811/F841/E702/E711/E712/E722/W292 全仓 0；C 级 D101-103/E501 只报基线；含好坏文件反向对照自检', 'tier': 'offline', 'providers': [], 'est_seconds': 15, 'est_cost_cny': 0, 'routes': [], 'requires': ['ruff']}

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

# TG-15：**覆盖路径清单与规则分级都是政策数据**（原先写死在本文件）——换目录/调分级只改
# `agents/policy.json`，不改代码。加载器 fail-closed：数据缺失即 POLICY-ERROR（退出 2）。
_POLICY = load_policy()
DEFAULT_PATHS = list(_POLICY.lint_paths)
HARD_A = str(_POLICY.lint_rules["hard_a"])
HARD_B = str(_POLICY.lint_rules["hard_b"])
REPORT_ONLY = str(_POLICY.lint_rules["report_only"])

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def ruff_cmd() -> list[str] | None:
    """优先用仓库 `.venv` 的 ruff，其次 PATH 上的 `ruff`，最后 `python -m ruff`（CI 装了 wheel 但不在 PATH 时）。"""
    for cand in (ROOT / ".venv" / "Scripts" / "ruff.exe", ROOT / ".venv" / "bin" / "ruff"):
        if cand.exists():
            return [str(cand)]
    which = shutil.which("ruff")
    if which:
        return [which]
    probe = subprocess.run([sys.executable, "-m", "ruff", "--version"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        return [sys.executable, "-m", "ruff"]
    return None


def run_ruff(binary: list[str], select: str, paths: list[str]) -> tuple[int, list[dict]]:
    r = subprocess.run(
        [*binary, "check", "--select", select, "--output-format", "json", *paths],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
    )
    try:
        found = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        found = []
    return r.returncode, found


def codes_of(found: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in found:
        code = (item.get("code") or "?")
        counts[code] = counts.get(code, 0) + 1
    return counts


def summarize(found: list[dict], limit: int = 6) -> str:
    out = []
    for item in found[:limit]:
        loc = item.get("filename", "?")
        try:
            loc = str(Path(loc).relative_to(ROOT))
        except ValueError:
            pass
        row = item.get("location", {}).get("row", "?")
        out.append(f"{loc}:{row} {item.get('code')}")
    return "; ".join(out) + (" …" if len(found) > limit else "")


BAD_FIXTURE = '''"""反向对照用坏文件（故意违规）。"""
import json  # F401 未使用


def f():
    return undefined_name_xyz()  # F82 未定义名
'''

GOOD_FIXTURE = '''"""反向对照用好文件（应当通过 A/B 级）。"""
import json


def f():
    """返回一个常量。"""
    return json.dumps({})
'''


def main() -> int:
    binary = ruff_cmd()
    if binary is None:
        if "--allow-missing" in sys.argv:
            print("SKIP: 未找到 ruff（--allow-missing 显式放行）；原因：环境未安装或不在 PATH")
            print("\nALL PASS (0 assertions, skipped)")
            return 0
        print("LINT-ERROR: 未找到 ruff —— fail-closed（安装：pip install -r requirements-windows.txt；"
              "确需跳过用 --allow-missing）")
        return 2

    ver = subprocess.run([*binary, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"[tool] {ver}")

    paths = DEFAULT_PATHS
    if "--paths" in sys.argv:
        paths = sys.argv[sys.argv.index("--paths") + 1:]

    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad_fixture.py"
        good = Path(td) / "good_fixture.py"
        bad.write_text(BAD_FIXTURE, encoding="utf-8")
        good.write_text(GOOD_FIXTURE, encoding="utf-8")

        rc_bad_a, found_bad_a = run_ruff(binary, HARD_A, [str(bad)])
        ok("自检 ① 坏文件在 A 级（E9/F63/F7/F82）判 FAIL", rc_bad_a != 0 and "F821" in codes_of(found_bad_a),
           f"rc={rc_bad_a} codes={codes_of(found_bad_a)}")
        rc_bad_b, found_bad_b = run_ruff(binary, HARD_B, [str(bad)])
        ok("自检 ② 坏文件在 B 级（未用导入）判 FAIL", rc_bad_b != 0 and "F401" in codes_of(found_bad_b),
           f"rc={rc_bad_b} codes={codes_of(found_bad_b)}")
        rc_good, found_good = run_ruff(binary, f"{HARD_A},{HARD_B}", [str(good)])
        ok("自检 ③ 好文件在 A+B 级判 PASS（防假红）", rc_good == 0 and not found_good,
           f"rc={rc_good} codes={codes_of(found_good)}")

    rc_a, found_a = run_ruff(binary, HARD_A, paths)
    ok(f"A 级硬闸门（{HARD_A}）全仓为 0", rc_a == 0 and not found_a,
       f"paths={paths} findings={len(found_a)} {summarize(found_a)}")

    rc_b, found_b = run_ruff(binary, HARD_B, paths)
    ok(f"B 级硬闸门（{HARD_B}）全仓为 0", rc_b == 0 and not found_b,
       f"findings={len(found_b)} {summarize(found_b)}")

    rc_c, found_c = run_ruff(binary, REPORT_ONLY, paths)
    counts_c = codes_of(found_c)
    print(f"[report-only C 级] {REPORT_ONLY} → {sum(counts_c.values())} 条 {counts_c}"
          f"（棘轮见 TG-6；本脚本不据此判失败）")
    ok("C 级基线被真实采集（>0 条；若归零说明规则选择或工具行为变了，需复核）",
       sum(counts_c.values()) > 0, f"counts={counts_c}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
