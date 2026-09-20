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

Run: .venv\\Scripts\\python.exe verify\\verify_usage.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'Retro③ token 用量采集与成本换算：解析/累计/增量/价表查找/缺价不臆测/换算式/回调防裁剪（离线）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "paper-qa-script") not in sys.path:
    sys.path.insert(0, str(ROOT / "paper-qa-script"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import usage as U  # noqa: E402

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


class _Resp:
    """模拟 litellm ModelResponse（对象形态）。"""

    def __init__(self, model: str, prompt: int, completion: int, total: int | None = None) -> None:
        self.model = model
        self.usage = type("_U", (), {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total if total is not None else prompt + completion})()


def main() -> int:
    U.reset()

    # ① 解析：对象形态 + dict 形态 + 无 usage（仍记一次调用，不抛）
    U.record_response(_Resp("openai/deepseek-v4-flash", 1000, 200))
    U.record_response({"model": "openai/deepseek-v4-flash", "usage": {"prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600}})
    U.record_response(object())  # 无 usage 字段
    s1 = U.snapshot()
    ok("① 对象+dict 两种形态都被累计（calls=3）", s1["calls"] == 3, f"calls={s1['calls']}")
    ok("① token 汇总正确（prompt=1500 completion=300 total=1800）",
       (s1["prompt_tokens"], s1["completion_tokens"], s1["total_tokens"]) == (1500, 300, 1800),
       f"{s1['prompt_tokens']}/{s1['completion_tokens']}/{s1['total_tokens']}")
    ok("① by_model 明细按模型归集", s1["by_model"].get("openai/deepseek-v4-flash", {}).get("calls") == 2
       and s1["by_model"].get("unknown", {}).get("calls") == 1, str(list(s1["by_model"])))

    # ② 增量：再记一笔后 delta 只含新增
    before = U.snapshot()
    U.record_response(_Resp("openai/deepseek-v4-flash", 100, 50))
    d = U.delta(before)
    ok("② delta 只含新增（calls=1, prompt=100）", d["calls"] == 1 and d["prompt_tokens"] == 100, f"{d['calls']}/{d['prompt_tokens']}")
    ok("② delta 带累计视图（cumulative.calls=4）", d["cumulative"]["calls"] == 4, str(d["cumulative"]))
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
    allowed_cost = {"cost_cny", "partial_cost_cny", "unpriced_models", "no_data", "fx_usd_cny", "priced_models"}
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

    # ⑥ 回调挂载：幂等 + prune 后仍挂载（防被裁剪）
    import litellm  # noqa: E402

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
