"""验证 LLM 服务商切换功能（deepseek / dashscope / openai）。

覆盖：
  1) provider_config 配置解析（三服务商的模型/向量化/api_base）
  2) 密钥解析优先级（DEEPSEEK/DASHSCOPE/OPENAI_API_KEY 各取各的）
  3) 后端 build_settings 对三服务商生成正确 Settings
  4) 实际连通性：deepseek 用真实 key 应成功；dashscope/openai 用占位 key
     应"到达各自端点并返回该端点的错误"（证明 api_base 路由正确，即使 key 无效）。

运行：
  .venv\\Scripts\\python.exe verify\\verify_provider_switch.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "paper-qa-script"))

# Windows GBK 控制台打印中文会乱码，强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from provider_config import PROVIDERS, get_provider_config, _load_dotenv  # noqa: E402


async def _completion(model: str, api_base: str | None, api_key: str) -> tuple[str, str]:
    import litellm

    try:
        r = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            api_base=api_base,
            api_key=api_key,
            max_tokens=8,
            timeout=30,
        )
        return "SUCCESS", (r.choices[0].message.content or "").strip()[:60]
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        # 只留关键错误信息，脱敏 key
        for marker in ("Error code:", "'message':", "message="):
            idx = msg.find(marker)
            if idx >= 0:
                msg = msg[idx:]
                break
        return "ERR", msg[:140].replace(api_key, "sk-***")


async def main() -> int:
    print("== 1) provider_config 配置解析 ==")
    for p in sorted(PROVIDERS):
        c = get_provider_config(p)
        print(
            f"  {p:10s} model={c['model']:40s} vision={c['vision_model']:40s} "
            f"emb={c['embedding']:36s} local={c['embedding_local']} base={c['api_base']}"
        )

    print("\n== 2) 密钥解析优先级（各服务商取各自的专属 key）==")
    os.environ["DEEPSEEK_API_KEY"] = "sk-TEST-deepseek"
    os.environ["DASHSCOPE_API_KEY"] = "sk-TEST-dashscope"
    os.environ["OPENAI_API_KEY"] = "sk-TEST-openai"
    for p in sorted(PROVIDERS):
        print(f"  {p:10s} -> {get_provider_config(p)['api_key']}")
    for k in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(k, None)

    print("\n== 3) 后端 build_settings 对三服务商 ==")
    spec = importlib.util.spec_from_file_location(
        "backend_main",
        ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py",
    )
    m = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    for p in sorted(PROVIDERS):
        s = m.build_settings(
            {"provider": p, "api_key": "dummy", "paper_directory": str(ROOT / "data" / "pdf")}
        )
        print(f"  {p:10s} llm={s.llm:40s} emb={s.embedding:36s} summary={s.summary_llm}")

    print("\n== 4) 实际连通性（deepseek 用真实 key；dashscope/openai 用占位 key 验证路由）==")
    # 第 3 步 build_settings 会污染 OPENAI_API_KEY，先清除再从 .env 重新加载真实 key
    for k in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(k, None)
    _load_dotenv()
    real_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    for p in sorted(PROVIDERS):
        c = get_provider_config(p)
        key = c["api_key"] if p == "deepseek" else "sk-invalid-placeholder"
        status, msg = await _completion(c["model"], c["api_base"], key)
        print(f"  {p:10s} {status:7s} {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
