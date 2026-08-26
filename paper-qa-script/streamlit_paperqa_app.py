import asyncio
import importlib.util
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from paperqa import Docs
from paperqa import Settings
from paperqa.agents.main import agent_query
from paperqa.agents.search import get_directory_index
from paperqa.settings import AgentSettings, IndexSettings, ParsingSettings

try:
    import graphviz as gv
except Exception:
    gv = None


def _ensure_graphviz_on_path() -> None:
    """把常见 Graphviz 安装目录加入 PATH（当 dot 不在 PATH 时），使 graphviz 包可渲染。"""
    import shutil

    if shutil.which("dot"):
        return
    for _d in (
        r"C:\Program Files\Graphviz\bin",
        r"C:\Program Files (x86)\Graphviz\bin",
        r"C:\ProgramData\chocolatey\bin",
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
    ):
        if os.path.isdir(_d) and (
            os.path.isfile(os.path.join(_d, "dot"))
            or os.path.isfile(os.path.join(_d, "dot.exe"))
        ):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            return


_ensure_graphviz_on_path()

class _NoopRuntimeTracer:
    def __init__(self) -> None:
        self.events = []

    def __enter__(self) -> "_NoopRuntimeTracer":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


try:
    from runtime_trace import RuntimeTracer
except Exception:
    try:
        # Fallback: load sibling file explicitly when app is launched with a different cwd.
        _this_dir = Path(__file__).resolve().parent
        _rt_path = _this_dir / "runtime_trace.py"
        if str(_this_dir) not in sys.path:
            sys.path.insert(0, str(_this_dir))
        spec = importlib.util.spec_from_file_location("runtime_trace", _rt_path)
        if spec is None or spec.loader is None:
            RuntimeTracer = _NoopRuntimeTracer
        else:
            _mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_mod)
            RuntimeTracer = _mod.RuntimeTracer
    except Exception:
        RuntimeTracer = _NoopRuntimeTracer


from provider_config import get_provider_config, PROVIDERS, DEFAULT_PROVIDER  # noqa: E402


class SessionLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Redact API keys in logs
            msg = re.sub(r"sk-[A-Za-z0-9]{16,}", "sk-***REDACTED***", msg)
            # Trim extremely long log lines (e.g. full settings dump)
            if len(msg) > 1800:
                msg = msg[:1800] + " ...[truncated]"
            st.session_state.setdefault("logs", []).append(msg)
        except Exception:
            pass


def init_state() -> None:
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("last_index_info", None)
    st.session_state.setdefault("last_answer", None)
    st.session_state.setdefault("last_pipeline", None)
    st.session_state.setdefault("last_runtime_trace", None)
    st.session_state.setdefault("runtime_trace_all", [])
    st.session_state.setdefault("runtime_trace_run_seq", 0)
    st.session_state.setdefault("async_loop", None)
    st.session_state.setdefault("logging_ready", False)


def run_coro(coro):
    loop = st.session_state.get("async_loop")
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        st.session_state["async_loop"] = loop
    _reset_litellm_logging_worker(loop)
    return loop.run_until_complete(coro)


def _reset_litellm_logging_worker(loop: asyncio.AbstractEventLoop) -> None:
    """
    LiteLLM keeps a global async LoggingWorker with an asyncio.Queue.
    In Streamlit reruns, that queue can stay bound to an old loop and cause:
    "Queue ... is bound to a different event loop".
    Rebind the worker to the current session loop before each run.
    """
    try:
        from litellm.litellm_core_utils import logging_worker as lw

        worker = getattr(lw, "GLOBAL_LOGGING_WORKER", None)
        if worker is None:
            return

        task = getattr(worker, "_worker_task", None)
        if task is not None and not task.done():
            task.cancel()
        worker._worker_task = None
        worker._queue = None

        # Start worker on current loop so future enqueue/get happen on this loop.
        loop.call_soon(worker.start)
    except Exception:
        # Best effort only; do not block core QA flow.
        return


def append_runtime_trace(events: list[dict], source: str) -> None:
    if not events:
        return
    st.session_state["runtime_trace_run_seq"] += 1
    run_id = st.session_state["runtime_trace_run_seq"]
    all_events: list[dict] = st.session_state["runtime_trace_all"]
    next_global_id = (all_events[-1]["global_call_id"] + 1) if all_events else 1
    merged: list[dict] = []
    for i, e in enumerate(events):
        item = dict(e)
        item["run_id"] = run_id
        item["source"] = source
        item["global_call_id"] = next_global_id + i
        merged.append(item)
    all_events.extend(merged)
    st.session_state["runtime_trace_all"] = all_events
    st.session_state["last_runtime_trace"] = merged


def setup_logging(level: str) -> None:
    if st.session_state["logging_ready"]:
        logging.getLogger().setLevel(getattr(logging, level))
        return
    root = logging.getLogger()
    root.setLevel(getattr(logging, level))
    handler = SessionLogHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root.addHandler(handler)

    # Keep noise down by default; can still inspect process via app logs.
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    st.session_state["logging_ready"] = True


def build_settings(
    api_key: str,
    api_base: str,
    model: str,
    embedding_model: str,
    temperature: float,
    paper_dir: str,
    index_name: str,
    embedding_batch_size: int,
    use_doc_details: bool,
    rebuild_index: bool,
    provider: str = "",
) -> Settings:
    provider_cfg = get_provider_config(provider or None)
    os.environ["OPENAI_API_KEY"] = api_key

    def _litellm_params(model_name: str, temp: float | None = None) -> dict:
        p: dict = {"model": model_name, "api_key": api_key}
        if api_base:
            p["api_base"] = api_base
        if temp is not None:
            p["temperature"] = temp
        if provider_cfg.get("thinking_disabled"):
            # DeepSeek 思考模式需关闭以支持多轮工具调用（litellm 用 extra_body 透传）
            p["extra_body"] = {"thinking": {"type": "disabled"}}
        return p

    vision_model = provider_cfg["vision_model"]
    llm_config = {
        "name": model,
        "model_list": [
            {"model_name": model, "litellm_params": _litellm_params(model, temperature)}
        ],
    }
    vision_config = {
        "name": vision_model,
        "model_list": [
            {"model_name": vision_model, "litellm_params": _litellm_params(vision_model)}
        ],
    }
    embedding_config = {
        "name": embedding_model,
        "model_list": [
            {"model_name": embedding_model, "litellm_params": _litellm_params(embedding_model)}
        ],
        "batch_size": embedding_batch_size,
    }
    embedding_local = bool(provider_cfg["embedding_local"]) and embedding_model.startswith("st-")

    return Settings(
        llm=model,
        llm_config=llm_config,
        summary_llm=vision_model,
        summary_llm_config=vision_config,
        agent=AgentSettings(
            agent_llm=model,
            agent_llm_config=llm_config,
            rebuild_index=rebuild_index,
            index=IndexSettings(
                paper_directory=str(Path(paper_dir).absolute()),
                files_filter=lambda f: f.suffix in {".pdf", ".txt", ".md", ".html"},
                name=index_name,
            ),
        ),
        embedding=embedding_model,
        # local "st-*" SentenceTransformer embeddings don't use the API model_list config
        embedding_config=(
            {"batch_size": embedding_batch_size} if embedding_local else embedding_config
        ),
        parsing=ParsingSettings(
            use_doc_details=use_doc_details,
            enrichment_llm=vision_model,
            enrichment_llm_config=vision_config,
        ),
    )


async def build_index(settings: Settings) -> dict:
    index = await get_directory_index(settings=settings)
    index_files = await index.index_files
    return {
        "index_name": index.index_name,
        "fields": index.fields,
        "changed": index.changed,
        "file_count": len(index_files),
        "files": index_files,
    }


async def ask_question(settings: Settings, question: str, agent_type: str):
    return await agent_query(query=question, settings=settings, agent_type=agent_type)


def _start_node(name: str, node_input: dict) -> dict:
    return {
        "name": name,
        "input": node_input,
        "output": None,
        "error": None,
        "status": "running",
        "_t0": time.perf_counter(),
        "duration_s": None,
    }


def _end_node(node: dict, output: dict | None = None, error: str | None = None) -> dict:
    node["duration_s"] = round(time.perf_counter() - node["_t0"], 3)
    node.pop("_t0", None)
    if error:
        node["status"] = "failed"
        node["error"] = error
    else:
        node["status"] = "ok"
        node["output"] = output or {}
    return node


async def run_transparent_pipeline(
    settings: Settings, question: str, search_top_n: int
) -> tuple[dict, object]:
    pipeline = {"question": question, "mode": "transparent", "nodes": []}

    # Node 1: load/build index
    node = _start_node(
        "Load Index",
        {"index_name": settings.agent.index.name, "paper_directory": settings.agent.index.paper_directory},
    )
    try:
        try:
            search_index = await get_directory_index(settings=settings, build=False)
            build_mode = False
        except RuntimeError:
            search_index = await get_directory_index(settings=settings, build=True)
            build_mode = True
        index_files = await search_index.index_files
        pipeline["nodes"].append(
            _end_node(
                node,
                {
                    "build_mode": build_mode,
                    "index_name": search_index.index_name,
                    "indexed_files": len(index_files),
                },
            )
        )
    except Exception as exc:
        pipeline["nodes"].append(_end_node(node, error=traceback.format_exc()))
        raise RuntimeError(f"Load Index failed: {exc}") from exc

    # Node 2: retrieve candidate files from search index
    node = _start_node("Retrieve Candidates", {"question": question, "top_n": search_top_n})
    try:
        results = await search_index.query(question, top_n=search_top_n, keep_filenames=True)
        candidate_paths = [r[1] for r in results if isinstance(r, tuple) and len(r) == 2]
        if not candidate_paths:
            all_paths = list((await search_index.index_files).keys())
            candidate_paths = all_paths[:search_top_n]
        pipeline["nodes"].append(
            _end_node(
                node,
                {
                    "candidate_count": len(candidate_paths),
                    "candidate_paths": candidate_paths,
                },
            )
        )
    except Exception as exc:
        pipeline["nodes"].append(_end_node(node, error=traceback.format_exc()))
        raise RuntimeError(f"Retrieve Candidates failed: {exc}") from exc

    # Node 3: parse/chunk/embed by adding docs
    node = _start_node("Parse Chunk Embed", {"candidate_count": len(candidate_paths)})
    docs = Docs()
    try:
        per_file = []
        paper_dir = Path(settings.agent.index.paper_directory)
        for p in candidate_paths:
            before_texts = len(docs.texts)
            t0 = time.perf_counter()
            abs_path = str((paper_dir / p).resolve()) if not Path(p).is_absolute() else p
            docname = await docs.aadd(path=abs_path, settings=settings)
            per_file.append(
                {
                    "file": p,
                    "docname": docname,
                    "added_chunks": len(docs.texts) - before_texts,
                    "duration_s": round(time.perf_counter() - t0, 3),
                }
            )
        pipeline["nodes"].append(
            _end_node(
                node,
                {
                    "docs_count": len(docs.docs),
                    "texts_count": len(docs.texts),
                    "per_file": per_file,
                },
            )
        )
    except Exception as exc:
        pipeline["nodes"].append(_end_node(node, error=traceback.format_exc()))
        raise RuntimeError(f"Parse Chunk Embed failed: {exc}") from exc

    # Node 4: gather evidence
    node = _start_node("Gather Evidence", {"question": question})
    try:
        evidence_session = await docs.aget_evidence(question, settings=settings)
        pipeline["nodes"].append(
            _end_node(
                node,
                {
                    "contexts_count": len(evidence_session.contexts or []),
                    "context_ids": [c.id for c in (evidence_session.contexts or [])][:20],
                    "token_counts": evidence_session.token_counts,
                },
            )
        )
    except Exception as exc:
        pipeline["nodes"].append(_end_node(node, error=traceback.format_exc()))
        raise RuntimeError(f"Gather Evidence failed: {exc}") from exc

    # Node 5: answer
    node = _start_node("Generate Answer", {"question": question})
    try:
        answer_session = await docs.aquery(evidence_session, settings=settings)
        pipeline["nodes"].append(
            _end_node(
                node,
                {
                    "answer_chars": len(answer_session.answer or ""),
                    "references_present": bool(answer_session.references),
                    "used_contexts": sorted(list(answer_session.used_contexts or [])),
                },
            )
        )
        return pipeline, answer_session
    except Exception as exc:
        pipeline["nodes"].append(_end_node(node, error=traceback.format_exc()))
        raise RuntimeError(f"Generate Answer failed: {exc}") from exc


def summarize_pipeline_steps(logs: list[str]) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    patterns = [
        ("agent_start", "开始 Agent", r"Beginning agent"),
        ("search", "检索论文", r"Starting paper search"),
        ("search_done", "检索结果", r"paper_search .* returned"),
        ("embed", "向量化", r"aembedding"),
        ("answer", "生成答案", r"Generating answer"),
        ("agent_finish", "结束 Agent", r"Finished agent"),
        ("error", "错误", r"ERROR|Traceback|MalformedMessageError|Trajectory failed"),
    ]
    for line in logs:
        for key, label, pattern in patterns:
            if re.search(pattern, line):
                steps.append({"type": key, "label": label, "raw": line})
                break
    return steps


def _dot_escape(s: str) -> str:
    # 安全加固：完整转义 DOT 特殊字符，避免论文文本/函数名破坏 DOT 结构
    # 或经 graphviz SVG 输出引入注入内容。
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("|", "\\|")
    )


def _func_to_module(func_id: str) -> str:
    # paperqa.docs.Docs.aadd -> paperqa.docs
    parts = func_id.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return func_id


def build_runtime_trace_dot(
    events: list[dict], granularity: str = "函数级", max_edges: int = 80
) -> str:
    if not events:
        return "digraph G { label=\"No trace events\"; }"

    def node_name(e: dict) -> str:
        return e["func"] if granularity == "函数级" else _func_to_module(e["func"])

    # Node stats
    node_stats: dict[str, dict[str, float]] = {}
    for e in events:
        n = node_name(e)
        item = node_stats.setdefault(n, {"count": 0, "errors": 0, "dur_sum": 0.0})
        item["count"] += 1
        item["dur_sum"] += float(e.get("duration_s") or 0.0)
        if e.get("status") == "error":
            item["errors"] += 1

    # Sequential transition edges (temporal trace)
    edges: dict[tuple[str, str], dict[str, object]] = {}
    ordered = sorted(events, key=lambda x: x.get("call_id", 0))
    for i in range(len(ordered) - 1):
        cur, nxt = ordered[i], ordered[i + 1]
        s, t = node_name(cur), node_name(nxt)
        if s == t:
            continue
        k = (s, t)
        item = edges.setdefault(k, {"count": 0, "sample": None})
        item["count"] = int(item["count"]) + 1
        if item["sample"] is None:
            out_v = str(cur.get("result") or "None")
            in_v = str((nxt.get("args") or {}).get("kwargs") or (nxt.get("args") or {}))
            sample = f"out: {out_v[:80]} | in: {in_v[:80]}"
            item["sample"] = sample

    # Keep strongest edges only
    edge_items = sorted(edges.items(), key=lambda x: int(x[1]["count"]), reverse=True)[
        :max_edges
    ]
    kept_nodes = set()
    for (s, t), _ in edge_items:
        kept_nodes.add(s)
        kept_nodes.add(t)
    if not kept_nodes:
        kept_nodes = set(node_stats.keys())

    lines = [
        "digraph RuntimeTrace {",
        '  rankdir=LR;',
        '  splines=ortho;',
        '  overlap=false;',
        '  graph [fontsize=12, labelloc="t", label="PaperQA Runtime Trace Graph", ranksep="0.7", nodesep="0.4", pad="0.2", dpi=300];',
        '  node [shape=box, style="rounded,filled", fillcolor="#eef5ff", color="#4a6fa5", fontname="Helvetica", fontsize=10, penwidth=1.2];',
        '  edge [color="#6b7280", fontname="Helvetica", fontsize=9, arrowsize=0.8, penwidth=1.0];',
    ]
    for n in sorted(kept_nodes):
        stt = node_stats.get(n, {"count": 0, "errors": 0, "dur_sum": 0.0})
        c = int(stt["count"])
        e = int(stt["errors"])
        avg = (float(stt["dur_sum"]) / c) if c else 0.0
        label = f"{n}\\ncalls={c}, errors={e}, avg={avg:.3f}s"
        fill = "#ffecec" if e > 0 else "#eef5ff"
        lines.append(
            f'  "{_dot_escape(n)}" [label="{_dot_escape(label)}", fillcolor="{fill}"];'
        )
    for (s, t), info in edge_items:
        label = f"x{info['count']}\\n{info['sample']}"
        lines.append(
            f'  "{_dot_escape(s)}" -> "{_dot_escape(t)}" [label="{_dot_escape(str(label))}"];'
        )
    lines.append("}")
    return "\n".join(lines)


def _event_node_name(e: dict, granularity: str) -> str:
    return e["func"] if granularity == "函数级" else _func_to_module(e["func"])


def build_runtime_sequence_dot(
    events: list[dict], granularity: str = "函数级", max_steps: int = 80
) -> str:
    if not events:
        return "digraph G { label=\"No trace events\"; }"

    ordered = sorted(events, key=lambda x: x.get("global_call_id", x.get("call_id", 0)))
    ordered = ordered[-max_steps:]

    lines = [
        "digraph RuntimeSequence {",
        '  rankdir=LR;',
        '  splines=polyline;',
        '  overlap=false;',
        '  graph [fontsize=12, labelloc="t", label="PaperQA Runtime Sequence (Temporal)", ranksep="0.65", nodesep="0.28", pad="0.2", dpi=300];',
        '  node [shape=box, style="rounded,filled", fillcolor="#f8fbff", color="#3b82f6", fontname="Helvetica", fontsize=9, penwidth=1.1, width=2.8, height=0.55, fixedsize=false];',
        '  edge [color="#64748b", fontname="Helvetica", fontsize=8, arrowsize=0.7, penwidth=1.0];',
    ]

    node_ids: list[str] = []
    for i, e in enumerate(ordered):
        gid = e.get("global_call_id", e.get("call_id", i + 1))
        nid = f"n{int(gid)}_{i}"
        node_ids.append(nid)
        base = _event_node_name(e, granularity)
        run_id = e.get("run_id", "-")
        status = e.get("status", "ok")
        dur = float(e.get("duration_s") or 0.0)
        fill = "#ffecec" if status == "error" else "#f8fbff"
        label = f"#{gid} run={run_id}\\n{base}\\n{dur:.3f}s | {status}"
        lines.append(
            f'  "{nid}" [label="{_dot_escape(label)}", fillcolor="{fill}"];'
        )

    for i in range(len(node_ids) - 1):
        cur = ordered[i]
        nxt = ordered[i + 1]
        out_v = str(cur.get("result") or "None")
        in_v = str((nxt.get("args") or {}).get("kwargs") or (nxt.get("args") or {}))
        edge_label = f"out: {out_v[:56]}\\nin: {in_v[:56]}"
        lines.append(
            f'  "{node_ids[i]}" -> "{node_ids[i+1]}" [label="{_dot_escape(edge_label)}"];'
        )

    lines.append("}")
    return "\n".join(lines)


def render_graph_download(dot: str, file_prefix: str) -> None:
    st.download_button(
        label="下载 DOT 源文件",
        data=dot.encode("utf-8"),
        file_name=f"{file_prefix}.dot",
        mime="text/vnd.graphviz",
        use_container_width=True,
    )
    if gv is None:
        st.caption("未检测到 `graphviz` Python 包，当前仅可下载 DOT。")
        return
    try:
        src = gv.Source(dot)
        svg_bytes = src.pipe(format="svg")
        png_bytes = src.pipe(format="png")
        c1, c2 = st.columns(2)
        c1.download_button(
            label="下载高清 SVG",
            data=svg_bytes,
            file_name=f"{file_prefix}.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
        c2.download_button(
            label="下载 PNG",
            data=png_bytes,
            file_name=f"{file_prefix}.png",
            mime="image/png",
            use_container_width=True,
        )
    except Exception as exc:
        st.caption(f"Graphviz 渲染失败，仅保留 DOT 下载。原因: {exc}")


def render_dot_preview(dot: str, use_container_width: bool = True) -> None:
    render_mode = st.radio(
        "预览渲染方式",
        ["内置渲染", "SVG渲染（推荐）"],
        horizontal=True,
        key="trace_preview_mode",
        help="内置渲染偶尔会截断；SVG 渲染更稳定，可滚动。"
    )
    if render_mode == "内置渲染" or gv is None:
        st.graphviz_chart(dot, use_container_width=use_container_width)
        return

    height = st.slider("SVG 预览高度", min_value=420, max_value=1600, value=900, step=60)
    try:
        svg_text = gv.Source(dot).pipe(format="svg").decode("utf-8", errors="replace")
        html = f"""
<div style="width:100%; height:{height}px; overflow:auto; border:1px solid #e5e7eb; border-radius:8px; background:white;">
  {svg_text}
</div>
"""
        components.html(html, height=height + 24, scrolling=True)
    except Exception as exc:
        st.caption(f"SVG 预览失败，回退到内置渲染。原因: {exc}")
        st.graphviz_chart(dot, use_container_width=use_container_width)


def main() -> None:
    st.set_page_config(page_title="PaperQA Debug UI", layout="wide")
    init_state()

    st.title("PaperQA Debug UI (MVP)")
    st.caption("用于本地调试索引与问答过程的最小可视化原型")

    with st.sidebar:
        st.subheader("配置")
        log_level = st.selectbox("日志级别", ["INFO", "DEBUG"], index=0)
        setup_logging(log_level)

        # [macOS original] 默认目录固定在 mac 路径上；Windows 副本默认使用仓库内 data/pdf
        _default_paper_dir = str(
            (Path(__file__).resolve().parent.parent / "data" / "pdf")
        )
        paper_dir = st.text_input("论文目录", _default_paper_dir)
        index_name = st.text_input("索引名", "debug_index")

        # 服务商切换：deepseek / dashscope / openai，切换后自动填充下方默认值（仍可手动覆盖）
        _provider_opts = sorted(PROVIDERS.keys())
        _provider_default = DEFAULT_PROVIDER if DEFAULT_PROVIDER in PROVIDERS else _provider_opts[0]
        provider = st.selectbox(
            "模型服务商",
            _provider_opts,
            index=_provider_opts.index(_provider_default),
            help="切换后自动填充 API Base / 模型 / Embedding 默认值，也可手动修改。",
        )
        _pcfg = get_provider_config(provider)

        api_key = st.text_input(
            "API Key",
            value=_pcfg["api_key"] or os.getenv("OPENAI_API_KEY", ""),
            type="password",
        )
        api_base = st.text_input("API Base", value=_pcfg["api_base"] or "")
        model = st.text_input("LLM 模型", value=_pcfg["model"])
        embedding_model = st.text_input("Embedding 模型", value=_pcfg["embedding"])
        qa_mode = st.selectbox(
            "问答执行模式",
            ["透明流程（推荐）", "Agent流程（Tool Calling）"],
            index=0,
            help="透明流程会展示固定节点的输入输出和耗时；Agent流程更接近原生 paperqa agent。",
        )
        agent_type = st.selectbox(
            "Agent 模式",
            ["fake", "ToolSelector"],
            index=0,
            help=(
                "fake: 稳定、按固定流程走工具；ToolSelector: 由模型决定调用工具，"
                "对工具调用格式要求更高。"
            ),
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.1, 0.1)
        embedding_batch_size = st.number_input(
            "Embedding Batch Size", min_value=1, max_value=64, value=10, step=1
        )
        search_top_n = st.number_input(
            "候选论文 Top-N", min_value=1, max_value=30, value=5, step=1
        )
        use_doc_details = st.checkbox("use_doc_details", value=False)
        rebuild_index = st.checkbox("提问前重建索引", value=False)
        enable_runtime_trace = st.checkbox("启用运行时追踪", value=True)

        col_a, col_b = st.columns(2)
        if col_a.button("清空日志", use_container_width=True):
            st.session_state["logs"] = []
        if col_b.button("清空结果", use_container_width=True):
            st.session_state["last_index_info"] = None
            st.session_state["last_answer"] = None
            st.session_state["last_pipeline"] = None
            st.session_state["last_runtime_trace"] = None
            st.session_state["runtime_trace_all"] = []
            st.session_state["runtime_trace_run_seq"] = 0
            loop = st.session_state.get("async_loop")
            if loop is not None and not loop.is_closed():
                loop.close()
            st.session_state["async_loop"] = None

    if not Path(paper_dir).exists():
        st.error(f"目录不存在: {paper_dir}")
        return

    settings = build_settings(
        api_key=api_key,
        api_base=api_base,
        model=model,
        embedding_model=embedding_model,
        temperature=temperature,
        paper_dir=paper_dir,
        index_name=index_name,
        embedding_batch_size=int(embedding_batch_size),
        use_doc_details=use_doc_details,
        rebuild_index=rebuild_index,
        provider=provider,
    )

    tab_overview, tab_index, tab_chat, tab_nodes, tab_trace, tab_logs = st.tabs(
        ["系统总览", "索引", "问答", "节点执行", "运行时追踪", "日志"]
    )

    with tab_overview:
        st.subheader("PaperQA 整体流程（输入/输出）")
        st.markdown(
            """
1. 文档输入：读取 `paper_directory` 下文件（PDF/TXT/MD/HTML）。
2. 解析与增强：提取文本与媒体；媒体可走 `enrichment_llm` 生成描述。
3. 分块与向量化：文本 chunk 后走 embedding，进入索引。
4. 检索：根据问题召回 top-k 相关片段。
5. 证据总结：`summary_llm` 对召回片段做摘要/打分。
6. 生成答案：`llm` 基于上下文生成最终回答与引用。
            """
        )
        st.markdown("**当前运行配置摘要**")
        st.json(
            {
                "qa_mode": qa_mode,
                "agent_type": agent_type,
                "paper_dir": paper_dir,
                "index_name": index_name,
                "llm": model,
                "embedding": embedding_model,
                "embedding_batch_size": int(embedding_batch_size),
                "use_doc_details": use_doc_details,
                "rebuild_index": rebuild_index,
                "runtime_trace": enable_runtime_trace,
            }
        )

        st.markdown("**最近一次运行步骤时间线**")
        if st.session_state["last_pipeline"]:
            timeline = [
                {
                    "label": n["name"],
                    "raw": f"status={n['status']} | duration={n['duration_s']}s",
                }
                for n in st.session_state["last_pipeline"]["nodes"]
            ]
        else:
            timeline = summarize_pipeline_steps(st.session_state["logs"])
        if timeline:
            for i, step in enumerate(timeline[-30:], start=1):
                st.write(f"{i}. [{step['label']}] {step['raw']}")
        else:
            st.caption("暂无可提取步骤。先执行一次索引或问答。")

    with tab_index:
        st.subheader("索引构建")
        if st.button("构建 / 刷新索引", type="primary"):
            if not api_key:
                st.error("请先填写 API Key")
            else:
                t0 = datetime.now()
                try:
                    with st.spinner("正在构建索引..."):
                        if enable_runtime_trace:
                            tracer = RuntimeTracer()
                            with tracer:
                                info = run_coro(build_index(settings))
                            append_runtime_trace(tracer.events, source="build_index")
                        else:
                            info = run_coro(build_index(settings))
                            st.session_state["last_runtime_trace"] = None
                    st.session_state["last_index_info"] = info
                    dt = datetime.now() - t0
                    st.success(f"索引完成，用时 {dt.total_seconds():.2f}s")
                except Exception:
                    st.error("索引构建失败")
                    st.code(traceback.format_exc())

        info = st.session_state["last_index_info"]
        if info:
            st.json(
                {
                    "index_name": info["index_name"],
                    "fields": info["fields"],
                    "changed": info["changed"],
                    "file_count": info["file_count"],
                }
            )
            st.write("Indexed files:")
            st.json(info["files"])

    with tab_chat:
        st.subheader("提问")
        question = st.text_area("问题", "什么是PaperQA？", height=90)
        if st.button("发送问题", type="primary"):
            if not api_key:
                st.error("请先填写 API Key")
            elif not question.strip():
                st.error("请输入问题")
            else:
                try:
                    with st.spinner("正在回答..."):
                        if enable_runtime_trace:
                            tracer = RuntimeTracer()
                            with tracer:
                                if qa_mode == "透明流程（推荐）":
                                    pipeline, resp = run_coro(
                                        run_transparent_pipeline(
                                            settings, question.strip(), int(search_top_n)
                                        )
                                    )
                                    st.session_state["last_pipeline"] = pipeline
                                else:
                                    resp = run_coro(
                                        ask_question(settings, question.strip(), agent_type)
                                    )
                                    st.session_state["last_pipeline"] = None
                            append_runtime_trace(tracer.events, source="qa")
                        elif qa_mode == "透明流程（推荐）":
                            pipeline, resp = run_coro(
                                run_transparent_pipeline(
                                    settings, question.strip(), int(search_top_n)
                                )
                            )
                            st.session_state["last_pipeline"] = pipeline
                        else:
                            resp = run_coro(
                                ask_question(settings, question.strip(), agent_type)
                            )
                            st.session_state["last_pipeline"] = None
                        if not enable_runtime_trace:
                            st.session_state["last_runtime_trace"] = None
                    st.session_state["last_answer"] = resp
                except Exception:
                    st.error("问答失败")
                    st.code(traceback.format_exc())

        resp = st.session_state["last_answer"]
        if resp:
            if hasattr(resp, "session"):
                status = str(resp.status)
                session = resp.session
            else:
                status = "ok"
                session = resp
            st.write(f"状态: `{status}`")
            if str(status).lower().endswith("fail"):
                st.warning(
                    "Agent 状态是 fail。常见原因是 ToolSelector 模式下模型未按工具调用格式返回。"
                    " 可切换 `问答执行模式=透明流程` 或 `Agent 模式=fake`。"
                )
            st.markdown("**答案**")
            st.write(session.answer)
            with st.expander("查看引用"):
                st.text(session.references or "")
            with st.expander("查看上下文片段"):
                for i, c in enumerate(session.contexts or [], start=1):
                    st.markdown(f"**{i}. {c.id} | score={c.score}**")
                    st.write(c.context)

    with tab_nodes:
        st.subheader("节点执行明细")
        pipeline = st.session_state["last_pipeline"]
        if not pipeline:
            st.caption("暂无节点数据。请在问答页使用 `透明流程（推荐）` 执行一次。")
        else:
            st.write(f"问题：`{pipeline['question']}`")
            for i, node in enumerate(pipeline["nodes"], start=1):
                title = (
                    f"{i}. {node['name']} | status={node['status']} | "
                    f"{node['duration_s']}s"
                )
                with st.expander(title, expanded=(i == 1)):
                    st.markdown("**Input**")
                    st.json(node["input"] or {})
                    if node["status"] == "ok":
                        st.markdown("**Output**")
                        st.json(node["output"] or {})
                    else:
                        st.markdown("**Error**")
                        st.code(node["error"] or "", language="text")

    with tab_trace:
        st.subheader("运行时函数追踪")
        events = st.session_state["runtime_trace_all"] or []
        if not events:
            st.caption("暂无追踪数据。勾选侧边栏 `启用运行时追踪` 后执行索引或问答。")
        else:
            total = len(events)
            err_count = sum(1 for e in events if e["status"] == "error")
            run_count = max((e.get("run_id", 0) for e in events), default=0)
            st.write(
                f"调用总数: **{total}** | 错误: **{err_count}** | 运行轮次: **{run_count}**"
            )
            by_func: dict[str, int] = {}
            for e in events:
                by_func[e["func"]] = by_func.get(e["func"], 0) + 1
            st.markdown("**函数调用频次（Top 20）**")
            top_items = sorted(by_func.items(), key=lambda x: x[1], reverse=True)[:20]
            st.table([{"func": k, "count": v} for k, v in top_items])

            st.markdown("**调用明细（会话累计，最近 400 条）**")
            for e in events[-400:]:
                title = (
                    f"#{e.get('global_call_id', e['call_id'])} "
                    f"(run {e.get('run_id', '-')}, {e.get('source', '-')}) "
                    f"{e['func']} | {e['status']} | "
                    f"{e['duration_s']}s"
                )
                with st.expander(title, expanded=False):
                    st.json(
                        {
                            "started_at": e["started_at"],
                            "run_id": e.get("run_id"),
                            "source": e.get("source"),
                            "call_id_in_run": e["call_id"],
                            "args": e["args"],
                            "result": e["result"],
                            "error": e["error"],
                        }
                    )

            st.markdown("**运行时追踪图**")
            granularity = st.radio(
                "图粒度",
                ["函数级", "模块级"],
                horizontal=True,
                key="trace_graph_granularity",
            )
            graph_mode = st.radio(
                "图模式",
                ["聚合转移图", "时序展开图（推荐）"],
                horizontal=True,
                key="trace_graph_mode",
            )
            if graph_mode == "聚合转移图":
                max_edges = st.slider(
                    "最多显示边数", min_value=20, max_value=240, value=80, step=10
                )
                dot = build_runtime_trace_dot(
                    events, granularity=granularity, max_edges=int(max_edges)
                )
                file_prefix = "paperqa_runtime_aggregate"
            else:
                max_steps = st.slider(
                    "时序展开步数（最近N次调用）",
                    min_value=20,
                    max_value=240,
                    value=90,
                    step=10,
                )
                dot = build_runtime_sequence_dot(
                    events, granularity=granularity, max_steps=int(max_steps)
                )
                file_prefix = "paperqa_runtime_sequence"
            render_dot_preview(dot, use_container_width=True)
            st.markdown("**下载图文件**")
            render_graph_download(dot, file_prefix=file_prefix)

    with tab_logs:
        st.subheader("过程日志")
        logs = st.session_state["logs"]
        if logs:
            st.code("\n".join(logs[-1200:]), language="text")
        else:
            st.caption("暂无日志")


if __name__ == "__main__":
    main()
