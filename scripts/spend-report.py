"""成本度量仪：把 DSH 会话日志里的逐次模型调用折成钱，按天／按会话汇总。

为什么需要它：`agents/runtime/registry.json` 里 99 条 run 只有 8 条带 `usage`
⇒ 成本**无法按 run 归属**；真实花费只在会话日志的逐次调用记录里（`data.usage`）。
本脚本是"压成本"策略的**唯一验证仪器**：改了做法之后，读数要能下降。

用法：
    python scripts/spend-report.py                 # 今天（与昨天）
    python scripts/spend-report.py --days 3        # 最近 3 天
    python scripts/spend-report.py --sessions      # 附当日按会话明细
    python scripts/spend-report.py --json          # 机读输出（供闸门/记账）

口径（全部可复算）：
  * 单价取 `agents/runtime/prices.json`（不写死）；档位按**事件自身时间戳**判
    （北京时间周一至五 09:00-12:00、14:00-18:00 为高峰，其余空闲）。
  * 模型名**不在事件里** ⇒ 按 `--model`（缺省 `deepseek-flash`，与本会话配置一致）计价；
    若实际计费模型不同，读数按倍率缩放 —— 这是本仪器的**已知假设**，不是测量。
  * 汇率取价表 `meta.fx_usd_cny`；来源 `~/.dsh/sessions`（父子会话各自一目录）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover
    print("需要 zstandard（仓库 .venv 已装）")
    print("用法：.venv\\Scripts\\python.exe scripts\\spend-report.py")
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SESS = pathlib.Path.home() / ".dsh" / "sessions"
CST = dt.timezone(dt.timedelta(hours=8))


def load_prices() -> tuple[dict, float]:
    """读价表：返回 (provider.models, fx_usd_cny)。单价不写死在脚本里。"""
    p = ROOT / "agents" / "runtime" / "prices.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    models = doc.get("scraped", {}).get("deepseek", {}).get("models", {})
    return models, float(doc.get("meta", {}).get("fx_usd_cny") or 7.2)


def is_peak(ms: int) -> bool:
    """该毫秒时刻是否落在高峰窗口（北京时间周一至五 9-12、14-18）。"""
    t = dt.datetime.fromtimestamp(ms / 1000, CST)
    return t.weekday() < 5 and (9 <= t.hour < 12 or 14 <= t.hour < 18)


def tier(models: dict, model: str, ms: int) -> dict:
    """取该模型在该时刻适用的单价档（peak / off_peak）。"""
    m = models.get(model) or {}
    return (m.get("_tiers") or {}).get("peak" if is_peak(ms) else "off_peak") or {}


def usage_of(obj: dict) -> dict | None:
    """从一条日志记录里取出 usage 字典；取不到返回 None。"""
    d = obj.get("data") if isinstance(obj.get("data"), dict) else obj
    u = d.get("usage")
    if isinstance(u, dict) and ("inputTokens" in u or "input_tokens" in u):
        return u
    dd = d.get("data")
    if isinstance(dd, dict) and isinstance(dd.get("usage"), dict):
        return dd["usage"]
    return None


def scan(days: int, model: str):
    """扫近 N 天的会话日志，按天与会话汇总 token 与金额。"""
    models, fx = load_prices()
    cut = dt.datetime.now(CST) - dt.timedelta(days=days)
    per_day: dict[str, list] = {}
    per_sess: dict[str, list] = {}
    files = 0
    for path in SESS.rglob("*.jsonl.zstd"):
        if dt.datetime.fromtimestamp(path.stat().st_mtime, CST) < cut:
            continue
        files += 1
        try:
            with open(path, "rb") as fh:
                dec = zstd.ZstdDecompressor().stream_reader(fh).read()
                raw = dec.decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        for line in raw.splitlines():
            if "usage" not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            u = usage_of(obj)
            if not u:
                continue
            ms = obj.get("time") or 0
            if not ms:
                continue
            t = dt.datetime.fromtimestamp(ms / 1000, CST)
            if t < cut:
                continue
            tr = tier(models, model, ms)
            i = u.get("inputTokens") or u.get("input_tokens") or 0
            o = u.get("outputTokens") or u.get("output_tokens") or 0
            c = u.get("cacheReadTokens") or u.get("cache_read_input_tokens") or 0
            w = u.get("cacheWriteTokens") or u.get("cache_creation_input_tokens") or 0
            usd = (i * (tr.get("input_cost_per_token") or 0)
                   + o * (tr.get("output_cost_per_token") or 0)
                   + c * (tr.get("cache_read_input_token_cost") or 0)
                   + w * (tr.get("cache_creation_input_token_cost") or 0))
            day = t.strftime("%Y-%m-%d")
            name = path.parent.name
            items = ((per_day, day), (per_sess, day + "|" + name))
            for bucket, key in items:
                a = bucket.setdefault(key, [0, 0, 0, 0, 0.0, 0])
                a[0] += i
                a[1] += o
                a[2] += c
                a[3] += w
                a[4] += usd
                a[5] += 1
    return per_day, per_sess, fx, files


def check(per_day: dict, per_sess: dict, fx: float, model: str) -> int:
    """按 agents/spend-budget.json 自检当日预算。

    超预算非零退出（供收口/汇报节点自跑）。
    """
    path = ROOT / "agents" / "spend-budget.json"
    if not path.exists():
        print(f"SKIP: 找不到 {path}（预算未配置，不判）")
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    budget = doc.get("budget") or {}
    base = doc.get("baseline") or {}
    today = max(per_day) if per_day else None
    if not today:
        print("SKIP: 今日无用量记录")
        return 0
    day = per_day[today]
    rows = [(k.split("|", 1)[1], v) for k, v in per_sess.items()
            if k.startswith(today + "|")]
    dispatched = len([1 for name, _ in rows
                      if not name.startswith("session-")])
    mine = doc.get("main_sessions") or []
    main_out = sum(a[1] for name, a in rows if name in mine)
    cny = day[4] * fx
    checks = [
        ("派单会话数/日", dispatched, budget.get("dispatched_sessions_per_day")),
        ("主代理 output token/日", main_out, budget.get("main_output_tokens_per_day")),
        ("当日合计 CNY", round(cny, 2), budget.get("all_sessions_cny_per_day")),
    ]
    over = []
    print(f"预算自检 {today}（模型 {model}）｜基线 {base.get('measured_at')}")
    for label, got, cap in checks:
        flag = "OK " if (cap is None or got <= cap) else "OVER"
        if flag == "OVER":
            over.append(label)
        b = base.get({"派单会话数/日": "dispatched_sessions_per_day",
                      "主代理 output token/日": "main_output_tokens_per_day",
                      "当日合计 CNY": "all_sessions_cny_per_day"}[label])
        print(f"  [{flag}] {label:<22} 实测 {got:<10} 预算 {cap} 基线 {b}")
    if over:
        print(f"SPEND-BUDGET FAIL（{len(over)} 项超预算）：{over}")
        return 1
    print("SPEND-BUDGET PASS（全部在预算内）")
    return 0


def main() -> int:
    """命令行入口：--days/--model/--sessions/--json/--check。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--sessions", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args()

    per_day, per_sess, fx, files = scan(ns.days, ns.model)
    if ns.json:
        payload = {"fx": fx, "days": dict(sorted(per_day.items())),
                   "sessions": per_sess}
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    if ns.check:
        return check(per_day, per_sess, fx, ns.model)

    print(f"日志文件 {files} 个（近 {ns.days} 天有写入）｜模型假设 {ns.model}｜fx {fx}")
    print(f"{'day(CST)':<12}{'calls':>7}{'in':>11}{'out':>10}{'cache_rd':>13}{'CNY':>9}")
    tot = [0, 0, 0, 0, 0.0, 0]
    for day, a in sorted(per_day.items()):
        print(f"{day:<12}{a[5]:>7}{a[0]:>11}{a[1]:>10}{a[2]:>13}{a[4] * fx:>9.2f}")
        for k in range(6):
            tot[k] += a[k]
    print("-" * 62)
    print(f"{'TOTAL':<12}{tot[5]:>7}{tot[0]:>11}{tot[1]:>10}{tot[2]:>13}"
          f"{tot[4] * fx:>9.2f}")
    if ns.sessions and per_day:
        day = max(per_day)
        print(f"\n{day} 按会话（前 12，按金额降序）")
        rows = [(k.split("|", 1)[1], v) for k, v in per_sess.items()
                if k.startswith(day + "|")]
        for name, a in sorted(rows, key=lambda kv: -kv[1][4])[:12]:
            print(f"  {name[:46]:<48}{a[5]:>6}{a[1]:>10}out{a[4] * fx:>8.2f} CNY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
