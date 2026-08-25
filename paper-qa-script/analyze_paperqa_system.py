from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/src/paperqa")
OUT_DIR = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa-script")


@dataclass
class FunctionRecord:
    id: str
    module: str
    file: str
    qualname: str
    name: str
    kind: str  # top_level | class_method | nested
    class_name: str | None
    is_async: bool
    lineno: int
    end_lineno: int
    signature: str
    return_annotation: str | None
    doc: str | None
    calls: list[str] = field(default_factory=list)
    resolved_calls: list[str] = field(default_factory=list)


def parse_annotation(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _format_arg(arg: ast.arg, default: ast.AST | None = None) -> str:
    ann = parse_annotation(arg.annotation)
    part = arg.arg + (f": {ann}" if ann else "")
    if default is not None:
        try:
            part += f"={ast.unparse(default)}"
        except Exception:
            part += "=..."
    return part


def format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    a = node.args
    parts: list[str] = []

    posonly = list(a.posonlyargs)
    regular = list(a.args)
    all_pos = posonly + regular
    pos_defaults = [None] * (len(all_pos) - len(a.defaults)) + list(a.defaults)

    for arg, default in zip(all_pos, pos_defaults, strict=True):
        parts.append(_format_arg(arg, default))
    if posonly:
        parts.insert(len(posonly), "/")

    if a.vararg:
        parts.append("*" + _format_arg(a.vararg))
    elif a.kwonlyargs:
        parts.append("*")

    for kwarg, default in zip(a.kwonlyargs, a.kw_defaults, strict=True):
        parts.append(_format_arg(kwarg, default))

    if a.kwarg:
        parts.append("**" + _format_arg(a.kwarg))

    ret = parse_annotation(node.returns)
    return f"({', '.join(parts)})" + (f" -> {ret}" if ret else "")


def collect_calls(node: ast.AST) -> list[str]:
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            try:
                calls.append(ast.unparse(child.func))
            except Exception:
                continue
    return calls


def extract_records(py_file: Path) -> list[FunctionRecord]:
    module = py_file.relative_to(ROOT).with_suffix("").as_posix().replace("/", ".")
    src = py_file.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(py_file))
    records: list[FunctionRecord] = []

    def visit(
        node: ast.AST,
        scope: list[str] | None = None,
        in_class: str | None = None,
        in_function: bool = False,
    ) -> None:
        if scope is None:
            scope = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "nested" if in_function else ("class_method" if in_class else "top_level")
                qual_parts = [*scope, child.name]
                qualname = ".".join(qual_parts)
                rec = FunctionRecord(
                    id=f"{module}:{qualname}",
                    module=module,
                    file=py_file.relative_to(ROOT).as_posix(),
                    qualname=qualname,
                    name=child.name,
                    kind=kind,
                    class_name=in_class,
                    is_async=isinstance(child, ast.AsyncFunctionDef),
                    lineno=child.lineno,
                    end_lineno=child.end_lineno or child.lineno,
                    signature=format_signature(child),
                    return_annotation=parse_annotation(child.returns),
                    doc=(ast.get_docstring(child) or None),
                    calls=collect_calls(child),
                )
                records.append(rec)
                visit(child, scope=qual_parts, in_class=None, in_function=True)
            elif isinstance(child, ast.ClassDef):
                visit(child, scope=[*scope, child.name], in_class=child.name, in_function=False)
            else:
                visit(child, scope=scope, in_class=in_class, in_function=in_function)

    visit(tree)
    return records


def resolve_calls(records: list[FunctionRecord]) -> None:
    by_id = {r.id: r for r in records}
    by_name: dict[str, list[str]] = {}
    by_module_top: dict[tuple[str, str], str] = {}
    by_class_method: dict[tuple[str, str], str] = {}

    for r in records:
        by_name.setdefault(r.name, []).append(r.id)
        if r.kind == "top_level":
            by_module_top[(r.module, r.name)] = r.id
        if r.class_name:
            by_class_method[(r.class_name, r.name)] = r.id

    for r in records:
        resolved: list[str] = []
        for c in r.calls:
            target_id: str | None = None
            # self.method()
            if c.startswith("self."):
                meth = c.split(".", 1)[1].split("(", 1)[0]
                if r.class_name and (r.class_name, meth) in by_class_method:
                    target_id = by_class_method[(r.class_name, meth)]
            # direct function call name(...)
            elif "." not in c:
                name = c.split("(", 1)[0]
                if (r.module, name) in by_module_top:
                    target_id = by_module_top[(r.module, name)]
                elif len(by_name.get(name, [])) == 1:
                    target_id = by_name[name][0]
            if target_id and target_id in by_id:
                resolved.append(target_id)
        r.resolved_calls = sorted(set(resolved))


def build_flow_paths(records: list[FunctionRecord], entry_ids: list[str], max_depth: int = 4) -> dict[str, list[list[str]]]:
    graph = {r.id: r.resolved_calls for r in records}
    paths: dict[str, list[list[str]]] = {}

    def dfs(node: str, path: list[str], depth: int) -> None:
        if depth == 0 or not graph.get(node):
            current.append(path.copy())
            return
        for nxt in graph[node]:
            if nxt in path:
                continue
            dfs(nxt, [*path, nxt], depth - 1)

    for entry in entry_ids:
        current: list[list[str]] = []
        if entry in graph:
            dfs(entry, [entry], max_depth)
        paths[entry] = current[:40]
    return paths


def render_markdown(records: list[FunctionRecord], paths: dict[str, list[list[str]]]) -> str:
    total = len(records)
    top = sum(1 for r in records if r.kind == "top_level")
    methods = sum(1 for r in records if r.kind == "class_method")
    nested = sum(1 for r in records if r.kind == "nested")
    async_n = sum(1 for r in records if r.is_async)

    lines: list[str] = []
    lines.append("# PaperQA System Inventory")
    lines.append("")
    lines.append(f"- Source root: `{ROOT}`")
    lines.append(f"- Total functions: **{total}**")
    lines.append(f"- Top-level: **{top}** | Class methods: **{methods}** | Nested: **{nested}** | Async: **{async_n}**")
    lines.append("")

    lines.append("## Key Entry Functions")
    keys = [
        "agents.main:agent_query",
        "agents.main:run_agent",
        "agents.search:get_directory_index",
        "docs:Docs.aadd",
        "docs:Docs.aget_evidence",
        "docs:Docs.aquery",
        "settings:Settings.get_llm",
        "settings:Settings.get_summary_llm",
        "settings:Settings.get_embedding_model",
    ]
    rec_map = {r.id: r for r in records}
    for k in keys:
        # allow exact or suffix match for class methods
        target = next((r for r in records if r.id.endswith(k)), None)
        if not target:
            continue
        lines.append(f"- `{target.id}` `{target.signature}`")
        if target.doc:
            lines.append(f"  - doc: {target.doc.splitlines()[0]}")
    lines.append("")

    lines.append("## Approximate Call Paths")
    for entry, entry_paths in paths.items():
        lines.append(f"### `{entry}`")
        if not entry_paths:
            lines.append("- (no resolved internal edges)")
            continue
        for p in entry_paths[:12]:
            lines.append(f"- {' -> '.join(p)}")
    lines.append("")

    lines.append("## Notes")
    lines.append("- Call paths are static approximations from AST, not runtime traces.")
    lines.append("- Dynamic dispatch / external library callbacks are intentionally not expanded.")
    return "\n".join(lines) + "\n"


def main() -> None:
    if not ROOT.exists():
        raise FileNotFoundError(f"Missing source root: {ROOT}")

    records: list[FunctionRecord] = []
    for py_file in sorted(ROOT.rglob("*.py")):
        records.extend(extract_records(py_file))
    resolve_calls(records)

    entry_ids = []
    suffix_targets = [
        "agents.main:agent_query",
        "agents.search:get_directory_index",
        "docs:Docs.aquery",
    ]
    for t in suffix_targets:
        match = next((r for r in records if r.id.endswith(t)), None)
        if match:
            entry_ids.append(match.id)
    paths = build_flow_paths(records, entry_ids, max_depth=5)

    inventory_path = OUT_DIR / "paperqa_function_interfaces.json"
    callgraph_path = OUT_DIR / "paperqa_callgraph.json"
    report_path = OUT_DIR / "paperqa_system_report.md"

    inventory_payload: list[dict[str, Any]] = [asdict(r) for r in records]
    inventory_path.write_text(
        json.dumps(inventory_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    callgraph_payload = {
        "nodes": [r.id for r in records],
        "edges": [
            {"source": r.id, "target": t}
            for r in records
            for t in r.resolved_calls
        ],
        "entry_paths": paths,
    }
    callgraph_path.write_text(
        json.dumps(callgraph_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(render_markdown(records, paths), encoding="utf-8")

    print(f"Functions discovered: {len(records)}")
    print(f"Wrote: {inventory_path}")
    print(f"Wrote: {callgraph_path}")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()
