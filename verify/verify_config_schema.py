"""Sprint-11/13 配置 SSOT 一致性断言（离线可跑）。



锁定（F2 阶段 A + C）：

1. get_config_schema() 结构完整：version=1、7 分组、字段必含 key/label/type、关键字段默认值正确；

2. assert_schema_consistency() 无 pydantic_path 漂移；

3. validate_config() 的 errors/warnings/hints 行为（非法 enum/范围外/未知参数/远程源未切 remote）；

4. **M7 收敛（Sprint-13 US-13.1 版）**：前端 App.jsx Config 节点**零硬编码**（16 个配置键不得以字面量出现在 n1 块）；

   provider_config 的 deepseek 条目 api_base/model 与 schema 默认一致（provider 默认值的 SSOT 归属）；

5. **Settings 升级护栏（Sprint-13 US-13.2）**：Settings 全字段路径与基线快照 `verify/settings_baseline.json` 比对——

   升级 paperqa 后出现新增/删除字段时 FAIL 并打印 diff（提示重新策展 GROUPS 后 `--regen-baseline` 重建基线）。



运行：.venv\\Scripts\\python.exe verify\\verify_config_schema.py（纯离线）

重建基线：.venv\\Scripts\\python.exe verify\\verify_config_schema.py --regen-baseline

"""



from __future__ import annotations

VERIFY_META = {'features': '配置 SSOT 一致性 + M7 前端零硬编码 + Settings 升级基线护栏（114 断言，离线）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': ['/api/config_schema', '/api/config/validate'], 'requires': ['none']}



import json

import re

import sys

from pathlib import Path

from typing import Any



ROOT = Path(__file__).resolve().parent.parent

PQA_SCRIPT = ROOT / "paper-qa-script"

BACKEND = PQA_SCRIPT / "reactflow-paperqa-prototype" / "backend"

APP_JSX = PQA_SCRIPT / "reactflow-paperqa-prototype" / "frontend" / "src" / "App.jsx"

BASELINE_PATH = ROOT / "verify" / "settings_baseline.json"



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





# 前端零硬编码清单（Sprint-13 US-13.1；032 加固：守卫键集合从 schema 派生，与 GROUPS 单一真源，杜绝手维护清单盲区）

CONFIG_KEYS = None  # 运行时由 get_config_schema() 派生（全部字段 key）





def collect_settings_paths(node: Any, prefix: str = "", depth: int = 0) -> list[str]:

    """递归收集 Settings 的 pydantic 字段点路径（BaseModel 分支下钻，深度上限 4）。"""

    from pydantic import BaseModel



    from app.config_schema import _unwrap_model_type



    out: list[str] = []

    if depth > 4 or not (isinstance(node, type) and issubclass(node, BaseModel)):

        return out

    for name, field in node.model_fields.items():

        path = f"{prefix}.{name}" if prefix else name

        sub = _unwrap_model_type(field.annotation)

        if sub is not None:

            out.extend(collect_settings_paths(sub, path, depth + 1))

        else:

            out.append(path)

    return sorted(out)





def main() -> int:

    from app.config_schema import get_config_schema, validate_config, assert_schema_consistency  # noqa: E402

    from paperqa.settings import Settings  # noqa: E402

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



    # M7（Sprint-13 版）：前端零硬编码——守卫键集合 = schema 全部字段 key（单一真源）

    # 块抽取假设：n1 为首个 makeNode，定界为 "makeNode(\"n1\"" 起至首个 "})," 止（n1 params 内不得嵌套对象，032 nit 记录）

    appjs = APP_JSX.read_text(encoding="utf-8")

    block = appjs[appjs.index('makeNode("n1"'):]

    block = block[: block.index("}),")]

    block_no_comments = "\n".join(ln for ln in block.splitlines() if not ln.lstrip().startswith("//"))

    for key in sorted(flat.keys()):

        hardcoded = re.search(rf"\b{key}\s*:", block_no_comments)

        ok(f"M7 前端零硬编码 {key}", hardcoded is None,

           ("App.jsx n1 含字面量（默认值唯一真源应为 schema）" if hardcoded else f"n1 无 {key} 字面量"))



    ds = PROVIDERS.get("deepseek", {})

    ok("provider_config deepseek api_base 存在", bool(ds.get("api_base")), f"api_base={ds.get('api_base')!r}")

    ok("provider_config deepseek model == schema", ds.get("model") == "openai/deepseek-v4-flash",

       f"provider_model={ds.get('model')!r}")



    # Settings 升级护栏（US-13.2）

    if "--regen-baseline" in sys.argv:

        current = collect_settings_paths(Settings)

        BASELINE_PATH.write_text(

            json.dumps({"fields": current, "note": "由 verify_config_schema.py --regen-baseline 生成（Settings BaseModel 分支字段路径，深度≤4；容器内字段不在基线范围内）"},

                       ensure_ascii=False, indent=2) + "\n",

            encoding="utf-8",

        )

        print(f"baseline regenerated: {len(current)} field paths -> {BASELINE_PATH}")

        return 0

    current = collect_settings_paths(Settings)

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["fields"]

    added = [p for p in current if p not in baseline]

    removed = [p for p in baseline if p not in current]

    ok("Settings 字段基线一致（升级护栏）", added == [] and removed == [],

       f"added={added[:10]} removed={removed[:10]}（paperqa 升级后请重新策展 GROUPS 并 --regen-baseline）")



    print(f"\nALL PASS ({PASSED} assertions)")

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

