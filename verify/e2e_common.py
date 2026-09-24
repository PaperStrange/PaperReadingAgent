"""TG-4：provider e2e 三脚本共享基座（唯一真源 = 6 步驱动逻辑与 config 参数构造）。

设计规则：
- config 步**恒显式**携带 provider/api_base/model/vision_model/embedding——缺失 provider 或
  vision_model 时 vision 会回落默认服务商（3-LEARNED 1.46），基座从构造上杜绝该漂移。
- 所有写盘一律二进制（3-LEARNED 1.47：Windows 文本模式写盘会静默翻译换行）。
- **自举前端口自检（TG-8）**：`start_backend` 在拉起子进程**之前**先探测端口（8787 后端、
  5173 前端 dev）——被占用即 **fail-fast 并点名**（哪个端口、占用进程 PID/镜像名、怎么释放或改端口），
  **绝不静默复用**别人的服务（旧行为见 `wait_healthy` 的历史注释）。
- 本文件是库而非测试，不参与覆盖矩阵收集（无 VERIFY_META）。
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

PORT = int(os.environ.get("PAPERQA_VERIFY_PORT", "8787"))
# TG-8①：端口**可配置**（报告里给出的"改用其它端口"提示必须真的生效——否则提示是空头支票）。
# 默认 8787 来自 `paper-qa-script/.../backend/main.py:252` 的 uvicorn 端口常量；改端口时两处都要改
# （前端 dev 端口不在此列：Vite 默认 5173，本仓库 vite.config.mjs 未写死）。
#
# `BACKEND_PORTS` = 自举后端时**必须空着**的端口。前端 dev（Vite 默认 5173）一起查的理由是套件的
# `gui` 档会同时占用两者（run_suite.py:197 的提示），而 dev 前端在跑时后端自举常常"看起来能跑"
# ——实际前端连的是 dev 后端（2026-09-20 走查：后端两次消失即该形态）。
# 顺序上 8787 在前：它是本基座直接依赖的服务，先报它信息量最大。
BACKEND_PORTS = (PORT, 5173)
# 占用进程查询命令行（Windows 自带；本仓库仅面向 Windows，见 1-WORKFLOW §2 双轨约定）。
_PORT_OWNER_CMD = "Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"


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


def _apply_offline_env() -> dict:
    """TG-8 正文 ③：离线开关开启时给后端注入 `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`。

    用**按文件路径加载**而不是 `from verify import offline_guard`：本基座的使用者
    （套件脚本、临时重放脚本）可能从任意 cwd 启动，`import verify` 在 `verify/` 是命名空间包
    （无 `__init__.py`）时会解析到**别的**同名目录（实测：`ImportError: cannot import name
    'offline_guard' from 'verify' (unknown location)`）。按路径加载与 cwd/sys.path 无关，
    失败也不抛（本动作只影响"HF 是否重试"，离线判据由各外呼入口自己把关）。
    """
    import importlib.util

    # ⚠️ 局部变量名不要叫 `path`：本文件里 `_append_metric` 用 `path = os.environ.get(
    # "PAPERQA_SUITE_METRICS", "")` 表示"缺省不落盘"，而 `verify_artifact_paths.py` 的分解器
    # 是**按名字**收集赋值的——同名多处且取值不一致 → 判定为"动态目标"，
    # 于是 e2e_common 的动态目标计数会从 2 顶到 3 而顶破棘轮上限（实测过一次）。
    guard_path = Path(__file__).resolve().parent / "outbound_guard.py"
    try:
        spec = importlib.util.spec_from_file_location("_tg8_outbound_guard", guard_path)
        if spec is None or spec.loader is None:
            return {}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.apply_env()
    except BaseException:  # noqa: BLE001 —— 含 OfflineRefused/PolicyError：不因开关数据问题挡住自举
        return {}


def start_backend(backend_path: Path, server_log: Path, root: Path) -> subprocess.Popen:
    # TG-8①：**先自检端口，再拉进程**——占用即明确报错并给出可操作提示（不复用、不换端口）。
    port_selfcheck(BACKEND_PORTS)
    # TG-8 正文 ③：离线开关开启时注入 HF 离线变量（消除本地向量模型解析时的 HEAD 重试阻塞）。
    _apply_offline_env()
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


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """端口是否已被占用（**独立探测**：绑定失败即被占，不依赖外部工具）。

    判据取"能否绑定"而不是"能否连上"：只连不绑会漏掉**已绑定但尚未开始 accept** 的进程
    （uvicorn 启动窗口期正是这样），而那种窗口恰好是"两个后端抢同一端口"的事故形态。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, int(port)))
        except OSError:
            return True
    return False


def port_owner(port: int, timeout_s: int = 15) -> str:
    """查出占用 `port` 的进程（`PID=… 镜像名=…`；查不到就如实说"查不到"）。

    限制（如实标注）：`Get-NetTCPConnection` 需要提权才能看到**其它用户**的进程名；
    本机开发场景（同一用户）可用。查不到时仍给出"怎么自己查"的命令，不假装知道。
    """
    query = _PORT_OWNER_CMD.format(port=int(port))
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"{query} | ForEach-Object {{ $_.OwningProcess }} | Sort-Object -Unique"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_s, check=False,
        )
        pids = [p.strip() for p in (proc.stdout or "").splitlines() if p.strip().isdigit()]
    except (OSError, subprocess.SubprocessError):
        pids = []
    if not pids:
        return f"查不到占用进程（可自行运行：{query}）"
    names = []
    for pid in pids[:4]:
        try:
            info = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).ProcessName"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout_s, check=False,
            )
            name = (info.stdout or "").strip() or "?"
        except (OSError, subprocess.SubprocessError):
            name = "?"
        names.append(f"PID={pid} 镜像名={name}")
    return "；".join(names)


def port_selfcheck(ports=BACKEND_PORTS) -> None:
    """自举前端口自检（TG-8①）：任一端口被占用 → **fail-fast 并点名**（不静默复用、不换端口）。

    报错内容必须包含三件可操作信息（本卡判据）：① **哪个端口**；② **被哪个进程占用**；
    ③ **怎么改 / 怎么释放**。失败形态是 `RuntimeError`（调用方未捕获 → 进程退出码非 0），
    且**在拉子进程之前**抛出：不会留下"半自举"的后端进程。
    """
    busy = [(p, port_owner(p)) for p in ports if port_in_use(p)]
    if not busy:
        return
    lines = [
        "ERR: 端口自检失败——以下端口已被占用，本脚本**不会复用**它（TG-8①：占用即 fail-fast，不静默换端口）：",
    ]
    for port, owner in busy:
        lines.append(f"  · 端口 {port}：被 {owner} 占用")
    alt = (int(ports[0]) + 100) if ports else 0
    lines += [
        "  解决方式（二选一）：",
        "    ① 释放端口：停掉上面的进程（如 dev 后端 `Ctrl+C`，或 `Stop-Process -Id <PID>`）后重跑；",
        f"    ② 改用其它端口：设环境变量 `PAPERQA_VERIFY_PORT={alt}` 后重跑（本基座的 `PORT` 即读它），",
        "       并同步改后端 uvicorn 端口（paper-qa-script/reactflow-paperqa-prototype/backend/main.py:252；"
        "前端 dev 端口用 `npm run dev -- --port <端口>`，Vite 默认 5173 未在本仓库 vite.config.mjs 里写死）。",
    ]
    raise RuntimeError("\n".join(lines))


def wait_healthy(server: subprocess.Popen, server_log: Path) -> bool:
    """等 `/api/health` 就绪。**只管健康探测，不管端口归属**（TG-8①）。

    归属校验已上移到 `start_backend` 的 `port_selfcheck`（自举前 fail-fast）：本函数保留
    "打不开就报错"的职责，不再承担"端口是不是我启的"——旧实现只探端口不校验归属，
    于是 dev 后端在跑时脚本会**静默复用它**并施加 parse/embed 负载（卡文事故形态）。
    """
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
        server.wait(timeout=10)  # TG-8③：kill 后也**必须 wait**——否则进程仍可能持有临时目录里的句柄


def dump_log_tail(server_log: Path, n: int = 6000) -> None:
    if server_log.exists():
        print("\n===== backend server log (tail) =====")
        print(server_log.read_text(encoding="utf-8", errors="replace")[-n:])


def fetch_usage(base: str = "", settle_quiet_s: float = 0.0, settle_max_s: float = 0.0) -> dict:
    """读后端进程累计用量（`/api/usage`，Retro ③）。失败返回 {}，绝不影响主流程。

    `settle_quiet_s > 0` 时做**有界稳定等待**：litellm 成功回调是异步落地的（复核 round-4 major
    实测：调用刚返回时计数仍为 0，约 1.5s 后才可见），"刚跑完就读账"会漏掉尾部用量。
    轮询到 `calls/total_tokens` 在 `settle_quiet_s` 内不再增长，或达到 `settle_max_s` 上限即返回。
    """
    url = f"{base or f'http://127.0.0.1:{PORT}'}/api/usage"

    def _once() -> dict:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code == 200:
                return r.json().get("usage") or {}
        except Exception:
            pass
        return {}

    if settle_quiet_s <= 0:
        return _once()
    deadline = time.monotonic() + max(0.0, settle_max_s)
    last = _once()
    stable_since = time.monotonic()
    while True:
        time.sleep(0.1)
        cur = _once()
        if (cur.get("calls"), cur.get("total_tokens")) != (last.get("calls"), last.get("total_tokens")):
            last, stable_since = cur, time.monotonic()
            continue
        now = time.monotonic()
        if now - stable_since >= settle_quiet_s or now >= deadline:
            return last


def report_usage(base: str = "", sink: dict | None = None) -> dict:
    """打印实测用量与成本，并以 `MEASURED_*` 行暴露给 `run_suite` 汇总。

    口径：token 是**实测**；`cost_cny=None`（价表缺该模型，或**一条调用都没记到**）时打印 `unknown`——
    宁可不认成本，也不臆测/不把空账当 0（复核 round-4 major：空账若记成 0.0 会把闸门从
    unknown 误推到 measured 并低估金额）。读取前做有界稳定等待以覆盖回调异步落地。

    若环境变量 `PAPERQA_SUITE_METRICS` 指向一个文件（run_suite 会设置），同时**追加一行 JSON**：
    suite 据此聚合出 `cost_measured_cny`，供 `scripts/scheduled-tasks.py` 自动回填三态闸门。
    """
    u = fetch_usage(base, settle_quiet_s=0.6, settle_max_s=5.0)
    cost = (u.get("cost") or {}) if u else {}
    cny = cost.get("cost_cny")
    print(f"MEASURED_CALLS={u.get('calls', 0)}")
    print(f"MEASURED_TOKENS={u.get('total_tokens', 0)}")
    print(f"MEASURED_COST_CNY={'unknown' if cny is None else cny}")
    if cost.get("no_data"):
        print("MEASURED_NOTE=空账（一条调用都没记到）→ 成本记 unknown")
    if cost.get("unpriced_models"):
        print(f"MEASURED_UNPRICED_MODELS={','.join(cost['unpriced_models'])}")
    if u:
        print("MEASURED_USAGE_JSON=" + json.dumps(u, ensure_ascii=False))
    if sink is not None:
        sink["usage"] = u
    _append_metric(u)
    return u


def _append_metric(u: dict) -> None:
    """把本次用量写成 suite 指标文件的一行（未设置 env 时静默跳过）。

    ⚠️ **局部变量名不要叫 `path`**（TG-8③ 实测）：`verify_artifact_paths.py` 的写盘目标分解器
    是**按变量名**收集赋值的（`TargetResolver.values`），而"套件里先跑过 `verify_agentops.py`"
    会让扫描集里出现**另一个** `path = Path(args.spec_file)` → 同名多处且取值不一致 → 本文件的
    `open(path, …)` 被判成"动态目标"，`e2e_common.py` 的计数从 2 顶到 3、**顶破棘轮上限**。
    后果是**测试顺序依赖**：`verify_artifact_paths.py` 单跑 PASS、在全序列里 FAIL（实测两次）。
    改名后判据与顺序无关（同类改名见 `_apply_offline_env` 的 `guard_path`）。
    """
    metrics_path = os.environ.get("PAPERQA_SUITE_METRICS", "")
    if not metrics_path:
        return
    try:
        cost = (u.get("cost") or {}) if u else {}
        rec = {
            "script": Path(sys.argv[0]).name,
            "calls": u.get("calls", 0),
            "total_tokens": u.get("total_tokens", 0),
            "prompt_tokens": u.get("prompt_tokens", 0),
            "completion_tokens": u.get("completion_tokens", 0),
            "cost_cny": cost.get("cost_cny"),
            "partial_cost_cny": cost.get("partial_cost_cny"),
            "unpriced_models": cost.get("unpriced_models") or [],
        }
        with open(metrics_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
