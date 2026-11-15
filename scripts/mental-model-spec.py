#!/usr/bin/env python3
"""MM-2: validate a model, then render an editable five-section spec draft.

Usage: python scripts/mental-model-spec.py --model <id.version.json>
Optional: --schema <schema.json>, --check, or --out <draft.md> [--force].
Only the standard library is needed. Model and schema files stay read-only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PHASE = ROOT / "docs" / "iteration" / "phases" / "mental-models"
SCHEMA = PHASE / "library" / "schema.json"
CHECKER = Path(__file__).with_name("mental-model-check.py")
SUPPORTED_MAJOR = "0"


def display(path: Path) -> str:
    """Use repository-relative paths where possible."""
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def failure(path: Path, field: str, expected: str, actual: object) -> str:
    """Keep every generator error attributable to a file and field."""
    return f"{display(path)}: {field}: 期望 {expected}，实际 {actual}"


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject duplicate JSON keys instead of silently losing an input value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"重复键 {key!r}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    """Reject non-JSON numeric constants accepted by Python's default decoder."""
    raise ValueError(f"非 JSON 常量 {value}")


def load(path: Path, errors: list[str]) -> tuple[dict, bytes]:
    """Read strict UTF-8 JSON without modifying the source."""
    try:
        raw = path.read_bytes()
        data = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        if not isinstance(data, dict):
            raise ValueError(f"顶层 {type(data).__name__}")
        return data, raw
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(failure(path, "<json>", "UTF-8 JSON 对象", exc))
        return {}, b""


def explain(detail: str, model: dict, schema: dict) -> str:
    """Add expected/actual context to legacy checker diagnostics consistently."""
    location, _, message = detail.partition(": ")
    field = message.partition(":")[0].split(" ", 1)[0]
    value = model
    spec = {"type": "object", "properties": schema["fields"]}
    try:
        for name, index in re.findall(r"([^.[\]]+)|\[(\d+)\]", field):
            if index:
                value = value[int(index)]
                spec = spec["items"]
            else:
                spec = spec["properties"][name]
                value = value.get(name, "<MISSING>")
        expected = {k: v for k, v in spec.items() if k in (
            "type", "required", "min_chars", "max_chars", "pattern",
            "min_items", "max_items", "values", "format",
        )}
        actual = json.dumps(value, ensure_ascii=False)
        if len(actual) > 120:
            actual = actual[:117] + "..."
        return (f"{location}: {field}: 期望 "
                f"{json.dumps(expected, ensure_ascii=False)}，实际 {actual}；{message}")
    except (KeyError, TypeError, IndexError, AttributeError):
        return (f"{location}: {field}: 期望符合 schema 与跨文件约束，"
                f"实际 {message}")


def precheck(model_path: Path, schema_path: Path, model: dict,
             schema: dict) -> list[str]:
    """Run the unchanged MM-1 CLI; only its exact success protocol passes."""
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--model", str(model_path),
         "--schema", str(schema_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    expected = [
        f"checked 1 model(s) against schema {schema.get('schema_version')}", "OK",
    ]
    if (result.returncode == 0 and result.stdout.splitlines() == expected
            and not result.stderr):
        return []
    details = []
    for line in result.stdout.splitlines():
        if line.startswith("  - "):
            details.append(explain(line[4:], model, schema))
    if details:
        return details
    return [failure(
        model_path, "<precheck>", "校验器 rc=0 + OK，且无 warning/SKIP",
        f"rc={result.returncode}; {result.stdout.strip()}; {result.stderr.strip()}",
    )]


def blank_required(data: dict, fields: dict, path: str = "") -> list[str]:
    """Cover required empty values even when a schema has no length minimum."""
    missing = []
    for key, spec in fields.items():
        field = f"{path}.{key}" if path else key
        if key not in data:
            continue  # The MM-1 checker reports absent keys.
        value = data[key]
        empty = value is None or value == [] or value == {}
        empty = empty or (isinstance(value, str) and not value.strip())
        if spec.get("required") and empty:
            missing.append(field)
        if isinstance(value, dict) and spec.get("type") == "object":
            missing.extend(blank_required(value, spec["properties"], field))
    return missing


def inline(value: object) -> str:
    """Escape model text so it cannot inject Markdown sections or comments."""
    text = " ".join(str(value).split())
    for char in "\\`*_{}[]()#+-.!|<>&":
        text = text.replace(char, "\\" + char)
    return text


def render_value(value: object, spec: dict, depth: int = 0) -> list[str]:
    """Render only schema-declared properties; explicit extensions stay in JSON."""
    indent = "  " * depth
    if isinstance(value, dict):
        lines = []
        for key, sub in spec.get("properties", {}).items():
            if key in value:
                lines.append(f"{indent}- {inline(sub.get('label', key))}：")
                lines.extend(render_value(value[key], sub, depth + 1))
        return lines
    if isinstance(value, list):
        return [line for item in value
                for line in render_value(item, spec.get("items", {}), depth)]
    return [f"{indent}- {inline(value)}"]


def degraded(data: dict, fields: dict, path: str = "") -> list[str]:
    """Mark every omitted optional field, including nested schema additions."""
    lines = []
    for key, spec in fields.items():
        field = f"{path}.{key}" if path else key
        if key not in data and not spec["required"]:
            action = "derived" if spec.get("maps_to") == "Steps" else "omitted"
            lines.append(f"DEGRADED:{field}:{action}")
        elif isinstance(data.get(key), dict) and spec.get("type") == "object":
            lines.extend(degraded(data[key], spec["properties"], field))
    return lines


def render(model: dict, schema: dict) -> str:
    """Project schema maps_to values into five sections without inventing facts."""
    buckets: dict[str, list[str]] = {}
    fields = schema["fields"]
    for key, spec in fields.items():
        if key in model and spec.get("maps_to", "—") != "—":
            target = spec["maps_to"]
            buckets.setdefault(target, []).extend([
                f"**{inline(spec.get('label', key))}**", "",
                *render_value(model[key], spec), "",
            ])
    title = " / ".join(
        inline(model[key]) for key, spec in fields.items()
        if spec.get("maps_to") == "spec 标题"
    )
    header = schema["flexible"]["human_edit"]["provenance_header"]
    for key in ("id", "version", "schema_version"):
        header = header.replace(f"<{key}>", str(model[key]))
    lines = [
        header, "", f"# {title}", "",
        "> 半自动生成的草稿；须人审填充后才可实例化。", "",
        "## Role", "", *buckets.pop("Role", []),
        "### Provenance", "", *buckets.pop("溯源头", []),
        "**建议 spec 文件名**", "",
        f"- {inline(model['id'])}.md", "",
    ]
    buckets.pop("spec 标题", None)
    buckets.pop("spec 文件名", None)
    lines.extend([
        "## Trigger (When to use)", "", *buckets.pop("Trigger", []),
        "## Inputs & Outputs", "",
        "### Task Input", "", *buckets.pop("Task Input", []),
        "### Output Template", "", *buckets.pop("Output Template", []),
        "### Done criteria", "", *buckets.pop("验收", []),
        "> 上述为模型的验收目标，本骨架不表示已通过或已首跑。", "",
        "## Steps", "",
    ])
    steps = buckets.pop("Steps", [])
    lines.extend(steps or [
        "1. 核对 Task Input 的材料与适用边界。",
        "2. 逐项完成 Output Template 中的产物；具体方法由人审补齐。",
        "3. 按 Done criteria 自查，并保留可核证据。", "",
    ])
    parameters = buckets.pop("Configurable Parameters", [])
    if parameters:
        lines.extend(["### Configurable Parameters", "", *parameters])
    lines.extend([
        "### Human edit", "",
        "- [ ] 补齐任务参数、执行细节与输出格式。",
        "- [ ] 人审后另行实例化、校验并演示；本生成器只产出草稿。", "",
        "## Forbidden (When not to use / Boundaries)", "",
        *buckets.pop("Forbidden", []),
    ])
    for target, content in buckets.items():
        lines.extend([f"### Schema addition: {inline(target)}", "", *content])
    lines.extend(["### Generation contract", ""])
    for group in ("robust", "flexible"):
        for rule in schema[group]["rules"]:
            lines.append(f"- {inline(rule['id'])}：{inline(rule['statement'])}")
    lines.extend(["", "### Degradation record", "", "```text"])
    lines.extend(degraded(model, fields) or ["DEGRADED:none"])
    lines.extend(["```", ""])
    return "\n".join(lines)


def publish(path: Path, content: str, force: bool) -> None:
    """Publish a complete LF draft atomically, protecting edits by default."""
    path = path.absolute()
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT) and not resolved.is_relative_to(PHASE):
        raise ValueError("仓库内 --out 仅允许 docs/iteration/phases/mental-models/")
    if path.suffix.lower() != ".md":
        raise ValueError("--out 必须为 .md 草稿，不得覆盖 JSON 源文件")
    if path.exists() and not force:
        raise FileExistsError("产物已存在；保留人工修改，显式 --force 才覆盖")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, path)
        elif os.name == "nt":
            os.rename(temporary, path)  # Windows rename never replaces a file.
        else:
            os.link(temporary, path)  # Atomic no-clobber publication on POSIX.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """Validate completely before producing stdout or touching an output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--schema", default=SCHEMA, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--out", type=Path)
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.force and not args.out:
        parser.error("--force 必须与 --out 同用")
    errors: list[str] = []
    model, model_raw = load(args.model, errors)
    schema, schema_raw = load(args.schema, errors)
    result = ""
    try:
        if not errors:
            errors.extend(precheck(args.model, args.schema, model, schema))
            major = str(schema.get("schema_version", "")).split(".")[0]
            if major != SUPPORTED_MAJOR:
                errors.append(failure(
                    args.schema, "schema_version", f"主版本 {SUPPORTED_MAJOR}",
                    schema.get("schema_version"),
                ))
        if not errors:
            for field in blank_required(model, schema["fields"]):
                errors.append(failure(args.model, field, "非空必填字段", "空值"))
            for path, raw in ((args.model, model_raw), (args.schema, schema_raw)):
                if path.read_bytes() != raw:
                    errors.append(failure(path, "<snapshot>", "校验期间不变", "已变"))
        if not errors:
            # Check mode validates the generation contract but never renders.
            for group in ("robust", "flexible"):
                for rule in schema[group]["rules"]:
                    if not all(isinstance(rule[k], str) for k in ("id", "statement")):
                        raise ValueError(f"{group}.rules 需要 id/statement 字符串")
            if args.check:
                result = "OK: model + schema validated; no spec generated\n"
            else:
                result = render(model, schema)
                if args.out:
                    publish(args.out, result, args.force)
                    result = f"OK: generated {display(args.out)}\n"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        target = args.out or args.schema
        errors.append(failure(target, "<generation>", "完整契约与可发布路径", exc))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"FAIL: {len(errors)} 项；未生成 spec", file=sys.stderr)
        return 1
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", newline="\n")
    raise SystemExit(main())
