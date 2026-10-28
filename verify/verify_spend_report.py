#!/usr/bin/env python3
"""A-COST：`scripts/spend-report.py` 的**派单计数口径**闸门（离线）。

## 病（2026-10-28 读码定位）
旧 `spend-report.py::check()` 的派单数是"目录名不以 `session-` 开头的会话数"，
而扫描面是 `~/.dsh/sessions` 的 `rglob("*.jsonl.zstd")`（**全机所有 cwd 桶**）⇒
判据是**目录名形状**、作用域是**整台机器**：别的主线、别的项目的子代理会话全被
算成"我的派单"，而同一时刻 `register` 的预算闸门读的是账本 ⇒ **同一天两个派单数**。

## 修法（被本闸门钉住的三件事）
1. 计数**只**来自账本，且**调用** `scripts/agent-ops.py::_dispatch_reading`
   （不复制算法）⇒ 与派单预算闸门**同一个数**；
2. 会话日志只用于①费用折算 ②一条**只报**的对账读数（父链可达
   `main_sessions` 的子会话数）——两口径不一致必须**上屏点名差额**；
3. 同一会话目录下的多个日志版本是**累积重放** ⇒ 只计价一次（否则费用按文件数翻倍）。

## 判据
1. **静态**：本仓不再有"目录名形状"计数式；`_dispatch_reading` 只在 agent-ops 定义
   一次，spend-report 是**调用**它。
2. **真驱动**（`%TEMP%` 合成夹具＝假账本＋假会话树，走 `AGENT_OPS_DIR`／
   `SPEND_SESSIONS_ROOT` 两个 env 把同一份代码指到夹具）：别的会话的子代理目录
   **不得**计入本会话读数（修前的算法会算进来——它的**冻结副本**在场上把这条
   反向对照证明成"真能红"）；本会话的子代理目录**必须**+1；账本补齐后两口径相等。
3. **fail-closed**：账本读不到 ⇒ 派单判据**未执行**（rc=3），不冒充"今天零派单"。
4. **费用作用域**：多版本日志只计一次；本会话 CNY ≤ 全机 CNY。
5. **真仓同源**：另一个进程里现算 `agent-ops` 的 `_dispatch_reading`，与 spend-report
   的账本读数**逐字相等**（两处各写一份算法就会在这里漂）。

## 用法
    .venv\\Scripts\\python.exe verify\\verify_spend_report.py
"""
from __future__ import annotations
VERIFY_META = {
    "features": (
        "A-COST 度量仪口径闸门：派单数只来自账本且调用 agent-ops 的 "
        "_dispatch_reading（与预算闸门同源）／会话日志只做费用与本会话只报读数／"
        "累积重放日志只计价一次／账本读不到 fail-closed(rc=3)／真仓双进程同源比对；"
        "反向对照条数见末行 `ALL PASS (N assertions)`"),
    "tier": "offline", "providers": [], "est_seconds": 25, "est_cost_cny": 0,
    "routes": [], "requires": ["none"],
}

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover —— 依赖缺失要响亮地坏，不静默跳过
    print("LINT-ERROR: 缺 zstandard（本闸门要造 .jsonl.zstd 夹具）："
          ".venv\\Scripts\\python.exe -m pip install -r requirements-windows.txt")
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
SPEND = ROOT / "scripts" / "spend-report.py"
AGENT_OPS = ROOT / "scripts" / "agent-ops.py"
CST = dt.timezone(dt.timedelta(hours=8))
MINE = "session-1111aaaa-1111-4111-8111-111111111111"
OTHER = "session-9999bbbb-9999-4999-8999-999999999999"
SUB_MINE = "2222cccc-2222-4222-8222-222222222222"
SUB_MINE2 = "4444ffff-4444-4444-8444-444444444444"
SUB_OTHER = "8888dddd-8888-4888-8888-888888888888"
SUB_OTHER2 = "3333eeee-3333-4333-8333-333333333333"
# 夹具落点一律**模块级常量**（`TG-9` 动态目标棘轮：新脚本的产物落点必须可静态
# 判定；把落点交给函数参数/argv 就会被判成"动态目标"）。
# 基座是 `tempfile.mkdtemp()` ⇒ 基座判定为 `%TEMP%`，段是字面量。
TMP = Path(tempfile.mkdtemp(prefix="spend-fx-"))
FX = TMP / "fx"
FX_BUCKET = FX / "sessions" / "--fx-layout--"
FX_MAIN = FX_BUCKET / MINE
FX_SUB = FX_BUCKET / SUB_MINE
FX_SUB2 = FX_BUCKET / SUB_MINE2
FX_OTHER = FX_BUCKET / OTHER
FX_OTHER_SUB = FX_BUCKET / SUB_OTHER
FX_OTHER_SUB2 = FX_BUCKET / SUB_OTHER2
FX_RUNTIME = FX / "agents" / "runtime"
FX_REG = FX_RUNTIME / "registry.json"
FX_REG_BAK = FX_RUNTIME / "registry.json.bak"
FX_BUDGET = FX / "agents" / "spend-budget.json"
DUP = TMP / "dup"
DUP_RUNTIME = DUP / "agents" / "runtime"
DUP_REG = DUP_RUNTIME / "registry.json"
DUP_BUDGET = DUP / "agents" / "spend-budget.json"
DUP_SESS = DUP / "sessions" / "--dup--" / SUB_MINE
DUP_V3 = DUP_SESS / "session.v3.jsonl.zstd"
DUP_V4 = DUP_SESS / "session.v4.jsonl.zstd"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_N = 0
_FAILS: list[str] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    """记一条断言（**只增不减**：条数有没有掉由 run_suite 的下限表盯）。"""
    global _N
    _N += 1
    tail = f"｜{detail}" if detail else ""
    if cond:
        print(f"PASS: {name}{tail}")
        return
    _FAILS.append(name)
    print(f"FAIL: {name}{tail}")


def blob(sid: str, parent: str | None, tokens: int = 1000) -> bytes:
    """一个会话日志的内容：首行头记录 + 两条 usage（压缩后返回，不落盘）。"""
    head = {"type": "session", "version": 4, "id": sid, "createdAt": now_ms(),
            "cwd": "fixture", "delegationDepth": 1 if parent else 0,
            "agentPreset": "default", "isSeeded": False, "origin": "test"}
    if parent:
        head["parentSession"] = parent
    lines = [json.dumps(head, ensure_ascii=False)]
    for seq in (1, 2):
        body = {"type": "message", "seq": seq, "time": now_ms(),
                "data": {"usage": {"inputTokens": tokens, "outputTokens": tokens,
                                   "cacheReadTokens": 0, "cacheWriteTokens": 0}}}
        lines.append(json.dumps(body, ensure_ascii=False))
    return zstd.ZstdCompressor().compress(("\n".join(lines) + "\n").encode())


def now_ms() -> int:
    """当前毫秒时间戳（夹具记录的时间；`UTC+8` 归属由度量仪自己折算）。"""
    return int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)


def ledger_doc(runs: int) -> str:
    """账本文本：`runs` 笔当日（UTC+8）run，id 带日期段 + `started_at` 两个信号。

    两个信号都给：闸门的读法是它们的**并集**，只给一个等于只测了半条判据。
    """
    day = dt.datetime.now(CST).strftime("%Y-%m-%d")
    started = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    rows = [{"run_id": f"run-{day}-implementation-{n}", "role": "implementation",
             "status": "running", "started_at": started} for n in range(1, runs + 1)]
    return json.dumps({"version": 1, "integrity": {}, "retractions": [],
                       "runs": rows}, ensure_ascii=False)


def budget_doc(mains: list) -> str:
    """预算文本：真仓预算的副本，只改 `main_sessions`（其余判据面保持原样）。"""
    doc = json.loads((ROOT / "agents" / "spend-budget.json").read_text("utf-8"))
    doc["main_sessions"] = list(mains)
    return json.dumps(doc, ensure_ascii=False, indent=2)


def usage_lines(path: Path) -> int:
    """该日志里带 `usage` 的记录条数（**解压后**数：压缩流里搜不到字面量）。"""
    try:
        with open(path, "rb") as fh:
            raw = zstd.ZstdDecompressor().stream_reader(fh).read()
    except Exception:  # noqa: BLE001
        return 0
    return raw.count(b"usage")


def prefix_reading(paths: list) -> int:
    """**修前算法的冻结副本**：目录名不以 `session-` 开头即算一笔派单。

    只用于反向对照——它必须能把"别的会话的子代理目录"数进来，否则说明夹具
    根本触发不了旧病，那条"修后不算"的断言就是**空转的**。生产代码不调用它。
    """
    return len([p for p in paths if not p.parent.name.startswith("session-")])


def run_check(env_extra: dict, *args: str) -> subprocess.CompletedProcess:
    """跑一次度量仪（子进程：同一份代码，只换 env 指到夹具）。"""
    env = dict(os.environ)
    env.pop("AGENT_OPS_DIR", None)
    env.pop("SPEND_SESSIONS_ROOT", None)
    env.update(env_extra)
    return subprocess.run([sys.executable, str(SPEND), "--check", *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def payload_of(proc: subprocess.CompletedProcess) -> dict:
    """取 `--check --json` 的机读载荷（只认最后一行 JSON）。"""
    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


def labels(pay: dict) -> dict:
    """`{行标签: 该行 dict}`（断言按语义名取行，不靠下标）。"""
    return {r["label"]: r for r in pay.get("checks", [])}


def got(pay: dict) -> dict:
    """`{行标签: 实测值}`。"""
    return {r["label"]: r["got"] for r in pay.get("checks", [])}


def main() -> int:
    """跑完全部判据；返回 0=全过、1=有断言失败（条数见末行，供套件棘轮）。"""
    src = SPEND.read_text(encoding="utf-8")
    aops = AGENT_OPS.read_text(encoding="utf-8")
    try:
        ok("静态①：`_dispatch_reading` 只在 agent-ops.py 定义**一次**，"
           "度量仪里没有第二份实现（口径漂移的结构性防线）",
           aops.count("def _dispatch_reading") == 1
           and "def _dispatch_reading" not in src,
           f"agent-ops 定义 {aops.count('def _dispatch_reading')} 处／"
           f"spend-report 定义 {src.count('def _dispatch_reading')} 处")
        ok("静态②：度量仪**调用**账本真源（importlib 加载 agent-ops ＋ 调该函数），"
           "不是照抄算法", "spec_from_file_location" in src
           and "_dispatch_reading(" in src and "REGISTRY_PATH" in src)
        ok("静态③：旧缺陷的计数式（按目录名形状数派单）已从生产代码消失",
           'not name.startswith("session-")' not in src)

        env = {"AGENT_OPS_DIR": str(FX / "agents"),
               "SPEND_SESSIONS_ROOT": str(FX / "sessions")}
        FX_MAIN.mkdir(parents=True, exist_ok=True)
        FX_SUB.mkdir(parents=True, exist_ok=True)
        FX_OTHER.mkdir(parents=True, exist_ok=True)
        FX_OTHER_SUB.mkdir(parents=True, exist_ok=True)
        FX_RUNTIME.mkdir(parents=True, exist_ok=True)
        FX_BUDGET.parent.mkdir(parents=True, exist_ok=True)
        (FX_MAIN / "session.v4.jsonl.zstd").write_bytes(blob(MINE, None, 0))
        (FX_SUB / "session.v4.jsonl.zstd").write_bytes(blob(SUB_MINE, MINE))
        (FX_OTHER / "session.v4.jsonl.zstd").write_bytes(blob(OTHER, None, 0))
        (FX_OTHER_SUB / "session.v4.jsonl.zstd").write_bytes(blob(SUB_OTHER, OTHER))
        FX_REG.write_text(ledger_doc(1), encoding="utf-8")
        FX_BUDGET.write_text(budget_doc([MINE]), encoding="utf-8")

        pay = payload_of(run_check(env, "--json"))
        ok("真驱动①：夹具账本 1 笔 ⇒ 判据行读数 1（账本口径真的在执行，不是摆设）",
           pay.get("ledger", {}).get("total") == 1,
           f"ledger={pay.get('ledger', {}).get('total')}")
        ok("真驱动②：本会话口径只数到**本会话的**子代理（1 笔），"
           "同一夹具里别的会话的子代理不计入",
           pay.get("own", {}).get("today") == [SUB_MINE],
           f"own={pay.get('own', {}).get('today')}")
        dirs0 = sorted(FX_BUCKET.glob("*/session.v4.jsonl.zstd"))
        own0 = pay.get("own", {}).get("today", [])
        ok("反向对照①（真阳性证明）：**修前算法**在同一夹具上数出 2 笔"
           "（含别的会话那笔）⇒ 夹具真的能触发旧病，"
           "上一条『修后只数 1 笔』才不是空转",
           prefix_reading(dirs0) == 2 and len(own0) == 1,
           f"修前={prefix_reading(dirs0)}／修后={len(own0)}")

        FX_OTHER_SUB2.mkdir(parents=True, exist_ok=True)
        (FX_OTHER_SUB2 / "session.v4.jsonl.zstd").write_bytes(blob(SUB_OTHER2, OTHER))
        pay1 = payload_of(run_check(env, "--json"))
        dirs1 = sorted(FX_BUCKET.glob("*/session.v4.jsonl.zstd"))
        ok("反向对照②：再造一个**别的会话**的子代理目录 ⇒ 本会话读数**不动**"
           "（仍是 1），而修前算法会涨到 3",
           pay1.get("own", {}).get("today") == [SUB_MINE]
           and prefix_reading(dirs1) == 3,
           f"修后={pay1.get('own', {}).get('today')}／修前={prefix_reading(dirs1)}")

        FX_SUB2.mkdir(parents=True, exist_ok=True)
        (FX_SUB2 / "session.v4.jsonl.zstd").write_bytes(blob(SUB_MINE2, MINE))
        pay2 = payload_of(run_check(env, "--json"))
        ok("反向对照③：再造一个**本会话**的子代理目录 ⇒ 本会话读数**+1**（1→2）"
           "——作用域收紧没有把该数的也挡掉",
           pay2.get("own", {}).get("today") == [SUB_MINE, SUB_MINE2],
           f"own={pay2.get('own', {}).get('today')}")
        rec2 = pay2.get("reconcile", {})
        ok("两口径不一致时**必须点名差额**（不许静默取其一）："
           "账本 1／日志 2 ⇒ gap=+1 且给出候选会话",
           rec2.get("gap") == 1 and len(rec2.get("unregistered") or []) == 2,
           f"reconcile={rec2}")
        txt2 = (run_check(env).stdout or "")
        ok("差额同时**上屏**（人读路径也看得见，不只藏在 JSON 里）",
           "口径对账" in txt2 and "差 +1" in txt2 and "未登记" in txt2)
        FX_REG.write_text(ledger_doc(2), encoding="utf-8")
        pay3 = payload_of(run_check(env, "--json"))
        rec3 = pay3.get("reconcile", {})
        ok("同源对账④：账本补到 2 笔 ⇒ **两口径相等**（账本 2＝本会话 2，gap=0）",
           pay3.get("ledger", {}).get("total") == 2
           and rec3.get("log") == 2 and rec3.get("gap") == 0,
           f"ledger={pay3.get('ledger', {}).get('total')}／{rec3}")
        rows3 = got(pay3)
        ok("金额轴仍是**判据**行（本批只修作用域，没有顺手把金额改成只报——"
           "放宽判据不是本卡的修法）",
           [r["judge"] for r in pay3.get("checks", [])
            if "CNY" in r["label"] and "全机" in r["label"]] == ["block"])
        ok("只报行不参与退出码（`judge=report` 且无预算值）："
           "读数与判据分开，避免用读数停工",
           all(r["judge"] == "report" and r["cap"] is None
               for lb, r in labels(pay3).items()
               if "日志" in lb or lb == "本会话合计 CNY"))

        FX_REG.rename(FX_REG_BAK)
        p4 = run_check(env)
        ok("fail-closed：账本读不到 ⇒ 派单判据**未执行**（rc=3）且不冒充"
           "『今天零派单』", p4.returncode == 3
           and "未执行" in (p4.stdout or ""), f"rc={p4.returncode}")
        FX_REG_BAK.rename(FX_REG)

        FX_BUDGET.write_text(budget_doc([]), encoding="utf-8")
        pay5 = payload_of(run_check(env, "--json"))
        own5 = [r for lb, r in labels(pay5).items() if "日志" in lb]
        ok("无『本会话』定义时（`main_sessions` 为空）：本会话行标**未执行**，"
           "而账本行照判（一处缺配不得把另一处拖成假绿）",
           bool(own5) and own5[0]["measurable"] is False
           and pay5.get("ledger", {}).get("total") == 2)
        FX_BUDGET.write_text(budget_doc([MINE]), encoding="utf-8")

        DUP_SESS.mkdir(parents=True, exist_ok=True)
        DUP_RUNTIME.mkdir(parents=True, exist_ok=True)
        DUP_BUDGET.parent.mkdir(parents=True, exist_ok=True)
        (DUP_SESS / "session.jsonl.zstd").write_bytes(blob(SUB_MINE, None, 200000))
        DUP_V3.write_bytes(blob(SUB_MINE, None, 200000))
        DUP_V4.write_bytes(blob(SUB_MINE, None, 200000))
        DUP_REG.write_text(ledger_doc(1), encoding="utf-8")
        DUP_BUDGET.write_text(budget_doc([]), encoding="utf-8")
        env_dup = {"AGENT_OPS_DIR": str(DUP / "agents"),
                   "SPEND_SESSIONS_ROOT": str(DUP / "sessions")}
        cny3 = got(payload_of(run_check(env_dup, "--json"))).get(
            "当日合计 CNY（全机）")
        files3 = sorted((DUP / "sessions").rglob("*.jsonl.zstd"))
        raw_records = sum(usage_lines(p) for p in files3)
        DUP_V3.unlink()
        DUP_V4.unlink()
        cny1 = got(payload_of(run_check(env_dup, "--json"))).get(
            "当日合计 CNY（全机）")
        ok("累积重放日志（同目录三份）**只计价一次**：三份并存与只留一份的全机"
           "CNY 相等，且读数不为 0（不是空转）",
           cny1 is not None and cny1 > 0.1 and cny3 == cny1,
           f"三份={cny3}／单份={cny1}／夹具 {len(files3)} 个日志文件共 "
           f"{raw_records} 条 usage 记录（修前按文件数计价＝×3）")
        ok("费用作用域是子集：本会话 CNY ≤ 全机 CNY（别的会话的用量不进本会话）",
           rows3.get("本会话合计 CNY", 1e9)
           <= rows3.get("当日合计 CNY（全机）", -1),
           f"本会话={rows3.get('本会话合计 CNY')}／"
           f"全机={rows3.get('当日合计 CNY（全机）')}")
    finally:
        shutil.rmtree(TMP, ignore_errors=True)

    # 真仓：两个进程各算一次同一个数（同源的最强证据）
    probe = ("import importlib.util,json,sys;"
             "s=importlib.util.spec_from_file_location('a',sys.argv[1]);"
             "m=importlib.util.module_from_spec(s);"
             "sys.modules['a']=m;s.loader.exec_module(m);"
             "d=json.loads(m.REGISTRY_PATH.read_text(encoding='utf-8'));"
             "print(m._dispatch_reading(d,m._local_date())[0])")
    r = subprocess.run([sys.executable, "-c", probe, str(AGENT_OPS)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    gate_n = (r.stdout or "").strip()
    env_real = dict(os.environ)
    env_real.pop("AGENT_OPS_DIR", None)
    env_real.pop("SPEND_SESSIONS_ROOT", None)
    real = subprocess.run([sys.executable, str(SPEND), "--check", "--json"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env_real)
    real_pay = payload_of(real)
    ok("真仓同源：spend-report 的账本读数 == 另一进程现算 agent-ops 的"
       "`_dispatch_reading`（两处各写一份算法就会在这里漂）",
       gate_n.isdigit() and real_pay.get("ledger", {}).get("total") == int(gate_n),
       f"agent-ops={gate_n}／spend-report={real_pay.get('ledger', {}).get('total')}")
    ok("真仓预算与账本**同源**（`_spend_budget_path()`）：预算文件跟着账本根走，"
       "夹具才能用受控预算真驱动闸门",
       "_spend_budget_path" in src)

    print(f"ALL PASS ({_N} assertions)" if not _FAILS
          else f"FAILURES ({len(_FAILS)}/{_N})：{_FAILS}")
    print(f"EVIDENCE: verify_spend_report.py assertions={_N} rc={1 if _FAILS else 0}")
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
