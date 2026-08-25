from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/src/paperqa")


@dataclass
class Counts:
    total: int = 0
    top_level: int = 0
    class_methods: int = 0
    nested_functions: int = 0
    async_functions: int = 0

    def add(self, other: "Counts") -> None:
        self.total += other.total
        self.top_level += other.top_level
        self.class_methods += other.class_methods
        self.nested_functions += other.nested_functions
        self.async_functions += other.async_functions


@dataclass
class FunctionItem:
    file: str
    name: str
    lineno: int
    kind: str  # top_level | class_method | nested
    is_async: bool
    qualname: str


def _is_func(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))


def count_in_tree(tree: ast.AST, file_rel: str) -> tuple[Counts, list[FunctionItem]]:
    counts = Counts()
    items: list[FunctionItem] = []

    def visit(
        node: ast.AST,
        in_class: bool = False,
        in_function: bool = False,
        stack: list[str] | None = None,
    ) -> None:
        if stack is None:
            stack = []
        for child in ast.iter_child_nodes(node):
            if _is_func(child):
                counts.total += 1
                is_async = isinstance(child, ast.AsyncFunctionDef)
                if is_async:
                    counts.async_functions += 1
                if in_function:
                    counts.nested_functions += 1
                    kind = "nested"
                elif in_class:
                    counts.class_methods += 1
                    kind = "class_method"
                else:
                    counts.top_level += 1
                    kind = "top_level"
                qualname = ".".join([*stack, child.name]) if stack else child.name
                items.append(
                    FunctionItem(
                        file=file_rel,
                        name=child.name,
                        lineno=child.lineno,
                        kind=kind,
                        is_async=is_async,
                        qualname=qualname,
                    )
                )
                visit(
                    child,
                    in_class=False,
                    in_function=True,
                    stack=[*stack, child.name],
                )
            elif isinstance(child, ast.ClassDef):
                visit(
                    child,
                    in_class=True,
                    in_function=False,
                    stack=[*stack, child.name],
                )
            else:
                visit(child, in_class=in_class, in_function=in_function, stack=stack)

    visit(tree)
    return counts, items


def main() -> None:
    if not ROOT.exists():
        raise FileNotFoundError(f"Path does not exist: {ROOT}")

    grand = Counts()
    file_counts: list[tuple[Path, Counts]] = []
    all_items: list[FunctionItem] = []

    for py_file in sorted(ROOT.rglob("*.py")):
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_file))
        rel = py_file.relative_to(ROOT).as_posix()
        c, items = count_in_tree(tree, rel)
        file_counts.append((py_file, c))
        grand.add(c)
        all_items.extend(items)

    print(f"Scanned files: {len(file_counts)}")
    print(f"Total functions: {grand.total}")
    print(f"Top-level functions: {grand.top_level}")
    print(f"Class methods: {grand.class_methods}")
    print(f"Nested functions: {grand.nested_functions}")
    print(f"Async functions: {grand.async_functions}")
    print("")
    print("Per-file totals (desc):")
    for path, c in sorted(file_counts, key=lambda x: x[1].total, reverse=True):
        if c.total == 0:
            continue
        rel = path.relative_to(ROOT)
        print(
            f"{rel}: total={c.total}, top_level={c.top_level}, "
            f"methods={c.class_methods}, nested={c.nested_functions}, async={c.async_functions}"
        )

    out_json = Path(
        "/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa-script/paperqa_function_inventory.json"
    )
    out_json.write_text(
        json.dumps([item.__dict__ for item in all_items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("")
    print(f"Wrote function inventory: {out_json}")


if __name__ == "__main__":
    main()
