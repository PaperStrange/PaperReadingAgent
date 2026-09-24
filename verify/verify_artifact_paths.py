"""TG-9：**新脚本产物目录约定**闸门（offline）——"写盘路径必须落在已忽略目录或 `%TEMP%`"。

**为什么需要这个闸门**（TG-9 卡内证据）：本轮出现过两次**误入库**——`verify_checkpoint_run.log`
与 `ci_fail_log.txt`（脚本把日志写到仓库根，`git status` 里直接多出未跟踪文件，被误提交）。
当时的补救是"发现一个补一条 `.gitignore`"，而 `agents/runtime/` 更是**逐条列名**：
新增脚本往这个目录写新文件时**默认不被忽略**（实测 `git check-ignore agents/runtime/probe.json`
rc=1）⇒ "约定"只写在卡文里，代码里没有任何东西守它。本闸门把约定变成**可执行判据**。

**判据**（唯一真源 = `agents/policy.json::artifact_paths`，本文件不另写一份路径清单）：

    ① **写盘目标必须落在已忽略目录或 `%TEMP%`**：扫描政策声明的扫描集，用 AST 找出**写盘调用**
       （`open(...,"w")`、`write_text`/`write_bytes`、`mkdir`/`makedirs`、`os.replace`、`shutil.copy*`、
       `savefig`/`to_csv`、`.mjs` 里的截图/写文件字面量……），把目标表达式**严格分解**成
       `(基座, 字面量路径段)`：基座 ∈ {仓库根、`tempfile`/`%TEMP%`}，名字按赋值链解析
       （`RUNTIME_DIR = AGENTS_BASE / "runtime"` 这类链要能还原）、`os.environ.get(K, 默认值)` 取
       **默认落点**（"新脚本产物**默认**写哪里"正是本卡要守的东西）。分解成功 → 该路径必须被
       `.gitignore` 真正忽略（`git check-ignore --no-index`），或是政策里显式登记的**已入库数据文件**；
       分解不出来的目标（路径来自函数参数/argv）**不算通过**，计入下面的棘轮。
    ② **忽略根双向差集**（政策 ↔ `.gitignore` ↔ 代码）：
       正向 = 政策 `ignored_roots` 每条都必须**真被忽略**（对合成探针路径 `check-ignore` 命中）
       **且**在 `.gitignore` 里有对应行——拼错一个字母（`agents/run/`）就是**死配置**，必须 FAIL
       （否则"已声明忽略"只是自我声明，代码会照写不误）；
       反向 = 每条声明根都必须**确有代码在用**（按写盘目标的字面量段判定，含分解失败的动态目标），
       且每个"已被忽略的落点"都要能归到某条声明根上——声明与真实落点必须互相解释，
       否则要么漏声明（写了没人管的地方），要么死声明（声明了没人用的地方）。
    ③ **动态目标棘轮**：分解不出的目标按**文件**设上限（2026-09-25 实测值，只许下调）；**未列入
       上限表的文件出现动态目标 = FAIL**（新脚本必须让产物落点可静态判定）；`review_by` 到期即 FAIL。
    ④ **反向对照（"倒过来试"，TG-6 ⑤）**：`--emit-fixture` 生成两类新脚本样本到 `%TEMP%`，
       再用 `--scan-root` 判定——**写到仓库根 → rc=1 且点名该路径**；**写到默认落点
       `agents/runtime/` → rc=0**；并**实跑**默认落点样本，断言产生"产物"后
       `git status --porcelain -- <产物>` **为空**（忽略覆盖真的生效），随后删除探针（不留痕）。

**与既有闸门的分工**：`verify_no_policy_hardcode.py` 守"政策不许写进代码"（本闸门的路径清单全部
来自政策数据，故不触发 R3）；本闸门守"**产物的落点**"；`verify_lint.py` 守代码风格，互不重叠。

**能抓什么 / 抓不到什么（诚实标注）**：能抓"字面量可还原的落点"（含模块级常量链、`os.environ.get`
默认值、`.mjs` 截图名），能抓"新脚本把产物写到仓库根/未忽略目录"；**抓不到**完全由调用方传入的
路径（`f(p)` 里的 `p`）与运行时才确定的路径——这类不静默放行，而是计入③的棘轮（按文件计数）。
另一处边界：**绝对路径**字面量若指向仓库外（实测 4 处 `paper-qa-script/*.py` 里遗留的 macOS
`/Volumes/...` 路径），它不产生仓库内产物、也不属本卡判据，故只 **WARN 点名**（属移植缺陷，另案）；
若绝对路径落在**仓库内**则照常判 FAIL（会先化归成仓库相对路径）。

**模式**：

    .venv\\Scripts\\python.exe verify\\verify_artifact_paths.py
        # 默认：真实仓库审计 + 内置自检（含注入样本反向对照；样本一律写 %TEMP%）
    .venv\\Scripts\\python.exe verify\\verify_artifact_paths.py --report
        # 只打印"动态目标"按文件分布（维护棘轮上限表用），不做判定
    .venv\\Scripts\\python.exe verify\\verify_artifact_paths.py --scan-root <dir>
        # 只判定指定目录下的脚本（注入样本用；跳过覆盖/棘轮判定）
    .venv\\Scripts\\python.exe verify\\verify_artifact_paths.py --emit-fixture <kind> --scan-root <dir>
        # 生成反向对照样本：dirty（写到仓库根）/ clean（写到默认落点 agents/runtime/）

退出码：0=通过；1=检出违规（逐条点名）；2=政策/数据缺失（fail-closed，不静默放行）。
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-9 产物目录约定闸门：脚本源码的写盘目标必须落在已忽略目录或 %TEMP%（政策 artifact_paths 驱动）+ 忽略根双向差集（须真被 .gitignore 忽略、确有其行、确有代码在用）+ 动态目标棘轮（新文件必须可静态判定）+ 反向对照（注入写仓库根 → rc=1 点名；默认落点实测 git status 干净）', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 10, 'routes': [], 'requires': ['git']}

import argparse
import ast
import fnmatch
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import PolicyError, load_policy  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0
PROBE_STEM = "tg9-landing-probe"
PROJECT_TZ = timezone(timedelta(hours=8))  # 与账本/闸门的时间口径一致（UTC+8）

# 写盘 sink 的**词表**（工具自身知识：哪些调用会落盘；不是政策——政策是"落点必须已忽略"）。
_FILE_METHODS = {"write_text", "write_bytes", "savefig", "to_csv", "to_json", "to_excel",
                 "writeFileSync", "writeFile"}
_FOLDER_METHODS = {"mkdir", "touch"}
_QUALIFIED_SINKS = {
    "os.makedirs": ((0,), "folder"), "os.mkdir": ((0,), "folder"), "os.rmdir": ((0,), "folder"),
    "os.remove": ((0,), "file"), "os.unlink": ((0,), "file"),
    # 复制/改名类**只判目标侧**（第 1 个参数）：源是**读**，把"读仓库里的数据文件"判成"往仓库写"是假红
    # （实测：`shutil.copy2(SRC_PDF, tmp_pdf)` 的 `SRC_PDF = ROOT/"data"/"pdf"/…` 曾被误判为违规）。
    "os.rename": ((1,), "file"), "os.replace": ((1,), "file"),
    "shutil.copyfile": ((1,), "file"), "shutil.copy": ((1,), "file"),
    "shutil.copy2": ((1,), "file"), "shutil.copytree": ((1,), "folder"),
    "shutil.move": ((1,), "file"), "shutil.rmtree": ((0,), "folder"),
    "zipfile.ZipFile": ((0,), "file"),
}
_ENV_LOOKUP = {"get", "getenv"}
_DROP_ATTRS = {"parent", "parents"}
_BARE_CONSTS = {"ROOT", "REPO_ROOT", "PROJECT_ROOT", "_ROOT", "__file__"}
_ABS_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]{1,2}[^\\/])")
MJS_ARTIFACT_RE = re.compile(r"[\"']([^\"'\r\n]*\.(?:png|log|json|txt|csv))[\"']", re.IGNORECASE)


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def _exempted_local(value):
    """本函数内造 fixture 数据（反向对照样本的脚本体），不是闸门政策。

    理由就地写在这里：`verify_no_policy_hardcode.py` 识别该调用名并放行这一处赋值；
    样本里的路径字符串是**被检查对象**，不是本闸门的政策数据。
    """
    return value


# ------------------------------------------------------------------ 政策数据

def artifacts_policy() -> dict:
    """`agents/policy.json::artifact_paths`（fail-closed：缺键/类型错 → PolicyError 退出码 2）。

    为什么必须数据化：忽略根清单若写死在本文件里，就等于"闸门自己声明自己正确"——
    新增落点要改代码、`.gitignore` 与代码会各自漂移（这正是 TG-9 事故的形态）。
    """
    data = load_policy().policy_file.get("artifact_paths")
    if not isinstance(data, dict):
        raise PolicyError("agents/policy.json 缺 artifact_paths（产物落点的唯一真源）")
    for key, typ in (("scan_globs", list), ("ignored_roots", list), ("tracked_targets", dict),
                     ("temp", dict), ("dynamic_ratchet", dict), ("ignore_file", str)):
        if key not in data or not isinstance(data[key], typ) or isinstance(data[key], bool):
            raise PolicyError(f"artifact_paths.{key} 缺失或类型非法：{data.get(key)!r}")
    if not data["scan_globs"] or not data["ignored_roots"]:
        raise PolicyError("artifact_paths.scan_globs / ignored_roots 不得为空（空表 = 闸门空转）")
    for key in ("module", "calls", "env_names", "literals"):
        if not data["temp"].get(key):
            raise PolicyError(f"artifact_paths.temp.{key} 不得为空（临时落点判定要有可核写法）")
    for path, reason in data["tracked_targets"].items():
        if str(path).startswith("_"):
            continue
        if not str(reason).strip():
            raise PolicyError(f"artifact_paths.tracked_targets[{path!r}] 缺 reason"
                              f"（已入库数据文件的例外必须写清为什么）")
    ratchet = data["dynamic_ratchet"]
    for key in ("cutoff_local_date", "review_by", "files"):
        if key not in ratchet:
            raise PolicyError(f"artifact_paths.dynamic_ratchet.{key} 缺失")
    for path, cap in ratchet["files"].items():
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
            raise PolicyError(f"artifact_paths.dynamic_ratchet.files[{path!r}] 必须是 ≥0 整数，"
                              f"实际 {cap!r}——上限写错会让棘轮静默失效")
    return data


# ------------------------------------------------------------------ 目标路径分解

class TargetResolver:
    """把写盘目标表达式**严格**分解成 `(基座, 字面量路径段)`。

    严格 = 任何无法解释的节点（函数参数、`sys.argv`、f-string 插值、未解析的调用）直接放弃
    （返回 `None`）——宁可把它算进"动态目标棘轮"，也不猜一个路径（猜错会让闸门报假红或**假绿**）。
    基座五种：`repo`（仓库根，来自 `Path(__file__)...parent` / `ROOT` 之类常量）、
    `temp`（`tempfile.*` / `%TEMP%` / `TEMP|TMP|TMPDIR`）、`rel`（纯相对字面量，按仓库相对处理）、
    `none`（`os.environ.get(K, "")`：默认值空串 = 显式不落盘）、`outside`（绝对路径且不在仓库内）。
    """

    def __init__(self, tree: ast.AST, data: dict) -> None:
        self.temp_calls = {str(c) for c in data["temp"]["calls"]}
        self.temp_names = {str(n) for n in data["temp"]["env_names"]}
        self.temp_literals = {str(x) for x in data["temp"]["literals"]}
        self.temp_module = str(data["temp"]["module"])
        self.values: dict[str, list[ast.AST]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.values.setdefault(target.id, []).append(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
                self.values.setdefault(node.target.id, []).append(node.value)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if isinstance(item.optional_vars, ast.Name):
                        self.values.setdefault(item.optional_vars.id, []).append(item.context_expr)

    @staticmethod
    def attr_of(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def temp_base(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in self.temp_names:
            return True
        if isinstance(node, ast.Constant) and node.value in self.temp_literals:
            return True
        if isinstance(node, ast.Call):
            if self.attr_of(node.func) in self.temp_calls:
                return True
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == self.temp_module and node.func.attr in self.temp_calls:
                return True
        return False

    def _absolute(self, value: str) -> tuple[str, list[str]]:
        """绝对路径字面量：**在仓库内**则化归仓库相对（照判），**在仓库外**单列 `outside`（见模块头边界说明）。"""
        if not _ABS_RE.match(value):
            return ("rel", [value])
        try:
            rel = Path(value).resolve().relative_to(ROOT.resolve())
            return ("repo", [rel.as_posix()])
        except (OSError, ValueError):
            return ("outside", [value])

    def _env_default(self, node: ast.Call) -> tuple[str, list[str]] | None:
        """`os.environ.get("K", 默认值)`：默认值 = 脚本产物的**默认落点**（本卡要守的东西）。

        只认**环境变量查表**形态（`os.environ.get` / `os.getenv`）——`dict.get(k, v)` 的默认值
        不是路径，误当成路径会制造假红/假绿。默认值是**空串**时表示"缺省不落盘"
        （实测 `e2e_common._report_metrics`：`os.environ.get("PAPERQA_SUITE_METRICS", "")` + `if not path: return`
        ——把它判成"写仓库根"是假红），单列 `none`。
        """
        if not node.args:
            return None
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
        is_environ = (isinstance(receiver, ast.Attribute) and receiver.attr == "environ") \
            or (isinstance(receiver, ast.Name) and receiver.id in {"os", "environ"}) \
            or (self.attr_of(node.func) == "getenv")
        if not is_environ or len(node.args) < 2:
            return None
        default = node.args[1]
        if isinstance(default, ast.Constant) and default.value == "":
            return ("none", [])
        return self.decompose(default, 1)

    def decompose(self, node: ast.AST, depth: int = 0) -> tuple[str, list[str]] | None:
        if depth > 12:
            return None
        if self.temp_base(node):
            return ("temp", [])
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in self.temp_literals:
                return ("temp", [])
            return self._absolute(node.value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            left = self.decompose(node.left, depth + 1)
            right = self.decompose(node.right, depth + 1)
            if left is None or right is None:
                return None
            if left[0] == "temp" or right[0] == "temp":
                return ("temp", [])
            if left[0] == "none" or right[0] == "none":
                return ("none", [])
            if left[0] == "outside" or right[0] == "outside":
                return ("outside", left[1] or right[1])
            base = "repo" if "repo" in (left[0], right[0]) else "rel"
            if isinstance(node.op, ast.Add) and left[1] and right[1]:
                # 字符串拼接（`PROBE_STEM + ".json"`）不是一个新路径段，要并进最后一段
                return (base, left[1][:-1] + [left[1][-1] + right[1][0]] + right[1][1:])
            return (base, left[1] + right[1])
        if isinstance(node, ast.Name):
            if node.id in _BARE_CONSTS:
                return ("repo", [])
            return self._from_name(node.id, depth)
        if isinstance(node, ast.Attribute):
            if node.attr in _DROP_ATTRS:
                base = self.decompose(node.value, depth + 1)
                if base is None or node.attr == "parents":
                    return None  # parents[N]：下标参与定位 → 动态
                if base[0] == "temp":
                    return base
                if not base[1]:
                    return ("repo", []) if base[0] == "repo" else None
                return (base[0], base[1][:-1])
            if self.temp_base(node):
                return ("temp", [])
            return None
        if isinstance(node, ast.Call):
            name = self.attr_of(node.func)
            if self.temp_base(node):
                return ("temp", [])
            if name in {"Path", "str", "fspath", "resolve", "absolute", "expanduser"}:
                if not node.args:
                    return None
                return self.decompose(node.args[0], depth + 1)
            if name == "join":
                base, parts = "rel", []
                for arg in node.args:
                    got = self.decompose(arg, depth + 1)
                    if got is None:
                        return None
                    if got[0] == "temp":
                        return ("temp", [])
                    if got[0] == "repo":
                        base = "repo"
                    parts += got[1]
                return (base, parts)
            if name == "with_name" and isinstance(node.func, ast.Attribute):
                base = self.decompose(node.func.value, depth + 1)
                if base is None or not node.args or not base[1]:
                    return None
                got = self.decompose(node.args[0], depth + 1)
                if got is None or got[0] == "temp" or len(got[1]) != 1:
                    return None
                return (base[0], base[1][:-1] + got[1])
            if name in _ENV_LOOKUP:
                return self._env_default(node)
            return None
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                else:
                    return None  # 插值 → 动态
            return ("rel", parts)
        return None

    def _from_name(self, name: str, depth: int) -> tuple[str, list[str]] | None:
        rhs = self.values.get(name)
        if not rhs:
            return None
        outs = [self.decompose(expr, depth + 1) for expr in rhs]
        if any(out is None for out in outs):
            return None
        first = outs[0]
        if any(out != first for out in outs[1:]):
            return None  # 同名多处赋值且不一致 → 不猜
        return first

    def loose_parts(self, node: ast.AST, depth: int = 0) -> list[str]:
        """**宽松**收集字面量段（只用于"这条声明根有没有代码在用"，不用于判违规）。

        分解失败的目标（如 `RUNS_DIR / run_id / "x.md"`）也要能证明"代码确实往 `agents/runs/` 写"，
        否则 `agents/runs/` 会被误判成死配置。
        """
        if depth > 10:
            return []
        if self.temp_base(node):
            return []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [] if node.value in self.temp_literals else [node.value]
        if isinstance(node, ast.BinOp):
            left = self.loose_parts(node.left, depth + 1)
            right = self.loose_parts(node.right, depth + 1)
            if isinstance(node.op, ast.Add) and left and right:
                return left[:-1] + [left[-1] + right[0]] + right[1:]
            return left + right
        if isinstance(node, ast.Name):
            return [p for rhs in self.values.get(node.id, []) for p in self.loose_parts(rhs, depth + 1)]
        if isinstance(node, ast.Attribute):
            if node.attr in _DROP_ATTRS:
                base = self.loose_parts(node.value, depth + 1)
                return base[:-1] if base else base
            return [p for rhs in self.values.get(node.attr, []) for p in self.loose_parts(rhs, depth + 1)]
        if isinstance(node, ast.Call):
            name = self.attr_of(node.func)
            args = list(node.args)
            if name in {"get", "getenv"} and args:
                args = args[1:]  # 环境变量名不是路径段
            if name == "with_name" and isinstance(node.func, ast.Attribute):
                base = self.loose_parts(node.func.value, depth + 1)
                tail = self.loose_parts(node.args[0], depth + 1) if node.args else []
                return (base[:-1] + tail) if base else tail
            return [p for arg in args for p in self.loose_parts(arg, depth + 1)]
        if isinstance(node, ast.JoinedStr):
            return [value.value for value in node.values
                    if isinstance(value, ast.Constant) and isinstance(value.value, str)]
        return []


# ------------------------------------------------------------------ 写盘调用收集

def _is_write_mode(mode: object) -> bool:
    return isinstance(mode, str) and any(ch in mode for ch in "wax+")


def _mode_of(node: ast.Call) -> object:
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def write_targets(tree: ast.AST) -> list[tuple[int, str, ast.AST, str]]:
    """收集 `(行号, 调用名, 目标表达式, 'file'|'folder')`。"""
    out: list[tuple[int, str, ast.AST, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = TargetResolver.attr_of(func)
        qualified = (f"{func.value.id}.{func.attr}"
                     if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else None)
        if qualified in _QUALIFIED_SINKS:
            indexes, kind = _QUALIFIED_SINKS[qualified]
            if qualified == "zipfile.ZipFile" and not _is_write_mode(_mode_of(node)):
                continue
            for index in indexes:
                if len(node.args) > index:
                    out.append((node.lineno, qualified, node.args[index], kind))
            continue
        if isinstance(func, ast.Attribute) and name in _FILE_METHODS:
            out.append((node.lineno, name, func.value, "file"))
            continue
        if isinstance(func, ast.Attribute) and name in _FOLDER_METHODS:
            out.append((node.lineno, name, func.value, "folder"))
            continue
        if name != "open":
            continue
        if isinstance(func, ast.Attribute):
            if node.args and _is_write_mode(_mode_of(node)):
                out.append((node.lineno, "open", func.value, "file"))
        elif node.args and _is_write_mode(_mode_of(node)):
            out.append((node.lineno, "open", node.args[0], "file"))
    return out


# ------------------------------------------------------------------ git 判定

def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def ignored(path: str) -> bool:
    """`path`（仓库相对）是否被 `.gitignore` 忽略。

    `--no-index`：**已入库**文件也照规则判定（`agents/runtime/prices.json` 走 `!` 白名单后
    必须报"未忽略"，否则"白名单"这件事无法被核）。
    """
    if not path:
        return False
    return git("check-ignore", "--no-index", "-q", path).returncode == 0


def tracked_files() -> set[str]:
    return {line.strip().replace("\\", "/") for line in git("ls-files").stdout.splitlines() if line.strip()}


def ignore_file_lines(data: dict) -> list[str]:
    """读**.gitignore**（路径来自政策 `artifact_paths.ignore_file`，不写死在代码里）。"""
    rel = str(data["ignore_file"])
    path = ROOT / rel
    if not path.is_file():
        raise PolicyError(f"{rel} 不存在（忽略覆盖是 TG-9 的判据基础）")
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def normalize(parts: list[str]) -> str:
    return "/".join(p.strip("/") for p in parts if p.strip("/"))


def covered_by_roots(candidate: str, roots: list[str]) -> str | None:
    """`candidate` 归到哪条声明根（返回该根；没有 = 漏声明）。"""
    for raw in roots:
        root = str(raw).strip()
        if not root or not candidate:
            continue
        if root.endswith("/*"):
            # 目录级忽略的写法（`agents/runtime/*`）：目录本身与其下任意深度都算覆盖
            base = root[:-2]
            if candidate == base or candidate.startswith(base + "/"):
                return root
        elif "*" in root or "?" in root:
            if fnmatch.fnmatch(candidate, root):
                return root
        elif root.endswith("/"):
            base = root.rstrip("/")
            if candidate == base or candidate.startswith(base + "/"):
                return root
        elif candidate == root or candidate.startswith(root + "/"):
            return root
    return None


def target_bad(candidate: str, *, is_folder: bool) -> bool:
    if not candidate:
        return True  # 空 = 直接写仓库根
    if is_folder:
        return not (ignored(candidate + "/") or ignored(candidate + "/" + PROBE_STEM + ".tmp"))
    return not ignored(candidate)


# ------------------------------------------------------------------ 审计

class Finding:
    def __init__(self, rel: str, line: int, call: str, detail: str) -> None:
        self.rel, self.line, self.call, self.detail = rel, line, call, detail

    def __str__(self) -> str:
        return f"{self.rel}:{self.line} [{self.call}] {self.detail}"


def scan_files(globs: list[str]) -> list[Path]:
    """扫描集 = 政策 `scan_globs` 的展开（每条 glob 命中 0 个文件 → 由 `coverage_problems()` 点名）。

    **本脚本自身也在扫描集内**（不自我豁免）：闸门自己也要满足"产物落点已忽略"的约定
    ——它的动态目标同样受棘轮约束（`dynamic_ratchet.files` 里有它一行）。
    """
    out: set[Path] = set()
    for pattern in globs:
        for path in ROOT.glob(str(pattern)):
            if not path.is_file() or path.suffix not in {".py", ".mjs"}:
                continue
            if "__pycache__" in path.parts:
                continue
            out.add(path)
    return sorted(out)


def scan_root_files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*")
                  if p.is_file() and p.suffix in {".py", ".mjs"} and "__pycache__" not in p.parts)


def audit(files: list[Path], data: dict, *, strict: bool) -> tuple[list[Finding], dict]:
    roots = [str(r) for r in data["ignored_roots"]]
    tracked = {str(k): str(v) for k, v in data["tracked_targets"].items() if not str(k).startswith("_")}
    inside = tracked_files()
    bad: list[Finding] = []
    dynamic: dict[str, list[str]] = {}
    used_roots: set[str] = set()
    tracked_seen: set[str] = set()
    undeclared: set[str] = set()
    outside: set[str] = set()
    stats = {"sinks": 0, "ignored": 0, "temp": 0, "tracked": 0, "files": 0, "none": 0, "outside": 0}
    for path in files:
        stats["files"] += 1
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".mjs":
            if not path.is_relative_to(ROOT):
                continue  # 仓库外样本：产物落在它自己旁边，与仓库落点无关
            prefix = path.parent.relative_to(ROOT).as_posix()
            for line_no, line in enumerate(text.splitlines(), start=1):
                for match in MJS_ARTIFACT_RE.finditer(line):
                    candidate = normalize([prefix, match.group(1)])
                    stats["sinks"] += 1
                    if ignored(candidate):
                        stats["ignored"] += 1
                        hit = covered_by_roots(candidate, roots)
                        used_roots.add(hit) if hit else undeclared.add(candidate)
                    else:
                        bad.append(Finding(rel, line_no, "screenshot/write",
                                           f"产物 {candidate!r} 未被 .gitignore 忽略"
                                           f"（截图/日志须落已忽略路径，例如 verify/*.png、verify/*.log）"))
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            bad.append(Finding(rel, exc.lineno or 0, "parse", f"语法错误：{exc.msg}"))
            continue
        resolver = TargetResolver(tree, data)
        for line_no, call, target, kind in write_targets(tree):
            stats["sinks"] += 1
            loose = normalize(resolver.loose_parts(target))
            hit = covered_by_roots(loose, roots) if loose else None
            if hit:
                used_roots.add(hit)
            got = resolver.decompose(target)
            if got is None:
                dynamic.setdefault(rel, []).append(f"{line_no} {call}({ast.unparse(target)[:60]})")
                continue
            base, parts = got
            if base == "temp":
                stats["temp"] += 1
                continue
            if base == "none":
                stats["none"] += 1  # 默认值 = 空串（显式"不落盘"）→ 不是落点
                continue
            if base == "outside":
                stats["outside"] += 1
                outside.add(f"{rel}:{line_no} {call} → {parts[0][:70] if parts else '?'}")
                continue
            candidate = normalize(parts)
            if candidate in tracked:
                if candidate not in inside:
                    bad.append(Finding(rel, line_no, call,
                                       f"{candidate!r} 被登记为 tracked_targets 但 **git 未跟踪它**"
                                       f"（政策说它是入库数据文件，其实是运行态产物）"))
                stats["tracked"] += 1
                tracked_seen.add(candidate)
                continue
            if not target_bad(candidate, is_folder=(kind == "folder")):
                stats["ignored"] += 1
                covered = covered_by_roots(candidate, roots)
                used_roots.add(covered) if covered else undeclared.add(candidate)
                continue
            hint = "目录" if kind == "folder" else "文件"
            bad.append(Finding(rel, line_no, call,
                               f"写盘{hint} {candidate or '<仓库根>'!r} **未被 .gitignore 忽略**"
                               f"——新脚本产物须落 `agents/runtime/`、`verify/*.log|png` 等已忽略路径"
                               f"或 %TEMP%（政策 artifact_paths.ignored_roots）"))
        # **弱证据**：模块级/局部路径常量（不一定是写盘目标，如 `SERVER_LOG = ROOT/"verify"/"x.log"`）
        # 也说明"这个落点在本仓库里真被用"——只用于"声明根是否死配置"的判定，**不产生违规**。
        for exprs in resolver.values.values():
            for expr in exprs:
                got = resolver.decompose(expr)
                if got and got[0] in {"repo", "rel"}:
                    hit = covered_by_roots(normalize(got[1]), roots)
                    if hit:
                        used_roots.add(hit)
    if strict:
        unused = [str(r).strip() for r in roots if str(r).strip() and str(r).strip() not in used_roots]
        for path, reason in tracked.items():
            if path not in tracked_seen:
                bad.append(Finding(str(data["ignore_file"]), 0, "dead-tracked-target",
                                   f"tracked_targets 登记了 {path!r}（理由：{reason}）但扫描集里没有脚本"
                                   f"写它 = **死配置**（删掉它）"))
        for candidate in sorted(undeclared):
            bad.append(Finding(str(data["ignore_file"]), 0, "undeclared-root",
                               f"写盘目标 {candidate!r} 虽然已被忽略，但**政策没声明**这个落点"
                               f"（政策与真实落点必须互相解释：补进 ignored_roots，或改写到已声明落点）"))
    else:
        unused = []
    return bad, {"dynamic": dynamic, "used_roots": used_roots, "stats": stats, "outside": outside,
                 "undeclared": undeclared, "unused_roots": unused}


def coverage_problems(data: dict) -> list[str]:
    """政策 ↔ `.gitignore` ↔ 文件系统**双向差集**（① 每条根真被忽略；② 忽略文件里确有其行；③ 无死 glob）。"""
    problems: list[str] = []
    ignore_rel = str(data["ignore_file"])
    lines = {ln.rstrip("/") for ln in ignore_file_lines(data)}
    for raw in data["ignored_roots"]:
        root = str(raw).strip()
        if not root:
            problems.append("[忽略根] 政策里出现空条目（空声明 = 闸门空转）")
            continue
        if "*" in root or "?" in root:
            probe = root.replace("*", PROBE_STEM).replace("?", PROBE_STEM)
        elif root.endswith("/"):
            probe = root + PROBE_STEM + ".tmp"
        else:
            probe = root
        if not ignored(probe):
            problems.append(f"[忽略根失效] 政策声明 {root!r}，但合成探针 {probe!r} **没被 {ignore_rel} 忽略**"
                            f"（拼错/规则被删 → 声明形同虚设，代码会照写不误）")
        if root not in lines and root.rstrip("/") not in lines:
            problems.append(f"[忽略根无据] 政策声明 {root!r}，但 {ignore_rel} 里找不到对应行"
                            f"（政策与忽略文件必须互相解释：要么补 .gitignore，要么删声明）")
    for pattern in data["scan_globs"]:
        if not any(p.is_file() for p in ROOT.glob(str(pattern))):
            problems.append(f"[死 glob] artifact_paths.scan_globs 的 {pattern!r} 命中 0 个文件"
                            f"（留着它 = 让人以为扫了、其实没扫）")
    return problems


def ratchet_problems(dynamic: dict[str, list[str]], data: dict, *, today: str) -> tuple[list[str], list[str]]:
    """动态目标棘轮：**按文件设上限**（只许下调）；未列入上限表的文件出现动态目标 → FAIL。

    返回 `(fail, info)`：`fail` = 判失败的问题（超上限 / 新文件有动态目标 / 到期未重评）；
    `info` = "上限可收紧"的提示（实测低于上限时提醒下调——**不判失败**，与
    `md_table_legacy_files` 的棘轮同口径：`len(found) > cap → FAIL`，低于上限只是提示，
    这样"顺手把动态目标改少"的重构不会被闸门惩罚）。
    """
    ratchet = data["dynamic_ratchet"]
    caps = {str(k): int(v) for k, v in ratchet["files"].items()}
    fail: list[str] = []
    info: list[str] = []
    for rel, items in sorted(dynamic.items()):
        if rel not in caps:
            fail.append(f"[动态目标] {rel} 有 {len(items)} 处写盘目标无法静态判定"
                        f"（例：{items[0]}）——**新脚本必须让产物落点可静态判定**"
                        f"（用模块级常量拼路径，别把落点交给参数/argv）")
        elif len(items) > caps[rel]:
            fail.append(f"[棘轮] {rel} 动态写盘目标 {len(items)} 处 > 上限 {caps[rel]}"
                        f"（上限只许下调；新增落点请改成可静态判定的常量）")
        elif len(items) < caps[rel]:
            info.append(f"[棘轮可收紧] {rel} 动态写盘目标已降到 {len(items)} 处（上限 {caps[rel]}）"
                        f"——顺手把上限下调到实测值")
    for rel, cap in sorted(caps.items()):
        if rel not in dynamic:
            if cap:
                info.append(f"[棘轮可收紧] {rel} 已无动态写盘目标（上限 {cap}）——请把该条删掉/置 0")
            else:
                info.append(f"[棘轮条目] {rel} 上限 0 且当前确无动态目标（保留 = 该文件不得再引入动态落点）")
    if str(ratchet["review_by"]) < today:
        fail.append(f"[棘轮到期] dynamic_ratchet.review_by={ratchet['review_by']} 已过（今天 {today}）"
                    f"——没有到期日的豁免就是永久豁免，须重评基线")
    return fail, info


# ------------------------------------------------------------------ 反向对照样本

def fixture_body(kind: str) -> str:
    """两类新脚本样本：`dirty` 写到仓库根（必须 FAIL）、`clean` 写默认落点（必须 PASS）。"""
    head = ('"""新脚本样本（TG-9 反向对照）。"""\n'
            "from pathlib import Path\n\n"
            "ROOT = Path(__file__).resolve().parent.parent\n")
    if kind == "dirty":
        body = head + '\nout = ROOT / "tg9-injected-artifact.json"\n' \
                      'out.write_text("{}\\n", encoding="utf-8")\n'
    elif kind == "clean":
        body = head + '\nout = ROOT / "agents" / "runtime" / "tg9-landing-probe.json"\n' \
                      'out.write_text("{}\\n", encoding="utf-8")\n'
    else:
        raise SystemExit(f"未知样本类型：{kind}（合法：dirty / clean）")
    return _exempted_local(body)


def emit_fixture(kind: str, scan_root: Path) -> int:
    scan_root.mkdir(parents=True, exist_ok=True)
    target = scan_root / "tg9_new_script.py"
    target.write_text(fixture_body(kind), encoding="utf-8", newline="\n")
    print(f"EMIT OK: {kind} → {target}")
    return 0


def run_self(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ 自检（反向对照）

def selfcheck(data: dict) -> None:
    ok("自检⓪ 政策数据封闭世界（无死键/无未声明 spec）",
       load_policy().closure_problems() == [], "problems=[]")

    problems = coverage_problems(data)
    ok(f"① 忽略根双向差集：{len(data['ignored_roots'])} 条声明根都被 {data['ignore_file']} 真正忽略、且确有其行",
       problems == [], "clean" if not problems else str(problems[:3]))

    with tempfile.TemporaryDirectory(prefix="tg9-rc-") as td:
        tmp = Path(td)
        dirty, clean = tmp / "dirty", tmp / "clean"
        emit_fixture("dirty", dirty)
        emit_fixture("clean", clean)
        probe_dirty = run_self("--scan-root", str(dirty))
        probe_clean = run_self("--scan-root", str(clean))
    ok("② 反向对照：注入**写到仓库根**的新脚本 → rc=1 且点名该未忽略路径（TG-9 事故形态）",
       probe_dirty.returncode == 1 and "tg9-injected-artifact.json" in probe_dirty.stdout
       and "tg9_new_script.py" in probe_dirty.stdout,
       f"rc={probe_dirty.returncode} out={probe_dirty.stdout.strip().splitlines()[-2:]}")
    ok("③ 反向对照：新脚本写**默认落点** `agents/runtime/` → rc=0（不制造假红）",
       probe_clean.returncode == 0, f"rc={probe_clean.returncode} out={probe_clean.stdout.strip()[:60]}")

    landing = ROOT / "agents" / "runtime" / (PROBE_STEM + ".json")
    rel = landing.relative_to(ROOT).as_posix()
    landing.parent.mkdir(parents=True, exist_ok=True)
    try:
        landing.write_text("{}\n", encoding="utf-8")
        porcelain = git("status", "--porcelain", "--untracked-files=all", "--", rel).stdout.strip()
        shown = git("status", "--porcelain", "--ignored=matching", "--", rel).stdout.strip()
    finally:
        landing.unlink(missing_ok=True)
    ok(f"④ 默认落点实测：产物写入 `{rel}` 后 `git status --porcelain -- <该路径>` **为空**",
       porcelain == "", f"porcelain={porcelain!r}（非空 = 产物污染 git status，TG-9 的原始事故形态）")
    ok("⑤ 同一条路径在 `--ignored=matching` 下**可见**（证明④不是「路径不存在」造成的假绿）",
       rel in shown, f"ignored-view={shown!r}")
    left = git("status", "--porcelain", "--untracked-files=all").stdout.strip()
    ok("⑥ 探针已清理：`git status --porcelain` 无残留未跟踪运行态产物（除已忽略者）",
       "tg9-landing-probe" not in left, f"status={left[:160]!r}")
    ok("⑦ 反向对照：仓库根下的假想产物判**未忽略**（判据有牙，不是恒真）",
       not ignored("tg9-injected-artifact.json"), "check-ignore rc=1")

    with tempfile.TemporaryDirectory(prefix="tg9-rc-") as td:
        empty = Path(td) / "empty"
        empty.mkdir()
        probe_empty = run_self("--scan-root", str(empty))
    ok("⑧ 空扫描目录 → rc=0 且如实打印 0 写盘目标（不因「没扫到东西」报错，也不谎报覆盖面）",
       probe_empty.returncode == 0 and "0 写盘目标" in probe_empty.stdout,
       f"rc={probe_empty.returncode} out={probe_empty.stdout.strip()[:60]}")

    with tempfile.TemporaryDirectory(prefix="tg9-rc-") as td:
        broken = Path(td) / "broken"
        broken.mkdir()
        (broken / "bad.py").write_text("def f(:\n", encoding="utf-8")
        probe_broken = run_self("--scan-root", str(broken))
    ok("⑨ 语法错误的脚本 → rc=1 并点名（不能因为解析不了就静默放行）",
       probe_broken.returncode == 1 and "语法错误" in probe_broken.stdout, f"rc={probe_broken.returncode}")


# ------------------------------------------------------------------ 主流程

def main() -> int:
    parser = argparse.ArgumentParser(description="TG-9 产物目录约定闸门")
    parser.add_argument("--scan-root", default=None,
                        help="只判定该目录下的脚本（注入样本用；跳过覆盖/棘轮判定）")
    parser.add_argument("--emit-fixture", choices=["dirty", "clean"], default=None,
                        help="生成反向对照样本（配合 --scan-root）")
    parser.add_argument("--report", action="store_true", help="只打印动态目标分布（维护棘轮上限表）")
    args = parser.parse_args()

    data = artifacts_policy()
    today = datetime.now(PROJECT_TZ).date().isoformat()

    if args.scan_root:
        scan_root = Path(args.scan_root).resolve()
        if args.emit_fixture:
            return emit_fixture(args.emit_fixture, scan_root)
        files = scan_root_files(scan_root)
        bad, info = audit(files, data, strict=False)
        stats, dynamic = info["stats"], info["dynamic"]
        print(f"扫描 {scan_root}：{stats['files']} 个脚本 / {stats['sinks']} 写盘目标"
              f"（已忽略 {stats['ignored']}、%TEMP% {stats['temp']}、已入库数据 {stats['tracked']}、"
              f"动态 {sum(len(v) for v in dynamic.values())}）")
        for item in bad:
            print(f"  - {item}")
        print(f"ARTIFACT-PATHS {'PASS' if not bad else 'FAIL'}（{len(bad)} 项）")
        return 1 if bad else 0

    files = scan_files([str(g) for g in data["scan_globs"]])
    bad, info = audit(files, data, strict=True)
    stats, dynamic = info["stats"], info["dynamic"]

    if args.report:
        print(f"扫描集：{stats['files']} 个脚本 / {stats['sinks']} 写盘目标"
              f"（已忽略 {stats['ignored']}、%TEMP% {stats['temp']}、已入库数据 {stats['tracked']}、"
              f"无默认落点 {stats['none']}、仓库外绝对路径 {stats['outside']}）")
        print(f"动态写盘目标（棘轮上限表用）：{sum(len(v) for v in dynamic.values())} 处 / "
              f"{len(dynamic)} 个文件")
        for rel, items in sorted(dynamic.items()):
            print(f'    "{rel}": {len(items)},')
        for rel, items in sorted(dynamic.items()):
            for item in items:
                print(f"   · {rel}:{item}")
        for candidate in sorted(info["undeclared"]):
            print(f"  未声明落点：{candidate}")
        for item in sorted(info["outside"]):
            print(f"  仓库外绝对路径：{item}")
        for root in info["unused_roots"]:
            print(f"  声明根当前无可静态判定写入：{root}")
        for item in bad:
            print(f"  违规：{item}")
        return 0

    print(f"扫描集（政策 artifact_paths.scan_globs）：{stats['files']} 个脚本 / {stats['sinks']} 写盘目标"
          f"（已忽略 {stats['ignored']}、%TEMP% {stats['temp']}、已入库数据 {stats['tracked']}、"
          f"无默认落点 {stats['none']}、仓库外绝对路径 {stats['outside']}、"
          f"动态 {sum(len(v) for v in dynamic.values())}）")
    ratchet_fail, ratchet_info = ratchet_problems(dynamic, data, today=today)
    problems = coverage_problems(data) + ratchet_fail
    if bad or problems:
        print(f"\nARTIFACT-PATHS FAIL（{len(bad) + len(problems)} 项）：")
        for item in bad:
            print(f"  - {item}")
        for item in problems:
            print(f"  - {item}")
        return 1
    # 非判定性的诚实标注（不 FAIL，但必须打印出来，不能"看不见"）
    for item in sorted(info["outside"]):
        print(f"WARN: 仓库外绝对路径落点（本闸门判据是「仓库内产物」，绝对路径不在判据内，"
              f"但属历史遗留的移植缺陷）：{item}")
    for root in info["unused_roots"]:
        print(f"WARN: 政策声明的落点 {root!r} 在当前扫描集里没有可静态判定的写入"
              f"（若是给新脚本预留的落点，把它写进 1-WORKFLOW §6 的约定里；若已废弃则删声明）")
    for item in ratchet_info:
        print(f"INFO: {item}")
    selfcheck(data)
    print(f"\nALL PASS ({PASSED} assertions)｜动态目标 {sum(len(v) for v in dynamic.values())} 处"
          f"（{len(dynamic)} 个文件全在棘轮表内且未超上限）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
