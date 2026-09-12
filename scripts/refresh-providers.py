"""Sprint-16 F-AC8：provider 官网调研刷新（一 provider 一文件 + M16 证据归档 + 到期判定）。

职责：
  1. 按 `paper-qa-script/providers/<name>.json` 的 `meta.source_urls` 抓取官方文档；
  2. 产出 **M16 归档**（`agents/runs/<run_id>/`：tech-research.report.md + context.md + evidence/ + reasoning.md），
     每条 evidence 含 URL / 层级 / 抓取时间 / **逐字原文摘录**（抓取失败也记录 reason，绝不静默丢弃）；
  3. 抽取候选模型名（text-embedding-v?、qwen*、deepseek-*、gpt-* 等）与现值对比，写 **proposal**（默认不自动改配置）；
  4. `--apply` 只刷新 `meta.fetched_at/last_refresh_status/last_evidence_run`；**模型名变更需显式 `--accept-candidates`**
     （半自动：抓原文 + 人工确认，见预研笔记 2026-09-07 目标 2/3 与调研 run-047 的翻案条件）；
  5. 抓取失败：**不动 provider 文件**，状态写 `agents/runtime/provider_refresh_status.json`（fail-closed，无坏文件落盘）。

用法：
  .venv\\Scripts\\python.exe scripts\\refresh-providers.py --check
  .venv\\Scripts\\python.exe scripts\\refresh-providers.py --fetch [--provider dashscope] [--apply]
  .venv\\Scripts\\python.exe scripts\\refresh-providers.py --from-file <snapshot.json> --apply   # 离线（verify 用）
  .venv\\Scripts\\python.exe scripts\\refresh-providers.py --migrate                            # 旧 providers.json 拆文件
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "paper-qa-script" / "providers"
LEGACY_FILE = ROOT / "paper-qa-script" / "providers.json"
RUNS_DIR = ROOT / "agents" / "runs"
STATUS_FILE = ROOT / "agents" / "runtime" / "provider_refresh_status.json"
PROPOSAL_FILE = ROOT / "agents" / "runtime" / "provider_refresh_proposal.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALLOWED_HOSTS = {
    "api-docs.deepseek.com",
    "help.aliyun.com",
    "platform.openai.com",
    "openrouter.ai",
    "www.aliyun.com",
}
MAX_BYTES = 3 * 1024 * 1024
TIMEOUT_S = 25
DEFAULT_INTERVAL_DAYS = 14

CANDIDATE_PATTERNS = {
    "embedding": re.compile(r"\btext-embedding-v\d+(?:-\w+)?\b", re.I),
    "st_embedding": re.compile(r"\bst-[\w.\-]+MiniLM[\w.\-]*\b", re.I),
    "qwen_llm": re.compile(r"\bqwen[\w.\-]*\b", re.I),
    "deepseek_llm": re.compile(r"\bdeepseek-[\w.\-]+\b", re.I),
    "openai_llm": re.compile(r"\bgpt-[\w.\-]+\b", re.I),
}


# ---------- 抓取（沿用项目 SSRF/大小上限防护：3-LEARNED 1.50） ----------

class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """逐跳复检 https + 白名单域。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise urllib.error.HTTPError(newurl, code, f"重定向到非白名单域: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_text(url: str) -> tuple[str | None, str | None]:
    """返回 (文本, 错误原因)；失败不抛异常，由调用方记录 reason。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        return None, f"仅允许 https：{parsed.scheme}"
    if parsed.hostname not in ALLOWED_HOSTS:
        return None, f"非白名单域：{parsed.hostname}"
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    req = urllib.request.Request(url, headers={"User-Agent": "PaperReading-provider-refresh/1.0"})
    try:
        with opener.open(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return None, f"响应体超过上限 {MAX_BYTES} 字节"
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    return _visible_text(text), None


def _visible_text(html: str) -> str:
    """粗清洗：去 script/style/标签 + 压缩空白（保留正文供逐字摘录）。"""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def excerpt_around(text: str, needle: str, width: int = 320) -> str:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    return text[start : start + width].strip()


def extract_candidates(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for label, pat in CANDIDATE_PATTERNS.items():
        hits = sorted({m.group(0) for m in pat.finditer(text)}, key=lambda s: (-text.lower().count(s.lower()), s))
        if hits:
            found[label] = hits[:12]
    return found


# ---------- 归档（M16 契约） ----------

def _net_now(fmt: str) -> str:
    """权威时间口径（3-LEARNED 1.51）：统一 UTC+8，不随开发机时区漂移。"""
    return time.strftime(fmt, time.gmtime(time.time() + 8 * 3600))


def _next_run_id() -> str:
    date = _net_now("%Y-%m-%d")
    seq = 1
    while (RUNS_DIR / f"run-{date}-provider-refresh-{seq:03d}").exists():
        seq += 1
    return f"run-{date}-provider-refresh-{seq:03d}"


def write_archive(run_id: str, depth: str, entries: list[dict], question: str, context_lines: list[str]) -> Path:
    run_dir = RUNS_DIR / run_id
    (run_dir / "evidence").mkdir(parents=True, exist_ok=True)
    now = _net_now("%Y-%m-%d %H:%M") + " UTC+8"

    for i, ev in enumerate(entries, start=1):
        status = "ok" if ev.get("text") else "failed"
        quote = ev.get("quote") or "（抓取失败，无原文）"
        (run_dir / "evidence" / f"{i:02d}-{ev['slug']}.md").write_text(
            f"# evidence {i:02d}\n"
            f"- url: {ev['url']}\n"
            f"- tier: {ev.get('tier', 'tier1')}\n"
            f"- fetched_at: {now}\n"
            f"- fetch_status: {status}" + (f"（reason: {ev['error']}）" if status == "failed" else "") + "\n"
            f"- supports: {ev.get('supports', '')}\n"
            "## 原文段落（verbatim）\n"
            f"> {quote}\n"
            "## 备注\n"
            f"{ev.get('note', '')}\n",
            encoding="utf-8",
        )

    index_rows = "\n".join(
        f"| {ev.get('supports', '')} | `evidence/{i:02d}-{ev['slug']}.md` | "
        f"{('ok' if ev.get('text') else 'failed')} | {(ev.get('quote') or '')[:60]} |"
        for i, ev in enumerate(entries, start=1)
    )
    (run_dir / "tech-research.report.md").write_text(
        f"# tech-research report（question={question}, depth={depth}）\n\n"
        f"- run: {run_id} ｜ depth: **{depth}** ｜ 执行：`scripts/refresh-providers.py --fetch`（半自动：抓原文 + 人工确认）\n"
        f"- 时间锚：{now}\n\n"
        "## 0. 上下文与基线对齐\n"
        + "\n".join(f"- {line}" for line in context_lines) + "\n\n"
        "## 1. 分解的子问题\n"
        "1. 各 provider 官方文档当前公开的模型/嵌入型号是什么？\n"
        "2. 与 `providers/*.json` 现值是否存在漂移？\n\n"
        "## 2. 证据与来源\n"
        + "\n".join(
            f"- {ev['url']}（{ev.get('tier', 'tier1')}，fetch_status={'ok' if ev.get('text') else 'failed'}）"
            + (f" → 候选：{json.dumps(ev.get('candidates') or {}, ensure_ascii=False)}" if ev.get("text") else f" → 失败：{ev.get('error')}")
            for ev in entries
        ) + "\n\n"
        "## 3. 交叉验证与分歧\n"
        "- 官方文档为 tier1；若同一型号在多个官方页出现则互为佐证；抓取失败页在本轮不提供证据（不臆测）。\n\n"
        "## 4. 对比矩阵（值 → 现值 vs 文档候选）\n"
        "| provider | 字段 | 现值 | 文档候选 | 判定 |\n|---|---|---|---|---|\n"
        + "\n".join(
            f"| {row['provider']} | {row['field']} | `{row['current']}` | {row['candidates']} | {row['verdict']} |"
            for row in _verdict_rows(entries)
        ) + "\n\n"
        "## 5. 结论与建议\n"
        "- 默认**不自动改模型名**：proposal 记录候选与判定，交人工确认（`--accept-candidates` 才写入）。\n"
        "- 改判条件：官方文档结构变化导致抽取为空 → 转为纯人工核对；连续两轮无变化 → 可放宽为季度刷新。\n\n"
        "## 6. 开放问题\n"
        "- 403/302 站点（如 platform.openai.com）无法自动抓取 → 需人工或改用官方 API 列表端点。\n\n"
        "## 7. 证据索引表\n"
        "| 结论/字段 | evidence 文件 | 状态 | 摘录摘要 |\n|---|---|---|---|\n"
        f"{index_rows}\n\n"
        "## 8. 来源清单\n"
        + "\n".join(f"{i}. {ev['url']}" for i, ev in enumerate(entries, start=1)) + "\n",
        encoding="utf-8",
    )
    (run_dir / "context.md").write_text(
        "# 调研上下文快照\n\n"
        f"- question: {question}\n- depth: {depth}\n- date（网络时间）: {now}\n"
        f"- run_dir: agents/runs/{run_id}/\n"
        "- 注入基线：`pre-research/tech/2026-09-07-research-workflow.MD`（P1~P3）；F2 验收台账 Q1（一 provider 一文件 + 两周定时）\n"
        "- 约束：模型名变更须人工确认（半自动）；抓取失败不改动 provider 文件；预算/周期可配置\n"
        "- 本次不重议：provider 一文件布局、两周默认刷新周期\n\n"
        "## 注入的既有决策\n"
        + "\n".join(f"- {line}" for line in context_lines) + "\n",
        encoding="utf-8",
    )
    (run_dir / "reasoning.md").write_text(
        "# 思考过程附件\n\n"
        "## 结论推导链\n"
        "- 每个 provider 的候选型号 ← 其 `meta.source_urls` 官方页面的逐字摘录（evidence/）；\n"
        "- 判定规则：候选集合含现值 → `no_change`；不含现值且出现新候选 → `needs_review`（人工确认后才写入）；\n"
        "- 抓取失败 → `error`（该 provider 本轮不产生结论，保留旧文件）。\n\n"
        "## 采信与排除\n"
        "- 采信 tier1 官方文档/官方 API 列表端点；排除第三方转载（本轮未使用）。\n"
        "- 403 页面按失败记录 reason，不用搜索摘要替代（M16 契约）。\n\n"
        "## 未决与风险\n"
        "- 抽取为启发式正则：宁可多列候选，也不自动改配置；模型下线/更名仍需人工判断。\n",
        encoding="utf-8",
    )
    return run_dir


def _verdict_rows(entries: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for ev in entries:
        for row in ev.get("verdicts") or []:
            rows.append(row)
    return rows


# ---------- provider 文件读写 ----------

def load_provider_validated(names: list[str]) -> tuple[dict[str, dict], list[str]]:
    """用 SSOT 校验器读 providers/*.json（provider_config.load_provider_files），避免两套校验口径。

    code-review 050 nit：原实现只判 is_file()，坏 JSON 直接抛栈、name/必填字段不校验。
    """
    sys.path.insert(0, str(ROOT / "paper-qa-script"))
    try:
        import provider_config as pc  # noqa: PLC0415

        registry, problems = pc.load_provider_files(PROVIDERS_DIR)
        picked = {n: registry[n] for n in names if n in registry}
        for n in names:
            if n not in registry:
                problems.append(f"providers/{n}.json 缺失或未通过校验")
        return picked, problems
    except Exception as exc:  # noqa: BLE001 —— 兜底：脚本仍需可用（但显式告警）
        print(f"WARN: 复用 provider_config 校验失败（{type(exc).__name__}: {exc}）→ 回落朴素读取（不校验）")
        reg: dict[str, dict] = {}
        for n in names:
            p = PROVIDERS_DIR / f"{n}.json"
            if p.is_file():
                reg[n] = json.loads(p.read_text(encoding="utf-8"))
        return reg, ["（回落模式：未执行 SSOT 校验）"]


def load_provider(name: str) -> dict | None:
    p = PROVIDERS_DIR / f"{name}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def write_provider(name: str, data: dict) -> None:
    p = PROVIDERS_DIR / f"{name}.json"
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def write_status(data: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_name(STATUS_FILE.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATUS_FILE)


def is_due(name: str, interval_days: float) -> tuple[bool, str]:
    data = load_provider(name) or {}
    fetched = ((data.get("meta") or {}).get("fetched_at") or "").strip()
    if not fetched:
        return True, "无 fetched_at 记录"
    try:
        ts = time.mktime(time.strptime(fetched[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return True, f"fetched_at 不可解析（{fetched!r}）"
    due = ts + interval_days * 86400
    if time.time() >= due:
        return True, f"已到期（fetched_at {fetched[:16]}，间隔 {interval_days:g} 天）"
    return False, f"未到期（剩 {(due - time.time()) / 86400:.2f} 天）"


# ---------- 命令 ----------

def cmd_check(interval_days: float) -> int:
    names = sorted(p.stem for p in PROVIDERS_DIR.glob("*.json"))
    print(f"providers: {len(names)}（间隔 {interval_days:g} 天）")
    due_any = False
    for n in names:
        due, why = is_due(n, interval_days)
        due_any = due_any or due
        print(f"  {n:12s} due={due}  {why}")
    return 0 if not due_any else 1


def cmd_migrate() -> int:
    if not LEGACY_FILE.exists():
        print(f"NONE: 旧文件不存在（{LEGACY_FILE}）")
        return 0
    legacy = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
    written = []
    for name, entry in legacy.items():
        target = PROVIDERS_DIR / f"{name}.json"
        if target.exists():
            print(f"SKIP: {target.name} 已存在（避免覆盖，请手工合并）")
            continue
        payload = {"$schema_version": 1, "name": name, **entry,
                   "meta": {"source": "migrated from legacy providers.json",
                            "source_urls": [], "fetched_at": _net_now("%Y-%m-%dT%H:%M:%S") + "+08:00",
                            "last_refresh_status": "pending"}}
        write_provider(name, payload)
        written.append(name)
    print(f"MIGRATED: {written or '（无新增）'}；旧文件保留未删（用户可自行移除）")
    return 0


def refresh(entries_spec: list[tuple[str, dict]], run_id: str, apply: bool, accepts: dict[tuple[str, str], str],
            snapshot: dict[str, str] | None = None) -> int:
    entries: list[dict] = []
    proposal: dict = {"run_id": run_id, "generated_at": time.time(), "providers": {}}
    failures = 0
    for name, data in entries_spec:
        meta = data.get("meta") or {}
        urls = list(meta.get("source_urls") or [])
        provider_verdicts: list[dict] = []
        provider_candidates: dict[str, list[str]] = {}
        provider_ok = False
        for url in urls:
            if snapshot is not None:
                if url in snapshot:
                    text, err = _visible_text(snapshot[url]), None
                else:
                    text, err = None, "snapshot 未包含该 URL（离线模式）"
            else:
                text, err = fetch_text(url)
            slug = re.sub(r"[^a-z0-9]+", "-", urllib.parse.urlparse(url).netloc + urllib.parse.urlparse(url).path).strip("-")[:48]
            cands = extract_candidates(text) if text else {}
            for k, v in cands.items():
                provider_candidates.setdefault(k, [])
                provider_candidates[k] = sorted(set(provider_candidates[k]) | set(v))
            quote = ""
            if text:
                provider_ok = True
                flat = [c for v in cands.values() for c in v]
                quote = excerpt_around(text, flat[0]) if flat else text[:320]
            entries.append({
                "url": url, "slug": slug or f"src-{len(entries) + 1}", "text": text, "error": err,
                "quote": quote, "candidates": cands, "tier": "tier1",
                "supports": f"{name} 官方文档/端点（{', '.join(cands) or '无候选'}）",
                "note": "" if text else "抓取失败：本轮该来源不提供证据（保留旧配置）",
            })
        # 判定：现值是否仍被文档覆盖
        for field in ("model", "embedding"):
            current = str(data.get(field) or "")
            key_hint = {
                "model": ("qwen_llm", "deepseek_llm", "openai_llm"),
                "embedding": ("embedding", "st_embedding"),
            }[field]
            pool = sorted({c for k in key_hint for c in provider_candidates.get(k, [])})
            if not provider_ok:
                verdict = "error（抓取失败，保留现值）"
            elif not pool:
                verdict = "no_evidence（未抽到候选，人工核对）"
            elif any(current.split("/")[-1].lower() == c.lower() for c in pool):
                verdict = "no_change"
            else:
                verdict = "needs_review"
            provider_verdicts.append({"provider": name, "field": field, "current": current,
                                      "candidates": pool[:8] or "—", "verdict": verdict})
        proposal["providers"][name] = {
            "fetched_ok": provider_ok,
            "verdicts": provider_verdicts,
            "candidates": provider_candidates,
            "source_urls": urls,
        }
        if not provider_ok:
            failures += 1

    run_dir = write_archive(
        run_id, "expert",
        entries,
        question="provider 官网模型/嵌入型号调研（F-AC8 一 provider 一文件刷新）",
        context_lines=[
            "F2 验收 Q1：provider_config 拆一 provider 一文件 + 官网调研更新 + 默认两周定时",
            "M16 P2：工程级由主代理直执；本轮为 expert 档（子代理可用时可由子代理执行，脚本化归档等价）",
            "M16 P3：阈值可配置（间隔 PAPERQA_PROVIDER_INTERVAL_DAYS / state.config）",
        ],
    )
    PROPOSAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROPOSAL_FILE.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ARCHIVE: {run_dir}")
    print(f"PROPOSAL: {PROPOSAL_FILE}")

    status = {"run_id": run_id, "finished_at": time.time(), "providers": {}}
    applied: list[str] = []
    for name, data in entries_spec:
        info = proposal["providers"][name]
        entry = {"fetched_ok": info["fetched_ok"], "verdicts": info["verdicts"]}
        if info["fetched_ok"] and apply:
            meta = data.setdefault("meta", {})
            meta["fetched_at"] = _net_now("%Y-%m-%dT%H:%M:%S") + "+08:00"
            meta["last_refresh_status"] = "ok"
            meta["last_evidence_run"] = run_id
            if accepts:
                applied_fields = []
                for (pv, fld), value in sorted(accepts.items()):
                    if pv != name:
                        continue
                    data[fld] = value
                    applied_fields.append(f"{fld}={value}")
                if applied_fields:
                    meta.setdefault("refresh_notes", []).append(
                        f"{_net_now('%Y-%m-%d')} 人工确认更新：{'、'.join(applied_fields)}（run {run_id}）"
                    )
            write_provider(name, data)
            applied.append(name)
            entry["status"] = "applied"
        elif not info["fetched_ok"]:
            entry["status"] = "error"  # fail-closed：文件未被修改
        else:
            entry["status"] = "fetched_only"
        status["providers"][name] = entry
    write_status(status)
    print(f"STATUS: {STATUS_FILE}（applied={applied}）")
    if failures:
        print(f"WARN: {failures} 个 provider 抓取失败 → 保留旧文件（fail-closed），详见归档 evidence 与状态文件")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="provider 官网调研刷新（F-AC8）")
    ap.add_argument("--check", action="store_true", help="只做到期判定（不联网）")
    ap.add_argument("--fetch", action="store_true", help="抓取官方文档并产出 M16 归档 + proposal")
    ap.add_argument("--from-file", default="", help="离线模式：从快照 JSON（{url: text}）生成归档/proposal")
    ap.add_argument("--provider", default="", help="仅处理指定 provider")
    ap.add_argument("--apply", action="store_true", help="抓取成功后刷新 meta（fetched_at/status/evidence_run）")
    ap.add_argument("--accept", action="append", default=[],
                    help="显式接受候选并写入：<provider>:<field>=<value>（可多次；人工确认路径）")
    ap.add_argument("--accept-candidates", action="store_true",
                    help="【已弃用】隐式取候选第一名；请改用 --accept")
    ap.add_argument("--migrate", action="store_true", help="把旧 providers.json 拆成 providers/*.json")
    ap.add_argument("--interval-days", type=float,
                    default=float(os.environ.get("PAPERQA_PROVIDER_INTERVAL_DAYS", DEFAULT_INTERVAL_DAYS)))
    ap.add_argument("--providers-dir", default="", help="覆盖 providers 目录（测试/迁移用）")
    ap.add_argument("--runs-dir", default="", help="覆盖归档目录（测试用）")
    ap.add_argument("--state-dir", default="", help="覆盖状态/proposal 目录（测试用）")
    args = ap.parse_args()

    global PROVIDERS_DIR, RUNS_DIR, STATUS_FILE, PROPOSAL_FILE
    if args.providers_dir:
        PROVIDERS_DIR = Path(args.providers_dir).resolve()
    if args.runs_dir:
        RUNS_DIR = Path(args.runs_dir).resolve()
    if args.state_dir:
        sd = Path(args.state_dir).resolve()
        STATUS_FILE = sd / "provider_refresh_status.json"
        PROPOSAL_FILE = sd / "provider_refresh_proposal.json"

    if args.migrate:
        return cmd_migrate()
    if args.check:
        return cmd_check(args.interval_days)

    names = [args.provider] if args.provider else sorted(p.stem for p in PROVIDERS_DIR.glob("*.json"))
    registry, problems = load_provider_validated(names)
    if problems:
        print("PROBLEMS（SSOT 校验）: " + "; ".join(problems))
    entries_spec: list[tuple[str, dict]] = [(n, dict(registry[n])) for n in names if n in registry]
    if not entries_spec:
        print("没有可处理的 provider（全部缺失或未通过校验）")
        return 2

    # 显式接受候选（code-review 050 minor）：--accept provider:field=value，可多次；禁止隐式取字母序第一名
    accepts: dict[tuple[str, str], str] = {}
    for item in args.accept or []:
        try:
            lhs, value = item.split("=", 1)
            provider, field = lhs.split(":", 1)
        except ValueError:
            print(f"FAIL: --accept 语法应为 <provider>:<field>=<value>，收到 {item!r}")
            return 2
        accepts[(provider.strip().lower(), field.strip())] = value.strip()
    if args.accept_candidates:
        print("WARN: --accept-candidates（隐式取候选第一名）已弃用——请改用 --accept <provider>:<field>=<value>；本次忽略该开关。")

    snapshot = None
    if args.from_file:
        snapshot = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    elif not args.fetch:
        print("请指定 --fetch（真实抓取）或 --from-file（离线快照）或 --check/--migrate")
        return 2

    return refresh(entries_spec, _next_run_id(), apply=args.apply, accepts=accepts, snapshot=snapshot)


if __name__ == "__main__":
    sys.exit(main())
