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


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


# 角色名形态：小写词 + 连字符分段（code-review / doc-audit / impact-assessment / lessons-learned）
def role_like(word: str) -> bool:
    if "-" not in word:
        return False
    return all(part.isidentifier() and part.islower() and part.isalpha() for part in word.split("-"))


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


def _str_const(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _iter_str(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            yield from _iter_str(elt)


def _num_const(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    return None


class Detector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def _add(self, rule: str, node: ast.AST, detail: str) -> None:
        self.findings.append({"rule": rule, "line": getattr(node, "lineno", 0), "detail": detail})

    # R1 / R3：政策常量赋值
    def visit_Assign(self, node: ast.Assign) -> None:
        if _is_exempted_local(node.value):
            self.generic_visit(node)
            return
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        for name in names:
            upper = name.upper()
            strings = [s for s in _iter_str(node.value)]
            roles = sorted({s for s in strings if role_like(s)})
            if roles and any(h in upper for h in POLICY_NAME_HINTS):
                self._add("R1", node, f"{name} = 角色集合{roles}（政策须来自 spec frontmatter/fanout.json）")
            elif len(roles) >= 2:
                self._add("R1", node, f"{name} 内含多个角色名字面量{roles}（疑似写死角色集合）")
            paths = [s for s in strings if len(s) > 1 and path_like(s)]
            if len(paths) >= 2 and any(h in upper for h in PATH_NAME_HINTS):
                self._add("R3", node, f"{name} = 路径清单{paths}（覆盖路径须来自 agents/policy.json::lint_paths）")
            num = _num_const(node.value)
            if num is not None and any(h in upper for h in POLICY_NAME_HINTS) and "VERSION" not in upper:
                self._add("R1", node, f"{name} = {num:g}（阈值须来自 agents/policy.json）")
        self.generic_visit(node)

    # R2：成员判定字面量 —— `x in {"code-review"}` / `x not in ("doc-audit",)`
    def visit_Compare(self, node: ast.Compare) -> None:
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            if not isinstance(op, (ast.In, ast.NotIn)):
                continue
            members = sorted({s for s in _iter_str(comparator) if role_like(s)})
            if members:
                self._add("R2", node,
                          f"成员判定使用角色名字面量{members}（角色集合须来自 spec frontmatter 的 scope_required）")
        self.generic_visit(node)


# ------------------------------------------------------------------ 豁免加载

def load_exemptions(path: Path | None = None) -> dict:
    path = path or EXEMPTIONS_PATH
    if not path.is_file():
        return {"roles": [], "paths": [], "numbers": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("roles", "paths", "numbers"):
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


def scan_file(path: Path, exemptions: dict) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [{"rule": "SYNTAX", "line": exc.lineno or 0, "detail": f"解析失败：{exc.msg}"}]

    detector = Detector()
    detector.visit(tree)
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name

    allowed_names: set[str] = set()
    fn_ranges: list[tuple[int, int]] = []
    for item in exemptions.get("roles", []) + exemptions.get("paths", []) + exemptions.get("numbers", []):
        if item.get("file") != rel:
            continue
        allowed_names |= {str(n) for n in (item.get("names") or [])}
        fn_ranges += _fn_ranges(tree, {str(f) for f in (item.get("functions") or [])})

    kept: list[dict] = []
    for finding in detector.findings:
        if finding["line"] in {ln for start, end in fn_ranges for ln in range(start, end + 1)}:
            continue
        if any(f"'{name}'" in finding["detail"] or f"={name} " in finding["detail"]
               for name in allowed_names):
            continue
        finding["file"] = rel
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



def scan(dirs: list[Path]) -> list[dict]:
    exemptions = load_exemptions()
    findings: list[dict] = []
    for base in dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name == SELF_NAME or "__pycache__" in path.parts:
                continue
            if any(part in {".venv", "node_modules"} for part in path.parts):
                continue
            findings += scan_file(path, exemptions)
    return findings


# ------------------------------------------------------------------ 反向对照

INJECTIONS = {
    "roles_set.py": '_ROLES = {"code-review"}\n',
    "member_literal.py": 'def f(role):\n    return role in ("doc-audit",)\n',
    "paths_list.py": '_SCAN_PATHS = ["verify", "scripts"]\n',
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
