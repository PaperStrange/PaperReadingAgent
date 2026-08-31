"""Sprint-11 US-11.1/11.2：配置 SSOT 一致性断言（离线可跑）。

锁定三件事（F2 阶段 A + M7 默认值漂移收敛）：
1. get_config_schema() 结构完整：version=1、7 分组、字段必含 key/label/type、关键字段默认值正确；
2. assert_schema_consistency() 无 pydantic_path 漂移；
3. validate_config() 的 errors/warnings/hints 行为（非法 enum/范围外/未知参数/远程源未切 remote）；
4. M7 收敛：前端 App.jsx 配置节点默认值（正则抽取源码字面量）与 schema 默认值一致；
   provider_config 的 deepseek 条目 api_base/model 与 schema 默认一致。

运行：.venv\\Scripts\\python.exe verify\\verify_config_schema.py（纯离线）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PQA_SCRIPT = ROOT / "paper-qa-script"
BACKEND = PQA_SCRIPT / "reactflow-paperqa-prototype" / "backend"
APP_JSX = PQA_SCRIPT / "reactflow-paperqa-prototype" / "frontend" / "src" / "App.jsx"

for _p in (str(PQA_SCRIPT), str(BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def main() -> int:
    from app.config_schema import get_config_schema, validate_config, assert_schema_consistency  # noqa: E402
    from provider_config import PROVIDERS  # noqa: E402

    schema = get_config_schema()
    ok("schema version=1", schema.get("version") == 1, f"version={schema.get('version')}")
    groups = schema["groups"]
    ok("schema 7 分组", len(groups) == 7, f"groups={[g['key'] for g in groups]}")
    flat: dict[str, dict] = {}
    for g in groups:
        assert g["key"] and g["label"], f"分组缺 key/label: {g}"
        for f in g["fields"]:
            for k in ("key", "label", "type"):
                ok(f"字段 {f.get('key')} 有 {k}", bool(f.get(k)), f"{f}")
            flat[f["key"]] = f
    ok("schema 字段总数", len(flat) == 23, f"fields={len(flat)}")

    # 关键字段默认值（app 有效默认）
    expect_defaults = {
        "provider": "deepseek", "model": "openai/deepseek-v4-flash",
        "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
        "temperature": 0.1, "embedding_batch_size": 10,
        "chunk_chars": 5000, "chunk_overlap": 250,
        "paper_directory": "data/pdf", "index_name": "debug_index",
        "data_source": "local",
    }
    for key, val in expect_defaults.items():
        got = flat.get(key, {}).get("default")
        ok(f"schema 默认值 {key}", got == val, f"got={got!r} expect={val!r}")

    problems = assert_schema_consistency()
    ok("pydantic_path 一致性", problems == [], f"problems={problems}")

    # validate_config 行为
    r = validate_config({"data_source": "nope"})
    ok("非法 enum → errors", r["errors"] and "取值非法" in r["errors"][0], str(r))
    r = validate_config({"temperature": 5})
    ok("范围外 number → errors", r["errors"] and "超出范围" in r["errors"][0], str(r))
    r = validate_config({"unknown_thing": 1})
    ok("未知参数 → warnings", r["warnings"] and "未知参数" in r["warnings"][0], str(r))
    r = validate_config({"source_urls": ["https://a/b.pdf"], "data_source": "local"})
    ok("远程源未切 remote → warnings", r["warnings"] and "不会生效" in r["warnings"][0], str(r))
    r = validate_config({"temperature": 0.1})
    ok("合法值 → 无 errors", r["errors"] == [], str(r))

    # M7 收敛：前端 App.jsx n1 节点默认值（源码字面量抽取，剔除注释行）与 schema 一致
    appjs = APP_JSX.read_text(encoding="utf-8")
    block = appjs[appjs.index('makeNode("n1"'):]
    block = block[: block.index("}),")]
    block = "\n".join(
        ln for ln in block.splitlines() if not ln.lstrip().startswith("//")
    )
    frontend_vals: dict[str, object] = {}
    for key in ("provider", "api_base", "model", "embedding_model", "paper_directory",
                "index_name", "data_source", "manifest_file", "embedding_batch_size",
                "chunk_chars", "chunk_overlap", "temperature",
                "source_urls", "source_arxiv_ids", "source_dois"):
        m = re.search(rf"\b{key}:\s*(\"([^\"]*)\"|\[|\d+(?:\.\d+)?|true|false)", block)
        if not m:
            ok(f"App.jsx n1 含 {key}", False, "未匹配")
            continue
        if m.group(1).startswith('"'):
            frontend_vals[key] = m.group(2)
        elif m.group(1) == "[":
            frontend_vals[key] = []  # 空列表字段
        elif m.group(1) in ("true", "false"):
            frontend_vals[key] = m.group(1) == "true"
        else:
            frontend_vals[key] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))

    # api_base 是 provider 预填值：与 provider_config deepseek 条目一致（不属于 schema 默认值）
    ds = PROVIDERS.get("deepseek", {})
    ok("M7 api_base = provider_config deepseek", frontend_vals.get("api_base") == ds.get("api_base"),
       f"front={frontend_vals.get('api_base')!r} provider={ds.get('api_base')!r}")

    for key, val in expect_defaults.items():
        if key in ("provider", "model", "embedding_model", "paper_directory", "index_name", "data_source"):
            ok(f"M7 前端默认值 {key} == SSOT", frontend_vals.get(key) == val,
               f"front={frontend_vals.get(key)!r} ssot={val!r}")
        else:
            # number/bool 字段：前端字面量数值应与 schema 默认一致
            ok(f"M7 前端默认值 {key} == SSOT", frontend_vals.get(key) == val,
               f"front={frontend_vals.get(key)!r} ssot={val!r}")
    ok("M7 空列表字段", frontend_vals.get("manifest_file") == "", f"manifest={frontend_vals.get('manifest_file')!r}")
    for key in ("source_urls", "source_arxiv_ids", "source_dois"):
        ok(f"M7 空列表字段 {key}", frontend_vals.get(key) == [],
           f"front={frontend_vals.get(key)!r} expect=[]")

    # provider_config 与 schema 的 provider/model 默认一致性
    ok("provider_config deepseek model == schema", ds.get("model") == "openai/deepseek-v4-flash",
       f"provider_model={ds.get('model')!r}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
