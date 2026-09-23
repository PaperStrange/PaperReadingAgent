#!/usr/bin/env python3
"""TG-15 一次性数据迁移：给角色 spec 补 frontmatter 声明字段（幂等）。

为什么用脚本而不是手工编辑 7 个文件：`agents/functions/*.md` 的 frontmatter 是**政策数据**
（`verify/agent_policy.py` 的 `scope_required` / `coverage_window` 来源），逐个手改容易漏、
且无法证明"改全了"。本脚本按固定表改，`--check` 模式可在 CI/复核时验证已改全。

改动内容（每个 spec 的 frontmatter，顶层字段）：
  scope_required    true  = 该角色产出**评审结论** → 其 run 必须有 scope 声明（C1 不变式）
                    false = scope 不在该角色语义里（如范围评估本身、环境核验）
  coverage_window   self  = 该 run 覆盖 (coverage_anchor, covers_through] 区间（参与 C3）
                    none  = 不参与 C3 覆盖计算（非审查类 run）
  version           补丁位 +1（数据声明变更，行为不变）
  metadata.tags     追加 tg15-scope / tg15-coverage 便于检索

用法：
    python scripts/migrate-scope-declarations.py            # 应用
    python scripts/migrate-scope-declarations.py --check    # 只校验（不改盘）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = REPO_ROOT / "agents" / "functions"

# (role, scope_required, coverage_window, 理由)
TABLE: list[tuple[str, bool, str, str]] = [
    ("code-review", True, "self",
     "产出评审结论（findings）；C1 要求 scope 声明，C3 要求其 (anchor, covers_through] 可归属"),
    ("doc-audit", True, "self",
     "产出评审结论（文档 findings）；同上"),
    ("impact-assessment", False, "self",
     "scope 的**来源本身**（C2 的指涉对象），不要求自证 scope；但其探测窗口仍参与 C3"),
    ("lessons-learned", False, "self",
     "产出经验条目而非评审结论，scope 不在其语义内；窗口仍参与 C3"),
    ("tech-research", False, "none",
     "调研 run 不产出评审结论、也不作为三查覆盖窗口（M16 研究级归档另有 verify_archive 守）"),
    ("workspace-check", False, "none",
     "由主代理执行、**不产生账本 run**（fanout.json: executor=main-agent），故无覆盖窗口"),
    ("_template-agent", False, "none",
     "模板文件（下划线前缀，非真实角色）；显式声明以免封闭世界自检把它当缺口"),
    ("agent-onboarding-review", True, "self",
     "对单个 agent/spec 做审查并产出结论 → 与 code-review 同族，必须有 scope 声明（C1）"),
]


def split_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    return text[3:end], text[end:]


def bump_patch(version: str) -> str:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not m:
        return version
    return f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"


def patch(role: str, scope_required: bool, coverage_window: str) -> tuple[str, str]:
    path = SPEC_DIR / f"{role}.md"
    if not path.is_file():
        return role, f"MISSING: {path}"
    text = path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        return role, "FAIL: 缺 frontmatter"
    fm, rest = parts

    lines = fm.split("\n")
    out: list[str] = []
    seen_version = False
    for line in lines:
        m = re.match(r"^version:\s*(.+?)\s*$", line)
        if m:
            seen_version = True
            old = m.group(1).strip().strip('"')
            out.append(f'version: "{bump_patch(old)}"')
            continue
        out.append(line)
    if not seen_version:
        return role, "FAIL: frontmatter 无 version"

    # 顶层声明字段：插在 version 行之后（YAML 顶层，必须在 metadata: 之前）
    insert_at = next(i for i, ln in enumerate(out) if ln.startswith("version:")) + 1
    decl = []
    if not any(ln.startswith("scope_required:") for ln in out):
        decl.append(f"scope_required: {'true' if scope_required else 'false'}")
    if not any(ln.startswith("coverage_window:") for ln in out):
        decl.append(f"coverage_window: {coverage_window}")
    out[insert_at:insert_at] = decl

    new_text = "---" + "\n".join(out) + rest
    if new_text == text:
        return role, "noop（已声明）"
    path.write_text(new_text, encoding="utf-8")
    return role, f"patched（scope_required={scope_required}, coverage_window={coverage_window}）"


def verify() -> list[str]:
    problems: list[str] = []
    for role, scope_required, coverage_window, _ in TABLE:
        path = SPEC_DIR / f"{role}.md"
        if not path.is_file():
            problems.append(f"{role}: 文件不存在")
            continue
        text = path.read_text(encoding="utf-8")
        parts = split_frontmatter(text)
        if parts is None:
            problems.append(f"{role}: 缺 frontmatter")
            continue
        fm = parts[0]
        want = f"scope_required: {'true' if scope_required else 'false'}"
        if want not in fm:
            problems.append(f"{role}: 缺 {want!r}")
        if f"coverage_window: {coverage_window}" not in fm:
            problems.append(f"{role}: 缺 coverage_window: {coverage_window}")
    # 反向：任何 spec 文件都必须被本表覆盖（新 spec 不补声明 → 这里报错）
    table_roles = {r for r, *_ in TABLE}
    for path in sorted(SPEC_DIR.glob("*.md")):
        if path.stem not in table_roles:
            problems.append(f"{path.name}: 不在迁移表内（新增 spec 必须显式声明 scope_required/coverage_window）")
    return problems


def main() -> int:
    check = "--check" in sys.argv
    if check:
        problems = verify()
        for p in problems:
            print(f"FAIL: {p}")
        if problems:
            print(f"\nSCOPE-DECLARATION-CHECK FAIL（{len(problems)} 项）")
            return 1
        print(f"SCOPE-DECLARATION-CHECK PASS（{len(TABLE)} 个 spec 均已声明）")
        return 0

    for role, scope_required, coverage_window, reason in TABLE:
        name, status = patch(role, scope_required, coverage_window)
        print(f"{name:20s} {status}   # {reason[:60]}")
    problems = verify()
    if problems:
        print("\n迁移后仍有问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"\n迁移完成（{len(TABLE)} 个 spec）。复核：python scripts/migrate-scope-declarations.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
