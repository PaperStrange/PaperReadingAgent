"""Verify agent flow (agent_query, fake agent) + translate endpoint with DeepSeek."""
import asyncio
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "paper-qa-script"))
from provider_config import get_provider_config  # noqa: E402

# 密钥由 provider_config 解析（专属 key 优先，回退通用 OPENAI_API_KEY / .env）
os.environ["OPENAI_API_KEY"] = get_provider_config()["api_key"]


async def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "backend_main",
        ROOT
        / "paper-qa-script"
        / "reactflow-paperqa-prototype"
        / "backend"
        / "main.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    params = {
        "api_key": os.environ["OPENAI_API_KEY"],
        "api_base": "https://api.deepseek.com",
        "model": "openai/deepseek-v4-flash",
        "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
        "paper_directory": str(ROOT / "data" / "pdf"),
        "index_name": "verify_e2e_index",  # reuse the index built by E2E
        "embedding_batch_size": 10,
        "chunk_chars": 5000,
        "chunk_overlap": 250,
        "temperature": 0.1,
    }
    settings = mod.build_settings(params)

    # 1) translate endpoint (LLM only)
    print("== translate (direct model call) ==", flush=True)
    llm = settings.get_llm()
    from aviary.core import Message

    r = await llm.call_single(
        messages=[Message(content="Translate to Chinese: PaperQA2 performs retrieval-augmented generation.")]
    )
    print("translated:", repr((r.text or "")[:120]), flush=True)

    # 2) agent flow with fake agent
    print("\n== agent_query (fake agent) ==", flush=True)
    from paperqa.agents.main import agent_query

    resp = await agent_query(
        "What is PaperQA2?",
        settings=settings,
        agent_type="fake",
    )
    print("status:", resp.status, flush=True)
    print("answer:", (resp.session.answer or "")[:300], flush=True)
    print("contexts:", len(resp.session.contexts or []), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
