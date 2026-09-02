"""F4 轻量评测基准（Sprint-6 US-6.3，可复现）：retrieve 命中质量小样本对比。



- 语料 A：data/pdf（PaperQA2.pdf）——验证"中文 query 零命中 → 英文关键词重试"路径；

- 语料 B：data/arxiv_pdf_sep（用户嵌套语料，12 篇）——验证直接命中与多语重试的覆盖。



运行：.venv\\Scripts\\python.exe verify\\eval_retrieve.py

输出：逐 query 的 strategy/result/hit@1，以及两语料的命中率汇总（作为 F1 的基线证据）。

"""



from __future__ import annotations

VERIFY_META = {'features': '检索质量小样本评测：双语料命中率 + hit@1 + 多语重试覆盖', 'tier': 'network', 'providers': ['deepseek'], 'est_seconds': 60, 'est_cost_cny': 0.3, 'routes': ['/api/run_step'], 'requires': ['keys', 'network']}



import io

import subprocess

import sys

import time

from pathlib import Path



sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")



import httpx



ROOT = Path(__file__).resolve().parent.parent

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"

BASE = "http://127.0.0.1:8787"



# (query, 期望文件名片段, 期望策略或 None 表示不校验策略)

CASES_A = [

    ("什么是PaperQA？", "PaperQA2.pdf", "keyword_retry"),   # 中文零命中 → 关键词重试应命中

    ("帮我总结 PaperQA 这篇论文", "PaperQA2.pdf", None),     # 中文 + 英文关键词

    ("paperqa agent factuality", "PaperQA2.pdf", "direct"), # 英文直接命中

]

# B[1] 为负对照：纯中文无英文关键词 → 预期 fallback（不参与 hit 统计）

CASES_B = [

    ("Agent-G2 是什么方法？", "Agent-G2", None),  # 含英文名，直接或重试命中

]



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



    def run_corpus(label: str, paper_dir: str, cases: list[tuple[str, str, str | None]]) -> dict:

        sid = client.post("/api/new_session").json()["session_id"]

        client.post("/api/run_step", json={"session_id": sid, "step": "config", "params": {

            "provider": "deepseek", "paper_directory": paper_dir,

            "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",

            "index_name": "eval_idx"}}).json()

        client.post("/api/run_step", json={"session_id": sid, "step": "load_index",

                                           "params": {"build": True}}).json()

        hits = 0

        print(f"--- 语料 {label} ({paper_dir}) ---")

        for q, expect, want_strategy in cases:

            r = client.post("/api/run_step", json={"session_id": sid, "step": "retrieve",

                            "params": {"query": q, "top_n": 5}}).json()

            out = r.get("output", {})

            top1 = (out.get("candidate_paths") or [""])[0]

            strategy = out.get("query_strategy")

            hit = expect in top1

            hits += 1 if hit else 0

            strategy_ok = (want_strategy is None) or (strategy == want_strategy)

            print(f"  [{strategy}|{out.get('result')}] {q!r} -> {top1[:60]!r} "

                  f"hit={hit} strategy_ok={strategy_ok}")

            if want_strategy and not strategy_ok:

                print(f"  !! 期望策略 {want_strategy}，实际 {strategy}")

        print(f"  hit@1: {hits}/{len(cases)}")

        return {"hits": hits, "total": len(cases)}



    a = run_corpus("A", "data/pdf", CASES_A)

    b = run_corpus("B", "data/arxiv_pdf_sep", CASES_B)

    # 负对照：纯中文无英文关键词 → 预期 fallback_first_n

    sid2 = client.post("/api/new_session").json()["session_id"]

    client.post("/api/run_step", json={"session_id": sid2, "step": "config", "params": {

        "provider": "deepseek", "paper_directory": "data/arxiv_pdf_sep",

        "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",

        "index_name": "eval_idx"}}).json()

    client.post("/api/run_step", json={"session_id": sid2, "step": "load_index",

                                       "params": {"build": True}}).json()

    r = client.post("/api/run_step", json={"session_id": sid2, "step": "retrieve",

                    "params": {"query": "阿拉伯语自然语言处理研究进展", "top_n": 5}}).json()

    out = r.get("output", {})

    neg_ok = out.get("query_strategy") == "fallback_first_n" and out.get("result") == "fallback_first_n"

    print(f"负对照（纯中文无关键词）: strategy={out.get('query_strategy')} "

          f"result={out.get('result')} -> {'PASS' if neg_ok else 'FAIL'}")

    print(f"== 汇总 hit@1：A={a['hits']}/{a['total']} B={b['hits']}/{b['total']} 负对照={neg_ok} ==")

finally:

    server.terminate()

    server.wait(timeout=30)

