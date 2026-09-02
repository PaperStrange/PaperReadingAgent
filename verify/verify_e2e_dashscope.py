"""dashscope 全流程端到端验证（用户验收项，2026-08-31；TG-4 起走共享基座 e2e_common）。

Phase 1（dashscope）：config -> load_index -> retrieve -> parse_chunk_embed -> evidence -> answer
  - LLM openai/qwen-omni-turbo、Embedding openai/text-embedding-v4（DashScope embedding API）、api_base compatible-mode
Phase 2（deepseek，同进程切换隔离回归，3-LEARNED 1.27 的 dashscope 方向）：
  同一后端进程内新会话再跑 deepseek 全流程（LLM deepseek-v4-flash + 本地 st- 向量）——
  若 make_settings 曾把解析出的 key 写回 OPENAI_API_KEY，Phase 2 会因 key 污染 401/路由错而失败。

Prereqs: .venv；paper-qa-script/.env 含 DASHSCOPE_API_KEY 与 DEEPSEEK_API_KEY（真实 key，本脚本不打印）。
Run: .venv\\Scripts\\python.exe verify\\verify_e2e_dashscope.py [--keep-server]
"""
from __future__ import annotations
VERIFY_META = {'features': 'dashscope 全链路 6 步 + 同进程 deepseek 切换隔离回归', 'tier': 'network', 'providers': ['dashscope', 'deepseek'], 'est_seconds': 150, 'est_cost_cny': 0.5, 'routes': ['/api/new_session', '/api/run_step', '/api/stream/{session_id}/{run_id}', '/api/session_records/{session_id}', '/api/reset_session'], 'requires': ['keys', 'network']}

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
PAPER_DIR = ROOT / "data" / "pdf"
OUT = ROOT / "verify" / "verify_e2e_dashscope_result.json"
SERVER_LOG = ROOT / "verify" / "verify_e2e_dashscope_server.log"
QUESTION = "What is PaperQA2 and what are its main components?"

sys.path.insert(0, str(ROOT / "paper-qa-script"))
from provider_config import get_provider_config  # noqa: E402

from e2e_common import (  # noqa: E402
    PORT,
    dump_log_tail,
    full_pipeline,
    make_cfg,
    start_backend,
    stop_backend,
    wait_healthy,
    write_results,
)

DS = get_provider_config("dashscope")
DEEP = get_provider_config("deepseek")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    if not DS.get("api_key"):
        print("ERR: DASHSCOPE_API_KEY not found（检查 paper-qa-script/.env）")
        return 2
    if not DEEP.get("api_key"):
        print("ERR: DEEPSEEK_API_KEY not found（检查 paper-qa-script/.env）")
        return 2

    server = start_backend(BACKEND, SERVER_LOG, ROOT)
    if not wait_healthy(server, SERVER_LOG):
        return 3

    import httpx

    base = f"http://127.0.0.1:{PORT}"
    results: dict[str, object] = {"phases": {}}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            for name, prov, idx in (
                ("dashscope", DS, "verify_e2e_dash_index"),
                ("deepseek-same-process", DEEP, "verify_e2e_deep_index"),
            ):
                print(f"\n===== Phase {name} =====")
                sink: dict[str, object] = {}
                await full_pipeline(
                    client, base,
                    run_id=f"verify-e2e-{name}",
                    cfg=make_cfg(prov),
                    paper_dir=PAPER_DIR,
                    index_name=idx,
                    question=QUESTION,
                    sink=sink,
                )
                sink["status"] = "PASS"
                results["phases"][name] = sink  # type: ignore[index]
        results["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        results["status"] = f"FAIL: {type(exc).__name__}: {exc}"
        print(f"\n[FAIL] {results['status']}")
        dump_log_tail(SERVER_LOG)
    finally:
        stop_backend(server, args.keep_server)

    write_results(OUT, results)
    return 0 if results.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
