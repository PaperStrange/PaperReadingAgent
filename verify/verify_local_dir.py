"""Sprint-15 F-AC3（验收①1.3④）：local_dir/paper_directory 引擎接线实证。

临时目录放入 PaperQA2.pdf → 真实后端 config(local, paper_directory=临时目录) →
load_index(build) → retrieve → 断言候选路径来自临时目录（证明前端改路径后索引真实生效）。
全程本地（st- 向量），零 API 成本。
另含 TG-8① 端口自检两类反向对照：① 可归属占用 ⇒ 三件可操作信息齐全；② 无属主占用
（查询无 PID／镜像名，含系统保留区间）⇒ 文案显式说明这一类。

Run: .venv\\Scripts\\python.exe verify\\verify_local_dir.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC3 引擎接线实证：临时目录 paper_directory → load_index → retrieve 候选来自该目录（免密：注入占位 key，链路无 LLM 调用）；TG-8① 端口自检两类反向对照（① 可归属占用 ⇒ 端口+PID+释放/改端口三件齐全；② 无属主占用 ⇒ 文案具名说明"被占用但查询不到属主进程／系统保留区间"）', 'tier': 'offline', 'providers': [], 'est_seconds': 90, 'est_cost_cny': 0, 'routes': ['/api/new_session', '/api/run_step'], 'requires': ['self-boots-backend']}

import asyncio
import atexit
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
    alloc_port,
    port_in_use,
    port_owner,
    port_selfcheck,
    start_backend,
    stop_backend,
    wait_healthy,
)

# 占用进程**查不到**时 `port_owner` 返回文本的开头（`e2e_common.port_owner` 那处是唯一真源）：
# 本脚本靠它判定"② 无属主占用"这一形态，并据此核错文案里的具名说明。
PORT_NOOWNER_MARK = "查不到占用进程（可自行运行："
# ② 档注入的哨兵值：子进程回显成 `STUB=<值>`，父进程只认这个值 ⇒ 外层环境里的同名变量
# 伪造不了这一档（单一真源，改一处即两处同步）。
OWNERLESS_STUB = "control-not-inherited"
# 接缝自核用的**原始**查询函数引用（在子脚本做任何替换之前捕获；子脚本据此自陈
# `STUBPATCHED=`——见 `SELFCHECK_CHILD`）。
_ORIG_PORT_OWNER = port_owner

BACKEND = ROOT / "paper-qa-script" / "reactflow-paperqa-prototype" / "backend" / "main.py"
# 行 24：后端日志落 `%TEMP%` 的 **run 级唯一目录**（原来是仓库内固定名
# `verify/verify_local_dir_server.log`）。它是并发实例之间的**第二个共享对象**：
# `start_backend` 以 "w" 打开，后跑的实例会**截断**正在跑的那个实例的日志，而失败归因
# （`wait_healthy` 打印的就是它）因此指向别人的后端。回收 = `atexit` 兜底 + 正常出口显式
# `rmtree`；两处目标都是下面这个模块级常量 ⇒ 落点可静态判定（不顶破动态目标棘轮）。
LOG_DIR = Path(tempfile.mkdtemp(prefix="verify_local_dir_log-"))
SERVER_LOG = LOG_DIR / "server.log"


def reclaim_log_dir(attempts: int = 6) -> None:
    """回收 run 级日志目录（行 24）。**必须重试**：后端子进程退出后句柄还压着文件
    0.1~2s（高负载下更久），一次性 `rmtree(ignore_errors=True)` 会**静默半途而废**
    ——实测留下带 `server.log` 的空目录（正是本函数存在的理由）。
    失败即**打印 WARN**（`ignore_errors=False` 才看得见），不假装删干净了。
    """
    for i in range(attempts):
        if not LOG_DIR.exists():
            return
        try:
            shutil.rmtree(LOG_DIR)
            return
        except OSError as exc:
            if i == attempts - 1:
                print(f"WARN: 日志目录未能删净（已重试 {attempts} 次）：{LOG_DIR}"
                      f"（{type(exc).__name__}: {exc}）——残留会占用磁盘")
            else:
                time.sleep(0.2 * (i + 1))


atexit.register(reclaim_log_dir)
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
    "import importlib\n"
    "import verify.e2e_common as _ec\n"
    # 子脚本的"原始查询函数"基准：**本进程内重载一次基座**取装载的属性。为什么不从父进程
    # `.format()` 注入：函数的 `repr()` 不是合法 Python（实测 SyntaxError ⇒ 子脚本 rc=1
    # 但**一条判据都没跑**）。必须先 `import … as _ec` 再 `from … import`：反过来会在本进程
    # 全局里另建 `port_owner` 同名绑定，它不随 `_ec.port_owner` 被替换。
    "_ORIG_OWNER = importlib.reload(_ec).port_owner\n"
    "from verify.e2e_common import PORT, port_selfcheck, start_backend\n"
    # 反向对照开关（TG-8①）：把**占用进程查询**换成"查不到"的实现。要覆盖的第二形态是
    # "**被占却查不到属主**"（CI 实测：端口落在 Hyper-V/WinNAT 的**系统保留区间**，已占用但
    # 无属主进程），而"自己 bind 一个 socket"永远查得到**自己的** PID ⇒ 该形态无法用真实占用
    # 造出来，只能替换查询函数（stub-ROOT-C）。占用探测 / fail-fast / 文案渲染全部照旧；
    # ✱ stub 返回值必须与生产同形（`查不到占用进程（可自行运行：…）`）——`port_selfcheck`
    # 按此前缀选"无属主"分支并渲染具名说明。⚠️ 上面的 `from … import port_owner` 陷阱实测让
    # stub 静默失效（读回真实 PID）：子脚本只按**模块属性** `_ec.port_owner` 取查询函数。
    # 不设该变量 = 'none' ⇒ 生产路径行为完全不变（未知值按 'missing' 处理）。
    "if os.environ.get('PAPERQA_VERIFY_OWNER_STUB', 'none').strip().lower() != 'none':\n"
    "    _ec.port_owner = lambda port: (\n"
    "        '查不到占用进程（可自行运行：Get-NetTCPConnection -LocalPort '\n"
    "        + str(port) + ' -State Listen）')\n"
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
    # 自陈本进程里查询函数的**实际形状**（三条独立通道）：`CHILD-OWNERLESS=` 该端口此刻是不是
    # 无属主形态；`STUBPATCHED=` 接缝是否生效；`STUB=` 回显收到的取值。为什么不由父进程自己查：
    # 父进程就是占用者，它的结果与"子进程是哪一档"无关——拿它当自核**恒真**＝假绿。
    # ⚠️ 自陈行的**名字**必须与父进程 detail 的标签不同：原用 `OWNERLESS= True` 做子串，而
    # detail 里有中文标签『子进程自陈无属主=True』⇒ 一条断言在两个命名空间找同一个串，父进程
    # 那半边恒真、自核形同虚设（本自核抓出来的）。`STUB=` 让父进程**只认自己注入的哨兵值**
    # （`control-not-inherited`）：外层环境恰好设了同名变量时对照不会被伪装成有效（实测：忘了
    # 清 shell 环境，四个档全串成 stub 档）。
    "    print('CHILD-OWNERLESS=', _ec.port_owner(PORT).startswith(\n"
    "        '查不到占用进程（可自行运行：'))\n"
    "    print('STUBPATCHED=', _ec.port_owner is not _ORIG_OWNER)\n"
    "    print('STUB=', os.environ.get('PAPERQA_VERIFY_OWNER_STUB', ''))\n"
    "    raise SystemExit(1)\n"
    "print('PRECHECK-PASSED')\n"
    "raise SystemExit(0)\n"
)
# 接缝自核用的**原始**查询函数引用（在任何替换之前捕获）。
_ORIG_PORT_OWNER = port_owner


def port_selfcheck_conflict_assertions() -> dict:
    """TG-8① 反向对照：**自己起监听占住端口** → 自举必须失败并点名；释放后 → 通过。

    为什么用子进程而不是直接调 `start_backend`：判据的真身是"**脚本进程**以非 0 退出、
    且 stdout 里能读到可操作提示"——同进程 try/except 只能证明"函数抛了异常"，
    证明不了"入口进程确实失败了"，也证明不了"没留下半自举的子进程"。
    **子脚本以内联 `-c` 传入、不落盘**（TG-9 产物落点约定 + 本文件动态目标棘轮：多一个
    `write_text(动态路径)` 就会顶破上限；内联脚本文本不产生任何写盘目标）。

    2026-09-30 补充（CI 红 `含占用PID=False` 的修法）：占用分**两类**，各自真驱动——① 真实占用
    （本进程自己 bind）⇒ 要求三件信息齐全；② 查询无属主（stub 子进程的占用进程查询，见
    `SELFCHECK_CHILD`）⇒ 要求文案具名说明这一类。
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
        # 行 24：`PORT` 是**本 run 分配**的，子进程必须被告知同一端口——否则子进程
        # 自己分配一个空闲端口，"父进程占着 PORT"这条对照就不成立（断言恒真 = 假绿）。
        occupied = run_child("start", {"PAPERQA_VERIFY_PORT": str(PORT)})
        # ② 无属主占用：只把**占用进程查询**换成"查不到"，占用本身仍是真的（listener 还在）；
        # 注入的是**本档哨兵**（不给通用值）：外层环境恰好设了同名变量也伪造不了这一档
        # （父进程只认它自己注入的 `OWNERLESS_STUB`）。
        ownerless = run_child("start", {"PAPERQA_VERIFY_PORT": str(PORT),
                                        "PAPERQA_VERIFY_OWNER_STUB": OWNERLESS_STUB})
        # 释放端口 → 同一路径通过。子进程用 `PAPERQA_VERIFY_PORT` 抬高端口（本基座的 `PORT` 读它），
        # 且**必须在子进程里读**：写死在生成代码里的端口号会忽略该环境变量（实测就是这样，
        # 于是"释放后通过"恒失败——断言自身的假红）。
        # 行 24：改用**分配到的空闲端口**（原写 `PORT + 100`；`PORT` 现在随机，+100 可能
        # 真被占 ⇒ 断言自身的假红）。
        free = run_child("preflight-only", {"PAPERQA_VERIFY_PORT": str(alloc_port())})
    finally:
        listener.close()

    out_occ = (occupied.stdout or "") + (occupied.stderr or "")
    out_noowner = (ownerless.stdout or "") + (ownerless.stderr or "")
    out_free = (free.stdout or "") + (free.stderr or "")
    return {
        "fail_fast": occupied.returncode != 0 and "PRECHECK-PASSED" not in out_occ,
        "pass_when_free": free.returncode == 0 and "PRECHECK-PASSED" in out_free,
        # ① 可归属占用（照旧，**未弱化**）：端口号 ＋ PID ＋ 释放/改端口提示，缺一即 FAIL。
        "actionable_attributable": all(t in out_occ for t in (str(PORT), f"PID={pid}",
                                                             "释放端口", "改用其它端口")),
        # ② 无属主占用：要求**具名说明这一类**，不强制要求一个并不存在的 PID。逐字核的短语＝渲染
        # 真源 `e2e_common.port_selfcheck` 的文案（是**查询不到属主进程**，不是"查不到属主进程"
        # ——后者只是前者的子串；实测因这一字之差撞过一次假红）。
        "actionable_ownerless": all(t in out_noowner for t in (
            str(PORT), PORT_NOOWNER_MARK, "被占用但查询不到属主进程",
            "系统保留区间", "excluded port range", "改用其它端口")),
        # 夹具自核（**三条独立通道**，都读子进程 stdout 的自陈行）：该档在子进程里确实是无属主
        # 形态、接缝确实生效、且收到本档注入的哨兵；缺任一条 ⇒ ②退化成①的重复或 stub 静默失效
        # ＝假绿。三个标记只出现在子进程输出里（名字与下面的中文标签刻意不同）。
        "ownerless_stub_live": all(t in out_noowner for t in ("CHILD-OWNERLESS= True",
                                                              "STUBPATCHED= True",
                                                              f"STUB= {OWNERLESS_STUB}")),
        "ownerless_stub_real_owner": f"PID={pid}" in out_occ,
        "detail_fail": f"rc={occupied.returncode} out={out_occ.strip().splitlines()[:2]}",
        "detail_attributable": (f"含端口={str(PORT) in out_occ} "
                                f"含占用PID={f'PID={pid}' in out_occ} "
                                f"含释放提示={'释放端口' in out_occ} "
                                f"含改端口提示={'改用其它端口' in out_occ}"),
        "detail_ownerless": (
            f"rc={ownerless.returncode} 含端口={str(PORT) in out_noowner} "
            f"含『无属主』={PORT_NOOWNER_MARK in out_noowner} "
            f"含无属主说明={'被占用但查询不到属主' in out_noowner} "
            f"含reserved={'系统保留区间' in out_noowner}／"
            f"{'excluded port range' in out_noowner} "
            f"含改端口={'改用其它端口' in out_noowner} "
            f"含假PID={f'PID={pid}' in out_noowner} "
            f"子进程自陈={'CHILD-OWNERLESS= True' in out_noowner} "
            f"接缝生效={'STUBPATCHED= True' in out_noowner} "
            f"哨兵回显={f'STUB= {OWNERLESS_STUB}' in out_noowner} "
            f"①档含本进程PID={f'PID={pid}' in out_occ}"),
        "detail_free": f"rc={free.returncode} out={out_free.strip()[:80]}",
    }


async def main() -> int:
    import httpx

    # 行 24：先报本 run 的身份——并发实例的失败归因靠它（谁用哪个端口、日志落在哪）
    print(f"[run] PORT={PORT} LOG={SERVER_LOG}")

    # ── TG-8①：自举前端口自检（**可核断言，含反向对照**） ────────────────────────────────
    # 事故形态（卡文正文）：`wait_healthy` 只探测端口、不校验"服务是不是自己启的" → dev 后端在跑时
    # 脚本会**静默复用它**并施加 parse/embed 负载；反之套件也会抢占/顶掉 dev 后端。
    # 修法判据 = 自举前 fail-fast 并点名，**不复用、不换端口**；文案分两类（都 fail-fast）。
    # 本函数的 daemon 线程只活到 `main()` 返回（`asyncio.run` 之后进程即退出），故不会留下监听。
    port_selfcheck((PORT,))  # ⑤c：本 run 分到的端口此刻确为空（占用即在此 fail-fast）
    conflicts = port_selfcheck_conflict_assertions()
    ok("⑤ 端口被占用时自举**明确失败**并点名：不发子进程、不静默复用（反向对照 / 修复前此断言不成立）",
       conflicts["fail_fast"], conflicts["detail_fail"])
    # 2026-09-30：原**一条**"三件可操作信息"断言（隐含"占用者一定可归属"）拆成下面两条——不是
    # 放宽：① 的判据逐字保留，② 覆盖 CI 新暴露的"被占却查不到属主"形态（旧判据在那一支要求
    # 一个**并不存在**的 PID ⇒ 判红）。
    ok("⑤① 可归属占用（查得到 PID/镜像名）：端口号 + 占用进程 + 怎么改/怎么释放，缺任一即 FAIL",
       conflicts["actionable_attributable"], conflicts["detail_attributable"])
    ok("⑤② 无属主占用（查询无 PID/镜像名，含系统保留区间）：文案**显式说明这一类**"
       "（『被占用但查询不到属主进程』＋『系统保留区间/excluded port range』）"
       "＋改端口提示——不强制一个并不存在的 PID",
       conflicts["actionable_ownerless"], conflicts["detail_ownerless"])
    ok("⑤②-夹具自核：无属主对照里**确实没有** PID/镜像名（查询被替换成空实现）"
       "——否则这条对照会退化成①的重复",
       conflicts["ownerless_stub_live"] and conflicts["ownerless_stub_real_owner"],
       f"无属主档含『查不到占用进程』={conflicts['ownerless_stub_live']} "
       f"同一端口真实查询可归属={conflicts['ownerless_stub_real_owner']}")
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
        reclaim_log_dir()  # 行 24：回收 run 级日志目录（重试 + 失败即 WARN）
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
