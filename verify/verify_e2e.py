"""End-to-end verification of the ported codebase on Windows.

Drives the real FastAPI backend (backend/main.py) through the full 6-step pipeline
with a real DeepSeek API (chat + vision) and local SentenceTransformer embeddings:
  config -> load_index -> retrieve -> parse_chunk_embed -> evidence -> answer

Prereqs:
  - .venv with paper-qa + fastapi/uvicorn + sentence-transformers (see docs/1-WORKFLOW.MD)
  - OPENAI_API_KEY env var set to the DeepSeek key
Run:
  .venv\\Scripts\\python.exe verify\\verify_e2e.py [--keep-server]
"""

from __future__ import annotations
VERIFY_META = {'features': 'deepseek 全链路 6 步（LLM+vision + 本地 st- 向量）', 'tier': 'network', 'providers': ['deepseek'], 'est_seconds': 120, 'est_cost_cny': 0.3, 'routes': ['/api/new_session', '/api/run_step', '/api/stream/{session_id}/{run_id}', '/api/session_records/{session_id}', '/api/reset_session'], 'requires': ['keys', 'network']}

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
PAPER_DIR = ROOT / "data" / "pdf"
OUT = ROOT / "verify" / "verify_e2e_result.json"
SERVER_LOG = ROOT / "verify" / "verify_e2e_server.log"
PORT = 8787

sys.path.insert(0, str(ROOT / "paper-qa-script"))
from provider_config import get_provider_config  # noqa: E402

DASH_KEY = get_provider_config()["api_key"]
# [macOS] 原验证使用 DashScope：API_BASE=dashscope compatible-mode, MODEL=openai/qwen-omni-turbo,
#         EMB=openai/text-embedding-v4（账户欠费后不可用）
# Windows 验证：DeepSeek LLM + 本地 sentence-transformers 向量化
API_BASE = "https://api.deepseek.com"
MODEL = "openai/deepseek-v4-flash"
EMB = "st-multi-qa-MiniLM-L6-cos-v1"
QUESTION = "What is PaperQA2 and what are its main components?"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    if not DASH_KEY:
        print("ERR: set OPENAI_API_KEY env var first")
        return 2

    server = subprocess.Popen(
        [sys.executable, str(BACKEND)],
        cwd=str(ROOT),
        stdout=open(SERVER_LOG, "w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    # wait for health
    import httpx

    base = f"http://127.0.0.1:{PORT}"
    for _ in range(60):
        try:
            r = httpx.get(f"{base}/api/health", timeout=3)
            if r.status_code == 200 and r.json().get("status") == "ok":
                break
        except Exception:
            time.sleep(1)
    else:
        print("ERR: backend did not become healthy")
        if SERVER_LOG.exists():
            print(SERVER_LOG.read_text(encoding="utf-8", errors="replace")[-4000:])
        server.kill()
        return 3
    print("[ok] backend healthy")

    results: dict[str, object] = {}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            sid = (await client.post(f"{base}/api/new_session")).json()["session_id"]
            results["session_id"] = sid
            print(f"[ok] session {sid}")

            async def step(name: str, params: dict, upstream: dict | None = None) -> dict:
                t0 = time.perf_counter()
                resp = await client.post(
                    f"{base}/api/run_step",
                    json={
                        "session_id": sid,
                        "run_id": "verify-e2e",
                        "step": name,
                        "params": params,
                        "upstream": upstream or {},
                    },
                )
                data = resp.json()
                dt = time.perf_counter() - t0
                ok = bool(data.get("ok"))
                print(
                    f"[{'ok' if ok else 'ERR'}] {name}: {dt:.1f}s "
                    f"funcs={len(data.get('function_trace') or [])} "
                    f"error={data.get('error')}"
                )
                results[name] = {
                    "duration_s": round(dt, 2),
                    "ok": ok,
                    "output": data.get("output"),
                    "error": data.get("error"),
                    "function_trace_count": len(data.get("function_trace") or []),
                }
                if not ok:
                    raise RuntimeError(f"{name} failed: {data.get('error')}")
                return data

            await step(
                "config",
                {
                    "api_key": DASH_KEY,
                    "api_base": API_BASE,
                    "model": MODEL,
                    "embedding_model": EMB,
                    "paper_directory": str(PAPER_DIR),
                    "index_name": "verify_e2e_index",
                    "embedding_batch_size": 10,
                    "chunk_chars": 5000,
                    "chunk_overlap": 250,
                    "temperature": 0.1,
                },
            )
            await step("load_index", {"build": True})

            ret = await step("retrieve", {"query": QUESTION, "top_n": 3})
            cands = ret["output"].get("candidate_paths") or []
            print(f"[ok] candidates: {cands}")

            await step("parse_chunk_embed", {"candidate_paths": cands})
            ev = await step("evidence", {"question": QUESTION})
            ctx = ev["output"].get("context_ids") or []
            print(f"[ok] evidence contexts: {len(ctx)}")

            ans = await step("answer", {})
            answer = (ans["output"] or {}).get("answer") or ""
            refs = (ans["output"] or {}).get("references") or ""
            print(f"[ok] answer chars: {len(answer)}")
            print("---- ANSWER (first 400 chars) ----")
            print(answer[:400])
            print("---- REFERENCES (first 200 chars) ----")
            print(refs[:200])

            if len(answer) < 20:
                raise RuntimeError("answer too short, pipeline did not really answer")
        results["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        results["status"] = f"FAIL: {type(exc).__name__}: {exc}"
        print(f"\n[FAIL] {results['status']}")
        if SERVER_LOG.exists():
            print("\n===== backend server log (tail) =====")
            print(SERVER_LOG.read_text(encoding="utf-8", errors="replace")[-6000:])
    finally:
        if not args.keep_server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[written] {OUT}")
    return 0 if results.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
