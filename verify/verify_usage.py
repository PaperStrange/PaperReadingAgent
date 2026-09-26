"""Sprint-16 Retro 行动项 ③：token 用量采集与成本换算的离线回归。

覆盖（全部离线、无网络、无付费调用）：
  ① 响应解析：对象形态与 dict 形态的 usage 都能提取（prompt/completion/total）
  ② 累计与增量：snapshot / delta 的数学关系，by_model 明细
  ③ 价表查找：`scraped.<provider>.models.<name>` 命中、`openai/` 前缀归一化、`auto` 兜底
  ④ **缺价模型绝不臆测**：cost_cny=None + unpriced_models 点名 + partial_cost_cny 只算已计价部分
  ⑤ 成本换算：token × 单价 × fx（用价表自身数值做公式断言，价格刷新不会误红）
  ⑥ 回调挂载：`ensure_installed()` 幂等；`prune_litellm_callbacks()` 之后仍挂载（防被裁剪）
  ⑦ 计费键解析：响应名是上游别名（无价）而请求名有价 → 按请求名计费 + `reported_as` 可追溯；
    两者都无价 → 仍 `cost_cny=None`（不臆测）
  ⑧ 边界与白名单：空账 → `cost_cny=None` + `no_data=True`（**不是 0.0**）；快照键 ⊆ 白名单
    （钉死 `/api/usage` 与 `output["usage"]` 的暴露面）；`settle()` 有界等待可用且不挂死
  ⑪ 行 20（TG-20）：**按该次调用自己的时刻选档** —— 夜间不再按高峰计（真函数入口 ＋
    真价表 ＋ **改前实现**（钉住的 revision）逐条对照；含跨档/零长度/时间戳缺失/
    时钟退化、可审计字段闭合、缺价与单档模型不被新逻辑带坏）
  ⑫ 真派发：litellm **真的**把该次调用自己的起止时刻交给回调（`mock_response`，离线）

Run: .venv\\Scripts\\python.exe verify\\verify_usage.py
"""
from __future__ import annotations
VERIFY_META = {
    'features': 'Retro③ 成本换算 ＋ TG-20 行 20 按调用时刻选档：真入口对照/跨档/'
                '缺失/退化/可审计/真派发，改前取自钉住 revision（离线，需 git）',
    'tier': 'offline', 'providers': [], 'est_seconds': 12, 'est_cost_cny': 0,
    'routes': [], 'requires': ['git'],
}

import asyncio
import importlib.util
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "paper-qa-script") not in sys.path:
    sys.path.insert(0, str(ROOT / "paper-qa-script"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import usage as U  # noqa: E402
import litellm  # noqa: E402

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


SH = ZoneInfo("Asia/Shanghai")
MODEL = "openai/deepseek-v4-flash"
# 「改前」实现 = 本卡开工时的 HEAD（父代理指定 `1ed6f93`）。**钉 revision，不钉
# `HEAD`**：本卡提交之后 `git show HEAD:…` 会拿到改后版本 ⇒「夜间减半」的对照自我作废。
BEFORE_REV = "1ed6f937396eb81e7fc6a9e40d87fbdd139fa926"
USAGE_REL = "paper-qa-script/app/usage.py"


def _cst(*parts: int) -> datetime:
    """CST（Asia/Shanghai）时刻——档位用例一律用带时区值，不依赖本机时区。"""
    return datetime(*parts, tzinfo=SH)


def _call(mod, window: tuple, prompt: int = 1000, completion: int = 0) -> tuple:
    """把**同一 usage** 经某版本的**真回调入口** `hook_success` 喂进去，读回读数。

    返回 `(cost_cny, 档位标签列表, tier_assumed_calls)`；改前实现没有档位字段 ⇒ 标签
    是空列表。
    """
    mod.reset()
    mod.hook_success({"model": MODEL}, _Resp("deepseek-flash", prompt, completion),
                     window[0], window[1])
    cost = mod.snapshot()["cost"]
    labels = sorted((cost.get("tier_by_model") or {}).get(MODEL) or {})
    return cost["cost_cny"], labels, int(cost.get("tier_assumed_calls") or 0)


def _load_before():
    """加载**改前**的 `app/usage.py`（钉住的 revision），并把价表钉到仓库那一份。

    钉价表是必须的：从 `%TEMP%` 加载时 `prices_path()` 的 `parents[2]` 指不到仓库，
    会读到空价表 ⇒ 对照退化成"无价 vs 有价"，与选档无关。钉住后两边**只差代码版本**。
    """
    proc = subprocess.run(["git", "-C", str(ROOT), "show", f"{BEFORE_REV}:{USAGE_REL}"],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"git show 失败：{proc.stderr.strip()}"
    assert "_tiers" not in proc.stdout, f"{BEFORE_REV} 里有 `_tiers` ⇒ 钉错 revision"
    probe = Path(tempfile.mkdtemp(prefix="g2l20-before-")) / "usage_before.py"
    probe.write_bytes(proc.stdout.encode("utf-8"))  # write_bytes：不引入 CRLF
    spec = importlib.util.spec_from_file_location("usage_before", probe)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    def _same_prices() -> Path:
        """与 worktree 版读**同一份**真实价表（对照只允许差代码版本）。"""
        return U.prices_path()

    mod.prices_path = _same_prices
    return mod


def _load_agent_ops():
    """加载 `scripts/agent-ops.py`（TG-20 行 16 的参考实现）做口径一致性对照。"""
    spec = importlib.util.spec_from_file_location("agent_ops_ref",
                                                  ROOT / "scripts" / "agent-ops.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    """模拟 litellm ModelResponse（对象形态）。"""

    def __init__(self, model: str, prompt: int, completion: int, total: int | None = None) -> None:
        self.model = model
        self.usage = type("_U", (), {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total if total is not None else prompt + completion})()


def main() -> int:
    U.reset()

    # ① 解析：对象形态 + dict 形态 + **无 usage（不记调用、不抛）**
    #    语义变更（2026-09-21 关闭三查·二查 major，教训 1.61）：旧实现把无 usage 的响应记成"1 次调用 + 0 token"，
    #    对**有价**模型会产出 `cost_cny=0.0` + `no_data=False` → 被判 measured 并自动回填 0 成本。
    #    现口径：无 usage = 无数据（保持空账，由上游判 None + no_data=True）。
    U.record_response(_Resp("openai/deepseek-v4-flash", 1000, 200))
    U.record_response({"model": "openai/deepseek-v4-flash", "usage": {"prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600}})
    U.record_response(object())  # 无 usage 字段 → 不记
    s1 = U.snapshot()
    ok("① 有 usage 的两种形态都被累计、无 usage 的不计入（calls=2）", s1["calls"] == 2, f"calls={s1['calls']}")
    ok("① token 汇总正确（prompt=1500 completion=300 total=1800）",
       (s1["prompt_tokens"], s1["completion_tokens"], s1["total_tokens"]) == (1500, 300, 1800),
       f"{s1['prompt_tokens']}/{s1['completion_tokens']}/{s1['total_tokens']}")
    ok("① by_model 只含真实模型（无 usage 的响应不再产出 'unknown' 0-token 桶）",
       s1["by_model"].get("openai/deepseek-v4-flash", {}).get("calls") == 2 and "unknown" not in s1["by_model"],
       str(list(s1["by_model"])))

    # ② 增量：再记一笔后 delta 只含新增
    before = U.snapshot()
    U.record_response(_Resp("openai/deepseek-v4-flash", 100, 50))
    d = U.delta(before)
    ok("② delta 只含新增（calls=1, prompt=100）", d["calls"] == 1 and d["prompt_tokens"] == 100, f"{d['calls']}/{d['prompt_tokens']}")
    ok("② delta 带累计视图（cumulative.calls=3，无 usage 的那次不计入）", d["cumulative"]["calls"] == 3, str(d["cumulative"]))
    ok("② delta.by_model 只含增量模型", list(d["by_model"]) == ["openai/deepseek-v4-flash"], str(list(d["by_model"])))

    # ③ 价表查找：前缀归一化 + scraped + auto 兜底
    p_deepseek = U.price_for("openai/deepseek-v4-flash")
    ok("③ `openai/` 前缀归一化后命中 scraped.deepseek 价目", bool(p_deepseek) and "input_cost_per_token" in p_deepseek,
       str(p_deepseek))
    p_auto = U.price_for("gpt-4o-mini")
    ok("③ auto 段兜底命中（gpt-4o-mini）", bool(p_auto) and "input_cost_per_token" in p_auto, str(p_auto))

    # ④ 缺价模型：绝不臆测
    missing = U.cost_cny({"definitely-not-a-real-model": {"prompt_tokens": 10, "completion_tokens": 10}})
    ok("④ 缺价 → cost_cny=None（不臆测）", missing["cost_cny"] is None, str(missing))
    ok("④ 缺价模型被点名", missing["unpriced_models"] == ["definitely-not-a-real-model"], str(missing["unpriced_models"]))
    ok("④ 缺价时 partial_cost_cny=0（无已计价部分）", missing["partial_cost_cny"] == 0, str(missing["partial_cost_cny"]))

    # ⑤ 换算式：用价表自身数值验证 token × 单价 × fx（价格刷新不会误红）
    fx = U.fx_usd_cny()
    price = U.price_for("openai/deepseek-v4-flash") or {}
    tokens = {"openai/deepseek-v4-flash": {"prompt_tokens": 1_000_000, "completion_tokens": 0}}
    expect = round(1_000_000 * float(price["input_cost_per_token"]) * fx, 6)
    got = U.cost_cny(tokens)
    ok("⑤ 成本换算 = token × 单价 × fx", got["cost_cny"] == expect, f"got={got['cost_cny']} expect={expect} fx={fx}")
    ok("⑤ 有价时 partial 与 cost 一致", got["partial_cost_cny"] == got["cost_cny"], str(got))
    ok("⑤ fx 取自价表 meta 且为正", fx > 0, f"fx={fx}")

    # ⑦ 计费键解析（2026-09-20 实测暴露）：litellm 响应的模型名常是上游别名（无价），
    #    请求名才有价 → 按请求名计费，原始回报名留在 reported_as 供追溯；两者都无价则仍不臆测
    U.reset()
    U.record_response(_Resp("deepseek-flash", 100, 10), model_hint="openai/deepseek-v4-flash")
    s7 = U.snapshot()
    entry = s7["by_model"].get("openai/deepseek-v4-flash") or {}
    ok("⑦ 响应名为上游别名时按**请求名**计费（该名字有价）", entry.get("calls") == 1, str(list(s7["by_model"])))
    ok("⑦ 原始回报名记入 reported_as（可追溯）", entry.get("reported_as") == ["deepseek-flash"],
       str(entry.get("reported_as")))
    ok("⑦ 该路径成本可换算（cost_cny 非 None）", s7["cost"]["cost_cny"] is not None, str(s7["cost"]))
    U.reset()
    U.record_response(_Resp("mystery-1", 5, 5), model_hint="mystery-2")
    s7b = U.snapshot()
    ok("⑦b 两个名字都无价 → cost_cny=None 且用回报名点名",
       s7b["cost"]["cost_cny"] is None and s7b["cost"]["unpriced_models"] == ["mystery-1"], str(s7b["cost"]))

    # ⑧ 边界与白名单（复核 round-4 nit/minor）：
    #    ① 快照键必须落在白名单内（钉死 /api/usage 与 output["usage"] 的暴露面，防将来泄密）；
    #    ② **空账 → cost_cny=None + no_data=True**（绝不能是 0.0：否则"回调未落地"会被当成"已测且花费 0"）；
    #    ③ settle(...) 有界等待可用且不挂死。
    U.reset()
    empty = U.snapshot()
    ok("⑧a 空账 cost_cny=None（不是 0.0）且 no_data=True",
       empty["cost"]["cost_cny"] is None and empty["cost"]["no_data"] is True, str(empty["cost"]))
    allowed_top = {"calls", "prompt_tokens", "completion_tokens", "total_tokens", "by_model", "cost"}
    ok("⑧a 快照顶层键 ⊆ 白名单", set(empty) <= allowed_top, str(sorted(set(empty) - allowed_top)))
    allowed_cost = {"cost_cny", "partial_cost_cny", "unpriced_models", "no_data",
                    "fx_usd_cny", "priced_models",
                    "by_tier", "tier_by_model", "tier_assumed_calls"}
    ok("⑧a cost 键 ⊆ 白名单", set(empty["cost"]) <= allowed_cost, str(sorted(set(empty["cost"]) - allowed_cost)))
    U.record_response(_Resp("openai/deepseek-v4-flash", 10, 5))
    snap8 = U.snapshot()
    allowed_entry = {"calls", "prompt_tokens", "completion_tokens", "total_tokens", "reported_as"}
    entry_keys = set()
    for v in snap8["by_model"].values():
        entry_keys |= set(v)
    ok("⑧a by_model 条目键 ⊆ 白名单（不含密钥类字段）", entry_keys <= allowed_entry,
       str(sorted(entry_keys - allowed_entry)))
    # ⑧b settle 有界等待：已记录的调用可见，且耗时不超过上限 + 余量
    t0s = time.monotonic()
    settled = U.settle(quiet_s=0.1, max_s=1.0, poll_s=0.02)
    elapsed = time.monotonic() - t0s
    ok("⑧b settle() 返回快照且包含已记录调用", settled["calls"] == 1, f"calls={settled['calls']}")
    ok("⑧b settle() 有界（未超过 max_s + 余量）", elapsed <= 1.5, f"elapsed={elapsed:.2f}s")

    # ⑨（2026-09-21 关闭三查·二查 major，教训 1.61）：**计数持续增长时也必须受 deadline 约束**。
    # 失效模式：旧实现在"计数变化"分支 `continue`，跳过 `t >= deadline` 判定 → max_s 形同虚设，
    # 复核实测注入持续流量后 >115s 未返回，而 `/api/run_step` 每步都调用它 → 请求路径可挂死。
    import threading as _th

    U.reset()
    stop = _th.Event()

    def _churn() -> None:
        while not stop.is_set():
            U.record_response({"model": "openai/deepseek-v4-flash",
                               "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
            time.sleep(0.005)

    churn = _th.Thread(target=_churn, daemon=True)
    churn.start()
    box: dict = {}

    def _call_settle() -> None:
        box["snap"] = U.settle(quiet_s=0.05, max_s=0.3, poll_s=0.02)

    # 断言自身必须**有界**（否则未修复实现会让回归脚本一起挂死——本断言的反向对照正是这样暴露的：
    # 首次运行 180s 超时未返回）。故把 settle 放进工作线程，join 超时即判 FAIL。
    t0c = time.monotonic()
    worker = _th.Thread(target=_call_settle, daemon=True)
    worker.start()
    worker.join(timeout=2.0)
    elapsed_c = time.monotonic() - t0c
    stop.set()
    churn.join(timeout=2.0)
    ok("⑨ settle() 在计数持续增长时仍有界（≤ max_s + 余量，不挂死）",
       not worker.is_alive() and elapsed_c < 1.5 and (box.get("snap") or {}).get("calls", 0) > 0,
       f"alive={worker.is_alive()} elapsed={elapsed_c:.2f}s calls={(box.get('snap') or {}).get('calls')}")

    # ⑩ 无 usage 的响应**不得**被记成"1 次调用 + 花费 0"——那会让 suite 判 measured 并自动回填 0 成本
    #    （正是本模块注释禁止的口径；复核实测旧实现给出 cost_cny=0.0 + no_data=False）。
    class _NoUsage:
        model = "openai/deepseek-v4-flash"

    U.reset()
    U.record_response(_NoUsage())
    s10 = U.snapshot()
    ok("⑩ usage 缺失的响应 → 不记调用、cost_cny=None + no_data=True（不得伪造 0 花费）",
       int(s10["calls"]) == 0 and s10["cost"]["cost_cny"] is None and s10["cost"]["no_data"] is True,
       f"calls={s10['calls']} cost={s10['cost']['cost_cny']} no_data={s10['cost']['no_data']}")

    # ⑪ 行 20（TG-20）：**按该次调用自己的时刻选档** —— 夜间不再按高峰计。
    #    真源 = docs/iteration/phases/agents-infra/2026-09-26-price-tier-spec.MD §3；
    #    参考实现 = scripts/agent-ops.py 的 is_peak_at / peak_frac_for（TG-20 行 16）。
    #    每条都**先断言前置条件确实发生**（机制案例 26）：前置不成立 ⇒ FAIL 且不作数。
    win = U.peak_windows()
    ok("⑪0 前置①：选档窗口来自**价表**（不是代码写死）；时区 Asia/Shanghai、两条窗口",
       bool(win) and win[1] == "Asia/Shanghai" and len(win[0]) == 2, f"windows={win}")
    tiers = (U.price_for(MODEL) or {}).get("_tiers") or {}
    pk, off = tiers.get("peak") or {}, tiers.get("off_peak") or {}
    fx = U.fx_usd_cny()
    ok("⑪0 前置②：真实价表里该模型确有 `_tiers` 两档，**输入**单价满足 空闲 == 高峰/2",
       bool(pk) and bool(off)
       and float(off.get("input_cost_per_token") or 0) * 2
       == float(pk.get("input_cost_per_token") or 0),
       f"peak_in={pk.get('input_cost_per_token')}"
       f" off_in={off.get('input_cost_per_token')}")
    raw_peak = 1000 * float(pk["input_cost_per_token"]) * fx
    raw_off = 1000 * float(off["input_cost_per_token"]) * fx
    exp_peak, exp_off = round(raw_peak, 6), round(raw_off, 6)

    # ⑪1 档位边界（spec §3.1 表，2026-09-28 周一）：**左闭右开**（09:00 峰、12:00 谷）
    mon = _cst(2026, 9, 28, 9, 0)
    ok("⑪1 前置：夹具时刻确实是 CST 周一（否则边界用例不作数）",
       mon.strftime("%a %H:%M") == "Mon 09:00"
       and mon.utcoffset() == timedelta(hours=8),
       f"{mon.isoformat()} = {mon.strftime('%a %H:%M')}")
    bounds = [("08:59", False), ("09:00", True), ("11:59", True), ("12:00", False),
              ("13:59", False), ("14:00", True), ("17:59", True), ("18:00", False)]
    bound_cases = []
    for hm, want in bounds:
        hh, mm = (int(x) for x in hm.split(":"))
        bound_cases.append((hm, _cst(2026, 9, 28, hh, mm), want))
    bad = [f"{hm}→{U.is_peak_at(at, win[0], win[1])}(应 {want})"
           for hm, at, want in bound_cases
           if U.is_peak_at(at, win[0], win[1]) is not want]
    ok("⑪1 边界 8 条与 spec §3.1 表逐条一致（左闭右开）", not bad, str(bad))

    # ⑪2 真入口·夜间：同一 usage、同一入口（`hook_success` = litellm 调的那个函数），
    #     只差**代码版本**——改前 = 钉住的 revision，且价表两边钉成同一份
    before = _load_before()
    night = (_cst(2026, 9, 28, 22, 30), _cst(2026, 9, 28, 22, 31))
    old_night, new_night = _call(before, night), _call(U, night)
    ok("⑪2 前置：夜间用例**确实落在空闲窗口内**（落在高峰则本条不作数）",
       U.peak_frac(night[0], night[1], win[0], win[1]) == 0.0
       and U.is_peak_at(night[0], win[0], win[1]) is False
       and night[0].strftime("%a %H:%M") == "Mon 22:30",
       f"{night[0].strftime('%a %H:%M')} CST peak_frac=0.0")
    ok("⑪2 真入口·夜间：同一 usage 改前 = 高峰口径、改后 = 空闲口径（**精确 2.0×**）",
       old_night[0] == exp_peak and new_night[0] == exp_off
       and old_night[0] == 2 * new_night[0] and new_night[1] == ["off_peak"],
       f"改前={old_night[0]} 改后={new_night[0]} 档={new_night[1]}"
       f" assumed={new_night[2]}")
    ok("⑪2 反证：**改前**实现在同一输入下**不**满足上面那条判据（证明它咬得住，不是恒真）",
       old_night[0] != exp_off and old_night[1] != ["off_peak"],
       f"改前={old_night[0]}/{old_night[1]}（判据要求 {exp_off}/['off_peak']）")

    # ⑪3 真入口·高峰对照：反向不得算错（高峰调用改后必须与改前同值）
    peak_w = (_cst(2026, 9, 28, 10, 0), _cst(2026, 9, 28, 10, 1))
    old_peak, new_peak = _call(before, peak_w), _call(U, peak_w)
    ok("⑪3 前置：高峰用例**确实落在高峰窗口内**",
       U.peak_frac(peak_w[0], peak_w[1], win[0], win[1]) == 1.0,
       f"{peak_w[0].strftime('%a %H:%M')} CST peak_frac=1.0")
    ok("⑪3 真入口·高峰对照：改后 == 改前 == 价表高峰值（没有反向算错）",
       new_peak[0] == old_peak[0] == exp_peak and new_peak[1] == ["peak"],
       f"改前={old_peak[0]} 改后={new_peak[0]} 档={new_peak[1]}")

    # ⑪4 跨档：周一 11:00→13:00 CST ＝ 高峰 1h ＋ 空闲 1h ⇒ §3.3 时间加权（同参考实现夹具）
    span = (_cst(2026, 9, 28, 11, 0), _cst(2026, 9, 28, 13, 0))
    ok("⑪4 前置：该调用**确实跨越**档位边界（peak_frac=0.5，不是 0 或 1）",
       U.peak_frac(span[0], span[1], win[0], win[1]) == 0.5, "peak_frac=0.5")
    mix = _call(U, span)
    ok("⑪4 跨档按时间加权（0.5×高峰 ＋ 0.5×空闲，逐位可复算）",
       mix[1] == ["mixed"] and mix[0] == round((raw_peak + raw_off) / 2, 6),
       f"档={mix[1]} 金额={mix[0]} 期望={round((raw_peak + raw_off) / 2, 6)}")

    # ⑪5~⑪8 "拿不到真时刻"的四种形态（§3.2）：一律**按高峰计**并打 `tier_assumed`；
    #        只有"零长度"例外（§8.4 裁定 1：起点是真实观测 ⇒ 按那一刻判档）
    two_none = _call(U, (None, None))
    ok("⑪5 两端都缺时间戳 ⇒ 高峰 ＋ tier_assumed（不得静默挑便宜的档）",
       two_none[0] == exp_peak and two_none[1] == ["peak"] and two_none[2] == 1,
       f"金额={two_none[0]} 档={two_none[1]} assumed={two_none[2]}")
    one_none = _call(U, (_cst(2026, 9, 28, 22, 30), None))
    ok("⑪6 只缺一端 ⇒ 同样高峰 ＋ tier_assumed（§3.2 的“任一端”）",
       one_none[0] == exp_peak and one_none[1] == ["peak"] and one_none[2] == 1,
       f"金额={one_none[0]} 档={one_none[1]} assumed={one_none[2]}")
    zero = _cst(2026, 9, 28, 22, 30)
    ok("⑪7 前置：零长度用例 end == start 且落在**空闲**窗口内",
       U.peak_frac(zero, zero, win[0], win[1]) == 0.0,
       f"{zero.strftime('%a %H:%M')} CST")
    zero_got = _call(U, (zero, zero))
    ok("⑪7 零长度调用按**起点那一刻**判档：空闲、**不**打 tier_assumed（§8.4 裁定 1）",
       zero_got[0] == exp_off and zero_got[1] == ["off_peak"] and zero_got[2] == 0,
       f"金额={zero_got[0]} 档={zero_got[1]} assumed={zero_got[2]}")
    back = _call(U, (_cst(2026, 9, 28, 10, 1), _cst(2026, 9, 28, 10, 0)))
    ok("⑪8 时钟退化（end < start）⇒ 高峰 ＋ tier_assumed",
       back[0] == exp_peak and back[1] == ["peak"] and back[2] == 1,
       f"金额={back[0]} 档={back[1]} assumed={back[2]}")

    # ⑪9 可审计：档位结论与金额都要能被读者复算（夜间一笔 ＋ 高峰一笔）
    U.reset()
    U.hook_success({"model": MODEL}, _Resp("deepseek-flash", 1000, 0), *night)
    U.hook_success({"model": MODEL}, _Resp("deepseek-flash", 1000, 0), *peak_w)
    snap9 = U.snapshot()
    cost9 = snap9["cost"]
    by_tier = cost9.get("by_tier") or {}
    usd_sum = round(sum(float(v["usd"]) for v in by_tier.values()), 12)
    tok_sum = sum(int(v["prompt_tokens"]) + int(v["completion_tokens"])
                  for v in by_tier.values())
    ok("⑪9 可审计①：`by_tier` 逐档给出实测 token，Σtoken == by_model 的实测总量",
       sorted(by_tier) == ["off_peak", "peak"]
       and tok_sum == int(snap9["prompt_tokens"]) + int(snap9["completion_tokens"]),
       f"tiers={sorted(by_tier)} Σtoken={tok_sum}")
    ok("⑪9 可审计②：Σ`by_tier.usd` × fx == partial_cost_cny（金额闭合、可复算）",
       round(usd_sum * fx, 6) == cost9["partial_cost_cny"]
       == round(raw_peak + raw_off, 6),
       f"Σusd={usd_sum}×{fx}={round(usd_sum * fx, 6)} vs {cost9['partial_cost_cny']}")
    ok("⑪9 可审计③：逐模型 × 档位明细回答“哪个模型用了哪一档”",
       sorted(cost9["tier_by_model"].get(MODEL) or {}) == ["off_peak", "peak"]
       and cost9["tier_assumed_calls"] == 0,
       str(sorted(cost9["tier_by_model"])))
    # ⑪10 增量窗口：step 输出走 `delta()`（`orchestration.py:522`），窗口内也要带档位
    before10 = U.snapshot()
    U.hook_success({"model": MODEL}, _Resp("deepseek-flash", 1000, 0), *night)
    d10 = U.delta(before10)
    ok("⑪10 `delta()` 的窗口成本同样带档位增量（只含本窗，不重复计上一窗）",
       sorted(d10["cost"]["by_tier"]) == ["off_peak"]
       and d10["cost"]["cost_cny"] == exp_off, str(d10["cost"]["by_tier"]))

    # ⑪11~⑪12 新逻辑不得把既有口径带坏：缺价仍不臆测；单档模型不假装分过档
    U.reset()
    U.hook_success({"model": "mystery-x"}, _Resp("mystery-x", 10, 0), *night)
    c11 = U.snapshot()["cost"]
    det11 = (c11.get("tier_by_model") or {}).get("mystery-x") or {}
    ok("⑪11 缺价模型：仍如实记档位但 `usd=None`、`cost_cny=None` ＋ 点名（不臆测单价）",
       c11["cost_cny"] is None and c11["unpriced_models"] == ["mystery-x"]
       and (det11.get("flat") or {}).get("usd") is None, str(c11["tier_by_model"]))
    flat_price = U.price_for("gpt-4o-mini") or {}
    U.reset()
    U.hook_success({"model": "gpt-4o-mini"}, _Resp("gpt-4o-mini", 1000, 0), *night)
    c12 = U.snapshot()["cost"]
    det12 = (c12.get("tier_by_model") or {}).get("gpt-4o-mini") or {}
    flat_raw = round(1000 * float(flat_price["input_cost_per_token"]) * fx, 6)
    ok("⑪12 单档模型（价表无 `_tiers`）⇒ 标 `flat`、按扁平键计价、**不**假装分过档",
       sorted(det12) == ["flat"] and c12["tier_assumed_calls"] == 0
       and c12["cost_cny"] == flat_raw,
       f"tiers={sorted(det12)} cost={c12['cost_cny']} 期望={flat_raw}")

    # ⑪13 反证：档位真的由**价表里的窗口数据**决定（不是"夜里就便宜"的巧合）
    all_day = [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "start": "00:00", "end": "23:59"}]
    ok("⑪13 反证①：把窗口换成“周一全天高峰”后，同一次夜间调用改判高峰",
       U.is_peak_at(night[0], all_day, "Asia/Shanghai") is True,
       f"{night[0].strftime('%a %H:%M')} → 高峰")
    broken = [{"days": ["Xx"], "start": "09:00", "end": "12:00"}]
    ok("⑪13 反证②：窗口形状非法 ⇒ fail-closed 判高峰（不许静默变便宜）",
       U.is_peak_at(night[0], broken, "Asia/Shanghai") is True, "")

    # ⑪14 与参考实现（`scripts/agent-ops.py`，行 16）**逐条**对齐：口径不许分叉
    ao = _load_agent_ops()
    names = ("is_peak_at", "peak_frac_for", "peak_windows_from_prices")
    missing = [n for n in names if not hasattr(ao, n)]
    ok("⑪14 前置：参考实现可加载且带这三个口径函数（缺 ⇒ 一致性无法验证，判 FAIL）",
       not missing, str(missing))
    ok("⑪14 窗口来源一致：两边从**同一份**价表读到同一组窗口/时区",
       ao.peak_windows_from_prices(U.load_prices()) == U.peak_windows(),
       str(ao.peak_windows_from_prices(U.load_prices())))
    mism = []
    for hm, at, _ in bound_cases:
        if ao.is_peak_at(at, win[0], win[1]) is not U.is_peak_at(at, win[0], win[1]):
            mism.append(hm)
    ok("⑪14 档位判定 8 个边界两边逐条同值", not mism, str(mism))
    spans = [("2026-09-28T22:30:00+08:00", "2026-09-28T22:31:00+08:00"),
             ("2026-09-28T10:00:00+08:00", "2026-09-28T10:01:00+08:00"),
             ("2026-09-28T11:00:00+08:00", "2026-09-28T13:00:00+08:00"),
             (None, None),
             ("2026-09-28T10:01:00+08:00", "2026-09-28T10:00:00+08:00")]
    frac_mism = []
    for s_iso, e_iso in spans:
        mine = U.peak_frac(s_iso, e_iso, win[0], win[1])
        theirs = ao.peak_frac_for({"started_at": s_iso, "ended_at": e_iso},
                                  win[0], win[1])
        if mine != theirs:
            frac_mism.append(f"{s_iso}→{e_iso}: {mine} vs {theirs}")
    ok("⑪14 高峰占比（含跨档/两端缺失/时钟退化）两边逐条同值", not frac_mism,
       str(frac_mism))
    naive = datetime(2026, 9, 28, 22, 30)
    local_off = datetime.now().astimezone().utcoffset()
    mine_n, theirs_n = U._as_instant(naive), ao._parse_ts(naive.isoformat())
    ok("⑪14 朴素时间戳的解释**刻意不同**且已具名：本模块按本机墙钟（litellm 的 "
       "`datetime.now()`），agent-ops 按 UTC（registry 的 ISO 串）",
       mine_n.utcoffset() == local_off and theirs_n.utcoffset() == timedelta(0)
       and theirs_n - mine_n == local_off,
       f"mine={mine_n.isoformat()} theirs={theirs_n.isoformat()} 本机偏移={local_off}")

    # ⑫ 真派发（可行性的机器根据）：litellm **真的**把该次调用自己的起止时刻交给回调。
    #    用 `mock_response`：离线、不出网、不付费（模块 docstring 记过同法实测）。
    seen: list = []
    real_hook = U.hook_success

    def _recording_hook(kwargs=None, completion_response=None,
                        start_time=None, end_time=None):
        """包住真回调：只记录 litellm 传来的实参，再原样转发（不改行为）。"""
        seen.append((start_time, end_time))
        return real_hook(kwargs, completion_response, start_time, end_time)

    async def _one_call() -> None:
        """跑一次离线 mock 调用，并在**事件循环内**等回调落地（有界 ≤8s）。"""
        await litellm.acompletion(
            model=MODEL, messages=[{"role": "user", "content": "ping"}],
            mock_response="pong", api_key="sk-offline-verify-usage")
        deadline = time.monotonic() + 8.0
        while not seen and time.monotonic() < deadline:
            await asyncio.sleep(0.05)

    U.reset()
    U.hook_success = _recording_hook  # async 回调按**名字**调它 ⇒ 不必动 litellm 的列表
    try:
        U.ensure_installed()
        asyncio.run(_one_call())
    finally:
        U.hook_success = real_hook
        litellm.success_callback = [x for x in
                                    (getattr(litellm, "success_callback", None) or [])
                                    if x is not _recording_hook]
    ok("⑫1 前置：真派发路径**确实**触发了回调（有界等待 ≤8s；未触发则不作数）",
       len(seen) == 1, f"hits={len(seen)}")
    st, en = (seen[0] if seen else (None, None))
    ok("⑫2 litellm 给回调的是**该次调用自己**的起止时刻（朴素本地时间，非读账那一刻）",
       isinstance(st, datetime) and isinstance(en, datetime)
       and st.tzinfo is None and en.tzinfo is None
       and timedelta(0) <= (en - st) <= timedelta(seconds=30)
       and abs((datetime.now() - en).total_seconds()) < 90,
       f"start={st} end={en} now={datetime.now()}")
    want_frac = U.peak_frac(st, en, win[0], win[1])
    want_tier = U.tier_prices(U.price_for(MODEL) or {}, want_frac)[1]
    snap12 = U.snapshot()["cost"]
    by_model12 = snap12.get("tier_by_model") or {}
    rec_models = sorted(by_model12)
    rec_tiers = sorted({lb for labels in by_model12.values() for lb in labels})
    ok("⑫3 记录的档位 == 用**捕获到的时刻**独立算出的档位（两条路径同一结论）",
       len(rec_models) == 1 and rec_tiers == [want_tier]
       and snap12["tier_assumed_calls"] == 0
       and U.price_for(rec_models[0]) == U.price_for(MODEL),
       f"recorded={rec_models}/{rec_tiers} 独立算={want_tier} frac={want_frac}"
       f" CST={U._as_instant(st).astimezone(SH).strftime('%a %H:%M') if st else None}")

    # ⑥ 回调挂载：幂等 + prune 后仍挂载（防被裁剪）
    U.ensure_installed()
    U.ensure_installed()
    sync_hits = [x for x in (getattr(litellm, "success_callback", None) or []) if x is U.hook_success]
    ok("⑥ ensure_installed 幂等（同步回调只挂一次）", len(sync_hits) == 1, f"hits={len(sync_hits)}")
    async_hits = [x for x in (getattr(litellm, "_async_success_callback", None) or []) if x is U.hook_success_async]
    ok("⑥ 异步回调也已挂载（paperqa 走 acompletion）", len(async_hits) == 1, f"hits={len(async_hits)}")

    from app.engine import prune_litellm_callbacks  # noqa: E402

    prune_litellm_callbacks()
    sync_after = [x for x in (getattr(litellm, "success_callback", None) or []) if x is U.hook_success]
    ok("⑥ prune_litellm_callbacks() 之后用量回调仍挂载（抗裁剪）", len(sync_after) == 1, f"hits={len(sync_after)}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
