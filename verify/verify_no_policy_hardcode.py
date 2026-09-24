"""TG-15⑦：**硬编码政策探测器**（offline）——"政策必须在数据文件，不许写进代码"的可执行闸门。

背景（`TG-15` 卡）：闸门原先靠"遇到一个场景加一条判据"成长，于是同一个政策在**多处**各存一份：
`scripts/agent-ops.py` 的角色集合与偏离长度、`verify/verify_close_readiness.py` 的关闭角色与
按角色判据、`verify/verify_lint.py` 的覆盖路径、`scripts/report-freshness.py` 的归档前缀、
`verify/verify_agentops.py` 又一份角色集合。**加角色/换分支/调阈值都要改代码**。
TG-15 起政策统一落在三处数据：`agents/fanout.json`（步骤/target）、各 spec frontmatter
（角色属性）、`agents/policy.json`（阈值与开关）；本脚本守住"不许再退回代码里"。

扫描对象（A6 / 审核 R1，2026-09-25 起**政策驱动**）：由
`agents/policy.json::hardcode_scan_coverage` 声明——`roots`（必扫树，每条必须存在）与 `globs`
（实际展开，每条必须 ≥1 命中）两侧必须**相等**，闸门打印『应扫 N / 实扫 M』，不一致即 FAIL 并
逐条点名；`exclude_dirs` 显式排除 vendored（`paper-qa/`）、环境（`.venv`/`node_modules`）、缓存
与**运行产物**（`agents/runs/`、`.agents/`）。**封闭世界**：仓库里任何含 `.py` 的树必须落在
roots 或 exclude_dirs 内，出现未纳管的新树即 FAIL。

  为什么必须政策驱动 + 双向差集（实测事故）：旧实现把 `('scripts','verify')` **写死在脚本里**，
  实测只覆盖 39/182 个 `.py`，而闸门照旧打印 `ALL PASS … clean`——『漏扫』比『漏报』更危险，
  它让 PASS 从『查过且没问题』退化成『没查』。真正的守门范围必须**可核**，不能靠读代码去猜。

判据（全部基于 AST，不是正则猜）：
  R1 政策变量赋值 —— `ROLE(S)/REVIEW_ROLES/CLOSE_ROLES/SCOPE_*/MIN_*/THRESHOLD/PATHS/ALLOWED_*/
     WHITELIST/`…`GLOBS` 之类名字，值是"角色名字符串集合/列表"或数字常量；
  R2 **成员判定字面量** —— `x in {"code-review", ...}` / `x not in ("doc-audit",)`：
     这是"临时写死一个角色集合"的最常见形态（换行也逃不掉 AST）；
  R3 路径清单字面量 —— 名字含 `PATHS/DIRS/ROOTS/TARGETS` 的常量，值是 ≥2 个路径字符串。
  （ruff 规则号分级不算政策：它们是工具配置，已在 `agents/policy.json::lint_rules`。）

豁免：`verify/policy-hardcode-exemptions.json` —— **每条必须写 category + reason**，
且只能豁免"显式列出的路径/名称/表达式"，不提供整文件豁免（豁免本身是政策决定，须留痕）。
另有**就地豁免**形态 `X = _exempted_local(...)`：用于"本函数内造 fixture 数据、不是闸门政策"的情形，
理由写在赋值处（探测器识别该调用名并放行，仍在扫描范围内，不是关掉检查）。

反向对照（`TG-6` ⑤"倒过来试"）：自检把注入样本写到临时目录再扫描，
断言 `_ROLES = {"code-review"}`、`x in ("doc-audit",)`、`PATHS = ["a","b"]` 三类**必须被判违规**，
并断言"从 policy 读取"与"`_exempted_local` 就地豁免"两种写法**必须放行**（防为了过闸门把代码写坏）。

用法：
    .venv\\Scripts\\python.exe verify\\verify_no_policy_hardcode.py            # 扫描政策声明的扫描集（0 = 干净）
    .venv\\Scripts\\python.exe verify\\verify_no_policy_hardcode.py --dir <d>  # 只扫指定目录（自检用）
    .venv\\Scripts\\python.exe verify\\verify_no_policy_hardcode.py --coverage # 只打印扫描集双向差集
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-15⑦ 硬编码政策闸门：scripts/verify 内不得再写死角色集合/成员判定字面量/覆盖路径清单；豁免须写 category+reason；含三类注入样本反向对照', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 10, 'routes': [], 'requires': ['none']}

import ast
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPTIONS_PATH = Path(__file__).resolve().parent / "policy-hardcode-exemptions.json"
# A6（R1）：扫描集**不再写死在这里**，改由 agents/policy.json::hardcode_scan_coverage 声明。
# 旧实现 `SCAN_DIRS = ("scripts", "verify")` 实测只覆盖 39/182 个 .py（审核 R1 判 major）。
SCAN_DIRS = ("scripts", "verify")  # 仅保留作"旧实现对照"（反向对照⑨ 用它证明覆盖面确实变宽了）
SELF_NAME = "verify_no_policy_hardcode.py"

sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0

# 说明（2026-09-23 doc-audit finding 1）：本脚本的断言语义数**不要抄进文档**——它会随新增判据变化
# （9 → 21 → 23 → …）。文档一律写"以脚本输出的 ALL PASS (N assertions) 为准"，或在证据行里
# 附**当时实测**的 N 与日期。手抄导致的漂移本轮已实测三次。


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


# 角色名形态：小写词 + 连字符分段（code-review / doc-audit / impact-assessment / lessons-learned）
def role_like(word: str, *, allow_single_segment_pair: bool = False) -> bool:
    """像"agent 角色名"。

    2026-09-23 二查后收紧（实测误报 18 条）：单连字符词里混着大量**非角色**的合法字面量——
    `self-chosen`（scope 来源值）、`doc-only`（覆盖归类）、`idx-demo`/`st-demo`（fixture 命名）。
    因此默认要求 **≥2 个连字符**（`impact-assessment`/`lessons-learned`/`tech-research`/`agent-onboarding-review`），
    这样单连字符的 `code-review`/`doc-audit` 只在**上下文明确指向角色**时才判
    （`allow_single_segment_pair=True`，由调用方按变量名/比较对象名给出）。

    这是一个**有意的取舍**，且写在注释里：闸门宁可"窄一点但要真"，也不要"宽到天天误报"——
    误报会让闸门被当成噪音绕过（这正是 TG-11 事故的形态之一）。
    """
    if "-" not in word:
        return False
    parts = word.split("-")
    if len(parts) < (2 if allow_single_segment_pair else 3):
        return False
    return all(part.isidentifier() and part.islower() and part.isalpha() for part in parts)


def names_role_context(node: ast.AST | None) -> bool:
    """该表达式是否**明确与角色相关**（名字里含 role/agent 或下标/属性名含之）。"""
    if node is None:
        return False
    for sub in ast.walk(node):
        for attr in ("id", "attr"):
            name = getattr(sub, attr, None)
            if isinstance(name, str) and ("role" in name.lower() or "agent" in name.lower()):
                return True
    return False


def path_like(word: str) -> bool:
    """像"目录/文件清单里的一项"。

    判据刻意宽松（`verify`/`scripts` 这类裸目录名也要被抓）但**先排除角色名形态**，
    否则 `["impact-assessment", …]` 会被同时判成角色集合与路径清单。
    """
    if role_like(word):
        return False
    if any(sep in word for sep in ("/", "\\")):
        return True
    if any(ch.isdigit() for ch in word):  # 模型名/版本号（text-embedding-3-large、gpt-4o）
        return False
    return bool(word) and all(ch.isalnum() or ch in "._-" for ch in word)


POLICY_NAME_HINTS = (
    "ROLE", "MIN_", "THRESHOLD", "ALLOWED_", "WHITELIST", "REVIEW", "CLOSE_",
)
PATH_NAME_HINTS = ("PATH", "DIR", "ROOT", "TARGET", "GLOB")

# 本探测器自身的内置兜底（跨平台 venv 目录名）——见 policy-hardcode-exemptions.json 的说明
VENV_PARTS = {"Scripts", "bin"}

# 探测器的**词表**（不是政策本身）：用来识别"有人在代码里抄账本状态白名单"。
# 这是"检查工具的词表"，与"闸门政策"是两回事——所以它是本文件的常量，并在
# policy-hardcode-exemptions.json 里以 category=tool-self 显式登记。
LEDGER_STATUS_VALUES = {"queued", "running", "succeeded", "failed", "cancelled"}


def _str_const(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _iter_str(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            yield from _iter_str(elt)
    elif isinstance(node, ast.Dict):
        # 2026-09-23 二查 finding：`{"code-review": 1}` 这类**字典字面量**此前完全漏检
        # （旧实现只遍历 List/Tuple/Set）——而"角色名当 key 建表"正是最自然的写死形态。
        for key in node.keys:
            if key is not None:
                yield from _iter_str(key)
        for val in node.values:
            yield from _iter_str(val)


def _num_const(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    return None


class Detector(ast.NodeVisitor):
    def __init__(self, known_roles: set[str] | None = None) -> None:
        self.findings: list[dict] = []
        # **角色名词表 = 仓库里实际存在的 spec 文件名**（`agents/functions/*.md`）。
        # 二查后收紧（实测误报：`definitely-not-a-real-model`、`run-empty-ev`、`idx-demo` 都被当角色名）：
        # 光看"像小写连字符词"太宽；而"像角色"的真判据是**它在仓库里有对应对象**。
        # 注意这不会造成"删 spec 即消音"：删掉 spec 会让封闭世界检查与 C2 立刻报错（见 agent_policy）。
        self.known_roles = known_roles or set()

    def _is_role(self, word: str, ctx_role: bool = False) -> bool:
        if word in self.known_roles:
            return True
        return ctx_role and role_like(word, allow_single_segment_pair=True)

    def _add(self, rule: str, node: ast.AST, detail: str, category: str = "policy") -> None:
        self.findings.append({"rule": rule, "line": getattr(node, "lineno", 0),
                              "detail": detail, "category": category})

    # R1 / R3：政策常量赋值
    def visit_Assign(self, node: ast.Assign) -> None:
        if _is_exempted_local(node.value):
            self.generic_visit(node)
            return
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        for name in names:
            upper = name.upper()
            # 变量名本身指向角色（`_ROLES`/`REVIEW_ROLES`/…）时，允许把单连字符词也算角色名——
            # 否则 `_ROLES = {"code-review"}`（最经典的写死形态）会被"≥2 连字符"规则漏掉。
            role_ctx = "ROLE" in upper or "AGENT" in upper
            strings = [s for s in _iter_str(node.value)]
            roles = sorted({s for s in strings if self._is_role(s, role_ctx)})
            if roles and any(h in upper for h in POLICY_NAME_HINTS):
                self._add("R1", node, f"{name} = 角色集合{roles}（政策须来自 spec frontmatter/fanout.json）")
            elif len(roles) >= 2:
                self._add("R1", node, f"{name} 内含多个角色名字面量{roles}（疑似写死角色集合）")
            paths = [s for s in strings if len(s) > 1 and path_like(s)]
            if len(paths) >= 2 and any(h in upper for h in PATH_NAME_HINTS):
                self._add("R3", node, f"{name} = 路径清单{paths}（覆盖路径须来自 agents/policy.json::lint_paths）")
            # 状态白名单（二查 finding：`_ALLOWED_STATES=[...]` 是 TG-15 明列须数据化的形态之一）
            states = sorted({s for s in strings if s in LEDGER_STATUS_VALUES})
            if len(states) >= 2:
                self._add("S1", node,
                          f"{name} = 状态白名单{states}（账本状态机须来自 agents/policy.json::ledger_status）",
                          category="status")
            num = _num_const(node.value)
            if num is not None and any(h in upper for h in POLICY_NAME_HINTS) and "VERSION" not in upper:
                self._add("R1", node, f"{name} = {num:g}（阈值须来自 agents/policy.json）")
        self.generic_visit(node)

    # R2：成员判定 / 等值判定 使用角色名字面量
    def visit_Compare(self, node: ast.Compare) -> None:
        # 上下文提示：`role == "code-review"` / `r["role"] in {...}` 这类明确与角色相关的比较，
        # 允许把单连字符词（code-review / doc-audit）也当角色名处理。
        ctx_role = names_role_context(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            members = sorted({s for s in _iter_str(comparator) if self._is_role(s, ctx_role)})
            if not members:
                continue
            if isinstance(op, (ast.In, ast.NotIn)):
                self._add("R2", node,
                          f"成员判定使用角色名字面量{members}（角色集合须来自 spec frontmatter 的 scope_required）")
            elif isinstance(op, (ast.Eq, ast.NotEq)):
                # 二查 finding：`if role == "code-review"` 是 TG-15 删掉的**旧版形态**，
                # 旧实现只认 in/not-in，于是同一形态可以原样写回而不被拦。
                self._add("R2", node,
                          f"等值判定使用角色名字面量{members}（角色集合须来自 spec frontmatter 的 scope_required）")
        self.generic_visit(node)


# ------------------------------------------------------------------ 豁免加载

def exemption_rules() -> dict:
    """台账校验参数（`agents/policy.json::hardcode_exemptions`，A11/N4）——政策数据，不写死在这里。"""
    data = load_policy().policy_file.get("hardcode_exemptions")
    if not isinstance(data, dict):
        raise SystemExit("HARDCODE-ERROR: agents/policy.json 缺 hardcode_exemptions"
                         "（豁免台账的校验参数；缺它则台账不可核 → fail-closed）")
    for key, typ in (("categories", list), ("min_reason_chars", int),
                     ("category_wide_categories", list), ("category_wide_files", list)):
        if not isinstance(data.get(key), typ) or isinstance(data.get(key), bool):
            raise SystemExit(f"HARDCODE-ERROR: hardcode_exemptions.{key} 类型非法：{data.get(key)!r}")
    return data


def load_exemptions(path: Path | None = None) -> dict:
    """读**并校验**豁免台账（A11 / 审核 N4）。

    为什么必须校验（二查实测的绕过路径）：原实现只要求每条有 category/reason 两个**非空字符串**，
    于是往台账里加一条 `{"file": "verify/verify_close_readiness.py", "category": "policy",
    "reason": "…", "categories": ["policy"]}` 就 rc 0、同一屏打印"无政策硬编码 clean"——
    **一条数据编辑把整份文件静音**，而这与台账自述"绝不整文件豁免"直接冲突，
    也与本模块"豁免 = 有理由的**最小**例外"的设计相反。

    现四条校验（参数全部来自 policy.json，见 `exemption_rules()`）：
      ① `category` ∈ 白名单（拼错/自造类别不再静默生效）；
      ② `reason` 必填且 ≥ `min_reason_chars`（"有理由"要能被复核）；
      ③ **作用域最小化**：`names`/`functions`/`categories` 不得全空——没有作用域的条目
         在 `scan_file` 里等价于"豁免该文件的一切发现"，即整文件豁免 → 拒；
      ④ 类别级豁免（`categories`）是唯一能覆盖整份文件内某一类发现的形态，
         因此只允许出现在 `category_wide_files`（工具自身的词表），取值限 `category_wide_categories`。
    """
    rules = exemption_rules()
    allowed = {str(c) for c in rules["categories"]}
    wide_files = {str(f) for f in rules["category_wide_files"]}
    wide_cats = {str(c) for c in rules["category_wide_categories"]}
    min_reason = int(rules["min_reason_chars"])

    if path is None:
        path = EXEMPTIONS_PATH
    path = Path(path)
    if not path.is_file():
        return {"roles": [], "paths": [], "numbers": [], "status": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("roles", "paths", "numbers", "status"):
        for i, item in enumerate(data.get(key) or []):
            where = f"{path.name}::{key}[{i}]"
            file = str(item.get("file") or "").strip()
            if not file:
                raise SystemExit(f"HARDCODE-ERROR: 豁免台账 {where} 缺 file（豁免必须指向具体文件）")
            category = str(item.get("category") or "").strip()
            if category not in allowed:
                raise SystemExit(
                    f"HARDCODE-ERROR: 豁免台账 {where} 的 category={category!r} 不在白名单 "
                    f"{sorted(allowed)} 内（{file}）——自造类别不能成为静音开关")
            reason = str(item.get("reason") or "").strip()
            if len(reason) < min_reason:
                raise SystemExit(f"HARDCODE-ERROR: 豁免台账 {where} 的 reason 过短（<{min_reason} 字符，"
                                 f"{file}）——豁免必须写明理由，否则无法复核")
            names = [str(n) for n in (item.get("names") or []) if str(n).strip()]
            funcs = [str(f) for f in (item.get("functions") or []) if str(f).strip()]
            cats = [str(c) for c in (item.get("categories") or []) if str(c).strip()]
            if not (names or funcs or cats):
                raise SystemExit(
                    f"HARDCODE-ERROR: 豁免台账 {where}（{file}）没有任何作用域"
                    f"（names/functions/categories 全空）= **整文件豁免**，台账自述『绝不整文件豁免』"
                    f"——请写明具体的常量名/函数名，或改用就地豁免 `_exempted_local`")
            if cats:
                bad = [c for c in cats if c not in wide_cats]
                if file not in wide_files or bad:
                    raise SystemExit(
                        f"HARDCODE-ERROR: 豁免台账 {where}（{file}）用 categories={cats} 做**类别级豁免**"
                        f"——这会把该文件里这一类发现**全部**静音（N4 实测的形态）。类别级豁免只允许"
                        f"出现在 {sorted(wide_files)} 且取值限 {sorted(wide_cats)}；"
                        f"其它文件请按 names/functions 精确豁免")
    return data


def _fn_ranges(tree: ast.AST, names: set[str]) -> list[tuple[int, int]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out.append((node.lineno, getattr(node, "end_lineno", node.lineno)))
    return out


def known_roles() -> set[str]:
    """仓库实际存在的角色名 = `agents/functions/*.md` 的文件名（政策数据源的目录清单）。"""
    try:
        spec_dir = load_policy().spec_dir
    except Exception:  # 政策缺失时仍要能扫（否则闸门自己先崩）
        spec_dir = ROOT / "agents" / "functions"
    if not spec_dir.is_dir():
        return set()
    return {p.stem for p in spec_dir.glob("*.md")}


def scan_file(path: Path, exemptions: dict, roles: set[str]) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        return [{"rule": "SYNTAX", "line": exc.lineno or 0, "file": rel,
                 "detail": f"解析失败：{exc.msg}"}]

    detector = Detector(roles)
    detector.visit(tree)
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name

    allowed_names: set[str] = set()
    fn_ranges: list[tuple[int, int]] = []
    allowed_categories: set[str] = set()
    for item in (exemptions.get("roles", []) + exemptions.get("paths", [])
                 + exemptions.get("numbers", []) + exemptions.get("status", [])):
        if item.get("file") != rel:
            continue
        allowed_names |= {str(n) for n in (item.get("names") or [])}
        fn_ranges += _fn_ranges(tree, {str(f) for f in (item.get("functions") or [])})
        allowed_categories |= {str(c) for c in (item.get("categories") or [])}

    kept: list[dict] = []
    for finding in detector.findings:
        # **先盖 file 键再判豁免**：`file` 是 findings 的契约字段，任何消费方（`--dir` 分支、
        # 未来的 JSON 输出、CI 解析）都按它定位。2026-09-23 doc-audit finding 5 实测：
        # `--dir` 分支在 `f['file']` 上 KeyError 崩溃（不是它猜的"恒 return 0"）——
        # 根因正是这里先判豁免、只对"存活项"盖键。
        finding["file"] = rel
        if finding.get("category") in allowed_categories:
            continue
        if finding["line"] in {ln for start, end in fn_ranges for ln in range(start, end + 1)}:
            continue
        # 名字豁免：以 detail 的**首个词元**（`<NAME> ...`）精确匹配台账里列出的常量名。
        # 旧实现用 `f"'{name}'" in detail or f"={name} " in detail` 反查，对
        # `FIXTURE_FANOUT 内含多个角色名…`（无引号、无 `=`）这种文案直接漏掉 → 已改为正向取值。
        head_token = finding["detail"].split(" ", 1)[0]
        if head_token in allowed_names:
            continue
        kept.append(finding)
    return kept


def _is_exempted_local(node: ast.AST) -> bool:
    """变量值取自 `_exempted_local()`（"本函数内造 fixture 数据，不是闸门政策"的显式声明）。

    这是"每处豁免都要有一句理由"的**就地理由**形态：比集中在台账里更贴近代码，
    同时仍可被本探测器识别（不是把检查关掉，而是把该处标成有理由的例外）。
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id == "_exempted_local"
    if isinstance(node, ast.Name):
        return node.id == "_exempted_local"
    return False



def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _excluded(rel: str, exclusions: list[str]) -> bool:
    """`rel`（仓库相对 posix 路径）是否落在 `exclude_dirs` 里。

    裸名（`paper-qa`/`.venv`/`node_modules`/`__pycache__`/…）按**路径任意段**匹配（能抓嵌套
    的 `node_modules`）；含 `/` 的（`agents/runs`）按前缀匹配。
    """
    parts = rel.split("/")
    for raw in exclusions:
        item = str(raw).strip("/")
        if not item:
            continue
        if "/" in item:
            if rel == item or rel.startswith(item + "/"):
                return True
        elif item in parts:
            return True
    return False


def _iter_py(base: Path, exclusions: list[str]) -> list[str]:
    """`base` 递归下的全部 `.py`（仓库相对路径，已剪枝排除目录）。"""
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        here = Path(dirpath)
        rel_dir = _rel(here) if here != ROOT else ""
        rel_dir = "" if rel_dir == ROOT.name or rel_dir == "." else rel_dir
        dirnames[:] = sorted(d for d in dirnames
                             if not _excluded(f"{rel_dir}/{d}".strip("/"), exclusions))
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                rel = f"{rel_dir}/{fn}".strip("/")
                if not _excluded(rel, exclusions):
                    out.append(rel)
    return out


def scan_coverage() -> tuple[list[str], list[str], list[str], list[str]]:
    """扫描集 ↔ 文件系统**双向差集**（同 `verify_md_tables.py` 的 A10 做法；审核 R1）。

    返回 `(应扫, 实扫, problems, exclude_dirs)`。

    * **应扫**（expected）= `hardcode_scan_coverage.roots` 递归下的全部 `.py`（每条 roots 必须是**存在**的目录）。
    * **实扫**（actual）= `hardcode_scan_coverage.globs` 的展开（每条必须 ≥1 命中）。
    * `exclude_dirs`（vendored / 环境 / 缓存 / 运行产物）在两侧同时生效。
    * **封闭世界**：仓库里任何含 `.py` 的树必须落在 roots 或 exclude_dirs 内——否则 FAIL 并点名，
      这样"新加一棵代码树但没人把它纳入闸门"不会静默通过。
    * 本脚本自身从两侧同时剔除，故 `N == M` 可直接比较（自跳数单独打印）。

    为什么 roots 必须**独立声明**（而不是从 globs 反推）见 `verify_md_tables.coverage_problems()`：
    从 glob 反推是恒真式，删掉一条 glob 会连带缩小它声明的范围，"少扫一棵树"永远看不出来。
    """
    data = load_policy().policy_file.get("hardcode_scan_coverage")
    if not isinstance(data, dict):
        raise SystemExit("HARDCODE-ERROR: agents/policy.json 缺 hardcode_scan_coverage"
                         "（扫描集范围声明；缺它则『应扫/实扫』无从核对 → fail-closed）")
    roots = [str(p) for p in (data.get("roots") or [])]
    globs = [str(p) for p in (data.get("globs") or [])]
    exclusions = [str(p) for p in (data.get("exclude_dirs") or [])]
    problems: list[str] = []
    if not roots:
        problems.append("[覆盖声明] hardcode_scan_coverage.roots 为空 → 应扫集无从计算（fail-closed）")
    if not globs:
        problems.append("[覆盖声明] hardcode_scan_coverage.globs 为空 → 实扫集无从计算（fail-closed）")

    expected: set[str] = set()
    for root in roots:
        base = ROOT / root
        if not base.is_dir():
            problems.append(f"[覆盖声明] roots 里的目录不存在：{root!r}（fail-closed，不静默跳过）")
            continue
        expected |= {r for r in _iter_py(base, exclusions)}

    actual: set[str] = set()
    for pattern in globs:
        hits = {_rel(p) for p in ROOT.glob(pattern) if p.is_file() and p.suffix == ".py"}
        hits = {h for h in hits if not _excluded(h, exclusions)}
        if not hits:
            problems.append(f"[死 glob] {pattern!r} 命中 0 个文件：留着它 = 让人以为扫了、其实没扫"
                            f"（删掉或写对，不要留死数据）")
        actual |= hits

    self_rel = _rel(Path(__file__).resolve())
    expected.discard(self_rel)
    actual.discard(self_rel)

    for rel in sorted(expected - actual):
        problems.append(f"[应扫未扫] {rel}：在 roots 范围内，但没有任何 glob 覆盖它"
                        f" → 闸门**根本不检查它**（R1 形态：旧实现漏 39/182）")
    for rel in sorted(actual - expected):
        problems.append(f"[实扫超出声明] {rel}：被 glob 扫到，但不在 roots 声明范围内"
                        f" → 要么补进 roots，要么把它移出扫描集（声明与行为必须一致）")

    # 封闭世界：含 .py 的树必须被显式纳管（roots）或显式排除（exclude_dirs）
    managed = {str(r).strip("/") for r in roots}
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir() or _excluded(entry.name, exclusions):
            continue
        stray = [r for r in _iter_py(entry, exclusions)
                 if r != self_rel and not any(r.startswith(m + "/") for m in managed)]
        if stray:
            problems.append(f"[未纳管树] {entry.name}/ 含 {len(stray)} 个 .py 但既不在 roots 也不在 "
                            f"exclude_dirs 内（例：{stray[:3]}）——新代码树必须显式纳管或显式排除，"
                            f"否则闸门会静默漏扫")
    return sorted(expected), sorted(actual), problems, exclusions


def scan(dirs: list[Path], roles: set[str] | None = None) -> list[dict]:
    exemptions = load_exemptions()
    roles = known_roles() if roles is None else roles
    findings: list[dict] = []
    for base in dirs:
        # 2026-09-25 修复：以前直接用调用方给的（可能是**相对**）路径 → `scan_file` 里的
        # `path.relative_to(ROOT)` 失败、回落成 `path.name`，于是**所有按文件作用域的豁免
        # 静默失效**（实测 `--dir verify` 因此报出 6 条本应豁免的发现）。统一 resolve 成绝对路径。
        base = base.resolve()
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name == SELF_NAME or "__pycache__" in path.parts:
                continue
            if any(part in {".venv", "node_modules"} for part in path.parts):
                continue
            findings += scan_file(path, exemptions, roles)
    return findings


def policy_scan_roots() -> list[Path]:
    """政策声明的扫描**树**（`hardcode_scan_coverage.roots`）；声明与实际不一致即 fail-closed。"""
    data = load_policy().policy_file.get("hardcode_scan_coverage") or {}
    roots = [str(p).strip("/") for p in (data.get("roots") or [])]
    if not roots:
        raise SystemExit("HARDCODE-ERROR: hardcode_scan_coverage.roots 为空 → 无扫描集（fail-closed）")
    return [ROOT / r for r in roots]



# ------------------------------------------------------------------ 反向对照

INJECTIONS = {
    "roles_set.py": '_ROLES = {"code-review"}\n',
    "member_literal.py": 'def f(role):\n    return role in ("doc-audit",)\n',
    "paths_list.py": '_SCAN_PATHS = ["verify", "scripts"]\n',
    # 二查 finding 实测的假阴性形态（旧实现全部漏检）：
    "dict_roles.py": '_ROLE_MAP = {"code-review": 1, "doc-audit": 2}\n',
    "eq_literal.py": 'def f(role):\n    if role == "code-review":\n        return True\n    return False\n',
    "status_whitelist.py": '_ALLOWED_STATES = ["succeeded", "failed", "cancelled"]\n',
}


def selfcheck() -> int:
    policy = load_policy()
    ok("数据源完备（政策已全部落到数据文件，无未声明 spec/无死键）",
       policy.closure_problems() == [], f"problems={policy.closure_problems()[:2]}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, body in INJECTIONS.items():
            (tmp / name).write_text(body, encoding="utf-8")
        findings = scan([tmp])
        by_file: dict[str, list[str]] = {}
        for f in findings:
            by_file.setdefault(f["file"], []).append(f["rule"])

    ok("反向对照① 注入 `_ROLES = {\"code-review\"}` → 判违规（R1）", "R1" in by_file.get("roles_set.py", []),
       f"findings={by_file}")
    ok("反向对照② 注入 `role in (\"doc-audit\",)` → 判违规（R2）",
       "R2" in by_file.get("member_literal.py", []), f"findings={by_file}")
    ok("反向对照③ 注入路径清单字面量（名字含 PATHS）→ 判违规（R3）",
       "R3" in by_file.get("paths_list.py", []), f"findings={by_file}")
    ok("反向对照⑥ 注入**字典字面量**角色表 → 判违规（R1，二查实测旧实现漏检）",
       "R1" in by_file.get("dict_roles.py", []), f"findings={by_file}")
    ok("反向对照⑦ 注入**等值判定** `role == \"code-review\"` → 判违规（R2，TG-15 删掉的旧形态）",
       "R2" in by_file.get("eq_literal.py", []), f"findings={by_file}")
    ok("反向对照⑧ 注入**状态白名单** `_ALLOWED_STATES=[...]` → 判违规（S1）",
       "S1" in by_file.get("status_whitelist.py", []), f"findings={by_file}")

    # 好样本：从政策读取的写法必须放行（防"为了过闸门把代码写坏"）
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "good.py").write_text(
            "from verify.agent_policy import load_policy\n"
            "POLICY = load_policy()\n"
            "ROLES = POLICY.review_roles\n"
            "PATHS = POLICY.lint_paths\n"
            "def f(role):\n"
            "    return role in ROLES\n", encoding="utf-8")
        findings = scan([tmp])
    ok("反向对照④ 政策来自 load_policy() 的写法 → 放行（不制造假红）", findings == [], f"findings={findings}")

    # 就地豁免：`_exempted_local(...)` 标注的 fixture 数据必须放行（但仅限该赋值处）
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "local_exempt.py").write_text(
            "def _exempted_local(value):\n"
            "    \"\"\"本函数内造 fixture 数据，不是闸门政策。\"\"\"\n"
            "    return value\n"
            "\n"
            "def f():\n"
            "    paths = _exempted_local(['Alpha.pdf', 'Beta.pdf'])\n"
            "    return paths\n"
            "\n"
            "_REAL_POLICY_PATHS = ['verify', 'scripts']\n", encoding="utf-8")
        findings = scan([tmp])
    ok("反向对照⑤ `_exempted_local` 就地豁免放行，但同文件真硬编码仍被抓",
       len(findings) == 1 and "_REAL_POLICY_PATHS" in findings[0]["detail"], f"findings={findings}")

    # ---- A6（R1）扫描集：政策驱动 + 双向差集 + 封闭世界 + 覆盖面确实变宽的对照 ---------------
    expected, actual, cov_problems, exclusions = scan_coverage()
    ok("A6 扫描集双向差集（政策 roots ↔ globs）：应扫 N / 实扫 M 一致",
       not cov_problems and len(expected) == len(actual),
       f"应扫 {len(expected)} / 实扫 {len(actual)}"
       + ("" if not cov_problems else f"；problems={cov_problems[:3]}"))
    old_scan = {r for r in _iter_py(ROOT / SCAN_DIRS[0], []) } | {r for r in _iter_py(ROOT / SCAN_DIRS[1], [])}
    widened = sorted(set(expected) - old_scan)
    ok("反向对照⑨ 覆盖面**确实**比旧实现（`SCAN_DIRS=('scripts','verify')`）宽：新纳入文件非空",
       bool(widened), f"旧实现 {len(old_scan)} 个 → 现应扫 {len(expected)} 个；新纳入 {len(widened)} 个"
                      f"（例：{widened[:3]}）")
    # 注入样本必须落在**此前未被扫**的树里，否则这条对照证明不了"新纳入的树真的被检查"
    probe_rel = next((r for r in widened if r.endswith(".py")), None)
    if probe_rel is None:
        ok("反向对照⑨b 此前未被扫的 .py 内注入政策硬编码 → 判违规并点名", False, "没有新纳入的文件可注入")
    else:
        src = (ROOT / probe_rel).read_text(encoding="utf-8", errors="replace")
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / Path(probe_rel).name
            probe.write_text(src + '\n_INJECTED_POLICY_ROLES = {"code-review", "doc-audit"}\n',
                             encoding="utf-8")
            # 用真实入口（`--dir`）跑，判据取**子进程 rc**，不读代码猜
            import subprocess
            run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--dir", str(probe.parent)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok(f"反向对照⑨b 此前未被扫的树（{Path(probe_rel).parts[0]}/）内注入政策硬编码 → rc≠0 且点名该文件",
           run.returncode != 0 and f"{Path(probe_rel).name}:" in run.stdout and "R1" in run.stdout,
           f"rc={run.returncode} out={run.stdout.strip().splitlines()[0] if run.stdout.strip() else ''}")

    real = scan(policy_scan_roots())
    ok("仓库现状：政策声明的扫描集（roots 展开）内无政策硬编码", real == [],
       "clean" if not real else f"{len(real)} 条：" + "; ".join(
           f"{f['file']}:{f['line']} {f['rule']} {f['detail'][:60]}" for f in real[:5]))

    # ---- N4 反向对照：豁免台账**必须被校验**（一条数据编辑不得静音整份文件）------------
    # 二查实测：往台账加一条 `{"file": "verify/verify_close_readiness.py", "category": "policy",
    # "categories": ["policy"], "reason": "…"}` → rc 0，且同一屏打印"无政策硬编码 clean"。
    bad_ledgers = {
        "整文件豁免（names/functions/categories 全空）": {
            "roles": [{"file": "verify/verify_agentops.py", "category": "test-fixture",
                       "reason": "就想放行整个文件，理由故意写得够长"}]},
        "类别级静音 categories:[\"policy\"]": {
            "roles": [{"file": "verify/verify_close_readiness.py", "category": "policy",
                       "reason": "想用一条类别豁免把这份文件整个静音掉，理由够长",
                       "categories": ["policy"]}]},
        "白名单外的自造 category": {
            "paths": [{"file": "verify/verify_agentops.py", "category": "whatever",
                       "reason": "随便编一个类别名，理由写得够长", "names": ["SOMETHING"]}]},
        "理由过短": {
            "numbers": [{"file": "verify/verify_agentops.py", "category": "test-fixture",
                         "reason": "短", "names": ["SOMETHING"]}]},
        "缺 file": {
            "status": [{"category": "tool-self", "reason": "没有指向任何文件的豁免，理由够长",
                        "names": ["SOMETHING"]}]},
    }
    for label, ledger in bad_ledgers.items():
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / "exemptions.json"
            probe.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
            try:
                load_exemptions(probe)
                ok(f"N4 反向对照：豁免台账「{label}」→ 必须被拒", False, "未抛错（整文件豁免被放行）")
            except SystemExit as exc:
                ok(f"N4 反向对照：豁免台账「{label}」→ 被拒（rc≠0）且点名原因",
                   "HARDCODE-ERROR" in str(exc), str(exc)[:96])

    with tempfile.TemporaryDirectory() as td:
        probe = Path(td) / "exemptions.json"
        probe.write_text(json.dumps(
            {"roles": [{"file": "verify/verify_agentops.py", "category": "test-fixture",
                        "reason": "合成角色名 fixture，不是闸门政策；作用域精确到常量名",
                        "names": ["code-review"]}]}, ensure_ascii=False), encoding="utf-8")
        good = load_exemptions(probe)
    ok("N4 正向对照：有理由 + 作用域精确的最小豁免 → 放行（好输入不误报）",
       (good["roles"][0]["names"] if good.get("roles") else None) == ["code-review"], f"good={good}")

    # ---- 退出码断言：**用真实入口跑**，不是"读代码判断它会不会 fail-closed" ----
    # 2026-09-23 doc-audit finding 5：`--dir` 分支被指"恒 return 0"。实测真相是它在
    # `f['file']` 上 KeyError 崩溃（已修：scan_file 先盖 file 键）。无论哪种，**判据都必须是
    # 子进程的真实退出码**——本轮之前只看了 return 语句，所以这个洞活着。
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bad_dir = tmp / "with_findings"
        clean_dir = tmp / "clean"
        bad_dir.mkdir()
        clean_dir.mkdir()
        (bad_dir / "bad.py").write_text('_ROLES = {"code-review"}\n', encoding="utf-8")
        (clean_dir / "good.py").write_text(
            "from verify.agent_policy import load_policy\nPOLICY = load_policy()\n", encoding="utf-8")
        probe_bad = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--dir", str(bad_dir)],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
        probe_clean = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--dir", str(clean_dir)],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok("`--dir` 分支：有发现 → 退出码非 0（判据取子进程真实 rc，不是读代码）",
       probe_bad.returncode != 0 and "1 findings" in probe_bad.stdout,
       f"rc={probe_bad.returncode} out={(probe_bad.stdout + probe_bad.stderr).strip()[:80]}")
    ok("`--dir` 分支：无发现 → 退出码 0（防假红）",
       probe_clean.returncode == 0, f"rc={probe_clean.returncode}")
    ok("`--dir` 分支发现项打印含 file 定位（契约字段，缺它即崩溃/无法定位）",
       "bad.py:" in probe_bad.stdout, f"out={probe_bad.stdout.strip()[:80]}")
    return 0


def main() -> int:
    if "--dir" in sys.argv:
        dirs = [Path(sys.argv[sys.argv.index("--dir") + 1])]
        findings = scan(dirs)
        for f in findings:
            print(f"{f['file']}:{f['line']} [{f['rule']}] {f['detail']}")
        print(f"--- {len(findings)} findings ---")
        return 1 if findings else 0

    # A6（R1）：**先核扫描集，再看扫描结果**——"应扫/实扫"不一致时，扫描结果本身没有意义
    # （PASS 会从"查过且没问题"退化成"没查"）。故一致性问题一律 fail-closed。
    expected, actual, cov_problems, exclusions = scan_coverage()
    print(f"扫描集双向差集（政策 hardcode_scan_coverage）：应扫 {len(expected)} / 实扫 {len(actual)} → "
          f"{'一致' if not cov_problems and len(expected) == len(actual) else '**不一致（fail-closed）**'}"
          f"（roots={[str(p) for p in (load_policy().policy_file.get('hardcode_scan_coverage') or {}).get('roots') or []]}；"
          f"排除 {exclusions}；本脚本自身跳过 1）")
    if cov_problems:
        print(f"\nHARDCODE FAIL（扫描集声明与实际不一致，{len(cov_problems)} 项）：")
        for item in cov_problems:
            print(f"  - {item}")
        return 1

    if "--coverage" in sys.argv:
        print("（--coverage：只核扫描集，不跑自检与仓库扫描）")
        return 0

    selfcheck()
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
