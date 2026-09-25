"""§2.1.1（用户 2026-09-25 采纳 v0）：**未闭环 critical/major 扣率**的数据闸门（offline）。

为什么单开一个闸门而不是把断言塞进别处：扣率是**一条独立的政策**（比例表 / 同根因合并
开关 / 封顶 / 取整步长 / "未闭环"四判据），真源 = `agents/policy.json::deduction_rates`。
`TG-15` 的教训是"政策散在多处就一定会分叉"，因此每个政策键都配一个守门闸门
（`ledger_measurement` → `verify_ledger_measurement.py`；`artifact_paths` →
`verify_artifact_paths.py`；`deduction_rates` → 本文件）。结算脚本**不建**
（§2.1.1：首次实际使用时再加），所以本闸门守的是**口径本身**：
读取器 fail-closed + 纯函数 `deduction_for()` 的两个方向。

**本文件里不得出现任何比例数值**（critical/major 的百分比、取整步长…）：期望值一律由
政策数据算出（`2.5 − 2.5 × ratios[major]`），否则闸门自己就成了"第二份政策"——
那正是 `verify_no_policy_hardcode.py` 要抓的形态，而闸门不该等它来抓。

**不写任何文件**：读取器的反例用 `dataclasses.replace(policy, policy_file=变异字典)`
在内存里构造（比写探针文件更强：测的就是读取器本身），因此本闸门没有动态写盘目标
（`verify_artifact_paths.py` 的动态目标棘轮要求新脚本落点可静态判定）。

反向对照（两组，缺一不可）：
  * **fail-closed 组**：缺键 / 比例超界 / 负值 / 字符串 / 布尔 / 全 0 / 步长非法 /
    判据缺证据 / 判据 id 重复 / 没有任何一条 `requires_due_date` / 折算级别越界 /
    折算条数非正 → 一律 `PolicyError`；
  * **数据驱动组**：改政策里的比例 → 同一输入的结果**随之改变**；关掉合并开关 →
    同根因不再合并；显式传 `rates` 时不读任何文件。

用法：
    .venv\\Scripts\\python.exe verify\\verify_deduction_rates.py           # 自检（默认）
    .venv\\Scripts\\python.exe verify\\verify_deduction_rates.py --show    # 打印当前口径
"""
from __future__ import annotations
VERIFY_META = {'features': '§2.1.1 扣率数据闸门：deduction_rates 读取器 fail-closed（缺键/超界/负值/全0/步长非法/判据缺证据/无到期日约束/折算级别越界）+ 纯函数 deduction_for 正反例（合并开关与比例均来自数据、封顶优先于取整）', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 5, 'routes': [], 'requires': ['none']}

import copy
import dataclasses
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from verify.agent_policy import (  # noqa: E402
    ENV_POLICY,
    Policy,
    PolicyError,
    deduction_for,
    load_policy,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    """断言 + 计数（与本仓其它闸门同形：`ALL PASS (N assertions)` 的 N 由它累加）。"""
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def _with_policy(base: Policy, mutate) -> Policy:
    """把 `mutate(policy_dict)` 的结果装回一个 `Policy`（**内存里**，不落盘）。

    为什么不用"写一份探针政策文件再 `load_policy`"：那会引入一个**动态写盘目标**
    （被 `verify_artifact_paths.py` 判 FAIL），而且测的是"文件→政策"这一段；
    这里要测的是**读取器本身**，直接构造 `Policy` 才是最小驱动面。
    """
    data = copy.deepcopy(base.policy_file)
    mutate(data)
    return dataclasses.replace(base, policy_file=data)


def _expect_error(label: str, mutate, base: Policy) -> None:
    """断言"读取该键"时 fail-closed（`PolicyError`）。

    拼错/坏值/缺键一律拒——不静默取默认值。理由是这条路正是 `TG-15` 的起点：
    静默回落常量让"关掉一条闸门"不需要改代码（见 `agent_policy` 模块头）。
    """
    try:
        got = _with_policy(base, mutate).deduction_rates  # noqa: B018
        ok(f"fail-closed：{label} → PolicyError", False, f"未抛错，读到 {str(got)[:60]}")
    except PolicyError as exc:
        ok(f"fail-closed：{label} → PolicyError（不静默取默认值）", True, str(exc)[:80])


def _set(data: dict, key: str, value) -> None:
    """把 `data["deduction_rates"][key]` 改成 `value`（反例表用，避免长 lambda）。"""
    data["deduction_rates"][key] = value


def _ratios_of(data: dict) -> dict:
    return data["deduction_rates"]["ratios"]


def selfcheck() -> int:
    """自检：读取器 fail-closed 组 + `deduction_for()` 正反例 + 数据驱动组（见模块头）。"""
    policy = load_policy()
    rates = policy.deduction_rates

    ok("数据源完备：政策无死键/无未声明 spec（`deduction_rates` 已登记 consumed）",
       policy.closure_problems() == [], f"problems={policy.closure_problems()[:2]}")

    ratios = {str(k): float(v) for k, v in rates["ratios"].items()}
    ok("读取器给出比例表：每条 ∈[0,1] 且**至少一项 >0**（全 0 = 规则恒不扣分）",
       bool(ratios) and all(0.0 <= v <= 1.0 for v in ratios.values())
       and any(v > 0 for v in ratios.values()),
       f"ratios={ratios}")
    ok("合并开关 / 封顶 / 取整步长都是显式数据（布尔 + (0,1] 内的数）",
       isinstance(rates["merge_same_root_cause"], bool)
       and isinstance(rates["cap_at_card_points"], bool)
       and 0.0 < float(rates["rounding_step"]) <= 1.0,
       f"merge={rates['merge_same_root_cause']} "
       f"cap={rates['cap_at_card_points']} step={rates['rounding_step']}")
    criteria = rates["unclosed_criteria"]
    due = [c for c in criteria if c.get("requires_due_date") is True]
    ok("『未闭环』判据**逐条**带 id/证据形态，且至少一条声明 requires_due_date"
       "（否则第 ④ 条退化成『说一句延期就算闭环』）",
       bool(criteria) and all(str(c.get("id") or "").strip()
                              and str(c.get("evidence") or "").strip()
                              and c.get("evidence_kinds") for c in criteria) and bool(due),
       f"{len(criteria)} 条判据：{[c['id'] for c in criteria]}；"
       f"带到期日约束的 = {[c['id'] for c in due]}")

    # ------------------------------------------------------------ fail-closed 组
    for label, mutate in (
        ("缺 deduction_rates 键", lambda d: d.pop("deduction_rates")),
        ("比例超界（1.5）", lambda d: _ratios_of(d).__setitem__("critical", 1.5)),
        ("比例为负（-0.1）", lambda d: _ratios_of(d).__setitem__("major", -0.1)),
        ("比例写成字符串", lambda d: _ratios_of(d).__setitem__("critical", "50%")),
        ("比例写成布尔", lambda d: _ratios_of(d).__setitem__("major", True)),
        ("比例表全部为 0（规则恒不扣分）",
         lambda d: _set(d, "ratios", {k: 0 for k in _ratios_of(d)})),
        ("取整步长 = 0", lambda d: _set(d, "rounding_step", 0)),
        ("取整步长 > 1（与账本精度口径不符）", lambda d: _set(d, "rounding_step", 5)),
        ("判据列表为空", lambda d: _set(d, "unclosed_criteria", [])),
        ("判据缺 evidence（只剩标题）",
         lambda d: d["deduction_rates"]["unclosed_criteria"][0].pop("evidence")),
        ("判据 id 重复（判据集合不可枚举）",
         lambda d: d["deduction_rates"]["unclosed_criteria"][1].__setitem__(
             "id", d["deduction_rates"]["unclosed_criteria"][0]["id"])),
        ("没有任何判据声明 requires_due_date（第 ④ 条被静默放宽）",
         lambda d: [c.__setitem__("requires_due_date", False)
                    for c in d["deduction_rates"]["unclosed_criteria"]]),
        ("棘轮折算级别不在比例表内（取值无处可取）",
         lambda d: _set(d, "ratchet_item_folding",
                        {"unclosed_folds_to_level": "no-such", "count": 1})),
        ("棘轮折算条数非正整数",
         lambda d: d["deduction_rates"]["ratchet_item_folding"].__setitem__("count", 0)),
    ):
        _expect_error(label, mutate, policy)

    # -------------------------------------------------- 纯函数：口径正例（期望值由政策算）
    r_crit, r_major = ratios["critical"], ratios["major"]
    card = 2.5

    res = deduction_for(card, [], rates=rates)
    ok(f"{card} 点 + 0 条未闭环 → 不扣（剩余 {res.points:g}）",
       res.points == card and res.deduction == 0.0 and res.ratio == 0.0,
       f"points={res.points:g}")

    res = deduction_for(card, ["major"], rates=rates)
    want = round(card - card * r_major, 10)
    ok(f"{card} 点 + 1 条 major 未闭环 → 剩余 {res.points:g}"
       f"（= {card} − {card}×{r_major:g} = {want:g}；期望值由政策算出、"
       f"**不写死在闸门里**）",
       res.points == want and res.deduction == round(card * r_major, 10),
       f"points={res.points:g} deduction={res.deduction:g}")

    res = deduction_for(card, ["critical"], rates=rates)
    want = round(card - card * r_crit, 10)
    ok(f"{card} 点 + 1 条 critical 未闭环 → 剩余 {res.points:g}"
       f"（= {card} − {card}×{r_crit:g} = {want:g}）",
       res.points == want and res.deduction == round(card * r_crit, 10),
       f"points={res.points:g} deduction={res.deduction:g}")

    res = deduction_for(card, ["critical", "major", "major"],
                        root_causes=["root-A", "root-A", "root-A"], rates=rates)
    unmerged = round(card - card * (r_crit + 2 * r_major), 10)
    ok(f"{card} 点 + 同根因 1 critical + 2 major → **合并计一次**"
       f"（取最高级别 critical，剩余 {res.points:g}；不合并会是 {unmerged:g}）",
       res.ratio == r_crit and res.points == round(card - card * r_crit, 10)
       and res.counted_levels == ("critical",),
       f"ratio={res.ratio:g} counted={res.counted_levels}")

    res = deduction_for(card, ["critical"] * 3, root_causes=["a", "b", "c"],
                        rates=rates)
    ok(f"{card} 点 + 3 条**不同根因** critical → 封顶（剩余 {res.points:g}，"
       f"扣分 {res.deduction:g} = 卡点数；3×{r_crit:g} > 100% ⇒ 封顶生效）",
       res.capped and res.points == 0.0 and res.deduction == card,
       f"points={res.points:g} ratio={res.ratio:g} capped={res.capped}")

    res = deduction_for(1, ["major"], rates=rates)
    tag = "（不等于归零；固定值口径的对照）" if res.points == 0.8 else ""
    ok(f"1 点小卡 + 1 条 major 未闭环 → 剩余 {res.points:g}{tag}",
       res.points == round(1 - 1 * r_major, 10), f"points={res.points:g}")

    step = float(rates["rounding_step"])
    res = deduction_for(1.3, ["major"], rates=rates)
    ok(f"取整：1.3 点 × {r_major:g} = {1.3 * r_major:g} → 落在 {step:g} 网格上"
       f"（扣 {res.deduction:g}，剩余 {res.points:g}）",
       math.isclose(res.deduction / step, round(res.deduction / step), abs_tol=1e-9),
       f"deduction={res.deduction:g} step={step:g}")

    res = deduction_for(0.98, ["critical"] * 3, root_causes=["a", "b", "c"],
                        rates=rates)
    ok("封顶优先于取整：0.98 点（不在取整网格上）被 3×critical 打满 →"
       "扣分不四舍五入到 1.00、剩余点数**不为负**（不倒扣）",
       res.deduction <= 0.98 and res.points >= 0.0 and res.capped,
       f"deduction={res.deduction:g} points={res.points:g}")

    # ------------------------------------------------------- 纯函数：fail-closed
    for label, kwargs in (
        ("级别名拼错（majro）", dict(levels=["majro"])),
        ("级别名自造（blocker）", dict(levels=["blocker"])),
    ):
        try:
            deduction_for(card, rates=rates, **kwargs)
            ok(f"fail-closed：{label} → PolicyError", False, "未抛错（静默按 0 计）")
        except PolicyError as exc:
            ok(f"fail-closed：{label} → PolicyError（不静默按 0 计）", True, str(exc)[:80])
    try:
        deduction_for(card, ["major", "major"], root_causes=["only-one"], rates=rates)
        ok("fail-closed：root_causes 与 levels 不等长 → PolicyError", False, "未抛错")
    except PolicyError as exc:
        ok("fail-closed：root_causes 与 levels 不等长 → PolicyError"
           "（静默截断会悄悄改变扣分）", True, str(exc)[:80])
    try:
        deduction_for(-1, ["major"], rates=rates)
        ok("fail-closed：卡点数为负 → PolicyError", False, "未抛错")
    except PolicyError as exc:
        ok("fail-closed：卡点数为负 → PolicyError", True, str(exc)[:80])

    # ------------------------------- 数据驱动组（口径确实来自数据文件，不是代码常量）
    hot = copy.deepcopy(rates)
    hot["ratios"]["major"] = min(1.0, r_major + 0.1)
    moved = deduction_for(card, ["major"], rates=hot)
    ok("反向对照（数据驱动）：改掉政策里的 major 比例 → 同一输入的结果**随之改变**"
       "（比例不是代码常量）",
       moved.points != deduction_for(card, ["major"], rates=rates).points,
       f"{r_major:g} → {hot['ratios']['major']:g}：points "
       f"{deduction_for(card, ['major'], rates=rates).points:g} → {moved.points:g}")

    off = copy.deepcopy(rates)
    off["merge_same_root_cause"] = False
    unmerged = deduction_for(card, ["critical", "major", "major"],
                             root_causes=["root-A", "root-A", "root-A"], rates=off)
    ok("反向对照（数据驱动）：关掉 `merge_same_root_cause` → 同一根因的三条"
       "**不再合并**（开关是数据，不是常量）",
       unmerged.ratio == round(r_crit + 2 * r_major, 10),
       f"ratio={unmerged.ratio:g} counted={unmerged.counted_levels}")

    # 纯度：显式传 rates 时**不读任何文件**（把政策指到不存在的路径也照样能算）
    saved = os.environ.get(ENV_POLICY)
    os.environ[ENV_POLICY] = os.path.join(os.environ.get("TEMP", "."), "absent.json")
    try:
        pure = deduction_for(card, ["major"], rates=rates)
        ok("纯函数对照：显式传 rates 时不碰文件系统（政策路径不存在也能算，"
           "说明结果只由入参决定）",
           pure.points == deduction_for(card, ["major"], rates=rates).points,
           f"points={pure.points:g}")
        try:
            deduction_for(card, ["major"])  # 不传 rates → 必须真去读政策（故此处应失败）
            ok("默认路径对照：不传 rates 时**确实**读取当前政策（缺失 → fail-closed）",
               False, "未抛错：默认路径没有读政策")
        except PolicyError as exc:
            ok("默认路径对照：不传 rates 时**确实**读取当前政策（缺失 → fail-closed）",
               True, str(exc)[:70])
    finally:
        if saved is None:
            os.environ.pop(ENV_POLICY, None)
        else:
            os.environ[ENV_POLICY] = saved

    print(f"\nALL PASS ({PASSED} assertions)")
    print(f"EVIDENCE: verify_deduction_rates.py assertions={PASSED} rc=0 "
          f"ratios={json.dumps(ratios, ensure_ascii=False)} "
          f"merge={rates['merge_same_root_cause']} cap={rates['cap_at_card_points']} "
          f"step={rates['rounding_step']} criteria={[c['id'] for c in criteria]}")
    return 0


def show() -> int:
    """`--show`：打印当前生效的扣率口径（比例表 / 开关 / 判据），供人读现值。"""
    print(json.dumps(load_policy().deduction_rates, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    """入口：默认跑自检；`--show` 只打印当前口径。"""
    if "--show" in sys.argv:
        return show()
    return selfcheck()


if __name__ == "__main__":
    raise SystemExit(main())
