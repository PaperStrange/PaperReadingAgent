"""AgentOps 账本 CLI（Sprint-8 A-LEDGER，US-8.4）。

职责：子代理 run 的登记/状态流转/成本估算，全部落在**文件真相源**：
  agents/runtime/registry.json          # 账本（append + 完整性校验，防手改双写 UC-7）
  agents/runtime/prices.json            # 价表（litellm 价表派生 + 人工覆盖段 UC-10）
  agents/runs/<run_id>/<role>.report.md # 报告存档（memory 浏览入口）

约束：纯 Python 标准库（UC-11），不依赖 DSH 或仓库外工具；任何编排方（DSH/CI/IDE）都可调用。

用法：
  python scripts/agent-ops.py register --role R --task T --spec "S@v" [--model M] [--start]
      [--input-chars N] [--context-input-tokens N] [--context-max-tokens N]
      [--scope-source <prefix><run_id> | --scope-source self-chosen --deviation "<理由>"]
      [--coverage-anchor <sha>]            # TG-15：默认自动记登记时的 HEAD
  python scripts/agent-ops.py update <run_id> --status running
      [--usage-in N --usage-out N --usage-cache-read N --usage-cache-write N]
  python scripts/agent-ops.py finish <run_id> --status succeeded|failed|cancelled
      [--covers-through <sha>]             # TG-15：默认自动记收尾时的 HEAD
  python scripts/agent-ops.py round <run_id> --note "Round 5：..." --output-chars 12000   # TG-10① 追加轮次（终态也可）
  python scripts/agent-ops.py interrupt <run_id> --reason "端口争用，让出 8787" --impact "round-3 顺延至 round-4"  # TG-10②
      [--output-chars N] [--result-file PATH] [--cost-override X] [--estimate-mode chars]
  python scripts/agent-ops.py list [--status S] [--role R] [--limit N]
  python scripts/agent-ops.py close-sync --sprint <sprint.md> [--write] [--fail-on-unowned]   # TG-15⑤ 覆盖候选生成
  python scripts/agent-ops.py validate-spec <file.md>
  python scripts/agent-ops.py fetch-spec <file.md> [--offline]
  python scripts/agent-ops.py parse-report <file.md>
  python scripts/agent-ops.py prices-derive

测量口径（TG-13，真源 `agents/policy.json::ledger_measurement`）：
  dur      = `ended_at - started_at`（累计**墙钟**；`round` 追加会前移到末轮）。
             **不是**"首末轮时间差"、**不是**报告自报时长（报告时长不得回填账本）。
  rounds   真源 = **报告轮次**（能数出 `Round N`/`第 N 轮` 时以报告为准并与账本核对）；
             报告不可数时账本声明值只是 `declared` 声明，不得当实测值上报看板。
  unknown  **缺值必须显式 unknown**：无墙钟读数 → `dur_minutes=null` + `measurement_source=unknown`
             （`list` 打印 `dur=unknown`）；**禁止**用 `0.00`／整十分钟等退化值冒充实测值。
  `finish`/`round` 写入时**检测时间戳退化并标注**（`measurement_flags` + 来源降级为 `declared`），
  不拒绝写入（真实 <1 秒的 run 不该被误杀；缺行比带标记的行更难审计），
  闸门 `verify/verify_ledger_measurement.py` 对截止日之后的新 run 一律 FAIL。

状态机（UC-3）：queued -> running -> succeeded|failed|cancelled；非法流转拒绝。
成本估算（UC-4）：cost = usage x prices.json 单价（含 cache 分列）；无 usage 时按
  input_chars/4、output_chars/4 兜底并标 estimated=true；价表缺该模型 → pending_price。
政策（TG-15）：**角色集合 / 阈值 / 覆盖路径 / 关闭步骤 一律来自数据文件**
  （agents/fanout.json + agents/functions/*.md frontmatter + agents/policy.json），
  本文件不得再出现政策常量；加载器 verify/agent_policy.py，规则见 docs/1-WORKFLOW.MD §6（政策数据化）。
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

if os.name == "nt":
    import msvcrt  # Windows 文件锁（LK_LOCK/LK_UNLCK）
else:
    import fcntl  # POSIX 文件锁（flock）

REPO_ROOT = Path(__file__).resolve().parent.parent
# AGENT_OPS_DIR 环境变量可重定向账本根（verify 脚本用临时目录隔离；默认 agents）
_AGENTS_BASE = Path(os.environ.get("AGENT_OPS_DIR", str(REPO_ROOT / "agents")))
RUNTIME_DIR = _AGENTS_BASE / "runtime"
REGISTRY_PATH = RUNTIME_DIR / "registry.json"
PRICES_PATH = RUNTIME_DIR / "prices.json"
RUNS_DIR = _AGENTS_BASE / "runs"

_CHARS_PER_TOKEN = 4.0  # UC-4 兜底：无 token 上报时 tokens ≈ chars/4

# TG-11（Sprint-17）：评审类 run 的 scope 来源必须可追溯。同一条规则写在 spec / workflow 里
# 曾被整条绕过（证据：phases/testing-governance/2026-09-21-review-scope-incident-evidence.MD），
# 所以改成 CLI 层 fail-closed：要么引用〇查（impact-assessment）的 run，要么显式声明偏离理由。
#
# TG-15（Sprint-17 D2）：**角色集合与阈值不再写在这里**——原先的 `_REVIEW_ROLES`/`_MIN_DEVIATION_CHARS`
# 与本文件外的 3 份副本一起构成"加角色要改代码"的硬编码面。现在全部来自数据：
#   agents/fanout.json（关闭流水线步骤/targets）+ 各 spec frontmatter 的 scope_required/coverage_window
#   + agents/policy.json（阈值与开关）。加载器见 verify/agent_policy.py；规则见 1-WORKFLOW.MD §6（政策数据化）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verify.agent_policy import load_policy, parse_frontmatter  # noqa: E402
from verify.outbound_guard import refuse_or_exit  # noqa: E402

_POLICY = None


def policy():
    """懒加载政策（首次调用时读盘；缺文件 → PolicyError，退出码 2，不静默回落常量）。"""
    global _POLICY
    if _POLICY is None:
        _POLICY = load_policy()
    return _POLICY


def _review_roles() -> set[str]:
    """凡产出评审结论的角色（= spec 声明 scope_required: true）→ 其 run 必须有 scope 声明（C1）。"""
    return policy().review_roles


def _scope_ref_prefixes() -> tuple[str, ...]:
    return policy().scope_ref_sources


def _ledger_policy() -> dict:
    """账本状态机（政策数据：`agents/policy.json::ledger_status`）。

    2026-09-23 二查 finding：状态白名单原先是本文件的 `_STATUSES/_TERMINAL/_TRANSITIONS` 常量，
    而 `1-WORKFLOW.MD` §6（政策数据化）明列"状态白名单须来自数据文件"——属"文档承诺 > 实现"。现由政策提供。
    """
    return policy()._data("ledger_status")


def _statuses() -> set[str]:
    return set(_ledger_policy()["all"])


def _terminal() -> set[str]:
    return set(_ledger_policy()["terminal"])


def _transitions() -> dict[str, set[str]]:
    return {k: set(v) for k, v in _ledger_policy()["transitions"].items()}


def _non_credible_statuses() -> set[str]:
    """不可采信的状态（scope 引用指向这类 run 时 fail-closed）——同一事实原先在本文件与
    `verify/verify_close_readiness.py` 各写一份字面量集合，现统一由政策提供。"""
    return set(_ledger_policy()["non_credible"])


def _git_head() -> str:
    """当前 HEAD（锚点自动化用）。非 git 环境返回空串（不阻断记账）。"""
    from verify.agent_policy import head_sha

    return head_sha(REPO_ROOT)


def _resolve_sha(value: str) -> str | None:
    """把用户给的锚点/区间端点**规范化成完整 40 位 sha**；无法解析返回 None（调用方 fail-closed）。

    审核发现 F1/N5：短 sha 会让 `CoverageWindow.covers()` 恒 False（`order` 里只有完整 sha），
    该 run 的覆盖窗口被**静默丢弃**。因此这里不接受"能存就行"的值：能解析就规范化，不能解析就报错。
    """
    value = (value or "").strip()
    if not value:
        return None
    from verify.agent_policy import git

    out = git(REPO_ROOT, "rev-parse", "--verify", f"{value}^{{commit}}", allow_fail=True).strip()
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else None



def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# A5（审核 finding M-g）：**自动 run-id 的日期段用 UTC+8**（项目权威时区），与 run 目录/文档命名同口径。
# 实测漂移：本地 2026-09-25 00:47 登记的 run 被自动命名成 `run-2026-09-24-doc-audit-066`
# （`_now()` 是 UTC），而同一次运行的产物目录按 UTC+8 叫 `run-2026-09-25-doc-audit-066`
# → 账本 id ↔ 目录名对不上（断言见 verify/verify_agentops.py 的「M-g 断言」）。
# 只改 **id 的日期段**：账本时间戳（started_at/ended_at/rounds）仍是 UTC 口径，
# 这样 `_duration_minutes`、`list` 与既有断言都不受影响（最小可行改动）。
_TZ_OFFSET_HOURS = 8  # UTC+8（项目权威时区；见 docs/1-WORKFLOW.MD 的时间口径）


def _local_date() -> str:
    """项目权威时区的日期 `YYYY-MM-DD`（自动 run-id 的日期段）。"""
    return (datetime.now(timezone.utc) + timedelta(hours=_TZ_OFFSET_HOURS)).strftime("%Y-%m-%d")


def _duration_minutes(start: str, end: str) -> float | None:
    """`_now()` 产出的 ISO 时间差（分钟）；解析失败返回 None（只影响展示，不影响记账）。"""
    try:
        return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60.0
    except (TypeError, ValueError):
        return None


# ------------------------------------------------ TG-13：账本『测量化』（来源/退化/unknown）

def _measurement_policy() -> dict:
    """测量口径（政策数据：`agents/policy.json::ledger_measurement`，TG-13）。

    口径此前只存在于讨论与注释里：`list` 打印 `dur=`、看板画时长、评审引用时长各按各的默认，
    于是"写入时刻的巧合"（两端时间戳逐字节相同 → `0.00`；恰好整十分钟）被一路当成测量值。
    现在 `dur`/`rounds`/`unknown` 三条口径 + 退化判定参数 + 合法来源取值全部来自数据文件。
    """
    return policy().ledger_measurement


def _round_multiple() -> int:
    return int(_measurement_policy()["degenerate"]["round_minutes_multiple"])


def measurement_of(started_at: str | None, ended_at: str | None) -> tuple[str, list[str], float | None]:
    """把一对时间戳翻译成 `(测量来源, 退化标记, dur_minutes)`——**纯函数**，供断言直接驱动。

    口径（`agents/policy.json::ledger_measurement`）：
      * 任一端缺失/不可解析 → `("unknown", ["missing_timestamp"], None)`——缺值必须**显式 unknown**，
        **不得**回落 `0.00`（`0.00` 的含义是"未测得"，不是"零耗时"）；
      * 两端逐字节相同/差值恰 `0.00`（`zero_duration`）、差值恰为整十分钟（`round_duration`）、
        末态早于起点（`negative_duration`）→ `("declared", [标记], None)`——这些是**写入时刻的巧合**，
        不是测量值；因此 **不写进 `dur_minutes`**（写进去就是把退化值冒充测量值；
        原始读数仍在 `started_at`/`ended_at` 里，标记说明它退化在哪）；
      * 其余 → `("wall-clock", [], round(dur, 3))`，即可信的墙钟实测值。

    为什么是"标注 + 字段降级"而不是"直接拒绝写入"（卡内要求二选一，这里择优并说明）：
    `finish` 的 `ended_at` 由 CLI 现取，一个真实耗时 <1 秒的 run 或恰好落在整十秒边界的 run
    会被 `reject` 误杀（把正确的记账挡在门外），而**账本缺行**比**带标记的行**更难审计；
    退化标记 + `measurement_source=declared` 让"这不是测量值"成为**可查询的事实**，
    闸门（`verify/verify_ledger_measurement.py`）再对截止日之后的新 run 一律 FAIL——
    于是既不在写入侧制造假红，也不让退化值冒充测量值。
    """
    try:
        start = datetime.fromisoformat(str(started_at))
        end = datetime.fromisoformat(str(ended_at))
    except (TypeError, ValueError):
        return "unknown", ["missing_timestamp"], None
    if start.tzinfo is None or end.tzinfo is None:
        return "unknown", ["missing_timestamp"], None
    mins = (end - start).total_seconds() / 60.0
    if mins == 0.0:
        return "declared", ["zero_duration"], None
    if mins < 0:
        return "declared", ["negative_duration"], None
    multiple = _round_multiple()
    ratio = mins / multiple
    if abs(ratio - round(ratio)) < 1e-9:
        return "declared", ["round_duration"], None
    return "wall-clock", [], round(mins, 3)


def _apply_measurement(run: dict) -> None:
    """把 `measurement_source`/`measurement_flags`/`dur_minutes` 刷成当前时间戳的结果。

    非终态 run（queued/running）尚无末态时间戳 → 记 `unknown` + 无标记（"还没测"不是缺陷）；
    终态 run → 走 `measurement_of()`：可测则 `wall-clock` + 实测值，退化则 `declared` + 标记 + `null`。
    """
    terminal = set(_ledger_policy()["terminal"])
    if run.get("status") not in terminal:
        run["measurement_source"] = "unknown"
        run["measurement_flags"] = []
        run["dur_minutes"] = None
        return
    source, flags, mins = measurement_of(run.get("started_at"), run.get("ended_at"))
    run["measurement_source"] = source
    run["measurement_flags"] = flags
    run["dur_minutes"] = mins


@contextlib.contextmanager
def _file_lock(lock_path: Path):
    """通用文件互斥锁（M10/M9）：注册表与价表共用同一模式（msvcrt/fcntl 双平台）。
    锁超时（~10s）以友好文案退出，不裸 traceback。"""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as fh:
        try:
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            raise SystemExit(f"锁获取超时：{lock_path} 被另一进程占用（并发写账本/价表）——稍后重试") from None
        try:
            yield
        finally:
            if os.name == "nt":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _registry_lock():
    """账本互斥锁（M10，2026-08-31）：register/update/finish 的 load→mutate→save
    全过程持锁，杜绝两个进程读同一快照后先后写回造成的 last-writer-wins 丢失更新。"""
    with _file_lock(RUNTIME_DIR / ".registry.lock"):
        yield


@contextlib.contextmanager
def _prices_lock():
    """价表互斥锁（Sprint-14 二查 035）：prices-derive 与 fetch-prices --apply 对同一
    prices.json 做 load→merge→save，必须同锁（否则 last-writer-wins 丢段落）。"""
    with _file_lock(RUNTIME_DIR / ".prices.lock"):
        yield


def _with_registry_lock(fn):
    """写命令装饰器：整条命令（含异常路径）都在锁内执行，异常自动释放锁。

    `functools.wraps`（2026-09-21 关闭三查·二查 major）：保留 `__wrapped__` 与函数元信息，
    使"某子命令是否真的走了加锁路径"可以被回归断言直接自检（`round`/`interrupt` 曾漏加锁）。
    """

    @functools.wraps(fn)
    def wrapper(args: argparse.Namespace):
        with _registry_lock():
            return fn(args)

    return wrapper


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        # review 修正（Sprint-8 三查）：存在但缺 integrity 键 = 手造文件 → 拒绝
        if not data.get("integrity"):
            raise SystemExit("registry.json 缺少完整性字段：疑似手工创建（防双写）。请用 agent-ops CLI 写入。")
    else:
        data = {"version": 1, "runs": []}
    # UC-7：加载时校验完整性（手改即拒，防双写）——必须在任何变更前检查
    if data.get("integrity") and _integrity(data) != data["integrity"]:
        raise SystemExit("registry.json 完整性校验失败：疑似被手工修改（防双写）。请用 agent-ops CLI 写入。")
    return data


def _integrity(data: dict) -> str:
    return _sha256(json.dumps(data["runs"], ensure_ascii=False, sort_keys=True))


def _save_registry(data: dict) -> None:
    """**原子**写账本（2026-09-21 关闭三查·二查 major）：先写同目录临时文件再 `os.replace`。

    原实现直接 `write_text`（截断 + 写入），并发写或写入中途被打断会留下**截断的 registry.json**
    （账本=唯一真相源，截断即数据损坏）。`os.replace` 在同一文件系统内是原子的：读者要么看到旧文件、
    要么看到完整新文件。配合 `_registry_lock` 使用。
    """
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    data["integrity"] = _integrity(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, REGISTRY_PATH)


def _find_run(data: dict, run_id: str) -> dict:
    for r in data["runs"]:
        if r["run_id"] == run_id:
            return r
    raise SystemExit(f"run {run_id} 不存在")


def _load_prices() -> dict:
    if PRICES_PATH.exists():
        return json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    return {"auto": {}, "manual": {}}


def _prices_for(model: str) -> dict | None:
    """review 修正（Sprint-8 三查）：manual 非 null 时**覆盖** auto（README 契约），auto 为兜底。
    M9（2026-08-31）：新增 scraped 段（官网固定 URL 抓取，fetch-prices.py）——
    优先级 manual（非 null）> scraped > auto；manual 永不被抓取覆盖。"""
    p = _load_prices()
    manual = p.get("manual", {}).get(model)
    if manual:  # 非 null 的人工价优先
        return manual
    for prov in p.get("scraped", {}).values():
        if isinstance(prov, dict) and model in prov.get("models", {}):
            # 注（035）：同名模型跨 provider 冲突时取首个命中；当前各 provider 模型名
            # 带命名空间/前缀（deepseek/deepseek-v4-flash vs deepseek-v4-flash），无实际碰撞。
            return prov["models"][model]
    return p.get("auto", {}).get(model)


def _fx_usd_cny() -> float:
    """用户决策（2026-08-30）：价格以 RMB 计。价表单价为 USD/token，按 meta.fx_usd_cny 换算（可人工覆盖）。"""
    try:
        return float(_load_prices().get("meta", {}).get("fx_usd_cny", 7.2))
    except (TypeError, ValueError):
        return 7.2


def _estimate_cost(entry: dict) -> dict:
    """UC-4：usage x 价表；无 usage 用 chars/4 兜底；无价表标 pending_price。
    输出单位 = CNY（USD 单价 × meta.fx_usd_cny 换算，用户决策 2026-08-30）。"""
    usage = entry.get("usage") or {}
    model = entry.get("model") or ""
    prices = _prices_for(model)
    if not prices:
        return {"total": None, "currency": "CNY", "estimated": True, "pending_price": True, "model": model}
    cost = {
        "input": (usage.get("input_tokens") or 0) * (prices.get("input_cost_per_token") or 0),
        "output": (usage.get("output_tokens") or 0) * (prices.get("output_cost_per_token") or 0),
        "cache_read": (usage.get("cache_read_tokens") or 0) * (prices.get("cache_read_input_token_cost") or 0),
        "cache_write": (usage.get("cache_write_tokens") or 0) * (prices.get("cache_creation_input_token_cost") or 0),
    }
    estimated = False
    if not any(usage.values()):
        ic = entry.get("input_chars") or 0
        oc = entry.get("output_chars") or 0
        cost["input"] = (ic / _CHARS_PER_TOKEN) * (prices.get("input_cost_per_token") or 0)
        cost["output"] = (oc / _CHARS_PER_TOKEN) * (prices.get("output_cost_per_token") or 0)
        estimated = True
    fx = _fx_usd_cny()
    # review 修正（Sprint-9 三查 P1）：分项同样 ×fx 转 CNY，保证分项之和 = total（此前分项仍为 USD、对象级却标 CNY，口径不一致）
    cny = {k: round(v * fx, 8) for k, v in cost.items()}
    return {**cny, "total": round(sum(cny.values()), 8), "currency": "CNY",
            "estimated": estimated, "pending_price": False, "model": model}


def parse_scope_ref(source: str, prefixes: tuple[str, ...]) -> str | None:
    """从 `--scope-source` 里解析出被引用的 run_id（**纯函数**，供断言直接驱动）。

    识别规则取自政策数据 `scope_ref_sources`（如 `"impact-assessment:"`）。刻意**不硬编码**
    "引用〇查"：C2 不变式要求"任何外部引用必须解析到存在且终态可用的对象，**不认角色名**"——
    因此这里只认前缀契约，被引用对象是什么角色由 `_validate_scope` 查账本后判定。
    """
    for prefix in prefixes:
        if source.startswith(prefix):
            return source[len(prefix):].strip()
    return None


def _validate_scope(args: argparse.Namespace, data: dict) -> tuple[str, str | None]:
    """TG-11 闸门（TG-15 起数据驱动）：评审类 run 的 scope 来源必须**机器可验**（fail-closed）。

    - `--scope-source <prefix><run_id>`：该 run 必须在账本中存在、其 spec 必须声明可作 scope 来源，
      且状态不为 failed/cancelled（否则其 scope 不可采信）；
    - 自选范围（未给 scope-source，或给了 `self-chosen`）：必须给 `--deviation "<理由>"`
      （长度下限取自 `agents/policy.json::scope_min_deviation_chars`），理由落库留痕；
    - 非评审类 role：不强制、不制造假红。
    """
    source = (getattr(args, "scope_source", "") or "").strip()
    deviation = (getattr(args, "deviation", "") or "").strip()
    pol = policy()
    if args.role not in pol.review_roles:
        return source, (deviation or None)
    ref = parse_scope_ref(source, pol.scope_ref_sources)
    if ref is not None:
        target = next((r for r in data["runs"] if r["run_id"] == ref), None)
        if target is None:
            raise SystemExit(f"scope 来源指向不存在的 run：{ref!r}（fail-closed，C2 指涉可核）")
        # C2：被引用对象必须"存在且处于可用终态"——不认角色名，只认账本事实 + spec 声明
        if target.get("role") not in pol.specs:
            raise SystemExit(
                f"scope 来源 {ref} 的 role={target.get('role')!r} 没有对应 spec（fail-closed，C2）")
        if target.get("status") in _non_credible_statuses():
            raise SystemExit(
                f"scope 来源 {ref} 状态为 {target.get('status')}，其 scope 不可采信（fail-closed）")
        return source, (deviation or None)
    if not deviation:
        raise SystemExit(
            "评审类 run 必须声明 scope 来源：--scope-source "
            + " 或 ".join(pol.scope_ref_sources)
            + "<run_id>；确需自选范围时必须给 --deviation \"<理由>\"（TG-11 闸门，fail-closed；"
              "角色清单与阈值来自 agents/policy.json + spec frontmatter，见 TG-15）")
    if len(deviation) < pol.scope_min_deviation_chars:
        raise SystemExit(
            f"--deviation 理由过短（{len(deviation)} < {pol.scope_min_deviation_chars} 字符）："
            "请说明为何偏离〇查范围")
    return (source or "self-chosen"), deviation



@_with_registry_lock
def cmd_register(args: argparse.Namespace) -> None:
    data = _load_registry()
    # review 修正（Sprint-8 三查）：显式 run_id 查重（_find_run 只命中第一条）
    if any(r["run_id"] == args.run_id for r in data["runs"]):
        raise SystemExit(f"run_id {args.run_id} 已存在，请更换")
    run_id = args.run_id or f"run-{_local_date()}-{args.role}-{len(data['runs']) + 1:03d}"
    # review 修正（Sprint-9 三查 P2）：run-id 将成为 runs/ 下的目录名，限字符集防路径穿越
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise SystemExit(f"run_id 含非法字符（仅允许字母数字 . _ -）：{run_id!r}")
    scope_source, scope_deviation = _validate_scope(args, data)
    # TG-15 ③ 锚点自动化：run 登记时自动记覆盖锚点（= 登记时的 HEAD），无需人往 Sprint 文档手抄。
    # `--coverage-anchor` 可显式覆盖（补录历史 run / fixture）；非 git 环境回落空串（不阻断记账）。
    pol = policy()
    spec = pol.specs.get(args.role)
    coverage_window = None
    if spec is not None:
        fm = parse_frontmatter(spec.path)
        coverage_window = (fm.get("coverage_window") or "").strip() or None
    raw_anchor = (getattr(args, "coverage_anchor", "") or "").strip()
    if raw_anchor:
        # 审核 F1/N5：显式锚点必须**规范化**（短 sha → 完整 40 位），解析失败 fail-closed
        resolved = _resolve_sha(raw_anchor)
        if not resolved:
            raise SystemExit(
                f"COVERAGE-ANCHOR-ERROR: --coverage-anchor {raw_anchor!r} 无法解析为提交"
                "（短 sha 会让覆盖窗口被静默丢弃，故 fail-closed）")
        coverage_anchor = resolved
    else:
        coverage_anchor = _git_head()
    entry = {
        "run_id": run_id,
        "task_id": args.task or "",
        "role": args.role,
        "spec_source": args.spec,
        "scope_source": scope_source,
        "scope_deviation": scope_deviation,
        # TG-15：覆盖窗口为**自动记录**字段；covered(run) = (coverage_anchor, covers_through]
        "coverage_anchor": coverage_anchor,
        "coverage_window": coverage_window,
        "covers_through": None,
        "model": args.model or "",
        "status": "running" if args.start else "queued",
        "started_at": _now() if args.start else None,
        "ended_at": None,
        "input_chars": args.input_chars or 0,
        "output_chars": 0,
        "usage": {},
        "context_occupancy": {
            "input_tokens": args.context_input_tokens or 0,
            "max_context": args.context_max_tokens or 0,
            "ratio": round((args.context_input_tokens / args.context_max_tokens), 4)
            if args.context_input_tokens and args.context_max_tokens else 0.0,
        },
        "cost_est": {"total": None, "currency": "CNY", "estimated": True},
        "result_files": [],
        "tags": {},
        "error": None,
    }
    # TG-13：测量来源（此刻只有 started_at、没有 ended_at → unknown，禁止写 0.00 冒充测量值）
    _apply_measurement(entry)
    data["runs"].append(entry)
    _save_registry(data)
    print(f"registered {run_id} (status={entry['status']})")


def _apply_usage(r: dict, args: argparse.Namespace) -> None:
    usage = r.setdefault("usage", {})
    for key, val in (("usage_in", "input_tokens"), ("usage_out", "output_tokens"),
                     ("usage_cache_read", "cache_read_tokens"), ("usage_cache_write", "cache_write_tokens")):
        v = getattr(args, key)
        if v is not None:
            usage[val] = v


@_with_registry_lock
def cmd_update(args: argparse.Namespace) -> None:
    data = _load_registry()
    r = _find_run(data, args.run_id)
    if args.status:
        # review 修正（Sprint-8 三查）：update 只能进入 running；终态一律走 finish
        # （否则 update --status succeeded 会产出 ended_at/cost_est 缺失的畸形行）
        if args.status != "running":
            raise SystemExit("update 只允许 --status running；终态请用 finish 子命令")
        allowed = _transitions().get(r["status"], set())
        if args.status not in allowed:
            raise SystemExit(f"非法流转 {r['status']} -> {args.status}（允许：{sorted(allowed) or '无'}）")
        r["status"] = args.status
        if not r["started_at"]:
            r["started_at"] = _now()
    _apply_usage(r, args)
    _apply_measurement(r)  # TG-13：时间戳变了就刷新测量来源/时长（仍是 running → unknown）
    _save_registry(data)
    print(f"updated {args.run_id} (status={r['status']})")


@_with_registry_lock
def cmd_set_anchor(args: argparse.Namespace) -> None:
    """受控回填：修正**已登记** run 的 `coverage_anchor`（审核 N5/F1 要求的口子）。

    约束：必须给 `--reason`（≥10 字符：谁修、为什么、依据哪条审核发现）；sha 必须可解析并规范化；
    每次回填追加一条 `anchor_backfills` 记录（可审计，不是静默改数）。
    """
    data = _load_registry()
    r = _find_run(data, args.run_id)
    resolved = _resolve_sha(args.anchor)
    if not resolved:
        raise SystemExit(f"COVERAGE-ANCHOR-ERROR: {args.anchor!r} 无法解析为提交（fail-closed）")
    reason = (args.reason or "").strip()
    if len(reason) < 10:
        raise SystemExit("回填必须给 --reason（≥10 字符的理由）：谁修、为什么、依据哪条审核发现")
    old = r.get("coverage_anchor")
    r["coverage_anchor"] = resolved
    r.setdefault("anchor_backfills", []).append(
        {"at": _now(), "from": old, "to": resolved, "reason": reason, "by": args.by})
    _save_registry(data)
    print(f"anchor updated {r['run_id']}: {str(old or '')[:8] or 'none'} -> {resolved[:8]} "
          f"(backfills={len(r['anchor_backfills'])})")


@_with_registry_lock
def cmd_finish(args: argparse.Namespace) -> None:
    data = _load_registry()
    r = _find_run(data, args.run_id)
    if args.status not in _terminal():
        raise SystemExit("finish 需要终态：{}".format(sorted(_terminal())))
    # review 修正（Sprint-8 三查）：finish 仅允许 running -> terminal（queued 先 update running）
    if r["status"] != "running":
        raise SystemExit(f"非法流转 {r['status']} -> {args.status}（finish 仅允许 running -> terminal）")
    r["status"] = args.status
    r["ended_at"] = _now()
    # TG-15 ③：收尾时记录覆盖上界（= 收尾时的 HEAD）——此前"三查锚点"要人往 Sprint 文档手抄，
    # 抄漏/抄错没有任何装置能发现；改为 run 自动记录后，闸门直接读账本，文档不再是覆盖真源。
    raw_through = (getattr(args, "covers_through", "") or "").strip()
    if raw_through:
        resolved_through = _resolve_sha(raw_through)
        if not resolved_through:
            raise SystemExit(
                f"COVERAGE-ANCHOR-ERROR: --covers-through {raw_through!r} 无法解析为提交（fail-closed）")
        r["covers_through"] = resolved_through
    else:
        r["covers_through"] = _git_head() or r.get("covers_through")

    if args.output_chars is not None:
        r["output_chars"] = args.output_chars
    if args.error:
        r["error"] = args.error
    _apply_usage(r, args)
    if args.result_file:
        rel = Path(args.result_file)
        r["result_files"] = [str(rel)]
        if rel.exists():
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            dest = RUNS_DIR / r["run_id"] / f"{r['role']}.report.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            # 审核 N10（2026-09-25）：**按字节复制**，不得改写换行。
            # 原实现是 `dest.write_text(rel.read_text(encoding="utf-8"), encoding="utf-8")`：
            # `read_text` 做 universal-newline 转换（CRLF→LF），`write_text` 又把 `\n` 写回
            # `os.linesep`（Windows = CRLF）——于是**仓库基线 LF 的报告被静默改成 CRLF**
            # （实测 35721 B → 35913 B / 192 行）。这与 D1 的 EOL 事故同族（`2206f376` 修过
            # 同一族的另一处，漏了这里），而且是"最不该动字节"的一步：归档动作改变了产物本身。
            # 复制实现按字节，源是 LF 就存 LF、源是 CRLF 就存 CRLF（不反向破坏），BOM 亦原样保留。
            dest.write_bytes(rel.read_bytes())
            # review 修正（Sprint-8 三查）：基准用 _AGENTS_BASE（AGENT_OPS_DIR 重定向时不再崩溃）
            r["result_files"] = [str(dest.relative_to(_AGENTS_BASE))]
    if args.cost_override is not None:
        r["cost_est"] = {"total": args.cost_override, "currency": "CNY", "estimated": False, "override": True}
    else:
        r["cost_est"] = _estimate_cost(r)
    # TG-13：终态 → 算测量值（可测 = wall-clock + dur_minutes；退化 = declared + 标记 + null）
    _apply_measurement(r)
    _save_registry(data)
    flags = ",".join(r.get("measurement_flags") or [])
    print(f"finished {args.run_id} -> {r['status']} (cost_est={r['cost_est']})"
          f" dur={r.get('dur_minutes')} min msrc={r.get('measurement_source')}"
          + (f" ⚠退化={'+'.join(r['measurement_flags'])}"
             "（该时长不是测量值，闸门会对新 run 判 FAIL，请检查时钟/时间戳来源）" if flags else ""))


@_with_registry_lock
def cmd_round(args: argparse.Namespace) -> None:
    """TG-10①：给同一 run **追加轮次**记录（多轮复核/追加验证），不改首轮语义。

    背景（用户 2026-09-21 疑虑："每个 agent 运行时间相比之前怎么短了很多…让我不太安心"）：
    run-053 被追加了 4 个复核轮次（报告 60 KB / 5 轮、实际跨约 4h53m），但账本只留**首轮**
    （`ended_at-started_at` = 53 秒、`output_chars` = 12800）——因为 `finish` 的状态机拒绝
    `succeeded→succeeded`，后续轮次无处回写 → 看板显示的时长与产出**严重低估**，且看不出被中断过。

    本子命令做**追加式**更新（允许对终态 run 使用）：
    - 首次追加时把当前记录快照为 `rounds[0]`（保留首轮 ended_at/output_chars 作为历史）；
    - 每轮追加 `{round, ended_at, note, output_chars, interrupted}`；
    - `ended_at` 更新为末轮时间（于是 `ended_at-started_at` ≈ **累计墙钟时长**）、
      `output_chars` **累加**、`rounds_count` = 轮次数。
    """
    data = _load_registry()
    r = _find_run(data, args.run_id)
    now = _now()
    rounds = r.setdefault("rounds", [])
    if not rounds:
        rounds.append({
            "round": 1,
            "ended_at": r.get("ended_at"),
            "note": "initial（finish 时记录）",
            "output_chars": r.get("output_chars") or 0,
            "usage": r.get("usage") or {},
        })
    n = len(rounds) + 1
    entry = {
        "round": n,
        "ended_at": now,
        "note": args.note or "",
        "output_chars": args.output_chars,
        "interrupted": bool(args.interrupted),
    }
    if args.usage_in is not None or args.usage_out is not None:
        entry["usage"] = {"input_tokens": args.usage_in or 0, "output_tokens": args.usage_out or 0}
    rounds.append(entry)
    if args.output_chars:
        r["output_chars"] = int(r.get("output_chars") or 0) + int(args.output_chars)
    r["ended_at"] = now
    r["rounds_count"] = n
    # TG-13：追加轮次把 ended_at 前移 → `dur` 必须随之刷新（累计墙钟口径），
    # 否则账本就是"记了轮次但没测量时长"（TG-10 的 53 秒 vs 4h53m 正是这个形态）。
    _apply_measurement(r)
    if args.interrupted:
        evs = r.setdefault("interruptions", [])
        evs.append({
            "at": now,
            "by": args.by or "main-agent",
            "reason": args.note or "",
            "impact": args.impact or "",
        })
        r["interruptions_count"] = len(evs)
    _save_registry(data)
    print(f"appended round {n} to {args.run_id} (rounds_count={n}, output_chars={r['output_chars']}, "
          f"ended_at={r['ended_at']}, dur={r.get('dur_minutes')} min msrc={r.get('measurement_source')})")


@_with_registry_lock
def cmd_interrupt(args: argparse.Namespace) -> None:
    """TG-10②：记录一次**中断/接管**事件（何时、谁、为什么、影响范围）。

    依据 `1-WORKFLOW.MD` §4.2："主代理中断/杀进程/接管子代理必须留痕"——2026-09-20 我中断复核者
    1 次、误杀其派生进程 3 次，当时**账本与看板完全看不出**（这正是用户不安的来源）。
    """
    data = _load_registry()
    r = _find_run(data, args.run_id)
    evs = r.setdefault("interruptions", [])
    evs.append({
        "at": _now(),
        "by": args.by or "main-agent",
        "reason": args.reason or "",
        "impact": args.impact or "",
    })
    r["interruptions_count"] = len(evs)
    _save_registry(data)
    print(f"logged interruption #{len(evs)} on {args.run_id}: {args.reason}")


def cmd_list(args: argparse.Namespace) -> None:
    data = _load_registry()
    rows = data["runs"]
    if args.status:
        rows = [r for r in rows if r["status"] == args.status]
    if args.role:
        rows = [r for r in rows if r["role"] == args.role]
    if args.limit:
        rows = rows[-args.limit:]
    for r in rows:
        rounds = r.get("rounds_count") or len(r.get("rounds") or []) or 1
        # TG-13 展示口径：**缺值必须显式 unknown**——无墙钟读数就打印 `dur=unknown`，
        # 不得留空、更不得回落 `dur=0.0`（0.0 会被读成"零耗时"）。退化读数同样标 unknown
        # 并把退化原因写在 flags 里（原始时间戳仍在行内，可复核）。
        source = str(r.get("measurement_source") or "")
        flags = r.get("measurement_flags") or []
        if source == "wall-clock":
            mins = _duration_minutes(r.get("started_at") or "", r.get("ended_at") or "")
            dur = f" dur={mins:.1f}m" if mins is not None else " dur=unknown"
        else:
            dur = " dur=unknown" + (f"(!{'+'.join(flags)})" if flags else "")
        if source:
            dur += f" msrc={source}"
        intr = f" int={r['interruptions_count']}" if r.get("interruptions_count") else ""
        # TG-11：scope 来源必须一眼可见——自选范围（self-chosen）在 list 里高亮标记，便于审计
        src = (r.get("scope_source") or "").strip()
        if src == "self-chosen":
            scope = " scope=self-chosen(!)"
        elif src:
            scope = f" scope={src}"
        elif r.get("role") in _review_roles():
            scope = " scope=(missing!)"
        else:
            scope = ""
        # TG-15：覆盖窗口（锚点自动化）——短 sha 便于审计，缺字段标 none 而不是留空
        cov = ""
        if r.get("coverage_window"):
            anchor = (r.get("coverage_anchor") or "")[:8] or "none"
            through = (r.get("covers_through") or "")[:8] or "open"
            cov = f" cov={anchor}..{through}"
        print(f"{r['run_id']:30s} {r['role']:20s} {r['status']:10s} "
              f"cost={r.get('cost_est', {}).get('total')} spec={r['spec_source']} rounds={rounds}{dur}{intr}{scope}{cov}")
    print(f"--- {len(rows)} runs ---")


_ANCHOR_RE = re.compile(r"\**三查锚点\**\s*[:：]\s*`?([0-9a-fA-F]{7,40})`?")


def cmd_close_sync(args: argparse.Namespace) -> None:
    """TG-15 ⑤：生成 C3 覆盖候选行——把"人肉判断哪个提交没被覆盖"变成机器给清单、人只挑类别。

    输出（不写盘，除非 `--write`）：
      ① 每个 run 的覆盖窗口（账本自动记录）；
      ② 锚点→HEAD 每个提交的归属（run 窗口 / 例外 / doc-only 自动归类 / **UNOWNED**）；
      ③ 未归属提交的候选例外 JSON 片段（`doc-only` 已自动归类，其余待人选类别 + 写理由）。

    `--fail-on-unowned` 时存在未归属提交即退出 1（供 CI/关闭前置使用）。
    """
    doc = Path(args.sprint)
    if not doc.is_file():
        raise SystemExit(f"CLOSE-SYNC-ERROR: Sprint 文档不存在：{doc}（fail-closed）")
    text = doc.read_text(encoding="utf-8", errors="replace")
    m = _ANCHOR_RE.search(text)
    if not m:
        raise SystemExit(
            "CLOSE-SYNC-ERROR: Sprint 文档未声明 `三查锚点: <sha>`（fail-closed）。"
            "TG-15 ③ 起锚点由 run 自动记录，但**关闭判定**仍需一个显式锚点：先在 §9.1 写入二查覆盖到的 HEAD。")
    anchor = m.group(1)
    head = _git_head()
    pol = policy()
    data = _load_registry()
    exc_path = REPO_ROOT / pol.close_gate["coverage"]["exceptions_file"]
    from verify.agent_policy import attribution, load_coverage_exceptions

    exceptions = load_coverage_exceptions(exc_path)
    att = attribution(REPO_ROOT, anchor, head, data.get("runs", []), exceptions, policy=pol)
    globs = tuple(pol.close_gate["coverage"].get("doc_only_globs") or ())

    print(f"close-sync: anchor={anchor[:10]} head={head[:10]} commits={len(att.shas)} "
          f"windows={len(att.windows)} exceptions={len(att.exceptions)}")
    for line in att.report_lines(globs):
        print("  " + line)

    # 2026-09-23 二查 critical：**零提交受检不得报"闭环 ✔"**。锚点 == HEAD 时区间为空集，
    # unowned 必为空——旧实现照样打勾、rc=0，而 §9.1 的占位文案正引导人这么填。
    structural = att.window_problems()
    if structural:
        print("\n窗口结构问题（这些都会让自动覆盖静默失效）：")
        for line in structural[:10]:
            print("  ! " + line)
    if att.empty_interval():
        print(f"\n覆盖闭环：**未验证**——锚点 {anchor[:10]} 与 HEAD {head[:10]} 之间没有任何提交。"
              "这不算通过：请把锚点填成二查实际覆盖到的提交，或写明本 Sprint 无需覆盖检查的理由。")
        raise SystemExit(2)

    unowned = att.unowned(globs)
    doconly = [s for s in att.shas if att.owner(s, globs) == "doc-only"]
    if doconly:
        print(f"\n自动归类 doc-only（改动文件全部命中 doc_only_globs，{len(doconly)} 个）：")
        from verify.agent_policy import commit_subject as _subject

        for sha in doconly[:10]:
            print(f"  {sha[:10]}  {_subject(REPO_ROOT, sha)[:70]}")
    if unowned:
        from verify.agent_policy import commit_subject

        candidates = [
            {"sha": sha, "class": "CHANGE-CLASS?", "reason": "",
             "subject": commit_subject(REPO_ROOT, sha), "files": att.files_of(sha)[:5]}
            for sha in unowned
        ]
        print(f"\n未归属提交 {len(unowned)} 个 → 候选例外（人只挑 class + 写 reason）：")
        print(json.dumps({"rules": candidates}, ensure_ascii=False, indent=2))
        if args.write:
            out = REPO_ROOT / "agents" / "runtime" / "coverage-candidates.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"anchor": anchor, "head": head, "rules": candidates},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n已写出候选：{out}")
    else:
        print("\n覆盖闭环：锚点→HEAD 的每个提交都有归属 ✔")

    if args.fail_on_unowned and unowned:
        raise SystemExit(1)



def cmd_validate_spec(args: argparse.Namespace) -> None:
    """UC-1：spec frontmatter 必填 name(=文件名)+description+version；source 块字段合法。"""
    p = Path(args.spec_file)
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        raise SystemExit("FAIL: 缺少 YAML frontmatter")
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    for field in ("name", "description", "version"):
        if not fm.get(field):
            raise SystemExit(f"FAIL: 缺少必填字段 {field}")
    if fm["name"] != p.stem:
        raise SystemExit(f"FAIL: name={fm['name']!r} 与文件名 {p.stem} 不一致")
    if "source" in fm:
        for f in ("url", "ref", "sha256", "fallback"):
            if f not in fm:
                raise SystemExit(f"FAIL: source 块缺 {f}")
    print(f"PASS: {p.name} frontmatter 合法（name={fm['name']} v{fm['version']}）")


def _match_sha256(text: str, want_sha: str) -> bool:
    """sha256 比对（M10，2026-08-31 抽出为纯函数：成功路径受 SSRF 防护无法离线走
    网络，抽出后由 verify_agentops UC-11 进程内断言命中/失配两分支）。"""
    return _sha256(text) == want_sha


def cmd_fetch_spec(args: argparse.Namespace) -> None:
    """UC-2：依 source 块远程拉取（锁 ref + sha256 校验）；--offline 或失败 → 回退本地并告警。"""
    p = Path(args.spec_file)
    text = p.read_text(encoding="utf-8")
    m = re.search(r"^source:\s*\n(?:^\s+(\w+):\s*(.+)$\s*)+", text, re.M)
    if not m:
        print(f"no source block in {p.name}; using local spec")
        return
    src = {
        k.strip(): v.strip().strip('"').strip("'")
        for k, v in (re.findall(r"^  (\w+):\s*(.+)$", m.group(0), re.M))
    }
    url = src.get("url", "")
    want_sha = src.get("sha256", "")
    if not url:
        print(f"WARN: 无 url → 回退本地 spec {p.name}")
        return
    if args.offline:
        print(f"WARN: offline/无 url → 回退本地 spec {p.name}")
        return
    # TG-8②：**离线开关**（政策 `agents/policy.json::offline_switch`）在"确实要外呼"这一刻生效。
    # 顺序理由（可核，不是风格）：上面两个分支都**不产生外呼**（无 url / 命令自带 `--offline`），
    # 对它们报"离线拒绝"是假红；而一旦要继续走网络，全局开关就必须优先于 `--offline`
    # ——否则"命令自带的局部离线档"会把全局开关**静默绕过**，而那正是本卡要消灭的形态。
    # 拒绝还必须在 SSRF 校验**之前**：否则内网 URL 会先撞 SSRF 分支，拒绝原因被替换成 SSRF，
    # 排障时会以为"是 URL 的问题"而不是"开关开着"。
    refuse_or_exit(f"fetch-spec {url}")
    # review 修正（Sprint-8 三查）：SSRF 防护——仅 http/https + 拒绝私网/回环/链路本地/保留地址
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(f"WARN: 非法 scheme {parsed.scheme!r} → 回退本地 spec {p.name}")
        return
    try:
        import ipaddress

        host = parsed.hostname or ""
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            print(f"WARN: 目标地址 {host} 为私网/保留地址（SSRF 防护）→ 回退本地 spec {p.name}")
            return
    except ValueError:
        pass  # 域名形式：交给 DNS 解析（不额外校验）
    ref = src.get("ref", "")
    fetch_url = url.replace("{ref}", ref) if "{ref}" in url else url
    if "{ref}" not in url and ref:
        print(f"NOTE: ref={ref!r} 为声明性锁定（URL 未含 {{ref}} 占位），以 sha256 校验为准")
    try:
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "agent-ops"})
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            remote = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: 拉取失败（{type(exc).__name__}: {exc}）→ 回退本地 spec {p.name}")
        return
    if not _match_sha256(remote, want_sha):
        print(f"WARN: sha256 校验不符 → 回退本地 spec {p.name}")
        return
    print(f"OK: remote spec fetched & verified ({fetch_url} @ {ref or '?'})")


def cmd_parse_report(args: argparse.Namespace) -> None:
    """UC-5：解析 spec 输出模板（`- critical <位置>：<问题>` 行）为结构化 JSON。

    review 修正（Sprint-8 三查）：位置以**首个全角冒号**切分（ASCII `:` 保留在 where 内，
    使 `engine.py:202` 这类 file:line 位置不被截断）。
    """
    p = Path(args.report_file)
    items = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(?:\*|-)\s*\**(critical|major|minor|nit)\**[ \t]+([^：]+)[：]\s*(.+)$", line, re.I)
        if m:
            items.append({"level": m.group(1).lower(), "where": m.group(2).strip(), "text": m.group(3).strip()})
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"--- parsed {len(items)} findings ---")


def _derive_prices(args: argparse.Namespace | None = None) -> None:
    """UC-10：从 litellm 捆绑价表派生 prices.json（人工覆盖段保留）。"""
    prices = _load_prices()
    auto = {}
    litellm_json = None
    for base in [Path(p) for p in sys.path if p]:
        cand = base / "litellm" / "model_prices_and_context_window_backup.json"
        if cand.exists():
            litellm_json = cand
            break
    if litellm_json:
        table = json.loads(litellm_json.read_text(encoding="utf-8"))
        for model in ("gpt-4o-mini", "text-embedding-3-large"):
            src = table.get(model, {})
            auto[model] = {k: src.get(k) for k in
                           ("max_input_tokens", "input_cost_per_token", "output_cost_per_token",
                            "cache_read_input_token_cost", "cache_creation_input_token_cost")}
    else:
        print("WARN: 未找到 litellm 价表，仅保留人工覆盖段")
    out = {"auto": auto, "manual": prices.get("manual", {}),
           "scraped": prices.get("scraped", {}),  # M9：派生不丢弃官网抓取段
           "meta": prices.get("meta", {"currency": "USD", "fx_usd_cny": 7.2})}
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with _prices_lock():  # 035：与 fetch-prices --apply 互斥
        # write_bytes：LF 字节写盘（1.47——文本模式在 Windows 会把 \n 翻成 \r\n）
        PRICES_PATH.write_bytes(json.dumps(out, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"prices.json 已派生：auto={sorted(auto)} manual={sorted(out['manual'])}")


def main() -> int:
    # review 修正（Sprint-8 三查）：跨 IDE 承诺——Windows 非 UTF-8 终端打印中文不乱码/不崩
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    ap = argparse.ArgumentParser(description="AgentOps 账本 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register")
    p.add_argument("--role", required=True)
    p.add_argument("--task", default="")
    p.add_argument("--spec", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--start", action="store_true")
    p.add_argument("--input-chars", type=int)
    p.add_argument("--context-input-tokens", type=int)
    p.add_argument("--context-max-tokens", type=int)
    p.add_argument("--run-id", default="")
    p.add_argument("--scope-source", default="",
                   help="TG-11：评审类 run 的 scope 来源，形如 impact-assessment:<run_id>")
    p.add_argument("--deviation", default="",
                   help="TG-11：自选/偏离〇查范围的理由（评审类 run 缺 scope-source 时必填）")
    p.add_argument("--coverage-anchor", default="",
                   help="TG-15：覆盖窗口下界 sha（默认 = 登记时的 HEAD，自动记录）")

    p = sub.add_parser("update")
    p.add_argument("run_id")
    p.add_argument("--status", choices=["running"])  # 终态一律走 finish（三查修正）
    p.add_argument("--usage-in", type=int)
    p.add_argument("--usage-out", type=int)
    p.add_argument("--usage-cache-read", type=int)
    p.add_argument("--usage-cache-write", type=int)

    p = sub.add_parser("finish")
    p.add_argument("run_id")
    p.add_argument("--status", required=True, choices=sorted(_terminal()))
    p.add_argument("--output-chars", type=int)
    p.add_argument("--result-file")
    p.add_argument("--cost-override", type=float)
    p.add_argument("--error", default="")
    p.add_argument("--usage-in", type=int)
    p.add_argument("--usage-out", type=int)
    p.add_argument("--usage-cache-read", type=int)
    p.add_argument("--usage-cache-write", type=int)
    p.add_argument("--covers-through", default="",
                   help="TG-15：覆盖窗口上界 sha（默认 = 收尾时的 HEAD，自动记录）")

    p = sub.add_parser("list")
    p.add_argument("--status")
    p.add_argument("--role")
    p.add_argument("--limit", type=int)

    p = sub.add_parser("round", help="TG-10①：给同一 run 追加轮次记录（允许对终态 run 使用）")
    p.add_argument("run_id")
    p.add_argument("--note", default="", help="本轮做了什么（如 'Round 5：F-AC16/M18 v1 复核'）")
    p.add_argument("--output-chars", type=int, default=0, help="本轮产出字符数（累加到 run 总计）")
    p.add_argument("--interrupted", action="store_true", help="本轮是否被中断（同时写一条 interruption 事件）")
    p.add_argument("--by", default="main-agent")
    p.add_argument("--impact", default="", help="中断影响范围（哪一轮评审/验证缺失、如何补做）")
    p.add_argument("--usage-in", type=int)
    p.add_argument("--usage-out", type=int)

    p = sub.add_parser("interrupt", help="TG-10②：记录一次中断/接管事件（何时/谁/为什么/影响）")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)
    p.add_argument("--impact", default="")
    p.add_argument("--by", default="main-agent")

    p = sub.add_parser("close-sync",
                       help="TG-15⑤：生成 C3 覆盖候选（未归属提交 + 改动文件 + doc-only 自动归类）")
    p.add_argument("--sprint", required=True, help="当前 Sprint 文档路径（读其中的 `三查锚点: <sha>`）")
    p.add_argument("--write", action="store_true", help="把候选例外写到 agents/runtime/coverage-candidates.json")
    p.add_argument("--fail-on-unowned", action="store_true", help="存在未归属提交即退出 1（CI/关闭前置）")

    p = sub.add_parser("set-anchor", help="审核 N5/F1：受控回填已登记 run 的 coverage_anchor（必须给理由）")
    p.add_argument("run_id")
    p.add_argument("--anchor", required=True, help="新锚点（短 sha 会被规范化为完整 40 位；无法解析则拒绝）")
    p.add_argument("--reason", required=True, help="回填理由（≥10 字符）：谁修、为什么、依据哪条审核发现")
    p.add_argument("--by", default="main-agent")
    p = sub.add_parser("validate-spec")
    p.add_argument("spec_file")
    p = sub.add_parser("fetch-spec")
    p.add_argument("spec_file")
    p.add_argument("--offline", action="store_true")
    p = sub.add_parser("parse-report")
    p.add_argument("report_file")
    sub.add_parser("prices-derive")

    args = ap.parse_args()
    {
        "register": cmd_register, "update": cmd_update, "finish": cmd_finish,
        "list": cmd_list, "validate-spec": cmd_validate_spec, "fetch-spec": cmd_fetch_spec,
        "parse-report": cmd_parse_report, "prices-derive": _derive_prices,
        "round": cmd_round, "interrupt": cmd_interrupt, "close-sync": cmd_close_sync,
        "set-anchor": cmd_set_anchor,
    }[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
