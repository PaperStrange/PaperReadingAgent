"""TG-14④：**卡索引 lint**（offline，纳入套件）——把"一卡一文档"从约定变成可判定不等式。

背景：卡片正文此前全塞在 `phases/<阶段>/backlog.MD` 的表格单元格里（实测单格最大 7.9 KB），
同一事实被抄进 backlog / Sprint §3/§7/§9 / 路线图多处，Sprint-16 内实测 5 波、11+ 处漂移。
TG-14 的解法是"**一卡一文件 + backlog 退化为瘦索引**"，而这类拓扑约束**必须有机检**，
否则下一次编辑又会把正文塞回索引里（本 Sprint 已实测 3 次结构性事故，全靠自检才拦住）。

判据（`--strict` 时 ①~⑤ 全开；**默认档自 2026-09-25（A3/N7）起 = strict**）：
  ① **一一对应**：每个阶段的 `backlog.MD` 索引行 ↔ `cards/<卡号>.md` 双向一致
     （索引有而文件缺 = 孤儿行；文件有而索引缺 = 孤儿文件；卡号重复 = FAIL）；
  ② **卡号 ↔ 文件名一致**：`cards/TG-1.md` 里的 `card:` 字段必须等于 `TG-1`；
  ③ **卡文件必备节**：`状态` / `规模` / `来源` / `Sprint` 四节存在（正文与证据可选）；
  ④ **Sprint 文档不得复制卡正文**：**全文行级指纹比对**——Sprint 文档中任何**非表格行**若
     **整行落在**某张卡的正文段落里（行长 ≥ `min_line_chars`、段落长 ≥ `min_fingerprint_chars`，
     两阈值在 `agents/policy.json::card_index`）即 FAIL。这是"只按卡号引用、不复制正文"的可执行形态；
     ⚠️ 首版只比"卡正文**前 60 字**"是否作为子串出现 → **在副本前填充 ≥61 字符即可规避**（N7），
     现改为整段包含关系：填充/加引号/插字都会打断包含关系，规避路径被堵。
  ⑤ **表格结构**：索引与卡文件里的 Markdown 表格列数一致（复用 `verify_md_tables.py` 的判据）。

反向对照（TG-6 ⑤"倒过来试"，fixture 段全自动）：删一份卡文件 / 改一处状态 / 往 Sprint 文档塞卡正文
（含 **≥61 字符填充**样本）/ 卡文件名与 `card:` 不符 → 各自必须 FAIL；合规 fixture 必须 PASS。

用法：
    .venv\\Scripts\\python.exe verify\\verify_card_index.py                 # 默认档：真数据 strict 判据 + fixture 反向对照
    .venv\\Scripts\\python.exe verify\\verify_card_index.py --check         # 真数据（同上；保留的等价写法）
    .venv\\Scripts\\python.exe verify\\verify_card_index.py --check --strict # 显式全判据
    .venv\\Scripts\\python.exe verify\\verify_card_index.py --selftest      # 只跑 fixture 反向对照（不校验真数据）
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-14④ 卡索引 lint：索引↔卡文件一一对应 / 卡号↔文件名一致 / 必备节 / Sprint 不得复制卡正文 / 表格结构；含 5 条反向对照自检', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 5, 'routes': [], 'requires': ['none']}

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.verify_md_tables import split_row  # noqa: E402  （同一套未转义管道切分口径）
from verify.agent_policy import load_policy  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PHASES = ROOT / "docs" / "iteration" / "phases"
SPRINT_DIR = ROOT / "docs" / "iteration" / "sprint"

# 判据参数一律来自政策数据（不得写死在本文件——实测被 verify_no_policy_hardcode.py 判为 R1）
_CARD_INDEX = load_policy().card_index
REQUIRED_SECTIONS: tuple[str, ...] = tuple(str(s) for s in _CARD_INDEX["required_sections"])
MIN_FINGERPRINT_CHARS: int = int(_CARD_INDEX["min_fingerprint_chars"])
MIN_LINE_CHARS: int = int(_CARD_INDEX["min_line_chars"])
PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def warn(name: str, detail: str = "") -> None:
    print(f"WARN: {name} {detail}")


def is_card_id(text: str) -> bool:
    """卡号判定（与 `scripts/card-inventory.py` 同口径；口径变更必须两处同改——两处不一致会被
    本 lint 的"索引↔文件一一对应"直接暴露，这正是它存在的意义）。"""
    if "-" in text:
        prefix, _, body = text.partition("-")
        if text.count("-") != 1 or not prefix.isalpha() or not prefix.isascii():
            return False
        return bool(body) and f"{prefix}_{body}".isidentifier() and body[0].isalnum()
    head = text.rstrip("0123456789")
    return bool(head) and len(head) < len(text) and head.isalpha() and head.isascii()


def index_cards(backlog: Path) -> list[str]:
    """backlog 瘦索引里的卡号序列（保序，含重复）。"""
    out: list[str] = []
    for line in backlog.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = split_row(line)
        if cells and is_card_id(cells[0]):
            out.append(cells[0])
    return out


def card_file_sections(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.M)]


def rel(path: Path, root: Path) -> str:
    """安全的相对路径显示（fixture 在临时目录、不在仓库内时回落到绝对路径）。

    首版直接用 `path.relative_to(ROOT)` → 在 `--selftest` 的临时 fixture 上抛
    `ValueError: ... is not in the subpath of ...`，把整条自检打挂。**路径显示不该让闸门崩**。
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)


def check_phase(phase_dir: Path, strict: bool, root: Path | None = None) -> list[str]:
    root = root or ROOT
    problems: list[str] = []
    backlog = phase_dir / "backlog.MD"
    cards_dir = phase_dir / "cards"
    if not backlog.is_file():
        return [f"{phase_dir.name}: 缺 backlog.MD"]

    idx = index_cards(backlog)
    dupes = sorted({c for c in idx if idx.count(c) > 1})
    if dupes:
        problems.append(f"{phase_dir.name}: 索引内卡号重复 {dupes}")

    files: dict[str, Path] = {}
    if cards_dir.is_dir():
        for f in sorted(cards_dir.glob("*.md")):
            files[f.stem] = f

    # ① 双向一一对应
    for card in sorted(set(idx) - set(files)):
        problems.append(f"{phase_dir.name}: 索引有 {card} 但缺 cards/{card}.md（孤儿索引行）")
    for card in sorted(set(files) - set(idx)):
        problems.append(f"{phase_dir.name}: cards/{card}.md 存在但索引未登记（孤儿文件）")

    # ②③ 卡文件自身
    for card, path in sorted(files.items()):
        text = path.read_text(encoding="utf-8", errors="replace")
        # ⚠️ 局部变量**不要叫 `m`**：本模块有模块级常量 `MIN_FINGERPRINT_CHARS`，
        # 首版用 `m = re.search(...)` 把它就地覆盖成 `re.Match` → 后面比较时抛 `TypeError`，
        # 而 `run()` 未捕获异常、自检把"没拿到 problems"当成"没问题" ⇒ **反向对照 D 假绿**。
        card_match = re.search(r"^\s*[-*]?\s*`?card`?\s*[:：]\s*`?([^`\s]+)`?\s*$", text, re.M)
        if not card_match:
            problems.append(f"{rel(path, root)}: 缺 `card:` 字段（卡号↔文件名一致性的判据）")
        elif card_match.group(1).strip() != card:
            problems.append(f"{rel(path, root)}: `card: {card_match.group(1)}` 与文件名 {card} 不一致")
        if strict:
            sections = card_file_sections(text)
            missing = [s for s in REQUIRED_SECTIONS if not any(s in sec for sec in sections)]
            if missing:
                problems.append(f"{rel(path, root)}: 缺必备节 {missing}（实测节名：{sections}）")

    # ④ Sprint 文档不得复制卡正文
    #    A3（finding N7，2026-09-25）**收紧为全文行级指纹比对**：首版取卡正文**前 N 字**当指纹、
    #    在 Sprint 文档里找该子串 —— 只要在副本前填充 ≥N+1 个字符，指纹就不再连续出现，
    #    判据**静默放行**（填充规避）。现在改为**整段**参与比对（不再截断成前 N 字）：
    #      * `line in para`：该行整行是卡正文的一段（**≥61 字符填充样本**就是这一形态——
    #        填充只是加了一行，被复制的那一行仍然整行落在卡正文里）；
    #      * `para in line`：卡正文的**整段**被原样嵌进更长的行（首版"前 N 字子串"的合法收紧版：
    #        指纹由 N 字延长到**整段**，填充/插字都会打断包含关系）。
    #    **合法的计划表行天然仍被放行**：它是表格行（被下面 `startswith("|")` 排除），且首格是卡号。
    if strict and files:
        sprint_dir = root / "docs" / "iteration" / "sprint"
        bodies: list[tuple[str, str]] = []
        for card, path in files.items():
            text = path.read_text(encoding="utf-8", errors="replace")
            # **按段落**抽正文块（首版两个 bug：按行抽 → 短句达不到阈值；正则写成 `.*$([\s\S]*?)`
            # → 捕获组从行尾开始，永远抽不到内容。现为 `.*\n([\s\S]*?)`，并以段落为单位）。
            for para_match in re.finditer(r"^##[^\n]*\n([\s\S]*?)(?=^##|\Z)", text, re.M):
                para = "".join(
                    ln.strip() for ln in para_match.group(1).splitlines()
                    if ln.strip() and not ln.strip().startswith("|")
                )
                if len(para) >= MIN_FINGERPRINT_CHARS:
                    bodies.append((card, para))
        for sprint in sorted(
            [*sprint_dir.glob("*.md"), *sprint_dir.glob("*.MD")]  # ⚠️ 两种扩展名都要（实测该目录 23 个小写 + 23 个大写）
        ) if sprint_dir.is_dir() else []:
            stext = sprint.read_text(encoding="utf-8", errors="replace")
            for i, sline in enumerate(stext.splitlines()):
                line = sline.strip()
                # 表格行不是"正文段落"（引用/索引天然出现在表格里）→ 不参与 ④
                if len(line) < MIN_LINE_CHARS or line.startswith("|"):
                    continue
                for card, para in bodies:
                    if line in para or para in line:
                        problems.append(
                            f"{rel(sprint, root)}:{i + 1}: 该行与卡片 {card} 的正文段落整段重合"
                            f"（行长 {len(line)} / 段落长 {len(para)}）"
                            f"——Sprint 文档只按卡号引用，不复制正文（判据 ④：全文行级指纹比对）")
                        break
    return problems


def run(strict: bool = True, root: Path | None = None) -> list[str]:
    """跑全部阶段（`strict=True` 是**默认档**——见 `main()` 的说明）。

    **单个阶段内的异常不得吞掉**（首版实测：check_phase 抛 TypeError 时
    自检把"没拿到 problems"当成"没问题" → 反向对照 D 假绿）。异常一律转成 problem 文本，
    让闸门对"自己坏了"与"数据坏了"都给非零退出。"""
    root = root or ROOT
    phases = sorted(p for p in (root / "docs" / "iteration" / "phases").glob("*") if p.is_dir()) \
        if root != ROOT else sorted(p for p in PHASES.glob("*") if p.is_dir())
    problems: list[str] = []
    for phase_dir in phases:
        if not (phase_dir / "backlog.MD").is_file():
            continue
        try:
            problems += check_phase(phase_dir, strict, root)
        except Exception as exc:  # noqa: BLE001 —— 闸门自身异常必须显式失败，不能静默
            problems.append(f"{phase_dir.name}: 检查过程异常（{type(exc).__name__}: {exc}）"
                            f"——闸门自身出错也必须 FAIL，不得当作通过")
    return problems


# ------------------------------------------------------------------ 自检 fixture

def _fixture(base: Path) -> Path:
    """造一个最小的合规结构（1 阶段 2 卡），供反向对照逐条破坏。

    ⚠️ 本函数**只重建阶段目录，不动 `docs/iteration/sprint/`**——首版每次都重建 sprint 目录，
    于是"重置 fixture"会把反向对照 D 刚写进去的 Sprint 文档删掉（实测：`sprint 内容: []`），
    导致 D 永远不触发。fixture 自身的这种"重置副作用"是反向对照最容易骗过自己的地方。

    正文刻意长于 `MIN_FINGERPRINT_CHARS`（首版 22 字 < 25 → 指纹不成立，D 同样漏报）。
    """
    sprint_dir = base / "docs" / "iteration" / "sprint"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    phase = base / "docs" / "iteration" / "phases" / "demo"
    cards = phase / "cards"
    if cards.is_dir():
        for old in cards.glob("*.md"):
            old.unlink()
    cards.mkdir(parents=True, exist_ok=True)
    (phase / "backlog.MD").write_text(
        "# demo backlog\n\n| 卡号 | 一句话 | 状态 | Sprint | 文件 |\n|---|---|---|---|---|\n"
        "| D-1 | 第一张卡 | 完成 | Sprint-1 | [cards/D-1.md](cards/D-1.md) |\n"
        "| D-2 | 第二张卡 | 候选 | Sprint-2 | [cards/D-2.md](cards/D-2.md) |\n", encoding="utf-8")
    for card, title in (("D-1", "第一张卡"), ("D-2", "第二张卡")):
        (cards / f"{card}.md").write_text(
            f"# {card} {title}\n\n- `card`: {card}\n- 索引: [../backlog.MD](../backlog.MD)\n\n"
            f"## 状态\n已完成并在 Sprint-1 关闭。\n\n## 规模\n1 点。\n\n## 来源\n用户插入。\n\n"
            f"## Sprint\nSprint-1。\n\n## 正文\n{card} 的正文内容写在这里，它应当只存在于本卡文件之中，"
            f"任何 Sprint 文档都不应复制这段文字。\n\n## 证据\n见 Sprint-1 §7。\n",
            encoding="utf-8")
    return phase


def selfcheck(check_real: bool = True) -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _fixture(base)
        ok("自检 ① 合规 fixture → PASS", run(True, base) == [], "problems=[]")

        # 反向对照 A：删一份卡文件
        (base / "docs/iteration/phases/demo/cards/D-2.md").unlink()
        p = run(True, base)
        ok("反向对照 A 删卡文件 → FAIL（孤儿索引行）",
           any("孤儿索引行" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 B：卡号与文件名不符
        (base / "docs/iteration/phases/demo/cards/D-2.md").write_text(
            "# D-9\n\n- `card`: D-9\n\n## 状态\nx\n\n## 规模\n1\n\n## 来源\ny\n\n## Sprint\nSprint-2\n",
            encoding="utf-8")
        p = run(True, base)
        ok("反向对照 B 卡号↔文件名不符 → FAIL",
           any("与文件名" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 C：缺必备节
        (base / "docs/iteration/phases/demo/cards/D-1.md").write_text(
            "# D-1\n\n- `card`: D-1\n\n## 正文\n只有正文。\n", encoding="utf-8")
        p = run(True, base)
        ok("反向对照 C 缺必备节 → FAIL（strict 档）", any("缺必备节" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 D：Sprint 文档塞入卡正文（**非计划表行**——普通段落里复制正文）
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").write_text(
            "# Sprint-1\n\n## 3. 看板\n\n说明文字里嵌了卡片正文：D-1 的正文内容写在这里，"
            "它应当只存在于本卡文件之中，任何 Sprint 文档都不应复制这段文字。\n",
            encoding="utf-8")
        p = run(True, base)
        ok("反向对照 D Sprint 文档出现卡正文 → FAIL",
           any("整段重合" in x for x in p), f"problems={p[:1]}")

        # 反向对照 D3：**≥61 字符填充规避**必须被判 FAIL（finding N7 的原始样本）。
        # 首版只比"卡正文前 60 字"是否出现 → 在副本**前面**填 61+ 字符即可让指纹不连续 ⇒ 静默放行。
        # 现按"整行落在卡正文段落里"判：填充不改变"这一行仍是卡正文的一段"这个事实。
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").write_text(
            "# Sprint-1\n\n## 3. 看板\n\n" + ("填" * 61) + "\n\n"
            "D-1 的正文内容写在这里，它应当只存在于本卡文件之中，任何 Sprint 文档都不应复制这段文字。\n",
            encoding="utf-8")
        p = run(True, base)
        ok("反向对照 D3 ≥61 字符填充规避 → FAIL（N7 回归样本）",
           any("整段重合" in x for x in p), f"problems={p[:1]}")

        # 反向对照 D2：**合法计划表行**必须放行（防"把正常计划表判成违规"——
        # 首版就是这个假阳性逼出一次对已关闭 Sprint 文档的历史改写，已 revert）
        _fixture(base)  # 重建阶段 fixture（D 用例前已把 D-2 卡删掉）
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").write_text(
            "# Sprint-1\n\n## 2. 计划\n\n| 卡号 | 主题 | 点 |\n|---|---|---|\n"
            "| D-1 | D-1 的正文内容写在这里，它应当只存在于本卡文件之中，任何 Sprint 文档都不应复制这段文字。 | 1 |\n",
            encoding="utf-8")
        p = run(True, base)
        ok("反向对照 D2 合法计划表行（首格=卡号，正文位于单元格开头）→ PASS",
           not any("整段重合" in x for x in p), f"problems={p[:1]}")
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").unlink(missing_ok=True)

        # 反向对照 E：孤儿卡文件（有文件无索引行）
        (base / "docs/iteration/phases/demo/cards/D-3.md").write_text(
            "# D-3\n\n- `card`: D-3\n\n## 状态\nx\n\n## 规模\n1\n\n## 来源\ny\n\n## Sprint\nz\n",
            encoding="utf-8")
        p = run(True, base)
        ok("反向对照 E 孤儿卡文件 → FAIL", any("孤儿文件" in x for x in p), f"problems={p[:1]}")

    # 真数据：**A3 起按默认档（strict）判**——由 `main()` 调用（`--selftest` 可显式跳过）。
    # 原因（finding N7/M-e）：迁移已宣称完成，而套件以**无参**调用本脚本；首版在这里只 WARN
    # ⇒ "SUITE PASSED" 并不能证明卡索引一致（实测同一份坏数据：`--check` rc=1 而套件模式 rc=0+WARN）。
    # **闸门自己给自己发警告 = 放行**；且真数据判据**只允许跑一次**（同一事实两处判会分叉）。
    if not check_real:
        ok("真数据判据由 main() 以默认档执行", True, "（本函数只跑 fixture 自检）")
        print(f"\nALL PASS ({PASSED} assertions)")
        return 0
    real = run(True)
    if real:
        print(f"FAIL: 真数据未通过默认档（{len(real)} 项）：")
        for p in real[:40]:
            print(f"  - {p}")
        if len(real) > 40:
            print(f"  … 另有 {len(real) - 40} 项")
        print("提示：迁移已完成 ⇒ 默认档与 `--check --strict` 同判；不得靠降档换绿。")
        return 1
    ok("真数据（默认档 = strict）通过", True, "索引↔卡文件一一对应 / 必备节 / 正文分离")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    """CLI 入口。

    **默认档（无参数）＝ real-data 全判据 → 再跑 fixture 反向对照**（A3/N7/M-e）。
    `--check` / `--strict` 保持既有语义（真数据 + 严格判据）；`--selftest` 显式跳过真数据、
    只跑 fixture 反向对照（阈值/自检调试用）。
    为什么默认档必须判真数据：套件（`run_suite.py`）以**无参**调用本脚本，默认档若只做 fixture
    自检，"SUITE PASSED" 就与真数据无关——这正是 N7 实测的失效形态（同一坏数据 rc=0+WARN）。
    """
    if "--selftest" in sys.argv:
        # 显式调试档：**只跑 fixture**（真数据判据由默认档/--check 负责，不重复判两处）
        return selfcheck(check_real=False)
    problems = run(strict="--strict" in sys.argv or "--check" not in sys.argv)
    if problems:
        print(f"CARD-INDEX FAIL（{len(problems)} 项）：")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  … 另有 {len(problems) - 40} 项")
        return 1
    print("CARD-INDEX PASS：索引↔卡文件一一对应（含必备节与正文分离）")
    # 真数据过了 → 再跑 fixture 反向对照（断言自检与真数据判据**同源**，不是两套口径）
    return selfcheck(check_real=False)


if __name__ == "__main__":
    raise SystemExit(main())
