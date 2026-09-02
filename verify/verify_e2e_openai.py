"""End-to-end verification: OpenAI as provider + embedding model (user-requested, 2026-08-30).



Phase 1 — OpenAI-only full pipeline（真实 OpenAI API）：

  provider=openai（gpt-4o-mini 主 LLM + 视觉增强/证据摘要），embedding=text-embedding-3-large（OpenAI API 向量）。

Phase 2 — 双 provider 共存切换：同一后端进程内 config(deepseek) → config(openai) → evidence → answer，

  验证 make_settings 不再把 deepseek key 污染进 OPENAI_API_KEY（否则 openai 段会 401）。



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

import json

import os

import subprocess

import sys

import time

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"

PAPER_DIR = ROOT / "data" / "pdf"

OUT = ROOT / "verify" / "verify_e2e_openai_result.json"

SERVER_LOG = ROOT / "verify" / "verify_e2e_openai_server.log"

PORT = 8787



sys.path.insert(0, str(ROOT / "paper-qa-script"))

from provider_config import get_provider_config, _load_dotenv  # noqa: E402



_load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY") or ""

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY") or ""



OPENAI_CFG = {

    "provider": "openai",                 # gpt-4o-mini（主 LLM / 视觉 / 证据摘要）

    "embedding_model": "text-embedding-3-large",  # OpenAI API 向量（3072 维）

    "paper_directory": str(PAPER_DIR),

    "index_name": "verify_e2e_openai_index",

    "embedding_batch_size": 10,

    "chunk_chars": 5000,

    "chunk_overlap": 250,

    "temperature": 0.1,

}

DEEPSEEK_CFG = {

    "provider": "deepseek",

    "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",

    "paper_directory": str(PAPER_DIR),

    "index_name": "verify_e2e_openai_index",

}

QUESTION = "What is PaperQA2 and what are its main components?"





async def main() -> int:

    ap = argparse.ArgumentParser()

    ap.add_argument("--keep-server", action="store_true")

    args = ap.parse_args()



    if not OPENAI_KEY:

        print("ERR: OPENAI_API_KEY not found in .env / environment")

        return 2

    if not DEEPSEEK_KEY:

        print("WARN: DEEPSEEK_API_KEY not found; Phase 2 (mixed switch) will be skipped")



    server = subprocess.Popen(

        [sys.executable, str(BACKEND)],

        cwd=str(ROOT),

        stdout=open(SERVER_LOG, "w", encoding="utf-8"),

        stderr=subprocess.STDOUT,

        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},

    )

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

            print(f"[ok] session {sid}")



            async def step(name: str, params: dict) -> dict:

                t0 = time.perf_counter()

                resp = await client.post(

                    f"{base}/api/run_step",

                    json={"session_id": sid, "run_id": "verify-e2e-openai",

                          "step": name, "params": params, "upstream": {}},

                )

                data = resp.json()

                dt = time.perf_counter() - t0

                ok = bool(data.get("ok"))

                print(

                    f"[{'ok' if ok else 'ERR'}] {name}: {dt:.1f}s "

                    f"error={data.get('error')}"

                )

                if not ok:

                    raise RuntimeError(f"{name} failed: {data.get('error')}")

                return data



            # ---- Phase 1：OpenAI-only 全流程 ----

            print("\n== Phase 1: OpenAI provider + OpenAI embedding, full pipeline ==")

            await step("config", dict(OPENAI_CFG))

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

            print(f"[ok] answer chars: {len(answer)}")

            print("---- ANSWER (first 300 chars) ----")

            print(answer[:300])

            if len(answer) < 20:

                raise RuntimeError("answer too short, OpenAI pipeline did not really answer")

            results["phase1"] = {"status": "PASS", "answer_chars": len(answer)}



            # ---- Phase 2：双 provider 共存切换（deepseek config → openai config → evidence/answer） ----

            if DEEPSEEK_KEY:

                print("\n== Phase 2: deepseek config then switch back to openai (key isolation) ==")

                await step("config", dict(DEEPSEEK_CFG))

                await step("config", dict(OPENAI_CFG))

                # docs 仍为 Phase 1 的 openai 向量；evidence/answer 用 openai key 走 OpenAI 端点

                ev2 = await step("evidence", {"question": QUESTION})

                ctx2 = ev2["output"].get("context_ids") or []

                ans2 = await step("answer", {})

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

