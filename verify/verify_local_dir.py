"""Sprint-15 F-AC3（验收①1.3④）：local_dir/paper_directory 引擎接线实证。

临时目录放入 PaperQA2.pdf → 真实后端 config(local, paper_directory=临时目录) →
load_index(build) → retrieve → 断言候选路径来自临时目录（证明前端改路径后索引真实生效）。
全程本地（st- 向量），零 API 成本。

Run: .venv\\Scripts\\python.exe verify\\verify_local_dir.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC3 引擎接线实证：临时目录 paper_directory → load_index → retrieve 候选来自该目录', 'tier': 'offline', 'providers': [], 'est_seconds': 90, 'est_cost_cny': 0, 'routes': ['/api/new_session', '/api/run_step'], 'requires': ['self-boots-backend']}

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.e2e_common import (  # noqa: E402
    PORT,
    start_backend,
    stop_backend,
    wait_healthy,
)

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
SERVER_LOG = ROOT / "verify" / "verify_local_dir_server.log"
SRC_PDF = ROOT / "data" / "pdf" / "PaperQA2.pdf"

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


async def main() -> int:
    import httpx

    tmp = Path(tempfile.mkdtemp(prefix="verify_local_dir_"))
    # 唯一文件名：data/pdf 下不存在 LocalDirProbe.pdf，候选命中它即证明索引来自临时目录
    tmp_pdf = tmp / "LocalDirProbe.pdf"
    shutil.copy2(SRC_PDF, tmp_pdf)
    server = start_backend(BACKEND, SERVER_LOG, ROOT)
    if not wait_healthy(server, SERVER_LOG):
        return 3
    base = f"http://127.0.0.1:{PORT}"
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            sid = (await client.post(f"{base}/api/new_session")).json()["session_id"]
            r = await client.post(
                f"{base}/api/run_step",
                json={
                    "session_id": sid, "run_id": "verify-local-dir", "step": "config",
                    "params": {
                        "provider": "deepseek",
                        "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
                        "data_source": "local",
                        "paper_directory": str(tmp),
                        "index_name": "verify_local_dir_index",
                    },
                    "upstream": {},
                },
            )
            r.raise_for_status()
            d = r.json()
            ok("F-AC3 config 临时目录成功", bool(d.get("ok")), str(d.get("error"))[:120])
            r = await client.post(
                f"{base}/api/run_step",
                json={"session_id": sid, "run_id": "verify-local-dir", "step": "load_index",
                      "params": {"build": True}, "upstream": {}},
            )
            r.raise_for_status()
            d = r.json()
            ok("F-AC3 load_index 成功", bool(d.get("ok")), str(d.get("error"))[:120])
            r = await client.post(
                f"{base}/api/run_step",
                json={"session_id": sid, "run_id": "verify-local-dir", "step": "retrieve",
                      "params": {"query": "What is PaperQA2?", "top_n": 3}, "upstream": {}},
            )
            r.raise_for_status()
            d = r.json()
            cands = ((d.get("output") or {}).get("candidate_paths")) or []
            ok("F-AC3 retrieve 候选来自临时目录",
               any("LocalDirProbe.pdf" in str(c) for c in cands), f"cands={cands}")
    finally:
        stop_backend(server, False)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
