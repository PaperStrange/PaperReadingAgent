"""成本度量仪：把 DSH 会话日志里的逐次模型调用折成钱，按天／按会话汇总。

为什么需要它：`agents/runtime/registry.json` 里 99 条 run 只有 8 条带 `usage`
⇒ 成本**无法按 run 归属**；真实花费只在会话日志的逐次调用记录里（`data.usage`）。
本脚本是"压成本"策略的**唯一验证仪器**：改了做法之后，读数要能下降。

用法：
    python scripts/spend-report.py                 # 今天（与昨天）
    python scripts/spend-report.py --days 3        # 最近 3 天
    python scripts/spend-report.py --sessions      # 附当日按会话明细
    python scripts/spend-report.py --check         # 预算自检（判决表＋口径对账）
    python scripts/spend-report.py --check --json  # 同上，机读（夹具／闸门用）

口径（全部可复算）：
  * **派单数**＝`agents/runtime/registry.json` 里当日（UTC+8）已登记的 run 数，
    直接调用 `scripts/agent-ops.py::_dispatch_reading`（同一函数、同一本账 ⇒ 与
    `register` 的派单预算闸门**同一个数**；本文件不复制那套算法）。
    会话日志**不用于计数**：旧实现按"目录名不以 `session-` 开头"数全机的会话
    目录，把别的主线的子代理会话也算成"我的派单"（作用域缺陷，见 A-COST 卡）。
  * **费用**只能从会话日志折算（账本 `usage` 缺口未修）。同一会话目录下并存的
    `session.jsonl.zstd`／`session.v3…`／`session.v4…` 是**累积重放**（首批记录
    逐字相同、末记录递增）⇒ 每目录只取**最新一份**，否则同一批调用会按文件数
    重复计价。
  * **本会话**＝父链可达 `agents/spend-budget.json::main_sessions` 的会话（头记录
    的 `parentSession`；旧布局的物理嵌套也算），其余会话只进"全机"合计。
  * 单价取 `agents/runtime/prices.json`（不写死）；档位按**事件自身时间戳**判
    （北京时间周一至五 09:00-12:00、14:00-18:00 为高峰，其余空闲）。
  * 模型名**不在事件里** ⇒ 按 `--model`（缺省 `deepseek-flash`）计价；
    若实际计费模型不同，读数按倍率缩放 —— 这是本仪器的**已知假设**，不是测量。
  * 汇率取价表 `meta.fx_usd_cny`；会话根取 `SPEND_SESSIONS_ROOT`（缺省
    `~/.dsh/sessions`；verify 夹具用它指到 %TEMP% 合成树）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import sys

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover
    # 行 41 修复：旧文案写"仓库 .venv 已装"——那是**本机现状**，不是清单事实：
    # 修复前 `requirements.txt` 与 `requirements-windows.txt` **都没有** `zstandard`，
    # 于是换机器/新克隆时它可能压根没装，而文案却让人以为已装（误导）。
    # 现在两份清单各自带 `zstandard`（版本与本仓 `.venv` 实装对齐，2026-09-29 核对 =
    # 0.25.0）。
    print("缺少运行依赖 zstandard（本脚本要解 DSH 会话日志 .jsonl.zstd）")
    print("安装：.venv\\Scripts\\python.exe -m pip install "
          "-r requirements-windows.txt（或 pip install zstandard）")
    print("用法：.venv\\Scripts\\python.exe scripts\\spend-report.py")
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
# 会话日志根：`SPEND_SESSIONS_ROOT` 可重定向（verify 夹具指到 %TEMP% 合成树）——
# 手法与 `agent-ops.py::AGENT_OPS_DIR` 同一套：**同一份代码**跑真数据与夹具。
SESS = pathlib.Path(os.environ.get("SPEND_SESSIONS_ROOT")
                    or (pathlib.Path.home() / ".dsh" / "sessions"))
AGENT_OPS = ROOT / "scripts" / "agent-ops.py"
CST = dt.timezone(dt.timedelta(hours=8))
# 「判据未执行」的专属退出码（`TG-19` M-B 口径：SKIP 与 PASS 互斥）——
# 与"超预算(1)"和"用法错误(2)"都不同：调用方不得把 SKIP 当成 OK。
SKIP_EXIT = 3


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


_AO_CACHE: dict = {}


def agent_ops():
    """把 `scripts/agent-ops.py` 当模块加载——派单计数的**唯一真源**。

    为什么是"加载别人的函数"而不是"照抄一遍算法"：账本读数必须与 `register` 的
    派单预算闸门给出**同一个数**，两处各写一份算法迟早漂移，而漂移的表现就是
    "同一天两个派单数"——那正是本卡要修的病。加载后连"同一本账"（`REGISTRY_PATH`
    与 `AGENT_OPS_DIR` 重定向）、"同一份预算"（`_spend_budget_path`）和"同一个
    今天"（`_local_date`）也一起同源（只加载一次，夹具里改 env 后再起进程才算）。
    """
    if not _AO_CACHE:
        spec = importlib.util.spec_from_file_location("_agent_ops_for_spend", AGENT_OPS)
        if spec is None or spec.loader is None:  # pragma: no cover —— 仓内文件
            raise SystemExit(f"SPEND-ERROR: 加载不了 {AGENT_OPS}（派单计数无真源）")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _AO_CACHE["ao"] = mod
    return _AO_CACHE["ao"]


def ledger_reading() -> dict:
    """当日（UTC+8）**账本口径**派单数：闸门用的那个数，逐字取自同一个函数。

    与闸门同源的三件事：① `_dispatch_reading`（同一函数）② `REGISTRY_PATH`
    （同一本账，`AGENT_OPS_DIR` 重定向时一起搬）③ 同一个"今天"（`_local_date`）。
    闸门的读法是**多信号取并集**（`run_id` 日期段 ∪ `started_at` 折算），本文件
    照用而不是另选一种：选一种就等于造第二个数。已知盲区（闸门文案里也写着）：
    既不带日期段、又漏 `--start` 的 run 归不出日期 ⇒ 不计入。
    `total=None` = 账本读不到 ⇒ 判据**未执行**（不是"今天零派单"）。
    """
    ao = agent_ops()
    day = ao._local_date()
    out = {"day": day, "path": str(ao.REGISTRY_PATH), "total": None,
           "by_id": 0, "by_start": 0, "why": ""}
    if not ao.REGISTRY_PATH.is_file():
        out["why"] = f"账本不存在（{ao.REGISTRY_PATH}）⇒ 判据未执行"
        return out
    try:
        data = json.loads(ao.REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        out["why"] = f"账本读不出（{exc}）⇒ 判据未执行"
        return out
    total, by_id, by_start = ao._dispatch_reading(data, day)
    out.update(total=total, by_id=by_id, by_start=by_start)
    return out


def session_header(path: pathlib.Path) -> dict:
    """会话日志**首行**的头记录（`type=session`，带 `id`/`parentSession`）。

    只解前 64 KiB：头记录是第一行，整份日志几十 MB 时全解纯属浪费。
    读不出／不是头记录 ⇒ `{}`——调用方按"归属未知"处理，**不猜成"本会话"**。
    """
    try:
        with open(path, "rb") as fh:
            chunk = zstd.ZstdDecompressor().stream_reader(fh).read(65536)
        obj = json.loads(chunk.split(b"\n", 1)[0].decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return {}
    return obj if isinstance(obj, dict) and obj.get("id") else {}


def session_files(root: pathlib.Path) -> dict:
    """`{会话 id: (最新日志路径, 头记录)}`——**每个会话目录只取最新一份**。

    同一目录下并存 `session.jsonl.zstd`／`session.v3.jsonl.zstd`／`session.v4…`
    是**累积重放**（2026-10-28 现跑核对：三份的首记录逐字相同、末记录依次递增
    到当下）⇒ 全读会把同一批调用按文件数重复计价。
    """
    newest: dict[pathlib.Path, pathlib.Path] = {}
    for path in root.rglob("*.jsonl.zstd"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        held = newest.get(path.parent)
        if held is None or mtime > held.stat().st_mtime:
            newest[path.parent] = path
    out: dict[str, tuple] = {}
    for path in newest.values():
        head = session_header(path)
        out[str(head.get("id") or path.parent.name)] = (path, head)
    return out


def _cst_day(ms: object) -> str:
    """毫秒时间戳 → UTC+8 日期串；缺失／非法 ⇒ 空串（不猜成今天）。"""
    if not isinstance(ms, (int, float)) or ms <= 0:
        return ""
    return dt.datetime.fromtimestamp(ms / 1000, CST).strftime("%Y-%m-%d")


def _nested(path: pathlib.Path, roots: list[str]) -> bool:
    """日志是否物理嵌在主会话目录下（旧布局的子代理目录形态）。"""
    return (path.parent.name in roots) or (path.parent.parent.name in roots)


def own_line(sessions: dict, roots: list[str], day: str) -> dict:
    """**本会话**名下的会话集合：父链可达 `main_sessions` 者。

    归属维度＝头记录的 `parentSession`（**可从数据判定**，不是"目录名长什么样"）：
    子代理会话逐级指回主线，主线的 id 由 `spend-budget.json::main_sessions` 给定
    （属本机数据，换会话只改数据文件）。旧布局的物理嵌套（`<主线目录>/<子>/`）
    也算——两种形态都能从磁盘看出来，所以都收。
    `members` = 本会话名下全部会话；`today` = 其中**建立于当日**的（＝当日派单）。
    """
    parent_of = {sid: str((head or {}).get("parentSession") or "")
                 for sid, (_p, head) in sessions.items()}
    members: list[str] = []
    for sid, (path, _head) in sessions.items():
        if sid in roots or _nested(path, roots):
            continue
        hop, seen = sid, set()
        while hop and hop not in seen:
            seen.add(hop)
            if hop in roots:
                members.append(sid)
                break
            hop = parent_of.get(hop, "")
    today = sorted(s for s in members
                   if _cst_day(sessions[s][1].get("createdAt")) == day)
    return {"roots": list(roots), "members": sorted(members), "today": today,
            "dirs": sorted({sessions[s][0].parent.name for s in members}),
            "today_dirs": sorted({sessions[s][0].parent.name for s in today})}


def scan(days: int, model: str, sessions: dict):
    """扫近 N 天的会话日志（每会话取最新一份），按天与会话汇总 token 与金额。"""
    models, fx = load_prices()
    cut = dt.datetime.now(CST) - dt.timedelta(days=days)
    per_day: dict[str, list] = {}
    per_sess: dict[str, list] = {}
    files = 0
    for path, _head in sessions.values():
        try:
            if dt.datetime.fromtimestamp(path.stat().st_mtime, CST) < cut:
                continue
        except OSError:
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


def baseline_note(got: float, base: float) -> str:
    """当日读数与 `baseline` 的**对照文本**（超基线/低于基线都要看得见）。

    G2 复盘行 40 修复：`agents/spend-budget.json::targets.verified_by` 声称
    "次日读数与 baseline 对比"，而旧实现只打印 `基线 <值>`、**从不比对**
    （声明了机制而机制不存在）⇒ 这里把比对真做出来。
    **口径**：`baseline` 自述"用于对照，不作为判据"⇒ 本函数只产出上屏文本，
    **不参与退出码**（退出码仍由预算上限决定）；"缺 baseline 字段 ⇒ SKIP"那条
    由调用方判（判据没被执行就不算通过，口径同 `TG-19` M-B）。
    """
    if base == 0:
        # 基线为 0 时**不能算倍率**（除零）——如实说"基线为 0"，不编一个无穷大出来
        return ("等于基线（基线 = 0，无倍率）" if got == 0
                else f"高于基线（基线 = 0，实测 {got}，无倍率）")
    if got > base:
        return f"高于基线 {abs(got / base - 1) * 100:.1f}%（{got / base:.2f}×）"
    if got < base:
        return f"低于基线 {(1 - got / base) * 100:.1f}%（{got / base:.2f}×）"
    return "等于基线（1.00×）"


def build_checks(per_day: dict, per_sess: dict, fx: float, model: str,
                 sessions: dict, doc: dict) -> dict:
    """当日判决表 ＋ 两口径对账（**只算不打印**：上屏与机读共用这一份）。"""
    led = ledger_reading()
    day = led["day"]
    budget = doc.get("budget") or {}
    base = doc.get("baseline") or {}
    targets = doc.get("targets") or {}
    mine = [str(x) for x in (doc.get("main_sessions") or [])]
    own = own_line(sessions, mine, day)
    rows = [(k.split("|", 1)[1], v) for k, v in per_sess.items()
            if k.startswith(day + "|")]
    d = per_day.get(day) or [0, 0, 0, 0, 0.0, 0]
    matched = {name for name, _a in rows if name in mine}
    main_out = sum(a[1] for name, a in rows if name in mine)
    own_cny = sum(a[4] for name, a in rows if name in own["dirs"]) * fx
    no_main = "配置的主线会话 id 在本机一条都没匹配到（换机器请改 `main_sessions`）"
    no_root = "`main_sessions` 为空 ⇒ 本机没有『本会话』定义"
    checks = [
        {"label": "派单会话数/日（账本）", "got": led["total"],
         "cap": budget.get("dispatched_sessions_per_day"),
         "base_key": "dispatched_sessions_per_day", "judge": "block",
         "measurable": led["total"] is not None, "why": led["why"],
         "note": "与 register 闸门同一函数、同一本账"},
        {"label": "派单会话数/日（日志·本会话）", "got": len(own["today"]),
         "cap": None, "base_key": None, "judge": "report",
         "measurable": bool(mine), "why": no_root,
         "note": "父链可达主线者；与账本对账用"},
        {"label": "主代理 output token/日", "got": main_out,
         "cap": budget.get("main_output_tokens_per_day"),
         "base_key": "main_output_tokens_per_day", "judge": "block",
         "measurable": bool(matched) or not mine, "why": no_main,
         "note": ""},
        {"label": "当日合计 CNY（全机）", "got": round(d[4] * fx, 2),
         "cap": budget.get("all_sessions_cny_per_day"),
         "base_key": "all_sessions_cny_per_day", "judge": "block",
         "measurable": True, "why": "",
         "note": "上限/基线按全机口径立，作用域未改"},
        {"label": "本会话合计 CNY", "got": round(own_cny, 2), "cap": None,
         "base_key": None, "judge": "report", "measurable": bool(mine),
         "why": no_root, "note": "作用域＝本会话"},
    ]
    gap = len(own["today"]) - (led["total"] or 0)
    recon = {"day": day, "ledger": led["total"], "log": len(own["today"]),
             "gap": gap, "unregistered": own["today"] if gap > 0 else [],
             "extra_in_ledger": -gap if gap < 0 else 0}
    return {"day": day, "model": model, "ledger": led,
            "own": {"today": own["today"], "members": own["members"],
                    "dirs": own["dirs"]},
            "baseline": base, "targets": targets, "checks": checks,
            "reconcile": recon}


def recon_line(recon: dict) -> str:
    """两口径对账的上屏文本（**差在哪必须写出来**，不许静默取其一）。"""
    led, log, gap = recon["ledger"], recon["log"], recon["gap"]
    head = (f"  口径对账 {recon['day']}：账本 {led if led is not None else '未执行'}"
            f" ｜ 日志·本会话 {log} ｜ 差 {gap:+d}")
    if gap == 0:
        return head + " ⇒ **两口径一致**（同一时点、同一 UTC+8 日）"
    if gap > 0:
        unreg = "、".join(recon["unregistered"])
        return (head + f" ⇒ 日志多 {gap} 笔＝**账本未登记**的派单；候选会话"
                f"（账本无 session_id，无法逐笔定位）：{unreg}")
    return (head + f" ⇒ 账本多 {recon['extra_in_ledger']} 笔**并非本会话**的登记"
            f"（同仓并行批／别的会话；账本行无 session_id，无法逐笔归属）")


def check(per_day: dict, per_sess: dict, fx: float, model: str,
          sessions: dict, want_json: bool = False) -> int:
    """按 agents/spend-budget.json 自检当日预算，并给出两口径对账。

    rc：`0` = 全部**判据**真的执行过且在预算内；`1` = 有判据项超预算；
    `3` = 有判据**没被执行**（① 账本读不到／② 配置的主线会话 id 在本机一条都
    没匹配到／③ `baseline` 缺该指标字段）——三条都**不得当 OK**；
    `0`＋`SKIP:` 行 = 预算未配置／今日无用量（既有口径，非"检查过"）。

    判决表分两类行：`block`（参与退出码）与 `report`（**只报**：无预算、无基线，
    不参与退出码）。"日志·本会话"与"本会话合计 CNY"两行是 `report`——它们是
    **读数**（作用域修正后才有的），判据仍是账本口径：两处用同一个数才叫同源。
    """
    path = agent_ops()._spend_budget_path()
    if not path.exists():
        print(f"SKIP: 找不到 {path}（预算未配置，不判）")
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    led = ledger_reading()
    if led["day"] not in per_day:
        print(f"SKIP: 今日（{led['day']}，UTC+8）无用量记录")
        return 0
    payload = build_checks(per_day, per_sess, fx, model, sessions, doc)
    base, targets = payload["baseline"], payload["targets"]
    over: list[str] = []
    skipped: list[str] = []
    shown: list[tuple] = []
    for row in payload["checks"]:
        label, got, cap = row["label"], row["got"], row["cap"]
        if row["judge"] == "report":
            why = row["why"] if not row["measurable"] else row["note"]
            shown.append(("只报", label, got, cap, None, why))
            continue
        b = base.get(row["base_key"])
        if not isinstance(b, (int, float)):
            b = None
        if not row["measurable"]:
            # **未执行优先于超预算**：这一格显示的 `OK` 是没有测量对象的 OK，
            # 若把它和别的超预算并列，真正的病（这条判据在换机后形同不存在）
            # 会被"另一项超预算"盖住 —— 那正是假绿换了个外衣（复核 major 7）。
            flag, note = "SKIP", f"未执行（{row['why']}）"
            skipped.append(f"{label}：{row['why']}")
        elif b is None:
            # 行 40：原文声称"与 baseline 对比"⇒ 没有基线字段时这一半**没被执行**，
            # 故是 SKIP（不是 OK，也不是 OVER）——判据没被触发就不算通过。
            why = f"`baseline.{row['base_key']}` 缺失 ⇒ 无对照对象"
            flag, note = "SKIP", f"未执行（{why}）"
            skipped.append(f"{label}：{why}")
        else:
            flag = "OK " if (cap is None or got <= cap) else "OVER"
            if flag == "OVER":
                over.append(label)
            note = baseline_note(float(got), float(b))
        shown.append((flag, label, got, cap, b, note))
    payload["rc"] = (SKIP_EXIT if skipped else (1 if over else 0))
    payload["shown"] = [{"flag": f, "label": lb, "got": g, "cap": c,
                         "baseline": bb, "note": nt} for f, lb, g, c, bb, nt in shown]
    if want_json:
        print(json.dumps(payload, ensure_ascii=False))
        return payload["rc"]
    print(f"预算自检 {payload['day']}（模型 {model}）｜基线 {base.get('measured_at')}"
          f"｜靶 相对基线 {targets.get('cut_ratio_vs_baseline')}×"
          f"（`targets.cut_ratio_vs_baseline`；对照只上屏，不作为判据）")
    for flag, label, got, cap, b, note in shown:
        if cap is None:
            print(f"  [{flag}] {label:<24} 实测 {str(got):<10}（{note}）")
            continue
        print(f"  [{flag}] {label:<24} 实测 {str(got):<10} 预算 {cap} "
              f"基线 {'（缺）' if b is None else b}｜对照 {note}")
    print(recon_line(payload["reconcile"]))
    if skipped:
        print(f"SPEND-BUDGET SKIP（{len(skipped)} 项判据**未执行**）"
              f"——**不是通过**：判据没有测量对象／没有对照对象，逐项原因见上"
              f"｜同时超预算的项：{over or '（无）'}")
        return payload["rc"]
    if over:
        print(f"SPEND-BUDGET FAIL（{len(over)} 项超预算）：{over}")
        return payload["rc"]
    print("SPEND-BUDGET PASS（全部在预算内；每项基线对照见上）")
    return payload["rc"]


def main() -> int:
    """命令行入口：--days/--model/--sessions/--json/--check。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--sessions", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args()

    sessions = session_files(SESS)
    per_day, per_sess, fx, files = scan(ns.days, ns.model, sessions)
    if ns.check:
        return check(per_day, per_sess, fx, ns.model, sessions, ns.json)
    if ns.json:
        payload = {"fx": fx, "days": dict(sorted(per_day.items())),
                   "sessions": per_sess}
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    print(f"会话日志 {files} 份（每会话取最新版本）｜近 {ns.days} 天有写入"
          f"｜模型假设 {ns.model}｜fx {fx}")
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
