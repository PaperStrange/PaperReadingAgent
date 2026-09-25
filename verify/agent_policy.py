"""TG-15：政策数据加载器（数据驱动闸门的唯一入口）。

**为什么需要这个模块**（背景与判据见 `docs/iteration/phases/testing-governance/backlog.MD` 的 `TG-15` 卡）：

闸门原先靠"遇到一个场景加一条判据"成长——角色名写死在 `scripts/agent-ops.py`（`_REVIEW_ROLES`）、
`verify/verify_close_readiness.py`（`CLOSE_ROLES`）、
`verify/verify_agentops.py`（又一份），
覆盖路径写死在 `verify/verify_lint.py`（`DEFAULT_PATHS`），
归档识别写死在 `scripts/report-freshness.py`
（`startswith("tech-research")`），阈值写死在 `agent-ops`（`_MIN_DEVIATION_CHARS`）。
后果：**加一个角色 / 换一个分支 / 改一个步骤都要改代码**，
而改代码这件事本身没有任何闸门在守。

本模块把"哪些角色要声明 scope""关闭必须跑哪些步骤/目标""阈值多少"全部**从数据读取**：

  数据源 1  `agents/fanout.json::
  sprint_close_pipeline`  —— 关闭流水线的步骤 / role / targets / ledger 标记
  数据源 2  各角色 spec（`agents/functions/<role>.md`）
  的 YAML frontmatter —— `scope_required` 等角色属性
  数据源 3  `agents/policy.json`（本卡新增）
  —— 不可从上述两者推导的**阈值与开关**（偏离理由最小长度、
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
import math
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 环境变量覆盖（测试与 CI 注入 fixture 用；优先级：
# env > agents/policy.json > 本文件兜底）
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
    一个拼写错误就能关掉一条闸门，这正是"数据驱动闸门"最该防的失效形态。
    现在非法取值直接报错。
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


def _require_iso_date(raw: object, where: str) -> str:
    """严格 `YYYY-MM-DD`（缺/格式错 → fail-closed，不猜）。

    闸门要按**字典序**比较日期，格式一乱比较就无意义；而"比较无意义"的后果是棘轮
    永不失效（永久豁免）。`md_table_legacy_files.review_by` 与 TG-13 的
    `legacy_ratchet.cutoff_local_date`/`review_by` 共用本判据。
    """
    text = str(raw or "").strip()
    parts = text.split("-")
    if len(parts) != 3 or [len(p) for p in parts] != [4, 2, 2] or not all(p.isdigit() for p in parts):
        raise PolicyError(f"{where} 必须是 'YYYY-MM-DD'，实际 {raw!r}——格式非法会让日期比较失去意义")
    return text


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

        2026-09-23 doc-audit finding 2 修正：此前只把 `scope_required` 做成不变量，
        而 §6（政策数据化）的
        条文明写"两个字段都必须显式声明"，且 `coverage_window` 决定该 run **是否参与 C3 覆盖计算**
        ——也就是说缺它就没有任何东西能判定"这个 run 该不该覆盖"，
        这正是"文档承诺 > 实现"的形态。
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

        A2（finding M-a/N2/R3，2026-09-25）：首版是**路径列表**，
        闸门只做路径比较 ⇒ 基线文件内
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

        为什么必须有到期日（R3）：
        没有到期日的豁免就是**永久豁免**——基线会变成"历史债合法化"的
        挡箭牌，而"重评"这件事不会有任何触发点。
        """
        val = self._data("md_table_legacy_files")
        raw = val.get("review_by") if isinstance(val, dict) else None
        # 严格 `YYYY-MM-DD`：闸门要按字典序比较日期，格式一乱比较就无意义（fail-closed，
        # 不猜）
        return _require_iso_date(raw, "md_table_legacy_files.review_by")

    @property
    def card_index(self) -> dict:
        """TG-14④ 卡索引 lint 的参数（必备节 / 指纹长度阈值 / 行级比对的最小行长）。

        2026-09-23：这些值最初写在 `verify/verify_card_index.py` 里，被
        `verify_no_policy_hardcode.py` 判为 R1（阈值硬编码）
        ——**闸门又一次抓住了写闸门的人**。
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
    def lint_readability_ratchet(self) -> dict:
        """C 级（可读性）**棘轮基线**（`policy.json::lint_readability_ratchet`，TG-6）。

        为什么分级之外还要一份上限表：C 级（缺 docstring / 行长）是**历史既存债**，
        且随正常改动漂移；硬 0 等于要求全仓重排，而"只报告"又等于没有闸门
        （数字没人看、涨了没人管）。棘轮 = 允许历史债在**计数上限**内存在，
        超出即 FAIL 并点名。

        校验一律 fail-closed（缺键 / 类型错 / 上限写成非数字 → `PolicyError`）：
        上限写错会让棘轮**静默失效**（同 `_as_bool` 与 TG-13 的 caps 校验）。
        与 `lint_rules.report_only` 的**逐键相等**由闸门判定
        （`verify_lint.ratchet_problems`），因为那是跨键一致性，属闸门职责。
        """
        val = self._data("lint_readability_ratchet")
        if not isinstance(val, dict):
            raise PolicyError(f"lint_readability_ratchet 必须是对象，实际 {val!r}")
        if not str(val.get("measured_at") or "").strip():
            raise PolicyError("lint_readability_ratchet.measured_at 缺失"
                              "（上限必须有实测日期，否则无从复核基线）")
        # 严格 `YYYY-MM-DD`：闸门按字典序比较 → 格式一乱比较就无意义（棘轮永不失效）
        _require_iso_date(val.get("review_by"), "lint_readability_ratchet.review_by")
        caps = val.get("caps")
        if not isinstance(caps, dict) or not caps:
            raise PolicyError(
                f"lint_readability_ratchet.caps 必须是非空映射，实际 {caps!r}")
        for code, cap in caps.items():
            if not str(code).strip():
                raise PolicyError(
                    f"lint_readability_ratchet.caps 出现空规则号：{caps!r}")
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
                raise PolicyError(
                    f"lint_readability_ratchet.caps[{code!r}] 必须是 ≥0 的整数，"
                    f"实际 {cap!r}——上限写错会让棘轮静默失效")
        return val

    def lint_readability_caps(self) -> dict[str, int]:
        """`{规则号: 计数上限}`（只许下调；换规则集须同时改 caps，闸门判双侧差集）。"""
        return {str(k): int(v)
                for k, v in self.lint_readability_ratchet["caps"].items()}

    def lint_readability_review_by(self) -> str:
        """棘轮到期日（过期未重评即 FAIL，同 `md_table_legacy_files.review_by`）。"""
        return _require_iso_date(self.lint_readability_ratchet["review_by"],
                                 "lint_readability_ratchet.review_by")

    @property
    def archive_role_prefix(self) -> str:
        return str(self._data("archive_role_prefix"))

    @property
    def md_table_targets(self) -> tuple[str, ...]:
        """Markdown 结构自检的目标集 = 显式文档 + glob 展开（`verify/verify_md_tables.py` 消费）。

        2026-09-23 两次被闸门/子代理抓到的覆盖缺口，都记在这里：
          ① 该清单最初写在新闸门文件里 → 被
          `verify_no_policy_hardcode.py` 判为 R3（闸门先抓住了写闸门的人）；
          ② 首版只列了
          `testing-governance/backlog.MD
          ` 一个阶段文件 → **迁移新增的瘦索引与 95 个卡文件
             默认一个都不查**（P2 子代理实测指出）。现改为"显式文档 + glob"，
             新增阶段/卡文件自动纳入。

        A10（2026-09-25，finding N1）起本属性**不再是闸门的唯一入口**：
        `verify_md_tables.py` 为了做
        "应扫/实扫"双向差集，会分别读 `md_table_docs`/`md_table_globs` 并各自核对（显式路径必须存在、
        每条 glob 必须命中 ≥1 文件、两侧集合必须相等）。
        本属性保留为"合并后的目标集"这一语义的
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
        """关闭闸门的需求侧开关（`close_gate`）。

        B1（2026-09-25）起新增一条**跨键一致性**校验：
        `close_gate.scope_ref_step` 是本闸门"本次关闭窗口从哪里开始"的唯一定义者
        （`verify_close_readiness.ledger_close_window` 取该步骤最新 run 的
        `started_at`）。
        它若拼错成一个**不存在的步骤名**，窗口就会悄悄退化成"不可推导"
        ⇒ C1/§9 判定域变成全域 ⇒ 闸门从"收窄"回到"永久噪音"，
        而拼错本身不会有任何东西报出来。故这里 fail-closed：名字必须非空、且必须能在
        `fanout.json::sprint_close_pipeline` 里找到一个 `ledger=True` 的步骤与之同名。

        同时校验 `coverage.scope_run_window`（B3 的语义说明文案）：窗口语义是本闸门的
        判据文案真源，缺它就是"文档承诺 > 实现"（同 `_as_bool` 一族）。
        """
        val = self._data("close_gate")
        if not isinstance(val, dict):
            raise PolicyError(f"close_gate 必须是对象，实际 {val!r}")
        step_name = str(val.get("scope_ref_step") or "").strip()
        if not step_name:
            raise PolicyError("close_gate.scope_ref_step 缺失"
                              "（关闭窗口的起点由它定义，不能留空）")
        matching = [s for s in self.steps if s.step == step_name]
        if not matching:
            raise PolicyError(
                f"close_gate.scope_ref_step={step_name!r} 在 "
                f"fanout.json::sprint_close_pipeline 里不存在"
                f"（已有步骤：{[s.step for s in self.steps]}）"
                f"——步骤名拼错会让关闭窗口不可推导、判定域静默退回全域")
        if not any(s.ledger for s in matching):
            raise PolicyError(
                f"close_gate.scope_ref_step={step_name!r} 对应的步骤没有产出账本 run"
                f"（close_ledger=false）⇒ 窗口起点无处可取，关闭窗口恒不可推导")
        coverage = val.get("coverage")
        if not isinstance(coverage, dict):
            raise PolicyError(f"close_gate.coverage 必须是对象，实际 {coverage!r}")
        if not str(coverage.get("scope_run_window") or "").strip():
            raise PolicyError(
                "close_gate.coverage.scope_run_window 缺失"
                "（B3：作用域类 run 不承担内容覆盖的语义说明是判据文案的真源，"
                "不得留空——否则空窗口该不该报全凭读代码）")
        return val

    # ---- 数据源 3：扣率（§2.1.1，用户 2026-09-25 采纳 v0） -------------------------
    @property
    def deduction_rates(self) -> dict:
        """未闭环 critical/major 的**扣率口径**（`deduction_rates`，§2.1.1）。

        为什么口径必须是数据：v0 提案里比例表（critical/major/minor）与「未闭环」四判据
        一度只存在于计划文档里，而**文档不是执行面**——结算一旦落地，比例就会被抄进脚本，
        于是「同一件事两种算法」重演（§2.1.1 第 5 条点名的形态）。
        落数据 + 登记 `consumed` ⇒ ① 结算方无从自选；
        ② 键写错/删掉不会被静默当默认值（`closure_problems` 判死键）。

        校验一律 fail-closed（缺键 / 类型错 / 比例超界 / 全 0 / 步长非法 →
        `PolicyError`）：
        **比例写错会让规则静默失效或静默放大**，两者都不能靠"读到坏值再猜"。
        结构性约束里最要紧的一条是 `unclosed_criteria` 必须**至少有一条声明
        `requires_due_date: true`**——否则第 ④ 条会静默退化成"说一句延期就算闭环"。
        """
        val = self._data("deduction_rates")
        if not isinstance(val, dict):
            raise PolicyError(f"deduction_rates 必须是对象，实际 {val!r}")

        ratios = val.get("ratios")
        if not isinstance(ratios, dict) or not ratios:
            raise PolicyError(
                f"ratios 必须是非空映射（级别 → 比例），实际 {ratios!r}")
        for level, ratio in ratios.items():
            if not str(level).strip():
                raise PolicyError(f"ratios 出现空级别名：{ratios!r}")
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) \
                    or not math.isfinite(float(ratio)) \
                    or not 0.0 <= float(ratio) <= 1.0:
                raise PolicyError(
                    f"ratios[{level!r}] 须为 ∈[0,1] 有限数，实际 {ratio!r}"
                    f"（注释键/字符串/超界都拒——坏值会让扣率静默失真）")
        if not any(float(r) > 0 for r in ratios.values()):
            raise PolicyError(
                f"ratios 全为 0（{ratios!r}）⇒ 规则恒不扣分 = 静默关规则，"
                f"故 fail-closed；确要停用请改 §2.1.1 条文而非清零")

        merge = val.get("merge_same_root_cause")
        if not isinstance(merge, bool):
            raise PolicyError(
                f"merge_same_root_cause 须为布尔，实际 {merge!r}"
                f"（拼错不得静默当 false——那会从「合并」变「逐条累加」）")
        cap = val.get("cap_at_card_points")
        if not isinstance(cap, bool):
            raise PolicyError(f"cap_at_card_points 须为布尔，实际 {cap!r}")

        step = val.get("rounding_step")
        if isinstance(step, bool) or not isinstance(step, (int, float)) \
                or not math.isfinite(float(step)) or not 0.0 < float(step) <= 1.0:
            raise PolicyError(
                f"rounding_step 须为 (0,1] 内有限数，实际 {step!r}"
                f"（步长写错 = 账本精度对不上，0 还会让取整除零）")

        folding = val.get("ratchet_item_folding")
        if not isinstance(folding, dict):
            raise PolicyError(
                f"ratchet_item_folding 须为对象，实际 {folding!r}"
                f"（§2.1.1 第 5 条的折算口径；缺它只能写回代码常量）")
        fold_level = str(folding.get("unclosed_folds_to_level") or "").strip()
        if fold_level not in ratios:
            raise PolicyError(
                f"ratchet_item_folding.unclosed_folds_to_level={fold_level!r} "
                f"不在级别表 {sorted(ratios)} 内 ⇒ 折算无从取比例")
        fold_count = folding.get("count")
        if isinstance(fold_count, bool) or not isinstance(fold_count, int) \
                or fold_count <= 0:
            raise PolicyError(
                f"ratchet_item_folding.count 须为正整数，实际 {fold_count!r}")

        criteria = val.get("unclosed_criteria")
        if not isinstance(criteria, list) or not criteria:
            raise PolicyError(
                f"unclosed_criteria 须为非空列表（四判据是本规则另一半），"
                f"实际 {criteria!r}")
        seen: set[str] = set()
        requires_due_date = 0
        for i, item in enumerate(criteria):
            where = f"deduction_rates.unclosed_criteria[{i}]"
            if not isinstance(item, dict):
                raise PolicyError(f"{where} 必须是对象，实际 {item!r}")
            for field in ("id", "label", "evidence"):
                if not str(item.get(field) or "").strip():
                    raise PolicyError(
                        f"{where}.{field} 缺失或为空（判据须逐条可核、可枚举）")
            cid = str(item["id"]).strip()
            if cid in seen:
                raise PolicyError(
                    f"{where}.id={cid!r} 与前面的判据重复（判据集合不可枚举）")
            seen.add(cid)
            kinds = item.get("evidence_kinds")
            if not isinstance(kinds, list) or not kinds \
                    or not all(isinstance(k, str) and k.strip() for k in kinds):
                raise PolicyError(
                    f"{where}.evidence_kinds 须为非空字符串列表"
                    f"（证据形态要可枚举），实际 {kinds!r}")
            rdd = item.get("requires_due_date")
            if not isinstance(rdd, bool):
                raise PolicyError(
                    f"{where}.requires_due_date 须为布尔，实际 {rdd!r}"
                    f"（缺它无法判定「显式延期须带到期日」这条约束）")
            requires_due_date += int(rdd)
        if not requires_due_date:
            raise PolicyError(
                "unclosed_criteria 没有任何一条声明 requires_due_date: true "
                "⇒「显式延期」判据静默退化成「说一句延期就算闭环」"
                "（§2.1.1 第 ④ 条要求无到期日即视为未闭环）；"
                "这是放宽方向，故 fail-closed")
        return val

    # ---- 数据源 3：离线开关（TG-8） ------------------------------------------------
    @property
    def offline_switch(self) -> dict:
        """离线开关的政策数据（`agents/policy.json::offline_switch`，TG-8）。

        为什么开关数据要在这里校验：`verify/outbound_guard.py` 是**运行时代码**，
        它只在每个外呼入口前读一次政策；若字段名拼错/取值非法而无人校验，闸门会
        **静默变成"永远在线"**——这正是"关掉一条闸门不需要改代码"的失效形态
        （同 `_as_bool` 的 2026-09-23 二查 major）。故此处字段校验一律 fail-closed。
        """
        val = self._data("offline_switch")
        if not isinstance(val, dict):
            raise PolicyError(f"offline_switch 必须是对象，实际 {val!r}")
        boolish = [*self._offline_env_true_values(val), *self._offline_env_false_values(val)]
        if not boolish:
            raise PolicyError("offline_switch.env_true_values / env_false_values 不得同时为空"
                              "（空表 = 开关取值无法判定）")
        if not str(val.get("env_var") or "").strip():
            raise PolicyError("offline_switch.env_var 缺失（显式开关的环境变量名是政策数据）")
        if not str(val.get("refusal_reason") or "").strip():
            raise PolicyError("offline_switch.refusal_reason 缺失（拒绝必须给出可核原因文案）")
        code = val.get("refuse_exit_code")
        if isinstance(code, bool) or not isinstance(code, int) or code <= 0:
            raise PolicyError(f"offline_switch.refuse_exit_code 必须是正整数，实际 {code!r}")
        hf = val.get("hf_offline_env")
        if not isinstance(hf, dict):
            raise PolicyError(f"offline_switch.hf_offline_env 必须是对象，实际 {hf!r}")
        return val

    def _offline_env_true_values(self, val: dict | None = None) -> tuple[str, ...]:
        """开关环境变量的**真值**取值集合（小写比较；来自政策数据，不写死在代码里）。"""
        data = val if val is not None else self.offline_switch
        raw = data.get("env_true_values")
        if not isinstance(raw, list) or not all(isinstance(v, str) and v for v in raw):
            raise PolicyError(f"offline_switch.env_true_values 必须是非空字符串列表，实际 {raw!r}")
        return tuple(str(v).strip().lower() for v in raw)

    def _offline_env_false_values(self, val: dict | None = None) -> tuple[str, ...]:
        """开关环境变量的**假值**取值集合。非法取值（如 `flase`）→ 报错，不静默当"关"。"""
        data = val if val is not None else self.offline_switch
        raw = data.get("env_false_values")
        if not isinstance(raw, list) or not all(isinstance(v, str) and v for v in raw):
            raise PolicyError(f"offline_switch.env_false_values 必须是非空字符串列表，实际 {raw!r}")
        return tuple(str(v).strip().lower() for v in raw)

    # ---- 数据源 3：账本测量口径与历史棘轮（TG-13） --------------------------------
    @property
    def ledger_measurement(self) -> dict:
        """账本『测量化』口径 + 棘轮基线（`agents/policy.json::ledger_measurement`，TG-13）。

        为什么口径也要数据化：`dur` / `rounds` 的语义此前**只存在于讨论与注释里**——
        `list` 打印 `dur=`、看板画时长、评审引用时长，各自默认自己的口径，于是
        「0.00 分钟」「恰好 10.00 分钟」这类**写入时刻的巧合**一路被当成测量值上报
        （见 TG-13 卡内证据①）。本属性提供唯一真源：三条可核文本（dur/rounds/unknown）、
        退化判定参数、报告轮次正则、以及历史 run 的棘轮上限与到期日。

        校验一律 fail-closed（缺键/类型错/数值非法 → `PolicyError`）：口径写错或上限写成
        非数字，都会让闸门**静默放行**，而静默放行正是本卡要消灭的形态。
        """
        val = self._data("ledger_measurement")
        if not isinstance(val, dict):
            raise PolicyError(f"ledger_measurement 必须是对象，实际 {val!r}")
        for key in ("dur", "rounds", "unknown"):
            if not str(val.get(key) or "").strip():
                raise PolicyError(f"ledger_measurement.{key} 缺失或为空（三条口径是可核文本，不得留空）")
        values = val.get("measurement_source_values")
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
            raise PolicyError(f"ledger_measurement.measurement_source_values 必须是非空字符串列表，实际 {values!r}")
        deg = val.get("degenerate")
        if not isinstance(deg, dict) or isinstance(deg.get("round_minutes_multiple"), bool) \
                or not isinstance(deg.get("round_minutes_multiple"), int) or deg["round_minutes_multiple"] <= 0:
            raise PolicyError("ledger_measurement.degenerate.round_minutes_multiple 必须是正整数"
                              f"（退化判定阈值，写错即静默失效），实际 {deg!r}")
        pattern = str(val.get("report_round_pattern") or "")
        if not pattern:
            raise PolicyError("ledger_measurement.report_round_pattern 缺失（报告轮次是 rounds 的真源）")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise PolicyError(f"ledger_measurement.report_round_pattern 不是合法正则：{exc}") from exc
        globs = val.get("terminal_report_globs")
        if not isinstance(globs, list) or not globs:
            raise PolicyError(f"ledger_measurement.terminal_report_globs 必须是非空列表，实际 {globs!r}")
        exc_file = str(val.get("run_dir_exceptions_file") or "").strip()
        if not exc_file:
            raise PolicyError("ledger_measurement.run_dir_exceptions_file 缺失"
                              "（目录↔账本的历史例外白名单路径；白名单机制必须可核，不能无路径）")
        tol = val.get("dur_minutes_tolerance")
        if isinstance(tol, bool) or not isinstance(tol, (int, float)) or float(tol) <= 0:
            raise PolicyError(f"ledger_measurement.dur_minutes_tolerance 必须是正数，实际 {tol!r}")
        ratchet = val.get("legacy_ratchet")
        if not isinstance(ratchet, dict):
            raise PolicyError(f"ledger_measurement.legacy_ratchet 必须是对象，实际 {ratchet!r}")
        # 两处日期都必须严格 `YYYY-MM-DD`（比较失去意义 = 棘轮永不失效）——只校验，
        # 取值走专用属性
        _require_iso_date(ratchet.get("cutoff_local_date"), "legacy_ratchet.cutoff_local_date")
        _require_iso_date(ratchet.get("review_by"), "legacy_ratchet.review_by")
        caps = ratchet.get("caps")
        if not isinstance(caps, dict) or not caps:
            raise PolicyError(f"ledger_measurement.legacy_ratchet.caps 必须是非空映射，实际 {caps!r}")
        for name, cap in caps.items():
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
                raise PolicyError(
                    f"ledger_measurement.legacy_ratchet.caps[{name!r}] 必须是 ≥0 的整数，实际 {cap!r}"
                    f"——上限写错会让棘轮静默失效")
        return val

    def ledger_cutoff_local_date(self) -> str:
        """截止日（`YYYY-MM-DD`，本地 UTC+8）：**≤** 该日期的 run 属历史（棘轮基线管），> 的严格判定。"""
        return _require_iso_date(self.ledger_measurement["legacy_ratchet"]["cutoff_local_date"],
                                 "legacy_ratchet.cutoff_local_date")

    def ledger_review_by(self) -> str:
        """棘轮基线到期日（过期未重评即 FAIL，同 `md_table_legacy_files.review_by` 的理由）。"""
        return _require_iso_date(self.ledger_measurement["legacy_ratchet"]["review_by"],
                                 "legacy_ratchet.review_by")

    def ledger_caps(self) -> dict[str, int]:
        return {str(k): int(v) for k, v in self.ledger_measurement["legacy_ratchet"]["caps"].items()}

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
        2. 每个被枚举的 spec 必须**显式**声明
        `scope_required`（`allow_undeclared` 时降级为提示）；
        3. `policy.json` 不得残留未被任何代码读取的键（防"数据文件变成新的垃圾场"）。

        注意第 2 条为什么是**不变式**而不是"再看一眼的警告"：C1 的判据是"凡声明
        `scope_required: true` 的 run 必须有 scope 声明"——若允许"未声明"存在，它就同时
        从判据里消失（**删声明 = 关掉闸门**）。所以缺声明只能是**错误**。
        `allow_undeclared`
        仅为一次性数据迁移开的口子（`PAPERQA_POLICY_ALLOW_UNDECLARED=1`），
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
            # TG-6：C 级（可读性）棘轮基线（计数上限 + measured_at + review_by），
            # 由 verify/verify_lint.py 消费
            "lint_readability_ratchet",
            "ledger_status", "md_table_docs", "md_table_globs", "md_table_legacy_files", "card_index",
            # A10（N1）：md_table_globs 的**范围声明**（roots/include_files），
            # 由 verify_md_tables.py 消费
            "md_table_coverage",
            # A11（N4）：豁免台账的校验参数（类别白名单/理由长度/作用域），
            # 由 verify_no_policy_hardcode.py 消费
            "hardcode_exemptions",
            # A6（R1）：硬编码闸门扫描集的**范围声明**（roots/globs/exclude_dirs），
            # 由 verify_no_policy_hardcode.py 消费
            "hardcode_scan_coverage",
            # TG-13：账本测量口径（dur/rounds/unknown）+ 退化判定 + 历史棘轮基线，
            # 由 verify/verify_ledger_measurement.py 与 scripts/agent-ops.py 消费
            "ledger_measurement",
            # TG-9：新脚本产物落点约定（忽略根清单 /
            # 扫描集 / 已入库数据文件例外 / 临时落点写法 /
            # 动态目标棘轮），由 verify/verify_artifact_paths.py 消费
            "artifact_paths",
            # TG-8：离线开关（开关名 / 默认值 / 真值表 / 拒绝文案 / 退出码），
            # 由 verify/outbound_guard.py（运行时唯一实现）
            # 与 verify/agent_policy.py 自身消费
            "offline_switch",
            # §2.1.1（用户 2026-09-25 采纳 v0）：未闭环 critical/major 的扣率口径
            # （比例表 / 同根因合并开关 / 封顶 / 取整步长 / 棘轮折算 / "未闭环"四判据）
            # ，
            # 由 Policy.deduction_rates() 与纯函数 deduction_for() 消费，
            # 守门闸门 = verify/verify_deduction_rates.py（首次实际结算时再加 CLI，见
            # §2.1.1）
            "deduction_rates",
            # 2026-09-25 关闭期：派生数字棘轮（verify_derived_numbers.py 消费）
            "derived_numbers",
            # 2026-09-25 关闭期：闸门可信度（-O 守卫 + 棘轮单调性，
            # verify_gate_integrity.py 消费）
            "gate_integrity",
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
        # targets：单任务用 task.target，多任务用 tasks[].target（两形态都支持，
        # 避免为旧数据加特例）
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
    # B1/B3（2026-09-25）：关闭闸门的需求侧数据（`close_gate`）同样纳入
    # **装载时**不变量。为什么不能只在被读取时校验：`scope_ref_step` 拼错会让
    # "本次关闭窗口"**恒不可推导** ⇒ C1/§9 的判定域静默退回全域（闸门从"收窄去噪"
    # 变回"永久噪音"），而"读不到就等于没这条判据"正是本模块开头点名的失效形态。
    # 让它在这里当场抛错，任何命令都不会带着一个"窗口永远定不出来"的政策继续跑。
    policy.close_gate  # noqa: B018 —— 触发属性校验（缺键/步骤名不存在/缺文案 → PolicyError）
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
    # D0-3(a)（2026-09-25）：该 run 已被**逐条列名 + 带理由**标注为"产出型 run"
    # （实现类工作补登记挂评审 role，不承担内容覆盖）。默认 False ⇒
    # 读取方不打标即不生效，
    # 收窄只由**账本数据**触发，不由"忘了传字段"触发（fail-closed 方向）。
    produced_only: bool = False
    produced_only_reason: str = ""

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
    现由 `SpecRole.participates_in_coverage` 提供判据（doc-audit finding 2 的修法之一）
    。

    D0-3(a)：账本行的 `produced_only`（`mark-produced` 写入，**逐条列名 + 必带理由**）
    透传到窗口上，供 `window_problems()` 区分"产出型 run"与"内容评审类 run"。
    这里只搬字段，
    不做判定——判定集中在一处，避免"读到打标就各处自行放行"。
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
            produced_only=bool(r.get("produced_only")),
            produced_only_reason=str(r.get("produced_only_reason") or ""),
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

    传 `policy` 时，声明 `coverage_window:
    none` 的角色不贡献窗口（判据同 `coverage_windows_from_runs`）。
    """
    shas = rev_list(root, anchor, head)
    order = order_index([head, *shas])
    windows = coverage_windows_from_runs(runs, policy)
    # B4（2026-09-25 复核 BLOCKER）：窗口锚点不在本次序号表内时，
    # **先判它是不是"更老"**——
    # 左端点是开区间，锚点比文档锚点更老是**合法且常见**的形态（本次复核 run 的锚点
    # `9ffc108d` 就早于文档锚点 `f30c6e47`）。判据用 git 的祖先关系（可核），
    # 判不了就**不**进集合（走 fail-closed + 逐条点名）。
    older_anchors: set[str] = set()
    for w in windows:
        if w.anchor in order or w.anchor in older_anchors:
            continue
        if _is_ancestor(root, w.anchor, anchor):
            older_anchors.add(w.anchor)
    return Attribution(
        anchor=anchor, head=head, shas=shas, order=order, windows=windows,
        exceptions=list(exceptions or []),
        root=root, policy=policy, older_anchors=older_anchors,
    )


def _is_ancestor(root: Path | None, older: str, newer: str) -> bool:
    """`older` 是否为 `newer` 的祖先（含相等）——用于判定"窗口锚点比文档锚点更老"。

    解析不了（git 失败 / sha 不存在 / 非祖先）→ `False`（调用方按 fail-closed 处理：
    不覆盖 + 逐条点名），**不做乐观推断**。

    ⚠️ **必须同时兜住 `SystemExit`**（2026-09-25 修复验证复核 finding，回归修复）：
    `git()` 非零退出时抛的是 `PolicyError`，而它是 `SystemExit` 的子类、
    **不是 `Exception`**——
    第一版写 `except Exception` ⇒ 捕获不到，于是"锚点解析不了 / 不是祖先 / shallow 历史"
    本该返回 `False` 的情形会**把整个关闭闸门硬中止**（`POLICY-ERROR`，连报告都不出），
    并让 `window_problems()` 的点名分支沦为**死代码**（复核实测：
    bogus / 孤儿分支 / shallow
    缺失 / 普通非祖先四种输入全部 `RAISED PolicyError`）。
    """
    if not older or not newer:
        return False
    try:
        git(root, "merge-base", "--is-ancestor", older, newer)
    except (Exception, SystemExit):  # noqa: BLE001 —— 任何失败都只是"证明不了"
        return False
    return True


class Attribution:
    """一次覆盖归属计算的完整结果（`unowned` 非空 = C3 未闭环 → 闸门 FAIL 并逐条点名）。

    `policy` 为可选（fixture 可省）：给了才能判定"该 run 属作用域类还是内容评审类"
    （B3 的空窗口语义）。省略时**所有**空窗口都判问题——收窄只由数据触发，
    不由"忘了传政策"触发（fail-closed 方向）。
    """

    def __init__(self, *, anchor: str, head: str, shas: list[str],
                 order: dict[str, int], windows: list[CoverageWindow],
                 exceptions: list[dict], root: Path | None,
                 policy: "Policy | None" = None,
                 older_anchors: set[str] | None = None):
        self.anchor = anchor
        self.head = head
        self.shas = shas
        self.order = order
        self.windows = windows
        self.exceptions = exceptions
        self.root = root
        self.policy = policy
        # B4（2026-09-25 复核 BLOCKER）：**已证明早于文档锚点**的窗口锚点集合
        # （`git merge-base --is-ancestor` 判过）。左端点是**开区间**，
        # 故这类锚点虽然不在
        # 序号表里，窗口依然有效——旧实现把它们一律当"不覆盖"，实测 14/14 窗口全失效。
        self.older_anchors = set(older_anchors or ())
        self._files: dict[str, list[str]] = {}

    def _covers(self, window: CoverageWindow, sha: str) -> bool:
        """窗口是否覆盖该提交（B4 修：左端点是**开区间**，锚点不必落在序号表内）。

        三种情形（①② 是"能证明"，③ 是"不能证明"）：
          ① 锚点在序号表内 → 交给
             `CoverageWindow.covers()` 按序号比较（原口径，未改动）；
          ② 锚点**已证明早于文档锚点**（`older_anchors`）→ 左端视为 **-∞**：
             只要 `through` 在表内且 `order[through] <= order[sha]` 即覆盖；
          ③ 其余（未来锚点 / 与本次历史无关联的提交 / 解析失败）
          → **不覆盖**（fail-closed，
             宁可点名也不做乐观推断），并由 `window_problems()
             ` 逐条点名——**不再静默丢弃**。
        """
        if window.anchor in self.order:
            return window.covers(sha, self.order)
        if window.anchor in self.older_anchors:
            return window.through in self.order and \
                self.order[window.through] <= self.order.get(sha, -1)
        return False

    # -- B3：覆盖窗口语义（作用域类 run vs 内容评审类 run） -----------------------
    def scope_role_names(self) -> set[str]:
        """**作用域类** role：只界定"本次关闭覆盖哪些变更"、不承担内容覆盖。

        两个来源（都不按 role 名硬编码）：
          ① `close_gate.scope_ref_step` 指向的关闭步骤 role
             （本仓 = `impact-assessment`）——fanout 的 `order: 1` 步，
             语义就是 T0 界定变更集；
          ② spec 自己声明 `coverage_window: none` 的 role（本仓 = workspace-check /
             tech-research / _template-agent）——它们本就不参与覆盖计算。
        """
        if self.policy is None:
            return set()
        names: set[str] = set()
        wanted = str(self.policy.close_gate.get("scope_ref_step") or "").strip()
        names |= {s.role for s in self.policy.steps if s.step == wanted}
        names |= {r for r, spec in self.policy.specs.items()
                  if spec.coverage_window == "none"}
        return names

    def is_scope_run(self, role: str) -> bool:
        return role in self.scope_role_names()

    # -- 例外表校验（用户 P2 关切的"表过期"三件套之 (b)：sha 钉死，禁止通配） -------
    def window_problems(self) -> list[str]:
        """窗口自身的结构性缺陷（2026-09-23 二查 major #3 + 2026-09-25 B3）。

        **短 sha（B2 同族，任何 run 都判）**：实测账本里 `covers_through="e6ccd257"`
        （8 位）而 `order` 里只有完整 sha → `covers()` 静默返回 False，
        该窗口**形同不存在**，却不报任何错。**静默**正是要消灭的东西：
        无论该 run 属哪一类，这里逐条点名。
        （受控回填见 `scripts/agent-ops.py set-anchor --covers-through`。）

        **空区间（B3 按 run 类别分语义）**：
        `coverage_anchor == covers_through`（`register` 与 `finish` 落在同一提交）
        意味着该 run 贡献 0 覆盖。此时**分类判定**：
          * **作用域类 run**（如 `impact-assessment`，见 `scope_role_names`）——
            **不判问题**。它的职责是 T0 界定本次关闭覆盖哪些变更，本来就不该扛内容覆盖；
            对它报"空区间"等于用一把量内容覆盖的尺子去量一把界定范围的尺子
            ⇒ 真数据上 `run-…-impact-assessment-065` 就是这种"跑完即登记"的形态，
            报它是**结构性假红**（TG-17 ①）。
          * **内容评审类 run**（`code-review` / `doc-audit` / `agent-onboarding-review`
            等 spec 声明 `coverage_window: self` 的评审 role）——**仍判 FAIL**，并
            给出可执行的修复路径。它们**声称**覆盖了一段内容却实际覆盖 0 个提交
            （`run-…-code-review-068` 就是这种），若放行则 C3 的压力会静默全落到例外表，
            正是本闸门存在的理由。判据文案真源 =
            `close_gate.coverage.scope_run_window`。
          * **已标注的"产出型 run"**（D0-3(a)，账本行 `produced_only: true`）——
            **不判问题**。理由不是"宽限"，而是**它本就不是评审**：这类 run 是"实现类工作
            补登记挂评审 role"的实例（`TG-17` ⑤：账本原先没有实现类 role），它没有
            内容覆盖的**声称**可违反。标注由 `scripts/agent-ops.py mark-produced`
            **逐条列名 + 必带理由**写入账本（留痕数组），**不是通配豁免**：
            ① 未标注的内容评审类 run 空窗口**仍判 FAIL**；
            ② 短 sha 判据**不以任何理由豁免**（打标也不放行）；
            ③ 打标只跳过本行这一条判据，**不产生任何覆盖**（C3 未归属提交一条不少）；
            ④ 已打标的 run 会被 `produced_only_notes()` 逐条打印，关闭报告里看得见。
        """
        problems: list[str] = []
        full = 40
        # B4（2026-09-25 复核 BLOCKER）：**窗口根本没参与计算**要能看见。
        # 旧实现在"锚点不在序号表内"时静默返回"不覆盖"——实测 14/14 窗口全失效、
        # 规范窗口 `(三查锚点, HEAD]` 无法表达，而 `window_problems()` 一个字都不报。
        # 只对**承担内容覆盖**的窗口点名（作用域类 / 已标注产出型不带覆盖声称，
        # 报它们是噪音）。
        for w in self.windows:
            if w.produced_only or self.is_scope_run(w.role):
                continue
            if w.anchor not in self.order and w.anchor not in self.older_anchors:
                problems.append(
                    f"{w.run_id}（role={w.role}）的 coverage_anchor={w.anchor[:12]} 既不在本次计算范围"
                    f"（{self.anchor[:8]}..{self.head[:8]}）内、也**证明不了**它早于文档锚点 "
                    f"⇒ 该窗口贡献 0 覆盖（fail-closed，不乐观推断）。要么它的锚点本就不该在这条历史上"
                    f"（改锚点），要么本次历史不完整（shallow clone？`fetch-depth: 0` 是必需项）。")
            # **上界**不在序号表内时同样贡献 0 覆盖。判据**必须与锚点判据并列**：
            # 第一版把它嵌在"锚点也解释不了"分支里（复核 #3 finding：`anchor∈order` +
            # `covers_through∉order` 这一组合 0 项、仍静默）——两个端点各自独立失效，
            # 不能互为前提。
            if w.through not in self.order:
                problems.append(
                    f"{w.run_id}（role={w.role}）的 covers_through={w.through[:12]} 不在本次计算范围"
                    f"（{self.anchor[:8]}..{self.head[:8]}）内 ⇒ 该窗口贡献 0 覆盖（静默丢弃的同族形态）。"
                    f"常见成因：该上界属于**另一条历史**（如 rebase/换分支后的提交）或本地历史不完整。")
        for w in self.windows:
            for label, sha in (("coverage_anchor", w.anchor), ("covers_through", w.through)):
                if len(sha) != full or any(c not in "0123456789abcdef" for c in sha.lower()):
                    flag = "anchor" if label == "coverage_anchor" else "covers-through"
                    problems.append(
                        f"{w.run_id} 的 {label}={sha!r} 不是完整 40 位 sha"
                        f" → 该窗口在覆盖计算中被静默丢弃"
                        f"（CLI 已改为自动记完整 sha；历史记录需受控回填："
                        f"`scripts/agent-ops.py set-anchor {w.run_id} "
                        f"--{flag} <sha> --reason <理由>`）")
            if len(w.anchor) == full and w.anchor == w.through:
                if self.is_scope_run(w.role):
                    # B3：作用域类 run 不承担内容覆盖，空区间是正常形态（见方法文档）
                    continue
                if w.produced_only:
                    # D0-3(a)：产出型 run 不声称内容覆盖（逐条列名 + 带理由，
                    # 见方法文档）
                    continue
                problems.append(
                    f"{w.run_id}（role={w.role}，内容评审类）的窗口 "
                    f"({w.anchor[:8]}, {w.through[:8]}] 是**空区间**"
                    f"（登记与收尾在同一提交）"
                    f"→ 该 run 声称覆盖内容却实际贡献 0 覆盖，C3 压力全落到例外表。"
                    f"修复：`scripts/agent-ops.py set-anchor {w.run_id} "
                    f"--covers-through <sha> --reason <受控回填理由>`（或重跑该评审）；"
                    f"若该 run 其实是**实现类工作挂评审 role**（不承担内容覆盖），"
                    f"用 `agent-ops.py mark-produced {w.run_id} --reason <理由>` "
                    f"如实标注（不改覆盖、不伪造范围）")
        return problems

    def produced_only_notes(self) -> list[str]:
        """已标注"产出型 run"的逐条打印（D0-3(a) 的**可见性**要求）。

        为什么必须打印而不是默默跳过：`produced_only` 会让一条判据对该 run 失效，
        若这件事只存在于 JSON 里，关闭报告就会"看起来全绿"而无人知道有豁免在生效——
        与例外表"必须逐条 sha 钉死 + 写理由"同源的防滥用设计（可核、可见、可复核）。
        """
        return [
            f"{w.run_id}（role={w.role}）已标注 produced_only："
            f"窗口 ({w.anchor[:8]}, {w.through[:8]}] 空 ⇒ 不承担内容覆盖；"
            f"理由={w.produced_only_reason or '（缺理由，账本数据不完整）'}"
            for w in self.windows if w.produced_only
        ]

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
            if self._covers(w, sha):
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


# ------------------------------------------- §2.1.1：扣率结算（纯函数，无 I/O）

@dataclass(frozen=True)
class DeductionResult:
    """一次扣率结算的可核结果（§2.1.1）。

    **不落账本、不建 CLI**：§2.1.1 明写"结算脚本在**首次实际使用**时再加（避免造用不上的
    机器）"。
    本结构与 `deduction_for()` 一起构成那台机器**唯一需要被提前固定的部分**——口径，
    而口径已经落在 `agents/policy.json::deduction_rates`（数据），不是常量。

    字段一律"可复算"：`counted_levels` 是**合并/封顶前参与计分**的级别序列（按根因分组后
    的
    代表级别），故 `ratio == Σ ratios[counted_levels]`、`points == card_points -
    deduction`
    可被调用方逐条复核，不必相信本函数。
    """

    card_points: float
    counted_levels: tuple[str, ...]
    ratio: float          # 合并后、封顶前的比例和
    capped: bool          # 是否被"不超过卡点数"这一步改变过结果
    deduction: float      # 实际扣分（已按 rounding_step 取整；封顶优先于取整）
    points: float         # 剩余点数 = card_points - deduction（下限 0，不倒扣）


def _round_to_step(value: float, step: float) -> float:
    """四舍五入到步长网格（先除后乘再 round，避免 0.05 步长下的浮点尾数）。"""
    return round(round(value / step) * step, 10)


def deduction_for(card_points, levels, *, root_causes=None, rates=None,
                  merge: bool | None = None) -> DeductionResult:
    """§2.1.1 的**纯结算函数**：`卡点数 + 未闭环发现的级别` → 扣分与剩余点数。

    口径全部来自 `agents/policy.json::deduction_rates`（数据）：

      * 比例**只按级别**取（`ratios[level]`），不按条数线性累加；
      * `merge_same_root_cause` 为真时，**同一根因**的多条发现合并计一次、取其中最高级别
        ——根因分组由调用方通过 `root_causes` 给出（与 `levels` 等长、逐项对应）；
      * **未给 `root_causes` 时按「每条各自一个根因」处理**：这是 fail-closed 方向
        （静默合并会**低估**扣分；而"少扣分"正是本规则要防止的失效形态）；
      * `cap_at_card_points` 为真时单卡总扣分不超过卡点数（**封顶优先于取整**：
        卡点数未必落在取整网格上，取整不得把结果顶过封顶）；
      * 结果按 `rounding_step` 四舍五入；`points` 为剩余点数（下限 0、不倒扣）。

    **fail-closed**：级别名不在 `ratios` 里（拼错/自造级别）、`root_causes` 与 `levels`
    不等长、
    `card_points` 非有限或为负 → 一律 `PolicyError`，**不静默按 0 计**——
    "读不到就当没有"正是本模块开头点名的失效形态。

    **纯度**：传 `rates` 时本函数不碰任何文件（自检里有对应反向对照：
    政策路径不存在也照样能算）；
    不传时取当前政策（`load_policy().deduction_rates()`）——那是**取默认值**，
    不是隐藏状态。
    """
    if rates is None:
        rates = load_policy().deduction_rates()
    ratios = {str(k): float(v) for k, v in rates["ratios"].items()}
    step = float(rates["rounding_step"])
    if merge is None:
        merge = bool(rates["merge_same_root_cause"])
    cap_at_points = bool(rates["cap_at_card_points"])

    if isinstance(card_points, bool) or not isinstance(card_points, (int, float)) \
            or not math.isfinite(float(card_points)) or float(card_points) < 0:
        raise PolicyError(
            f"deduction_for: card_points 必须是 ≥0 的有限数，实际 {card_points!r}")

    level_list = [str(lv).strip() for lv in levels]
    unknown = sorted({lv for lv in level_list if lv not in ratios})
    if unknown:
        raise PolicyError(
            f"deduction_for: 级别 {unknown} 不在 deduction_rates.ratios 的级别表 "
            f"{sorted(ratios)} 内——拼错/自造级别不得静默按 0 计")

    if root_causes is None:
        causes = [f"finding-{i}" for i in range(len(level_list))]
    else:
        causes = [str(c).strip() for c in root_causes]
        if len(causes) != len(level_list):
            raise PolicyError(
                f"deduction_for: root_causes 与 levels 须等长"
                f"（{len(causes)} != {len(level_list)}）"
                f"——长度对不上时「哪几条同根因」无从判定，静默截断会改变扣分")

    if merge:
        best: dict[str, str] = {}
        for level, cause in zip(level_list, causes):
            current = best.get(cause)
            if current is None or ratios[level] > ratios[current]:
                best[cause] = level
        counted = tuple(best[c] for c in dict.fromkeys(causes))  # 保序，去重
    else:
        counted = tuple(level_list)

    ratio = sum(ratios[lv] for lv in counted)
    raw = float(card_points) * ratio
    capped = False
    if cap_at_points:
        capped = raw > float(card_points)
        raw = min(raw, float(card_points))
    deduction = _round_to_step(raw, step)
    if cap_at_points and deduction > float(card_points):
        deduction = float(card_points)  # 封顶优先于取整（见 docstring）
    return DeductionResult(
        card_points=float(card_points), counted_levels=counted, ratio=round(ratio, 10),
        capped=capped, deduction=deduction,
        points=round(float(card_points) - deduction, 10),
    )

