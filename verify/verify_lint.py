"""G1 Python 可读性/正确性闸门（ruff）——`§2.3` 语言覆盖表的 Python 行。

判定分级（**分级是刻意的**：先挡真 bug，再谈风格；理由与实测基线见 Sprint-17 §7 与
`pre-research/tech/2026-09-21-lint-deps-security-check.MD` §3.2）：

  * **A 级（硬，全仓）** `E9,F63,F7,F82` —— 语法错误 / 未定义名 / 非法语法类；基线 **0**。
  * **B 级（硬，全仓）** `F401,F811,F841,E702,E711,E712,E722,W292` —— 未用导入/变量、
    重复定义、分号多语句、与 None/True 比较、裸 except、缺行尾换行；基线 **0**
    （2026-09-23 一次清干净）。
  * **C 级（棘轮，2026-09-25 / TG-6 起）** `D101,D102,D103,E501` —— docstring 与行宽。
    **规则分级与上限都来自 policy**（`lint_rules` + `lint_readability_ratchet`）：
    判 `计数 > cap → FAIL` 并**逐条点名**（规则号 + 实测 + 上限）；
    `review_by` 过期同样 FAIL。cap **只许下调**；caps 键集必须与
    `lint_rules.report_only` **逐键相等**（少一条 = 该类无限放行；多一条 = 死数据）。

    ⚠️ **计数会随正常改动漂移**（增删代码行/函数/字符串都改变数字）：本文件与卡片里
    手抄过的读数（610/1398、11/42/191~192/1774~1804）**实测都漂过**——一律以**当次
    实测**为准：先看 `[report-only C 级]` 行，再据实测值重评基线（只许下调）。

**反向对照**（`TG-6` ⑤"倒过来试"，全部是**真实 ruff 调用**，不是读代码猜）：

  ① 坏文件在 A 级判 FAIL、② 坏文件在 B 级判 FAIL、③ 好文件判 PASS（防假红）；
  ④ 干净副本 + **实测上限** → 棘轮零 problem（等价 rc=0，防假红）；
  ⑤ 临时副本里**注入 1 处新的 C 级违规**（缺 docstring 的公开函数、一行超长行）
     → 同一上限下必须 FAIL 并点名 D103/E501（cap 真的"咬得住"，不是摆设）；
  ⑥ `review_by` 设为过去 → FAIL；⑦ caps 少一类 → FAIL；⑧ caps 多出拼错的键 →
     FAIL（棘轮基线自身不得被静默关掉）。

**机读证据行（TG-6，2026-09-25 立规）**：成功路径打印一行可 grep 的证据——
`EVIDENCE: verify_lint.py assertions=N rc=0 …`（失败/SKIP 不打印；见 §6）。

工具缺失时 **fail-closed（退出 2）**；确需在无工具环境跳过时显式传 `--allow-missing`
（打印 `SKIP` + 原因，不静默）。

用法：
    .venv\\Scripts\\python.exe verify\\verify_lint.py
    .venv\\Scripts\\python.exe verify\\verify_lint.py --paths verify scripts   # 子集
"""

from __future__ import annotations
VERIFY_META = {'features': 'G1 Python ruff 闸门：A 级 E9/F63/F7/F82 与 B 级 F401/F811/F841/E702/E711/E712/E722/W292 全仓 0；C 级 D101-103/E501 改为棘轮（caps+review_by 来自 policy，计数>cap 即 FAIL 点名；含干净副本/注入违规/过期/缺键/多键五条反向对照）+ EVIDENCE 机读证据行', 'tier': 'offline', 'providers': [], 'est_seconds': 15, 'est_cost_cny': 0, 'routes': [], 'requires': ['ruff']}

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

# TG-15：**覆盖路径清单与规则分级都是政策数据**（原先写死在本文件）——换目录/调分级只改
# `agents/policy.json`，不改代码。加载器 fail-closed：数据缺失即 POLICY-ERROR（退出 2）
# 。
# TG-6：**C 级的计数上限与到期日同样是政策数据**（`lint_readability_ratchet`），
# 理由与"只许下调"的纪律写在该键的 `_comment` 与 policy 属性的 docstring 里，
# 本文件不另抄一份（政策只有一处真源）。
_POLICY = load_policy()
DEFAULT_PATHS = list(_POLICY.lint_paths)
HARD_A = str(_POLICY.lint_rules["hard_a"])
HARD_B = str(_POLICY.lint_rules["hard_b"])
REPORT_ONLY = str(_POLICY.lint_rules["report_only"])
# caps 的键集必须与规则集逐键相等（判据在 `ratchet_problems`，不在这里静默取交集）。
C_RULES: tuple[str, ...] = tuple(r.strip() for r in REPORT_ONLY.split(",") if r.strip())
C_CAPS: dict[str, int] = _POLICY.lint_readability_caps()
C_REVIEW_BY: str = _POLICY.lint_readability_review_by()
C_MEASURED_AT: str = str(_POLICY.lint_readability_ratchet["measured_at"])

# 项目权威时区 UTC+8（与账本/产物目录命名同口径，见 scripts/agent-ops.py 的 A5 说明）
PROJECT_TZ = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def ruff_cmd() -> list[str] | None:
    """优先用仓库 `.venv` 的 ruff，其次 PATH 上的 `ruff`，最后 `python -m ruff`。

    第三种留给"CI 装了 wheel 但不在 PATH"的情形。
    """
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
    """跑一次 ruff，返回 `(退出码, JSON 发现列表)`（解析失败按空列表处理）。"""
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
    """按规则号计数。"""
    counts: dict[str, int] = {}
    for item in found:
        code = (item.get("code") or "?")
        counts[code] = counts.get(code, 0) + 1
    return counts


def summarize(found: list[dict], limit: int = 6) -> str:
    """把前若干条发现压成 `路径:行 规则号` 串（失败时点名用）。"""
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


def ratchet_problems(counts: dict[str, int], caps: dict[str, int], review_by: str,
                     today: str, rules: tuple[str, ...] = C_RULES) -> list[str]:
    """C 级棘轮判定（**纯函数**：反向对照直接驱动它，不必往仓库里造几千条真违规）。

    四条判据（每条都对应一种"棘轮被静默关掉"的形态）：

      * **caps 键集 ↔ 规则集逐键相等**：少一条 = 该规则**无限放行**
        （确已清零要显式写 0，不要删键）；
      * 多一条 = 死数据/拼写漂移（上限表与规则集分叉）；
      * **`计数 > cap` → FAIL 并点名**（规则号 + 实测 + 上限 + 超出条数）；
      * **`review_by` 过期 → FAIL**（没有到期日的豁免就是永久豁免）。
    """
    problems: list[str] = []
    expected, actual_keys = set(rules), set(caps)
    for missing in sorted(expected - actual_keys):
        problems.append(f"[棘轮基线] caps 缺 {missing!r} —— 少一条上限就等于"
                        f"该类**无限放行**（确已清零请显式写 0，不要删键）")
    for extra in sorted(actual_keys - expected):
        problems.append(f"[棘轮基线] caps 多出 {extra!r} —— 上限表与 lint_rules."
                        f"report_only 不同步（死数据/拼写漂移）")
    if today > review_by:
        problems.append(f"[棘轮基线] review_by={review_by} 已过期（今天 {today}）→ "
                        f"必须重新测量并重评基线（按实测下调 caps、更新 measured_at / "
                        f"review_by），不得静默延期")
    for code in sorted(expected & actual_keys):
        count, cap = int(counts.get(code, 0)), int(caps[code])
        if count > cap:
            problems.append(f"[棘轮/{code}] 实测 {count} > 上限 {cap}"
                            f"（超出 {count - cap} 条）—— cap 只许在重评基线时下调，"
                            f"不许为变绿上调；新违规请直接修掉")
    return problems


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

# 棘轮反向对照的临时副本：干净版**不触发任何 C 级规则**（公开函数有 docstring、
# 行长 < 88）。
CLEAN_COPY_FIXTURE = '''"""反向对照用干净副本（不触发 D101/D102/D103/E501）。"""


def public_function():
    """有 docstring 的公开函数（不触发 D103），且每行都短于行宽上限。"""
    return 1
'''

# 注入样本：① 缺 docstring 的公开函数 → D103；② 一行超长物理行 → E501。
# 超长行用 `"x" * 100` **在运行时拼出**，否则这一行源码自己就会变成 E501
# （把 fixture 自己变成违规——反向对照最容易骗到自己的地方）。
INJECTED_VIOLATION_FIXTURE = (
    "\n\ndef injected_public_function():\n    return 2\n\n\n"
    'INJECTED_LONG_LINE = "' + "x" * 100 + '"\n'
)

# **自检哨兵日期**（不是政策）：④⑤⑦⑧ 只考"计数比较"这一层，用固定未过期日期，
# 免得政策一过期就把这几条自检顶成 AssertionError（真正的到期判定走 C_REVIEW_BY 与 ⑥）。
SELFTEST_VALID_UNTIL = "9999-12-31"


def ratchet_selfcheck(binary: list[str], today: str) -> None:
    """棘轮的五条反向对照（**真实 ruff + 临时副本**，`%TEMP%` 内，不写进仓库）。

    "cap 咬得住"这句话必须可执行：先量干净副本 → 以**实测值**为上限 →
    注入 1 处新违规 → 同一上限下必须 FAIL。另三条守的是棘轮基线自身
    （过期/缺键/多键）。样本目录随 `TemporaryDirectory` 退出即删。

    ④⑤⑦⑧ 用 `SELFTEST_VALID_UNTIL`（**自检哨兵日期**，不是政策；政策到期日走
    `C_REVIEW_BY` 与 ⑥），否则政策一过期，"计数比较"这几条自检会被过期错误顶掉，
    看不到真正的失败原因（实测：过期政策下首版 ④ 直接 AssertionError）。
    """
    with tempfile.TemporaryDirectory(prefix="verify_lint_rc_") as td:
        copy = Path(td) / "pkg"
        copy.mkdir()
        # ⚠️ 局部名不要叫 `probe`：本文件 `ruff_cmd()` 里已有一个同名变量（值为
        # `subprocess.run(...)`），而 `verify_artifact_paths.py` 的分解器是**按名字**
        # 收集全文件赋值（同名多处且不一致 → 判"动态目标"）。实测：叫 `probe` 会被判
        # 2 处动态写盘目标（本卡落地时过一次红），改名即消失。
        sample_file = copy / "clean_copy.py"
        sample_file.write_text(CLEAN_COPY_FIXTURE, encoding="utf-8")
        _, found_clean = run_ruff(binary, REPORT_ONLY, [str(copy)])
        clean_counts = codes_of(found_clean)
        caps = {code: int(clean_counts.get(code, 0)) for code in C_RULES}
        ok("自检 ④ 干净副本 + 实测上限 → 棘轮零 problem（等价 rc=0，防假红）",
           ratchet_problems(clean_counts, caps, SELFTEST_VALID_UNTIL, today) == [],
           f"counts={clean_counts} caps={caps}")

        sample_file.write_text(CLEAN_COPY_FIXTURE + INJECTED_VIOLATION_FIXTURE,
                               encoding="utf-8")
        _, found_bad = run_ruff(binary, REPORT_ONLY, [str(copy)])
        injected_counts = codes_of(found_bad)
        problems = ratchet_problems(injected_counts, caps, SELFTEST_VALID_UNTIL, today)
        hit = [code for code in ("D103", "E501")
               if any(f"[棘轮/{code}]" in p for p in problems)]
        ok("反向对照 ⑤ 临时副本注入 1 处缺 docstring 公开函数 + 1 行超长行 → "
           "cap 顶破即 FAIL 并点名 D103/E501",
           hit == ["D103", "E501"],
           f"counts={injected_counts} caps={caps} 点名={hit} "
           f"首条={problems[0] if problems else '-'}")

    expired = ratchet_problems(clean_counts, caps, "2020-01-01", today)
    ok("反向对照 ⑥ review_by 设为过去 → FAIL 且点名『已过期』（必须重评基线）",
       any("已过期" in p for p in expired), f"problems={expired[:1]}")
    missing = ratchet_problems(clean_counts,
                               {k: v for k, v in caps.items() if k != "D103"},
                               SELFTEST_VALID_UNTIL, today)
    ok("反向对照 ⑦ caps 少一类（漏 D103）→ FAIL（少一条上限 = 该类无限放行）",
       any("caps 缺" in p for p in missing), f"problems={missing[:1]}")
    typo = ratchet_problems(clean_counts, {**caps, "E5001": 0},
                            SELFTEST_VALID_UNTIL, today)
    ok("反向对照 ⑧ caps 多出拼错的键（E5001）→ FAIL（上限表与规则集不同步）",
       any("caps 多出" in p for p in typo), f"problems={typo[:1]}")


def main() -> int:
    binary = ruff_cmd()
    if binary is None:
        if "--allow-missing" in sys.argv:
            print("SKIP: 未找到 ruff（--allow-missing 显式放行）；原因：环境未安装或不在 PATH")
            print("\nALL PASS (0 assertions, skipped)")
            return 0
        print("LINT-ERROR: 未找到 ruff —— fail-closed（安装：pip install "
              "-r requirements-windows.txt；确需跳过用 --allow-missing）")
        return 2

    ver = subprocess.run([*binary, "--version"], capture_output=True,
                         text=True).stdout.strip()
    print(f"[tool] {ver}")

    paths = DEFAULT_PATHS
    if "--paths" in sys.argv:
        paths = sys.argv[sys.argv.index("--paths") + 1:]
    today = datetime.now(PROJECT_TZ).strftime("%Y-%m-%d")

    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad_fixture.py"
        good = Path(td) / "good_fixture.py"
        bad.write_text(BAD_FIXTURE, encoding="utf-8")
        good.write_text(GOOD_FIXTURE, encoding="utf-8")

        rc_bad_a, found_bad_a = run_ruff(binary, HARD_A, [str(bad)])
        ok("自检 ① 坏文件在 A 级（E9/F63/F7/F82）判 FAIL",
           rc_bad_a != 0 and "F821" in codes_of(found_bad_a),
           f"rc={rc_bad_a} codes={codes_of(found_bad_a)}")
        rc_bad_b, found_bad_b = run_ruff(binary, HARD_B, [str(bad)])
        ok("自检 ② 坏文件在 B 级（未用导入）判 FAIL",
           rc_bad_b != 0 and "F401" in codes_of(found_bad_b),
           f"rc={rc_bad_b} codes={codes_of(found_bad_b)}")
        rc_good, found_good = run_ruff(binary, f"{HARD_A},{HARD_B}", [str(good)])
        ok("自检 ③ 好文件在 A+B 级判 PASS（防假红）",
           rc_good == 0 and not found_good,
           f"rc={rc_good} codes={codes_of(found_good)}")

    ratchet_selfcheck(binary, today)

    rc_a, found_a = run_ruff(binary, HARD_A, paths)
    ok(f"A 级硬闸门（{HARD_A}）全仓为 0", rc_a == 0 and not found_a,
       f"paths={paths} findings={len(found_a)} {summarize(found_a)}")

    rc_b, found_b = run_ruff(binary, HARD_B, paths)
    ok(f"B 级硬闸门（{HARD_B}）全仓为 0", rc_b == 0 and not found_b,
       f"findings={len(found_b)} {summarize(found_b)}")

    rc_c, found_c = run_ruff(binary, REPORT_ONLY, paths)
    counts_c = codes_of(found_c)
    ratchet_line = " ".join(f"{code}={counts_c.get(code, 0)}/{C_CAPS.get(code, '?')}"
                            for code in C_RULES)
    print(f"[report-only C 级] {REPORT_ONLY} → {sum(counts_c.values())} 条 {counts_c}"
          f"（棘轮 caps：{ratchet_line}；实测日 {C_MEASURED_AT}，**只许下调**；"
          f"review_by {C_REVIEW_BY}，今日 {today}）")
    ok("C 级计数被真实采集（>0 条；若归零说明规则选择或工具行为变了，需复核）",
       sum(counts_c.values()) > 0, f"counts={counts_c}")

    ratchet = ratchet_problems(counts_c, C_CAPS, C_REVIEW_BY, today)
    if ratchet:
        print(f"\nLINT FAIL（C 级可读性棘轮，{len(ratchet)} 项）：")
        for item in ratchet:
            print(f"  - {item}")
        print("  修法：① 棘轮只放行**历史既存债**——新违规请直接修掉"
              "（缺 docstring 补一行、长行折行）；② 确需重评基线时按**当次实测**"
              "下调 policy.json::lint_readability_ratchet.caps（不许上调）；"
              "③ 到期后更新 review_by（不得静默延期）。")
        return 1

    print(f"\nALL PASS ({PASSED} assertions)")
    print(f"EVIDENCE: verify_lint.py assertions={PASSED} rc=0 c_ratchet={ratchet_line}")
    return 0


if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句，不能是 assert
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")


if __name__ == "__main__":
    raise SystemExit(main())
