"""TG-4：provider e2e 三脚本共享基座（唯一真源 = 6 步驱动逻辑与 config 参数构造）。

设计规则：
- config 步**恒显式**携带 provider/api_base/model/vision_model/embedding——缺失 provider 或
  vision_model 时 vision 会回落默认服务商（3-LEARNED 1.46），基座从构造上杜绝该漂移。
- 所有写盘一律二进制（3-LEARNED 1.47：Windows 文本模式写盘会静默翻译换行）。
- 本文件是库而非测试，不参与覆盖矩阵收集（无 VERIFY_META）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

PORT = 8787


def build_config_params(cfg: dict, paper_dir: Path, index_name: str) -> dict:
    """构造 config 步参数（cfg 键：provider/api_key/api_base/model/vision_model/embedding）。"""
    return {
        "provider": cfg["provider"],
        "api_key": cfg["api_key"],
        "api_base": cfg["api_base"],
        "model": cfg["model"],
        "vision_model": cfg["vision_model"],
        "embedding_model": cfg["embedding"],
        "paper_directory": str(paper_dir),
        "index_name": index_name,
        "embedding_batch_size": 10,
        "chunk_chars": 5000,
        "chunk_overlap": 250,
        "temperature": 0.1,
    }


def start_backend(backend_path: Path, server_log: Path, root: Path) -> subprocess.Popen:
    # 035：日志句柄在父进程侧关闭（子进程持自己的副本），避免测试生命周期内句柄泄漏
    fh = open(server_log, "w", encoding="utf-8")
    try:
        return subprocess.Popen(
            [sys.executable, str(backend_path)],
            cwd=str(root),
            stdout=fh,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
    finally:
        fh.close()


def make_cfg(provider: dict) -> dict:
    """由 get_provider_config() 返回值组装 e2e config 六键（provider 名由 provider_config 注入）。
    三个入口脚本共用，消除 CFG/_cfg 复制粘贴（035 tech-debt）。"""
    return {
        "provider": provider["provider"],
        "api_key": provider["api_key"],
        "api_base": provider["api_base"],
        "model": provider["model"],
        "vision_model": provider["vision_model"],
        "embedding": provider["embedding"],
    }


def wait_healthy(server: subprocess.Popen, server_log: Path) -> bool:
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(60):
        try:
            r = httpx.get(f"{base}/api/health", timeout=3)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            time.sleep(1)
    print("ERR: backend did not become healthy")
    if server_log.exists():
        print(server_log.read_text(encoding="utf-8", errors="replace")[-4000:])
    server.kill()
    return False


def stop_backend(server: subprocess.Popen, keep: bool) -> None:
    if keep:
        return
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()


def dump_log_tail(server_log: Path, n: int = 6000) -> None:
    if server_log.exists():
        print("\n===== backend server log (tail) =====")
        print(server_log.read_text(encoding="utf-8", errors="replace")[-n:])


def write_results(out: Path, results: dict) -> None:
    out.write_bytes(json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"\n[written] {out}")


async def step(
    client: httpx.AsyncClient,
    base: str,
    session_id: str,
    run_id: str,
    name: str,
    params: dict,
    sink: dict | None = None,
) -> dict:
    t0 = time.perf_counter()
    resp = await client.post(
        f"{base}/api/run_step",
        json={
            "session_id": session_id,
            "run_id": run_id,
            "step": name,
            "params": params,
            "upstream": {},
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
    if sink is not None:
        sink[name] = {
            "duration_s": round(dt, 2),
            "ok": ok,
            "error": data.get("error"),
            "function_trace_count": len(data.get("function_trace") or []),
        }
    if not ok:
        raise RuntimeError(f"{name} failed: {data.get('error')}")
    return data


async def full_pipeline(
    client: httpx.AsyncClient,
    base: str,
    *,
    run_id: str,
    cfg: dict,
    paper_dir: Path,
    index_name: str,
    question: str,
    sink: dict,
) -> str:
    """全新会话内跑完整 6 步：config→load_index→retrieve→parse_chunk_embed→evidence→answer。
    step 记录写入 sink；返回答案文本。"""
    resp = await client.post(f"{base}/api/new_session")
    resp.raise_for_status()  # 035：先查状态码再取 json，500 错误页不被 JSON 解码掩盖
    sid = resp.json()["session_id"]
    sink["session_id"] = sid
    print(f"[ok] session {sid}")

    await step(client, base, sid, run_id, "config", build_config_params(cfg, paper_dir, index_name), sink)
    await step(client, base, sid, run_id, "load_index", {"build": True}, sink)
    ret = await step(client, base, sid, run_id, "retrieve", {"query": question, "top_n": 3}, sink)
    cands = ret["output"].get("candidate_paths") or []
    print(f"[ok] candidates: {cands}")
    await step(client, base, sid, run_id, "parse_chunk_embed", {"candidate_paths": cands}, sink)
    ev = await step(client, base, sid, run_id, "evidence", {"question": question}, sink)
    ctx = ev["output"].get("context_ids") or []
    print(f"[ok] evidence contexts: {len(ctx)}")
    ans = await step(client, base, sid, run_id, "answer", {}, sink)
    answer = (ans["output"] or {}).get("answer") or ""
    refs = (ans["output"] or {}).get("references") or ""
    print(f"[ok] answer chars: {len(answer)}")
    print("---- ANSWER (first 300 chars) ----")
    print(answer[:300])
    print("---- REFERENCES (first 150 chars) ----")
    print(refs[:150])
    if len(answer) < 20:
        raise RuntimeError("answer too short, pipeline did not really answer")
    return answer
