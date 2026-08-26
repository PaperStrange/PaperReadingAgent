"""统一模型服务商配置：DeepSeek / DashScope / OpenAI 三选一。

用法：
  1) 环境变量 PAPERQA_PROVIDER=deepseek|dashscope|openai 选择服务商（默认 deepseek）。
  2) 密钥按以下顺序读取：
     - 服务商专属环境变量（DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / OPENAI_API_KEY）
     - 通用 OPENAI_API_KEY
     - 本地 paper-qa-script/.env 文件
  3) 也可在调用时显式传入 provider 参数，或在 config 节点覆盖 api_base/model/embedding_model。
"""
from __future__ import annotations

import os
from pathlib import Path

PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "api_base": "https://api.deepseek.com",
        "model": "openai/deepseek-v4-flash",           # 可选 deepseek-v4-pro
        "vision_model": "openai/deepseek-v4-flash-vision-exp",  # 图片增强/证据摘要
        "embedding": "st-multi-qa-MiniLM-L6-cos-v1",   # 本地向量，无需 key
        "embedding_local": True,
        "key_envs": ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": True,                     # DeepSeek 思考模式需关闭以支持多轮工具调用
    },
    "dashscope": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "openai/qwen-omni-turbo",             # 或 openai/qwen3-max
        "vision_model": "openai/qwen-omni-turbo",
        "embedding": "openai/text-embedding-v4",
        "embedding_local": False,
        "key_envs": ("DASHSCOPE_API_KEY", "OPENAI_API_KEY"),
        "thinking_disabled": False,
    },
    "openai": {
        "api_base": None,                              # 使用 OpenAI 官方默认端点
        "model": "gpt-4o-mini",
        "vision_model": "gpt-4o-mini",
        "embedding": "text-embedding-3-small",
        "embedding_local": False,
        "key_envs": ("OPENAI_API_KEY",),
        "thinking_disabled": False,
    },
}

# Windows 仓库默认 deepseek；macOS 仓库默认 dashscope（各自保持一致行为）
DEFAULT_PROVIDER = os.getenv("PAPERQA_PROVIDER", "deepseek").lower()


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


def resolve_key(provider: str) -> str:
    _load_dotenv()
    for env_name in PROVIDERS[provider]["key_envs"]:
        key = os.getenv(env_name)
        if key:
            return key
    return os.getenv("OPENAI_API_KEY", "")


def get_provider_config(provider: str | None = None) -> dict:
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(
            f"未知服务商 {provider!r}，可选值：{sorted(PROVIDERS)}。"
            f"请设置 PAPERQA_PROVIDER 环境变量或传入 provider 参数。"
        )
    cfg = dict(PROVIDERS[provider])
    cfg["provider"] = provider
    cfg["api_key"] = resolve_key(provider)
    return cfg
