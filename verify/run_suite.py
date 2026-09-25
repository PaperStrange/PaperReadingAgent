"""Sprint-16 TG-5：分层验证 runner（fail-closed + 三态预算闸门）。

按 VERIFY_META.tier 分层执行 verify/ 下的脚本：
  offline = 零网络零 key（CI/本地默认）
  gui     = 需前后端 + Playwright
  network = 真实 API e2e（**花钱**，受预算上限约束）

语义（调研 run-2026-09-12-tech-research-047 采纳）：
  ① **fail-closed**：任一层任一脚本失败 → 整体 FAIL（非零退出，不"部分通过"）；
  ② **预算闸门**：启动前按 VERIFY_META.est_cost_cny 求上界，超上限 → **拒绝启动**（退出码 3，不静默降级）；
  ③ **三态记账**：本轮实际花费 = 由账本/价表核对；runner 自身不臆测花费——network 档记 `cost_status=unknown`
     并提示用真实用量回填（下一轮夜间套件遇到 unknown 会拒绝放行，见 scripts/scheduled-tasks.py）；
  ④ 上限与周期一律可配置：`--budget-cny` > env `PAPERQA_NIGHTLY_BUDGET_CNY` > 默认 10（D3 约束：不得写死）。

用法：
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier network --budget-cny 10
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline --verify-dir <fixture> --json <out>

结果 JSON（F4，2026-09-25 起**总是**写）：`--json` 默认 = `verify/suite_result.json`（已 gitignore），
且**启动时先落一份 `status=running` 的占位**再执行——中途崩/被杀留下的是"正在跑"，
而不是上一轮那份看起来仍像最新结果的 `ok`（`scheduled-tasks` 只认 `cost_status=measured`，占位不会被误采信）。
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-5 分层 runner：offline/gui/network 分层 + fail-closed + 三态预算闸门（上限可配置）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from verify.verify_matrix import collect  # noqa: E402

SELF_NAMES = {"run_suite.py"}
# F4（2026-09-25）：结果 JSON 的**标准路径**。原实现 `--json` 默认为空字符串，而 `_write_json("")`
# 直接 return ⇒ 默认跑一次 `run_suite.py --tier offline` **不刷新** `verify/suite_result.json`，
# 那份旧文件（上次 network 档留下的）看起来仍像"最新结果"——读的人要翻 `finished_at` 才发现不是本轮。
# 现改为：默认就写这个路径（它已在 `.gitignore` 内 → 不产生 git 产物），
# 并在**启动时**先落一份 `status=running` 的占位（中途崩/被杀留下的是"正在跑"，不是旧的 `ok`）。
SUITE_RESULT_REL = "verify/suite_result.json"
DEFAULT_BUDGET_CNY = 10.0
EST_SAFETY_FACTOR_DEFAULT = 1.3  # 预检上界 = Σest_cost_cny × 系数（可配置：--est-factor / PAPERQA_EST_SAFETY_FACTOR）
REFUSE_EXIT = 3


def budget_from(args) -> float:
    """上限优先级：CLI > env PAPERQA_NIGHTLY_BUDGET_CNY > 默认 10（可配置，不写死常量语义）。

    **必须是有限正数**：`nan` 会让 `est_cost > budget` 恒为 False（裸比较）→ 闸门被静默绕过
    （复核 run-053 Round 5 major#1 同型问题；预算与系数两条入口都要挡）。
    """
    raw: object = args.budget_cny if args.budget_cny is not None else os.environ.get("PAPERQA_NIGHTLY_BUDGET_CNY")
    if raw is None or raw == "":
        return DEFAULT_BUDGET_CNY
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        print(f"WARN: PAPERQA_NIGHTLY_BUDGET_CNY 非法（{raw!r}）→ 回落默认 {DEFAULT_BUDGET_CNY}")
        return DEFAULT_BUDGET_CNY
    if not math.isfinite(val) or val <= 0:
        print(f"WARN: 预算上限必须为有限正数（{raw!r}）→ 回落默认 {DEFAULT_BUDGET_CNY}（不放松闸门）")
        return DEFAULT_BUDGET_CNY
    return val


def est_factor_from(args) -> float:
    """预估安全系数（**可配置**，2026-09-21 用户口径）：CLI `--est-factor` > env `PAPERQA_EST_SAFETY_FACTOR` > 默认 1.3。

    为什么需要系数：`VERIFY_META.est_cost_cny` 记的是"近次实测值"，而预检闸门需要的是**上界**——
    实测 ¥1.013 而 est 定 1.1 时只剩 8.6% 余量，一次略长的运行就会被误拒（真花钱反而更少），
    故默认 ×1.3 留余量。

    **必须是有限正数**（复核 run-053 Round 5 major#1 实测）：只挡 `<=0` 不够——`--est-factor nan`
    或 env `=nan` 会让 `est_cost=nan`，而闸门是裸比较 `est_cost > budget` → **NaN 比较恒 False → 直接放行**。
    故用 `math.isfinite` 一并挡掉 `nan/inf`，非法值一律回落默认（绝不放松闸门）。
    """
    raw: object = args.est_factor if args.est_factor is not None else os.environ.get("PAPERQA_EST_SAFETY_FACTOR")
    if raw is None or raw == "":
        return EST_SAFETY_FACTOR_DEFAULT
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        print(f"WARN: est 安全系数非法（{raw!r}）→ 回落默认 {EST_SAFETY_FACTOR_DEFAULT}")
        return EST_SAFETY_FACTOR_DEFAULT
    if not math.isfinite(val) or val <= 0:
        print(f"WARN: est 安全系数必须为有限正数（{raw!r}）→ 回落默认 {EST_SAFETY_FACTOR_DEFAULT}（不放松闸门）")
        return EST_SAFETY_FACTOR_DEFAULT
    if val < 1.0:
        print(f"WARN: est 安全系数 {val} < 1 → 预检上界低于实测值，闸门更紧（可能误拒真实运行）")
    return val


def nonfinite_sources(est_values: list[tuple[str, float]], est_raw: float, est_cost: float) -> list[str]:
    """返回"使预估花费非有限"的来源名（空列表 = 正常）。

    教训 1.61（2026-09-21 关闭三查·二查 major）：`est_cost_cny: NaN` 会让 `nan > budget` 恒为 False
    → **付费 network 档被静默放行**（修复前实测 `exit=0 status=ok executed=True`）。故 Σ 入口、
    乘积入口都必须挡，不能只挡 CLI/env 两个入口（`budget_from`/`est_factor_from`）。
    抽成纯函数是为了让该守卫本身可被回归断言直接驱动（而不是只能靠端到端 fixture 间接触发）。
    """
    bad = sorted({n for n, v in est_values if not math.isfinite(v)})
    if not math.isfinite(est_raw):
        bad = sorted(set(bad) | {"<Σ est_cost_raw>"})
    if not math.isfinite(est_cost) and not bad:
        bad = ["<Σ est_cost>"]
    return bad


def select(verify_dir: Path, tier: str, only: list[str] | None) -> list[tuple[Path, dict]]:
    try:
        entries = collect(verify_dir)
    except SystemExit as exc:  # 元数据缺失/非法 → fail-closed 且给出可执行提示
        print(f"FAIL: 脚本元数据校验未通过，runner 拒绝启动（fail-closed）：{exc}")
        print("提示：TG-2 规则要求每个 verify 脚本带 VERIFY_META 头部；修复后重跑 `verify_matrix.py derive`。")
        raise SystemExit(2) from exc
    picked = [
        (p, m)
        for p, m in entries
        if m.get("tier") == tier and p.name not in SELF_NAMES and (not only or p.name in only)
    ]
    return sorted(picked, key=lambda pm: pm[0].name)


def run_one(path: Path, meta: dict, timeout_s: int) -> tuple[int, float]:
    if path.suffix == ".py":
        cmd = [sys.executable, str(path)]
    elif path.suffix == ".mjs":
        cmd = ["node", str(path)]
    else:
        return 127, 0.0
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), timeout=timeout_s, check=False)
        return proc.returncode, round(time.perf_counter() - t0, 2)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout_s}s")
        return 124, round(time.perf_counter() - t0, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="分层验证 runner（TG-5）")
    ap.add_argument("--tier", default="offline", choices=["offline", "gui", "network"])
    ap.add_argument("--budget-cny", dest="budget_cny", type=float, default=None,
                    help="本轮花费上限（CNY）；缺省读 env PAPERQA_NIGHTLY_BUDGET_CNY，再缺省 10")
    ap.add_argument("--est-factor", dest="est_factor", default=None,
                    help="预估安全系数（预检上界 = Σest_cost_cny × 系数）；缺省读 env PAPERQA_EST_SAFETY_FACTOR，再缺省 1.3")
    ap.add_argument("--verify-dir", default=str(ROOT / "verify"))
    ap.add_argument("--scripts", default="", help="只跑这些脚本（逗号分隔文件名）")
    ap.add_argument("--json", default=SUITE_RESULT_REL,
                    help=f"结果 JSON 落盘路径（默认 {SUITE_RESULT_REL}——**总是**会写，不会静默跳过）")
    ap.add_argument("--dry-run", action="store_true", help="只列将执行的脚本与预估花费，不执行")
    args = ap.parse_args()

    verify_dir = Path(args.verify_dir)
    if not verify_dir.is_absolute():
        verify_dir = (ROOT / verify_dir).resolve()
    only = [s.strip() for s in args.scripts.split(",") if s.strip()] or None

    picked = select(verify_dir, args.tier, only)
    est_values = [(p.name, float(m.get("est_cost_cny") or 0)) for p, m in picked]
    est_factor = est_factor_from(args)
    est_raw = round(sum(v for _, v in est_values), 4)
    est_cost = round(est_raw * est_factor, 4)
    budget = budget_from(args)
    started = time.time()
    summary: dict = {
        "tier": args.tier,
        "verify_dir": str(verify_dir),
        "budget_cny": budget,
        "est_cost_cny": est_cost,
        "est_cost_cny_raw": est_raw,
        "est_safety_factor": est_factor,
        "cost_measured_cny": None,
        "cost_status": "not_applicable" if args.tier != "network" else "unknown",
        "started_at": started,
        "scripts": [],
        "status": "unknown",
    }

    print(f"== run_suite tier={args.tier} scripts={len(picked)} est_raw={est_raw} × factor={est_factor} "
          f"→ est_cost={est_cost} CNY budget={budget} CNY ==")
    # F4：**启动即落占位**（status=running）——见 SUITE_RESULT_REL 处的说明。
    # 位置在预算/非有限闸门之前：这两条 fail-closed 路径会各自覆写为 refused_*，语义仍然正确。
    _write_json(args.json, {**summary, "status": "running"})
    if args.tier == "gui":
        print("NOTE: gui 档需要后端 8787 + 前端 5173 已启动（并用 Playwright）；请先确认端口空闲/服务在线，否则本档必然失败。")
    for p, m in picked:
        print(f"  - {p.name} (est {m.get('est_seconds')}s / {m.get('est_cost_cny')} CNY)")

    # 非有限值守卫（2026-09-21 关闭三查·二查 windows major，教训 1.61）：
    # `est_cost_cny: NaN` 会让 `nan > budget` 恒为 False → **付费 network 档被静默放行**（实测复现）。
    # 反向对照证据：修复前该 fixture 得到 `exit=0 status=ok executed=True`。
    # 关键：**Σ 入口与乘积入口都必须挡**——只挡 CLI/env 两个入口（budget_from / est_factor_from）等于没挡。
    bad = nonfinite_sources(est_values, est_raw, est_cost)
    if bad:
        summary["status"] = "refused_nonfinite_est"
        summary["finished_at"] = time.time()
        print(f"REFUSED: 预估花费含非有限值（{'、'.join(bad)}）→ 拒绝启动（fail-closed）。"
              f"NaN/inf/-inf 会使预算比较恒为 False 从而静默绕过闸门；请修脚本 VERIFY_META.est_cost_cny。")
        _write_json(args.json, summary)
        return REFUSE_EXIT

    if not math.isfinite(est_cost) or est_cost > budget:
        # 三态之"超限"：直接拒绝启动（fail-closed，不降级、不部分执行）
        summary["status"] = "refused_budget"
        summary["finished_at"] = time.time()
        print(f"REFUSED: 预估花费 {est_cost} CNY 超过上限 {budget} CNY → 拒绝启动（fail-closed）。"
              f"如需放行请调高 --budget-cny 或 env PAPERQA_NIGHTLY_BUDGET_CNY。")
        _write_json(args.json, summary)
        return REFUSE_EXIT

    if args.dry_run:
        summary["status"] = "dry_run"
        summary["finished_at"] = time.time()
        print("DRY-RUN: 未执行任何脚本。")
        _write_json(args.json, summary)
        return 0

    failed: list[str] = []
    # Retro ③（2026-09-20）：子脚本把实测用量写成 JSONL 指标文件，suite 据此聚合出真实成本。
    # 复核 round-4 minor：文件在**确定要执行之后**才创建（避免 --dry-run/拒绝启动路径遗留文件）。
    fd, metrics_name = tempfile.mkstemp(prefix="suite_metrics_", suffix=".jsonl")
    os.close(fd)  # 关键：立即关闭句柄，否则子进程继承 fd → unlink 报 WinError 32
    metrics_path = Path(metrics_name)
    os.environ["PAPERQA_SUITE_METRICS"] = str(metrics_path)
    try:
        for p, m in picked:
            timeout_s = int((m.get("est_seconds") or 60) * 4 + 60)
            print(f"--- {p.name} ---", flush=True)
            code, secs = run_one(p, m, timeout_s)
            summary["scripts"].append({"name": p.name, "exit": code, "seconds": secs})
            print(f"--- {p.name}: exit={code} ({secs}s) ---", flush=True)
            if code != 0:
                failed.append(p.name)

        metrics = _read_metrics(metrics_path)
    finally:
        # 复核 round-4 minor：环境变量必须清理，否则会泄漏到同进程的后续非套件运行
        os.environ.pop("PAPERQA_SUITE_METRICS", None)
        try:
            metrics_path.unlink(missing_ok=True)
        except OSError:
            pass  # 被占用也不影响结论（临时文件，系统会清）

    # 复核 round-4 major：只有**确有调用**（calls>0）且成本可换算的记录才算"已回报实测成本"，
    # 空账（回调尚未落地）不得被当成 measured，否则闸门会从 unknown 误推到 measured 且金额低估。
    measured = [m for m in metrics if isinstance(m.get("cost_cny"), (int, float)) and int(m.get("calls") or 0) > 0]
    unpriced = sorted({u for m in metrics for u in (m.get("unpriced_models") or [])})
    no_data = sorted({m.get("script") for m in metrics if not int(m.get("calls") or 0)})
    executed = [s["name"] for s in summary["scripts"]]
    summary["metrics"] = metrics
    summary["cost_measured_cny"] = round(sum(float(m["cost_cny"]) for m in measured), 6) if measured else None
    summary["cost_unpriced_models"] = unpriced
    summary["cost_no_data_scripts"] = no_data
    if args.tier == "network":
        # 三态之"未测量"：只有**所有被执行脚本**都给出可换算成本才转 measured；否则保持 unknown（不臆测）
        summary["cost_status"] = (
            "measured" if executed and set(executed) <= {m.get("script") for m in measured} else "unknown"
        )

    summary["finished_at"] = time.time()
    summary["status"] = "failed" if failed else "ok"
    summary["failed_scripts"] = failed
    _write_json(args.json, summary)

    if args.tier == "network":
        print(f"MEASURED: cost={summary['cost_measured_cny']} CNY status={summary['cost_status']} "
              f"scripts_reporting={len(measured)}/{len(executed)} unpriced={unpriced}"
              + (f" no_data={no_data}" if no_data else ""))
    if failed:
        print(f"\nSUITE FAILED ({len(failed)}/{len(picked)}): {', '.join(failed)}")
        return 1
    print(f"\nSUITE PASSED ({len(picked)} scripts)")
    if args.tier == "network":
        if summary["cost_status"] == "measured":
            print(f"NOTE: network 档**实测**花费 {summary['cost_measured_cny']} CNY（token 实测 + 本地价表换算）；"
                  "`scheduled-tasks.py` 会自动回填该值（无需人工 --record-cost）。")
        else:
            print("NOTE: network 档成本未测量完整（脚本缺用量回报或价表缺单价）→ cost_status=unknown；"
                  "未回填时下一轮夜间套件仍拒绝放行（三态闸门）。"
                  + (f" 缺价模型：{unpriced}" if unpriced else ""))
    return 0


def _read_metrics(path: Path) -> list[dict]:
    """读子脚本写的用量指标行（JSONL；Retro ③）。文件不存在/坏行 → 跳过，不抛。"""
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except OSError:
        pass
    return out


def _write_json(path_str: str, data: dict) -> None:
    """把结果 JSON **原子落盘**（先写 `.tmp` 再 `os.replace`）。

    **不再有"静默跳过"分支**（F4，2026-09-25）：旧实现在 `path_str` 为空时直接 `return`，
    而 `--json` 的默认值就是空串 ⇒ 默认跑法**不刷新** `verify/suite_result.json`，
    盘上那份旧结果看起来仍像最新结果（`scheduled-tasks` 靠 `finished_at ≥ t0` 才没被它骗到，
    但读文件的人会）。现默认路径 = `SUITE_RESULT_REL`；即使调用方显式传空串，
    也落到默认路径而不是什么都不写——"以为写了其实没写"正是要消灭的形态。
    """
    p = Path(path_str.strip() or SUITE_RESULT_REL)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
    print(f"summary → {p}（status={data.get('status')}）")


if __name__ == "__main__":
    sys.exit(main())
