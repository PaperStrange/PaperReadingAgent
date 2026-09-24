"""TG-15：政策数据加载器（数据驱动闸门的唯一入口）。

**为什么需要这个模块**（背景与判据见 `docs/iteration/phases/testing-governance/backlog.MD` 的 `TG-15` 卡）：

闸门原先靠"遇到一个场景加一条判据"成长——角色名写死在 `scripts/agent-ops.py`（`_REVIEW_ROLES`）、
`verify/verify_close_readiness.py`（`CLOSE_ROLES`）、`verify/verify_agentops.py`（又一份），
覆盖路径写死在 `verify/verify_lint.py`（`DEFAULT_PATHS`），归档识别写死在 `scripts/report-freshness.py`
（`startswith("tech-research")`），阈值写死在 `agent-ops`（`_MIN_DEVIATION_CHARS`）。
后果：**加一个角色 / 换一个分支 / 改一个步骤都要改代码**，而改代码这件事本身没有任何闸门在守。

本模块把"哪些角色要声明 scope""关闭必须跑哪些步骤/目标""阈值多少"全部**从数据读取**：

  数据源 1  `agents/fanout.json::sprint_close_pipeline`  —— 关闭流水线的步骤 / role / targets / ledger 标记
  数据源 2  各角色 spec（`agents/functions/<role>.md`）的 YAML frontmatter —— `scope_required` 等角色属性
  数据源 3  `agents/policy.json`（本卡新增）—— 不可从上述两者推导的**阈值与开关**（偏离理由最小长度、
            覆盖路径清单、归档识别开关、范围声明的引用前缀）

**没有循环依赖**（这是本卡最容易做错的地方）。`TG-15` ① 的三条不变式是**内部判据**，
不是数据：数据只提供"哪些对象需要满足哪条不变式"，对象本身（账本里的 run、`git rev-list` 的提交）
由闸门独立枚举。因此"把 `scope_required` 删掉就能绕过 C1"这条路被两件事堵死：

  * **封闭世界**（`closure_problems()`）：凡出现在 `fanout.json` 或被 `spec_glob` 匹配到的 role，
    都必须同时被 `scope_required` 显式声明——**没声明就是错**，不是"不需要"；
  * **未登记 role 报警**：账本里出现 `spec_glob` 匹配不到 spec 的 role → C2 直接 FAIL。

所有数据文件缺失/字段缺失一律 **fail-closed**（抛 `PolicyError`），不静默回落常量——
静默回落正是"硬编码"复活的路径。
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 环境变量覆盖（测试与 CI 注入 fixture 用；优先级：env > agents/policy.json > 本文件兜底）
ENV_POLICY = "PAPERQA_AGENT_POLICY"
ENV_FANOUT = "PAPERQA_FANOUT"
ENV_SPEC_DIR = "PAPERQA_AGENT_SPECS"

# 兜底值**只在数据文件缺失时用于报错文案**，不作为运行时静默默认（见模块头）。
_FALLBACK = {
    "scope_min_deviation_chars": 10,
    "scope_ref_sources": ["impact-assessment:"],
    "lint_paths": [],
    "archive_role_prefix": "",
}


class PolicyError(SystemExit):
    """政策数据缺失/非法 —— fail-closed（退出码 2，与"验出了违规"的退出码 1 区分）。"""

    def __init__(self, msg: str):
        super().__init__(f"POLICY-ERROR: {msg}（TG-15：政策来自数据文件，不静默回落代码常量）")


def _read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise PolicyError(f"{label} 不存在：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyError(f"{label} JSON 非法：{path}: {exc}") from exc


def parse_frontmatter(path: Path) -> dict:
    """解析 spec 的 YAML frontmatter（**复用 `agent-ops.py validate-spec` 同款宽松解析**：
    逐行 `key: value`，不做完整 YAML——两条路径必须同口径，否则"验得过"与"读得到"会分叉）。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def _as_bool(raw: str | bool | None, *, field: str = "?", where: str = "?") -> bool | None:
    """解析布尔声明。**不给"拼错即 False"留活口**（2026-09-23 二查 major）：
    `_as_bool("ture")` 旧实现静默返回 False ⇒ 该角色**静默退出 C1 声明完备性检查**——
    一个拼写错误就能关掉一条闸门，这正是"数据驱动闸门"最该防的失效形态。现在非法取值直接报错。
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    val = str(raw).strip().lower()
    if val == "":
        return None
    if val in {"true", "yes", "1", "on"}:
        return True
    if val in {"false", "no", "0", "off"}:
        return False
    raise PolicyError(f"{where} 的 {field}={raw!r} 不是合法布尔值（合法：true/false/yes/no/1/0/on/off）"
                      f"——拼错不会静默降级，请修正数据文件")


COVERAGE_WINDOW_VALUES = ("self", "none")


@dataclass
class SpecRole:
    """一个角色 spec 的**声明**（数据源 2）。"""

    role: str
    path: Path
    scope_required: bool | None = None  # None = 未声明（封闭世界判为缺口）
    coverage_window: str | None = None  # "self" | "none"；None = 未声明（同上）
    source_block: dict = field(default_factory=dict)

    @property
    def declared(self) -> bool:
        """两个声明字段都在 → 该 spec 满足封闭世界要求。

        2026-09-23 doc-audit finding 2 修正：此前只把 `scope_required` 做成不变量，而 §3.1 的
        条文明写"两个字段都必须显式声明"，且 `coverage_window` 决定该 run **是否参与 C3 覆盖计算**
        ——也就是说缺它就没有任何东西能判定"这个 run 该不该覆盖"，这正是"文档承诺 > 实现"的形态。
        现把两个字段一起纳入不变量。
        """
        return self.scope_required is not None and self.coverage_window is not None

    @property
    def undeclared_fields(self) -> list[str]:
        missing = []
        if self.scope_required is None:
            missing.append("scope_required")
        if self.coverage_window is None:
            missing.append("coverage_window")
        return missing

    @property
    def participates_in_coverage(self) -> bool:
        return self.coverage_window == "self"


@dataclass
class CloseStep:
    """关闭流水线的一步（数据源 1）。`targets` 空 = 该步只要求"存在 run"。"""

    order: int
    step: str
    role: str
    spec: str
    targets: tuple[str, ...] = ()
    ledger: bool = False  # 该步是否产出账本 run（workspace-check 由主代理执行 → False）

    @property
    def label(self) -> str:
        return f"{self.role}" + (f"[{','.join(self.targets)}]" if self.targets else "")


@dataclass
class Policy:
    fanout: dict
    policy_file: dict
    spec_dir: Path
    steps: tuple[CloseStep, ...]
    specs: dict[str, SpecRole]
    allow_undeclared: bool = False

    # ---- 数据源 2 派生：角色属性 -------------------------------------------------
    @property
    def review_roles(self) -> set[str]:
        """**凡产出评审结论的 run**（= spec 声明 `scope_required: true`）→ 必须声明 scope 来源（C1）。"""
        return {r.role for r in self.specs.values() if r.scope_required is True}

    @property
    def scope_optional_roles(self) -> set[str]:
        """显式声明 `scope_required: false` 的角色（scope 不在该 role 的语义里）。"""
        return {r.role for r in self.specs.values() if r.scope_required is False}

    @property
    def undeclared_specs(self) -> list[str]:
        """被 spec_glob 枚举到但**没写全** `scope_required`/`coverage_window` 的 role（封闭世界缺口）。"""
        return sorted(r.role for r in self.specs.values() if not r.declared)

    @property
    def close_ledger_steps(self) -> tuple[CloseStep, ...]:
        return tuple(s for s in self.steps if s.ledger)

    def role_targets(self) -> dict[str, list[str]]:
        """role -> 关闭时必须覆盖的 target（多步同 role 合并；同 role 多 target 去重）。"""
        out: dict[str, list[str]] = {}
        for step in self.steps:
            if not step.ledger or not step.targets:
                continue
            bucket = out.setdefault(step.role, [])
            for t in step.targets:
                if t not in bucket:
                    bucket.append(t)
        return out

    # ---- 数据源 3：阈值与开关 ----------------------------------------------------
    def _data(self, key: str):
        if key not in self.policy_file:
            raise PolicyError(f"agents/policy.json 缺键 {key!r}")
        return self.policy_file[key]

    @property
    def md_table_legacy_files(self) -> dict[str, int]:
        """棘轮基线：`{相对路径: 缺陷数上限}`（历史既存债，见 policy 内说明）。

        A2（finding M-a/N2/R3，2026-09-25）：首版是**路径列表**，闸门只做路径比较 ⇒ 基线文件内
        **任意数量**的新缺陷全被吸收（实测：注入 200 处仍 `MD-TABLE PASS`）。现改为**按文件设上限**：
        `verify_md_tables.py` 对基线文件判 `len(found) > cap → FAIL`（棘轮只许变紧）。
        上限必须是正整数（`0` 也允许：表示该文件已清干净，不得再回退）。
        """
        val = self._data("md_table_legacy_files")
        files = val.get("files") if isinstance(val, dict) else val
        if not isinstance(files, dict):
            raise PolicyError(
                f"md_table_legacy_files.files 必须是 {{路径: 缺陷数上限}} 映射（A2 上限制），实际 {files!r}")
        out: dict[str, int] = {}
        for path, cap in files.items():
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
                raise PolicyError(
                    f"md_table_legacy_files.files[{path!r}] 的缺陷数上限必须是 ≥0 的整数，实际 {cap!r}"
                    f"——上限写错会让棘轮静默失效")
            out[str(path)] = cap
        return out

    @property
    def md_table_review_by(self) -> str:
        """棘轮基线的**到期日**（`YYYY-MM-DD`）。过期即 FAIL（提示"必须重评基线"）。

        为什么必须有到期日（R3）：没有到期日的豁免就是**永久豁免**——基线会变成"历史债合法化"的
        挡箭牌，而"重评"这件事不会有任何触发点。
        """
        val = self._data("md_table_legacy_files")
        raw = val.get("review_by") if isinstance(val, dict) else None
        text = str(raw or "").strip()
        # 严格 `YYYY-MM-DD`：闸门要按字典序比较日期，格式一乱比较就无意义（fail-closed，不猜）
        parts = text.split("-")
        if len(parts) != 3 or [len(p) for p in parts] != [4, 2, 2] or not all(p.isdigit() for p in parts):
            raise PolicyError(
                f"md_table_legacy_files.review_by 必须是 'YYYY-MM-DD'，实际 {raw!r}"
                f"——格式非法会让到期判定失去意义")
        return text

    @property
    def card_index(self) -> dict:
        """TG-14④ 卡索引 lint 的参数（必备节 / 指纹长度阈值 / 行级比对的最小行长）。

        2026-09-23：这些值最初写在 `verify/verify_card_index.py` 里，被
        `verify_no_policy_hardcode.py` 判为 R1（阈值硬编码）——**闸门又一次抓住了写闸门的人**。
        2026-09-25（A3/N7）：`body_prefix_chars`（只比前 N 字）被**含填充的副本**规避，
        改为全文行级指纹比对后由 `min_line_chars` 取代；两键都必须存在且为正整数。
        """
        val = self._data("card_index")
        for key in ("required_sections", "min_fingerprint_chars", "min_line_chars"):
            if key not in val:
                raise PolicyError(f"card_index 缺键 {key!r}")
        for key in ("min_fingerprint_chars", "min_line_chars"):
            raw = val[key]
            if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
                raise PolicyError(f"card_index.{key} 必须是正整数，实际 {raw!r}"
                                  f"——阈值写错会让 ④ 判据静默失效（这正是 N7 的形态）")
        return val

    @property
    def scope_min_deviation_chars(self) -> int:
        val = self._data("scope_min_deviation_chars")
        if not isinstance(val, int) or val <= 0:
            raise PolicyError(f"scope_min_deviation_chars 必须是正整数，实际 {val!r}")
        return val

    @property
    def scope_ref_sources(self) -> tuple[str, ...]:
        val = self._data("scope_ref_sources")
        if not isinstance(val, list) or not val:
            raise PolicyError(f"scope_ref_sources 必须是非空列表，实际 {val!r}")
        return tuple(str(v) for v in val)

    @property
    def lint_paths(self) -> tuple[str, ...]:
        val = self._data("lint_paths")
        if not isinstance(val, list) or not val:
            raise PolicyError(f"lint_paths 必须是非空列表，实际 {val!r}")
        return tuple(str(v) for v in val)

    @property
    def lint_rules(self) -> dict:
        val = self._data("lint_rules")
        for key in ("hard_a", "hard_b", "report_only"):
            if not str(val.get(key) or "").strip():
                raise PolicyError(f"lint_rules.{key} 缺失或为空（分级规则是政策数据）")
        return val

    @property
    def archive_role_prefix(self) -> str:
        return str(self._data("archive_role_prefix"))

    @property
    def md_table_targets(self) -> tuple[str, ...]:
        """Markdown 结构自检的目标集 = 显式文档 + glob 展开（`verify/verify_md_tables.py` 消费）。

        2026-09-23 两次被闸门/子代理抓到的覆盖缺口，都记在这里：
          ① 该清单最初写在新闸门文件里 → 被 `verify_no_policy_hardcode.py` 判为 R3（闸门先抓住了写闸门的人）；
          ② 首版只列了 `testing-governance/backlog.MD` 一个阶段文件 → **迁移新增的瘦索引与 95 个卡文件
             默认一个都不查**（P2 子代理实测指出）。现改为"显式文档 + glob"，新增阶段/卡文件自动纳入。

        A10（2026-09-25，finding N1）起本属性**不再是闸门的唯一入口**：`verify_md_tables.py` 为了做
        "应扫/实扫"双向差集，会分别读 `md_table_docs`/`md_table_globs` 并各自核对（显式路径必须存在、
        每条 glob 必须命中 ≥1 文件、两侧集合必须相等）。本属性保留为"合并后的目标集"这一语义的
        对外 API（等价于那两个集合的并集），不再被差值逻辑依赖。
        """
        docs = self._data("md_table_docs")
        globs = self._data("md_table_globs")
        for label, val in (("md_table_docs", docs), ("md_table_globs", globs)):
            if not isinstance(val, list) or not val:
                raise PolicyError(f"{label} 必须是非空列表，实际 {val!r}")
        out: list[str] = [str(p) for p in docs]
        for pattern in globs:
            out += sorted(str(p.relative_to(REPO_ROOT)).replace("\\", "/")
                          for p in REPO_ROOT.glob(str(pattern)) if p.is_file())
        # 去重保序
        seen: set[str] = set()
        return tuple(p for p in out if not (p in seen or seen.add(p)))

    @property
    def close_gate(self) -> dict:
        return self._data("close_gate")

    # ---- C2：指涉可核 ------------------------------------------------------------
    def unresolved_roles(self, roles) -> list[str]:
        """出现在运行数据（账本）里、但**解析不到 spec 对象**的 role → C2 FAIL。

        这是"不认角色名"的可执行形态：role 字符串不是自证的，它必须能落到一个真实存在的
        spec 文件；新增 role 若忘了建 spec（或改了名），这里立刻点名。
        """
        return sorted({r for r in roles if r and r not in self.specs})

    # ---- 封闭世界：声明完备性自检 -------------------------------------------------
    def closure_problems(self) -> list[str]:
        """数据源自身的完备性，**与数据源的具体取值无关**（`verify_no_policy_hardcode.py` 断言它为空）。

        1. `fanout.json` 的每个 ledger 步骤 role 必须有 spec；
        2. 每个被枚举的 spec 必须**显式**声明 `scope_required`（`allow_undeclared` 时降级为提示）；
        3. `policy.json` 不得残留未被任何代码读取的键（防"数据文件变成新的垃圾场"）。

        注意第 2 条为什么是**不变式**而不是"再看一眼的警告"：C1 的判据是"凡声明
        `scope_required: true` 的 run 必须有 scope 声明"——若允许"未声明"存在，它就同时
        从判据里消失（**删声明 = 关掉闸门**）。所以缺声明只能是**错误**。
        `allow_undeclared` 仅为一次性数据迁移开的口子（`PAPERQA_POLICY_ALLOW_UNDECLARED=1`），
        迁移脚本自带 `--check` 收口，运行时一律 fail-closed。
        """
        problems: list[str] = []
        for step in self.steps:
            if step.role not in self.specs:
                problems.append(
                    f"fanout.json 步骤 {step.order}:{step.step} 的 role={step.role!r} 没有对应 spec"
                    f"（{self.spec_dir}/<role>.md）")
        for role in self.undeclared_specs:
            spec = self.specs[role]
            msg = (f"{spec.path.name} 未声明 {'/'.join(spec.undeclared_fields)}"
                   f"（封闭世界：每个角色都必须显式声明 scope_required 与 coverage_window，"
                   f"缺声明不会让闸门放行，只会让闸门报错）")
            problems.append("[迁移期提示] " + msg if self.allow_undeclared else msg)
        for role, spec in sorted(self.specs.items()):
            if spec.coverage_window is not None and spec.coverage_window not in COVERAGE_WINDOW_VALUES:
                problems.append(
                    f"{spec.path.name} 的 coverage_window={spec.coverage_window!r} 非法"
                    f"（合法值 {list(COVERAGE_WINDOW_VALUES)}）——取值错误会让该 run 静默退出 C3 覆盖计算")
        # 3. 悬空键：闸门读不到的键 = 死数据
        consumed = {
            "version", "_comment", "spec_glob", "spec_dir", "scope_min_deviation_chars",
            "scope_ref_sources", "lint_paths", "lint_rules", "archive_role_prefix", "close_gate",
            "ledger_status", "md_table_docs", "md_table_globs", "md_table_legacy_files", "card_index",
            # A10（N1）：md_table_globs 的**范围声明**（roots/include_files），由 verify_md_tables.py 消费
            "md_table_coverage",
            # A11（N4）：豁免台账的校验参数（类别白名单/理由长度/作用域），由 verify_no_policy_hardcode.py 消费
            "hardcode_exemptions",
        }
        for key in self.policy_file:
            if key not in consumed:
                problems.append(f"agents/policy.json 存在无人读取的键 {key!r}（死数据 = 下一轮漂移源）")
        return problems



def _load_fanout(path: Path) -> tuple[dict, tuple[CloseStep, ...]]:
    data = _read_json(path, "agents/fanout.json")
    raw_steps = data.get("sprint_close_pipeline")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PolicyError(f"{path} 缺 sprint_close_pipeline（关闭流水线是 C1/C2 的需求来源）")
    steps: list[CloseStep] = []
    for item in raw_steps:
        if not isinstance(item, dict):
            raise PolicyError(f"{path} 的 sprint_close_pipeline 项必须是对象：{item!r}")
        role = str(item.get("role") or "").strip()
        if not role:
            raise PolicyError(f"{path} 的步骤缺 role：{item!r}")
        # targets：单任务用 task.target，多任务用 tasks[].target（两形态都支持，避免为旧数据加特例）
        targets: list[str] = []
        for t in ([item["task"].get("target")] if isinstance(item.get("task"), dict) else []):
            if t:
                targets.append(str(t))
        for t in (item.get("tasks") or []):
            if isinstance(t, dict) and t.get("target"):
                targets.append(str(t["target"]))
        steps.append(CloseStep(
            order=int(item.get("order") or len(steps) + 1),
            step=str(item.get("step") or role),
            role=role,
            spec=str(item.get("spec") or role),
            targets=tuple(targets),
            ledger=_as_bool(item.get("close_ledger"), field="close_ledger",
                            where=f"{path.name} 步骤 {item.get('step') or role}") or False,
        ))
    steps.sort(key=lambda s: s.order)
    return data, tuple(steps)


def load_policy(root: Path | None = None, *, spec_dir: Path | None = None,
                policy_path: Path | None = None, fanout_path: Path | None = None) -> Policy:
    """装载政策。三个数据文件任一缺失 → `PolicyError`（fail-closed）。"""
    root = Path(root) if root else REPO_ROOT
    policy_path = policy_path or Path(os.environ.get(ENV_POLICY, root / "agents" / "policy.json"))
    fanout_path = fanout_path or Path(os.environ.get(ENV_FANOUT, root / "agents" / "fanout.json"))

    policy_file = _read_json(policy_path, "agents/policy.json")
    fanout, steps = _load_fanout(fanout_path)

    # spec_dir：以 policy.json 为准，env 可覆盖（测试 fixture）
    raw_dir = os.environ.get(ENV_SPEC_DIR) or str(policy_file.get("spec_dir") or "agents/functions")
    base = Path(raw_dir)
    resolved_spec_dir = base if base.is_absolute() else (root / base)

    glob = str(policy_file.get("spec_glob") or "").strip()
    if not glob:
        raise PolicyError("agents/policy.json 缺 spec_glob（角色枚举靠它，不能靠代码里的角色名单）")
    name_glob = glob.split("/")[-1]
    if not resolved_spec_dir.is_dir():
        raise PolicyError(f"spec 目录不存在：{resolved_spec_dir}")

    specs: dict[str, SpecRole] = {}
    for path in sorted(resolved_spec_dir.iterdir()):
        if not path.is_file() or not fnmatch.fnmatch(path.name, name_glob):
            continue
        fm = parse_frontmatter(path)
        role = path.stem
        specs[role] = SpecRole(
            role=role,
            path=path,
            scope_required=_as_bool(fm.get("scope_required"), field="scope_required", where=path.name),
            coverage_window=(fm.get("coverage_window") or "").strip().lower() or None,
            source_block={k: v for k, v in fm.items() if k.startswith("source")} if "source" in fm else {},
        )
    if not specs:
        raise PolicyError(f"{resolved_spec_dir} 下没有任何 spec 匹配 {name_glob!r}")

    allow_undeclared = os.environ.get("PAPERQA_POLICY_ALLOW_UNDECLARED", "").strip().lower() in {"1", "true", "yes"}
    policy = Policy(fanout=fanout, policy_file=policy_file, spec_dir=resolved_spec_dir,
                    steps=steps, specs=specs, allow_undeclared=allow_undeclared)    # **封闭世界是运行时不变量**（不只是自检项）：spec 缺声明 = 数据缺口 = fail-closed。
    # 若只在"某些闸门的自检"里检查，普通命令（register/list）就会带着缺口照常运行，
    # 而缺口恰恰是"删声明关掉 C1"的入口（见 closure_problems 文档）。
    problems = [p for p in policy.closure_problems() if not p.startswith("[迁移期提示]")]
    if problems:
        raise PolicyError(
            "；".join(problems) + "｜修复：python scripts/migrate-scope-declarations.py"
            "（迁移期可临时设 PAPERQA_POLICY_ALLOW_UNDECLARED=1，但不得用于正常开发）")
    return policy


# --------------------------------------------------------------------------- git

def git(root: Path | None = None, *args: str, allow_fail: bool = False) -> str:
    """跑一条 git 命令（UTF-8 安全）。失败时返回空串（`allow_fail`）或抛错。"""
    root = Path(root) if root else REPO_ROOT
    r = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        if allow_fail:
            return ""
        raise PolicyError(f"git {' '.join(args)} 失败：{(r.stderr or '').strip()[:160]}")
    return r.stdout.strip()


def head_sha(root: Path | None = None) -> str:
    return git(root, "rev-parse", "HEAD", allow_fail=True)


def rev_list(root: Path | None, anchor: str, to: str = "HEAD") -> list[str]:
    """`git rev-list <anchor>..<to>`（新→旧）。anchor 非法时抛错，不静默当空。"""
    if not anchor:
        return []
    out = git(root, "rev-list", f"{anchor}..{to}")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def commit_files(root: Path | None, sha: str) -> list[str]:
    out = git(root, "show", "--pretty=format:", "--name-only", sha, allow_fail=True)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def commit_subject(root: Path | None, sha: str) -> str:
    return git(root, "log", "-1", "--pretty=%s", sha, allow_fail=True)


# ------------------------------------------------------------------ C3：覆盖闭环

@dataclass
class CoverageWindow:
    """一个 run 声明的覆盖窗口 `(anchor, through]`（左开右闭，与 `git rev-list a..b` 同口径）。"""

    run_id: str
    role: str
    anchor: str
    through: str
    from_run: bool  # True=账本自动记录；False=调用方显式传入（fixture/异常）

    def covers(self, sha: str, order: dict[str, int]) -> bool:
        """`order` = `{sha: index}`（**0 = HEAD/最新**，与 `git rev-list` 输出同序）。

        窗口 = `(anchor, through]`，即"比 anchor 新、且不新于 through"的提交：
            order[through] <= order[sha] < order[anchor]
        （序号越小越新，故 through 的序号是下界、anchor 的序号是上界，**左开右闭**与
        `git rev-list anchor..through` 同口径。）

        anchor/through 不在 `order` 里（= 超出本次计算范围，例如锚点比本地历史还老）
        时按 **不覆盖** 处理：fail-closed，宁可点名也不做乐观推断。
        """
        if self.anchor not in order or self.through not in order:
            return False
        upper, lower = order[self.anchor], order[self.through]
        return lower <= order[sha] < upper


def order_index(shas_newest_first: list[str]) -> dict[str, int]:
    return {sha: i for i, sha in enumerate(shas_newest_first)}


def coverage_windows_from_runs(runs, policy: "Policy | None" = None) -> list[CoverageWindow]:
    """从账本行构造覆盖窗口。**只认自动记录字段**（`coverage_anchor`/`covers_through`）。

    传入 `policy` 时按 spec 的 `coverage_window` 声明过滤：声明为 `none` 的角色
    （如 tech-research / workspace-check）**不参与 C3 覆盖计算**——这条此前只写在文档里，
    现由 `SpecRole.participates_in_coverage` 提供判据（doc-audit finding 2 的修法之一）。
    """
    out: list[CoverageWindow] = []
    for r in runs:
        role = str(r.get("role") or "")
        if policy is not None:
            spec = policy.specs.get(role)
            if spec is not None and not spec.participates_in_coverage:
                continue
        anchor = (r.get("coverage_anchor") or "").strip()
        through = (r.get("covers_through") or "").strip()
        if not anchor or not through:
            continue
        out.append(CoverageWindow(
            run_id=str(r.get("run_id") or "?"), role=role,
            anchor=anchor, through=through, from_run=True,
        ))
    return out


def attribution(root: Path | None, anchor: str, head: str, runs,
                exceptions: list[dict] | None = None,
                policy: "Policy | None" = None) -> "Attribution":
    """C3 覆盖闭环：`git rev-list <anchor>..<head>` 的**每个提交**必须有归属。

    归属来源（三选一）：
      1. run 窗口（`coverage_anchor`/`covers_through` 自动记录）——默认路径；
      2. C3-T 例外表（sha 钉死，见 `attribution.exceptions` 校验）；
      3. `doc-only` 自动归类（改动文件**全部**命中 `doc_only_globs`）——不覆盖未来提交。

    传 `policy` 时，声明 `coverage_window: none` 的角色不贡献窗口（判据同 `coverage_windows_from_runs`）。
    """
    shas = rev_list(root, anchor, head)
    order = order_index([head, *shas])
    windows = coverage_windows_from_runs(runs, policy)
    return Attribution(
        anchor=anchor, head=head, shas=shas, order=order, windows=windows,
        exceptions=list(exceptions or []),
        root=root,
    )


class Attribution:
    """一次覆盖归属计算的完整结果（`unowned` 非空 = C3 未闭环 → 闸门 FAIL 并逐条点名）。"""

    def __init__(self, *, anchor: str, head: str, shas: list[str], order: dict[str, int],
                 windows: list[CoverageWindow], exceptions: list[dict], root: Path | None):
        self.anchor = anchor
        self.head = head
        self.shas = shas
        self.order = order
        self.windows = windows
        self.exceptions = exceptions
        self.root = root
        self._files: dict[str, list[str]] = {}

    # -- 例外表校验（用户 P2 关切的"表过期"三件套之 (b)：sha 钉死，禁止通配） -------
    def window_problems(self) -> list[str]:
        """窗口自身的结构性缺陷（2026-09-23 二查 major #3）。

        实测：账本里 `covers_through="e6ccd257"`（**8 位短 sha**），而 `order` 里只有完整 sha
        → `covers()` 静默返回 False，该窗口**形同不存在**，却不报任何错。
        同理：(X, X] 是空区间（register 与 finish 都在同一 HEAD）——这两种都会让"自动覆盖"
        悄悄变成零，从而把 C3 的压力全推给例外表。**静默**正是要消灭的东西：这里逐条点名。
        """
        problems: list[str] = []
        full = 40
        for w in self.windows:
            for label, sha in (("coverage_anchor", w.anchor), ("covers_through", w.through)):
                if len(sha) != full or any(c not in "0123456789abcdef" for c in sha.lower()):
                    problems.append(
                        f"{w.run_id} 的 {label}={sha!r} 不是完整 40 位 sha → 该窗口在覆盖计算中"
                        f"被静默丢弃（CLI 已改为自动记完整 sha；历史记录需回填）")
            if len(w.anchor) == full and w.anchor == w.through:
                problems.append(
                    f"{w.run_id} 的窗口 ({w.anchor[:8]}, {w.through[:8]}] 是**空区间**"
                    f"（登记与收尾在同一提交）→ 该 run 实际贡献 0 覆盖，C3 压力全落到例外表")
        return problems

    def empty_interval(self) -> bool:
        """锚点→HEAD 之间**没有任何提交**受检（2026-09-23 二查 critical）。

        此时 `unowned` 必然为空，闸门与 `close-sync` 都会打出"覆盖闭环 ✔"——
        而事实是**一个提交都没查**。锚点 == HEAD 就是这种情形，而 Sprint §9.1 的占位文案
        恰恰引导人填"二查覆盖到的 HEAD"。故：空区间**不算通过**，必须显式判定。
        """
        return not self.shas

    def exception_problems(self) -> list[str]:
        problems: list[str] = []
        sha_re_len = 40
        for i, item in enumerate(self.exceptions):
            if not isinstance(item, dict):
                problems.append(f"例外 #{i} 不是对象：{item!r}")
                continue
            sha = str(item.get("sha") or "")
            if any(ch in sha for ch in "*?[]") or "/" in sha:
                problems.append(f"例外 #{i} 的 sha={sha!r} 含通配/路径（C3-T 要求 sha 钉死，禁止模式匹配）")
            elif len(sha) != sha_re_len or any(c not in "0123456789abcdef" for c in sha.lower()):
                problems.append(f"例外 #{i} 的 sha={sha!r} 不是完整 40 位十六进制（短 sha 不可核）")
            if not str(item.get("reason") or "").strip():
                problems.append(f"例外 #{i}（sha={sha[:8]}）缺 reason（例外必须写理由）")
        return problems

    def exception_shas(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for item in self.exceptions:
            if isinstance(item, dict) and item.get("sha"):
                out[str(item["sha"])] = item
        return out

    # -- 归属判定 ---------------------------------------------------------------
    def files_of(self, sha: str) -> list[str]:
        if sha not in self._files:
            self._files[sha] = commit_files(self.root, sha)
        return self._files[sha]

    def is_doc_only(self, sha: str, globs: tuple[str, ...]) -> bool:
        files = self.files_of(sha)
        if not files:
            return False  # 空 diff（合并/空提交）→ 不自动归类，交人判
        return all(any(fnmatch.fnmatch(f.replace("\\", "/"), g) for g in globs) for f in files)

    def owner(self, sha: str, doc_only_globs: tuple[str, ...]) -> str | None:
        for w in self.windows:
            if w.covers(sha, self.order):
                return f"run:{w.run_id}"
        if sha in self.exception_shas():
            return "exception"
        if self.is_doc_only(sha, doc_only_globs):
            return "doc-only"
        return None

    def unowned(self, doc_only_globs: tuple[str, ...]) -> list[str]:
        return [sha for sha in self.shas if self.owner(sha, doc_only_globs) is None]

    def report_lines(self, doc_only_globs: tuple[str, ...], limit: int = 40) -> list[str]:
        lines: list[str] = []
        for sha in self.shas[:limit]:
            owner = self.owner(sha, doc_only_globs) or "**UNOWNED**"
            files = self.files_of(sha)
            head = ", ".join(files[:3]) + (" …" if len(files) > 3 else "")
            lines.append(f"{sha[:10]}  {owner:28s} {commit_subject(self.root, sha)[:60]:60s} {head[:60]}")
        if len(self.shas) > limit:
            lines.append(f"… 另有 {len(self.shas) - limit} 个提交未列出")
        return lines


def load_coverage_exceptions(path: Path) -> list[dict]:
    """读 C3-T 例外表。文件缺失 = 无例外（不是错误）；内容非法 = PolicyError。"""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rules = data.get("rules")
        if rules is None:
            raise PolicyError(f"{path} 缺 rules 数组")
        return list(rules)
    if isinstance(data, list):
        return data
    raise PolicyError(f"{path} 结构非法（应为 {{rules: [...]}} 或数组）")

