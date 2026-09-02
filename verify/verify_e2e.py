"""End-to-end verification: deepseek provider, full 6-step pipeline（TG-4 起走共享基座 e2e_common）。

Prereqs:
  - .venv with paper-qa + fastapi/uvicorn + sentence-transformers (see docs/1-WORKFLOW.MD)
  - paper-qa-script/.env 含 DEEPSEEK_API_KEY
Run:
  .venv\\Scripts\\python.exe verify\\verify_e2e.py [--keep-server]
"""
from __future__ import annotations
VERIFY_META = {'features': 'deepseek 全链路 6 步（LLM+vision + 本地 st- 向量）', 'tier': 'network', 'providers': ['deepseek'], 'est_seconds': 120, 'est_cost_cny': 0.3, 'routes': ['/api/new_session', '/api/run_step', '/api/stream/{session_id}/{run_id}', '/api/session_records/{session_id}', '/api/reset_session'], 'requires': ['keys', 'network']}

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
PAPER_DIR = ROOT / "data" / "pdf"
OUT = ROOT / "verify" / "verify_e2e_result.json"
SERVER_LOG = ROOT / "verify" / "verify_e2e_server.log"
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

DEEP = get_provider_config("deepseek")
CFG = make_cfg(DEEP)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    if not CFG["api_key"]:
        print("ERR: DEEPSEEK_API_KEY not found（检查 paper-qa-script/.env）")
        return 2

    server = start_backend(BACKEND, SERVER_LOG, ROOT)
    if not wait_healthy(server, SERVER_LOG):
        return 3

    import httpx

    base = f"http://127.0.0.1:{PORT}"
    results: dict[str, object] = {}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            answer = await full_pipeline(
                client, base,
                run_id="verify-e2e",
                cfg=CFG,
                paper_dir=PAPER_DIR,
                index_name="verify_e2e_index",
                question=QUESTION,
                sink=results,
            )
            results["answer_chars"] = len(answer)
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
