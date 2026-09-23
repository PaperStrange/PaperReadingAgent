"""TG-15⑦：**硬编码政策探测器**（offline）——"政策必须在数据文件，不许写进代码"的可执行闸门。

背景（`TG-15` 卡）：闸门原先靠"遇到一个场景加一条判据"成长，于是同一个政策在**多处**各存一份：
`scripts/agent-ops.py` 的角色集合与偏离长度、`verify/verify_close_readiness.py` 的关闭角色与
按角色判据、`verify/verify_lint.py` 的覆盖路径、`scripts/report-freshness.py` 的归档前缀、
`verify/verify_agentops.py` 又一份角色集合。**加角色/换分支/调阈值都要改代码**。
TG-15 起政策统一落在三处数据：`agents/fanout.json`（步骤/target）、各 spec frontmatter
（角色属性）、`agents/policy.json`（阈值与开关）；本脚本守住"不许再退回代码里"。

扫描对象：`scripts/**`、`verify/**` 的 `.py`，**同时覆盖 scripts 与 verify 两棵树的同名点**。

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
    .venv\\Scripts\\python.exe verify\\verify_no_policy_hardcode.py            # 扫描仓库（0 = 干净）
    .venv\\Scripts\\python.exe verify\\verify_no_policy_hardcode.py --dir <d>  # 只扫指定目录（自检用）
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-15⑦ 硬编码政策闸门：scripts/verify 内不得再写死角色集合/成员判定字面量/覆盖路径清单；豁免须写 category+reason；含三类注入样本反向对照', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 10, 'routes': [], 'requires': ['none']}

import ast
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPTIONS_PATH = Path(__file__).resolve().parent / "policy-hardcode-exemptions.json"
SCAN_DIRS = ("scripts", "verify")
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

def load_exemptions(path: Path | None = None) -> dict:
    path = path or EXEMPTIONS_PATH
    if not path.is_file():
        return {"roles": [], "paths": [], "numbers": [], "status": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("roles", "paths", "numbers", "status"):
        for item in data.get(key) or []:
            if not str(item.get("category") or "").strip() or not str(item.get("reason") or "").strip():
                raise SystemExit(
                    f"HARDCODE-ERROR: 豁免台账 {path.name} 的 {key} 条目缺 category/reason：{item!r}"
                    "（豁免必须可核：说明类别与理由）")
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



def scan(dirs: list[Path], roles: set[str] | None = None) -> list[dict]:
    exemptions = load_exemptions()
    roles = known_roles() if roles is None else roles
    findings: list[dict] = []
    for base in dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name == SELF_NAME or "__pycache__" in path.parts:
                continue
            if any(part in {".venv", "node_modules"} for part in path.parts):
                continue
            findings += scan_file(path, exemptions, roles)
    return findings


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

    real = scan([ROOT / d for d in SCAN_DIRS])
    ok("仓库现状：scripts/** 与 verify/** 无政策硬编码", real == [],
       "clean" if not real else f"{len(real)} 条：" + "; ".join(
           f"{f['file']}:{f['line']} {f['rule']} {f['detail'][:60]}" for f in real[:5]))

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

    selfcheck()
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
