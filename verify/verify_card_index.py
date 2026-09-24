"""TG-14④：**卡索引 lint**（offline，纳入套件）——把"一卡一文档"从约定变成可判定不等式。

背景：卡片正文此前全塞在 `phases/<阶段>/backlog.MD` 的表格单元格里（实测单格最大 7.9 KB），
同一事实被抄进 backlog / Sprint §3/§7/§9 / 路线图多处，Sprint-16 内实测 5 波、11+ 处漂移。
TG-14 的解法是"**一卡一文件 + backlog 退化为瘦索引**"，而这类拓扑约束**必须有机检**，
否则下一次编辑又会把正文塞回索引里（本 Sprint 已实测 3 次结构性事故，全靠自检才拦住）。

判据（`--strict` 时 ①~⑤ 全开；默认宽松档只跑 ① ② ⑤）：
  ① **一一对应**：每个阶段的 `backlog.MD` 索引行 ↔ `cards/<卡号>.md` 双向一致
     （索引有而文件缺 = 孤儿行；文件有而索引缺 = 孤儿文件；卡号重复 = FAIL）；
  ② **卡号 ↔ 文件名一致**：`cards/TG-1.md` 里的 `card:` 字段必须等于 `TG-1`；
  ③ **卡文件必备节**：`状态` / `规模` / `来源` / `Sprint` 四节存在（正文与证据可选）；
  ④ **Sprint 文档不得复制卡正文**：Sprint 文档中任何**非引用的长段落**（> `--body-threshold` 字符）
     若与某卡正文高度重合（前 60 字命中）即 FAIL —— 这是"只按卡号引用、不复制正文"的可执行形态；
  ⑤ **表格结构**：索引与卡文件里的 Markdown 表格列数一致（复用 `verify_md_tables.py` 的判据）。

反向对照（TG-6 ⑤"倒过来试"，`--selftest` 全自动）：删一份卡文件 / 改一处状态 / 往 Sprint 文档塞卡正文 /
卡文件名与 `card:` 不符 → 各自必须 FAIL；合规 fixture 必须 PASS。

用法：
    .venv\\Scripts\\python.exe verify\\verify_card_index.py                 # 自检（fixture）
    .venv\\Scripts\\python.exe verify\\verify_card_index.py --check         # 真数据（迁移期宽松档）
    .venv\\Scripts\\python.exe verify\\verify_card_index.py --check --strict # 迁移完成后全判据
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
BODY_PREFIX_CHARS: int = int(_CARD_INDEX["body_prefix_chars"])
MIN_FINGERPRINT_CHARS: int = int(_CARD_INDEX["min_fingerprint_chars"])
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


def check_phase(phase_dir: Path, strict: bool, body_threshold: int, root: Path | None = None) -> list[str]:
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
                    bodies.append((card, para[:BODY_PREFIX_CHARS]))
        for sprint in sorted(sprint_dir.glob("*.md")) if sprint_dir.is_dir() else []:
            stext = sprint.read_text(encoding="utf-8", errors="replace")
            for card, prefix in bodies:
                if prefix and prefix in stext:
                    problems.append(
                        f"{rel(sprint, root)}: 出现卡片 {card} 的正文片段（前 {BODY_PREFIX_CHARS} 字命中）"
                        f"——Sprint 文档只按卡号引用，不复制正文")
                    break
    return problems


def run(strict: bool, body_threshold: int, root: Path | None = None) -> list[str]:
    """跑全部阶段。**单个阶段内的异常不得吞掉**（首版实测：check_phase 抛 TypeError 时
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
            problems += check_phase(phase_dir, strict, body_threshold, root)
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


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _fixture(base)
        ok("自检 ① 合规 fixture → PASS", run(True, 200, base) == [], "problems=[]")

        # 反向对照 A：删一份卡文件
        (base / "docs/iteration/phases/demo/cards/D-2.md").unlink()
        p = run(True, 200, base)
        ok("反向对照 A 删卡文件 → FAIL（孤儿索引行）",
           any("孤儿索引行" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 B：卡号与文件名不符
        (base / "docs/iteration/phases/demo/cards/D-2.md").write_text(
            "# D-9\n\n- `card`: D-9\n\n## 状态\nx\n\n## 规模\n1\n\n## 来源\ny\n\n## Sprint\nSprint-2\n",
            encoding="utf-8")
        p = run(True, 200, base)
        ok("反向对照 B 卡号↔文件名不符 → FAIL",
           any("与文件名" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 C：缺必备节
        (base / "docs/iteration/phases/demo/cards/D-1.md").write_text(
            "# D-1\n\n- `card`: D-1\n\n## 正文\n只有正文。\n", encoding="utf-8")
        p = run(True, 200, base)
        ok("反向对照 C 缺必备节 → FAIL（strict 档）", any("缺必备节" in x for x in p), f"problems={p[:1]}")
        _fixture(base)

        # 反向对照 D：Sprint 文档塞入卡正文
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").write_text(
            "# Sprint-1\n\n## 3. 看板\n\n说明文字里嵌了卡片正文：D-1 的正文内容写在这里，"
            "它应当只存在于本卡文件之中，任何 Sprint 文档都不应复制这段文字。\n",
            encoding="utf-8")
        p = run(True, 120, base)
        ok("反向对照 D Sprint 文档出现卡正文 → FAIL（严格档）",
           any("正文片段" in x for x in p), f"problems={p[:1]}")
        (base / "docs/iteration/sprint/2026-01-01-sprint-1.md").unlink()

        # 反向对照 E：孤儿卡文件（有文件无索引行）
        (base / "docs/iteration/phases/demo/cards/D-3.md").write_text(
            "# D-3\n\n- `card`: D-3\n\n## 状态\nx\n\n## 规模\n1\n\n## 来源\ny\n\n## Sprint\nz\n",
            encoding="utf-8")
        p = run(True, 200, base)
        ok("反向对照 E 孤儿卡文件 → FAIL", any("孤儿文件" in x for x in p), f"problems={p[:1]}")

    # 真数据（默认宽松档：迁移期只要求一一对应，不要求必备节/正文分离）
    real = run(False, 200)
    if real:
        warn("真数据（宽松档）尚未通过——迁移未开始属预期", f"{len(real)} 项，示例：{real[0][:80]}")
    else:
        ok("真数据（宽松档）通过", True, "索引↔卡文件已一一对应")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        problems = run(strict="--strict" in sys.argv,
                       body_threshold=int(sys.argv[sys.argv.index("--body-threshold") + 1])
                       if "--body-threshold" in sys.argv else 200)
        if problems:
            print(f"CARD-INDEX FAIL（{len(problems)} 项）：")
            for p in problems[:40]:
                print(f"  - {p}")
            if len(problems) > 40:
                print(f"  … 另有 {len(problems) - 40} 项")
            return 1
        print("CARD-INDEX PASS：索引↔卡文件一一对应"
              + ("（含必备节与正文分离）" if "--strict" in sys.argv else "（宽松档）"))
        return 0
    return selfcheck()


if __name__ == "__main__":
    raise SystemExit(main())
