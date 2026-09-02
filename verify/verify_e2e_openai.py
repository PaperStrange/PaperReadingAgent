"""End-to-end verification: OpenAI as provider + embedding model (user-requested, 2026-08-30；TG-4 起走共享基座).

Phase 1 — OpenAI-only full pipeline（真实 OpenAI API）：
  provider=openai（gpt-4o-mini 主 LLM + 视觉增强/证据摘要），embedding=text-embedding-3-large（OpenAI API 向量）。
Phase 2 — 双 provider 共存切换：同一后端进程内 config(deepseek) → config(openai) → evidence → answer，
  验证 make_settings 不再把 deepseek key 污染进 OPENAI_API_KEY（否则 openai 段会 401）。

TG-4 修复：config 恒显式携带 provider/api_base/model/vision_model（1.46——此前缺 vision_model，
vision 会回落默认服务商的视觉模型）。

Prereqs:
  - paper-qa-script/.env 或环境变量含 OPENAI_API_KEY（真实 OpenAI key）与 DEEPSEEK_API_KEY
  - 联网（api.openai.com + api.deepseek.com）
Run:
  .venv\\Scripts\\python.exe verify\\verify_e2e_openai.py [--keep-server]
"""
from __future__ import annotations
VERIFY_META = {'features': 'OpenAI provider+embedding 全流程 + 同进程 deepseek→openai 切换隔离回归', 'tier': 'network', 'providers': ['openai', 'deepseek'], 'est_seconds': 150, 'est_cost_cny': 1.0, 'routes': ['/api/new_session', '/api/run_step', '/api/stream/{session_id}/{run_id}', '/api/session_records/{session_id}', '/api/reset_session'], 'requires': ['keys', 'network', 'balance']}

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
PAPER_DIR = ROOT / "data" / "pdf"
OUT = ROOT / "verify" / "verify_e2e_openai_result.json"
SERVER_LOG = ROOT / "verify" / "verify_e2e_openai_server.log"
QUESTION = "What is PaperQA2 and what are its main components?"

sys.path.insert(0, str(ROOT / "paper-qa-script"))
from provider_config import get_provider_config  # noqa: E402

from e2e_common import (  # noqa: E402
    PORT,
    build_config_params,
    dump_log_tail,
    full_pipeline,
    make_cfg,
    start_backend,
    step,
    stop_backend,
    wait_healthy,
    write_results,
)

OAI = get_provider_config("openai")
DEEP = get_provider_config("deepseek")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    if not OAI.get("api_key"):
        print("ERR: OPENAI_API_KEY not found in .env / environment")
        return 2
    if not DEEP.get("api_key"):
        print("WARN: DEEPSEEK_API_KEY not found; Phase 2 (mixed switch) will be skipped")

    server = start_backend(BACKEND, SERVER_LOG, ROOT)
    if not wait_healthy(server, SERVER_LOG):
        return 3

    import httpx

    base = f"http://127.0.0.1:{PORT}"
    results: dict[str, object] = {}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            # ---- Phase 1：OpenAI-only 全流程 ----
            print("\n== Phase 1: OpenAI provider + OpenAI embedding, full pipeline ==")
            sink1: dict[str, object] = {}
            answer = await full_pipeline(
                client, base,
                run_id="verify-e2e-openai",
                cfg=make_cfg(OAI),
                paper_dir=PAPER_DIR,
                index_name="verify_e2e_openai_index",
                question=QUESTION,
                sink=sink1,
            )
            results["phase1"] = {"status": "PASS", "answer_chars": len(answer)}

            # ---- Phase 2：双 provider 共存切换（key 隔离） ----
            if DEEP.get("api_key"):
                print("\n== Phase 2: deepseek config then switch back to openai (key isolation) ==")
                sid = (await client.post(f"{base}/api/new_session")).json()["session_id"]
                await step(client, base, sid, "verify-e2e-openai", "config",
                           build_config_params(make_cfg(DEEP), PAPER_DIR, "verify_e2e_openai_index"))
                await step(client, base, sid, "verify-e2e-openai", "config",
                           build_config_params(make_cfg(OAI), PAPER_DIR, "verify_e2e_openai_index"))
                ev2 = await step(client, base, sid, "verify-e2e-openai", "evidence", {"question": QUESTION})
                ctx2 = ev2["output"].get("context_ids") or []
                ans2 = await step(client, base, sid, "verify-e2e-openai", "answer", {})
                answer2 = (ans2["output"] or {}).get("answer") or ""
                print(f"[ok] mixed-switch answer chars: {len(answer2)} contexts={len(ctx2)}")
                if len(answer2) < 20:
                    raise RuntimeError("mixed-provider switch answer too short")
                results["phase2"] = {"status": "PASS", "answer_chars": len(answer2)}
            else:
                results["phase2"] = {"status": "SKIPPED", "reason": "no DEEPSEEK_API_KEY"}

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
