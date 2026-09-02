"""验证 parse_chunk_embed 的 载入(load)/重新生成(regen)/缓存 逻辑。"""
VERIFY_META = {'features': 'parse_chunk_embed 三种模式：run/load 同会话/load 新会话（embed 缓存）', 'tier': 'network', 'providers': ['deepseek'], 'est_seconds': 90, 'est_cost_cny': 0.3, 'routes': ['/api/run_step'], 'requires': ['keys', 'network']}

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
PAPER_DIR = ROOT / "data" / "pdf"
BASE = "http://127.0.0.1:8787"

async def main() -> int:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    server = subprocess.Popen([sys.executable, str(BACKEND)], cwd=str(ROOT), env=env)
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{BASE}/api/health", timeout=3).status_code == 200:
                    break
            except Exception:
                time.sleep(1)
        else:
            print("backend not healthy"); return 3

        async def session_and_steps():
            sid = httpx.post(f"{BASE}/api/new_session").json()["session_id"]
            async with httpx.AsyncClient(timeout=None) as c:
                def cfg(name):
                    return {
                        "session_id": sid, "run_id": "embed-test", "step": name,
                        "params": {}, "upstream": {},
                    }
                await c.post(f"{BASE}/api/run_step", json={**cfg("config"), "params": {
                    "api_key": os.getenv("OPENAI_API_KEY",""),
                    "api_base": "https://api.deepseek.com",
                    "model": "openai/deepseek-v4-flash",
                    "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
                    "paper_directory": str(PAPER_DIR),
                    "index_name": "verify_e2e_index",
                    "embedding_batch_size": 10, "chunk_chars": 5000, "chunk_overlap": 250,
                    "temperature": 0.1,
                }})
                await c.post(f"{BASE}/api/run_step", json={**cfg("load_index"), "params": {"build": False}})
                ret = await c.post(f"{BASE}/api/run_step", json={**cfg("retrieve"), "params": {"query": "What is PaperQA2?", "top_n": 1}})
                cands = ret.json().get("output", {}).get("candidate_paths") or []
                return sid, cands

        # 会话 1：先跑一次（慢，生成 session docs + 缓存），再 load（应复用 docs、秒完成）
        sid1, cands = await session_and_steps()
        async with httpx.AsyncClient(timeout=None) as c:
            async def step(name, params):
                t0 = time.perf_counter()
                r = await c.post(f"{BASE}/api/run_step", json={"session_id": sid1, "run_id": "embed-test", "step": name, "params": params, "upstream": {}})
                d = r.json(); dt = time.perf_counter() - t0
                return d, dt
            print(f"[candidates] {cands}")
            d1, t1 = await step("parse_chunk_embed", {"candidate_paths": cands, "embed_mode": "run"})
            print(f"[1] run  : ok={d1.get('ok')} dur={t1:.1f}s texts={d1.get('output',{}).get('texts_count')} loaded={d1.get('output',{}).get('loaded')}")
            d2, t2 = await step("parse_chunk_embed", {"candidate_paths": cands, "embed_mode": "load"})
            print(f"[2] load : ok={d2.get('ok')} dur={t2:.1f}s loaded={d2.get('output',{}).get('loaded')} src={d2.get('output',{}).get('source')} texts={d2.get('output',{}).get('texts_count')}")

        # 会话 2（全新 session，无内存 docs）：load 应从缓存命中
        sid2, cands2 = await session_and_steps()
        async with httpx.AsyncClient(timeout=None) as c:
            t0 = time.perf_counter()
            r = await c.post(f"{BASE}/api/run_step", json={"session_id": sid2, "run_id": "embed-test2", "step": "parse_chunk_embed", "params": {"candidate_paths": cands2, "embed_mode": "load"}, "upstream": {}})
            d = r.json(); dt = time.perf_counter() - t0
            print(f"[3] load(new session): ok={d.get('ok')} dur={dt:.1f}s loaded={d.get('output',{}).get('loaded')} src={d.get('output',{}).get('source')} texts={d.get('output',{}).get('texts_count')}")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
