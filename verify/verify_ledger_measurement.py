"""TG-13：账本『测量化』闸门（offline）——口径可核 / 双向一致 / 退化值 / 终态写回 / 棘轮基线。

**为什么需要这个闸门**（TG-13 卡内证据，2026-09-21 实测）：账本此前记录的是"写入时刻的巧合"而
不是测量值——`started_at`/`ended_at` 逐字节相同（3 例，dur 恰 `0.00`）、
`dur` 恰为整十分钟（3 例，
恰好 `10.00`）、`rounds=5` 而报告只有 3 轮、
60 个 `agents/runs/*` 目录 vs 59 条账本记录、
`doc-audit-009` 终态未写回（账本滞留 `status=running`）。
这些数字会被看板与评审直接引用，
**失真的可观测性比没有可观测性更坏**（3-LEARNED 1.59：可观测性必须自证）。

**口径**（唯一真源 = `agents/policy.json::ledger_measurement`，本文件不另写一份；三条可核文本）：

    dur      = `ended_at - started_at`（同一 run 的**累计墙钟**时长；
    `round` 追加会把 ended_at
               前移到末轮）。**不是**『首末轮时间差』（账本没有逐轮 started_at），
               **不是**报告自报时长——报告时长不得回填账本。
    rounds   真源 = **报告轮次**（`report_round_pattern` 能从产物报告数出时以报告为准，
               并与账本 `rounds_count`/`rounds[]` 核对）；报告不可数时账本声明值只是
               **declared 声明**（`measurement_source=declared`），不得当实测值上报看板。
    unknown  **缺值必须显式 `unknown`**：
    无法测量时 `dur_minutes=null` + `measurement_source=unknown`，
               展示层写 `dur=unknown`；**禁止**用 `0.00`／整十分钟等退化值冒充实测值
               （`0.00` 的含义是"未测得"，不是"零耗时"）。

**断言分组**（哪些 FAIL、哪些 WARN 写死在政策文本 + 本文件的信息串里）：

    A 账本 ↔ `agents/runs/**` **双向**一致：
    有目录无记录 / 有记录无目录（终态 run 必须有产物目录；
      非终态 run 尚未产出，不算缺失）。
      历史例外走 `run-dir-exceptions.json` 白名单（**每条必须有
      reason**，且**只减不增**：已不再需要的例外留在表里 = FAIL）。
    B 时间戳非退化：`zero_duration`（两端逐字节相同 / dur 恰 0.00）、
    `round_duration`（dur 恰为
      `degenerate.round_minutes_multiple` 的整数倍）、
      `negative_duration`（末态早于起点）、
      `missing_timestamp`（终态 run 缺任一端）→ **新 run 一律 FAIL；
      历史 run 计入棘轮上限**。
    C `rounds` 与报告轮次一致（报告可数者）→ 新 run FAIL；历史计入棘轮。
    D **终态已写回**：`status`
    仍非终态但产物目录里已有终态报告（`terminal_report_globs`）→ FAIL。
    E 产出未测量：`succeeded` 但 `output_chars=0`；评审类 run（spec `scope_required:
    true`）无
      `result_files` → 新 run FAIL；历史计入棘轮。
    F `measurement_source` 契约（`wall-clock` / `declared` / `unknown`）
    + `dur_minutes` 一致性：
      新 run 必须带这两个字段；标 `unknown` 时
      `dur_minutes` 必须是 `null`（不得回落 0.00）；
      可测量的终态 run 必须标 `wall-clock`；
      `dur_minutes` 与时间戳的偏差 > 容差 = 数字被改写。
      **行 18**：新 run 若 `measurement_source=declared` 且**当前仍退化** ⇒ 必须在该行记
      `degenerate_reason`（≥10 字符）——具名豁免的理由不得只上屏；
      反向：`measurement_flags` 为空却带该字段 ⇒ FAIL（字段与事实不符）。
    A' **行 19 撤回留痕**（顶层 `retractions[]`）：撤回是**改判定域**的动作 ⇒ 必须可核：
      留痕条目必须齐（`run_id`/`at`/`by`/`reason`≥10 字符/`evidence`）；
      撤回后该 run **不得**再出现在 `runs`（撤回不完整 = 污染仍在域里）；
      留痕里的 `quarantine` 非空 ⇒ 该路径必须真实存在（产物被保全，不是销毁现场）。
    G **历史棘轮**：**早于本次关闭窗口起点**的 run 按**计数上限**放行
      （上限 = 2026-09-25 实测值，写在 `legacy_ratchet.caps`，只许下调），
      超过上限逐条点名 FAIL；**窗口内**的 run 无上限、无豁免（严格判定）。
      `review_by` 到期未重评 → FAIL（没有到期日的豁免就是永久豁免）。

**判定域（2026-09-25 修，M2；数据键 `legacy_ratchet.domain.window`）**：

    凭什么改：旧口径把**截止日**（= 上限实测日 = 交付日）之前（含当日）的 run
    全判成"历史"，于是**当天新建**的 run 被拿**当天更早**实测的上限去量
    ⇒ 计数必然顶破上限（实测 `missing_result_files_review` 9→10、
    `output_chars_zero` 12→13），本闸门在**自己的交付日**结构性 FAIL，
    且与被评审代码无关——结构性假红会把闸门变成"人人无视的噪音"。

    现口径：窗口起点**由账本侧唯一推导**（
    `verify_close_readiness.ledger_close_window()` = `close_gate.scope_ref_step`
    作用域 run 的 `started_at`；本闸门**复用同一实现**、同一比较口径
    `started_at >= 起点` = 窗口内，与 C1/N6 逐字一致——一个窗口只能有一处推导）。
    `started_at` 早于起点 → 计入计数上限（棘轮域）；其余（含起点那条作用域 run）
    → 严格判定（无上限、无豁免）。`started_at` 缺失/不可解析 → **按窗口内**
    严格判定（fail-closed：不拿"字段缺失"换免检）。窗口推导不出
    （作用域 run 缺席 / 无 started_at）→ 退回 `cutoff_local_date` 的日期域，
    并在输出里点名"**回退域**"（回退是放宽方向，必须可见）。

**在飞 run（2026-09-25 修，M2；数据键 `ledger_measurement.in_flight`）**：
    spec 强制"**先写报告、后 finish**"，故"报告已落盘、终态尚未写回"在
    `terminal_writeback_grace_minutes` 宽限期内**不算缺陷**
    （只打 INFO，不计棘轮、也不 FAIL）——把这一瞬当缺陷是与工作流互斥的
    结构性假红（旧口径该类 cap=0，于是每个在飞 run 必踩）。超过宽限期仍不写回
    = 停摆，照旧逐条判。评审类无 `result_files` 只对**终态** run 判
    （非终态 run 尚未产出，同 A 类既有口径"非终态 run 尚未产出，不算缺失"）。

**模式**：

    .venv\\Scripts\\python.exe verify\\verify_ledger_measurement.py
        # 默认：真实数据（仓库 agents/）+ 内置自检（干净 fixture 必须过、
        # 四类反向对照必须 FAIL）
    .venv\\Scripts\\python.exe verify\\verify_ledger_measurement.py --agents-root <dir>
        # 只判定指定 agents 根（反向对照样本注入用；样本一律放 %TEMP%，不写进仓库）
    .venv\\Scripts\\python.exe verify\\verify_ledger_measurement.py --emit-fixture <kind> --agents-root <dir>
        # 生成反向对照样本：clean / same-timestamp / missing-dir / rounds-mismatch /
        # terminal-not-written-back / orphan-dir / legacy-overflow / legacy-within-cap

**账本"缺失"vs"坏账本"（C3，2026-09-25 code-review-072）**：
    `agents/runtime/registry.json` 被 `.gitignore` 忽略（`agents/runtime/*`）
    ⇒ **CI 的全新
    checkout 必然没有它**。旧实现一律 fail-closed ⇒ 本闸门在干净 checkout 上恒红，并把
    「Offline verify suite」整步拖红。现在**只有"文件不存在"**走显式 SKIP（rc=0，
    理由上屏：
    `SKIP: 账本不存在（fresh clone；registry.json 被 .gitignore 忽略）`）；
    文件**存在但坏**（JSON 非法 / 缺 `runs` 数组 / 结构非法）
    **照旧 rc=2**——坏账本是真缺陷，
    跳过它等于把"失真的可观测性"放行。判据在 `real_ledger_present()` + `print_ledger_skip()`。

退出码：0=通过（含"账本不存在 → SKIP"）；1=检出违规（逐条点名）；
2=政策缺失 / **账本存在但
非法**（fail-closed，不静默放行）。
"""
from __future__ import annotations
VERIFY_META = {
    'features': 'TG-13 账本测量化闸门：口径可核（dur/rounds/unknown 来自 policy）'
                '+ 账本↔agents/runs 双向一致（白名单须有 reason 且只减不增）'
                '+ 时间戳退化（相同/0.00/整十分钟/负值/缺失）'
                '+ rounds vs 报告轮次 + 终态已写回'
                '+ measurement_source/dur_minutes 契约'
                '（含行 18：declared 且仍退化 ⇒ 行内必须有 degenerate_reason）'
                '+ 行 19 撤回留痕（retractions[] 齐备/撤回后不得复活/隔离区在）'
                '+ 历史棘轮（计数上限 + review_by）'
                '+ CLI 写入侧自检（finish/round 标注退化、list 显示 unknown）',
    'tier': 'offline', 'providers': [], 'est_seconds': 14, 'est_cost_cny': 0,
    'routes': [], 'requires': ['none'],
}

import fnmatch
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import PolicyError, load_policy  # noqa: E402
# 关闭窗口口径的**唯一实现**：本闸门的棘轮判定域直接复用它（一处推导、两处消费；
# 不在这里另写一份"窗口从哪开始"，否则两处口径迟早分叉）
from verify.verify_close_readiness import ledger_close_window  # noqa: E402

# 项目权威时区 UTC+8（与自动 run-id / 产物目录命名同口径，
# 见 scripts/agent-ops.py 的 A5 说明）
PROJECT_TZ = timezone(timedelta(hours=8))
PASSED = 0

# 参与棘轮计数上限的缺陷类（其余类一律"任何日期都 FAIL"）。
# 政策 caps 必须与它**逐键相等**
# （少一类 = 棘轮被静默关掉；多一类 = 死数据/拼写漂移），见 `check_caps_shape`。
RATCHET_KINDS = (
    "output_chars_zero",
    "missing_result_files_review",
    "zero_duration",
    "round_duration",
    "negative_duration",
    "missing_timestamp",
    "rounds_mismatch",
    "terminal_not_written_back",
)

# 新 run（截止日之后）的 measurement_source 契约类（无棘轮：任何一例都 FAIL）
SOURCE_KINDS = (
    "measurement_source_missing",
    "measurement_source_invalid",
    "dur_minutes_missing",
    "degenerate_value_stored",
    "unknown_not_declared",
    "measurement_not_wall_clock",
    "dur_minutes_inconsistent",
)

# 棘轮判定域**规则名**（政策数据 `legacy_ratchet.domain.window` 的取值；只认这一个）。
# 数据改了值而实现没跟上 → `check_caps_shape` 直接 FAIL
# （判定域不得靠改数据悄悄换成另一套口径）。
DOMAIN_WINDOW_RULE = "close_window_start_exclusive"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def warn(name: str, detail: str = "") -> None:
    print(f"WARN: {name} {detail}")


def _exempted_local(value):
    """本函数内造 fixture 数据、不是闸门政策（TG-15⑦：`verify_no_policy_hardcode.py` 识别该名并放行）。

    仅用于反向对照样本（合成 run 行/目录名）；闸门自身引用的口径、阈值、
    白名单路径一律来自
    `agents/policy.json::ledger_measurement`。
    """
    return value


# ------------------------------------------------------------------ 时间/日期口径

def parse_ts(raw: object) -> datetime | None:
    """ISO 时间戳 → aware datetime；缺失/无时区/不可解析 → None（**fail-closed**：

    无时区的"测量值"无法与 UTC+8 的截止日比较，按不可测处理而不是猜一个时区）。
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        ts = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return None if ts.tzinfo is None else ts


def run_local_date(run: dict) -> str | None:
    """run 的本地（UTC+8）日期：优先 `started_at`，缺失时回落 run-id 的日期段，都没有 → None。"""
    ts = parse_ts(run.get("started_at"))
    if ts is not None:
        return ts.astimezone(PROJECT_TZ).strftime("%Y-%m-%d")
    matched = re.match(r"run-(\d{4}-\d{2}-\d{2})-", str(run.get("run_id") or ""))
    return matched.group(1) if matched else None


def is_legacy_date(run: dict, cutoff: str) -> bool:
    """**回退域**判据：本地日期 **≤** 截止日 = 历史；日期不可判定 → 按新 run 严格判。

    只在"关闭窗口推导不出"时使用（见 `in_ratchet_domain`）——主域是窗口，不是日期。
    """
    date = run_local_date(run)
    return bool(date) and date <= cutoff


def in_ratchet_domain(run: dict, *, window_start: str | None, cutoff: str) -> bool:
    """该 run 是否在**棘轮域**内（= 早于本次关闭窗口起点；窗口缺失 → 日期域）。

    比较口径与 C1/N6 **逐字一致**：`started_at` 与窗口起点都按**字符串字典序**比较
    （账本时间戳统一 `+00:00` 偏移时字典序 = 时间序，该前提由账本自身保证）。

    fail-closed 方向：`started_at` 缺失/不可解析 → **不在**棘轮域
    （按窗口内的严格判据走），宁可多判一条，也不拿"字段缺失"换免检（同 C1 的 D1）。
    """
    if window_start is None:
        return is_legacy_date(run, cutoff)
    started = str(run.get("started_at") or "").strip()
    return bool(started) and started < window_start


def ratchet_domain_note(window_start: str | None, cutoff: str) -> str:
    """判定域的可核说明（打印用：主域 = 窗口；回退域必须**可见**）。
    """
    if window_start is None:
        return (f"**回退域**（关闭窗口不可推导 = 作用域 run 缺席/无 started_at）"
                f"：本地日期 ≤ {cutoff} = 历史（棘轮），其余严格判定")
    return (f"主域：started_at < {window_start}（本次关闭窗口起点）= 历史（棘轮），"
            f"窗口内（含起点那条作用域 run）严格判定")


def duration_minutes(run: dict) -> float | None:
    """`dur` = ended_at - started_at（墙钟累计，分钟）。任一端不可解析 → None（= unknown）。"""
    start, end = parse_ts(run.get("started_at")), parse_ts(run.get("ended_at"))
    if start is None or end is None:
        return None
    return (end - start).total_seconds() / 60.0


def degeneracy(run: dict, multiple: int) -> list[str]:
    """时间戳退化判定（政策口径：`0.00` / 整十分钟都是**写入时刻的巧合**，不是测量值）。"""
    start, end = run.get("started_at"), run.get("ended_at")
    if parse_ts(start) is None or parse_ts(end) is None:
        return ["missing_timestamp"]
    mins = duration_minutes(run)
    if mins is None:
        return ["missing_timestamp"]
    if mins == 0.0:
        return ["zero_duration"]
    if mins < 0:
        return ["negative_duration"]
    ratio = mins / multiple
    if abs(ratio - round(ratio)) < 1e-9:
        return ["round_duration"]
    return []


# ------------------------------------------------------------------ 政策与数据装载

def _read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        print(f"LEDGER-MEASUREMENT-ERROR: {label} 不存在：{path}（fail-closed，不静默放行）")
        raise SystemExit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"LEDGER-MEASUREMENT-ERROR: {label} JSON 非法：{path}: {exc}")
        raise SystemExit(2) from exc


def load_runs(agents_root: Path) -> list[dict]:
    data = _read_json(agents_root / "runtime" / "registry.json", "账本 registry.json")
    runs = data.get("runs")
    if not isinstance(runs, list):
        print(f"LEDGER-MEASUREMENT-ERROR: 账本缺 runs 数组：{agents_root / 'runtime' / 'registry.json'}")
        raise SystemExit(2)
    return [r for r in runs if isinstance(r, dict)]


def load_retractions(agents_root: Path) -> list[dict]:
    """读账本顶层的**撤回留痕** `retractions[]`（复盘行 19）。

    为什么它是闸门的事：撤回是**改判定域**的动作（把一个 run 从判定域里移出去），
    而"域被谁改、凭什么改"必须可核——只删行不留痕 = 不可审计的删除，
    那正是行 19 要消灭的形态（此前账本**没有**合法删除路径，于是只能手改或伪造读数）。
    缺该键 = 没有撤回（不是错误）；结构非法（非数组）= fail-closed。
    """
    data = _read_json(agents_root / "runtime" / "registry.json", "账本 registry.json")
    if "retractions" not in data:
        return []
    items = data.get("retractions")
    if not isinstance(items, list):
        print(f"LEDGER-MEASUREMENT-ERROR: 账本 retractions 必须是数组，实际 {items!r}")
        raise SystemExit(2)
    return [i for i in items if isinstance(i, dict)]


def load_exceptions(path: Path) -> tuple[list[dict], list[dict]]:
    """读目录/记录例外白名单（`ledger_measurement.run_dir_exceptions_file`）。

    返回 `(目录例外, 记录例外)`。缺文件 = 无例外（不是错误）；结构非法 = fail-closed。
    两类条目都**必须写 reason**——白名单不是静音开关。
    """
    if not path.is_file():
        return [], []
    data = _read_json(path, "run-dir-exceptions.json")
    dirs = data.get("exceptions") or []
    records = data.get("record_exceptions") or []
    for label, items in (("exceptions", dirs), ("record_exceptions", records)):
        if not isinstance(items, list):
            print(f"LEDGER-MEASUREMENT-ERROR: {path.name} 的 {label} 必须是数组，实际 {items!r}")
            raise SystemExit(2)
    return [i for i in dirs if isinstance(i, dict)], [i for i in records if isinstance(i, dict)]


# ------------------------------------------------------------------ 判据

def _terminal_statuses(policy) -> tuple[set[str], set[str]]:
    """`(终态集合, 可信终态集合)`——状态机来自政策数据（不在这里抄一份白名单）。

    可信终态 = 终态 - `non_credible`（即"成功"类）：只有成功类 run 的 `output_chars` 才能当产出测量值，
    `failed`/`cancelled` 的 0 是正常值（不能把失败也当"产出未测量"）。
    """
    ledger = policy._data("ledger_status")
    terminal = set(ledger["terminal"])
    return terminal, terminal - set(ledger["non_credible"])


def report_rounds(run_dir: Path, globs: tuple[str, ...], pattern: re.Pattern) -> set[int]:
    """从产物报告的**文件名**匹配 `globs` 的文件里数轮次标记（返回去重后的轮次号集合，空 = 不可数）。"""
    if not run_dir.is_dir():
        return set()
    found: set[int] = set()
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or not any(fnmatch.fnmatch(path.name, g) for g in globs):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for matched in pattern.finditer(text):
            value = matched.group(1) or matched.group(2)
            if value:
                found.add(int(value))
    return found


def terminal_report_paths(run_dir: Path, globs: tuple[str, ...]) -> list[Path]:
    """产物目录里像"终态报告"的文件（**Path 形态**）。

    判"终态已写回"与算在飞宽限期**共用这一份列举**（两处口径不得分叉）。
    """
    if not run_dir.is_dir():
        return []
    return [p for p in sorted(run_dir.rglob("*"))
            if p.is_file() and any(fnmatch.fnmatch(p.name, g) for g in globs)]


def terminal_report_files(run_dir: Path, globs: tuple[str, ...]) -> list[str]:
    """产物目录里像"终态报告"的文件（相对路径名，用于在 FAIL 文案里点名证据）。"""
    return [str(p.relative_to(run_dir)) for p in terminal_report_paths(run_dir, globs)]


def newest_report_age_seconds(run_dir: Path, globs: tuple[str, ...]) -> float | None:
    """最新"终态报告"距现在多少秒（**epoch 秒**：`time.time()` vs `os.path.getmtime()`，
    与项目时区无关——宽限期问的是"报告写完之后等了多久"）；没有报告 → None。

    用途 = 在飞宽限判据（`in_flight.terminal_writeback_grace_minutes`）：spec 强制
    "**先写报告、后 finish**"，报告刚落盘、`finish` 尚未调用这一瞬**不是缺陷**；
    报告放了很久还不写回 = 停摆，照旧判。
    """
    paths = terminal_report_paths(run_dir, globs)
    if not paths:
        return None
    return time.time() - max(p.stat().st_mtime for p in paths)


def declared_rounds(run: dict) -> int:
    """账本**声明**的轮次数（`rounds_count` > `rounds[]` 长度 > 1）——声明值，不是实测值。"""
    return int(run.get("rounds_count") or len(run.get("rounds") or []) or 1)


def check_caps_shape(caps: dict, review_by: str, cutoff: str, today: str,
                     domain_window: object, grace_minutes: object) -> list[str]:
    """棘轮基线自身的完备性（**与数据无关的不变式**，防"删掉一条上限即静默放行"）。

    这里同时守住本次修的两项语义数据：判定域**规则名**（只认本文件实现的那一个取值）与
    在飞宽限（正整数）。两者写错都会让判定域/在飞判据**静默变成另一套口径**——
    那是"改数据即放宽"，比改代码更隐蔽，故一律 fail-closed。
    """
    problems: list[str] = []
    expected = set(RATCHET_KINDS)
    actual = set(caps)
    for missing in sorted(expected - actual):
        problems.append(f"[棘轮基线] caps 缺 {missing!r} —— 少一条上限就等于该类**无限放行**"
                        f"（棘轮不得被静默关掉；如确已清零请显式写 0）")
    for extra in sorted(actual - expected):
        problems.append(f"[棘轮基线] caps 多出 {extra!r} —— 上限表与闸门判据不同步（死数据/拼写漂移）")
    if domain_window != DOMAIN_WINDOW_RULE:
        problems.append(f"[棘轮基线] 判定域规则 domain.window={domain_window!r} "
                        f"本闸门不认（只认 {DOMAIN_WINDOW_RULE!r}）—— "
                        f"数据与实现不同步会让判定域静默变成另一套口径"
                        f"（fail-closed：宁可不判，也不按没实现的规则放行）")
    if (isinstance(grace_minutes, bool) or not isinstance(grace_minutes, int)
            or grace_minutes <= 0):
        problems.append(f"[棘轮基线] in_flight.terminal_writeback_grace_minutes "
                        f"必须是正整数，实际 {grace_minutes!r} —— "
                        f"写错会让在飞 run 立刻假红或让该类永不判缺陷")
    if today > review_by:
        problems.append(f"[棘轮基线] review_by={review_by} 已过期（今天 {today}）→ 必须重新测量并重评基线，"
                        f"过期基线不得继续放行历史债")
    if cutoff > today:
        problems.append(f"[棘轮基线] cutoff_local_date={cutoff} 晚于今天 {today} —— 截止日在未来会把所有"
                        f"新 run 都当成历史（棘轮被反向利用）")
    return problems


def evaluate(policy, runs: list[dict], runs_dir: Path,
             dir_exceptions: list[dict], record_exceptions: list[dict], *,
             today: str,
             retractions: list[dict] | None = None,
             ) -> tuple[list[str], list[str], dict[str, int]]:
    """核心判定。返回 `(problems, warnings, 历史缺陷计数)`；`problems` 非空 = FAIL。"""
    problems: list[str] = []
    warnings: list[str] = []
    measure = policy.ledger_measurement
    cutoff = policy.ledger_cutoff_local_date()
    review_by = policy.ledger_review_by()
    caps = policy.ledger_caps()
    ratchet = measure["legacy_ratchet"]
    domain_window = (ratchet.get("domain") or {}).get("window")
    in_flight = measure.get("in_flight") or {}
    grace_minutes = in_flight.get("terminal_writeback_grace_minutes")
    window_start = ledger_close_window(policy, runs)
    multiple = int(measure["degenerate"]["round_minutes_multiple"])
    globs = tuple(str(g) for g in measure["terminal_report_globs"])
    pattern = re.compile(str(measure["report_round_pattern"]))
    tolerance = float(measure["dur_minutes_tolerance"])
    sources = set(str(v) for v in measure["measurement_source_values"])
    terminal, credible = _terminal_statuses(policy)
    review_roles = policy.review_roles

    problems += check_caps_shape(caps, review_by, cutoff, today, domain_window,
                                 grace_minutes)

    findings: list[dict] = []          # 参与棘轮的历史缺陷
    strict: list[dict] = []            # 窗口内 run 缺陷（无上限、无豁免）

    def in_domain(run: dict) -> bool:
        return in_ratchet_domain(run, window_start=window_start, cutoff=cutoff)

    def add(kind: str, run: dict | None, detail: str, *, force_strict: bool = False) -> None:
        item = {"kind": kind, "run_id": str((run or {}).get("run_id") or "-"), "detail": detail}
        if force_strict or run is None or not in_domain(run):
            strict.append(item)
        else:
            findings.append(item)

    # ---- A 白名单自身的完备性 + 双向一致（目录类不设计数上限，走白名单）--------------
    dir_exc: dict[str, dict] = {}
    for item in dir_exceptions:
        name = str(item.get("dir") or "").strip()
        if not name:
            problems.append(f"[白名单] `exceptions` 有条目缺 `dir`（{json.dumps(item, ensure_ascii=False)[:80]}）")
            continue
        if not str(item.get("reason") or "").strip():
            problems.append(f"[白名单] 目录例外 {name!r} 缺 reason —— 白名单不是静音开关")
        dir_exc[name] = item
    rec_exc: dict[str, dict] = {}
    for item in record_exceptions:
        rid = str(item.get("run_id") or "").strip()
        if not rid:
            problems.append(f"[白名单] `record_exceptions` 有条目缺 `run_id`"
                            f"（{json.dumps(item, ensure_ascii=False)[:80]}）")
            continue
        if not str(item.get("reason") or "").strip():
            problems.append(f"[白名单] 记录例外 {rid!r} 缺 reason —— 白名单不是静音开关")
        rec_exc[rid] = item

    ledger_ids = {str(r.get("run_id") or "") for r in runs}
    disk_dirs = {p.name for p in runs_dir.iterdir() if p.is_dir()} if runs_dir.is_dir() else set()
    if not runs_dir.is_dir():
        problems.append(f"[A] 产物目录不存在：{runs_dir}（fail-closed：无从判定双向一致）")

    for name in sorted(disk_dirs - ledger_ids - set(dir_exc)):
        problems.append(f"[A/dirs_without_record] 目录 {name!r} 在账本里没有同名 run，也不在例外白名单里"
                        f"（有目录无记录 = 动作执行了但没入账；新增例外须写 reason）")
    for rid, item in sorted(dir_exc.items()):
        if rid not in disk_dirs:
            problems.append(f"[白名单] 目录例外 {rid!r} 已无对应目录（例外只减不增，失效条目必须删除）")
        elif rid in ledger_ids:
            problems.append(f"[白名单] 目录例外 {rid!r} 现在账本里已有同名 run —— 例外已不再需要，必须删除")
    for rid, item in sorted(rec_exc.items()):
        if rid not in ledger_ids:
            problems.append(f"[白名单] 记录例外 {rid!r} 已不在账本里（例外只减不增，失效条目必须删除）")
        elif rid in disk_dirs:
            problems.append(f"[白名单] 记录例外 {rid!r} 现在已有产物目录 —— 例外已不再需要，必须删除")

    # ---- A' 撤回留痕（复盘行 19）--------------------------------------------------
    # "撤回"必须是**受控路径**，不是"账本里少了一行"：删行不留痕 = 不可审计的删除，
    # 而判定域恰恰由账本派生（域被谁改、凭什么改必须可核）。三条判据各堵一种形态：
    #   ① 留痕条目本身必须完整（run_id / at / by / reason≥10 字符 / evidence）；
    #   ② 撤回后该 run **不得**再出现在 `runs`（撤回不完整 = 污染还在判定域里）；
    #   ③ 留痕里的 `quarantine` 非空 ⇒ 该路径必须**真实存在**（产物被保全了；
    #      只删不隔离 = 把那次动作的现场销毁，账本与目录两边都查不到了）。
    quarantines: dict[str, dict] = {}
    for item in retractions or []:
        rid_r = str(item.get("run_id") or "").strip()
        if not rid_r:
            problems.append("[撤回] retractions 有条目缺 run_id"
                            f"（{json.dumps(item, ensure_ascii=False)[:80]}）")
            continue
        for key in ("at", "by", "reason", "evidence"):
            if not str(item.get(key) or "").strip():
                problems.append(f"[撤回] {rid_r} 的留痕缺 {key}"
                                " —— 撤回必须留痕（行 19：删行不留痕 = 不可审计）")
        reason_len = len(str(item.get("reason") or "").strip())
        if 0 < reason_len < 10:
            problems.append(f"[撤回] {rid_r} 的 reason 只有 {reason_len} 字符（<10）"
                            " —— 说不清为什么撤回就不是受控撤回")
        quarantines[rid_r] = item
    for rid_r, item in sorted(quarantines.items()):
        if rid_r in ledger_ids:
            problems.append(f"[撤回] {rid_r} 已在 retractions[] 里撤回，"
                            "却仍在账本 runs 中"
                            " —— 撤回不完整（这条污染还在判定域里）")
        rel_q = str(item.get("quarantine") or "").strip()
        if rel_q and not (runs_dir.parent / rel_q).exists():
            problems.append(f"[撤回] {rid_r} 的留痕写了隔离路径 {rel_q!r}，"
                            "但该路径不存在"
                            " —— 产物没被保全（撤回只许删账本行，不许销毁现场）")

    # ---- 逐 run 判据 --------------------------------------------------------------
    for run in runs:
        rid = str(run.get("run_id") or "-")
        status = str(run.get("status") or "")
        run_dir = runs_dir / rid
        legacy = in_domain(run)

        # A：终态 run 必须有产物目录（非终态 run 尚未产出 → 不算缺失）
        if status in terminal and rid not in disk_dirs and rid not in rec_exc:
            problems.append(f"[A/records_without_dir] 终态 run {rid}（status={status}）没有产物目录 "
                            f"{runs_dir.name}/{rid} —— 有记录无目录（账本说了做过，产物不见了）")

        # D：终态已写回（status 仍非终态，产物目录却已有终态报告）
        #    **在飞宽限**（M2）：spec 强制"先写报告、后 finish"，报告刚落盘尚未 finish
        #    的这一瞬不是缺陷（否则每个在飞 run 都踩 cap=0，与工作流互斥）；
        #    超过宽限期仍不写回 = 停摆，照旧判。
        if status and status not in terminal:
            written = terminal_report_files(run_dir, globs)
            if written:
                age = newest_report_age_seconds(run_dir, globs)
                grace_s = int(grace_minutes) * 60
                if age is not None and age <= grace_s:
                    print(f"INFO 在飞：{rid} 报告已写"
                          f"（{age / 60:.1f} 分钟前）但 status={status}，"
                          f"在 {int(grace_minutes)} 分钟宽限期内 → **不计缺陷**"
                          f"（先写报告、后 finish 是 spec 强制的顺序）")
                else:
                    waited = ("报告时间不可读" if age is None
                              else f"已等待 {age / 60:.1f} 分钟")
                    add("terminal_not_written_back", run,
                        f"status={status}（非终态）但产物目录已有终态报告 {written[:2]}"
                        f"（{waited} > 宽限期 {int(grace_minutes)} 分钟）—— "
                        f"终态未写回账本（账本会长期显示 running）")

        # B：时间戳退化
        for kind in degeneracy(run, multiple):
            if kind == "missing_timestamp":
                if status in terminal:
                    add("missing_timestamp", run, f"终态 run 缺 started_at/ended_at"
                                                  f"（started={run.get('started_at')!r} ended={run.get('ended_at')!r}）"
                                                  f" —— 无法测量时长，必须显式 unknown 而不是留空/写 0")
            elif kind == "zero_duration":
                add("zero_duration", run, f"started_at == ended_at（{run.get('started_at')!r}）→ dur 恰 0.00 分钟"
                                          f"：这是『未测得』被写成『零耗时』的退化形态")
            elif kind == "negative_duration":
                add("negative_duration", run, f"ended_at 早于 started_at"
                                              f"（{run.get('started_at')!r} → {run.get('ended_at')!r}）")
            elif kind == "round_duration":
                add("round_duration", run,
                    f"dur 恰为 {multiple} 分钟的整数倍（{duration_minutes(run):.2f} 分钟）→ 写入时刻凑整的"
                    f"退化形态，不是测量值")

        # C：rounds 与报告轮次一致（报告可数者）
        reported = report_rounds(run_dir, globs, pattern)
        declared = declared_rounds(run)
        if reported and max(reported) != declared:
            add("rounds_mismatch", run,
                f"账本声明 rounds={declared}，而报告里数得出的轮次为 {sorted(reported)}"
                f"（判据：报告轮次是真源）")

        # E：产出/产物未测量
        if status in credible and int(run.get("output_chars") or 0) == 0:
            add("output_chars_zero", run, f"status={status} 但 output_chars=0 —— 产出未测量"
                                          f"（不得以 0 冒充『无产出』）")
        #    **只对终态 run 判**（M2）：非终态 run 尚未产出 → 不是"产物未归档"，
        #    同 A 类既有口径"非终态 run 尚未产出，不算缺失"
        #    （否则每个在飞的评审 run 一登记就被判缺陷）。
        if status in terminal and str(run.get("role") or "") in review_roles \
                and not (run.get("result_files") or []):
            add("missing_result_files_review", run,
                f"评审类 run（role={run.get('role')}，spec 声明 scope_required=true）"
                f"已终态（status={status}）却没有 result_files —— "
                f"评审产物未归档，评审结论不可回溯")

        # F：measurement_source / dur_minutes 契约（**只对新 run 强制**；
        # 历史 run 无此字段属棘轮范围）
        # 模型（政策 measurement_sources）：
        # wall-clock = 可测且非退化（dur_minutes 必为实测值）；
        # declared = 有读数但不是测量值（退化）；unknown = 无从测量。
        # 后两者的 dur_minutes **必须为
        #    null**——把退化读数写进测量字段就是"用 0.00/整十分钟冒充测量值"。
        measured = duration_minutes(run)
        flags = degeneracy(run, multiple)
        measurable = measured is not None and not flags
        source = run.get("measurement_source")
        has_dur = "dur_minutes" in run
        dur_value = run.get("dur_minutes")
        if not legacy:
            if source is None:
                strict.append({"kind": "measurement_source_missing", "run_id": rid,
                               "detail": "新 run 缺 measurement_source（合法值 "
                                         f"{sorted(sources)}）—— 测量来源必须显式声明"})
            elif str(source) not in sources:
                strict.append({"kind": "measurement_source_invalid", "run_id": rid,
                               "detail": f"measurement_source={source!r} 非法（合法值 {sorted(sources)}）"})
            if not has_dur:
                strict.append({"kind": "dur_minutes_missing", "run_id": rid,
                               "detail": "新 run 缺 dur_minutes（无测量时必须显式为 null，不得省略）"})
            if dur_value is not None and str(source) != "wall-clock":
                strict.append({"kind": "degenerate_value_stored", "run_id": rid,
                               "detail": f"measurement_source={source!r}（非实测）却把 dur_minutes="
                                         f"{dur_value!r} 写进测量字段 —— 退化/声明值不得冒充测量值（必须 null）"})
            if status in terminal:
                if measured is None and source is not None and str(source) != "unknown":
                    strict.append({"kind": "unknown_not_declared", "run_id": rid,
                                   "detail": f"时间戳缺失/不可解析（无从测量）但 measurement_source="
                                             f"{source!r} —— 缺值必须显式 unknown"})
                if str(source) == "wall-clock" and not measurable:
                    strict.append({"kind": "measurement_not_wall_clock", "run_id": rid,
                                   "detail": f"标 measurement_source=wall-clock，但时间戳不可测或退化"
                                             f"（flags={flags or ['unparseable']}）—— 不得声称实测"})
                elif str(source) == "wall-clock" and has_dur and (
                        dur_value is None or abs(float(dur_value) - measured) > tolerance):
                    strict.append({"kind": "dur_minutes_inconsistent", "run_id": rid,
                                   "detail": f"dur_minutes={dur_value!r} 与墙钟时间戳算出的 {measured:.3f} "
                                             f"分钟不一致（容差 {tolerance}）—— 数字被改写或未随轮次刷新"})
            # 行 18：具名豁免的**理由必须落账本**（`degenerate_reason`）。
            # 此前理由只上屏 ⇒ 事后读账本只有 `declared`+退化标记+null，
            # "这不是测量值"落库了、"为什么不可测"没有——唯一的解释留在某次终端输出里。
            # 判据用的是**重算出的 `flags`**（= 该行**当前**是否仍处退化态），
            # 不是行内存储的 `measurement_flags`：受控回填（`set-started-at`）修好起点后
            # 行内标记会**陈旧**——实测 `run-2026-09-26-code-review-092` 正是这种行
            # （它写于守卫存在之前，从未走过 `--allow-degenerate`）⇒ 按存储标记判会把它
            # 追溯判红，而那是"修复工具修好了它"的后果，不是本条的缺口。
            # 反向（字段与事实不符）则按**存储**标记配对：两者是同一次写入的产物。
            stored_flags = [str(f) for f in (run.get("measurement_flags") or [])]
            reason18 = str(run.get("degenerate_reason") or "").strip()
            if str(source) == "declared" and flags and len(reason18) < 10:
                strict.append({"kind": "degenerate_reason_missing", "run_id": rid,
                               "detail": f"measurement_source=declared"
                                         f" + 当前仍退化 {flags}"
                                         f" ⇒ 必须在该行记 `degenerate_reason`"
                                         f"（≥10 字符，实测 {len(reason18)}）"
                                         f"—— 具名豁免的理由不得只上屏（行 18）"})
            elif reason18 and not stored_flags:
                strict.append({"kind": "degenerate_reason_orphan", "run_id": rid,
                               "detail": f"该行 `measurement_flags` 为空"
                                         f"（{stored_flags}）"
                                         f"却带 degenerate_reason={reason18!r}"
                                         f" —— 字段与事实不符（无退化却记豁免理由）"})

    # ---- G 棘轮：历史缺陷计数上限 ------------------------------------------------
    counts: dict[str, int] = {kind: 0 for kind in RATCHET_KINDS}
    for item in findings:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    for kind in sorted(counts):
        cap = caps.get(kind)
        named = [f["run_id"] for f in findings if f["kind"] == kind]
        if named and cap is not None and len(named) > int(cap):
            problems.append(f"[棘轮/{kind}] 历史 run 中该类缺陷 {len(named)} 例 > 上限 {cap}："
                            f"{named[:6]}{' …' if len(named) > 6 else ''}"
                            f" —— 上限只许在重评基线时下调（不许为变绿上调）")
        for item in [f for f in findings if f["kind"] == kind]:
            warnings.append(f"{kind} {item['run_id']}：{item['detail']}")
    for item in strict:
        problems.append(f"[{item['kind']}] {item['run_id']}：{item['detail']}")
    return problems, warnings, counts


# ------------------------------------------------------------------ 反向对照样本

# 合成 run 的样本表。**判定域**由 fixture 自己体现：901 = 作用域 run
# （它定义关闭窗口起点），902 = 窗口内的评审 run（大多数反向对照的**变异目标**，
# 窗口内 = 严格判定、无上限），903 = 在飞 run（queued、无时间戳：验证"在飞不算缺陷"）。
# 只有 `_exempted_local` 标注的 fixture 字面量使用角色名，
# 闸门自身政策一律来自 policy.json。
(FIXTURE_SCOPE_ROW, FIXTURE_REVIEW_ROW, FIXTURE_IN_FLIGHT_ROW) = _exempted_local((
    "run-2026-09-26-impact-assessment-901",
    "run-2026-09-26-code-review-902",
    "run-2026-09-26-impact-assessment-903",
))

REVIEW_REPORT_REL = f"runs/{FIXTURE_REVIEW_ROW}/code-review.report.md"

FIXTURE_ROWS = _exempted_local([
    {"run_id": FIXTURE_SCOPE_ROW, "role": "impact-assessment", "status": "succeeded",
     "started_at": "2026-09-25T00:30:00+00:00", "ended_at": "2026-09-25T00:45:00+00:00",
     "output_chars": 800, "result_files": [], "measurement_source": "wall-clock",
     "dur_minutes": 15.0, "measurement_flags": []},
    {"run_id": FIXTURE_REVIEW_ROW, "role": "code-review", "status": "succeeded",
     "started_at": "2026-09-25T01:00:00+00:00", "ended_at": "2026-09-25T01:37:00+00:00",
     "output_chars": 12345, "result_files": [REVIEW_REPORT_REL],
     "rounds_count": 2, "measurement_source": "wall-clock", "dur_minutes": 37.0,
     "measurement_flags": []},
    {"run_id": FIXTURE_IN_FLIGHT_ROW, "role": "impact-assessment", "status": "queued",
     "started_at": None, "ended_at": None, "output_chars": 0, "result_files": [],
     "measurement_source": "unknown", "dur_minutes": None, "measurement_flags": []},
])

FIXTURE_FILES = _exempted_local({
    FIXTURE_SCOPE_ROW: {"notes.md": "合成作用域 run（定义关闭窗口起点；无轮次标记）\n"},
    FIXTURE_REVIEW_ROW: {"code-review.report.md":
        "# 合成评审报告（fixture）\n\nRound 1：越查样本，用于核对 rounds 与报告轮次。\n"
        "Round 2：第二轮同样合成。\n"},
})

FIXTURE_KINDS = ("clean", "same-timestamp", "missing-dir", "rounds-mismatch",
                 "terminal-not-written-back", "in-flight-report", "orphan-dir",
                 "legacy-overflow", "legacy-within-cap", "fallback-domain")

# 这些类别的产物文件 mtime 要拨到**超出在飞宽限期**之前：同形状、只差"等了多久"——
# `terminal-not-written-back` = 停摆（该判），`in-flight-report` = 刚写完（不该判）。
FIXTURE_STALE_KINDS = ("terminal-not-written-back",)
FIXTURE_STALE_EXTRA_MINUTES = 60


def legacy_rows(count: int, *, role: str = "impact-assessment") -> list[dict]:
    """合成**历史**（窗口之前）零时长 run：验证棘轮两方向（限内 WARN / 超限 FAIL）。

    `role` 可换：`fallback-domain` 类要用**非作用域步骤**的角色，否则这些行自己就成了
    "最新的作用域 run"、把窗口定在它们身上，于是它们从棘轮域挪进窗口内
    （测的就不是回退域了）。
    """
    rows = []
    for i in range(1, count + 1):
        rid = f"run-2026-09-20-{role}-8{i:02d}"
        rows.append({"run_id": rid, "role": role, "status": "succeeded",
                     "started_at": "2026-09-20T01:00:00+00:00", "ended_at": "2026-09-20T01:00:00+00:00",
                     "output_chars": 100, "result_files": []})
    return rows


def fixture(kind: str) -> tuple[list[dict], dict[str, dict[str, str]]]:
    """按类别造 `(账本行, {run_id: {文件名: 内容}})`。`clean` 必须**无任何** problem。

    变异一律打在**窗口内**的评审 run（`FIXTURE_REVIEW_ROW`）上：窗口内是严格判定，
    每个变异都必须 FAIL（M2 的反向对照 (a)）；`legacy-*` 两类把**同形状**的 run 放到
    窗口之前（棘轮域），用于验证"限内只 WARN、超限 FAIL"（反向对照 (b)）。
    """
    if kind not in FIXTURE_KINDS:
        raise SystemExit(f"未知 fixture 类别 {kind!r}（合法：{list(FIXTURE_KINDS)}）")
    rows = [dict(r) for r in FIXTURE_ROWS]
    files = {rid: dict(fs) for rid, fs in FIXTURE_FILES.items()}
    review = next(i for i, r in enumerate(rows) if r["run_id"] == FIXTURE_REVIEW_ROW)
    if kind == "same-timestamp":  # ① 时间戳相同（dur 恰 0.00 → 退化，不进测量字段）
        rows[review] = {**rows[review], "ended_at": rows[review]["started_at"],
                        "measurement_source": "declared", "dur_minutes": None,
                        "measurement_flags": ["zero_duration"]}
    elif kind == "missing-dir":  # ② 缺目录（有记录无目录）
        files.pop(FIXTURE_REVIEW_ROW, None)
    elif kind == "rounds-mismatch":  # ③ rounds 与报告不符（报告 2 轮，账本声明 4）
        rows[review] = {**rows[review], "rounds_count": 4}
    elif kind == "terminal-not-written-back":  # ④ 停摆：报告放了很久仍不写回
        files[FIXTURE_IN_FLIGHT_ROW] = {
            "impact-assessment.report.md": "# 已完成的报告\n"}
    elif kind == "in-flight-report":  # ④' 在飞：报告刚写完、finish 尚未调用（不算缺陷）
        files[FIXTURE_IN_FLIGHT_ROW] = {
            "impact-assessment.report.md": "# 刚写完的报告\n"}
    elif kind == "orphan-dir":  # A 的另一向：有目录无记录
        files["run-2026-09-26-impact-assessment-904"] = {
            "impact-assessment.report.md": "# 孤儿目录\n"}
    elif kind == "legacy-overflow":  # 棘轮超限（4 > 上限 3）
        rows = rows + legacy_rows(4)
        files.update({r["run_id"]: {"notes.md": "合成历史 run\n"} for r in legacy_rows(4)})
    elif kind == "legacy-within-cap":  # 棘轮限内（3 = 上限 3 → 只 WARN，不 FAIL）
        rows = rows + legacy_rows(3)
        files.update({r["run_id"]: {"notes.md": "合成历史 run\n"} for r in legacy_rows(3)})
    elif kind == "fallback-domain":  # 无带 started_at 的作用域 run → 回退日期域
        rows = [r for r in rows if r["run_id"] != FIXTURE_SCOPE_ROW]
        files.pop(FIXTURE_SCOPE_ROW, None)
        # 非作用域步骤的角色：这些历史行不得自己定义关闭窗口
        stale = legacy_rows(3, role="lessons-learned")
        rows = rows + stale
        files.update({r["run_id"]: {"notes.md": "合成历史 run\n"} for r in stale})
    return rows, files


def fixture_stale_age_minutes(policy, kind: str) -> float | None:
    """该类别的产物 mtime 要拨回多久（`None` = 用当前时间）。

    "停摆"样本 = 政策宽限期 + 1 小时：判据是"等了多久"，样本必须真的等过头，
    否则反向对照测的是别的分支（这是最容易自欺的一处）。
    """
    if kind not in FIXTURE_STALE_KINDS:
        return None
    grace = int((policy.ledger_measurement.get("in_flight") or {})
                .get("terminal_writeback_grace_minutes") or 0)
    return grace + FIXTURE_STALE_EXTRA_MINUTES


def write_fixture_root(base: Path, rows: list[dict], files: dict[str, dict[str, str]],
                       *, stale_age_minutes: float | None = None,
                       retractions: list[dict] | None = None) -> None:
    """把 fixture 写成 agents 根（`runtime/registry.json` + `runs/<run_id>/...`）。

    样本一律在 %TEMP%。`stale_age_minutes` 非空时把产物 mtime 拨回那么久之前
    （`os.utime`，epoch 秒口径）。`retractions` 非空时写进账本顶层（行 19 的反向对照）。
    """
    (base / "runtime").mkdir(parents=True, exist_ok=True)
    ledger = {"version": 1, "runs": rows}
    if retractions is not None:
        ledger["retractions"] = retractions
    (base / "runtime" / "registry.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = None if stale_age_minutes is None else time.time() - stale_age_minutes * 60
    for rid, entries in files.items():
        run_dir = base / "runs" / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        for name, text in entries.items():
            path = run_dir / name
            path.write_text(text, encoding="utf-8")
            if stamp is not None:
                os.utime(path, (stamp, stamp))


def evaluate_fixture(policy, kind: str, base: Path, *, today: str,
                     dir_exceptions: list[dict] | None = None,
                     record_exceptions: list[dict] | None = None,
                     retractions: list[dict] | None = None):
    rows, files = fixture(kind)
    write_fixture_root(base, rows, files,
                       stale_age_minutes=fixture_stale_age_minutes(policy, kind),
                       retractions=retractions)
    return evaluate(policy, rows, base / "runs", list(dir_exceptions or []),
                    list(record_exceptions or []), today=today,
                    retractions=retractions)


# ------------------------------------------------------------------ CLI 写入侧自检

def _load_agent_ops(agents_root: Path):
    """在进程内加载 `scripts/agent-ops.py`（`AGENT_OPS_DIR` 指向临时目录，不碰真实账本）。

    用**进程内**而不是子进程：退化时间戳的三种形态无法靠"跑两次真实 CLI"稳定复现
    （`_now()` 是秒级，两个进程可能跨秒），纯函数 + 直接驱动才是确定性判据
    （同 `verify_usage.py`/`verify_run_suite` 的"抽成纯函数以便断言直接驱动"做法）。
    """
    previous = os.environ.get("AGENT_OPS_DIR")
    os.environ["AGENT_OPS_DIR"] = str(agents_root)
    try:
        spec = importlib.util.spec_from_file_location("tg13_agent_ops", ROOT / "scripts" / "agent-ops.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            os.environ.pop("AGENT_OPS_DIR", None)
        else:
            os.environ["AGENT_OPS_DIR"] = previous
    return module


def _ns(**kwargs):
    import argparse

    return argparse.Namespace(**kwargs)


def run_cli_selfcheck(tmp: Path) -> None:
    """断言 CLI 侧真的"检测退化并标注 + 记测量来源"（TG-13 ③）。"""
    agents = tmp / "agents"
    module = _load_agent_ops(agents)
    report = tmp / "selfcheck.report.md"
    report.write_text("# CLI 自检报告\n\n无轮次标记。\n", encoding="utf-8")

    # ⓪ 纯函数：四类时间戳 → 测量来源/退化标记/时长
    cases = [
        (("2026-09-26T01:00:00+00:00", "2026-09-26T01:37:00+00:00"), "wall-clock", []),
        (("2026-09-26T01:00:00+00:00", "2026-09-26T01:00:00+00:00"), "declared", ["zero_duration"]),
        (("2026-09-26T01:00:00+00:00", "2026-09-26T01:10:00+00:00"), "declared", ["round_duration"]),
        ((None, None), "unknown", ["missing_timestamp"]),
    ]
    got = [module.measurement_of(*ts) for ts, _, _ in cases]
    ok("CLI 自检 ⓪ measurement_of 纯函数四例（墙钟/相同/整十分钟/缺失）→ 来源/退化标记/时长正确"
       "（退化读数不进测量字段 → dur=None）",
       [(src, flags) for src, flags, _ in got] == [(src, flags) for _, src, flags in cases]
       and [dur for _, _, dur in got] == [37.0, None, None, None],
       f"got={got}")

    # ① register --start → 尚无 ended_at → 必须 unknown/null（不是 0.00）
    module.cmd_register(_ns(run_id="run-2026-09-26-impact-assessment-950", role="impact-assessment",
                            task="cli-selfcheck", spec="impact-assessment@1.4.4", model="", start=True,
                            input_chars=None, context_input_tokens=None, context_max_tokens=None,
                            scope_source="", deviation="", coverage_anchor=""))
    row = module._load_registry()["runs"][0]
    ok("CLI 自检 ① register --start 写入 measurement_source=unknown 且 dur_minutes=null（缺值不得写 0.00）",
       row.get("measurement_source") == "unknown" and row.get("dur_minutes") is None
       and row.get("measurement_flags") == [],
       f"source={row.get('measurement_source')} dur={row.get('dur_minutes')}")

    # ② finish → 墙钟实测（正常时长）→ wall-clock + dur_minutes 与时间戳一致
    import time as _time

    _time.sleep(1.2)
    module.cmd_finish(_ns(run_id=row["run_id"], status="succeeded", output_chars=1200, result_file=None,
                          cost_override=None, error="", usage_in=None, usage_out=None,
                          usage_cache_read=None, usage_cache_write=None, covers_through=""))
    row = module._load_registry()["runs"][0]
    finish_dur = float(row.get("dur_minutes"))
    expected = duration_minutes(row)
    ok("CLI 自检 ② finish 写入 wall-clock + dur_minutes（与墙钟时间戳一致）且无退化标记",
       row.get("measurement_source") == "wall-clock" and row.get("measurement_flags") == []
       and expected is not None and abs(finish_dur - expected) < 1e-3,
       f"source={row.get('measurement_source')} dur={row.get('dur_minutes')} 期望={expected:.4f}")

    # ③ round → 刷新（ended_at 前移 → dur 必须随之刷新，否则就是"记了但没测量"）
    _time.sleep(1.2)
    module.cmd_round(_ns(run_id=row["run_id"], note="第二轮追加", output_chars=300, interrupted=False,
                         by="main-agent", impact="", usage_in=None, usage_out=None))
    row = module._load_registry()["runs"][0]
    ok("CLI 自检 ③ round 追加后 dur_minutes 随 ended_at 前移而刷新（累计墙钟口径）",
       row.get("measurement_source") == "wall-clock"
       and abs(float(row.get("dur_minutes")) - duration_minutes(row)) < 1e-3
       and float(row["dur_minutes"]) > finish_dur,
       f"dur {finish_dur} → {row.get('dur_minutes')} 分钟, rounds={row.get('rounds_count')}")

    # ④ 退化标注的写入路径：手造一行（用 CLI 自己的完整性算法，保证账本可被 CLI 读回）
    data = module._load_registry()
    data["runs"].append({"run_id": "run-2026-09-26-impact-assessment-951", "role": "impact-assessment",
                         "task_id": "fixture", "spec_source": "impact-assessment@1.4.4", "status": "running",
                         "started_at": "2026-09-26T03:00:00+00:00", "ended_at": "2026-09-26T03:00:00+00:00",
                         "input_chars": 0, "output_chars": 0, "usage": {}, "result_files": [], "tags": {}})
    data["integrity"] = module._integrity(data)
    module._save_registry(data)
    ok("CLI 自检 ④ 人工写的退化行（started==ended）被识别为 zero_duration（写入侧重算 + 闸门兜底）",
       degeneracy(module._load_registry()["runs"][1], 10) == ["zero_duration"], "zero_duration")


def run_cli_retract_selfcheck(policy, tmp: Path, *, today: str) -> None:
    """行 19 正向样本：**真 CLI** 撤回一条 run，再用本闸门判同一份数据（零 problem）。

    为什么走 CLI 而不是手工造目录：写盘路径（`runs/<id>/` → `runtime/retracted-runs/<id>/`）
    只有一处实现（`agent-ops.py::cmd_retract`）；这里手工造目录等于**测自己造的样本**，
    而且会给本文件新增动态写盘落点（`artifact_paths` 的动态目标棘轮只许下调）。
    `--result-file` 的来源用**已存在的仓库文件**（读，不写）——
    避免为了造一个"产物"再添一个落点。
    """
    agents = tmp / "agents-row19"
    module = _load_agent_ops(agents)
    rid = _exempted_local("run-2026-09-26-impact-assessment-960")
    module.cmd_register(_ns(run_id=rid, role="impact-assessment", task="row19-probe",
                            spec="impact-assessment@1.4.4", model="", start=True,
                            input_chars=None, context_input_tokens=None,
                            context_max_tokens=None, scope_source="", deviation="",
                            coverage_anchor=""))
    module.cmd_finish(_ns(run_id=rid, status="succeeded", output_chars=10,
                          result_file=str(Path(__file__).resolve()), cost_override=None,
                          error="", usage_in=None, usage_out=None, usage_cache_read=None,
                          usage_cache_write=None, covers_through="",
                          allow_degenerate=True,
                          degenerate_reason="fixture: 同秒收尾，非真实测量（行 19 样本）"))
    run_dir = agents / "runs" / rid
    ok("CLI 自检 ⑦ 行 19 前置：撤回前该 run 有产物目录、账本行仍在"
       "（前置不成立则本条判据未被触发 ⇒ 不作数）",
       run_dir.is_dir() and any(r.get("run_id") == rid for r in load_runs(agents)),
       f"runs/{rid}/ 存在={run_dir.is_dir()}")
    evidence = agents / "runs" / rid / "impact-assessment.report.md"
    module.cmd_retract(_ns(run_id=rid,
                           reason="探针误写入生产账本（行 19 自检样本）",
                           evidence=str(evidence), by="main-agent"))
    rows, retr = load_runs(agents), load_retractions(agents)
    problems, _, _ = evaluate(policy, rows, agents / "runs", [], [],
                              today=today, retractions=retr)
    q = str((retr[0] if retr else {}).get("quarantine") or "")
    ok("CLI 自检 ⑦ 行 19 正向：真 CLI 撤回后，闸门对同一份数据判**零 problem**"
       "（行已删、留痕七字段齐、产物在隔离区且不在 `runs/`）",
       problems == [] and len(retr) == 1
       and not any(r.get("run_id") == rid for r in rows)
       and q and (agents / q).is_dir() and not run_dir.exists(),
       f"problems={problems[:1]} retr={len(retr)} quarantine={q!r}")


def cli_list_lines(module, limit: int | None = None) -> list[str]:
    """跑一次 `list` 并抓回 stdout 行（用于断言展示层的 unknown 口径）。"""
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        module.cmd_list(_ns(status=None, role=None, limit=limit))
    return buffer.getvalue().splitlines()


def run_cli_display_selfcheck(tmp: Path) -> None:
    """`list` 的展示口径：无时间戳 → `dur=unknown`（不得打印 dur=0.0），且带测量来源。"""
    agents = tmp / "agents-display"
    module = _load_agent_ops(agents)
    data = {"version": 1, "runs": [
        {"run_id": "run-2026-09-26-impact-assessment-952", "role": "impact-assessment", "task_id": "x",
         "spec_source": "impact-assessment@1.4.4", "status": "succeeded", "started_at": None, "ended_at": None,
         "input_chars": 0, "output_chars": 10, "usage": {}, "result_files": [], "tags": {},
         "measurement_source": "unknown", "dur_minutes": None},
        {"run_id": "run-2026-09-26-impact-assessment-953", "role": "impact-assessment", "task_id": "y",
         "spec_source": "impact-assessment@1.4.4", "status": "succeeded",
         "started_at": "2026-09-26T04:00:00+00:00", "ended_at": "2026-09-26T04:25:00+00:00",
         "input_chars": 0, "output_chars": 10, "usage": {}, "result_files": [], "tags": {},
         "measurement_source": "wall-clock", "dur_minutes": 25.0},
    ]}
    data["integrity"] = module._integrity(data)
    (agents / "runtime").mkdir(parents=True, exist_ok=True)
    module._save_registry(data)
    lines = cli_list_lines(module)
    unknown_line = next((ln for ln in lines if "952" in ln), "")
    wall_line = next((ln for ln in lines if "953" in ln), "")
    ok("CLI 自检 ⑤ list 对缺时间戳的行打印 dur=unknown（不是 0.0/留空）",
       "dur=unknown" in unknown_line and "dur=0.0" not in unknown_line, unknown_line.strip()[:110])
    ok("CLI 自检 ⑥ list 打印测量来源（msrc=unknown / wall-clock）",
       "msrc=unknown" in unknown_line and "msrc=wall-clock" in wall_line, wall_line.strip()[:110])


# ------------------------------------------------------------------ 入口

def report(policy, runs: list[dict], runs_dir: Path, problems: list[str], warnings: list[str],
           counts: dict[str, int], *, label: str) -> int:
    caps = policy.ledger_caps()
    cutoff = policy.ledger_cutoff_local_date()
    window_start = ledger_close_window(policy, runs)
    n_dirs = (len([p for p in runs_dir.iterdir() if p.is_dir()])
              if runs_dir.is_dir() else "-")
    print(f"-- {label}：agents 根={runs_dir.parent}｜账本 {len(runs)} 条"
          f"｜目录 {n_dirs} 个")
    print(f"   判定域：{ratchet_domain_note(window_start, cutoff)}")
    print(f"   棘轮基线（{policy.ledger_measurement['legacy_ratchet'].get('measured_at')} 实测，"
          f"review_by {policy.ledger_review_by()}）："
          + " ".join(f"{k}={counts.get(k, 0)}/{caps.get(k)}" for k in sorted(caps)))
    for line in warnings:
        warn("棘轮放行（历史债，到期须重评）", line)
    if problems:
        print(f"LEDGER-MEASUREMENT FAIL（{len(problems)} 项）：")
        for item in problems:
            print(f"  - {item}")
        return 1
    print(f"LEDGER-MEASUREMENT PASS：{label}"
          f"（棘轮域内 {sum(counts.values())} 例全部在上限内，窗口内 run 零违规）")
    return 0


def exceptions_path(agents_root: Path, policy) -> Path:
    """目录/记录例外白名单的位置：`<agents 根>/policy/<政策声明的文件名>`。

    真实仓库里 agents 根就是 `agents/`，于是这条路径正好等于政策键
    `ledger_measurement.run_dir_exceptions_file` 指向的文件；
    而反向对照样本（`%TEMP%` 下的
    合成 agents 根）没有政策目录 → **无例外**，否则仓库的历史白名单会被套到合成数据上，
    把"干净样本"判成"白名单条目失效"（假红——反向对照最容易被自己骗到的地方）。
    """
    name = Path(str(policy.ledger_measurement["run_dir_exceptions_file"])).name
    candidate = agents_root / "policy" / name
    if candidate.is_file():
        return candidate
    repo_default = ROOT / str(policy.ledger_measurement["run_dir_exceptions_file"])
    if agents_root.resolve() == (ROOT / "agents").resolve():
        return repo_default
    return candidate


def real_data(agents_root: Path, policy) -> int:
    runs = load_runs(agents_root)
    retractions = load_retractions(agents_root)
    runs_dir = agents_root / "runs"
    exc_path = exceptions_path(agents_root, policy)
    dir_exc, rec_exc = load_exceptions(exc_path)
    print(f"   白名单：{exc_path}{'' if exc_path.is_file() else '（不存在 → 无例外）'}")
    if retractions:
        # 撤回是**改判定域**的动作 ⇒ 必须可见（不许静默少一行）
        named = ", ".join(str(i.get("run_id") or "?") for i in retractions)
        print(f"   撤回留痕：{len(retractions)} 条（{named}）"
              f"——每条含 reason/evidence，产物在 quarantine 指向的隔离区")
    problems, warnings, counts = evaluate(policy, runs, runs_dir, dir_exc, rec_exc,
                                          today=datetime.now(PROJECT_TZ).strftime("%Y-%m-%d"),
                                          retractions=retractions)
    label = "真实账本" if agents_root.resolve() == (ROOT / "agents").resolve() else f"agents 根 {agents_root}"
    return report(policy, runs, runs_dir, problems, warnings, counts, label=label)


def real_ledger_present(agents_root: Path) -> bool:
    """本机有没有可判定的账本（`<agents 根>/runtime/registry.json` 是否存在）。

    `agents/runtime/registry.json` 被 `.gitignore` 忽略（`agents/runtime/*`）
    ⇒ **CI 的全新
    checkout 必然没有它**。旧实现一律 fail-closed（`_read_json` 里 rc=2），
    于是这个 offline
    档闸门在干净 checkout 上**恒红**，还把「Offline verify suite」整步拖红（C3，
    2026-09-25 code-review-072）。

    **两种"没有"必须分开**：
      * 文件**不存在** = 本环境没有账本可比（fresh clone）→ 显式 SKIP（rc=0），理由上屏；
      * 文件**存在但坏**（JSON 非法 / 缺 `runs` / 结构非法）→ **照旧 fail-closed（rc≠0）**：
        坏账本是真缺陷，跳过它等于把"失真的可观测性"放行——那正是本闸门存在的理由。
    """
    return (agents_root / "runtime" / "registry.json").is_file()


def print_ledger_skip(agents_root: Path) -> None:
    """显式、响亮的 SKIP 行（说清"跳过了什么、为什么、判据边界在哪"）。"""
    print("SKIP: 账本不存在（fresh clone；registry.json 被 .gitignore 忽略）"
          "→ 该闸门只在本机/有账本的环境执行")
    print(f"      agents 根={agents_root}｜期望路径="
          f"{agents_root / 'runtime' / 'registry.json'}")
    print("      边界：**缺失**= 无可判定对象 → SKIP rc=0；"
          "**存在但 JSON 非法/结构非法**仍 fail-closed rc≠0（不静默放行）")


def selfcheck(policy) -> None:
    """内置自检：干净 fixture 必须过 + 各类反向对照必须 FAIL。

    守卫面：判定域（窗口/回退域）、在飞、棘轮两方向、白名单、测量契约。
    """
    today = datetime.now(PROJECT_TZ).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory(prefix="verify_ledger_measurement_") as td:
        tmp = Path(td)
        base = tmp / "clean"
        problems, warnings, counts = evaluate_fixture(policy, "clean", base, today=today)
        ok("自检 ① 干净 fixture（窗口内 run + 在飞 run，字段齐全）→ 零 problem",
           problems == [], f"problems={problems[:2]} counts={counts}")

        # ①' 判定域真的由**窗口**推导（M2）：作用域 run 定义起点，评审 run 落在窗口内
        window = ledger_close_window(policy, FIXTURE_ROWS)
        in_window = not in_ratchet_domain(FIXTURE_ROWS[1], window_start=window,
                                          cutoff=today)
        ok("自检 ①' 判定域来自账本侧关闭窗口（作用域 run 的 started_at）",
           window == FIXTURE_ROWS[0]["started_at"] and in_window,
           f"window={window} review_in_window={in_window}")

        for kind, expect, name in (
            ("same-timestamp", "zero_duration",
             "② **窗口内**零时长（反向对照 a：真缺陷照旧 FAIL）"),
            ("missing-dir", "records_without_dir", "③ 缺目录（有记录无目录）"),
            ("rounds-mismatch", "rounds_mismatch", "④ rounds 与报告轮次不符"),
            ("terminal-not-written-back", "terminal_not_written_back",
             "⑤ 停摆：报告已超出在飞宽限期仍不写回"),
            ("orphan-dir", "dirs_without_record", "⑥ 反向：有目录无记录"),
        ):
            target = tmp / kind
            problems, _, _ = evaluate_fixture(policy, kind, target, today=today)
            hit = [p for p in problems if f"[{expect}]" in p or f"[A/{expect}]" in p]
            ok(f"反向对照 {name} → FAIL 且点名 {expect}", bool(hit) and bool(problems),
               f"problems={problems[:1]}")

        # ⑤' 在飞（反向对照 c）：报告**刚写完**、finish 未调用 → 不得算终态未写回
        problems, _, _ = evaluate_fixture(policy, "in-flight-report", tmp / "in-flight",
                                         today=today)
        ok("反向对照 ⑤' 在飞 run（报告已写、finish 未调用，宽限期内）→ "
           "**不计** terminal_not_written_back"
           "（spec 强制先写报告后 finish，把这一瞬当缺陷是与工作流互斥的假红）",
           problems == [], f"problems={problems[:1]}")

        # ⑦⑧ 白名单：缺 reason / 过期条目
        problems, _, _ = evaluate_fixture(policy, "clean", tmp / "exc-noreason", today=today,
                                          dir_exceptions=[{"dir": "wrapper-scratch"}])
        ok("反向对照 ⑦ 白名单条目不写 reason → FAIL", any("缺 reason" in p for p in problems),
           f"problems={problems[:1]}")
        problems, _, _ = evaluate_fixture(
            policy, "clean", tmp / "exc-stale", today=today,
            dir_exceptions=[{"dir": FIXTURE_REVIEW_ROW,
                             "reason": "过期例外样本：该目录已是账本 run"}])
        ok("反向对照 ⑧ 白名单条目已不再需要（目录就是账本 run）→ FAIL（例外只减不增）",
           any("必须删除" in p for p in problems), f"problems={problems[:1]}")

        # ⑨⑩⑪ 棘轮基线本身不得被静默关掉
        saved = policy.policy_file["ledger_measurement"]["legacy_ratchet"]["caps"]
        try:
            policy.policy_file["ledger_measurement"]["legacy_ratchet"]["caps"] = \
                {k: v for k, v in saved.items() if k != "rounds_mismatch"}
            problems, _, _ = evaluate_fixture(policy, "clean", tmp / "cap-missing", today=today)
            ok("反向对照 ⑨ 棘轮 caps 少一类 → FAIL（少一条上限 = 该类无限放行）",
               any("caps 缺" in p for p in problems), f"problems={problems[:1]}")
            policy.policy_file["ledger_measurement"]["legacy_ratchet"]["caps"] = {**saved, "zero_duraton": 9}
            problems, _, _ = evaluate_fixture(policy, "clean", tmp / "cap-typo", today=today)
            ok("反向对照 ⑩ 棘轮 caps 多出拼错的键 → FAIL（上限表与判据不同步）",
               any("caps 多出" in p for p in problems), f"problems={problems[:1]}")
        finally:
            policy.policy_file["ledger_measurement"]["legacy_ratchet"]["caps"] = saved
        saved_by = policy.policy_file["ledger_measurement"]["legacy_ratchet"]["review_by"]
        try:
            policy.policy_file["ledger_measurement"]["legacy_ratchet"]["review_by"] = "2026-01-01"
            problems, _, _ = evaluate_fixture(policy, "clean", tmp / "cap-expired", today=today)
            ok("反向对照 ⑪ 棘轮 review_by 过期 → FAIL（必须重评基线，过期豁免不得继续放行）",
               any("已过期" in p for p in problems), f"problems={problems[:1]}")
        finally:
            policy.policy_file["ledger_measurement"]["legacy_ratchet"]["review_by"] = saved_by

        # ⑫⑬ 棘轮两个方向：限内只 WARN、超限 FAIL（反向对照 b：窗口之前的同形状 run）
        problems, warnings, counts = evaluate_fixture(policy, "legacy-within-cap",
                                                      tmp / "cap-within", today=today)
        ok("自检 ⑫ **窗口之前**的同形状缺陷在棘轮上限内（3 = 上限）→ 不 FAIL，"
           "但逐条 WARN 点名（棘轮真的在放行，不是永远红）",
           problems == [] and counts["zero_duration"] == 3 and len(warnings) == 3,
           f"problems={problems[:1]} counts={counts} warns={len(warnings)}")
        problems, _, counts = evaluate_fixture(policy, "legacy-overflow",
                                               tmp / "cap-overflow", today=today)
        ok("反向对照 ⑬ 历史缺陷**超上限**（4 > 3）→ FAIL 且点名条数与上限",
           any("4 例 > 上限 3" in p for p in problems), f"problems={problems[:1]}")

        # ⑬' 窗口不可推导 → **回退域**（日期域）且输出点名（回退是放宽方向，必须可见）
        fb_rows, _ = fixture("fallback-domain")
        fb_window = ledger_close_window(policy, fb_rows)
        problems, warnings, counts = evaluate_fixture(policy, "fallback-domain",
                                                      tmp / "fallback", today=today)
        ok("反向对照 ⑬' 关闭窗口推导不出（无带 started_at 的作用域 run）→ "
           "退回日期域且**点名回退域**（回退域下窗口前的 3 例仍在限内）",
           fb_window is None and "回退域" in ratchet_domain_note(fb_window, today)
           and problems == [] and counts["zero_duration"] == 3,
           f"window={fb_window} problems={problems[:1]} "
           f"counts={counts.get('zero_duration')}")

        # ⑭-⑳ 窗口内 run 的测量契约（每类都要能被单独命中；变异打在窗口内评审 run）
        mutants = _exempted_local([
            ("msrc-missing", "measurement_source_missing", {"measurement_source": None}, "缺测量来源"),
            ("msrc-invalid", "measurement_source_invalid", {"measurement_source": "wallclock"}, "非法取值"),
            ("dur-missing", "dur_minutes_missing", {"__del__": "dur_minutes"}, "缺 dur_minutes"),
            ("dur-rewritten", "dur_minutes_inconsistent", {"dur_minutes": 12.0}, "dur_minutes 被改写"),
            ("declared-with-value", "degenerate_value_stored",
             {"measurement_source": "declared", "dur_minutes": 0.0}, "声明值写进测量字段（0.00 冒充）"),
            ("unknown-not-declared", "unknown_not_declared",
             {"started_at": None, "ended_at": None, "measurement_source": "declared", "dur_minutes": None},
             "缺值不标 unknown"),
            ("not-wall-clock", "measurement_not_wall_clock",
             {"ended_at": "2026-09-26T01:00:00+00:00", "measurement_source": "wall-clock",
              "dur_minutes": None}, "时间戳退化（dur 0.00）却声称 wall-clock 实测"),
            ("round-duration", "round_duration",
             {"ended_at": "2026-09-26T01:10:00+00:00", "measurement_source": "declared", "dur_minutes": None},
             "dur 恰为整十分钟"),
            ("no-result-files", "missing_result_files_review", {"result_files": []}, "评审类无 result_files"),
            ("zero-output", "output_chars_zero", {"output_chars": 0}, "succeeded 但 output_chars=0"),
        ])
        for tag, expect, patch, label in mutants:
            rows, files = fixture("clean")
            review = next(i for i, r in enumerate(rows)
                          if r["run_id"] == FIXTURE_REVIEW_ROW)
            row = dict(rows[review])
            if "__del__" in patch:
                row.pop(patch["__del__"], None)
            else:
                row.update({k: v for k, v in patch.items()})
            rows[review] = row
            target = tmp / tag
            write_fixture_root(target, rows, files)
            problems, _, _ = evaluate(policy, rows, target / "runs", [], [],
                                      today=today)
            ok(f"反向对照 ⑭ {label} → FAIL 且点名 {expect}",
               any(p.startswith(f"[{expect}]") or f"[棘轮/{expect}]" in p for p in problems),
               f"problems={problems[:1]}")

        # 行 18：具名豁免的**理由必须落账本**（`degenerate_reason`）。
        # 变异打在窗口内评审 run 上，且让该行**当前真的退化**（ended_at = started_at）——
        # 否则 `degenerate_reason_missing` 不该触发
        # （那正是 run-092 的形态，见 F 组注释）。
        # 注意：理由**不豁免退化本身**（该行照旧被 `[zero_duration]` 点名）——
        # 正向样本断的是"本条新判据不点名"，不是"整行零 problem"。
        reason18 = _exempted_local("probe: 同秒收尾，非真实测量（行 18 正向样本）")
        for tag, patch, expect, label in _exempted_local([
            ("r18-ok", {"degenerate_reason": reason18}, None,
             "declared + 当前退化 + 理由 → 本条不点名"
             "（且理由不豁免退化本身）"),
            ("r18-missing", {}, "degenerate_reason_missing",
             "declared + 当前退化但**缺理由** → FAIL（理由不得只上屏）"),
        ]):
            rows, files = fixture("clean")
            idx = next(i for i, r in enumerate(rows)
                       if r["run_id"] == FIXTURE_REVIEW_ROW)
            row = {**rows[idx], "ended_at": rows[idx]["started_at"],
                   "measurement_source": "declared", "dur_minutes": None,
                   "measurement_flags": ["zero_duration"], **patch}
            rows[idx] = row
            target = tmp / tag
            write_fixture_root(target, rows, files)
            problems, _, _ = evaluate(policy, rows, target / "runs", [], [],
                                      today=today)
            if expect is None:
                ok(f"自检 ㉑ 行 18 {label}",
                   row["ended_at"] == row["started_at"]
                   and not any(p.startswith("[degenerate_reason_missing]")
                               for p in problems)
                   and any(p.startswith("[zero_duration]") for p in problems),
                   f"problems={problems[:2]}")
            else:
                ok(f"反向对照 ㉑ 行 18 {label}",
                   any(p.startswith(f"[{expect}]") for p in problems),
                   f"problems={problems[:1]}")
        rows, files = fixture("clean")
        idx = next(i for i, r in enumerate(rows) if r["run_id"] == FIXTURE_REVIEW_ROW)
        rows[idx] = {**rows[idx], "degenerate_reason": reason18}
        target = tmp / "r18-orphan"
        write_fixture_root(target, rows, files)
        problems, _, _ = evaluate(policy, rows, target / "runs", [], [], today=today)
        ok("反向对照 ㉑ 行 18 无退化标记却带 `degenerate_reason`"
           " → FAIL（字段与事实不符）",
           any(p.startswith("[degenerate_reason_orphan]") for p in problems),
           f"problems={problems[:1]}")

        # 行 19：撤回留痕（`retractions[]`）——删行必须留痕、产物必须保全。
        # 正向样本走**真 CLI**（`agent-ops.py retract`：写盘全在 CLI 侧，本闸门只读它）
        # 见 `run_cli_retract_selfcheck()`；下面三条反向对照只改**读入的数据**
        # （`write_fixture_root(..., retractions=...)` 复用既有写盘点，不新增落点——
        # `verify_artifact_paths.py` 的动态目标棘轮只许下调）。
        retr_ok = _exempted_local([{
            "at": "2026-09-27T00:30:00+00:00", "by": "probe",
            "run_id": FIXTURE_REVIEW_ROW,
            "reason": "探针误写入生产账本；正确形态是隔离账本 AGENT_OPS_DIR=%TEMP%",
            "evidence": "probe-receipt.md",
            "status_at_retraction": "succeeded",
            "quarantine": f"runtime/retracted-runs/{FIXTURE_REVIEW_ROW}"}])

        def _retract_case(tag: str, *, keep_row: bool, retr: list[dict]) -> list[str]:
            rows, files = fixture("clean")
            if not keep_row:
                rows = [r for r in rows if r["run_id"] != FIXTURE_REVIEW_ROW]
                files.pop(FIXTURE_REVIEW_ROW, None)
            target = tmp / tag
            write_fixture_root(target, rows, files, retractions=retr)
            problems, _, _ = evaluate(policy, rows, target / "runs", [], [],
                                      today=today, retractions=retr)
            return problems

        pm = _retract_case("r19-live", keep_row=True, retr=retr_ok)
        ok("反向对照 ㉒ 行 19 已留痕撤回、账本行却还在"
           " → FAIL（撤回不完整，污染仍在域里）",
           any("撤回不完整" in p for p in pm), f"problems={pm[:1]}")
        pm = _retract_case("r19-short", keep_row=False,
                           retr=_exempted_local([{**retr_ok[0], "reason": "太短"}]))
        ok("反向对照 ㉒ 行 19 理由 <10 字符 → FAIL（说不清为什么撤回 = 不受控的删除）",
           any("10" in p and "撤回" in p for p in pm), f"problems={pm[:1]}")
        pm = _retract_case("r19-noq", keep_row=False, retr=retr_ok)
        ok("反向对照 ㉒ 行 19 留痕写了隔离路径但该路径不存在 → FAIL（产物没被保全）",
           any("产物没被保全" in p for p in pm), f"problems={pm[:1]}")

        # CLI 侧自检也在本临时目录内（临时目录在 `with` 退出时即被删除 → 必须在块内跑）
        run_cli_selfcheck(tmp)
        run_cli_display_selfcheck(tmp)
        run_cli_retract_selfcheck(policy, tmp, today=today)


def main() -> int:
    argv = sys.argv[1:]
    try:
        policy = load_policy()
    except PolicyError as exc:
        print(f"LEDGER-MEASUREMENT-ERROR: {exc}")
        return 2

    if "--emit-fixture" in argv:
        kind = argv[argv.index("--emit-fixture") + 1]
        if "--agents-root" not in argv:
            print("LEDGER-MEASUREMENT-ERROR: --emit-fixture 需要 --agents-root <dir>"
                  "（样本一律写 %TEMP%，不得写进仓库）")
            return 2
        base = Path(argv[argv.index("--agents-root") + 1]).resolve()
        rows, files = fixture(kind)
        write_fixture_root(base, rows, files,
                           stale_age_minutes=fixture_stale_age_minutes(policy, kind))
        print(f"FIXTURE {kind} → {base}（{len(rows)} run / {len(files)} 目录）")
        return 0

    if "--agents-root" in argv:
        base = Path(argv[argv.index("--agents-root") + 1]).resolve()
        return real_data(base, policy)

    # 真实数据先跑：**成功路径才打印成功行**（旧实现无论真实账本 rc 如何都打印
    # ALL PASS，屏幕上"最后的成功行"与退出码互相矛盾——本 Sprint 要治的失信形态）。
    # C3（2026-09-25 code-review-072）：账本**文件不存在**时走显式 SKIP（rc=0，
    # 理由上屏）——
    # 它被 .gitignore 忽略，CI 全新 checkout 必然没有；
    # **存在但坏**仍走 real_data 的 fail-closed。
    agents_root = ROOT / "agents"
    if real_ledger_present(agents_root):
        code = real_data(agents_root, policy)
    else:
        print_ledger_skip(agents_root)
        code = 0
    selfcheck(policy)
    if code == 0:
        print(f"\nALL PASS ({PASSED} assertions)")
        # TG-6：**只在成功路径**打印机读证据行（失败/SKIP 不打印——"跳过"不得冒充"通过"）
        print(f"EVIDENCE: verify_ledger_measurement.py assertions={PASSED} rc=0 "
              f"ledger={'present' if real_ledger_present(agents_root) else 'absent-skip'}")
    else:
        print(f"\nSELFCHECK PASS ({PASSED} assertions)，但**真实账本 FAIL**：rc={code}"
              f"（上面的逐条点名就是未通过项；本行不是成功行）")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
