#!/usr/bin/env python3
"""思维模型库只读校验器（MM-1 交付；schema 见 library/schema.json）。

判据全部来自 `library/schema.json`：本脚本不写死字段名、取值域或阈值——
加字段/改取值域只改 schema.json，不改这里（同 1-WORKFLOW §6「政策数据化」）。

校验项：
  ① JSON 可解析；文件名 = `<id>.<version>.json`；schema_version 主版本兼容；
  ② 必填字段齐全且非空；类型/长度/正则/枚举/日期逐项匹配；
  ③ 未知顶层键 = FAIL（拼错字段名不得静默通过）；`x_` 前缀扩展键放行；
  ④ 跨文件：id 与 name 在库内唯一。
任一失败 → 逐条点名（`文件: 字段路径: 期望 …，实际 …`）并 rc=1；
全过 → 末行 `OK`、rc=0。

本脚本只读：不写文件、不接入 `verify/` 门禁体系。

用法：
    python scripts/mental-model-check.py
    python scripts/mental-model-check.py --model <file.json>
    python scripts/mental-model-check.py --library <dir> --schema <schema.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "docs" / "iteration" / "phases" / "mental-models" / "library"
SCHEMA = LIBRARY / "schema.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path, errors: list[str]):
    """读取并解析 UTF-8 JSON；失败时记一条错误并返回 None。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: 读取失败：{exc}")
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(
            f"{path}: JSON 解析失败（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}"
        )
        return None


def show_value(value) -> str:
    """把任意值渲染成短文本（错误消息里的「实际」）。"""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            text = repr(value)
    return text if len(text) <= 48 else text[:45] + "..."


def describe(spec: dict) -> str:
    """把 schema 片段渲染成人读的期望描述（错误消息用）。"""
    kind = spec.get("type")
    if kind == "string":
        bits: list[str] = []
        low = spec.get("min_chars")
        high = spec.get("max_chars")
        if low is not None or high is not None:
            bits.append(f"{low if low is not None else 0}.."
                        f"{high if high is not None else '∞'} 字")
        if spec.get("pattern"):
            bits.append(f"匹配 {spec['pattern']}")
        if spec.get("format") == "date":
            bits.append("YYYY-MM-DD")
        return "字符串(" + "，".join(bits) + ")" if bits else "非空字符串"
    if kind == "array":
        return f"数组[{describe(spec.get('items') or {})}]"
    if kind == "object":
        keys = "、".join((spec.get("properties") or {}).keys())
        return f"对象(键：{keys})"
    if kind == "enum":
        return "取值 " + " / ".join(str(item) for item in spec.get("values") or [])
    if kind == "boolean":
        return "布尔"
    return f"未知类型 {kind!r}"


def check_string(value, spec: dict, where: str, errors: list[str]) -> None:
    """校验字符串：类型 / 去空白长度 / 正则 / 日期。"""
    if not isinstance(value, str):
        errors.append(
            f"{where}: 期望 {describe(spec)}，实际 {type(value).__name__} "
            f"{show_value(value)}"
        )
        return
    text = value.strip()
    low = spec.get("min_chars")
    high = spec.get("max_chars")
    if low is not None and len(text) < low:
        errors.append(f"{where}: 去空白后 {len(text)} 字 < 下限 {low} 字（或全空白）")
    if high is not None and len(text) > high:
        errors.append(f"{where}: 去空白后 {len(text)} 字 > 上限 {high} 字")
    pattern = spec.get("pattern")
    if pattern is not None and re.search(str(pattern), value) is None:
        errors.append(f"{where}: 不匹配 {pattern}：{show_value(value)}")
    if spec.get("format") == "date":
        try:
            date.fromisoformat(text)
        except ValueError:
            errors.append(f"{where}: 不是合法日期（YYYY-MM-DD）：{show_value(value)}")


def check_array(value, spec: dict, where: str, errors: list[str],
                prefix: str) -> None:
    """校验数组：类型、项数上下限、逐项递归。"""
    if not isinstance(value, list):
        errors.append(
            f"{where}: 期望 {describe(spec)}，实际 {type(value).__name__} "
            f"{show_value(value)}"
        )
        return
    low = spec.get("min_items")
    high = spec.get("max_items")
    if low is not None and len(value) < low:
        errors.append(f"{where}: 只有 {len(value)} 项 < 下限 {low} 项")
    if high is not None and len(value) > high:
        errors.append(f"{where}: 有 {len(value)} 项 > 上限 {high} 项")
    items = spec.get("items")
    if not isinstance(items, dict):
        errors.append(f"{where}: schema 缺 items 规格（校验器 fail-closed）")
        return
    for index, item in enumerate(value):
        check_value(item, items, f"{where}[{index}]", errors, prefix)


def check_object(value, spec: dict, where: str, errors: list[str],
                 prefix: str) -> None:
    """校验对象：必填键、逐键递归、未知键（x_ 前缀除外）。"""
    if not isinstance(value, dict):
        errors.append(
            f"{where}: 期望 {describe(spec)}，实际 {type(value).__name__} "
            f"{show_value(value)}"
        )
        return
    props = spec.get("properties")
    if not isinstance(props, dict):
        errors.append(f"{where}: schema 缺 properties 规格（校验器 fail-closed）")
        return
    for key, sub in props.items():
        path = f"{where}.{key}"
        if key not in value:
            if sub.get("required"):
                errors.append(f"{path}: 缺必填键（期望 {describe(sub)}）")
            continue
        check_value(value[key], sub, path, errors, prefix)
    for key in value:
        if key not in props and not key.startswith(prefix):
            errors.append(
                f"{where}.{key}: 未知键（拼错字段名一律 FAIL；"
                f"自定义扩展须以 {prefix} 开头）"
            )


def check_value(value, spec: dict, where: str, errors: list[str],
                prefix: str) -> None:
    """按 schema 片段递归校验一个值；错误逐条写入 errors（不抛异常）。"""
    kind = spec.get("type")
    if kind == "string":
        check_string(value, spec, where, errors)
    elif kind == "boolean":
        if not isinstance(value, bool):
            errors.append(
                f"{where}: 期望布尔，实际 {type(value).__name__} {show_value(value)}"
            )
    elif kind == "enum":
        values = spec.get("values") or []
        if not isinstance(value, str) or value not in values:
            errors.append(f"{where}: 期望 {describe(spec)}，实际 {show_value(value)}")
    elif kind == "array":
        check_array(value, spec, where, errors, prefix)
    elif kind == "object":
        check_object(value, spec, where, errors, prefix)
    else:
        errors.append(f"{where}: schema 的 type={kind!r} 未定义（fail-closed）")


def check_model(rel: str, data, schema: dict, prefix: str,
                errors: list[str], seen: dict[str, dict[str, str]]) -> None:
    """校验一个模型文件；跨文件唯一性记在 seen。"""
    if not isinstance(data, dict):
        errors.append(f"{rel}: 顶层必须是 JSON 对象，实际 {type(data).__name__}")
        return
    fields = schema["fields"]
    for key, spec in fields.items():
        where = f"{rel}: {key}"
        if key not in data:
            if spec.get("required") is True:
                errors.append(f"{where}: 缺必填字段（期望 {describe(spec)}）")
            continue
        check_value(data[key], spec, where, errors, prefix)
    for key in data:
        if key in fields or key.startswith(prefix):
            continue
        errors.append(
            f"{rel}: {key}: 未知字段（拼错字段名一律 FAIL；"
            f"自定义扩展须以 {prefix} 开头）"
        )


def check_cross_file(rel: str, data: dict, schema: dict,
                     errors: list[str], seen: dict[str, dict[str, str]]) -> None:
    """跨文件约束：文件名、id 唯一、name 唯一、schema 主版本。"""
    model_id = data.get("id")
    version = data.get("version")
    if isinstance(model_id, str) and isinstance(version, str):
        expected = f"{model_id}.{version}.json"
        if Path(rel).name != expected:
            errors.append(f"{rel}: 文件名必须是 {expected}（<id>.<version>.json）")
        if model_id in seen["ids"]:
            errors.append(
                f"{rel}: id {model_id!r} 与 {seen['ids'][model_id]} 重复"
                f"（库内一个 id 只保留一个在库版本）"
            )
        else:
            seen["ids"][model_id] = rel
    name = data.get("name")
    if isinstance(name, str) and name:
        if name in seen["names"]:
            errors.append(f"{rel}: name {name!r} 与 {seen['names'][name]} 重复")
        else:
            seen["names"][name] = rel
    declared = data.get("schema_version")
    supported = str(schema.get("schema_version") or "")
    if isinstance(declared, str) and "." in declared and "." in supported:
        old = declared.split(".", 1)[0]
        now = supported.split(".", 1)[0]
        if old != now:
            errors.append(
                f"{rel}: schema_version {declared!r} 与本库 schema "
                f"{supported!r} 主版本不一致（flexible 要求主版本相同）"
            )


def check_schema(schema, path: Path, errors: list[str]) -> bool:
    """schema 自检：fields 非空、每项有 type 与布尔 required、前缀可用。"""
    fields = schema.get("fields")
    if not isinstance(fields, dict) or not fields:
        errors.append(f"{path}: schema.fields 缺失或为空（校验器 fail-closed）")
        return False
    good = True
    for key, spec in fields.items():
        if not isinstance(spec, dict):
            errors.append(f"{path}: fields.{key} 不是对象")
            good = False
            continue
        if not isinstance(spec.get("type"), str):
            errors.append(f"{path}: fields.{key}.type 缺失或不是字符串")
            good = False
        if not isinstance(spec.get("required"), bool):
            errors.append(f"{path}: fields.{key}.required 缺失或不是布尔")
            good = False
    prefix = (schema.get("flexible") or {}).get("extension_prefix")
    if not isinstance(prefix, str) or not prefix:
        errors.append(f"{path}: flexible.extension_prefix 缺失（fail-closed）")
        good = False
    return good


def display_path(path: Path) -> str:
    """尽量显示仓库相对路径（POSIX），否则原样返回。"""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def print_fail(errors: list[str]) -> None:
    """打印失败清单（逐条一行）并以统一末行收尾。"""
    print(f"MENTAL-MODEL CHECK FAIL: {len(errors)} 项")
    for item in errors:
        print(f"  - {item}")
    print(f"FAIL: {len(errors)} 项")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """命令行参数：默认校验 library/ 下全部模型。"""
    parser = argparse.ArgumentParser(
        description="思维模型库只读校验器（schema 驱动，零依赖）"
    )
    parser.add_argument(
        "--model", action="append", default=[],
        help="只校验指定模型文件（可重复）",
    )
    parser.add_argument(
        "--library", default=None,
        help="模型库目录（默认 docs/iteration/phases/mental-models/library）",
    )
    parser.add_argument(
        "--schema", default=None, help="schema.json 路径（默认库内 schema.json）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """入口：返回退出码（0 = 全部通过；1 = 有错误）。"""
    args = parse_args(argv)
    errors: list[str] = []
    library = Path(args.library) if args.library else LIBRARY
    if args.schema:
        schema_path = Path(args.schema)
    elif args.library:
        schema_path = library / "schema.json"
    else:
        schema_path = SCHEMA
    schema = load_json(schema_path, errors)
    if not isinstance(schema, dict) or not check_schema(schema, schema_path, errors):
        print_fail(errors)
        return 1
    prefix = str(schema["flexible"]["extension_prefix"])
    if args.model:
        files = [Path(item) for item in args.model]
    else:
        if not library.is_dir():
            errors.append(f"{display_path(library)}: 库目录不存在（fail-closed）")
        files = sorted(
            path for path in library.glob("*.json")
            if path.resolve() != schema_path.resolve()
        )
        if not files and library.is_dir():
            errors.append(
                f"{display_path(library)}: 没有任何模型文件（空库不算通过）"
            )
    seen: dict[str, dict[str, str]] = {"ids": {}, "names": {}}
    for path in files:
        rel = display_path(path)
        data = load_json(path, errors)
        if data is None:
            continue
        check_model(rel, data, schema, prefix, errors, seen)
        if isinstance(data, dict):
            check_cross_file(rel, data, schema, errors, seen)
    if errors:
        print_fail(errors)
        return 1
    print(f"checked {len(files)} model(s) against schema {schema['schema_version']}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
