"""统一模型服务商配置：DeepSeek / DashScope / OpenAI / OpenRouter + 用户自定义。

**Sprint-16 F-AC8：一 provider 一文件**（`paper-qa-script/providers/<name>.json`）——
切换 provider 只加载对应文件；文件由首轮/定时官网调研（`scripts/refresh-providers.py`）刷新。

加载顺序（后者覆盖前者同名项）：
  1) 代码内 `PROVIDERS`：**引导兜底**（providers/ 目录缺失/损坏时保证应用可用；与内置文件内容一致）
  2) `providers/*.json`：**主来源**（逐文件 schema 校验；单个文件非法只跳过该文件并记录原因，不拖垮注册表）
  3) `providers.json`（旧版单文件，gitignored，模板 providers.example.json）：用户自定义/覆盖，兼容保留
  4) 环境变量 `PAPERQA_PROVIDERS_JSON`（JSON 字符串，优先级最高）

密钥顺序：服务商专属环境变量（key_envs）→ 通用 OPENAI_API_KEY → `paper-qa-script/.env`。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PROVIDERS_DIR = Path(__file__).resolve().parent / "providers"
LEGACY_PROVIDERS_FILE = Path(__file__).resolve().parent / "providers.json"

# 引导兜底（providers/ 缺失时仍可运行；字段与 providers/<name>.json 一致）
PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "api_base": "https://api.deepseek.com",
        "model": "openai/deepseek-v4-flash",           # 可选 deepseek-v4-pro
        "vision_model": "openai/deepseek-v4-flash-vision-exp",  # 图片增强/证据摘要
        "embedding": "st-multi-qa-MiniLM-L6-cos-v1",   # 兜底本地向量（自动推荐时会被 HF 热门多语言模型替换）
        "embedding_local": True,
        "has_embedding_api": False,                    # DeepSeek 无 embedding API → 默认走 HF 本地模型
        "key_envs": ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": True,                     # DeepSeek 思考模式需关闭以支持多轮工具调用
    },
    "dashscope": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "openai/qwen3.5-omni-plus",           # 2026-09 官网调研更新（原 qwen-omni-turbo）
        "vision_model": "openai/qwen3.5-omni-plus",
        "embedding": "openai/text-embedding-v4",       # 官网已核实（run-2026-09-12-provider-refresh-001）
        "embedding_local": False,
        "has_embedding_api": True,
        "key_envs": ("DASHSCOPE_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": False,
    },
    "openai": {
        "api_base": None,                              # 使用 OpenAI 官方默认端点
        "model": "gpt-4o-mini",
        "vision_model": "gpt-4o-mini",
        "embedding": "text-embedding-3-large",         # 更省可改 text-embedding-3-small
        "embedding_local": False,
        "has_embedding_api": True,
        "key_envs": ("OPENAI_API_KEY",),
        "thinking_disabled": False,
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",    # OpenRouter 通用网关（支持上百家模型）
        "model": "openrouter/auto",                    # 智能路由；指定模型如 openrouter/anthropic/claude-sonnet-4
        "vision_model": "",                            # 留空 -> 回落使用 model（engine 兜底）
        "embedding": "st-multi-qa-MiniLM-L6-cos-v1",   # OpenRouter 无 embedding API，兜底本地模型
        "embedding_local": True,
        "has_embedding_api": False,
        "key_envs": ("OPENROUTER_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": False,
    },
}

# Windows 仓库默认 deepseek；macOS 仓库默认 dashscope（各自保持一致行为）
DEFAULT_PROVIDER = os.getenv("PAPERQA_PROVIDER", "deepseek").lower()

# provider 条目字段全集与默认值（缺省字段补齐）
_ENTRY_DEFAULTS: dict = {
    "api_base": None,
    "model": "",
    "vision_model": "",
    "embedding": "st-multi-qa-MiniLM-L6-cos-v1",
    "embedding_local": True,
    "has_embedding_api": False,
    "key_envs": ("OPENAI_API_KEY",),
    "thinking_disabled": False,
}

# 文件内不允许出现在配置顶层的元数据键（拆分出来单独保存，不进运行配置）
_META_KEY = "meta"


def normalize_entry(name: str, entry: dict) -> dict:
    """规范化单个 provider 条目：补齐默认值、key_envs 转元组、校验必填字段。"""
    if not isinstance(entry, dict):
        raise ValueError(f"provider {name!r} 条目必须是对象")
    meta = entry.get(_META_KEY) if isinstance(entry.get(_META_KEY), dict) else {}
    cfg = dict(_ENTRY_DEFAULTS)
    cfg.update({k: v for k, v in entry.items() if k in _ENTRY_DEFAULTS})
    if not cfg["model"]:
        raise ValueError(f"provider {name!r} 缺少必填字段 model")
    if isinstance(cfg["key_envs"], str):
        cfg["key_envs"] = (cfg["key_envs"],)
    cfg["key_envs"] = tuple(str(x) for x in cfg["key_envs"])
    cfg["meta"] = dict(meta)
    return cfg


def load_provider_files(directory: Path | None = None) -> tuple[dict[str, dict], list[str]]:
    """读 `providers/*.json`（主来源）。返回 (注册表, 问题列表)；单文件非法只跳过该文件。"""
    directory = directory or PROVIDERS_DIR
    registry: dict[str, dict] = {}
    problems: list[str] = []
    if not directory.is_dir():
        return registry, [f"目录不存在: {directory}"]
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{path.name}: JSON 解析失败（{type(exc).__name__}: {exc}）")
            continue
        if not isinstance(data, dict):
            problems.append(f"{path.name}: 顶层必须是对象")
            continue
        name = str(data.get("name") or path.stem).strip().lower()
        if name != path.stem.lower():
            problems.append(f"{path.name}: name 字段（{name}）与文件名不一致")
            continue
        try:
            registry[name] = normalize_entry(name, data)
        except ValueError as exc:
            problems.append(f"{path.name}: {exc}")
    return registry, problems


def _load_legacy_custom() -> dict[str, dict]:
    """旧版单文件 providers.json（用户自定义）+ PAPERQA_PROVIDERS_JSON（env，优先级最高）。"""
    custom: dict[str, dict] = {}
    if LEGACY_PROVIDERS_FILE.exists():
        try:
            data = json.loads(LEGACY_PROVIDERS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                custom.update({str(k).strip().lower(): v for k, v in data.items()})
        except Exception:
            pass
    env_raw = os.environ.get("PAPERQA_PROVIDERS_JSON", "").strip()
    if env_raw:
        try:
            data = json.loads(env_raw)
            if isinstance(data, dict):
                custom.update({str(k).strip().lower(): v for k, v in data.items()})
        except Exception:
            pass
    return custom


def get_providers() -> dict[str, dict]:
    """合并注册表：代码兜底 < providers/*.json < 旧版 providers.json < env JSON。

    review 修正（Sprint-4 保留）：单个自定义条目非法**只跳过该条目**，
    不拖垮整个注册表（/api/providers 与所有 config 步骤保持可用）。
    """
    registry: dict[str, dict] = {k: dict(v) for k, v in PROVIDERS.items()}
    file_registry, _problems = load_provider_files()
    registry.update(file_registry)
    for name, entry in _load_legacy_custom().items():
        try:
            registry[str(name).strip().lower()] = normalize_entry(str(name).strip().lower(), entry)
        except ValueError:
            continue  # 非法自定义条目：跳过（请求该 provider 时会报"未知服务商"并列出可用项）
    return registry


def _source_map() -> dict[str, str]:
    """一次性算出各 provider 的生效来源（env > legacy > file > builtin），避免逐个 provider 重复读盘。"""
    env_names: set[str] = set()
    env_raw = os.environ.get("PAPERQA_PROVIDERS_JSON", "").strip()
    if env_raw:
        try:
            env_names = {str(k).strip().lower() for k in json.loads(env_raw)}
        except Exception:
            env_names = set()
    legacy_names: set[str] = set()
    if LEGACY_PROVIDERS_FILE.exists():
        try:
            legacy_names = {
                str(k).strip().lower()
                for k in json.loads(LEGACY_PROVIDERS_FILE.read_text(encoding="utf-8"))
            }
        except Exception:
            legacy_names = set()
    file_registry, _ = load_provider_files()
    out: dict[str, str] = {}
    for n in set(env_names) | set(legacy_names) | set(file_registry) | set(PROVIDERS):
        out[n] = (
            "env" if n in env_names
            else "legacy" if n in legacy_names
            else "file" if n in file_registry
            else "builtin"
        )
    return out


def provider_source(name: str, sources: dict[str, str] | None = None) -> str:
    """`name` 的生效来源（env / legacy / file / builtin / unknown）。

    可选 `sources`：传入 `_source_map()` 的结果以复用（列表场景避免 N 次读盘）。
    """
    mapping = sources if sources is not None else _source_map()
    return mapping.get(name.strip().lower(), "unknown")


def list_providers_safe() -> list[dict]:
    """provider 列表 + 默认值（**不含密钥**，供 /api/providers 与前端下拉）。"""
    out: list[dict] = []
    sources = _source_map()  # 一次算好来源，避免每个 provider 重复读盘
    for name, cfg in sorted(get_providers().items()):
        meta = cfg.get(_META_KEY) or {}
        out.append(
            {
                "name": name,
                "api_base": cfg.get("api_base"),
                "model": cfg.get("model"),
                "vision_model": cfg.get("vision_model"),
                "embedding": cfg.get("embedding"),
                "has_embedding_api": bool(cfg.get("has_embedding_api")),
                "builtin": name in PROVIDERS,
                "source": provider_source(name, sources),
                "fetched_at": meta.get("fetched_at"),
                "source_urls": list(meta.get("source_urls") or []),
            }
        )
    return out


def _load_dotenv() -> None:
    """读取 paper-qa-script/.env（bash 风格 export KEY=value），不覆盖已存在的环境变量。"""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def resolve_key(provider: str, registry: dict[str, dict] | None = None) -> str:
    _load_dotenv()
    registry = registry or get_providers()
    for env_name in registry[provider]["key_envs"]:
        key = os.getenv(env_name)
        if key:
            return key
    return os.getenv("OPENAI_API_KEY", "")


def get_provider_config(provider: str | None = None) -> dict:
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    registry = get_providers()
    if provider not in registry:
        raise ValueError(
            f"未知服务商 {provider!r}，可选值：{sorted(registry)}。"
            f"内置：{sorted(PROVIDERS)}；自定义见 providers/*.json、providers.json 或 PAPERQA_PROVIDERS_JSON。"
        )
    cfg = dict(registry[provider])
    cfg["provider"] = provider
    cfg["provider_source"] = provider_source(provider)
    cfg["api_key"] = resolve_key(provider, registry)
    return cfg
