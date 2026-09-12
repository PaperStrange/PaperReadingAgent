"""Sprint-16 F-AC10（验收⑧）：文献级 embedding checkpoint——逐篇落盘 / 零成本复用 / fail-closed。

链路（离线，st- 本地向量，零 API 成本；语料 = fitz 现场生成的两份**内容不同**的小 PDF）：
  config → load_index → parse_chunk_embed ×6 轮：
   ① 首跑：2 篇全部嵌入（embedded=2, reused=0）
   ② 重跑同路径：全部命中 checkpoint → **reused=2, embedded=0**（不再调用嵌入模型）
   ③ 边界-文件变更（touch Alpha 改 mtime）：Alpha 重跑、Beta 复用（embedded=1, reused=1）
   ④ 边界-载荷损坏（截断 Beta 的 .json.gz）：Beta 重跑、Alpha 复用（embedded=1, reused=1）
   ⑤ 边界-模型不匹配（篡改 manifest.embedding_model）：整份失效 → 全部重跑（embedded=2, reused=0，fail-closed）
   ⑥ 边界-同内容去重（Gamma.pdf 与 Alpha.pdf 逐字节相同）：记 deduped 不算失败，步骤仍 ok
断言另含：texts_count 跨轮稳定、manifest 结构（schema/status/条目 status=ready）。

Run: .venv\\Scripts\\python.exe verify\\verify_checkpoint.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC10 文献级 checkpoint：逐篇落盘 + 零成本复用 + 文件变更/载荷损坏/模型不匹配/同内容去重四重边界 fail-closed', 'tier': 'offline', 'providers': [], 'est_seconds': 180, 'est_cost_cny': 0, 'routes': ['/api/new_session', '/api/run_step'], 'requires': ['self-boots-backend']}

import asyncio
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # 控制台中文不乱码（GBK 默认）

from verify.e2e_common import PORT, start_backend, stop_backend, wait_healthy  # noqa: E402

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
SERVER_LOG = ROOT / "verify" / "verify_checkpoint_server.log"

PASSED = 0

_ALPHA_TEXT = (
    "PaperQA2 is an agentic retrieval augmented generation system for scientific literature. "
    "It iteratively searches, reads and cites papers, and aggregates evidence across documents. "
    "The agent uses tool calling with citation traversal to improve answer grounding. "
) * 6
_BETA_TEXT = (
    "Chunking strategy strongly affects recall for long documents in retrieval pipelines. "
    "Overlapping windows preserve context across chunk boundaries and reduce answer fragmentation. "
    "Embedding checkpoints let long ingestion jobs resume without recomputing finished documents. "
) * 6


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def make_pdf(path: Path, text: str, pages: int = 3) -> None:
    """生成 pages 页 PDF：paperqa 引用窥视固定读 1~3 页，单页 PDF 会报 'page not in document'。"""
    import fitz  # PyMuPDF（项目既有依赖）

    doc = fitz.open()
    chunk = max(1, len(text) // pages)
    for i in range(pages):
        page = doc.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 545, 780), text[i * chunk : (i + 1) * chunk] or text[:chunk], fontsize=11
        )
    doc.save(str(path))
    doc.close()


async def run_parse(client, base: str, sid: str, run_id: str, paths: list[str]) -> dict:
    r = await client.post(
        f"{base}/api/run_step",
        json={
            "session_id": sid,
            "run_id": run_id,
            "step": "parse_chunk_embed",
            "params": {"candidate_paths": paths, "embed_mode": "regen"},
            "upstream": {},
        },
    )
    r.raise_for_status()
    return r.json()


async def main() -> int:
    import httpx

    tmp = Path(tempfile.mkdtemp(prefix="verify_checkpoint_"))
    alpha = tmp / "Alpha.pdf"
    beta = tmp / "Beta.pdf"
    gamma = tmp / "Gamma.pdf"
    make_pdf(alpha, _ALPHA_TEXT)
    make_pdf(beta, _BETA_TEXT)
    shutil.copy2(alpha, gamma)  # 逐字节相同 → 触发 paperqa 内容去重
    paths = ["Alpha.pdf", "Beta.pdf"]

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
                    "session_id": sid, "run_id": "verify-checkpoint", "step": "config",
                    "params": {
                        "provider": "deepseek",
                        "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
                        "data_source": "local",
                        "paper_directory": str(tmp),
                        "index_name": "verify_checkpoint_index",
                    },
                    "upstream": {},
                },
            )
            r.raise_for_status()
            ok("F-AC10 config 临时语料目录成功", bool(r.json().get("ok")), str(r.json().get("error"))[:120])

            r = await client.post(
                f"{base}/api/run_step",
                json={"session_id": sid, "run_id": "verify-checkpoint", "step": "load_index",
                      "params": {"build": True}, "upstream": {}},
            )
            r.raise_for_status()
            ok("F-AC10 load_index 成功", bool(r.json().get("ok")), str(r.json().get("error"))[:120])

            # ① 首跑：全部嵌入
            d1 = await run_parse(client, base, sid, "ckpt-1", paths)
            ok("① 首跑成功", bool(d1.get("ok")), str(d1.get("error"))[:160])
            o1 = d1.get("output") or {}
            c1 = o1.get("checkpoint") or {}
            ok("① 首跑全部嵌入（embedded=2 / reused=0）",
               c1.get("embedded") == 2 and c1.get("reused") == 0, json.dumps(c1, ensure_ascii=False))
            ok("① per_file 标记 reused=False", all(x.get("reused") is False for x in o1.get("per_file") or []),
               json.dumps([x.get("reused") for x in o1.get("per_file") or []]))
            texts_count_1 = o1.get("texts_count")
            manifest_path = Path(c1.get("manifest") or "")
            ok("① manifest 落盘", manifest_path.is_file(), str(manifest_path))
            m1 = json.loads(manifest_path.read_text(encoding="utf-8"))
            ok("① manifest schema/status/两条 ready",
               m1.get("schema") == 1 and m1.get("status") == "ready"
               and len(m1.get("docs") or {}) == 2
               and all(v.get("status") == "ready" for v in (m1.get("docs") or {}).values()),
               json.dumps({k: v.get("status") for k, v in (m1.get("docs") or {}).items()}, ensure_ascii=False))

            # ② 重跑同路径：零成本复用
            d2 = await run_parse(client, base, sid, "ckpt-2", paths)
            ok("② 重跑成功", bool(d2.get("ok")), str(d2.get("error"))[:160])
            o2 = d2.get("output") or {}
            c2 = o2.get("checkpoint") or {}
            ok("② 全部命中 checkpoint（reused=2 / embedded=0，零嵌入成本）",
               c2.get("reused") == 2 and c2.get("embedded") == 0, json.dumps(c2, ensure_ascii=False))
            ok("② per_file 标记 reused=True", all(x.get("reused") is True for x in o2.get("per_file") or []),
               json.dumps([x.get("reused") for x in o2.get("per_file") or []]))
            ok("② texts_count 与首跑一致（复用内容等价）",
               o2.get("texts_count") == texts_count_1, f"{texts_count_1} vs {o2.get('texts_count')}")

            # ③ 边界：文件变更（mtime 变化 → 该篇重跑）
            alpha.touch()
            d3 = await run_parse(client, base, sid, "ckpt-3", paths)
            ok("③ 文件变更轮成功", bool(d3.get("ok")), str(d3.get("error"))[:160])
            o3 = d3.get("output") or {}
            c3 = o3.get("checkpoint") or {}
            reused_3 = {x["file"]: x.get("reused") for x in o3.get("per_file") or []}
            ok("③ 指纹变化篇重跑、另一篇复用（embedded=1 / reused=1）",
               c3.get("embedded") == 1 and c3.get("reused") == 1, json.dumps(c3, ensure_ascii=False))
            ok("③ 重跑的是 Alpha", reused_3.get("Alpha.pdf") is False and reused_3.get("Beta.pdf") is True,
               json.dumps(reused_3, ensure_ascii=False))

            # ④ 边界：载荷损坏（截断 Beta 的载荷 → 该篇重跑）
            m3 = json.loads(manifest_path.read_text(encoding="utf-8"))
            beta_dockey = str((m3.get("docs") or {}).get("Beta.pdf", {}).get("dockey") or "")
            payload = manifest_path.parent / str(m3.get("checkpoint_key") or manifest_path.stem) / f"{beta_dockey}.json.gz"
            payload.write_bytes(b"corrupt")
            d4 = await run_parse(client, base, sid, "ckpt-4", paths)
            ok("④ 载荷损坏轮成功", bool(d4.get("ok")), str(d4.get("error"))[:160])
            o4 = d4.get("output") or {}
            c4 = o4.get("checkpoint") or {}
            reused_4 = {x["file"]: x.get("reused") for x in o4.get("per_file") or []}
            ok("④ 坏件篇重跑、另一篇复用（embedded=1 / reused=1）",
               c4.get("embedded") == 1 and c4.get("reused") == 1, json.dumps(c4, ensure_ascii=False))
            ok("④ 重跑的是 Beta", reused_4.get("Beta.pdf") is False and reused_4.get("Alpha.pdf") is True,
               json.dumps(reused_4, ensure_ascii=False))

            # ⑤ 边界：模型不匹配（篡改 manifest.embedding_model → 整份失效，不静默复用）
            m4 = json.loads(manifest_path.read_text(encoding="utf-8"))
            m4["embedding_model"] = "tampered-model"
            manifest_path.write_text(json.dumps(m4, ensure_ascii=False), encoding="utf-8")
            d5 = await run_parse(client, base, sid, "ckpt-5", paths)
            ok("⑤ 模型不匹配轮成功", bool(d5.get("ok")), str(d5.get("error"))[:160])
            c5 = (d5.get("output") or {}).get("checkpoint") or {}
            ok("⑤ 模型不匹配 → 全部重跑（embedded=2 / reused=0，fail-closed）",
               c5.get("embedded") == 2 and c5.get("reused") == 0 and c5.get("model_match") is False,
               json.dumps(c5, ensure_ascii=False))

            # ⑥ 边界：同内容去重（Gamma 与 Alpha 逐字节相同 → paperqa 按 content_hash 去重）
            d6 = await run_parse(client, base, sid, "ckpt-6", ["Alpha.pdf", "Beta.pdf", "Gamma.pdf"])
            ok("⑥ 含重复内容文件时步骤仍成功（不误报失败）",
               bool(d6.get("ok")), str(d6.get("error"))[:160])
            o6 = d6.get("output") or {}
            c6 = o6.get("checkpoint") or {}
            per6 = {x["file"]: x for x in o6.get("per_file") or []}
            ok("⑥ 同内容文件记 deduped（deduped=1、embedded=0、reused=2）",
               c6.get("deduped") == 1 and c6.get("embedded") == 0 and c6.get("reused") == 2,
               json.dumps(c6, ensure_ascii=False))
            ok("⑥ per_file 标出 deduped 项", per6.get("Gamma.pdf", {}).get("deduped") is True,
               json.dumps({k: v.get("deduped") for k, v in per6.items()}, ensure_ascii=False))
    finally:
        stop_backend(server, False)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
