"""验证 LLM 服务商切换功能（内置 deepseek / dashscope / openai / openrouter + 自定义）。

覆盖：
  1) provider_config 配置解析（全注册表 provider 的模型/向量化/api_base）
  2) 密钥解析优先级（DEEPSEEK/DASHSCOPE/OPENAI/OPENROUTER_API_KEY 各取各的）
  3) 后端 build_settings 对全注册表生成正确 Settings
  4) 实际连通性（Sprint-7 M5 升级为**路由实证断言**）：
     - deepseek 用真实 key 应 SUCCESS；
     - 其余内置 provider 用占位 key 应 ERR 且为**端点级错误**（非连接类错误），
       证明 api_base 路由正确（真实 key 实测为用户资源门控，见 README）；
     - 自定义 provider（PAPERQA_PROVIDERS_JSON）同样断言路由正确。

运行：
  .venv\\Scripts\\python.exe verify\\verify_provider_switch.py
前提：联网；deepseek 真实 key（.env 或 OPENAI_API_KEY）。
"""

from __future__ import annotations
VERIFY_META = {'features': 'provider 切换路由实证：内置 4 家 + 自定义（端点级拒绝断言）', 'tier': 'network', 'providers': ['deepseek', 'dashscope', 'openai', 'openrouter'], 'est_seconds': 30, 'est_cost_cny': 0.1, 'routes': ['/api/providers'], 'requires': ['keys', 'network']}

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

# 连接类错误标记：占位 key 打到错误端点/断网时会出现这类错误，不能作为"路由正确"的证据
_CONN_MARKERS = ("Connection error", "timed out", "getaddrinfo", "NameResolutionError", "connect")


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


def _assert_endpoint_error(p: str, status: str, msg: str) -> None:
    """路由实证：占位 key 必须拿到端点级拒绝（非连接类错误）。"""
    assert status == "ERR", f"{p}: 占位 key 应被端点拒绝，实际 {status}"
    assert msg, f"{p}: 错误信息为空"
    assert not any(m in msg for m in _CONN_MARKERS), f"{p}: 疑似连接类错误（端点不可达？）：{msg}"


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
    os.environ["OPENROUTER_API_KEY"] = "sk-TEST-openrouter"
    for p in sorted(PROVIDERS):
        print(f"  {p:10s} -> {get_provider_config(p)['api_key']}")
    for k in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        os.environ.pop(k, None)

    print("\n== 3) 后端 build_settings 对全注册表 provider ==")
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

    print("\n== 3b) make_settings 不污染 OPENAI_API_KEY（多 provider 共存回归，Sprint-7 修复）==")
    # 旧实现把解析出的 api_key 写回 OPENAI_API_KEY：先跑 deepseek 再切 openai 会拿到 deepseek key → 401
    sentinel = "sk-SENTINEL-openai"
    os.environ["OPENAI_API_KEY"] = sentinel
    m.build_settings(
        {"provider": "deepseek", "api_key": "sk-PLACEHOLDER-ds",
         "paper_directory": str(ROOT / "data" / "pdf")}
    )
    assert os.environ.get("OPENAI_API_KEY") == sentinel, (
        f"OPENAI_API_KEY 被 deepseek 配置污染：{os.environ.get('OPENAI_API_KEY')}"
    )
    assert get_provider_config("openai")["api_key"] == sentinel, (
        "resolve_key('openai') 未取 OPENAI_API_KEY 本身（污染未隔离）"
    )
    os.environ.pop("OPENAI_API_KEY", None)
    print("PASS: deepseek 配置后 OPENAI_API_KEY 未被覆盖；resolve_key('openai') 取到自身 key（隔离正确）")

    print("\n== 4) 实际连通性（deepseek 真实 key；其余占位 key 断言路由）==")
    # Sprint-7 修复后 make_settings 不再写 OPENAI_API_KEY（无污染）；仍清一遍并从 .env 重载真实 key 兜底
    for k in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        os.environ.pop(k, None)
    _load_dotenv()
    real_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    for p in sorted(PROVIDERS):
        c = get_provider_config(p)
        key = c["api_key"] if p == "deepseek" else "sk-invalid-placeholder"
        status, msg = await _completion(c["model"], c["api_base"], key)
        print(f"  {p:10s} {status:7s} {msg}")
        if p == "deepseek":
            assert status == "SUCCESS", f"deepseek 真实 key 应成功：{msg}"
        else:
            _assert_endpoint_error(p, status, msg)
    print("PASS: deepseek 真实 SUCCESS；dashscope/openai/openrouter 占位 key 端点级拒绝（路由正确）")

    print("\n== 5) 自定义 provider 路由实证（PAPERQA_PROVIDERS_JSON → api.deepseek.com）==")
    # 自定义条目指向 DeepSeek 端点：占位 key 应拿到 DeepSeek 的 401（证明自定义注册表 → litellm 路由正确）
    os.environ["PAPERQA_PROVIDERS_JSON"] = (
        '{"cust-test": {"api_base": "https://api.deepseek.com", "model": "openai/deepseek-v4-flash", "key_envs": ["OPENAI_API_KEY"]}}'
    )
    try:
        from provider_config import get_providers

        assert "cust-test" in get_providers(), "自定义 provider 未注册"
        c = get_provider_config("cust-test")
        status, msg = await _completion(c["model"], c["api_base"], "sk-invalid-placeholder")
        print(f"  cust-test {status:7s} {msg}")
        _assert_endpoint_error("cust-test", status, msg)
    finally:
        os.environ.pop("PAPERQA_PROVIDERS_JSON", None)
    print("PASS: 自定义 provider 占位 key 端点级拒绝（api_base 路由正确）")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
