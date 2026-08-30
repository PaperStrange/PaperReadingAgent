"""配置唯一真源（Sprint-2 US-2.1，方案 B：手工策展 schema + 自动提取）。

设计（refactor-analysis.MD §4 Q2）：
- **唯一真源** = 本模块的 `GROUPS`（策展覆盖层：分组/中文标签/类型/范围/影响提示/顺序），
  分七组：LLM / Embedding / Parsing / Agent / Answer / 数据源 / Index（数据源组为 Sprint-3 主题 B 新增）。
- 字段默认值两级来源：
  1. 策展层显式 `default`（app 有效默认，如 build_settings 的 `temperature=0.1`）优先；
  2. 否则若有 `pydantic_path`，从 paperqa `Settings.model_fields` **自动提取**默认值
     （`Settings.model_json_schema()` 因 `AsyncContextSerializer` 不可 JSON-Schema 化，不可用），
     避免与框架双份维护。
- `readonly: true` 的字段 = 通过 Settings 默认值生效、但当前表单/参数暂不可改
  （如 evidence_k / answer_length / multimodal），如实展示 + 提示，不误导。
- 维护成本控制：新增 paperqa 字段只需在 GROUPS 加一行（可只给 pydantic_path 自动取默认）；
  `assert_schema_consistency()` 校验所有 pydantic_path 真实存在（CLI/CI 用，防拼写/漂移）。
- 输出物：
  - `get_config_schema()` -> 供前端渲染/文档使用的 schema（分组 + 字段元数据）；
  - `validate_config(params)` -> {errors, warnings, hints}（用户友好报错与"影响提示"）；
  - `python -m app.config_schema` 打印 schema JSON 并做一致性自检。
"""
from __future__ import annotations

import types
import typing
from typing import Any

from pydantic import BaseModel
from pydantic.fields import PydanticUndefined

from paperqa.settings import Settings

# 影响提示模板（切换前可预期）
_IMPACTS_EMBEDDING = "切换后需重新下载对应模型并重建索引"
_IMPACTS_INDEX = "修改后需重建索引才生效"
_IMPACTS_PROVIDER = "更换服务商将替换 LLM/向量化/API Base 的默认值"
_IMPACTS_MULTIMODAL = "图片内容是否参与回答、parse_chunk_embed 耗时（视觉增强最慢）"


GROUPS: list[dict[str, Any]] = [
    {
        "key": "llm",
        "label": "LLM",
        "fields": [
            {"key": "provider", "type": "enum", "options": ["deepseek", "dashscope", "openai"],
             "default": "deepseek", "label": "模型服务商",
             "hint": "deepseek/dashscope/openai 三选一", "impacts": [_IMPACTS_PROVIDER]},
            {"key": "api_key", "type": "password", "label": "API Key",
             "hint": "留空则读取环境变量 / paper-qa-script/.env"},
            {"key": "api_base", "type": "string", "label": "API Base",
             "hint": "留空则使用服务商默认端点"},
            {"key": "model", "type": "string", "default": "openai/deepseek-v4-flash",
             "label": "LLM 模型名", "hint": "显式覆盖 provider 默认；如 provider=openai 时填 gpt-5、gpt-4o-mini"},
            {"key": "vision_model", "type": "string",
             "label": "视觉/增强模型",
             "hint": "证据摘要与图片增强用（含图片上下文必须支持视觉）；留空则随 provider 默认"},
            {"key": "temperature", "type": "number", "default": 0.1, "range": [0.0, 1.0],
             "label": "温度", "hint": "越高越发散（app 默认 0.1，paperqa 框架默认 0.0）",
             "pydantic_path": ("temperature",)},
        ],
    },
    {
        "key": "embedding",
        "label": "Embedding",
        "fields": [
            {"key": "embedding_model", "type": "string", "default": "st-multi-qa-MiniLM-L6-cos-v1",
             "label": "Embedding 模型",
             "hint": "st- 前缀 = HuggingFace 任意 SentenceTransformer 模型（本地下载/远程下载，首次自动拉取，不依赖 provider 的 embedding API）；其它名 = litellm API 向量（需 provider 支持）；litellm- 前缀强制 API",
             "impacts": [_IMPACTS_EMBEDDING]},
            {"key": "embedding_batch_size", "type": "integer", "default": 10, "range": [1, 64],
             "label": "Embedding 批大小", "hint": "每批向量化条数"},
        ],
    },
    {
        "key": "parsing",
        "label": "Parsing",
        "fields": [
            {"key": "chunk_chars", "type": "integer", "default": 5000, "range": [200, 100000],
             "label": "分块字符数", "hint": "文本分块大小", "impacts": [_IMPACTS_INDEX]},
            {"key": "chunk_overlap", "type": "integer", "default": 250, "range": [0, 10000],
             "label": "分块重叠", "hint": "相邻块重叠字符数", "impacts": [_IMPACTS_INDEX]},
            {"key": "use_doc_details", "type": "boolean", "default": False,
             "label": "元数据详情", "hint": "开启后走 Crossref/SemanticScholar 查元数据与撤稿状态（更慢；app 默认关闭，框架默认开启）",
             "impacts": ["元数据检索耗时", _IMPACTS_INDEX], "pydantic_path": ("parsing", "use_doc_details")},
            {"key": "multimodal", "type": "enum", "options": [0, 1, 2], "readonly": True,
             "label": "多模态(图片)处理",
             "hint": "0=仅文本 1=图片+视觉增强(默认) 2=图片不增强；当前由框架默认固定，表单暂不可改",
             "impacts": [_IMPACTS_MULTIMODAL], "pydantic_path": ("parsing", "multimodal")},
        ],
    },
    {
        "key": "agent",
        "label": "Agent",
        "fields": [
            {"key": "rebuild_index", "type": "boolean", "default": False, "readonly": True,
             "label": "提问前重建索引",
             "hint": "当前 app 固定为 False（提问前不重建；框架默认 True）",
             "pydantic_path": ("agent", "rebuild_index")},
        ],
    },
    {
        "key": "answer",
        "label": "Answer",
        "fields": [
            {"key": "evidence_k", "type": "integer", "range": [1, 50], "readonly": True,
             "label": "证据条数 K", "hint": "检索证据数量（当前由框架默认生效，表单暂不可改）",
             "pydantic_path": ("answer", "evidence_k")},
            {"key": "answer_length", "type": "string", "readonly": True,
             "label": "答案长度", "hint": "如 about 200 words（当前由框架默认生效，表单暂不可改）",
             "pydantic_path": ("answer", "answer_length")},
        ],
    },
    {
        "key": "datasource",
        "label": "数据源",
        "fields": [
            {"key": "data_source", "type": "enum", "options": ["local", "remote"],
             "default": "local", "label": "数据源模式",
             "hint": "local=本地论文目录（默认）；remote=URL/arXiv/DOI 下载后建索引",
             "impacts": ["切换 remote 需联网下载（首次较慢）", _IMPACTS_INDEX]},
            {"key": "source_urls", "type": "string_list", "default": [],
             "label": "URL 列表",
             "hint": "每行一个：PDF/HTML 直链（http/https）", "impacts": ["需联网"]},
            {"key": "source_arxiv_ids", "type": "string_list", "default": [],
             "label": "arXiv ID 列表",
             "hint": "每行一个：如 2409.13740（export.arxiv.org 解析，免 key）", "impacts": ["需联网"]},
            {"key": "source_dois", "type": "string_list", "default": [],
             "label": "DOI 列表",
             "hint": "每行一个：如 10.xxxx/yyyy（Unpaywall 查开放全文；需设置 UNPAYWALL_EMAIL 环境变量为真实邮箱）",
             "impacts": ["需联网", "部分论文无 OA 全文会失败"]},
            {"key": "manifest_file", "type": "string", "default": "",
             "label": "Manifest 清单",
             "hint": "可选：元数据 CSV/JSON（相对论文目录或绝对路径），对索引文件做元数据增强",
             "pydantic_path": ("agent", "index", "manifest_file")},
        ],
    },
    {
        "key": "index",
        "label": "Index",
        "fields": [
            {"key": "paper_directory", "type": "string", "default": "data/pdf",
             "label": "论文目录", "hint": "本地目录（相对后端工作目录）；remote 模式时为下载暂存目录",
             "impacts": ["数据源"]},
            {"key": "index_name", "type": "string", "default": "debug_index",
             "label": "索引名", "hint": "存于 ~/.pqa/indexes/<name>/；remote 下载目录为 data/remote/<name>/"},
        ],
    },
]

# 各步骤运行时参数（不属于配置 schema，但前端/步骤会传，不应报未知参数）
KNOWN_RUNTIME_KEYS = {
    "query", "top_n", "build", "question", "candidate_paths", "embed_mode",
    "session_id", "run_id", "step", "data_source", "source_urls",
    "source_arxiv_ids", "source_dois",
}


def _unwrap_model_type(annotation: Any) -> type[BaseModel] | None:
    """从注解中取首个 BaseModel 子类；Optional/Union 依次尝试；None 表示到容器叶子。"""
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        for arg in typing.get_args(annotation):
            found = _unwrap_model_type(arg)
            if found is not None:
                return found
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _path_exists(path: tuple[str, ...]) -> bool:
    """校验路径段都真实存在于 Settings 的 model_fields（防拼写错误）；到非 BaseModel 容器即视为叶子成功。"""
    node: Any = Settings
    for part in path:
        if not (isinstance(node, type) and issubclass(node, BaseModel)):
            return True  # 到达容器叶子（如 MaybeDict），无法静态深入，视为存在
        if part not in node.model_fields:
            return False
        field = node.model_fields[part]
        node = _unwrap_model_type(field.annotation)
    return True


def _resolve_pydantic_default(path: tuple[str, ...]) -> Any | None:
    """沿 pydantic_path 从 Settings.model_fields 提取默认值（尽力而为）；失败返回 None -> 回落策展 default。"""
    node: Any = Settings
    for i, part in enumerate(path):
        if not (isinstance(node, type) and issubclass(node, BaseModel)):
            return None
        if part not in node.model_fields:
            return None
        field = node.model_fields[part]
        if i == len(path) - 1:
            if field.default is not PydanticUndefined:
                return field.default
            if field.default_factory is not None:
                try:
                    return field.default_factory()  # type: ignore[misc]
                except Exception:
                    return None
            return None
        node = _unwrap_model_type(field.annotation)
    return None


def get_config_schema() -> dict[str, Any]:
    """生成配置 schema（分组 + 字段元数据），唯一真源的对外形态。"""
    groups: list[dict[str, Any]] = []
    for g in GROUPS:
        fields: list[dict[str, Any]] = []
        for f in g["fields"]:
            item: dict[str, Any] = {
                "key": f["key"],
                "label": f["label"],
                "type": f["type"],
                "hint": f.get("hint", ""),
                "impacts": f.get("impacts", []),
                "readonly": bool(f.get("readonly")),
            }
            if "options" in f:
                item["options"] = f["options"]
            if "range" in f:
                item["range"] = f["range"]
            if "default" in f:
                item["default"] = f["default"]  # 策展默认值优先（app 有效默认）
            elif "pydantic_path" in f:
                item["default"] = _resolve_pydantic_default(f["pydantic_path"])
            if "pydantic_path" in f:
                item["pydantic_path"] = list(f["pydantic_path"])
            fields.append(item)
        groups.append({"key": g["key"], "label": g["label"], "fields": fields})
    return {"version": 1, "groups": groups}


def _field_by_key(key: str) -> dict[str, Any] | None:
    for g in GROUPS:
        for f in g["fields"]:
            if f["key"] == key:
                return f
    return None


def validate_config(params: dict[str, Any]) -> dict[str, list[str]]:
    """校验/提示配置。返回 {errors, warnings, hints}（用户友好的中文文案）。

    注意：仅做**提示性**校验，不改变现有 build_settings 行为（行为不变原则）。
    """
    errors: list[str] = []
    warnings: list[str] = []
    hints: list[str] = []

    for key, value in params.items():
        field = _field_by_key(key)
        if field is None:
            if key not in KNOWN_RUNTIME_KEYS:
                warnings.append(f"未知参数 {key!r}（不会被生效，请检查是否拼写错误）")
            continue

        # 只读字段：后端固定默认，表单值暂不生效 -> 警告而非报错
        if field.get("readonly"):
            warnings.append(
                f"参数 {field['label']}({key}) 当前由默认值固定：{field.get('hint', '')}"
            )
            continue

        ft = field.get("type")
        if ft == "enum":
            if value not in field.get("options", []):
                errors.append(
                    f"参数 {field['label']}({key}) 取值非法：{value!r}，可选值 {field.get('options')}"
                )
        elif ft == "boolean":
            if not isinstance(value, bool):
                errors.append(f"参数 {field['label']}({key}) 应为 true/false，收到 {value!r}")
        elif ft in ("integer", "number"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"参数 {field['label']}({key}) 应为数字，收到 {value!r}")
            elif "range" in field:
                lo, hi = field["range"]
                if value < lo or value > hi:
                    errors.append(f"参数 {field['label']}({key}) 超出范围 [{lo}, {hi}]")
        elif ft == "string_list":
            # 与解析层（parse_remote_sources）契约一致：接受字符串（换行/逗号/分号切分）或列表
            if isinstance(value, str):
                pass
            elif isinstance(value, (list, tuple)):
                if any(not isinstance(v, str) for v in value):
                    errors.append(f"参数 {field['label']}({key}) 列表元素应全部为字符串")
            else:
                errors.append(f"参数 {field['label']}({key}) 应为字符串或字符串列表，收到 {type(value).__name__}")

        # 影响提示（切换前可预期）
        for impact in field.get("impacts", []):
            hints.append(f"[{field['label']}] {impact}")

    # 跨字段提示：提供了远程源但模式仍为 local -> 不会生效
    has_remote = any(
        params.get(k)
        for k in ("source_urls", "source_arxiv_ids", "source_dois")
    )
    if has_remote and (params.get("data_source") or "local") != "remote":
        warnings.append(
            "已提供 URL/arXiv/DOI 数据源，但 data_source=local：远程源不会生效，请切换为 remote"
        )

    # 未显式指定 embedding_model -> 按 provider 自动选择（见 embedding_recommender）
    if not params.get("embedding_model"):
        hints.append(
            "[Embedding 模型] 未显式指定：将按 provider 自动选择"
            "（服务商有 embedding API 用其最新策展模型；无则选 HuggingFace 下载量最高的"
            "多语言（含中文）模型并自动下载）；可用 embedding_model 参数手动覆盖"
        )

    return {"errors": errors, "warnings": warnings, "hints": hints}


def assert_schema_consistency() -> list[str]:
    """自检：所有 pydantic_path 都真实存在于 Settings model_fields（CLI/CI 用，防拼写错误）。"""
    problems: list[str] = []
    for g in GROUPS:
        for f in g["fields"]:
            if "pydantic_path" in f and not _path_exists(f["pydantic_path"]):
                problems.append(f"pydantic_path 不存在: {f['key']} -> {f['pydantic_path']}")
    return problems


if __name__ == "__main__":
    import json
    import sys

    payload = json.dumps(get_config_schema(), ensure_ascii=False, indent=2)
    if len(sys.argv) > 1:
        Path = __import__("pathlib").Path
        Path(sys.argv[1]).write_text(payload + "\n", encoding="utf-8")
        print(f"schema 已写入 {sys.argv[1]}")
    else:
        print(payload)
    problems = assert_schema_consistency()
    if problems:
        print("schema 一致性告警:", problems)
    else:
        print("schema 一致性检查通过")
