"""M18 v1：调研报告**时效（freshness）检测**——"依据变了，旧报告还成立吗"。

动机（用户走查 M16-5）：provider 模型信息/证据源更新后，**旧报告不会被改写**（证据是抓取快照），
但此前**没有任何机制提示"这份报告的依据已变"**。v1 做只读检测：

| 判定 | 触发条件 | 含义 |
|---|---|---|
| `stale` | 某 provider 的 `fetched_at` **晚于**该归档的最新证据抓取时间 | 官网信息在报告之后又刷新过 → 报告里的模型/价格结论可能已过时 |
| `stale` | 报告 §7 点名的 evidence 文件**缺失** | 引用不落地（与归档门禁同口径） |
| `stale` | provider 当前 `model`/`embedding` 与归档证据里记录的"当前值"不同 | 默认模型已变更，报告结论需复核 |
| `suspect` | 某 evidence 文件的 mtime **晚于**报告 mtime | 证据在报告之后被改动，二者可能不一致 |
| `fresh` | 以上均不触发 | 依据未变 |

用法：
  .venv\\Scripts\\python.exe scripts\\report-freshness.py                 # 打印表格
  .venv\\Scripts\\python.exe scripts\\report-freshness.py --json <path>   # 结果落盘（默认 agents/runtime/report_freshness.json）
  .venv\\Scripts\\python.exe scripts\\report-freshness.py --check         # 有 stale 时退出 1（供定时任务/CI 使用）
  .venv\\Scripts\\python.exe scripts\\report-freshness.py --runs-dir <d> --providers-dir <d> --state-dir <d>   # 测试用重定向

**v1 边界（诚实声明）**：只做**只读检测**，不改写报告、不自动重跑；**不做自动"模型值漂移"归因**
（那需要逐结论溯源，见 `M18` 卡后续增量）——现值只在结果里列出供人工比对。判定规则仅三条：
"provider 在归档之后又刷新过" / "报告点名的证据缺失" / "证据在报告之后被改动"。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS = ROOT / "agents" / "runs"
DEFAULT_PROVIDERS = ROOT / "paper-qa-script" / "providers"
DEFAULT_STATE = ROOT / "agents" / "runtime" / "report_freshness.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_FETCHED_RE = re.compile(r"fetched_at:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?)")
_CURRENT_RE = re.compile(r'"current"\s*:\s*"([^"]+)"')
# 只在 §7 证据索引表区间内找引用（与归档门禁同口径）——否则会把正文里提到的项目文档
# （如 `1-WORKFLOW.MD`）误判成"缺失证据"（2026-09-21 在真实归档上实测到的假阳性）
_SECTION7_RE = re.compile(r"^##\s*7\.[^\n]*(?:\n|$)(.*?)(?=^##\s|\Z)", re.M | re.S)

# 教训 1.62（2026-09-21 关闭三查·二查 major）：§7 标题的真实写法有多种，单形态正则会**静默漏检**。
# 旧实现只认 `^##\s*7\.` → `### 7.` / `## 7、` / `## §7` / `## 证据索引表` 全部定位失败 →
# `cited=∅` → "点名证据缺失"完全静默（假阴性），与归档门禁 `verify_archive.py`（标题兜底 +
# 定位失败显式 FAIL）口径不一致。现改为：按标题层级定位（多形态）＋定位失败**显式退化并标注来源**。
_HEAD_RE = re.compile(r"^(#{1,6})[ \t]*(.+?)[ \t]*$", re.M)
_SECTION7_TITLE_RE = re.compile(r"^(?:§\s*)?7(?:[.、．:：)）]|\s|$)|证据索引")


def _extract_section7(text: str) -> tuple[str, str]:
    """定位 §7（证据索引表）区间 → (正文, 来源)；来源 ∈ {`heading`, `whole-doc`}。

    `whole-doc` = 没有可识别的 §7 标题：此时**退化为全文**（宁可多判、不可静默漏判），
    并把来源写进结果 JSON，使"为什么这次判成这样"可追溯。
    """
    heads = list(_HEAD_RE.finditer(text))
    for i, m in enumerate(heads):
        title = m.group(2).strip()
        if not _SECTION7_TITLE_RE.match(title):
            continue
        level = len(m.group(1))
        end = len(text)
        for nxt in heads[i + 1:]:
            if len(nxt.group(1)) <= level:  # 同级或更高级标题 = 本节结束
                end = nxt.start()
                break
        return text[m.end():end], "heading"
    return text, "whole-doc"


def _parse_ts(raw: str) -> float | None:
    """宽松时间解析 → epoch。

    关键口径（2026-09-21 实测踩坑）：**无时区信息的时间一律按项目权威时区 UTC+8 解释**，
    不能用本机时区——本机是 UTC+9，而证据头普遍写成 `2026-09-20 23:23 UTC+8`（`UTC+8` 是**字面标签**，
    不是可解析的偏移），若按本机解析会整体偏 1 小时，把"同一轮刷新产出的归档"误判为 stale。
    """
    s = (raw or "").strip()
    if not s:
        return None
    from datetime import datetime, timedelta, timezone

    tz = None
    m = re.search(r"UTC\s*([+-])\s*(\d{1,2})", s, re.I)
    if m:
        tz = timezone(timedelta(hours=int(m.group(2)) * (1 if m.group(1) == "+" else -1)))
        s = s[: m.start()].strip()
    cand = s.replace("Z", "+00:00")
    dt = None
    try:
        dt = datetime.fromisoformat(cand)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz or timezone(timedelta(hours=8)))  # 项目权威时区 UTC+8
    return dt.timestamp()


def _provider_current(providers_dir: Path) -> dict[str, dict]:
    """读 providers/*.json 的现值与刷新时间（只读；坏文件跳过）。"""
    out: dict[str, dict] = {}
    if not providers_dir.is_dir():
        return out
    for p in sorted(providers_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                continue
        except Exception:
            continue
        meta = data.get("meta") or {}
        out[str(data.get("name") or p.stem)] = {
            "model": data.get("model"),
            "embedding": data.get("embedding"),
            "fetched_at": meta.get("fetched_at"),
            "fetched_ts": _parse_ts(str(meta.get("fetched_at") or "")),
            "file": str(p),
        }
    return out


def _find_report(run_dir: Path) -> Path | None:
    """与 `verify/verify_archive.py::find_report()` **同口径**（复核 Round 5 minor#3）：
    优先 `tech-research.report.md` / `report.md`，再退回任意 `*.report.md`——
    避免多报告目录下两个工具分析不同报告。"""
    for name in ("tech-research.report.md", "report.md"):
        p = run_dir / name
        if p.is_file():
            return p
    hits = sorted(run_dir.glob("*.report.md"))
    return hits[0] if hits else None


def _analyze_archive(run_dir: Path, providers: dict[str, dict], refresh_tolerance_s: float = 3600.0) -> dict | None:
    """分析单个归档；**只分析调研（tech-research）归档**，其余 agent 的 run 直接跳过。

    跳过理由：其它 role 的报告引用的是项目文档（`1-WORKFLOW.MD` 之类），与"provider 官网依据"
    的时效无关；把它们纳入会产出大量假阳性（2026-09-21 实测 16 条 stale 里多数如此）。
    判定"是调研归档" = **至少 1 篇 `evidence/*.md`**，或报告文件名以 `tech-research` 开头
    （复核 Round 5 minor#2：只要求"有 evidence/ 目录"过宽，空目录也会被当成调研归档）。
    """
    report = _find_report(run_dir)
    if report is None:
        return None
    ev_dir = run_dir / "evidence"
    text = report.read_text(encoding="utf-8", errors="replace")
    ev_files = sorted(p for p in ev_dir.glob("*.md") if p.is_file()) if ev_dir.is_dir() else []
    if not (ev_files or report.name.startswith("tech-research")):
        return None

    newest_ev_ts: float | None = None
    ev_modified_after_report = False
    report_mtime = report.stat().st_mtime
    current_values: set[str] = set()
    for ev in ev_files:
        head = ev.read_text(encoding="utf-8", errors="replace")
        for raw in _FETCHED_RE.findall(head):
            ts = _parse_ts(raw)
            if ts and (newest_ev_ts is None or ts > newest_ev_ts):
                newest_ev_ts = ts
        current_values.update(_CURRENT_RE.findall(head))
        try:
            if ev.stat().st_mtime > report_mtime + 1.0:
                ev_modified_after_report = True
        except OSError:
            pass

    # §7 证据索引表点名的 evidence 是否都在磁盘。
    # 口径（复核 Round 5 major#2）：**优先只认表格行**（避免把 §7 之后的自由段落算成引用），
    # 但若 §7 内**没有表格行**（写成项目符号/自由段落），则退化为整段 §7 —— 否则"点名证据缺失"
    # 会完全静默（假阴性），且与归档门禁（只要求文件名出现在 §7 文本、不要求表格行）口径不一致。
    have = {p.name.lower() for p in ev_files}
    section7, section7_source = _extract_section7(text)
    rows = "\n".join(line for line in section7.splitlines() if line.strip().startswith("|"))
    scope_text = rows or section7
    cited = set(re.findall(r"evidence[/\\]([\w.\-]+\.(?:md|markdown))", scope_text, re.I))
    cited |= set(re.findall(r"(?<![\w/\\-])(\d{2}-[\w.\-]+\.(?:md|markdown))", scope_text, re.I))
    missing = sorted(n for n in cited if n.lower() not in have)

    reasons: list[str] = []
    status = "fresh"
    refreshed_since: list[str] = []
    for name, prov in providers.items():
        ts = prov.get("fetched_ts")
        # 容差：provider meta 的写入通常比抓取证据晚几秒~几分钟（同一轮刷新），
        # 不加容差会让"自己刚产出的归档"被自己判 stale（2026-09-21 实测）
        if ts and newest_ev_ts and ts > newest_ev_ts + refresh_tolerance_s:
            refreshed_since.append(name)
    if refreshed_since:
        status = "stale"
        reasons.append(f"provider 官网信息在该归档之后又刷新过：{', '.join(refreshed_since)}")
    if missing:
        status = "stale"
        reasons.append(f"报告点名的证据文件缺失：{', '.join(missing[:3])}")
    if ev_modified_after_report and status == "fresh":
        status = "suspect"
        reasons.append("有 evidence 文件在报告之后被改动（二者可能不一致）")

    return {
        "run_id": run_dir.name,
        "report": str(report),
        "report_mtime": report_mtime,
        "evidence_files": len(ev_files),
        "evidence_newest_fetched_at": newest_ev_ts,
        "recorded_current_values": sorted(current_values),
        "citation_scope": section7_source,
        "status": status,
        "reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="M18 v1 调研报告时效检测（只读）")
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    ap.add_argument("--providers-dir", default=str(DEFAULT_PROVIDERS))
    ap.add_argument("--json", default=str(DEFAULT_STATE), help="结果 JSON 落盘路径（默认 agents/runtime/report_freshness.json）")
    ap.add_argument("--check", action="store_true", help="有 stale 时退出 1")
    ap.add_argument("--fail-on", choices=["stale", "suspect"], default="stale",
                    help="--check 的告警阈值：默认 stale；suspect 会把『证据被改动』也纳入（复核 Round 5 minor#6）")
    ap.add_argument("--only", default="", help="只分析匹配该子串的 run 目录")
    ap.add_argument("--refresh-tolerance-s", type=float, default=3600.0,
                    help="provider 刷新晚于证据多久才算 stale（默认 3600s，容忍同轮刷新的写入延迟）")
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir)
    providers = _provider_current(Path(args.providers_dir))
    records: list[dict] = []
    if runs_dir.is_dir():
        for d in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            if args.only and args.only not in d.name:
                continue
            rec = _analyze_archive(d, providers, args.refresh_tolerance_s)
            if rec:
                records.append(rec)

    stale = [r for r in records if r["status"] == "stale"]
    suspect = [r for r in records if r["status"] == "suspect"]
    print(f"== 报告时效检测：{len(records)} 份归档（providers={len(providers)}，扫描 {runs_dir}）==")
    for r in records:
        mark = {"fresh": "✅ fresh", "suspect": "⚠ suspect", "stale": "❌ stale"}[r["status"]]
        print(f"  {mark:12s} {r['run_id']}（证据 {r['evidence_files']} 篇）")
        for why in r["reasons"]:
            print(f"      - {why}")
    print(f"\n汇总：fresh={len(records) - len(stale) - len(suspect)} suspect={len(suspect)} stale={len(stale)}")

    payload = {
        "generated_at": time.time(),
        "runs_dir": str(runs_dir),
        "providers": {k: {kk: vv for kk, vv in v.items() if kk != "file"} for k, v in providers.items()},
        "summary": {"total": len(records), "stale": len(stale), "suspect": len(suspect),
                    "fresh": len(records) - len(stale) - len(suspect)},
        "reports": records,
    }
    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(out)
        print(f"结果 → {out}")
    fail = bool(stale) or (args.fail_on == "suspect" and bool(suspect))
    return 1 if (args.check and fail) else 0


if __name__ == "__main__":
    sys.exit(main())
