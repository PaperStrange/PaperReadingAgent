"""dashscope 全流程端到端验证（用户验收项，2026-08-31）。



真实 FastAPI 后端跑完整 6 步流水线：

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

import json

import os

import subprocess

import sys

import time

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"

PAPER_DIR = ROOT / "data" / "pdf"

OUT = ROOT / "verify" / "verify_e2e_dashscope_result.json"

SERVER_LOG = ROOT / "verify" / "verify_e2e_dashscope_server.log"

PORT = 8787



sys.path.insert(0, str(ROOT / "paper-qa-script"))

from provider_config import get_provider_config  # noqa: E402



DS = get_provider_config("dashscope")

DEEP = get_provider_config("deepseek")

QUESTION = "What is PaperQA2 and what are its main components?"





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



    results: dict[str, object] = {"phases": {}}



    async def phase(name: str, cfg: dict, index_name: str) -> None:

        phase_res: dict[str, object] = {}

        async with httpx.AsyncClient(timeout=None) as client:

            sid = (await client.post(f"{base}/api/new_session")).json()["session_id"]

            phase_res["session_id"] = sid

            print(f"\n===== Phase {name}（session {sid}）=====")



            async def step(sname: str, params: dict, upstream: dict | None = None) -> dict:

                t0 = time.perf_counter()

                resp = await client.post(

                    f"{base}/api/run_step",

                    json={

                        "session_id": sid,

                        "run_id": f"verify-e2e-{name}",

                        "step": sname,

                        "params": params,

                        "upstream": upstream or {},

                    },

                )

                data = resp.json()

                dt = time.perf_counter() - t0

                ok = bool(data.get("ok"))

                print(

                    f"[{'ok' if ok else 'ERR'}] {sname}: {dt:.1f}s "

                    f"funcs={len(data.get('function_trace') or [])} "

                    f"error={data.get('error')}"

                )

                phase_res[sname] = {

                    "duration_s": round(dt, 2),

                    "ok": ok,

                    "error": data.get("error"),

                    "function_trace_count": len(data.get("function_trace") or []),

                }

                if not ok:

                    raise RuntimeError(f"{sname} failed: {data.get('error')}")

                return data



            await step(

                "config",

                {

                    "provider": cfg["provider"],

                    "api_key": cfg["api_key"],

                    "api_base": cfg["api_base"],

                    "model": cfg["model"],

                    "vision_model": cfg["vision_model"],

                    "embedding_model": cfg["embedding"],

                    "paper_directory": str(PAPER_DIR),

                    "index_name": index_name,

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

            print("---- ANSWER (first 300 chars) ----")

            print(answer[:300])

            print("---- REFERENCES (first 150 chars) ----")

            print(refs[:150])

            if len(answer) < 20:

                raise RuntimeError("answer too short, pipeline did not really answer")

        phase_res["status"] = "PASS"

        results["phases"][name] = phase_res  # type: ignore[index]



    try:

        await phase(

            "dashscope",

            {

                "provider": "dashscope",

                "api_key": DS["api_key"],

                "api_base": DS["api_base"],

                "model": DS["model"],

                "vision_model": DS["vision_model"],

                "embedding": DS["embedding"],

            },

            "verify_e2e_dash_index",

        )

        await phase(

            "deepseek-same-process",

            {

                "provider": "deepseek",

                "api_key": DEEP["api_key"],

                "api_base": DEEP["api_base"],

                "model": DEEP["model"],

                "vision_model": DEEP["vision_model"],

                "embedding": DEEP["embedding"],

            },

            "verify_e2e_deep_index",

        )

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

