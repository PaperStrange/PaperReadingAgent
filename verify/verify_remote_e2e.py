"""remote 数据源全链路验证（Sprint-3 US-3.3/US-3.5 证据，可重复执行）：

config(remote: arXiv 2409.13740) -> load_index -> retrieve -> parse_chunk_embed -> evidence -> answer



运行前提：OPENAI_API_KEY（DeepSeek）；联网（export.arxiv.org）。

运行：.venv\\Scripts\\python.exe verify\\verify_remote_e2e.py

"""

VERIFY_META = {'features': 'remote 数据源全链路（arXiv 下载+索引+6 步）', 'tier': 'network', 'providers': ['deepseek'], 'est_seconds': 180, 'est_cost_cny': 0.4, 'routes': ['/api/new_session', '/api/run_step', '/api/stream/{session_id}/{run_id}', '/api/session_records/{session_id}', '/api/reset_session'], 'requires': ['keys', 'network']}



import io

import json

import subprocess

import sys

import time

from pathlib import Path



sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")



import httpx



ROOT = Path(__file__).resolve().parent.parent

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"

BASE = "http://127.0.0.1:8787"



server = subprocess.Popen(

    [str(ROOT / ".venv" / "Scripts" / "python.exe"), str(BACKEND)],

    cwd=str(ROOT),

    stdout=subprocess.DEVNULL,

    stderr=subprocess.STDOUT,

)



try:

    for _ in range(60):

        try:

            httpx.get(f"{BASE}/api/health", timeout=2).raise_for_status()

            break

        except Exception:

            time.sleep(1)



    client = httpx.Client(base_url=BASE, timeout=600)

    sid = client.post("/api/new_session").json()["session_id"]

    print("session:", sid)



    config_params = {

        "provider": "deepseek",

        "data_source": "remote",

        "source_arxiv_ids": ["2409.13740"],

        "index_name": "remote_e2e_idx",

    }



    def step(name, params):

        r = client.post(

            "/api/run_step",

            json={"session_id": sid, "step": name, "params": params},

        )

        data = r.json()

        print(f"[{name}] ok={data.get('ok')} dur={data.get('duration_s')} err={data.get('error')}")

        if not data.get("ok"):  # review m11：失败即止，避免误导性输出

            raise SystemExit(f"step {name} failed: {data.get('error')}")

        return data



    step("config", config_params)

    li = step("load_index", {"build": True})

    print("  load_index output:", json.dumps(li.get("output", {}), ensure_ascii=False)[:500])

    re_ = step("retrieve", {"query": "PaperQA2", "top_n": 3})

    print("  retrieve output:", json.dumps(re_.get("output", {}), ensure_ascii=False)[:300])

    step("parse_chunk_embed", {"embed_mode": "run"})

    ev = step("evidence", {"question": "What is PaperQA2?"})

    print("  evidence contexts:", ev.get("output", {}).get("contexts_count"))

    an = step("answer", {})

    print("  answer chars:", len(an.get("output", {}).get("answer", "")))

    print("  answer head:", an.get("output", {}).get("answer", "")[:200])

finally:

    server.terminate()

    server.wait(timeout=30)

