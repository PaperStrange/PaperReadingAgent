"""统一模型服务商配置：DeepSeek / DashScope / OpenAI / OpenRouter + 用户自定义。

用法：
  1) 环境变量 PAPERQA_PROVIDER=deepseek|dashscope|openai|openrouter|<自定义名> 选择服务商。
  2) 密钥按以下顺序读取：
     - 服务商专属环境变量（DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY）
     - 通用 OPENAI_API_KEY
     - 本地 paper-qa-script/.env 文件
  3) 也可在调用时显式传入 provider 参数，或在 config 节点覆盖 api_base/model/embedding_model。
  4) 扩展 provider（Sprint-4 US-4.3）：
     - 内置：deepseek / dashscope / openai / openrouter（OpenRouter 网关，api_base https://openrouter.ai/api/v1）
     - 用户自定义：`paper-qa-script/providers.json`（gitignored，模板见 providers.example.json）
       或环境变量 `PAPERQA_PROVIDERS_JSON`（JSON 字符串，优先级最高，覆盖内置同名项）。
     自定义条目字段：api_base, model, vision_model, embedding, embedding_local,
     has_embedding_api, key_envs(列表), thinking_disabled。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

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
        "model": "openai/qwen-omni-turbo",             # 或 openai/qwen3-max
        "vision_model": "openai/qwen-omni-turbo",
        "embedding": "openai/text-embedding-v4",       # 最新策展（2026-08）
        "embedding_local": False,
        "has_embedding_api": True,
        "key_envs": ("DASHSCOPE_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": False,
    },
    "openai": {
        "api_base": None,                              # 使用 OpenAI 官方默认端点
        "model": "gpt-4o-mini",
        "vision_model": "gpt-4o-mini",
        "embedding": "text-embedding-3-large",         # 最新策展（2026-08；更省可改 text-embedding-3-small）
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

# 自定义 provider 条目的默认值（缺省字段补齐）
_CUSTOM_DEFAULTS: dict = {
    "api_base": None,
    "model": "",
    "vision_model": "",
    "embedding": "st-multi-qa-MiniLM-L6-cos-v1",
    "embedding_local": True,
    "has_embedding_api": False,
    "key_envs": ("OPENAI_API_KEY",),
    "thinking_disabled": False,
}


def _load_custom_providers() -> dict[str, dict]:
    """加载用户自定义 provider：providers.json（gitignored）< PAPERQA_PROVIDERS_JSON（环境变量）。"""
    custom: dict[str, dict] = {}
    json_file = Path(__file__).resolve().parent / "providers.json"
    if json_file.exists():
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                custom.update(data)
        except Exception:
            pass
    env_raw = os.environ.get("PAPERQA_PROVIDERS_JSON", "").strip()
    if env_raw:
        try:
            data = json.loads(env_raw)
            if isinstance(data, dict):
                custom.update(data)
        except Exception:
            pass
    return custom


def _normalize_entry(name: str, entry: dict) -> dict:
    cfg = dict(_CUSTOM_DEFAULTS)
    cfg.update({k: v for k, v in entry.items() if k in _CUSTOM_DEFAULTS})
    if not cfg["model"]:
        raise ValueError(f"自定义 provider {name!r} 缺少必填字段 model")
    if isinstance(cfg["key_envs"], str):
        cfg["key_envs"] = (cfg["key_envs"],)
    return cfg


def get_providers() -> dict[str, dict]:
    """内置 + 自定义 provider 注册表（自定义可覆盖内置同名项）。"""
    registry: dict[str, dict] = {k: dict(v) for k, v in PROVIDERS.items()}
    for name, entry in _load_custom_providers().items():
        if not isinstance(entry, dict):
            continue
        registry[str(name).strip().lower()] = _normalize_entry(str(name).strip().lower(), entry)
    return registry


def list_providers_safe() -> list[dict]:
    """provider 列表 + 默认值（**不含密钥**，供 /api/providers 与前端下拉）。"""
    out: list[dict] = []
    for name, cfg in sorted(get_providers().items()):
        out.append(
            {
                "name": name,
                "api_base": cfg.get("api_base"),
                "model": cfg.get("model"),
                "vision_model": cfg.get("vision_model"),
                "embedding": cfg.get("embedding"),
                "has_embedding_api": bool(cfg.get("has_embedding_api")),
                "builtin": name in PROVIDERS,
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
            f"内置：{sorted(PROVIDERS)}；自定义见 providers.json / PAPERQA_PROVIDERS_JSON。"
        )
    cfg = dict(registry[provider])
    cfg["provider"] = provider
    cfg["api_key"] = resolve_key(provider, registry)
    return cfg
