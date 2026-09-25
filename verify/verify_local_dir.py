"""Sprint-15 F-AC3（验收①1.3④）：local_dir/paper_directory 引擎接线实证。

临时目录放入 PaperQA2.pdf → 真实后端 config(local, paper_directory=临时目录) →
load_index(build) → retrieve → 断言候选路径来自临时目录（证明前端改路径后索引真实生效）。
全程本地（st- 向量），零 API 成本。

Run: .venv\\Scripts\\python.exe verify\\verify_local_dir.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC3 引擎接线实证：临时目录 paper_directory → load_index → retrieve 候选来自该目录（免密：注入占位 key，链路无 LLM 调用）', 'tier': 'offline', 'providers': [], 'est_seconds': 90, 'est_cost_cny': 0, 'routes': ['/api/new_session', '/api/run_step'], 'requires': ['self-boots-backend']}

import asyncio
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 2026-09-25（TG-8 收尾）：子进程输出以 errors="replace" 解码后可能带回 U+FFFD，而本机 stdout
# 为 GBK → 打印断言详情时 UnicodeEncodeError 崩溃（实测单跑 rc=1；`PYTHONUTF8=1` 时不复现）。
# 与仓库其它 verify 脚本一致：显式 UTF-8 + 容错，消除"环境相关假红"。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from verify.e2e_common import (  # noqa: E402
    PORT,
    port_in_use,
    port_selfcheck,
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


# ---------------------------------------------------------------- TG-8① 端口自检断言

SELFCHECK_CHILD = (
    "import os, sys\n"
    "sys.path.insert(0, {root})\n"
    "from verify.e2e_common import PORT, port_selfcheck, start_backend\n"
    "if sys.argv[1] == 'preflight-only':\n"
    "    print('CHILD-PORT', PORT)\n"
    "    port_selfcheck((PORT,))\n"
    "    print('PRECHECK-PASSED')\n"
    "    raise SystemExit(0)\n"
    "try:\n"
    "    start_backend({backend}, None, {root})\n"
    "except Exception as exc:\n"
    "    print('PRECHECK-FAILED', type(exc).__name__)\n"
    "    print(exc)\n"
    "    raise SystemExit(1)\n"
    "print('PRECHECK-PASSED')\n"
    "raise SystemExit(0)\n"
)


def port_selfcheck_conflict_assertions() -> dict:
    """TG-8① 反向对照：**自己起监听占住端口** → 自举必须失败并点名；释放后 → 通过。

    为什么用子进程而不是直接调 `start_backend`：判据的真身是"**脚本进程**以非 0 退出、
    且 stdout 里能读到可操作提示"——同进程 try/except 只能证明"函数抛了异常"，
    证明不了"入口进程确实失败了"，也证明不了"没留下半自举的子进程"。
    **子脚本以内联 `-c` 传入、不落盘**（TG-9 产物落点约定 + 本文件动态目标棘轮：多一个
    `write_text(动态路径)` 就会顶破上限；内联脚本文本不产生任何写盘目标）。
    """
    import socket
    import subprocess

    def run_child(mode: str, env_extra: dict) -> subprocess.CompletedProcess:
        code = SELFCHECK_CHILD.format(backend=repr(str(BACKEND)), root=repr(str(ROOT)))
        # 2026-09-25（TG-8 收尾实测）：子进程 stdout/stderr 是**管道**，Windows 下 Python 默认按
        # 本地编码（GBK）写；父进程按 UTF-8 解码 → 中文提示全变 mojibake，导致"含释放提示/含改端口
        # 提示"两条断言恒 False（假红）。故显式让子进程用 UTF-8 写（PYTHONUTF8/PYTHONIOENCODING）。
        child_env = {**os.environ, **env_extra,
                     "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        return subprocess.run([sys.executable, "-c", code, mode], cwd=str(ROOT), check=False,
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=child_env, timeout=120)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", PORT))
    listener.listen(1)
    pid = os.getpid()
    try:
        occupied = run_child("start", {})
        # 释放端口 → 同一路径通过。子进程用 `PAPERQA_VERIFY_PORT` 抬高端口（本基座的 `PORT` 读它），
        # 且**必须在子进程里读**：写死在生成代码里的端口号会忽略该环境变量（实测就是这样，
        # 于是"释放后通过"恒失败——断言自身的假红）。
        free = run_child("preflight-only", {"PAPERQA_VERIFY_PORT": str(PORT + 100)})
    finally:
        listener.close()

    out_occ = (occupied.stdout or "") + (occupied.stderr or "")
    out_free = (free.stdout or "") + (free.stderr or "")
    return {
        "fail_fast": occupied.returncode != 0 and "PRECHECK-PASSED" not in out_occ,
        "pass_when_free": free.returncode == 0 and "PRECHECK-PASSED" in out_free,
        "actionable": all(t in out_occ for t in (str(PORT), f"PID={pid}", "释放端口", "改用其它端口")),
        "detail_fail": f"rc={occupied.returncode} out={out_occ.strip().splitlines()[:2]}",
        "detail_actionable": (f"含端口={str(PORT) in out_occ} 含占用PID={f'PID={pid}' in out_occ} "
                              f"含释放提示={'释放端口' in out_occ} 含改端口提示={'改用其它端口' in out_occ}"),
        "detail_free": f"rc={free.returncode} out={out_free.strip()[:80]}",
    }


async def main() -> int:
    import httpx

    # ── TG-8①：自举前端口自检（**可核断言，含反向对照**） ────────────────────────────────
    # 事故形态（卡文正文）：`wait_healthy` 只探测端口、不校验"服务是不是自己启的" → dev 后端在跑时
    # 脚本会**静默复用它**并施加 parse/embed 负载；反之套件也会抢占/顶掉 dev 后端。
    # 修法判据 = 自举前 fail-fast 并点名（端口 / 占用进程 / 怎么释放或改端口），**不复用、不换端口**。
    # 本函数的 daemon 线程只活到 `main()` 返回（`asyncio.run` 之后进程即退出），故不会留下监听。
    port_selfcheck((PORT,))  # ⑤c：真实仓库端口此刻确为空（占用即在此 fail-fast）
    conflicts = port_selfcheck_conflict_assertions()
    ok("⑤ 端口被占用时自举**明确失败**并点名：不发子进程、不静默复用（反向对照 / 修复前此断言不成立）",
       conflicts["fail_fast"], conflicts["detail_fail"])
    ok("⑤ 错误信息含三件可操作信息：端口号 + 占用进程（PID/镜像名）+ 怎么改/怎么释放",
       conflicts["actionable"], conflicts["detail_actionable"])
    ok("⑤ 释放端口后同一路径**通过**（证明失败来自占用本身，而非『预检恒失败』）",
       conflicts["pass_when_free"], conflicts["detail_free"])
    ok("⑤ 预检通过路径**不留下任何监听**（未产生半自举进程 / 未占住端口）",
       not port_in_use(PORT), f"port {PORT} in_use={port_in_use(PORT)}")

    # 免密化（2026-09-12，CI 离线档实证）：本链路 config → load_index → retrieve **不调用 LLM**，
    # 但两处会要求/触发 LLM：① `make_settings` 要求 api_key 非空；② **索引构建内部会走 `aadd` 的
    # citation 推断**（3-LEARNED 1.30 同型坑）。故：注入占位 key + 用 CSV manifest 提供 citation
    # （与 verify_index_health 同一解法）。若将来此链路意外发起真实调用，占位 key 会 401 直接暴露。
    #
    # TG-8③ 归因结论的确定性加固：**索引名带唯一后缀**。旧实现写死 `verify_local_dir_index`，
    # 而 paperqa 的 `SearchIndex` 有**进程内**的 `_OPENED_INDEX_CACHE`（键 = 索引名 + 索引目录绝对路径）
    # 与 Tantivy 的 `.tantivy-writer.lock`；同名索引叠加重试会让"上一轮没删净的目录/句柄"影响本轮，
    # 使失败无法归因。唯一化后每轮都是干净命名空间（也顺带覆盖 `_embed_checkpoint_key` 的
    # (目录, 索引名, 模型) 命名空间）。
    os.environ.setdefault("DEEPSEEK_API_KEY", "sk-offline-dummy-for-verify-local-dir")
    tmp = Path(tempfile.mkdtemp(prefix="verify_local_dir_"))
    # 唯一文件名：data/pdf 下不存在 LocalDirProbe.pdf，候选命中它即证明索引来自临时目录
    tmp_pdf = tmp / "LocalDirProbe.pdf"
    shutil.copy2(SRC_PDF, tmp_pdf)
    manifest = tmp / "manifest.csv"
    manifest.write_text(
        "file_location,citation,title\n"
        'LocalDirProbe.pdf,"LocalDirProbe, 2026, Verify Fixture","LocalDirProbe"\n',
        encoding="utf-8",
    )
    index_name = f"verify_local_dir_index_{uuid.uuid4().hex[:8]}"
    # TG-8③ **flaky 根因的修法**：关掉**媒体 vision 增强**（后端 `app/engine.py` 读此 env）。
    # 证据（本轮抓到的真实 flaky，见卡 `TG-8.md`）：占位 key 的 401 被 litellm 转成
    # `RateLimitError`，而 paperqa 的 enrichment 只捕获 `BadRequestError`/`InternalServerError`
    # （`settings.py:1134`）⇒ 逃出 `asyncio.gather` → `Docs.aadd` → `process_file` 的
    # 非 ValueError 分支 `raise` → anyio TaskGroup 报
    # `unhandled errors in a TaskGroup (1 sub-exception)`，整步 FAIL。
    # 本链路（本地目录 → 本地 st- 向量 → 检索）按设计**不调用 LLM**，故关掉该外呼是本测试的**正当前置**，
    # 不是"放宽断言"：断言（config/load_index/retrieve 三步成功 + 候选来自临时目录）一条未改。
    # 生命周期：`start_backend` 拉起后端时继承该 env；finally 里恢复原值（不泄漏给套件后续脚本）。
    _enrich_backup = os.environ.get("PAPERQA_NO_MEDIA_ENRICHMENT")
    os.environ["PAPERQA_NO_MEDIA_ENRICHMENT"] = "1"
    try:
        server = start_backend(BACKEND, SERVER_LOG, ROOT)
        if not wait_healthy(server, SERVER_LOG):
            return 3
        base = f"http://127.0.0.1:{PORT}"
        async with httpx.AsyncClient(timeout=None) as client:
            sid = (await client.post(f"{base}/api/new_session")).json()["session_id"]

            async def run_step(step: str, params: dict) -> dict:
                """POST /api/run_step 并**在失败时打印完整堆栈**（TG-8③ 的可归因性修复）。

                旧实现只断言 `d["ok"]`，失败信息只有 `error` 字符串；而本链路的失败形态恰好是
                `unhandled errors in a TaskGroup (1 sub-exception)` —— **anyio 的 ExceptionGroup
                在 `str()` 里不展开**，于是卡内证据只能写"根因未展开"。后端其实已经把完整 traceback
                放在 `error_detail`（`app/orchestration.py` 的 `traceback.format_exc()`，前端错误卡
                也是用它），**是本脚本把它丢了**。现在失败即打印，偶发失败可直接归因到叶子异常
                （本轮就是靠它抓到根因：占位 key 的 401 → `litellm.RateLimitError` 逃逸）。
                """
                resp = await client.post(
                    f"{base}/api/run_step",
                    json={"session_id": sid, "run_id": "verify-local-dir", "step": step,
                          "params": params, "upstream": {}},
                )
                resp.raise_for_status()
                data = resp.json()
                if not data.get("ok"):
                    print(f"\n---- {step} FAILED: {data.get('error')!r} ----")
                    print(data.get("error_detail") or "(后端未返回 error_detail)")
                    print(f"---- end {step} error_detail ----\n")
                return data

            d = await run_step("config", {
                "provider": "deepseek",
                "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",
                "data_source": "local",
                "paper_directory": str(tmp),
                "index_name": index_name,
                "manifest_file": str(manifest),  # citation 由 manifest 提供 → 索引构建无 LLM 调用
            })
            ok("F-AC3 config 临时目录成功", bool(d.get("ok")), str(d.get("error"))[:120])
            d = await run_step("load_index", {"build": True})
            ok("F-AC3 load_index 成功", bool(d.get("ok")), str(d.get("error"))[:120])
            d = await run_step("retrieve", {"query": "What is PaperQA2?", "top_n": 3})
            cands = ((d.get("output") or {}).get("candidate_paths")) or []
            ok("F-AC3 retrieve 候选来自临时目录",
               any("LocalDirProbe.pdf" in str(c) for c in cands), f"cands={cands}")
    finally:
        # TG-8③：先确认后端**真的退出**（`stop_backend` 内含 kill 后 `wait()`），再清临时目录。
        # 清理**就地内联**（`tmp` 是 `tempfile.mkdtemp()` 的直接结果 → 写盘目标可静态判定）而不是
        # 抽成 `rmtree_robust(tmp)` 之类的公共函数：一旦目标成了**函数参数**，`verify_artifact_paths.py`
        # 的分解器就判它"动态目标"并顶破 `e2e_common.py` 的棘轮上限（实测过一次，闸门是对的）。
        stop_backend(server, False)
        if _enrich_backup is None:
            os.environ.pop("PAPERQA_NO_MEDIA_ENRICHMENT", None)
        else:
            os.environ["PAPERQA_NO_MEDIA_ENRICHMENT"] = _enrich_backup
        for attempt in range(5):
            if not tmp.exists():
                break
            try:
                shutil.rmtree(tmp)
                break
            except OSError as exc:
                if attempt == 4:
                    print(f"WARN: 临时目录未能删净（已重试 5 次）：{tmp}"
                          f"（{type(exc).__name__}: {exc}）——残留会占用磁盘并干扰下一轮归因")
                else:
                    time.sleep(0.2 * (attempt + 1))
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
